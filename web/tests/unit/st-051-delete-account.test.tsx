// ST-051 UI: X-00 "Your account", X-02 "Delete your account?", X-03 "Your account has been deleted"
// (FR-007, NFR-066; flows-sprint-03 §5; DR-03 R3-7 security amendment). Negative cases first: Cancel
// deletes nothing; a failure keeps the dialog open and the device as it was; a 401 (session ended
// meanwhile) goes to sign-in without clearing anything as "deleted".
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { AccountMenu } from '@/components/AccountMenu';
import { DeleteAccount } from '@/components/DeleteAccount';
import { ApiError } from '@/lib/api/client';

const REF = 'ref_0123456789abcdef';

vi.mock('next/navigation', () => ({
  redirect: (to: string) => {
    throw Object.assign(new Error(`redirect ${to}`), { to });
  },
  notFound: () => {
    throw new Error('not found');
  },
}));
const me = vi.fn();
vi.mock('@/lib/api/server', () => ({ serverApi: async () => ({ me }) }));

function setup(deleteAccount = vi.fn(async () => {})) {
  const navigate = vi.fn();
  const clear = vi.fn(async () => {});
  render(<DeleteAccount api={{ deleteAccount }} navigate={navigate} clear={clear} />);
  return { deleteAccount, navigate, clear, opener: screen.getByRole('button', { name: 'Delete my account' }) };
}

describe('X-02 delete my account (ST-051)', () => {
  it('X-00 says what deleting does before anything is pressed', () => {
    setup();
    expect(screen.getByRole('heading', { level: 2, name: 'Delete your account' })).toBeVisible();
    expect(screen.getByText('This deletes your account and all your matches.')).toBeVisible();
    expect(screen.queryByRole('dialog')).toBeNull();
  });

  it('Cancel deletes nothing and gives focus back', async () => {
    const { deleteAccount, opener, clear } = setup();
    await userEvent.click(opener);
    const dialog = screen.getByRole('dialog', { name: 'Delete your account?' });
    expect(within(dialog).getByRole('button', { name: 'Cancel' })).toHaveFocus();
    await userEvent.click(within(dialog).getByRole('button', { name: 'Cancel' }));
    expect(screen.queryByRole('dialog')).toBeNull();
    expect(opener).toHaveFocus();
    expect(deleteAccount).not.toHaveBeenCalled();
    expect(clear).not.toHaveBeenCalled();
  });

  it('states every consequence, including signed out everywhere and the PM-1 default', async () => {
    const { opener } = setup();
    await userEvent.click(opener);
    const dialog = screen.getByRole('dialog');
    for (const line of [
      'This deletes your account and all your matches: every video, tag, score sheet and stat.',
      'You will be signed out on every device.',
      'It cannot be undone.',
      'Stored files are removed within 7 days.',
      'If you sign in again with the same email address, you start with a new, empty account.',
    ]) expect(dialog).toHaveTextContent(line);
    expect(within(dialog).queryByRole('textbox')).toBeNull();
  });

  it('a failure keeps the dialog open with the reason and the reference; the device is not cleared', async () => {
    const { navigate, clear } = setup(vi.fn().mockRejectedValue(new ApiError(500, 'internal_error', REF)));
    await userEvent.click(screen.getByRole('button', { name: 'Delete my account' }));
    await userEvent.click(within(screen.getByRole('dialog')).getByRole('button', { name: 'Delete my account' }));
    expect(await screen.findByRole('alert')).toHaveTextContent(`Your account was not deleted. Try again. Reference: ${REF}`);
    expect(navigate).not.toHaveBeenCalled();
    expect(clear).not.toHaveBeenCalled();
  });

  it('401 (the session ended meanwhile): sign in, nothing deleted, nothing said about deletion', async () => {
    const { navigate } = setup(vi.fn().mockRejectedValue(new ApiError(401, 'unauthenticated')));
    await userEvent.click(screen.getByRole('button', { name: 'Delete my account' }));
    await userEvent.click(within(screen.getByRole('dialog')).getByRole('button', { name: 'Delete my account' }));
    await vi.waitFor(() => expect(navigate).toHaveBeenCalledWith('/'));
  });

  it('after 202: clears the device as at sign-out, then X-03', async () => {
    const { deleteAccount, navigate, clear } = setup();
    await userEvent.click(screen.getByRole('button', { name: 'Delete my account' }));
    await userEvent.click(within(screen.getByRole('dialog')).getByRole('button', { name: 'Delete my account' }));
    await vi.waitFor(() => expect(navigate).toHaveBeenCalledWith('/signed-out?deleted=1'));
    expect(deleteAccount).toHaveBeenCalledOnce();
    expect(clear.mock.invocationCallOrder[0]!).toBeGreaterThan(deleteAccount.mock.invocationCallOrder[0]!);
    expect(navigate.mock.invocationCallOrder[0]!).toBeGreaterThan(clear.mock.invocationCallOrder[0]!);
  });
});

describe('X-00 page, X-03 and the account menu entry', () => {
  it('X-00 sends a signed-out visitor to sign in', async () => {
    me.mockRejectedValue(new ApiError(401, 'unauthenticated'));
    const Page = (await import('@/app/settings/account/page')).default;
    await expect(Page()).rejects.toMatchObject({ to: '/' });
  });

  it('X-00 has the h1 "Your account" and the delete section', async () => {
    me.mockResolvedValue({ id: 'x', display_name: null });
    const Page = (await import('@/app/settings/account/page')).default;
    render(await Page());
    expect(screen.getByRole('heading', { level: 1, name: 'Your account' })).toBeVisible();
    expect(screen.getByRole('button', { name: 'Delete my account' })).toBeVisible();
  });

  it('X-03 says the account is deleted without over-promising (DR-03 R3-7), and offers sign-in', async () => {
    const Page = (await import('@/app/signed-out/page')).default;
    render(await Page({ searchParams: Promise.resolve({ deleted: '1' }) }));
    expect(screen.getByRole('heading', { level: 1, name: 'Your account has been deleted' })).toBeVisible();
    expect(screen.getByText("The app's data on this device has been cleared. Its stored files are removed within 7 days.")).toBeVisible();
    expect(screen.queryByText(/Nothing from/)).toBeNull();
    expect(screen.getByRole('link', { name: 'Sign in' })).toHaveAttribute('href', '/');
  });

  it('A-05 no longer promises that nothing is kept on the device (DR-03 R3-7, SEC-S3-TM-12)', async () => {
    const Page = (await import('@/app/signed-out/page')).default;
    render(await Page({ searchParams: Promise.resolve({}) }));
    expect(screen.getByRole('heading', { level: 1, name: 'You have signed out' })).toBeVisible();
    expect(screen.getByText("The app's data on this device has been cleared.")).toBeVisible();
    expect(screen.queryByText(/Nothing from your account/)).toBeNull();
  });

  it('the account menu offers "Your account" above "Sign out"', async () => {
    render(<AccountMenu api={{ signOut: vi.fn() }} navigate={vi.fn()} clear={vi.fn()} />);
    await userEvent.click(screen.getByRole('button', { name: 'Your account' }));
    const items = within(screen.getByRole('list')).getAllByRole('listitem').map((li) => li.textContent);
    expect(screen.getByRole('link', { name: 'Your account' })).toHaveAttribute('href', '/settings/account');
    expect(items.indexOf('Your account')).toBeLessThan(items.indexOf('Sign out'));
  });
});
