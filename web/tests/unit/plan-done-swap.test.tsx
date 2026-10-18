// P-03 on P-01 (ST-063c; FR-124; flows-sprint-04 §4): "Mark done" through the outbox, "Undo", the
// "Not for me" dialog and the offline P-01 state. Negative first: a "done" that cannot be sent is
// kept and said so; never shown as synced.
import 'fake-indexeddb/auto';
import { IDBFactory } from 'fake-indexeddb';
import { act, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { PlanView } from '@/components/plan/PlanView';
import { parsePlan, type PlanRead } from '@/lib/api/plan';
import { createOutbox, type Outbox } from '@/lib/plan-outbox';
import { idbOutboxStore } from '@/lib/plan-outbox-idb';
import type { FollowThroughApi } from '@/lib/plan-outbox-api';
import { planBody } from './fixtures/plan';

const S1 = '00000000-0000-4000-8000-000000000010';
const A1 = '00000000-0000-4000-8000-000000000102';
let online: boolean;
let outbox: Outbox;

beforeEach(() => {
  online = true;
  vi.spyOn(navigator, 'onLine', 'get').mockImplementation(() => online);
  outbox = createOutbox(idbOutboxStore(new IDBFactory()));
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
  render(<PlanView api={{ getPlan }} followApi={api} outbox={outbox} evidenceApi={{ stats: vi.fn(), evidence: vi.fn() }} />);
  await screen.findByText('Serve to a target');
  return { getPlan };
}

const session1 = () => screen.getByRole('region', { name: /^Session 1 of 3/ });

describe('Mark done (negative first)', () => {
  it('online, a failed send keeps the op and says it will sync', async () => {
    const api = followApi({ markDone: vi.fn(async () => ({ kind: 'failed' as const, supportRef: null })) });
    await show(api);
    await userEvent.setup().click(within(session1()).getByRole('button', { name: 'Mark done' }));
    expect(
      await within(session1()).findByText("We could not save 'done'. It stays on this device and will sync."),
    ).toBeVisible();
    expect((await outbox.pending()).map((o) => o.session_id)).toEqual([S1]);
  });

  it('a session gone from the plan drops the op, says so and reads the plan again', async () => {
    const api = followApi({ markDone: vi.fn(async () => ({ kind: 'not_found' as const })) });
    const { getPlan } = await show(api);
    await userEvent.setup().click(within(session1()).getByRole('button', { name: 'Mark done' }));
    expect(
      await screen.findByText("We could not save 'done' for a session that is no longer in your plan."),
    ).toBeVisible();
    await waitFor(() => expect(getPlan).toHaveBeenCalledTimes(2));
    expect(await outbox.pending()).toEqual([]);
  });

  it('online, done at once and "Undo" offered', async () => {
    const api = followApi();
    await show(api);
    await userEvent.setup().click(within(session1()).getByRole('button', { name: 'Mark done' }));
    expect(await within(session1()).findByText('Done')).toBeVisible();
    expect(within(session1()).getByRole('button', { name: 'Undo' })).toBeEnabled();
  });

  it('an op left from an earlier visit is synced on page load', async () => {
    await outbox.queueDone(S1);
    const api = followApi();
    await show(api);
    expect(await screen.findByText('Session 1 synced.')).toBeVisible();
    expect(api.markDone).toHaveBeenCalledWith({ op_id: expect.any(String), session_id: S1 });
  });

  it('plan_conflict reads the plan again and sends the op once more', async () => {
    const markDone = vi
      .fn<FollowThroughApi['markDone']>()
      .mockResolvedValueOnce({ kind: 'plan_conflict' })
      .mockResolvedValue({ kind: 'done', planVersion: 4, replayed: false });
    const { getPlan } = await show(followApi({ markDone }));
    await userEvent.setup().click(within(session1()).getByRole('button', { name: 'Mark done' }));
    expect(await screen.findByText('Session 1 synced.')).toBeVisible();
    expect(getPlan).toHaveBeenCalledTimes(2);
    expect(markDone).toHaveBeenCalledTimes(2);
  });

  it('undo before the sync removes the queued op, with no request', async () => {
    const api = followApi();
    await show(api);
    online = false;
    const user = userEvent.setup();
    await user.click(within(session1()).getByRole('button', { name: 'Mark done' }));
    await within(session1()).findByText('Saved on this device, will sync');
    await user.click(within(session1()).getByRole('button', { name: 'Undo' }));
    expect(await within(session1()).findByRole('button', { name: 'Mark done' })).toBeVisible();
    expect(await outbox.pending()).toEqual([]);
    expect(api.undoDone).not.toHaveBeenCalled();
  });

  it('undo of a synced session calls the API', async () => {
    const body = planBody();
    (body.sessions as Record<string, unknown>[])[0]!.done = true;
    const api = followApi();
    await show(api, vi.fn(async (): Promise<PlanRead> => ({ kind: 'plan', plan: parsePlan(body) })));
    await userEvent.setup().click(within(session1()).getByRole('button', { name: 'Undo' }));
    expect(await within(session1()).findByRole('button', { name: 'Mark done' })).toBeVisible();
    expect(api.undoDone).toHaveBeenCalledWith(S1);
  });
});

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

describe('P-01 offline', () => {
  it('no plan on this device: says so, not the load error', async () => {
    online = false;
    render(
      <PlanView
        api={{ getPlan: vi.fn(async (): Promise<PlanRead> => ({ kind: 'error', supportRef: null })) }}
        followApi={followApi()}
        outbox={outbox}
      />,
    );
    expect(await screen.findByText('You are offline and this plan is not saved on this device yet.')).toBeVisible();
    expect(screen.queryByText('We could not load your plan. Try again.')).toBeNull();
  });

  it('the saved plan says when it is from; "Mark done" still works', async () => {
    online = false;
    const read: PlanRead = { kind: 'plan', plan: parsePlan(planBody()), offlineAsOf: '2026-10-18T09:30:00Z' };
    await show(followApi(), vi.fn(async () => read));
    expect(screen.getByText(/^You are offline\. This is your plan as of /)).toBeVisible();
    expect(within(session1()).getByRole('button', { name: 'Mark done' })).toBeEnabled();
    await act(async () => {
      await userEvent.setup().click(within(session1()).getByRole('button', { name: 'Mark done' }));
    });
    expect(await within(session1()).findByText('Saved on this device, will sync')).toBeVisible();
  });
});
