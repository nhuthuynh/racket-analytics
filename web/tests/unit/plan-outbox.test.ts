// The "Mark done" outbox (ST-063c; FR-124; flows-sprint-04 §4 P-03; api-sprint-04 §3.1). An op
// {op_id, session_id} is kept in IndexedDB (fake-indexeddb here) until the API has it; the sync
// replays it with the same op id, so a replay is idempotent (ST-062). Negative first: a sync that
// fails keeps the op.
import 'fake-indexeddb/auto';
import { IDBFactory } from 'fake-indexeddb';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { createOutbox, type DoneOp, type SendDone } from '@/lib/plan-outbox';
import { idbOutboxStore } from '@/lib/plan-outbox-idb';
import { clearClientData } from '@/lib/session/clear';

const S1 = '00000000-0000-4000-8000-000000000010';
const S2 = '00000000-0000-4000-8000-000000000011';

let factory: IDBFactory;
let ids: number;

function outbox() {
  return createOutbox(idbOutboxStore(factory), () => `op-${++ids}`);
}

beforeEach(() => {
  factory = new IDBFactory();
  ids = 0;
});

describe('plan outbox (negative first)', () => {
  it('a sync that fails keeps the op, with the same op id, for the next sync', async () => {
    const box = outbox();
    await box.queueDone(S1);
    const send = vi.fn<SendDone>(async () => ({ kind: 'failed', supportRef: null }));
    const report = await box.sync(send);
    expect(report).toMatchObject({ synced: [], dropped: [], kept: [S1] });
    expect(await outbox().pending()).toEqual([{ op_id: 'op-1', session_id: S1 }]);
  });

  it('a signed-out answer keeps every op and stops the sync', async () => {
    const box = outbox();
    await box.queueDone(S1);
    await box.queueDone(S2);
    const send = vi.fn<SendDone>(async () => ({ kind: 'signed_out' }));
    const report = await box.sync(send);
    expect(send).toHaveBeenCalledTimes(1);
    expect(report.signedOut).toBe(true);
    expect((await box.pending()).map((o) => o.session_id).sort()).toEqual([S1, S2]);
  });

  it('pressing "Mark done" twice for one session stores one op', async () => {
    const box = outbox();
    const first = await box.queueDone(S1);
    const second = await box.queueDone(S1);
    expect(second).toEqual(first);
    expect(await box.pending()).toEqual([{ op_id: 'op-1', session_id: S1 }]);
  });

  it('two presses at once (a double tap) store one op and both get it', async () => {
    const box = outbox();
    const [a, b] = await Promise.all([box.queueDone(S1), box.queueDone(S1)]);
    expect(b).toEqual(a);
    expect(await box.pending()).toEqual([a]);
  });

  it('the op survives a new page (a new outbox on the same IndexedDB)', async () => {
    await outbox().queueDone(S1);
    expect(await outbox().pending()).toEqual([{ op_id: 'op-1', session_id: S1 }]);
  });

  it('undo before the sync removes the queued op', async () => {
    const box = outbox();
    await box.queueDone(S1);
    await box.cancel(S1);
    expect(await box.pending()).toEqual([]);
  });

  it('a synced op is removed and reported', async () => {
    const box = outbox();
    await box.queueDone(S1);
    const sent: DoneOp[] = [];
    const report = await box.sync(async (op) => {
      sent.push(op);
      return { kind: 'done', planVersion: 2, replayed: false };
    });
    expect(sent).toEqual([{ op_id: 'op-1', session_id: S1 }]);
    expect(report).toMatchObject({ synced: [S1], kept: [], dropped: [], planChanged: false });
    expect(await box.pending()).toEqual([]);
  });

  it('a replayed answer counts as synced (idempotent, ST-062)', async () => {
    const box = outbox();
    await box.queueDone(S1);
    const report = await box.sync(async () => ({ kind: 'done', planVersion: 2, replayed: true }));
    expect(report.synced).toEqual([S1]);
  });

  it('a session no longer in the plan (404) drops the op and reports it', async () => {
    const box = outbox();
    await box.queueDone(S1);
    const report = await box.sync(async () => ({ kind: 'not_found' }));
    expect(report).toMatchObject({ synced: [], dropped: [S1], kept: [] });
    expect(await box.pending()).toEqual([]);
  });

  it('plan_conflict keeps the op and says the plan changed', async () => {
    const box = outbox();
    await box.queueDone(S1);
    const report = await box.sync(async () => ({ kind: 'plan_conflict' }));
    expect(report).toMatchObject({ kept: [S1], planChanged: true });
    expect(await box.pending()).toEqual([{ op_id: 'op-1', session_id: S1 }]);
  });

  it('idempotency_key_reused gives the op a new op id and sends it once more', async () => {
    const box = outbox();
    await box.queueDone(S1);
    const send = vi
      .fn<SendDone>()
      .mockResolvedValueOnce({ kind: 'key_reused' })
      .mockResolvedValueOnce({ kind: 'done', planVersion: 3, replayed: false });
    const report = await box.sync(send);
    expect(send.mock.calls.map(([op]) => op.op_id)).toEqual(['op-1', 'op-2']);
    expect(report.synced).toEqual([S1]);
  });

  it('a second idempotency_key_reused keeps the op under its new id', async () => {
    const box = outbox();
    await box.queueDone(S1);
    const report = await box.sync(async () => ({ kind: 'key_reused' }));
    expect(report.kept).toEqual([S1]);
    expect(await box.pending()).toEqual([{ op_id: 'op-2', session_id: S1 }]);
  });
});

describe('plan outbox and sign-out (NFR-067)', () => {
  it('sign-out is not blocked by an open outbox and leaves no op behind', async () => {
    const box = outbox();
    await box.queueDone(S1);
    const outcome = await new Promise<string>((resolve) => {
      const request = factory.deleteDatabase('ra-plan-outbox');
      request.onsuccess = () => resolve('success');
      request.onerror = () => resolve('error');
      request.onblocked = () => resolve('blocked');
    });
    expect(outcome).toBe('success');
    expect(await outbox().pending()).toEqual([]);
  });

  it('clearClientData wipes a queued op while the outbox that stored it is still open', async () => {
    const box = outbox();
    await box.queueDone(S1);
    await clearClientData({ indexedDB: factory });
    expect(await box.pending()).toEqual([]);
    expect(await outbox().pending()).toEqual([]);
  });
});
