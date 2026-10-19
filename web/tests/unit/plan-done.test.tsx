// P-03 on P-01 (ST-063c; FR-124; flows-sprint-04 §4): "Mark done" through the outbox, "Undo" and the
// offline P-01 state ("Not for me": plan-not-for-me.test.tsx). Negative first: a "done" that cannot be sent is
// kept and said so; never shown as synced.
import 'fake-indexeddb/auto';
import { IDBFactory } from 'fake-indexeddb';
import { act, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { browserOutbox } from '@/components/plan/PlanFollowThrough';
import { PlanView } from '@/components/plan/PlanView';
import { parsePlan, type PlanRead } from '@/lib/api/plan';
import { createOutbox, type Outbox } from '@/lib/plan-outbox';
import { idbOutboxStore } from '@/lib/plan-outbox-idb';
import type { FollowThroughApi } from '@/lib/plan-outbox-api';
import { planBody } from './fixtures/plan';

const S1 = '00000000-0000-4000-8000-000000000010';
let online: boolean;
let outbox: Outbox;

beforeEach(() => {
  online = true;
  vi.spyOn(navigator, 'onLine', 'get').mockImplementation(() => online);
  outbox = createOutbox(idbOutboxStore(new IDBFactory()));
});
afterEach(() => vi.unstubAllGlobals());

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

// Undo of a synced session refused by the server (review #146 M1): never shown as undone.
describe('Undo refused (negative first)', () => {
  async function undoWith(result: Awaited<ReturnType<FollowThroughApi['undoDone']>>) {
    const body = planBody();
    (body.sessions as Record<string, unknown>[])[0]!.done = true;
    const api = followApi({ undoDone: vi.fn(async () => result) });
    const getPlan = vi.fn(async (): Promise<PlanRead> => ({ kind: 'plan', plan: parsePlan(body) }));
    const onSignedOut = vi.fn();
    render(
      <PlanView
        api={{ getPlan }}
        followApi={api}
        outbox={outbox}
        onSignedOut={onSignedOut}
        evidenceApi={{ stats: vi.fn(), evidence: vi.fn() }}
      />,
    );
    await screen.findByText('Serve to a target');
    await userEvent.setup().click(within(session1()).getByRole('button', { name: 'Undo' }));
    await waitFor(() => expect(api.undoDone).toHaveBeenCalledWith(S1));
    return { getPlan, onSignedOut };
  }

  it('failed: says it could not undo and the session stays done', async () => {
    await undoWith({ kind: 'failed', supportRef: null });
    expect(await within(session1()).findByRole('alert')).toHaveTextContent("We could not undo 'done'. Try again.");
    expect(within(session1()).getByText('Done')).toBeVisible();
    expect(within(session1()).queryByRole('button', { name: 'Mark done' })).toBeNull();
  });

  it('signed out: hands over to sign-in, no error shown', async () => {
    const { onSignedOut } = await undoWith({ kind: 'signed_out' });
    await waitFor(() => expect(onSignedOut).toHaveBeenCalledTimes(1));
    expect(within(session1()).queryByRole('alert')).toBeNull();
  });

  it('session gone: says so and reads the plan again', async () => {
    const { getPlan } = await undoWith({ kind: 'not_found' });
    expect(
      await screen.findByText("We could not save 'done' for a session that is no longer in your plan."),
    ).toBeVisible();
    await waitFor(() => expect(getPlan).toHaveBeenCalledTimes(2));
  });

  it('plan changed: reads the plan again and says it changed', async () => {
    const { getPlan } = await undoWith({ kind: 'plan_conflict' });
    expect(await screen.findByText('Your plan changed on another device. Showing your current plan.')).toBeVisible();
    expect(getPlan).toHaveBeenCalledTimes(2);
    expect(within(session1()).queryByRole('alert')).toBeNull();
  });
});

// IndexedDB fails late: the store opens lazily, so a blocked store (open throws SecurityError), a
// failing open request or a disabled one (null) only shows on the first operation (review M1/F1).
const throwingOpen = {
  open: () => {
    throw new DOMException('blocked', 'SecurityError');
  },
} as unknown as IDBFactory;
const failingOpen = {
  open: () => {
    const request = { error: new DOMException('broken', 'UnknownError') } as unknown as IDBOpenDBRequest;
    setTimeout(() => request.onerror?.(new Event('error')));
    return request;
  },
} as unknown as IDBFactory;

describe('IndexedDB unavailable: the outbox falls back to memory (negative first)', () => {
  it.each([
    ['open throws', throwingOpen],
    ['open fails', failingOpen],
    ['indexedDB is null', null],
  ])('%s: ops are still queued, listed and cancelled', async (_, factory) => {
    vi.stubGlobal('indexedDB', factory);
    const box = browserOutbox();
    expect(await box.pending()).toEqual([]);
    await box.queueDone(S1);
    expect((await box.pending()).map((o) => o.session_id)).toEqual([S1]);
    await box.cancel(S1);
    expect(await box.pending()).toEqual([]);
  });

  it('offline, "Mark done" still says it will sync', async () => {
    vi.stubGlobal('indexedDB', throwingOpen);
    outbox = browserOutbox();
    await show(followApi());
    online = false;
    await userEvent.setup().click(within(session1()).getByRole('button', { name: 'Mark done' }));
    expect(await within(session1()).findByText('Saved on this device, will sync')).toBeVisible();
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

  it('offline, "Show me" and "Change my setup" need a connection', async () => {
    online = false;
    await show(followApi());
    expect(screen.getByRole('button', { name: /^Show me the rallies behind Serve faults/ })).toBeDisabled();
    expect(screen.queryByRole('link', { name: 'Change my setup' })).toBeNull();
    expect(screen.getAllByText('Needs a connection').length).toBeGreaterThan(1);
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
