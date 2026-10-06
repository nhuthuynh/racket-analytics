// ST-031 undo on the tagging screen: "Undo last change" button and the Z key (FR-052, FR-UX-61). Negative
// case first: nothing to undo leaves the score as it was.
import { act, render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { QuickTag, type QuickTagApi } from '@/components/tagging/QuickTag';
import { ApiError } from '@/lib/api/client';
import type { Match } from '@/lib/api/types';
import type { ScoreSheet, SheetRow } from '@/lib/tagging/types';

const ID = '0b8f6c1e-3f3a-4c55-9a51-8d1f0e7d2a10';
const match: Match = {
  id: ID, title: 'Saturday doubles', format: 'doubles', status: 'video_received', media: null,
  created_at: 'x', updated_at: 'x', upload: null, rejection: null,
  participants: [{ slot: 'A1', nickname: 'Ivy', is_me: true }, { slot: 'B1', nickname: 'Carlos', is_me: false }],
};
const row1: SheetRow = {
  rally_id: '7d0c6c1e-3f3a-4c55-9a51-8d1f0e7d2a10', number: 1, game: 1, start_ms: 1000, end_ms: 5000, serving_side: 'A',
  score_before: '0-0-2', score_after: '1-0-2', winning_side: 'A', ending: 'winner', responsible_player: null, fault_kind: null,
  marker: null, corrected_by_user: false,
};
const sheet = (rows: SheetRow[]): ScoreSheet => ({
  rules_version: 'PROVISIONAL-UNVERIFIED', unofficial: true, label: 'unofficial scoring (rules not yet verified)',
  rows, games: [{ number: 1, first_serving_side: 'A', winner: null }], match_winner: null,
});

function setup() {
  const api = { tagRally: vi.fn(), startGame: vi.fn(), getScoreSheet: vi.fn(), undo: vi.fn<QuickTagApi['undo']>() };
  render(<QuickTag match={match} initialSheet={sheet([row1])} initialVersion={2} api={api as unknown as QuickTagApi} clock={() => 0} videoSrc={null} />);
  return api;
}

describe('QuickTag undo (ST-031)', () => {
  it('nothing to undo says so and keeps the score', async () => {
    const api = setup();
    api.undo.mockRejectedValueOnce(new ApiError(409, 'nothing_to_undo'));
    await userEvent.click(screen.getByRole('button', { name: 'Undo last change' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('There is nothing to undo.');
    expect(within(screen.getByRole('group', { name: 'Score' })).getByText('1-0-2')).toBeVisible();
  });

  it('Z undoes the last tag: the server sheet comes back and it is announced', async () => {
    const api = setup();
    api.undo.mockResolvedValueOnce({ version: 3, sheet: sheet([]) });
    await act(async () => {
      await userEvent.keyboard('z');
    });
    expect(api.undo).toHaveBeenCalledWith(ID, 2);
    expect(within(screen.getByRole('group', { name: 'Score' })).getByText('0-0-2')).toBeVisible();
    expect(screen.getByRole('status')).toHaveTextContent('Last change undone.');
  });
});
