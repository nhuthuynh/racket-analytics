// Sign-out clears stored upload URLs even if the server call fails (ASVS 14.3.1).
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { SignOutButton } from '@/components/SignOutButton';
import { ApiError } from '@/lib/api/client';

const push = vi.fn();
vi.mock('next/navigation', () => ({ useRouter: () => ({ push, refresh: vi.fn() }) }));

beforeEach(() => {
  push.mockReset();
  window.localStorage.clear();
});

describe('SignOutButton', () => {
  it('clears local upload data and leaves even when the server call fails', async () => {
    window.localStorage.setItem('tus::ra1-x::1', '{}');
    const api = { signOut: vi.fn().mockRejectedValue(new ApiError(0, 'network_error')) };
    render(<SignOutButton api={api} />);
    await userEvent.click(screen.getByRole('button', { name: 'Sign out' }));
    await waitFor(() => expect(push).toHaveBeenCalledWith('/'));
    expect(window.localStorage.getItem('tus::ra1-x::1')).toBeNull();
  });

  it('signs out on the server', async () => {
    const api = { signOut: vi.fn().mockResolvedValue(undefined) };
    render(<SignOutButton api={api} />);
    await userEvent.click(screen.getByRole('button', { name: 'Sign out' }));
    await waitFor(() => expect(api.signOut).toHaveBeenCalledOnce());
  });
});
