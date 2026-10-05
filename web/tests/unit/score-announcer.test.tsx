// ST-029 score call and polite announcement (FR-048, call format provisional
// @needs-verification; DES FR-UX-62). Negative case first: nothing is announced before a tag is
// confirmed, and focus never moves.
import { act, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { ScoreAnnouncer } from '@/components/tagging/ScoreAnnouncer';
import { QuickTag, type QuickTagApi } from '@/components/tagging/QuickTag';
import type { Match } from '@/lib/api/types';
import type { ScoreSheet, SheetRow } from '@/lib/tagging/types';

const ID = '0b8f6c1e-3f3a-4c55-9a51-8d1f0e7d2a10';
const match: Match = {
  id: ID, title: 'Saturday doubles', format: 'doubles', status: 'video_received', media: null,
  created_at: 'x', updated_at: 'x', upload: null, rejection: null,
  participants: [{ slot: 'A1', nickname: 'Ivy', is_me: true }, { slot: 'B1', nickname: 'Carlos', is_me: false }],
};
const sheet = (rows: SheetRow[] = []): ScoreSheet => ({
  rules_version: 'PROVISIONAL-UNVERIFIED', unofficial: true, label: 'unofficial scoring (rules not yet verified)',
  rows, games: [{ number: 1, first_serving_side: 'A', winner: null }], match_winner: null,
});
const row = (n: number, over: Partial<SheetRow> = {}): SheetRow => ({
  rally_id: `7d0c6c1e-3f3a-4c55-9a51-8d1f0e7d2a${String(n).padStart(2, '0')}`, number: n, game: 1, start_ms: n * 10_000,
  end_ms: n * 10_000 + 5000, serving_side: 'A', score_before: '0-0-2', score_after: '0-0-1', winning_side: 'B', ending: 'winner',
  responsible_player: null, fault_kind: null, marker: null, corrected_by_user: false, ...over,
});

describe('ScoreAnnouncer', () => {
  it('is one polite status region that is present before anything is said', () => {
    render(<ScoreAnnouncer message="" />);
    const region = screen.getByRole('status');
    expect(region).toHaveAttribute('aria-live', 'polite');
    expect(region).toHaveTextContent('');
  });
});

describe('QuickTag announcements (E2E-02-03 at unit level)', () => {
  it('announces nothing for a pending tag, then "Rally n: them. Score x-y-z." and keeps focus', async () => {
    let answer!: (v: Awaited<ReturnType<QuickTagApi['tagRally']>>) => void;
    const api = {
      tagRally: vi.fn<QuickTagApi['tagRally']>(() => new Promise((res) => { answer = res; })),
      startGame: vi.fn(), getScoreSheet: vi.fn(), undo: vi.fn(),
    } as unknown as QuickTagApi;
    let t = 1000;
    render(<QuickTag match={match} initialSheet={sheet()} initialVersion={1} api={api} clock={() => t} videoSrc={null} />);
    const u = userEvent.setup();
    await u.click(screen.getByRole('button', { name: 'Rally start' }));
    t = 5000;
    await u.click(screen.getByRole('button', { name: 'Rally end' }));
    await u.click(screen.getByRole('button', { name: /^Other side/ }));
    const ending = screen.getByRole('button', { name: 'Winner' });
    await u.click(ending);
    const region = screen.getByRole('status');
    expect(region).toHaveTextContent('');
    await act(async () => answer({ version: 2, rallyId: row(1).rally_id, sheet: sheet([row(1)]) }));
    expect(region).toHaveTextContent('Rally 1: them. Score 0-0-1.');
    expect(ending).toHaveFocus();
  });
});
