// A-03 Signing you in… (ST-013; flows §2; api-sprint-01 §2.2; NFR-055, T-ML-4).
import { render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { AuthCallback } from '@/components/AuthCallback';
import { ApiError } from '@/lib/api/client';

const TOKEN = 'Abc_-0123456789abcdefghijklmnopqrstuvwxyzAB';
const replace = vi.fn();

beforeEach(() => {
  replace.mockReset();
  window.history.replaceState(null, '', '/auth/callback');
});

function withHash(hash: string) {
  window.history.replaceState(null, '', `/auth/callback${hash}`);
}

describe('AuthCallback', () => {
  it('shows "This link has expired" without calling the API when there is no token', async () => {
    const api = { exchangeLink: vi.fn(), requestLink: vi.fn() };
    render(<AuthCallback api={api} navigate={replace} />);
    expect(await screen.findByRole('heading', { level: 1, name: 'This link has expired' })).toBeVisible();
    expect(api.exchangeLink).not.toHaveBeenCalled();
  });

  it('removes the token from the address bar before the request is sent', async () => {
    withHash(`#token=${TOKEN}`);
    let hrefAtRequest = '';
    const api = {
      exchangeLink: vi.fn(async () => {
        hrefAtRequest = window.location.href;
        return { newAccount: true };
      }),
      requestLink: vi.fn(),
    };
    render(<AuthCallback api={api} navigate={replace} />);
    await waitFor(() => expect(replace).toHaveBeenCalled());
    expect(api.exchangeLink).toHaveBeenCalledWith(TOKEN);
    expect(hrefAtRequest).not.toContain('token');
    expect(window.location.href).not.toContain('token');
  });

  it('opens the first-run page for a new account and the matches for a returning one', async () => {
    withHash(`#token=${TOKEN}`);
    const first = { exchangeLink: vi.fn(async () => ({ newAccount: true })), requestLink: vi.fn() };
    const { unmount } = render(<AuthCallback api={first} navigate={replace} />);
    await waitFor(() => expect(replace).toHaveBeenCalledWith('/welcome'));
    unmount();
    withHash(`#token=${TOKEN}`);
    const again = { exchangeLink: vi.fn(async () => ({ newAccount: false })), requestLink: vi.fn() };
    render(<AuthCallback api={again} navigate={replace} />);
    await waitFor(() => expect(replace).toHaveBeenCalledWith('/matches'));
  });

  it('shows A-04 for an expired or used link, with an empty email field', async () => {
    withHash(`#token=${TOKEN}`);
    const api = {
      exchangeLink: vi.fn(async () => {
        throw new ApiError(401, 'link_expired');
      }),
      requestLink: vi.fn(),
    };
    render(<AuthCallback api={api} navigate={replace} />);
    expect(await screen.findByRole('heading', { level: 1, name: 'This link has expired' })).toBeVisible();
    expect(screen.getByLabelText('Email address')).toHaveValue('');
    expect(replace).not.toHaveBeenCalled();
  });

  it('shows a server problem with its reference and a way to get a new link', async () => {
    withHash(`#token=${TOKEN}`);
    const api = {
      exchangeLink: vi.fn(async () => {
        throw new ApiError(500, 'internal_error', 'ref_5c1e0f3a9b7d4e21');
      }),
      requestLink: vi.fn(),
    };
    render(<AuthCallback api={api} navigate={replace} />);
    expect(
      await screen.findByText('Sorry, we could not sign you in. Request a new link. Reference: ref_5c1e0f3a9b7d4e21'),
    ).toBeVisible();
    expect(screen.getByRole('link', { name: 'Send a new link' })).toHaveAttribute('href', '/');
  });

  it('says to reconnect when offline, and keeps nothing on the device', async () => {
    withHash(`#token=${TOKEN}`);
    const api = {
      exchangeLink: vi.fn(async () => {
        throw new ApiError(0, 'network_error');
      }),
      requestLink: vi.fn(),
    };
    render(<AuthCallback api={api} navigate={replace} />);
    expect(await screen.findByText("You're offline. Connect and open the link again.")).toBeVisible();
    expect(window.localStorage.length + window.sessionStorage.length).toBe(0);
  });
});
