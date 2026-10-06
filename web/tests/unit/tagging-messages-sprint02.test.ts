// Review round 2 (BE-RV1-FE-01, QA-RV2-11): the Sprint 2 refusals of api-sprint-02 §3/§4 each
// get copy that says what happened and what the player can do. A refusal that a retry can never
// fix (rules_unavailable, scorebook_full) never says "Try again". Negative cases first.
import { describe, expect, it } from 'vitest';
import { ApiError } from '@/lib/api/client';
import { commandProblem, gameStartProblem, tagFailureMessage } from '@/lib/tagging/messages';

const invalidRally = (code: string, field = 'start_ms') =>
  new ApiError(422, 'invalid_rally', null, { fields: [{ field, code: code as never }] });

describe('tag refusals (T-01)', () => {
  it('rules_unavailable is not a retry: scoring for the format is not available yet', () => {
    const m = tagFailureMessage(new ApiError(409, 'rules_unavailable', 'ref_0123456789abcdef'));
    expect(m).toBe('Scoring for this match format is not available yet.');
    expect(m).not.toMatch(/try again/i);
  });

  it('scorebook_full names the cap and is not a retry', () => {
    const rallies = tagFailureMessage(new ApiError(422, 'scorebook_full', null, { fields: [{ field: null, code: 'too_many_rallies' }] }));
    const changes = tagFailureMessage(new ApiError(422, 'scorebook_full', null, { fields: [{ field: null, code: 'too_many_changes' }] }));
    expect(rallies).toBe('The rally was not saved: this match cannot hold any more rallies.');
    expect(changes).toBe('The rally was not saved: this match cannot hold any more changes.');
    expect(rallies + changes).not.toMatch(/try again/i);
  });

  it('rate_limited says when to try again (local time), or to wait a minute', () => {
    const at = new ApiError(429, 'rate_limited', null, { retryAt: '2026-10-06T14:32:00Z' });
    expect(tagFailureMessage(at, 'UTC')).toBe('The rally was not saved: too many changes in a short time. You can try again at 14:32.');
    expect(tagFailureMessage(new ApiError(429, 'rate_limited'))).toBe(
      'The rally was not saved: too many changes in a short time. Wait a minute, then try again.',
    );
  });

  it('invalid_rally says which time rule failed, not always "overlap"', () => {
    expect(tagFailureMessage(invalidRally('time_after_video', 'end_ms'))).toBe(
      'The rally was not saved: it ends after the end of the video. Mark its end again.',
    );
    expect(tagFailureMessage(invalidRally('out_of_game_order'))).toBe(
      "The rally was not saved: its times fall among another game's rallies. Mark its start and end again.",
    );
    expect(tagFailureMessage(invalidRally('end_before_start', 'end_ms'))).toBe(
      'The rally was not saved: it ends before it starts. Mark its start and end again.',
    );
    expect(tagFailureMessage(invalidRally('overlaps_rally'))).toBe(
      'The rally was not saved: its times overlap another rally. Mark its start and end again.',
    );
    expect(tagFailureMessage(invalidRally('time_after_video', 'end_ms'))).not.toMatch(/overlap/);
  });
});

describe('game start refusals (T-02)', () => {
  it('rules_unavailable is not a retry', () => {
    const m = gameStartProblem(new ApiError(409, 'rules_unavailable', 'ref_0123456789abcdef'), 1);
    expect(m).toBe('Scoring for this match format is not available yet.');
  });

  it('scorebook_full, rate_limited, game_not_over and a server error', () => {
    expect(gameStartProblem(new ApiError(422, 'scorebook_full', null, { fields: [{ field: null, code: 'too_many_changes' }] }), 2)).toBe(
      'Game 2 was not started: this match cannot hold any more changes.',
    );
    expect(gameStartProblem(new ApiError(429, 'rate_limited'), 2)).toBe(
      'Game 2 was not started: too many changes in a short time. Wait a minute, then try again.',
    );
    expect(gameStartProblem(new ApiError(409, 'game_not_over'), 2)).toBe(
      'Game 2 cannot start yet: the game before it is not over. Open the score sheet to check it.',
    );
    expect(gameStartProblem(new ApiError(500, 'internal_error', 'ref_0123456789abcdef'), 1)).toBe(
      'Game 1 could not be started. Try again. Reference: ref_0123456789abcdef',
    );
  });
});

describe('correction and decision refusals (S-01)', () => {
  it('rules_unavailable, scorebook_full and rate_limited', () => {
    expect(commandProblem(new ApiError(409, 'rules_unavailable'), 'Correction')).toBe('Scoring for this match format is not available yet.');
    expect(commandProblem(new ApiError(422, 'scorebook_full', null, { fields: [{ field: null, code: 'too_many_changes' }] }), 'Correction')).toBe(
      'Correction was not saved: this match cannot hold any more changes.',
    );
    expect(commandProblem(new ApiError(429, 'rate_limited', null, { retryAt: '2026-10-06T14:32:00Z' }), 'Undo', 'UTC')).toBe(
      'Undo was not saved: too many changes in a short time. You can try again at 14:32.',
    );
  });

  it('move_to_previous_game refusals say what to do instead', () => {
    const decision = (code: string) =>
      commandProblem(new ApiError(422, 'validation_failed', null, { fields: [{ field: 'decision', code: code as never }] }), 'Decision');
    expect(decision('previous_game_over')).toBe(
      'The previous game is already over, so the rally cannot move back into it. Remove the rally, or move it to the next game.',
    );
    expect(decision('not_first_in_game')).toBe(
      'Only the first rally of a game can move back to the previous game. Decide that rally first.',
    );
    expect(decision('no_previous_game')).toBe('There is no previous game to move this rally to.');
    expect(decision('not_needed')).toBe('This rally no longer needs a decision.');
  });

  it('a time correction refusal names the rule', () => {
    expect(commandProblem(invalidRally('time_after_video', 'end_ms'), 'Correction')).toBe(
      'Correction was refused: the rally would end after the end of the video.',
    );
  });
});
