// P-03 on P-01 (ST-063c; FR-124; flows-sprint-04 §4): the "Not for me" dialog. Negative first: offline
// it is disabled; a failed or limited swap keeps the dialog and the reason.
import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { PlanView } from '@/components/plan/PlanView';
import { parsePlan, type PlanRead } from '@/lib/api/plan';
import type { FollowThroughApi } from '@/lib/plan-outbox-api';
import { swapRateLimitMessage } from '@/components/plan/PlanViewWords';
import { planBody } from './fixtures/plan';

const A1 = '00000000-0000-4000-8000-000000000102';
let online: boolean;

beforeEach(() => {
  online = true;
  vi.spyOn(navigator, 'onLine', 'get').mockImplementation(() => online);
});

function followApi(over: Partial<FollowThroughApi> = {}): FollowThroughApi {
  return {
    markDone: vi.fn(async () => ({ kind: 'done' as const, planVersion: 2, replayed: false })),
    undoDone: vi.fn(async () => ({ kind: 'undone' as const, planVersion: 3 })),
    swap: vi.fn(async () => ({ kind: 'no_alternative' as const })),
    ...over,
  };
}

const planRead = (): PlanRead => ({ kind: 'plan', plan: parsePlan(planBody()) });

async function show(
  api: FollowThroughApi,
  getPlan = vi.fn(async (): Promise<PlanRead> => planRead()),
  onSignedOut = vi.fn(),
) {
  render(
    <PlanView api={{ getPlan }} followApi={api} onSignedOut={onSignedOut} evidenceApi={{ stats: vi.fn(), evidence: vi.fn() }} />,
  );
  await screen.findByText('Serve to a target');
  return { getPlan };
}

describe('Not for me (negative first)', () => {
  it('offline, "Not for me" is disabled and says it needs a connection', async () => {
    online = false;
    await show(followApi());
    const button = screen.getByRole('button', { name: 'Not for me, Serve to a target' });
    expect(button).toBeDisabled();
    expect(within(button.closest('li')!).getByText('Needs a connection')).toBeVisible();
  });

  it('a 5xx keeps the dialog and the reason, with the reference', async () => {
    const api = followApi({ swap: vi.fn(async () => ({ kind: 'failed' as const, supportRef: 'ref_0123456789abcdef' })) });
    await show(api);
    const user = userEvent.setup();
    await user.click(screen.getByRole('button', { name: 'Not for me, Serve to a target' }));
    const dialog = screen.getByRole('dialog', { name: 'Swap Serve to a target?' });
    await user.type(within(dialog).getByLabelText('Why not? (optional)'), 'too hard');
    await user.click(within(dialog).getByRole('button', { name: 'Swap drill' }));
    const alert = await within(dialog).findByRole('alert');
    expect(alert).toHaveTextContent('We could not swap the drill. Try again.');
    expect(alert).toHaveTextContent('Reference: ref_0123456789abcdef');
    expect(within(dialog).getByLabelText('Why not? (optional)')).toHaveValue('too hard');
  });

  it('429 rate_limited keeps the dialog and the reason and says when to try again', async () => {
    const api = followApi({ swap: vi.fn(async () => ({ kind: 'rate_limited' as const, retryAt: null })) });
    await show(api);
    const user = userEvent.setup();
    await user.click(screen.getByRole('button', { name: 'Not for me, Serve to a target' }));
    const dialog = screen.getByRole('dialog', { name: 'Swap Serve to a target?' });
    await user.type(within(dialog).getByLabelText('Why not? (optional)'), 'too hard');
    await user.click(within(dialog).getByRole('button', { name: 'Swap drill' }));
    const alert = await within(dialog).findByRole('alert');
    expect(alert).toHaveTextContent('You have swapped many drills in a short time. Try again in an hour.');
    expect(alert).not.toHaveTextContent('rate_limited');
    expect(within(dialog).getByLabelText('Why not? (optional)')).toHaveValue('too hard');
  });

  it('the 429 text gives the retry time in local 24-hour time, never a raw code', () => {
    expect(swapRateLimitMessage('2026-10-18T14:05:00Z', 'UTC')).toBe(
      'You have swapped many drills in a short time. You can swap again at 14:05. Your reason is kept.',
    );
    expect(swapRateLimitMessage('not a time', 'UTC')).toBe(
      'You have swapped many drills in a short time. Try again in an hour. Your reason is kept.',
    );
  });

  it('the dialog opens with Cancel focused, a 200-character reason and a counter', async () => {
    await show(followApi());
    const user = userEvent.setup();
    await user.click(screen.getByRole('button', { name: 'Not for me, Serve to a target' }));
    const dialog = screen.getByRole('dialog', { name: 'Swap Serve to a target?' });
    expect(within(dialog).getByRole('button', { name: 'Cancel' })).toHaveFocus();
    expect(within(dialog).getByText('We will pick another drill that works on the same thing and fits your session.')).toBeVisible();
    const reason = within(dialog).getByLabelText('Why not? (optional)');
    expect(reason).toHaveAttribute('maxlength', '200');
    await user.type(reason, 'slow');
    expect(within(dialog).getByText('4 of 200 characters')).toBeVisible();
    await user.click(within(dialog).getByRole('button', { name: 'Cancel' }));
    expect(screen.queryByRole('dialog')).toBeNull();
  });

  it('409 no_alternative moves focus to the alert; Close closes the dialog', async () => {
    await show(followApi());
    const user = userEvent.setup();
    await user.click(screen.getByRole('button', { name: 'Not for me, Serve to a target' }));
    await user.click(screen.getByRole('button', { name: 'Swap drill' }));
    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent('No other drill fits your setup for this. Your plan is unchanged.');
    await waitFor(() => expect(alert).toHaveFocus());
    await user.click(screen.getByRole('button', { name: 'Close' }));
    expect(screen.queryByRole('dialog')).toBeNull();
  });

  it('409 session_done says so and, on Close, reads the plan again', async () => {
    const api = followApi({ swap: vi.fn(async () => ({ kind: 'session_done' as const })) });
    const { getPlan } = await show(api);
    const user = userEvent.setup();
    await user.click(screen.getByRole('button', { name: 'Not for me, Serve to a target' }));
    await user.click(screen.getByRole('button', { name: 'Swap drill' }));
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'This session is already done, so its drills cannot be swapped. Your plan is unchanged.',
    );
    await user.click(screen.getByRole('button', { name: 'Close' }));
    await waitFor(() => expect(getPlan).toHaveBeenCalledTimes(2));
  });

  it('409 plan_conflict offers "Reload plan", which reads the plan again', async () => {
    const api = followApi({ swap: vi.fn(async () => ({ kind: 'plan_conflict' as const })) });
    const { getPlan } = await show(api);
    const user = userEvent.setup();
    await user.click(screen.getByRole('button', { name: 'Not for me, Serve to a target' }));
    await user.click(screen.getByRole('button', { name: 'Swap drill' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Your plan changed on another device. Nothing was swapped.');
    await user.click(screen.getByRole('button', { name: 'Reload plan' }));
    await waitFor(() => expect(getPlan).toHaveBeenCalledTimes(2));
    expect(api.swap).toHaveBeenCalledWith(A1, '');
  });
});

// Review findings on PR #142 (principal-engineer F1-F3, senior-backend-engineer S1/S2/N1, nits).
describe('Not for me: the remaining swap answers and states (review of #142)', () => {
  async function openAndSwap(reason = '') {
    const user = userEvent.setup();
    await user.click(screen.getByRole('button', { name: 'Not for me, Serve to a target' }));
    const dialog = screen.getByRole('dialog', { name: 'Swap Serve to a target?' });
    if (reason) await user.type(within(dialog).getByLabelText('Why not? (optional)'), reason);
    await user.click(within(dialog).getByRole('button', { name: 'Swap drill' }));
    return { user, dialog };
  }

  it('going offline while the dialog is open disables "Swap drill" and says it needs a connection', async () => {
    await show(followApi());
    const user = userEvent.setup();
    await user.click(screen.getByRole('button', { name: 'Not for me, Serve to a target' }));
    const dialog = screen.getByRole('dialog', { name: 'Swap Serve to a target?' });
    online = false;
    act(() => {
      window.dispatchEvent(new Event('offline'));
    });
    expect(within(dialog).getByRole('button', { name: 'Swap drill' })).toBeDisabled();
    expect(within(dialog).getByText('Needs a connection')).toBeVisible();
  });

  it('opening the dialog again clears the last "Swapped for ..." status, so a repeat swap is announced', async () => {
    const swapped = parsePlan(planBody()).sessions[0]!;
    const api = followApi({ swap: vi.fn(async () => ({ kind: 'swapped' as const, session: swapped, planVersion: 2 })) });
    await show(api);
    await openAndSwap();
    expect(await screen.findByText('Swapped for Serve to a target.')).toBeVisible();
    await userEvent.setup().click(screen.getByRole('button', { name: 'Not for me, Serve to a target' }));
    expect(screen.queryByText('Swapped for Serve to a target.')).toBeNull();
  });

  it('404 not_found closes the dialog and reads the plan again', async () => {
    const api = followApi({ swap: vi.fn(async () => ({ kind: 'not_found' as const })) });
    const { getPlan } = await show(api);
    await openAndSwap();
    await waitFor(() => expect(getPlan).toHaveBeenCalledTimes(2));
    expect(screen.queryByRole('dialog')).toBeNull();
  });

  it('401 signed_out sends the player to sign in once', async () => {
    const api = followApi({ swap: vi.fn(async () => ({ kind: 'signed_out' as const })) });
    const onSignedOut = vi.fn();
    await show(api, undefined, onSignedOut);
    await openAndSwap();
    await waitFor(() => expect(onSignedOut).toHaveBeenCalledTimes(1));
  });

  it('Escape after 409 session_done closes the dialog and reads the plan again', async () => {
    const api = followApi({ swap: vi.fn(async () => ({ kind: 'session_done' as const })) });
    const { getPlan } = await show(api);
    const { dialog } = await openAndSwap();
    await screen.findByRole('alert');
    fireEvent(dialog, new Event('cancel', { cancelable: true }));
    await waitFor(() => expect(getPlan).toHaveBeenCalledTimes(2));
    expect(screen.queryByRole('dialog')).toBeNull();
  });

  it('Escape before any answer closes the dialog without reading the plan again', async () => {
    const { getPlan } = await show(followApi());
    await userEvent.setup().click(screen.getByRole('button', { name: 'Not for me, Serve to a target' }));
    fireEvent(screen.getByRole('dialog', { name: 'Swap Serve to a target?' }), new Event('cancel', { cancelable: true }));
    expect(screen.queryByRole('dialog')).toBeNull();
    expect(getPlan).toHaveBeenCalledTimes(1);
  });

  it('a 429 with a retry time shows that time in the dialog and keeps the reason', async () => {
    const retryAt = '2026-10-18T14:05:00Z';
    const api = followApi({ swap: vi.fn(async () => ({ kind: 'rate_limited' as const, retryAt })) });
    await show(api);
    const { dialog } = await openAndSwap('too hard');
    expect(await within(dialog).findByRole('alert')).toHaveTextContent(swapRateLimitMessage(retryAt));
    expect(within(dialog).getByLabelText('Why not? (optional)')).toHaveValue('too hard');
  });
});
