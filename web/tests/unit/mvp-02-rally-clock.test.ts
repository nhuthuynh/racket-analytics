// MVP-02 (FR-050): the rally clock gives "Rally start" and "Rally end" their times. With a video
// that plays, the video's time; when the video cannot play here, the page clock, carried on from
// the end of the last tagged rally so every later mark is accepted. Negative case first.
import { describe, expect, it } from 'vitest';
import { RallyClock } from '@/lib/tagging/clock';
import { initialTagging, taggingReducer, type TaggingState } from '@/lib/tagging/reducer';
import type { ScoreSheet, SheetRow } from '@/lib/tagging/types';

const sheet = (rows: SheetRow[] = []): ScoreSheet => ({
  rules_version: 'PROVISIONAL-UNVERIFIED', unofficial: true, label: 'unofficial', rows,
  games: [{ number: 1, first_serving_side: 'A', winner: null }], match_winner: null,
});
const row = (n: number, start: number, end: number): SheetRow => ({
  rally_id: `r${n}`, number: n, game: 1, start_ms: start, end_ms: end, serving_side: 'A', score_before: '0-0-2',
  score_after: '1-0-2', winning_side: 'A', ending: 'winner', responsible_player: null, fault_kind: null,
  marker: null, corrected_by_user: false,
});

describe('MVP-02 rally clock', () => {
  it('a video that cannot play (stuck at 0) never gives a rally start before the last rally end', () => {
    let page = 1_000;
    const clock = new RallyClock(() => page);
    const lastEnd = 4_000; // rally 1 was tagged earlier
    page = 5_000;
    const start = clock.read({ plays: false, videoMs: 0 }, lastEnd);
    expect(start).toBeGreaterThanOrEqual(lastEnd);
    page = 7_000;
    const end = clock.read({ plays: false, videoMs: 0 }, lastEnd);
    expect(end).toBeGreaterThan(start);
  });

  it('carries on from a last rally end later than the page clock (rallies tagged from the video before)', () => {
    let page = 2_000;
    const clock = new RallyClock(() => page);
    const start = clock.read(null, 600_000);
    expect(start).toBe(600_000);
    page = 3_500;
    expect(clock.read(null, 600_000)).toBe(601_500);
  });

  it('three rallies tagged without a playable video are all accepted by the tagging reducer', () => {
    let page = 0;
    const clock = new RallyClock(() => page);
    let state: TaggingState = initialTagging({ sheet: sheet(), version: 1, firstServingSide: 'A', game: 1 });
    const rows: SheetRow[] = [];
    for (let n = 1; n <= 3; n += 1) {
      const lastEnd = rows.length ? rows[rows.length - 1]!.end_ms : null;
      page += 1_000;
      state = taggingReducer(state, { type: 'mark_start', ms: clock.read({ plays: false, videoMs: 0 }, lastEnd) });
      page += 3_000;
      state = taggingReducer(state, { type: 'mark_end', ms: clock.read({ plays: false, videoMs: 0 }, lastEnd) });
      expect(state.notice).toBeNull();
      const { start_ms, end_ms } = state.draft;
      rows.push(row(n, start_ms!, end_ms!));
      state = taggingReducer(state, { type: 'confirmed', sheet: sheet([...rows]), version: n + 1 });
    }
    expect(rows.map((r) => r.number)).toEqual([1, 2, 3]);
    expect(rows[1]!.start_ms).toBeGreaterThanOrEqual(rows[0]!.end_ms);
    expect(rows[2]!.start_ms).toBeGreaterThanOrEqual(rows[1]!.end_ms);
  });

  it('a video that plays gives its own time, whatever the page clock says', () => {
    const clock = new RallyClock(() => 99_999);
    expect(clock.read({ plays: true, videoMs: 12_345.9 }, 4_000)).toBe(12_345);
  });
});
