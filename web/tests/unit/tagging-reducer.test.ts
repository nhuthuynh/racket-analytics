// ST-027 FE slice 1 (sprint-02 §5 front-end TDD plan): the tagging reducer and the optimistic
// score. Negative cases first: "end" before "start" is ignored; the optimistic score rolls back
// on a server error. The score itself always comes from the server sheet (FR-049); the client
// only shows a provisional call until the server answers (NFR-012a).
import { describe, expect, it } from 'vitest';
import { initialTagging, taggingReducer, type TaggingState } from '@/lib/tagging/reducer';
import { nextCall, type CallState } from '@/lib/tagging/score';
import type { ScoreSheet, SheetRow } from '@/lib/tagging/types';

function row(over: Partial<SheetRow> = {}): SheetRow {
  return {
    rally_id: '7d0c6c1e-3f3a-4c55-9a51-8d1f0e7d2a10', number: 1, game: 1, start_ms: 0, end_ms: 5000,
    serving_side: 'A', score_before: '0-0-2', score_after: '1-0-2', winning_side: 'A', ending: 'winner',
    responsible_player: null, fault_kind: null, marker: null, corrected_by_user: false, ...over,
  };
}
const sheet = (rows: SheetRow[] = []): ScoreSheet => ({
  rules_version: 'PROVISIONAL-UNVERIFIED', unofficial: true, label: 'unofficial scoring (rules not yet verified)', rows,
});
const ready = (s: Partial<TaggingState> = {}): TaggingState => ({
  ...initialTagging({ sheet: sheet(), version: 3, firstServingSide: 'A' }), ...s,
});

describe('nextCall (provisional side-out doubles, optimistic display only)', () => {
  const start: CallState = { servingSide: 'A', call: '0-0-2' };
  it('refuses a call it cannot read instead of guessing', () => {
    expect(nextCall({ servingSide: 'A', call: '0-0' }, 'A')).toBeNull();
    expect(nextCall({ servingSide: 'A', call: 'x-0-1' }, 'A')).toBeNull();
  });
  it('the serving side scores when it wins', () => {
    expect(nextCall(start, 'A')).toEqual({ servingSide: 'A', call: '1-0-2' });
  });
  it('0-0-2: losing the first rally is a side-out', () => {
    expect(nextCall(start, 'B')).toEqual({ servingSide: 'B', call: '0-0-1' });
  });
  it('server 1 losing passes to server 2 on the same side', () => {
    expect(nextCall({ servingSide: 'B', call: '3-5-1' }, 'A')).toEqual({ servingSide: 'B', call: '3-5-2' });
  });
  it('a replay changes nothing', () => {
    expect(nextCall({ servingSide: 'B', call: '3-5-1' }, null)).toEqual({ servingSide: 'B', call: '3-5-1' });
  });
});

describe('taggingReducer', () => {
  it('1. "end" before "start" is ignored', () => {
    const s = taggingReducer(ready(), { type: 'mark_end', ms: 4000 });
    expect(s.draft.end_ms).toBeUndefined();
    expect(s.notice).toBe('Mark the rally start first.');
  });

  it('an end at or before the start is ignored', () => {
    let s = taggingReducer(ready(), { type: 'mark_start', ms: 4000 });
    s = taggingReducer(s, { type: 'mark_end', ms: 4000 });
    expect(s.draft.end_ms).toBeUndefined();
    expect(s.notice).toBe('The rally end must be after its start.');
  });

  it('a start before the end of the last tagged rally is refused (I5, no overlap)', () => {
    const s = taggingReducer(ready({ sheet: sheet([row({ end_ms: 9000 })]) }), { type: 'mark_start', ms: 8000 });
    expect(s.draft.start_ms).toBeUndefined();
    expect(s.notice).toBe('This rally starts before the end of rally 1. Play on to the next rally, then mark its start.');
  });

  it('times are whole milliseconds', () => {
    const s = taggingReducer(ready(), { type: 'mark_start', ms: 1234.7 });
    expect(s.draft.start_ms).toBe(1234);
  });

  it('cannot submit without start, end, winner side and ending', () => {
    let s = taggingReducer(ready(), { type: 'mark_start', ms: 0 });
    s = taggingReducer(s, { type: 'choose_ending', ending: 'winner' });
    expect(s.pending).toBeNull();
    expect(s.notice).toBe('Mark the rally end first.');
    s = taggingReducer(s, { type: 'mark_end', ms: 5000 });
    s = taggingReducer(s, { type: 'choose_ending', ending: 'winner' });
    expect(s.pending).toBeNull();
    expect(s.notice).toBe('Choose which side won the rally first.');
  });

  it('choosing the ending submits the tag with an optimistic score', () => {
    let s = taggingReducer(ready(), { type: 'mark_start', ms: 0 });
    s = taggingReducer(s, { type: 'mark_end', ms: 5000 });
    s = taggingReducer(s, { type: 'choose_winner', side: 'B' });
    s = taggingReducer(s, { type: 'choose_player', slot: 'A1' });
    s = taggingReducer(s, { type: 'choose_ending', ending: 'unforced_error' });
    expect(s.pending).toEqual({
      tag: { start_ms: 0, end_ms: 5000, winning_side: 'B', ending: 'unforced_error', responsible_player: 'A1', fault_kind: null },
      number: 1,
      optimisticCall: '0-0-1',
      baseVersion: 3,
    });
    expect(s.draft).toEqual({});
  });

  it('a replay needs no winner side and keeps the score', () => {
    let s = ready({ sheet: sheet([row({ end_ms: 5000, score_after: '1-0-2', serving_side: 'A', winning_side: 'A' })]) });
    s = taggingReducer(s, { type: 'mark_start', ms: 6000 });
    s = taggingReducer(s, { type: 'mark_end', ms: 9000 });
    s = taggingReducer(s, { type: 'choose_ending', ending: 'replay' });
    expect(s.pending?.tag.winning_side).toBeNull();
    expect(s.pending?.optimisticCall).toBe('1-0-2');
    expect(s.pending?.number).toBe(2);
  });

  it('a responsible player on the wrong side is refused before sending (I6)', () => {
    let s = taggingReducer(ready(), { type: 'mark_start', ms: 0 });
    s = taggingReducer(s, { type: 'mark_end', ms: 5000 });
    s = taggingReducer(s, { type: 'choose_winner', side: 'A' });
    s = taggingReducer(s, { type: 'choose_player', slot: 'A2' });
    s = taggingReducer(s, { type: 'choose_ending', ending: 'unforced_error' });
    expect(s.pending).toBeNull();
    expect(s.notice).toBe('The player who made the error must be on the side that lost the rally.');
    s = taggingReducer(s, { type: 'choose_ending', ending: 'winner' });
    expect(s.pending?.tag.responsible_player).toBe('A2');
  });

  it('2. the optimistic score rolls back on a server error, and the draft is restored', () => {
    let s = taggingReducer(ready(), { type: 'mark_start', ms: 0 });
    s = taggingReducer(s, { type: 'mark_end', ms: 5000 });
    s = taggingReducer(s, { type: 'choose_winner', side: 'A' });
    s = taggingReducer(s, { type: 'choose_ending', ending: 'winner' });
    expect(s.pending?.optimisticCall).toBe('1-0-2');
    s = taggingReducer(s, { type: 'failed', message: 'The rally was not saved. Try again.' });
    expect(s.pending).toBeNull();
    expect(s.sheet.rows).toHaveLength(0);
    expect(s.version).toBe(3);
    expect(s.draft).toEqual({ start_ms: 0, end_ms: 5000, winning_side: 'A' });
    expect(s.notice).toBe('The rally was not saved. Try again.');
  });

  it('the server sheet replaces the optimistic score when confirmed', () => {
    let s = taggingReducer(ready(), { type: 'mark_start', ms: 0 });
    s = taggingReducer(s, { type: 'mark_end', ms: 5000 });
    s = taggingReducer(s, { type: 'choose_winner', side: 'A' });
    s = taggingReducer(s, { type: 'choose_ending', ending: 'winner' });
    s = taggingReducer(s, { type: 'confirmed', sheet: sheet([row()]), version: 4 });
    expect(s.pending).toBeNull();
    expect(s.version).toBe(4);
    expect(s.sheet.rows).toHaveLength(1);
    expect(s.notice).toBeNull();
  });

  it('a stale version takes the latest sheet and says the match changed', () => {
    let s = taggingReducer(ready(), { type: 'mark_start', ms: 0 });
    s = taggingReducer(s, { type: 'mark_end', ms: 5000 });
    s = taggingReducer(s, { type: 'choose_winner', side: 'A' });
    s = taggingReducer(s, { type: 'choose_ending', ending: 'winner' });
    s = taggingReducer(s, { type: 'stale', sheet: sheet([row()]), version: 9 });
    expect(s.pending).toBeNull();
    expect(s.version).toBe(9);
    expect(s.sheet.rows).toHaveLength(1);
    expect(s.notice).toBe('This match was changed on another device. The latest score is shown; your rally was not saved.');
  });

  it('ignores a second submit while one is pending', () => {
    let s = taggingReducer(ready(), { type: 'mark_start', ms: 0 });
    s = taggingReducer(s, { type: 'mark_end', ms: 5000 });
    s = taggingReducer(s, { type: 'choose_winner', side: 'A' });
    s = taggingReducer(s, { type: 'choose_ending', ending: 'winner' });
    const pending = s.pending;
    s = taggingReducer(s, { type: 'mark_start', ms: 6000 });
    expect(s.pending).toBe(pending);
  });

  it('the current call follows the last scored row of the current game', () => {
    const s = ready({ sheet: sheet([row(), row({ number: 2, start_ms: 6000, end_ms: 9000, serving_side: 'A', score_before: '1-0-2', score_after: '1-0-2', winning_side: null, ending: 'replay' })]) });
    expect(taggingReducer(s, { type: 'mark_start', ms: 9500 }).draft.start_ms).toBe(9500);
  });
});

describe('taggingReducer clear (ST-028a, Esc)', () => {
  it('clears the marks but never a pending tag', () => {
    let s = taggingReducer(ready(), { type: 'mark_start', ms: 0 });
    s = taggingReducer(s, { type: 'clear' });
    expect(s.draft).toEqual({});
    s = taggingReducer(s, { type: 'mark_start', ms: 0 });
    s = taggingReducer(s, { type: 'mark_end', ms: 10 });
    s = taggingReducer(s, { type: 'choose_winner', side: 'A' });
    s = taggingReducer(s, { type: 'choose_ending', ending: 'winner' });
    expect(taggingReducer(s, { type: 'clear' }).pending).not.toBeNull();
  });
});
