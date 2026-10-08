// PD-R3S2-02 (minor, Sprint 2 review round 3 carry-over; sprint-03 C3-10): H-01 "Reload the
// history" that fails again gave no feedback: the same text stayed, so the press looked ignored.
// Now the button says it is loading while it works, and a failed reload says so in an alert with
// the try count, so a screen-reader user hears it too. Red first, negative case first.
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { ScoreSheetView, type SheetApi } from '@/components/score-sheet/ScoreSheetView';
import type { Match } from '@/lib/api/types';
import type { HistoryItem, ScoreSheet } from '@/lib/tagging/types';

const ID = '0b8f6c1e-3f3a-4c55-9a51-8d1f0e7d2a10';
const match: Match = {
  id: ID, title: 'Saturday doubles', format: 'doubles', status: 'video_received', media: null,
  created_at: 'x', updated_at: 'x', upload: null, rejection: null, participants: [],
};
const sheet: ScoreSheet = {
  rules_version: 'PROVISIONAL-UNVERIFIED', unofficial: true, label: 'unofficial scoring (rules not yet verified)',
  rows: [], games: [], match_winner: null,
};

function setup(corrections: SheetApi['corrections']) {
  const api = { undo: vi.fn(), corrections, correctRally: vi.fn(), getScoreSheet: vi.fn(), rallyMedia: vi.fn() };
  render(<ScoreSheetView match={match} initialSheet={sheet} initialVersion={1} api={api as unknown as SheetApi} />);
}

describe('PD-R3S2-02: H-01 failed reload gives feedback', () => {
  it('a reload that fails again says so in an alert', async () => {
    setup(vi.fn<SheetApi['corrections']>().mockRejectedValue(new Error('down')));
    await userEvent.click(await screen.findByRole('button', { name: 'Reload the history' }));
    const section = screen.getByRole('region', { name: 'Correction history' });
    expect(await within(section).findByRole('alert')).toHaveTextContent(
      'The history still could not be loaded (tried 2 times). Check your connection, then reload it again.',
    );
    await userEvent.click(screen.getByRole('button', { name: 'Reload the history' }));
    expect(await within(section).findByRole('alert')).toHaveTextContent('(tried 3 times)');
  });

  it('while reloading the button says it is busy', async () => {
    let release: (v: HistoryItem[]) => void = () => {};
    const corrections = vi
      .fn<SheetApi['corrections']>()
      .mockRejectedValueOnce(new Error('down'))
      .mockImplementationOnce(() => new Promise<HistoryItem[]>((r) => { release = r; }));
    setup(corrections);
    const button = await screen.findByRole('button', { name: 'Reload the history' });
    await userEvent.click(button);
    expect(button).toHaveAttribute('aria-busy', 'true');
    expect(button).toHaveTextContent('Reloading the history…');
    release([]);
    expect(await screen.findByText('No changes yet.', { exact: false })).toBeVisible();
  });

  it('a reload that works shows the history and no alert', async () => {
    setup(vi.fn<SheetApi['corrections']>().mockRejectedValueOnce(new Error('down')).mockResolvedValueOnce([]));
    await userEvent.click(await screen.findByRole('button', { name: 'Reload the history' }));
    const section = screen.getByRole('region', { name: 'Correction history' });
    expect(within(section).queryByRole('alert')).toBeNull();
    expect(within(section).queryByRole('button', { name: 'Reload the history' })).toBeNull();
  });
});
