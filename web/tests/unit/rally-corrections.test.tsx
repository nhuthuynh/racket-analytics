// ST-032 FE: correct any rally from the score sheet in at most 2 taps or keys (NFR-036d,
// E2E-02-05). Negative cases first: a refused correction leaves the sheet as it was; a replay has
// no winner to switch.
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { ScoreSheetView, type SheetApi } from '@/components/score-sheet/ScoreSheetView';
import { ApiError } from '@/lib/api/client';
import type { Match } from '@/lib/api/types';
import type { ScoreSheet, SheetRow } from '@/lib/tagging/types';

const ID = '0b8f6c1e-3f3a-4c55-9a51-8d1f0e7d2a10';
const rid = (n: number) => `7d0c6c1e-3f3a-4c55-9a51-8d1f0e7d2a${String(n).padStart(2, '0')}`;
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

function setup(initial: ScoreSheet) {
  const api = {
    undo: vi.fn(), corrections: vi.fn().mockResolvedValue([]), correctRally: vi.fn<SheetApi['correctRally']>(),
    getScoreSheet: vi.fn<SheetApi['getScoreSheet']>(), rallyMedia: vi.fn(),
  };
  render(<ScoreSheetView match={match} initialSheet={initial} initialVersion={7} api={api as unknown as SheetApi} />);
  return api;
}

describe('rally corrections on the score sheet (ST-032)', () => {
  it('a refused correction says why and leaves the sheet as it was', async () => {
    const api = setup(sheet([row(1), row(2)]));
    api.correctRally.mockRejectedValueOnce(new ApiError(422, 'invalid_outcome'));
    await userEvent.click(screen.getByRole('button', { name: 'Rally 2: change the winner to the other side' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Correction was refused');
    expect(screen.queryByText('corrected by you')).toBeNull();
  });

  it('a replay has no winner to switch', () => {
    setup(sheet([row(1, { ending: 'replay', winning_side: null })]));
    expect(screen.queryByRole('button', { name: /Rally 1: change the winner/ })).toBeNull();
  });

  it('one tap switches the winner; later rallies come back re-scored from the server', async () => {
    const api = setup(sheet([row(1), row(2), row(3)]));
    api.correctRally.mockResolvedValueOnce({
      version: 8,
      sheet: sheet([row(1), row(2, { winning_side: 'B', score_after: '0-0-1', corrected_by_user: true }), row(3, { score_before: '0-0-1', score_after: '0-0-2' })]),
    });
    await userEvent.click(screen.getByRole('button', { name: 'Rally 2: change the winner to the other side' }));
    expect(api.correctRally).toHaveBeenCalledWith(ID, 7, rid(2), 'winning_side', 'B');
    const r2 = await screen.findByRole('row', { name: /Rally 2/ });
    expect(within(r2).getByText('corrected by you')).toBeVisible();
    expect(within(screen.getByRole('row', { name: /Rally 3/ })).getAllByRole('cell')[3]).toHaveTextContent('0-0-2');
    expect(screen.getByRole('status')).toHaveTextContent('Rally 2 corrected. The score sheet is up to date.');
  });

  it('PD-S2R1-02: moving through the ending or player options with the keyboard saves nothing', async () => {
    const api = setup(sheet([row(1, { ending: 'unforced_error', winning_side: 'B' })]));
    expect(screen.queryByRole('combobox')).toBeNull();
    const u = userEvent.setup();
    await u.click(screen.getByRole('button', { name: 'Change ending, rally 1' }));
    await u.keyboard('{Tab}{ArrowDown}{ArrowDown}{Tab}{ArrowUp}');
    await u.click(screen.getByRole('button', { name: 'Change player, rally 1' }));
    await u.keyboard('{Tab}{ArrowDown}{Tab}');
    expect(api.correctRally).not.toHaveBeenCalled();
  });

  it('PD-S2R1-01: switching the winner of a rally with a tagged player also clears the player, in one command', async () => {
    const api = setup(sheet([row(1, { responsible_player: 'A1' })]));
    api.correctRally.mockResolvedValueOnce({ version: 8, sheet: sheet([row(1, { winning_side: 'B', corrected_by_user: true })]) });
    await userEvent.click(screen.getByRole('button', { name: 'Rally 1: change the winner to the other side' }));
    expect(api.correctRally).toHaveBeenCalledTimes(1);
    expect(api.correctRally).toHaveBeenCalledWith(ID, 7, rid(1), 'outcome', {
      ending: 'winner', winning_side: 'B', responsible_player: null, fault_kind: null,
    });
    expect(await screen.findByRole('status')).toHaveTextContent('Rally 1 corrected. The score sheet is up to date.');
  });

  it('two taps change the ending: open "Change ending", choose', async () => {
    const api = setup(sheet([row(1)]));
    api.correctRally.mockResolvedValueOnce({ version: 8, sheet: sheet([row(1, { ending: 'forced_error', winning_side: 'A', corrected_by_user: true })]) });
    const u = userEvent.setup();
    const toggle = screen.getByRole('button', { name: 'Change ending, rally 1' });
    expect(toggle).toHaveAttribute('aria-expanded', 'false');
    await u.click(toggle);
    expect(toggle).toHaveAttribute('aria-expanded', 'true');
    const group = screen.getByRole('group', { name: 'Rally 1 ending' });
    expect(within(group).getByRole('button', { name: 'Winner' })).toHaveAttribute('aria-pressed', 'true');
    await u.click(within(group).getByRole('button', { name: 'Unforced error' }));
    expect(api.correctRally).toHaveBeenCalledWith(ID, 7, rid(1), 'ending', 'unforced_error');
    expect(screen.queryByRole('group', { name: 'Rally 1 ending' })).toBeNull();
    expect(screen.getByRole('button', { name: 'Change ending, rally 1' })).toHaveFocus();
  });

  it('an ending that no longer fits the tagged player clears the player in the same command', async () => {
    const api = setup(sheet([row(1, { responsible_player: 'A1' })]));
    api.correctRally.mockResolvedValueOnce({ version: 8, sheet: sheet([row(1, { ending: 'forced_error', corrected_by_user: true })]) });
    const u = userEvent.setup();
    await u.click(screen.getByRole('button', { name: 'Change ending, rally 1' }));
    await u.click(within(screen.getByRole('group', { name: 'Rally 1 ending' })).getByRole('button', { name: 'Forced error' }));
    expect(api.correctRally).toHaveBeenCalledWith(ID, 7, rid(1), 'outcome', {
      ending: 'forced_error', winning_side: 'A', responsible_player: null, fault_kind: null,
    });
  });

  it('a scored rally becomes a replay in one command (no winner, no player)', async () => {
    const api = setup(sheet([row(1, { responsible_player: 'A1' })]));
    api.correctRally.mockResolvedValueOnce({ version: 8, sheet: sheet([row(1, { ending: 'replay', winning_side: null, corrected_by_user: true })]) });
    const u = userEvent.setup();
    await u.click(screen.getByRole('button', { name: 'Change ending, rally 1' }));
    await u.click(within(screen.getByRole('group', { name: 'Rally 1 ending' })).getByRole('button', { name: 'Replay' }));
    expect(api.correctRally).toHaveBeenCalledWith(ID, 7, rid(1), 'outcome', {
      ending: 'replay', winning_side: null, responsible_player: null, fault_kind: null,
    });
  });

  it('the player can be set or cleared, and only players who fit the winner and the ending are offered', async () => {
    const api = setup(sheet([row(1, { responsible_player: 'A1' })]));
    api.correctRally.mockResolvedValue({ version: 8, sheet: sheet([row(1)]) });
    const u = userEvent.setup();
    await u.click(screen.getByRole('button', { name: 'Change player, rally 1' }));
    const group = screen.getByRole('group', { name: 'Rally 1 player' });
    expect(within(group).getByRole('button', { name: 'Ivy' })).toHaveAttribute('aria-pressed', 'true');
    expect(within(group).queryByRole('button', { name: 'Carlos' })).toBeNull();
    await u.click(within(group).getByRole('button', { name: 'Not tagged' }));
    expect(api.correctRally).toHaveBeenCalledWith(ID, 7, rid(1), 'responsible_player', null);
  });

  it('choosing the value it already has saves nothing and closes the options', async () => {
    const api = setup(sheet([row(1)]));
    const u = userEvent.setup();
    await u.click(screen.getByRole('button', { name: 'Change ending, rally 1' }));
    await u.click(within(screen.getByRole('group', { name: 'Rally 1 ending' })).getByRole('button', { name: 'Winner' }));
    expect(api.correctRally).not.toHaveBeenCalled();
    expect(screen.queryByRole('group', { name: 'Rally 1 ending' })).toBeNull();
  });

  it('Esc closes the options and returns focus to the button that opened them', async () => {
    setup(sheet([row(1)]));
    const u = userEvent.setup();
    await u.click(screen.getByRole('button', { name: 'Change ending, rally 1' }));
    await u.keyboard('{Tab}{Escape}');
    expect(screen.queryByRole('group', { name: 'Rally 1 ending' })).toBeNull();
    expect(screen.getByRole('button', { name: 'Change ending, rally 1' })).toHaveFocus();
  });
});
