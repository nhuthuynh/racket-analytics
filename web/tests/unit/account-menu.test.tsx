// Account menu and sign-out (ST-014; flows A-05 and "Your upload will stop"; FR-011).
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { AccountMenu } from '@/components/AccountMenu';
import { ApiError } from '@/lib/api/client';
import { setActiveUpload } from '@/lib/upload/activity';

afterEach(() => setActiveUpload(null));

function setup(signOut = vi.fn(async () => undefined)) {
  const navigate = vi.fn();
  const clear = vi.fn(async () => undefined);
  render(<AccountMenu api={{ signOut }} navigate={navigate} clear={clear} />);
  return { signOut, navigate, clear };
}

async function chooseSignOut() {
  await userEvent.click(screen.getByRole('button', { name: 'Your account' }));
  await userEvent.click(screen.getByRole('button', { name: 'Sign out' }));
}

describe('AccountMenu', () => {
  it('keeps the menu closed until asked', async () => {
    setup();
    const toggle = screen.getByRole('button', { name: 'Your account' });
    expect(toggle).toHaveAttribute('aria-expanded', 'false');
    expect(screen.queryByRole('button', { name: 'Sign out' })).toBeNull();
    await userEvent.click(toggle);
    expect(toggle).toHaveAttribute('aria-expanded', 'true');
  });

  it('clears the device and says so even when the server cannot be reached', async () => {
    const { navigate, clear } = setup(vi.fn(async () => {
      throw new ApiError(0, 'network_error');
    }));
    await chooseSignOut();
    await waitFor(() => expect(navigate).toHaveBeenCalledWith('/signed-out?server=unreachable'));
    expect(clear).toHaveBeenCalledOnce();
  });

  it('signs out on the server, clears the device, then shows A-05', async () => {
    const { signOut, navigate, clear } = setup();
    await chooseSignOut();
    await waitFor(() => expect(navigate).toHaveBeenCalledWith('/signed-out'));
    expect(signOut).toHaveBeenCalledOnce();
    expect(clear).toHaveBeenCalledOnce();
    expect(clear.mock.invocationCallOrder[0]!).toBeGreaterThan(signOut.mock.invocationCallOrder[0]!);
  });

  it('asks first while an upload is running, with "Keep uploading" focused', async () => {
    setActiveUpload({ title: 'Sat doubles', percent: 64, stop: vi.fn() });
    const { signOut } = setup();
    await chooseSignOut();
    expect(screen.getByRole('heading', { level: 1, name: 'Your upload will stop' })).toBeVisible();
    expect(
      screen.getByText(
        "'Sat doubles' is 64% uploaded. If you sign out now, the upload stops. You can resume it later from the match page by choosing the same video.",
      ),
    ).toBeVisible();
    expect(screen.getByRole('button', { name: 'Keep uploading' })).toHaveFocus();
    await userEvent.click(screen.getByRole('button', { name: 'Keep uploading' }));
    expect(screen.queryByRole('heading', { name: 'Your upload will stop' })).toBeNull();
    expect(signOut).not.toHaveBeenCalled();
  });

  it('stops the upload before signing out when the user insists', async () => {
    const stop = vi.fn();
    setActiveUpload({ title: 'Sat doubles', percent: 64, stop });
    const { signOut, navigate } = setup();
    await chooseSignOut();
    await userEvent.click(screen.getByRole('button', { name: 'Sign out anyway' }));
    await waitFor(() => expect(navigate).toHaveBeenCalledWith('/signed-out'));
    expect(stop.mock.invocationCallOrder[0]!).toBeLessThan(signOut.mock.invocationCallOrder[0]!);
  });
});
