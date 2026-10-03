// Server pages (ST-010): how API outcomes become pages. The API decides access; the page
// only maps 401 → sign-in and 404 → the one not-found page (no existence oracle, ST-006).
import { render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ApiError } from '@/lib/api/client';
import type { Match } from '@/lib/api/types';

const api = {
  listDevUsers: vi.fn(),
  listMatches: vi.fn(),
  me: vi.fn(),
  getMatch: vi.fn(),
};

vi.mock('@/lib/api/server', () => ({
  serverApi: async () => api,
  getMatchForRequest: (id: string) => api.getMatch(id),
}));

class Redirect extends Error {
  constructor(readonly to: string) {
    super(`redirect ${to}`);
  }
}
class NotFound extends Error {}

vi.mock('next/navigation', () => ({
  redirect: (to: string) => {
    throw new Redirect(to);
  },
  notFound: () => {
    throw new NotFound();
  },
  useRouter: () => ({ push: vi.fn(), refresh: vi.fn() }),
}));

const SignInPage = (await import('@/app/page')).default;
const MatchesPage = (await import('@/app/matches/page')).default;
const NewMatchPage = (await import('@/app/matches/new/page')).default;
const MatchPage = (await import('@/app/matches/[matchId]/page')).default;

const ID = '0b8f6c1e-3f3a-4c55-9a51-8d1f0e7d2a10';
const match: Match = {
  id: ID,
  title: 'Skeleton test',
  format: 'doubles',
  status: 'awaiting_upload',
  media: null,
  created_at: '2026-10-05T09:12:44.123Z',
  updated_at: '2026-10-05T09:12:44.123Z',
};

beforeEach(() => {
  for (const fn of Object.values(api)) fn.mockReset();
});

describe('sign-in page', () => {
  it('says sign-in is unavailable when the API is down', async () => {
    api.listDevUsers.mockRejectedValue(new ApiError(503, 'unavailable'));
    render(await SignInPage());
    expect(screen.getByText(/sign-in is not available right now/i)).toBeVisible();
  });

  it('shows the empty state when development sign-in is switched off (404)', async () => {
    api.listDevUsers.mockRejectedValue(new ApiError(404, 'not_found'));
    render(await SignInPage());
    expect(screen.getByText(/no test players are available/i)).toBeVisible();
  });

  it('offers one button per development user', async () => {
    api.listDevUsers.mockResolvedValue([{ username: 'ivy', display_name: 'Ivy' }]);
    render(await SignInPage());
    expect(screen.getByRole('button', { name: 'Sign in as Ivy' })).toBeVisible();
  });
});

describe('matches page', () => {
  it('sends a signed-out visitor to sign in', async () => {
    api.listMatches.mockRejectedValue(new ApiError(401, 'unauthenticated'));
    await expect(MatchesPage()).rejects.toMatchObject({ to: '/' });
  });

  it('lets other API failures reach the error page', async () => {
    api.listMatches.mockRejectedValue(new ApiError(500, 'internal_error'));
    await expect(MatchesPage()).rejects.toBeInstanceOf(ApiError);
  });

  it('shows the empty state', async () => {
    api.listMatches.mockResolvedValue([]);
    render(await MatchesPage());
    expect(screen.getByRole('heading', { level: 1, name: 'Your matches' })).toBeVisible();
    expect(screen.getByText('No matches yet')).toBeVisible();
    expect(screen.getAllByRole('heading')).toHaveLength(1);
  });

  it('lists matches with their status in words', async () => {
    api.listMatches.mockResolvedValue([{ ...match, status: 'video_received' }]);
    render(await MatchesPage());
    expect(screen.getByRole('link', { name: 'Skeleton test' })).toHaveAttribute('href', `/matches/${ID}`);
    expect(screen.getByText(/Doubles · Video received · Created 5 Oct 2026/)).toBeVisible();
  });
});

describe('new match page', () => {
  it('sends a signed-out visitor to sign in', async () => {
    api.me.mockRejectedValue(new ApiError(401, 'unauthenticated'));
    await expect(NewMatchPage()).rejects.toMatchObject({ to: '/' });
  });

  it('lets other API failures reach the error page', async () => {
    api.me.mockRejectedValue(new ApiError(503, 'unavailable'));
    await expect(NewMatchPage()).rejects.toBeInstanceOf(ApiError);
  });

  it('shows the form', async () => {
    api.me.mockResolvedValue({ id: ID, display_name: 'Ivy' });
    render(await NewMatchPage());
    expect(screen.getByRole('heading', { level: 1, name: 'New match' })).toBeVisible();
    expect(screen.getByRole('button', { name: 'Create match' })).toBeVisible();
  });
});

describe('match page', () => {
  const params = Promise.resolve({ matchId: ID });

  it('renders the shared not-found page for a match that is not yours or does not exist', async () => {
    api.getMatch.mockRejectedValue(new ApiError(404, 'not_found'));
    await expect(MatchPage({ params })).rejects.toBeInstanceOf(NotFound);
  });

  it('sends a signed-out visitor to sign in', async () => {
    api.getMatch.mockRejectedValue(new ApiError(401, 'unauthenticated'));
    await expect(MatchPage({ params })).rejects.toMatchObject({ to: '/' });
  });

  it('lets other API failures reach the error page', async () => {
    api.getMatch.mockRejectedValue(new ApiError(500, 'internal_error'));
    await expect(MatchPage({ params })).rejects.toBeInstanceOf(ApiError);
  });

  it('shows the match with its title as the heading', async () => {
    api.getMatch.mockResolvedValue(match);
    render(await MatchPage({ params }));
    expect(screen.getByRole('heading', { level: 1, name: 'Skeleton test' })).toBeVisible();
    expect(screen.getByText('Awaiting upload')).toBeVisible();
  });
});
