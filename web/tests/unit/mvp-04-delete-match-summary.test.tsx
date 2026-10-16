// MVP-04 X-01 "Delete this match?" names the match once (ST-050, FR-006; flows D-2;
// tests/features/mvp_04_delete_match_summary.feature). The default title is
// "{Doubles|Singles} · {d Mon yyyy}" (backend default_title), so the dialog must not append the
// date again. Negative cases first: a default title, including September ("Sep" from the
// server, "Sept" from Intl en-GB), never shows the date twice. Then: a title of the player's own
// still gets the date; the component also behaves this way inside M-02 (MatchDetail).
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { DeleteMatch, matchSummary } from '@/components/DeleteMatch';
import { MatchDetail } from '@/components/MatchDetail';
import type { Match } from '@/lib/api/types';

const match: Match = {
  id: '0b8f6c1e-3f3a-4c55-9a51-8d1f0e7d2a10', title: 'Doubles · 11 Oct 2026', format: 'doubles',
  status: 'video_received', media: null, created_at: '2026-10-11T09:00:00Z', updated_at: 'x',
  played_on: '2026-10-11', upload: null, rejection: null, participants: [],
};

async function openDialog(m: Match) {
  render(<DeleteMatch match={m} api={{ deleteMatch: vi.fn(async () => {}) }} navigate={vi.fn()} />);
  await userEvent.click(screen.getByRole('button', { name: 'Delete match' }));
  return screen.getByRole('dialog', { name: 'Delete this match?' });
}

const occurrences = (text: string, part: string) => text.split(part).length - 1;

describe('MVP-04 matchSummary (unit)', () => {
  it('does not repeat the date a default title already carries', () => {
    expect(matchSummary('Doubles · 11 Oct 2026', '2026-10-11')).toBe('Doubles · 11 Oct 2026');
  });

  it('does not repeat a September date written "Sep" by the server', () => {
    expect(matchSummary('Singles · 5 Sep 2026', '2026-09-05')).toBe('Singles · 5 Sep 2026');
  });

  it('adds the date to a title of the player\'s own', () => {
    expect(matchSummary('Saturday doubles', '2026-10-03')).toBe('Saturday doubles · 3 Oct 2026');
  });

  it('adds the date when the title names another day', () => {
    expect(matchSummary('Doubles · 4 Oct 2026', '2026-10-11')).toBe('Doubles · 4 Oct 2026 · 11 Oct 2026');
  });

  // Review round 1 (PE-MVP04-R1-1, QA-MVP04-01): "11 Oct 2026" ends with "1 Oct 2026", so the
  // check must stop at a whole day number, or the irreversible delete names the wrong day.
  it('adds the date when the title names a day whose last digit is the day played', () => {
    expect(matchSummary('Rematch of 11 Oct 2026', '2026-10-01')).toBe('Rematch of 11 Oct 2026 · 1 Oct 2026');
    expect(matchSummary('Doubles · 21 Oct 2026', '2026-10-01')).toBe('Doubles · 21 Oct 2026 · 1 Oct 2026');
    expect(matchSummary('Final 12 Sep 2026', '2026-09-02')).toBe('Final 12 Sep 2026 · 2 Sept 2026');
    expect(matchSummary('Doubles · 15 Sep 2026', '2026-09-05')).toBe('Doubles · 15 Sep 2026 · 5 Sept 2026');
    expect(matchSummary('Doubles · 25 Sept 2026', '2026-09-05')).toBe('Doubles · 25 Sept 2026 · 5 Sept 2026');
  });

  it('shows a title that is only the date played alone', () => {
    expect(matchSummary('5 Sep 2026', '2026-09-05')).toBe('5 Sep 2026');
  });

  it('shows the title alone when there is no valid date', () => {
    expect(matchSummary('Saturday doubles', 'not a date')).toBe('Saturday doubles');
  });
});

describe('MVP-04 X-01 dialog (component)', () => {
  it('shows a default title once, with the date once', async () => {
    const dialog = await openDialog(match);
    expect(within(dialog).getByText('Doubles · 11 Oct 2026', { selector: 'p' })).toBeVisible();
    expect(occurrences(dialog.textContent ?? '', '11 Oct 2026')).toBe(1);
  });

  it('shows a September default title once', async () => {
    const dialog = await openDialog({ ...match, title: 'Singles · 5 Sep 2026', format: 'singles', played_on: '2026-09-05' });
    expect(within(dialog).getByText('Singles · 5 Sep 2026', { selector: 'p' })).toBeVisible();
    expect(dialog).not.toHaveTextContent(/Sept? 2026.*Sept? 2026/);
  });

  it('keeps the date played when the title names a later day ending in the same digit', async () => {
    const dialog = await openDialog({ ...match, title: 'Doubles · 15 Sep 2026', played_on: '2026-09-05' });
    expect(within(dialog).getByText('Doubles · 15 Sep 2026 · 5 Sept 2026', { selector: 'p' })).toBeVisible();
  });

  it('keeps the date after a title of the player\'s own', async () => {
    const dialog = await openDialog({ ...match, title: 'Saturday doubles', played_on: '2026-10-03' });
    expect(within(dialog).getByText('Saturday doubles · 3 Oct 2026', { selector: 'p' })).toBeVisible();
  });
});

describe('MVP-04 M-02 with X-01 (integration of MatchDetail and DeleteMatch)', () => {
  it('the dialog opened from the match page names a default-titled match once', async () => {
    render(<MatchDetail initialMatch={match} api={{ getMatch: vi.fn() }} pollMs={60_000} />);
    await userEvent.click(screen.getByRole('button', { name: 'Delete match' }));
    const dialog = screen.getByRole('dialog', { name: 'Delete this match?' });
    expect(occurrences(dialog.textContent ?? '', '11 Oct 2026')).toBe(1);
  });
});
