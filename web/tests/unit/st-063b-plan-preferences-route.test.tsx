// ST-063b P-02 route wrapper: the last preferences are read before the form shows (SC 3.3.7);
// signed out goes to the start page; an unreadable plan starts the form empty. Negative first.
import { render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

const router = { push: vi.fn(), replace: vi.fn() };
vi.mock('next/navigation', () => ({ useRouter: () => router }));
const { PlanPreferencesRoute } = await import('@/components/plan/PlanPreferencesRoute');

function answering(status: number, body: unknown) {
  vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify(body), { status })));
}
afterEach(() => {
  vi.unstubAllGlobals();
  router.push.mockClear();
  router.replace.mockClear();
});

describe('PlanPreferencesRoute (negative first)', () => {
  it('signed out: goes to the start page and shows no form', async () => {
    answering(401, { error: { code: 'unauthenticated' } });
    render(<PlanPreferencesRoute />);
    expect(screen.getByRole('status')).toHaveTextContent('Loading your setup…');
    await vi.waitFor(() => expect(router.replace).toHaveBeenCalledWith('/'));
    expect(screen.queryByRole('heading', { name: 'Your practice setup' })).not.toBeInTheDocument();
  });

  it('an unreadable plan starts the form empty, with no "replaces" line', async () => {
    answering(500, { error: { code: 'internal_error' } });
    render(<PlanPreferencesRoute />);
    expect(await screen.findByRole('heading', { name: 'Your practice setup' })).toBeInTheDocument();
    expect(screen.getByLabelText('How long is each session?')).toHaveValue('');
    expect(screen.queryByText('This replaces your current plan.')).not.toBeInTheDocument();
  });

  it('reads GET /api/me/plan and prefills the form from its preferences', async () => {
    answering(200, { preferences: { minutes_per_session: 60, sessions_per_week: 4, players_available: 4, equipment: ['full_court'], level: 'advanced' } });
    render(<PlanPreferencesRoute />);
    expect(await screen.findByLabelText('How long is each session?')).toHaveValue('60');
    expect(screen.getByLabelText('A full court')).toBeChecked();
    expect(vi.mocked(fetch)).toHaveBeenCalledWith('/api/me/plan', expect.objectContaining({ method: 'GET' }));
  });
});
