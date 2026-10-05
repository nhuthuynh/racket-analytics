// ST-032 FE slice 2: a rally that a correction pushed past the end of a game is kept and marked
// "needs your decision"; the player moves it to the next game or removes it (FR-053 (a),
// provisional, @needs-verification). Negative cases first: a refused decision changes nothing;
// tagging while decisions are open says where to go.
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { ScoreSheetView, type SheetApi } from '@/components/score-sheet/ScoreSheetView';
import { ApiError } from '@/lib/api/client';
import type { Match } from '@/lib/api/types';
import { tagFailureMessage } from '@/lib/tagging/messages';
import type { ScoreSheet, SheetRow } from '@/lib/tagging/types';

const ID = '0b8f6c1e-3f3a-4c55-9a51-8d1f0e7d2a10';
const rid = (n: number) => `7d0c6c1e-3f3a-4c55-9a51-8d1f0e7d2a${String(n).padStart(2, '0')}`;
const match: Match = {
  id: ID, title: 'Saturday doubles', format: 'doubles', status: 'video_received', media: null,
  created_at: 'x', updated_at: 'x', upload: null, rejection: null, participants: [],
};
const row = (n: number, over: Partial<SheetRow> = {}): SheetRow => ({
  rally_id: rid(n), number: n, game: 1, start_ms: n * 1000, end_ms: n * 1000 + 500, serving_side: 'A',
  score_before: '10-0-2', score_after: '11-0-2', winning_side: 'A', ending: 'winner', responsible_player: null,
  fault_kind: null, marker: null, corrected_by_user: false, ...over,
});
const conflict = (n: number) => row(n, { marker: 'needs_decision', serving_side: null, score_before: null, score_after: null });
const sheet = (rows: SheetRow[]): ScoreSheet => ({
  rules_version: 'PROVISIONAL-UNVERIFIED', unofficial: true, label: 'unofficial scoring (rules not yet verified)',
  rows, games: [{ number: 1, first_serving_side: 'A', winner: 'A' }], match_winner: null,
});

function setup(initial: ScoreSheet) {
  const api = {
    undo: vi.fn(), corrections: vi.fn().mockResolvedValue([]), correctRally: vi.fn(), getScoreSheet: vi.fn(),
    rallyMedia: vi.fn(), resolveRally: vi.fn<NonNullable<SheetApi['resolveRally']>>(),
  };
  render(<ScoreSheetView match={match} initialSheet={initial} initialVersion={3} api={api as unknown as SheetApi} />);
  return api;
}

describe('needs your decision (ST-032)', () => {
  it('only conflict rows offer a decision', () => {
    setup(sheet([row(11), conflict(12)]));
    expect(within(screen.getByRole('row', { name: /Rally 11/ })).queryByRole('button', { name: /Move rally/ })).toBeNull();
    expect(within(screen.getByRole('row', { name: /Rally 12/ })).getByRole('button', { name: 'Move rally 12 to the next game' })).toBeVisible();
    expect(within(screen.getByRole('row', { name: /Rally 12/ })).getByRole('button', { name: 'Remove rally 12' })).toBeVisible();
  });

  it('a refused decision says why and changes nothing', async () => {
    const api = setup(sheet([row(11), conflict(12)]));
    api.resolveRally.mockRejectedValueOnce(new ApiError(409, 'conflict'));
    await userEvent.click(screen.getByRole('button', { name: 'Remove rally 12' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Decision failed. Try again.');
    expect(screen.getByText('needs your decision')).toBeVisible();
  });

  it('moving sends the decision with If-Match and shows the new sheet', async () => {
    const api = setup(sheet([row(11), conflict(12)]));
    api.resolveRally.mockResolvedValueOnce({ version: 4, sheet: sheet([row(11), row(12, { game: 2, score_before: '0-0-2', score_after: '1-0-2' })]) });
    await userEvent.click(screen.getByRole('button', { name: 'Move rally 12 to the next game' }));
    expect(api.resolveRally).toHaveBeenCalledWith(ID, 3, rid(12), 'move_to_next_game');
    expect(await screen.findByText('Rally 12 moved to the next game.')).toBeVisible();
    expect(screen.queryByText('needs your decision')).toBeNull();
  });

  it('removing sends "withdraw"', async () => {
    const api = setup(sheet([row(11), conflict(12)]));
    api.resolveRally.mockResolvedValueOnce({ version: 4, sheet: sheet([row(11)]) });
    await userEvent.click(screen.getByRole('button', { name: 'Remove rally 12' }));
    expect(api.resolveRally).toHaveBeenCalledWith(ID, 3, rid(12), 'withdraw');
    expect(await screen.findByText('Rally 12 removed. It stays in the correction history.')).toBeVisible();
  });
});

describe('tag refusals from open decisions and game order', () => {
  it('names the way out', () => {
    expect(tagFailureMessage(new ApiError(409, 'decision_needed'))).toBe('Some rallies need your decision first. Open the score sheet to decide.');
    expect(tagFailureMessage(new ApiError(409, 'game_not_started'))).toBe('Start the game first: choose who serves first.');
  });
});
