// ST-030 score sheet S-01 (FR-049, FR-055; DES FR-UX-70; sprint-02 §7.3). Negative/edge cases
// first: the empty sheet, the unofficial label always shown, conflict rows without a score,
// markers in text and not colour alone.
import { render, screen, within } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { ScoreSheetTable } from '@/components/score-sheet/ScoreSheetTable';
import type { Match } from '@/lib/api/types';
import type { ScoreSheet, SheetRow } from '@/lib/tagging/types';
import { formatClock } from '@/lib/tagging/view';

const ID = '0b8f6c1e-3f3a-4c55-9a51-8d1f0e7d2a10';
const match: Match = {
  id: ID, title: 'Saturday doubles', format: 'doubles', status: 'video_received', media: null,
  created_at: 'x', updated_at: 'x', upload: null, rejection: null,
  participants: [
    { slot: 'A1', nickname: 'Ivy', is_me: true }, { slot: 'A2', nickname: 'Dana', is_me: false },
    { slot: 'B1', nickname: 'Carlos', is_me: false }, { slot: 'B2', nickname: 'Bo', is_me: false },
  ],
};
const LABEL = 'unofficial scoring (rules not yet verified)';
const row = (n: number, over: Partial<SheetRow> = {}): SheetRow => ({
  rally_id: `7d0c6c1e-3f3a-4c55-9a51-8d1f0e7d2a${String(n).padStart(2, '0')}`, number: n, game: 1,
  start_ms: 872_000, end_ms: 880_000, serving_side: 'A', score_before: '4-6-1', score_after: '5-6-1',
  winning_side: 'A', ending: 'winner', responsible_player: 'A1', fault_kind: null, marker: null, corrected_by_user: false, ...over,
});
const sheet = (rows: SheetRow[], over: Partial<ScoreSheet> = {}): ScoreSheet => ({
  rules_version: 'PROVISIONAL-UNVERIFIED', unofficial: true, label: LABEL, rows,
  games: [{ number: 1, first_serving_side: 'A', winner: null }], match_winner: null, ...over,
});

describe('formatClock', () => {
  it('floors to the second: the video never starts after the rally', () => {
    expect(formatClock(872_999)).toBe('14:32');
    expect(formatClock(0)).toBe('0:00');
    expect(formatClock(3_725_000)).toBe('1:02:05');
  });
});

describe('ScoreSheetTable (S-01)', () => {
  it('an empty sheet says so, still carries the label, and links to tagging', () => {
    render(<ScoreSheetTable match={match} sheet={sheet([])} />);
    expect(screen.getByText(LABEL)).toBeVisible();
    expect(screen.getByText('No rallies tagged yet.')).toBeVisible();
    expect(screen.getByRole('link', { name: 'Tag rallies' })).toHaveAttribute('href', `/matches/${ID}/tag`);
    expect(screen.queryByRole('table')).toBeNull();
  });

  it('shows the label whenever the server says unofficial, even if it sends another label text', () => {
    render(<ScoreSheetTable match={match} sheet={sheet([row(1)], { label: 'something else' })} />);
    expect(screen.getByText(LABEL)).toBeVisible();
  });

  it('is one semantic table per game with a caption, column headers and row headers', () => {
    render(<ScoreSheetTable match={match} sheet={sheet([row(1), row(2, { game: 2 })], { games: [{ number: 1, first_serving_side: 'A', winner: 'A' }, { number: 2, first_serving_side: 'B', winner: null }] })} />);
    const tables = screen.getAllByRole('table');
    expect(tables).toHaveLength(2);
    expect(within(tables[0]!).getByRole('caption')).toHaveTextContent('Game 1, won by your side');
    expect(within(tables[1]!).getByRole('caption')).toHaveTextContent('Game 2');
    const headers = within(tables[0]!).getAllByRole('columnheader').map((h) => h.textContent);
    expect(headers).toEqual(['Rally', 'Start', 'Server', 'Score before', 'Score after', 'Won by', 'Ending', 'Player', 'Notes']);
    expect(within(tables[0]!).getByRole('rowheader', { name: 'Rally 1' })).toBeInTheDocument();
  });

  it('every rally shows its number, start, server, score before and after, winner, ending and player', () => {
    render(<ScoreSheetTable match={match} sheet={sheet([row(12)])} />);
    const r = screen.getByRole('row', { name: /Rally 12/ });
    const cells = within(r).getAllByRole('cell').map((c) => c.textContent);
    expect(cells).toEqual(['14:32', 'Your side, server 1', '4-6-1', '5-6-1', 'Your side', 'Winner', 'Ivy', '']);
  });

  it('a skipped player reads "player not tagged"; a replay names no winner and no player', () => {
    render(<ScoreSheetTable match={match} sheet={sheet([row(8, { responsible_player: null }), row(9, { ending: 'replay', winning_side: null, responsible_player: null, score_after: '4-6-1' })])} />);
    expect(within(screen.getByRole('row', { name: /Rally 8/ })).getByText('player not tagged')).toBeVisible();
    const replay = within(screen.getByRole('row', { name: /Rally 9/ })).getAllByRole('cell').map((c) => c.textContent);
    expect(replay.slice(4, 7)).toEqual(['No one (replay)', 'Replay', 'Not applicable']);
  });

  it('marks corrected and conflicting rallies in text; a conflict row shows no score', () => {
    render(<ScoreSheetTable match={match} sheet={sheet([
      row(2, { corrected_by_user: true }),
      row(3, { marker: 'needs_decision', serving_side: null, score_before: null, score_after: null }),
    ])} />);
    expect(within(screen.getByRole('row', { name: /Rally 2/ })).getByText('corrected by you')).toBeVisible();
    const conflict = within(screen.getByRole('row', { name: /Rally 3/ })).getAllByRole('cell').map((c) => c.textContent);
    expect(conflict.slice(1, 4)).toEqual(['Not scored', 'Not scored', 'Not scored']);
    expect(conflict[7]).toBe('needs your decision');
  });

  it('names the rules version under the label', () => {
    render(<ScoreSheetTable match={match} sheet={sheet([row(1)])} />);
    expect(screen.getByText('Rules: PROVISIONAL-UNVERIFIED')).toBeVisible();
  });
});
