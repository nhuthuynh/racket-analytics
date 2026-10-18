// P-01 nav (ST-063a; flows-sprint-04 §1, §2 "Nav"): D-01 links to the training plan under its
// header. The account-menu link is checked in plan-view.test.tsx.
import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import type { Match } from '@/lib/api/types';

const ID = '0b8f6c1e-3f3a-4c55-9a51-8d1f0e7d2a10';
const match: Match = {
  id: ID, title: 'Saturday doubles', format: 'doubles', status: 'uploading', media: null,
  created_at: 'x', updated_at: 'x', upload: null, rejection: null, participants: [],
};

const api = vi.hoisted(() => ({ getMatch: vi.fn() }));
vi.mock('@/lib/api/server', () => ({
  serverApi: async () => api,
  getMatchForRequest: (id: string) => api.getMatch(id),
}));
vi.mock('next/navigation', () => ({ redirect: vi.fn(), notFound: vi.fn() }));

describe('D-01 links to P-01', () => {
  it('"Your training plan" sits under the stats header', async () => {
    api.getMatch.mockResolvedValue(match);
    const StatsPage = (await import('@/app/matches/[matchId]/stats/page')).default;
    render(await StatsPage({ params: Promise.resolve({ matchId: ID }) }));
    const link = screen.getByRole('link', { name: 'Your training plan' });
    expect(link).toHaveAttribute('href', '/plan');
    const h1 = screen.getByRole('heading', { level: 1, name: 'Stats' });
    expect(h1.compareDocumentPosition(link) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });
});
