// Display helpers for the tagging screens: side names, the announcement line (FR-048,
// @needs-verification call format) and the game status read from the sheet.
import { describe, expect, it } from 'vitest';
import type { Match } from '@/lib/api/types';
import type { ScoreSheet, SheetRow } from '@/lib/tagging/types';
import { gameStatus, sideNames, tagLine } from '@/lib/tagging/view';

const match = (participants: Match['participants']): Match => ({
  id: 'x', title: 't', format: 'doubles', status: 'video_received', media: null, created_at: 'x', updated_at: 'x', participants,
});
const row: SheetRow = {
  rally_id: 'r', number: 7, game: 1, start_ms: 0, end_ms: 1, serving_side: 'A', score_before: '6-4-1',
  score_after: '4-6-1', winning_side: 'B', ending: 'winner', responsible_player: null, fault_kind: null, marker: null, corrected_by_user: false,
};
const sheet = (over: Partial<ScoreSheet> = {}): ScoreSheet => ({ rules_version: 'v', unofficial: true, label: 'l', rows: [], ...over });

describe('sideNames', () => {
  it('without participants, side A is "your side" and labels have no names', () => {
    const n = sideNames(match([]));
    expect(n.mySide).toBe('A');
    expect(n.label('A')).toBe('Your side');
    expect(n.label('B')).toBe('Other side');
  });
  it('names each side after the player marked "me"', () => {
    const n = sideNames(match([
      { slot: 'B2', nickname: 'Bo', is_me: false }, { slot: 'B1', nickname: 'Ivy', is_me: true },
      { slot: 'A1', nickname: 'Carlos', is_me: false },
    ]));
    expect(n.mySide).toBe('B');
    expect(n.label('B')).toBe('Your side (Ivy and Bo)');
    expect(n.label('A')).toBe('Other side (Carlos)');
    expect(n.players.map((p) => p.slot)).toEqual(['A1', 'B1', 'B2']);
  });
});

describe('tagLine (FR-048 example "Rally 7: them. Score 4-6-1.")', () => {
  it('a conflict row says it needs a decision, never a score', () => {
    expect(tagLine({ ...row, marker: 'needs_decision', score_after: null }, 'A')).toBe('Rally 7: them. Needs your decision.');
  });
  it('a replay names no winner', () => {
    expect(tagLine({ ...row, ending: 'replay', winning_side: null, score_after: '6-4-1' }, 'A')).toBe('Rally 7: replay. Score 6-4-1.');
  });
  it('us / them from the player side', () => {
    expect(tagLine(row, 'A')).toBe('Rally 7: them. Score 4-6-1.');
    expect(tagLine(row, 'B')).toBe('Rally 7: us. Score 4-6-1.');
  });
});

describe('gameStatus', () => {
  it('no games and no rallies: nothing started', () => {
    expect(gameStatus(sheet({ games: [] }))).toMatchObject({ current: 0, over: false, matchOver: false });
    expect(gameStatus(sheet())).toMatchObject({ current: 0 });
  });
  it('reads the newest game and the match winner', () => {
    const s = gameStatus(sheet({ games: [{ number: 1, first_serving_side: 'B', winner: 'A' }], match_winner: null }));
    expect(s).toEqual({ current: 1, firstServingSide: 'B', over: true, lastWinner: 'A', matchOver: false, matchWinner: null });
    expect(gameStatus(sheet({ games: [], match_winner: 'B' })).matchOver).toBe(true);
  });
  it('without a games list, falls back to the rows', () => {
    expect(gameStatus(sheet({ rows: [row, { ...row, game: 2, serving_side: 'B' }] }))).toMatchObject({ current: 2, firstServingSide: 'B' });
  });
});
