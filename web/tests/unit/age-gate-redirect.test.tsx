// ST-068b review PE-ST068b-01 (flows-sprint-04 §5): a 403 `age_confirmation_required` on the sign-in page, the
// matches list or match setup (a live session, age not answered) goes to A-10; any other 403 does not.
import { describe, expect, it, vi } from 'vitest';
import { ApiError } from '@/lib/api/client';

const api = { me: vi.fn(), listMatches: vi.fn(), listDevUsers: vi.fn(), uploadPolicy: vi.fn(), publicConfig: vi.fn() };
vi.mock('@/lib/api/server', () => ({ serverApi: async () => api }));
vi.mock('next/navigation', () => ({
  redirect: (to: string) => {
    throw Object.assign(new Error(`redirect ${to}`), { to });
  },
}));

const pages = {
  'sign-in page': (await import('@/app/page')).default,
  'matches list': (await import('@/app/matches/(list)/page')).default,
  'match setup': (await import('@/app/matches/(list)/new/page')).default,
};

function apiAnswers(error: ApiError) {
  api.me.mockRejectedValue(error);
  api.listMatches.mockRejectedValue(error);
  api.listDevUsers.mockResolvedValue([]);
  api.publicConfig.mockResolvedValue({ ageGate: true });
}

describe.each(Object.entries(pages))('%s and the age gate', (_name, Page) => {
  it('does not send another 403 to the age question', async () => {
    apiAnswers(new ApiError(403, 'under_age'));
    expect(await Promise.resolve(Page()).catch((e: unknown) => e)).not.toMatchObject({ to: '/welcome/age' });
  });

  it('sends a 403 age_confirmation_required to the age question', async () => {
    apiAnswers(new ApiError(403, 'age_confirmation_required'));
    await expect(Page()).rejects.toMatchObject({ to: '/welcome/age' });
  });
});
