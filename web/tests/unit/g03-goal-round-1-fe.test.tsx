// Goal round 1 (G03-06, G03-07, G03-10), found on the live Compose stack over HTTPS with Chrome for
// Testing 141 (E2E-03-06, E2E-03-09, E2E-03-01):
// 1. targets: the inline "score sheet" link of D-01's HAX sentence measured 104x21; it needs a
//    24 px target (NFR-028; the E2E target check has no inline exception);
// 2. E2E-03-09 loading: the busy region was in the server HTML, so it was visible before the
//    browser had asked for the numbers ("D-01 never asked the API for its numbers"). The server
//    HTML reserves the same space without claiming to be busy; the region turns busy when the
//    request starts.
import { render, screen } from '@testing-library/react';
import { renderToString } from 'react-dom/server';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { StatsDashboard } from '@/components/stats/StatsDashboard';
import type { Match } from '@/lib/api/types';
import { parseStats } from '@/lib/stats/parse';
import { WORKED_BODY } from './fixtures/stats';

const ID = '0b8f6c1e-3f3a-4c55-9a51-8d1f0e7d2a10';
const match: Match = {
  id: ID, title: 'Saturday doubles', format: 'doubles', status: 'video_received', media: null,
  created_at: 'x', updated_at: 'x', upload: null, rejection: null, participants: [],
};

const api = vi.hoisted(() => ({ getMatch: vi.fn(), getScoreSheet: vi.fn() }));
vi.mock('@/lib/api/server', () => ({
  serverApi: async () => api,
  getMatchForRequest: (id: string) => api.getMatch(id),
}));
vi.mock('next/navigation', () => ({ redirect: vi.fn(), notFound: vi.fn() }));

beforeEach(() => {
  api.getMatch.mockReset();
  api.getScoreSheet.mockReset();
});

describe('D-01 HAX sentence link target (G03-10 b)', () => {
  it('"score sheet" carries the 24 px inline target class', async () => {
    api.getMatch.mockResolvedValue(match);
    api.getScoreSheet.mockResolvedValue({ version: 0, sheet: { rules_version: 'x', unofficial: true, label: 'x', rows: [], games: [], match_winner: null } });
    const StatsPage = (await import('@/app/matches/[matchId]/stats/page')).default;
    render(await StatsPage({ params: Promise.resolve({ matchId: ID }) }));
    expect(screen.getByRole('link', { name: 'score sheet' })).toHaveClass('inline-target');
  });
});

describe('D-01 loading only once the request has started (E2E-03-09)', () => {
  it('the server HTML reserves the cards but is neither busy nor a status', () => {
    const html = renderToString(<StatsDashboard match={match} rallyCount={14} api={{ stats: vi.fn(), evidence: vi.fn() }} />);
    expect(html).toContain('stat-card--reserved');
    expect(html).not.toContain('aria-busy="true"');
    expect(html).not.toContain('role="status"');
  });

  it('in the browser the region is busy while the request runs, and the request has been made', async () => {
    const stats = vi.fn(() => new Promise<never>(() => {}));
    const { container } = render(<StatsDashboard match={match} rallyCount={14} api={{ stats, evidence: vi.fn() }} />);
    expect(stats).toHaveBeenCalledTimes(1);
    expect(container.querySelector('[aria-busy="true"]')).not.toBeNull();
    expect(screen.getByRole('status')).toHaveTextContent('Loading your stats…');
  });

  it('still shows the numbers once they come', async () => {
    render(<StatsDashboard match={match} rallyCount={14} api={{ stats: vi.fn(async () => parseStats(structuredClone(WORKED_BODY))), evidence: vi.fn() }} />);
    expect(await screen.findByRole('heading', { name: 'Rallies won on serve' })).toBeVisible();
  });
});
