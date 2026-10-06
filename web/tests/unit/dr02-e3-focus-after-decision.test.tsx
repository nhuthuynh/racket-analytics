// DR-02 R2-5 / flows-sprint-02 §12 E-3 (FE follow-up of DR-02; flows §5 "After any change"):
// after a decision removes the row's controls, focus goes to the next row's first action, or to
// "Undo last change" when there is no next row; it never drops to the page (SC 2.4.3, 2.4.7).
// A refused decision keeps focus on the control used. Red first, negative case first.
import { render, screen } from '@testing-library/react';
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
  rows, games: [{ number: 1, first_serving_side: 'A', winner: 'A' }, { number: 2, first_serving_side: 'B', winner: null }],
  match_winner: null,
});

function setup(initial: ScoreSheet) {
  const api = {
    undo: vi.fn(), corrections: vi.fn().mockResolvedValue([]), correctRally: vi.fn(), getScoreSheet: vi.fn(),
    rallyMedia: vi.fn(), resolveRally: vi.fn<NonNullable<SheetApi['resolveRally']>>(),
  };
  render(<ScoreSheetView match={match} initialSheet={initial} initialVersion={3} api={api as unknown as SheetApi} />);
  return api;
}

describe('DR-02 E-3: focus after a decision', () => {
  it('a refused decision keeps focus on the control used', async () => {
    const api = setup(sheet([row(11), conflict(12)]));
    api.resolveRally.mockRejectedValueOnce(new ApiError(409, 'conflict'));
    const remove = screen.getByRole('button', { name: 'Remove rally 12' });
    await userEvent.click(remove);
    await screen.findByRole('alert');
    expect(remove).toHaveFocus();
  });

  it('removing a rally moves focus to the next row\'s first action', async () => {
    const api = setup(sheet([row(11), conflict(12), conflict(13)]));
    api.resolveRally.mockResolvedValueOnce({ version: 4, sheet: sheet([row(11), conflict(13)]) });
    await userEvent.click(screen.getByRole('button', { name: 'Remove rally 12' }));
    await screen.findByText('Rally 12 removed. It stays in the correction history.');
    expect(screen.getByRole('button', { name: 'Move rally 13 to the next game' })).toHaveFocus();
  });

  it('after a removal the server renumbers; focus follows the rally that came next, not the number', async () => {
    const api = setup(sheet([row(11), conflict(12), conflict(13), conflict(14)]));
    // Rally 12 removed: the old 13 is now "Rally 12", the old 14 "Rally 13" (same rally ids).
    api.resolveRally.mockResolvedValueOnce({
      version: 4,
      sheet: sheet([row(11), { ...conflict(13), number: 12 }, { ...conflict(14), number: 13 }]),
    });
    await userEvent.click(screen.getByRole('button', { name: 'Remove rally 12' }));
    await screen.findByText('Rally 12 removed. It stays in the correction history.');
    expect(screen.getByRole('button', { name: 'Remove rally 12' })).toHaveFocus();
  });

  it('moving the last rally to the next game moves focus to "Undo last change" when no row follows', async () => {
    const api = setup(sheet([row(11), conflict(12)]));
    api.resolveRally.mockResolvedValueOnce({ version: 4, sheet: sheet([row(11), row(12, { game: 2 })]) });
    await userEvent.click(screen.getByRole('button', { name: 'Move rally 12 to the next game' }));
    await screen.findByText('Rally 12 moved to the next game.');
    expect(screen.getByRole('button', { name: 'Undo last change' })).toHaveFocus();
  });
});
