// ST-085 (FR-124.R4): the page's sync queue (usePlanFollowThrough over the outbox) sends a session
// marked done offline exactly once after the connection returns, also when the connection drops
// and returns again while the first send is still in flight. Negative first.
import { act, renderHook, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { usePlanFollowThrough } from '@/components/plan/PlanFollowThrough';
import { createOutbox, memoryOutboxStore, type DoneResult } from '@/lib/plan-outbox';
import type { FollowThroughApi } from '@/lib/plan-outbox-api';

const S1 = '00000000-0000-4000-8000-000000000010';
let online: boolean;

beforeEach(() => {
  online = true;
  vi.spyOn(navigator, 'onLine', 'get').mockImplementation(() => online);
});

function connection(up: boolean) {
  online = up;
  act(() => {
    window.dispatchEvent(new Event(up ? 'online' : 'offline'));
  });
}

/** The hook with a "Mark done" sender whose answers the test lets go. */
function queue() {
  const answers: (() => void)[] = [];
  const done: DoneResult = { kind: 'done', planVersion: 2, replayed: false };
  const markDone = vi.fn(() => new Promise<DoneResult>((resolve) => answers.push(() => resolve(done))));
  const api: FollowThroughApi = { markDone, undoDone: vi.fn(), swap: vi.fn() };
  const outbox = createOutbox(memoryOutboxStore());
  // Stable props, as PlanView passes them: a new `reload` each render would restart the page-load sync.
  const props = { outbox, api, sessionIndex: () => 1, reload: vi.fn(async () => undefined), onSignedOut: vi.fn() };
  const hook = renderHook(() => usePlanFollowThrough(props));
  const answerAll = () => act(async () => void answers.splice(0).forEach((a) => a()));
  return { hook, markDone, outbox, answerAll };
}

async function markDoneOffline(q: ReturnType<typeof queue>) {
  connection(false);
  await act(() => q.hook.result.current.markDone(S1));
  expect(q.hook.result.current.pending.has(S1)).toBe(true);
  expect(q.markDone).not.toHaveBeenCalled();
}

describe('FR-124.R4 sync once (negative first)', () => {
  it('drop and return twice while the first send is in flight: still one request', async () => {
    const q = queue();
    await markDoneOffline(q);
    connection(true);
    await waitFor(() => expect(q.markDone).toHaveBeenCalledTimes(1));
    connection(false);
    connection(true);
    await q.answerAll();
    await q.answerAll(); // a second send, if one was made, is answered too
    await waitFor(() => expect(q.hook.result.current.doneNow[S1]).toBe(true));
    expect(q.markDone).toHaveBeenCalledTimes(1);
    expect(await q.outbox.pending()).toEqual([]);
  });

  it('two "online" events in a row before the queue drains: one request', async () => {
    const q = queue();
    await markDoneOffline(q);
    connection(true);
    connection(true);
    await q.answerAll();
    await q.answerAll();
    await waitFor(() => expect(q.hook.result.current.doneNow[S1]).toBe(true));
    expect(q.markDone).toHaveBeenCalledTimes(1);
  });

  it('one session marked done offline: one request once the connection returns, then done', async () => {
    const q = queue();
    await markDoneOffline(q);
    connection(true);
    await waitFor(() => expect(q.markDone).toHaveBeenCalledTimes(1));
    expect(q.markDone.mock.calls[0]![0]).toMatchObject({ session_id: S1 });
    await q.answerAll();
    await waitFor(() => expect(q.hook.result.current.doneNow[S1]).toBe(true));
    expect(q.hook.result.current.pending.has(S1)).toBe(false);
    expect(q.markDone).toHaveBeenCalledTimes(1);
  });
});
