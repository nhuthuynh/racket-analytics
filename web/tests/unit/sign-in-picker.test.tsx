// Dev sign-in picker (ST-010 with ST-006). Accessible names match web/e2e/helpers/journey.ts.
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ApiError } from '@/lib/api/client';
import { SignInPicker } from '@/components/SignInPicker';

const push = vi.fn();
const refresh = vi.fn();
vi.mock('next/navigation', () => ({ useRouter: () => ({ push, refresh }) }));

const users = [
  { username: 'ivy', display_name: 'Ivy' },
  { username: 'carlos', display_name: 'Carlos' },
];

beforeEach(() => {
  push.mockReset();
  refresh.mockReset();
  window.localStorage.clear();
});

describe('SignInPicker', () => {
  it('reports a failed sign-in without navigating', async () => {
    const api = { signIn: vi.fn().mockRejectedValue(new ApiError(401, 'unauthenticated')) };
    render(<SignInPicker users={users} api={api} />);
    await userEvent.click(screen.getByRole('button', { name: 'Sign in as Ivy' }));
    expect(await screen.findByRole('alert')).toHaveTextContent(/could not sign you in/i);
    expect(push).not.toHaveBeenCalled();
  });

  it('shows an empty state when there are no development users', () => {
    render(<SignInPicker users={[]} api={{ signIn: vi.fn() }} />);
    expect(screen.getByText(/no test players are available/i)).toBeVisible();
  });

  it('signs in as the chosen player and opens the matches list', async () => {
    window.localStorage.setItem('tus::ra1-old::1', '{}');
    const api = { signIn: vi.fn().mockResolvedValue(undefined) };
    render(<SignInPicker users={users} api={api} />);
    await userEvent.click(screen.getByRole('button', { name: 'Sign in as Carlos' }));
    await waitFor(() => expect(push).toHaveBeenCalledWith('/matches'));
    expect(api.signIn).toHaveBeenCalledWith('carlos');
    expect(window.localStorage.getItem('tus::ra1-old::1')).toBeNull();
  });
});
