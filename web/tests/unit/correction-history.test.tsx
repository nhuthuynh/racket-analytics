// ST-031 undo and correction history H-01 (FR-052; sprint-02 §7.4). Negative cases first:
// an empty history, nothing to undo, and a failed undo leaves the sheet as it was.
import { act, render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { CorrectionHistory } from '@/components/score-sheet/CorrectionHistory';
import { ScoreSheetView, type SheetApi } from '@/components/score-sheet/ScoreSheetView';
import { ApiError } from '@/lib/api/client';
import type { Match } from '@/lib/api/types';
import type { HistoryItem, ScoreSheet, SheetRow } from '@/lib/tagging/types';

const ID = '0b8f6c1e-3f3a-4c55-9a51-8d1f0e7d2a10';
const rid = (n: number) => `7d0c6c1e-3f3a-4c55-9a51-8d1f0e7d2a${String(n).padStart(2, '0')}`;
const hid = (n: number) => `9d0c6c1e-3f3a-4c55-9a51-8d1f0e7d2a${String(n).padStart(2, '0')}`;
const match: Match = {
  id: ID, title: 'Saturday doubles', format: 'doubles', status: 'video_received', media: null,
  created_at: 'x', updated_at: 'x', upload: null, rejection: null,
  participants: [{ slot: 'A1', nickname: 'Ivy', is_me: true }, { slot: 'B1', nickname: 'Carlos', is_me: false }],
};
const row = (n: number, over: Partial<SheetRow> = {}): SheetRow => ({
  rally_id: rid(n), number: n, game: 1, start_ms: n * 10_000, end_ms: n * 10_000 + 5000, serving_side: 'A',
  score_before: '0-0-2', score_after: '1-0-2', winning_side: 'A', ending: 'winner', responsible_player: null,
  fault_kind: null, marker: null, corrected_by_user: false, ...over,
});
const sheet = (rows: SheetRow[]): ScoreSheet => ({
  rules_version: 'PROVISIONAL-UNVERIFIED', unofficial: true, label: 'unofficial scoring (rules not yet verified)',
  rows, games: [{ number: 1, first_serving_side: 'A', winner: null }], match_winner: null,
});
const change: HistoryItem = {
  id: hid(1), kind: 'correction', rally_id: rid(5), rally_number: 5, field: 'ending', old_value: 'winner',
  new_value: 'forced_error', undoes: null, at: '2026-10-05T10:00:00Z',
};
const undo: HistoryItem = { ...change, id: hid(2), kind: 'undo', field: null, old_value: null, new_value: null, undoes: hid(1) };

describe('CorrectionHistory (H-01)', () => {
  it('says when nothing was changed', () => {
    render(<CorrectionHistory items={[]} match={match} />);
    expect(screen.getByText('No changes yet.')).toBeVisible();
  });

  it('shows the rally, the field, the old and the new value, and the undo of it', () => {
    render(<CorrectionHistory items={[change, undo]} match={match} />);
    const list = screen.getByRole('list', { name: 'Correction history' });
    const items = within(list).getAllByRole('listitem').map((li) => li.textContent);
    expect(items[0]).toContain('Rally 5: ending changed from winner to forced error');
    expect(items[1]).toContain('Undone: Rally 5: ending changed from winner to forced error');
  });

  it('names sides and players in words, and a removed rally', () => {
    render(<CorrectionHistory match={match} items={[
      { ...change, field: 'winning_side', old_value: 'B', new_value: 'A' },
      { ...change, id: hid(3), field: 'responsible_player', old_value: null, new_value: 'B1' },
      { ...change, id: hid(4), kind: 'withdrawal', rally_number: 7, field: null, old_value: null, new_value: null },
    ]} />);
    const items = screen.getAllByRole('listitem').map((li) => li.textContent);
    expect(items[0]).toContain('Rally 5: won by changed from the other side to your side');
    expect(items[1]).toContain('Rally 5: player changed from not tagged to Carlos');
    expect(items[2]).toContain('Rally 7 removed');
  });
});

function setup(initial = sheet([row(1), row(2)]), history: HistoryItem[] | Error = []) {
  const api = {
    undo: vi.fn<SheetApi['undo']>(),
    corrections: history instanceof Error
      ? vi.fn<SheetApi['corrections']>().mockRejectedValue(history)
      : vi.fn<SheetApi['corrections']>().mockResolvedValue(history),
    correctRally: vi.fn<SheetApi['correctRally']>(),
    getScoreSheet: vi.fn<SheetApi['getScoreSheet']>(),
    rallyMedia: vi.fn<SheetApi['rallyMedia']>(),
  };
  render(<ScoreSheetView match={match} initialSheet={initial} initialVersion={4} api={api} />);
  return api;
}

describe('ScoreSheetView undo (ST-031)', () => {
  it('nothing to undo says so and changes nothing', async () => {
    const api = setup();
    api.undo.mockRejectedValueOnce(new ApiError(409, 'nothing_to_undo'));
    await userEvent.click(screen.getByRole('button', { name: 'Undo last change' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('There is nothing to undo.');
    expect(screen.getAllByRole('row', { name: /^Rally \d/ })).toHaveLength(2);
  });

  it('undo replaces the sheet, reloads the history and announces it', async () => {
    const api = setup(sheet([row(1), row(2, { corrected_by_user: true })]), [change]);
    expect(await screen.findByText(/ending changed from winner to forced error/)).toBeVisible();
    api.undo.mockResolvedValueOnce({ version: 5, sheet: sheet([row(1), row(2)]) });
    api.corrections.mockResolvedValueOnce([change, undo]);
    await userEvent.click(screen.getByRole('button', { name: 'Undo last change' }));
    expect(api.undo).toHaveBeenCalledWith(ID, 4);
    expect(await screen.findByText(/^Undone: /)).toBeVisible();
    expect(screen.queryByText('corrected by you')).toBeNull();
    expect(screen.getByRole('status')).toHaveTextContent('Last change undone.');
  });

  it('a history that cannot be loaded says so and can be reloaded; the sheet stays usable', async () => {
    const api = setup(sheet([row(1), row(2)]), new ApiError(500, 'internal_error'));
    expect(await screen.findByText('The correction history could not be loaded.')).toBeVisible();
    expect(screen.getAllByRole('table')).toHaveLength(1);
    api.corrections.mockReset().mockResolvedValue([change]);
    await act(async () => {
      await userEvent.click(screen.getByRole('button', { name: 'Reload the history' }));
    });
    expect(screen.getByText(/ending changed from winner to forced error/)).toBeVisible();
  });
});
