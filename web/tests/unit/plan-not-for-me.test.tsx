// P-03 on P-01 (ST-063c; FR-124; flows-sprint-04 §4): the "Not for me" dialog. Negative first: offline
// it is disabled; a failed or limited swap keeps the dialog and the reason.
import { render, screen, waitFor, within } from '@testing-library/react';
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

async function show(api: FollowThroughApi, getPlan = vi.fn(async (): Promise<PlanRead> => planRead())) {
  render(<PlanView api={{ getPlan }} followApi={api} evidenceApi={{ stats: vi.fn(), evidence: vi.fn() }} />);
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
