// The "Mark done" outbox (ST-063c; FR-124; flows-sprint-04 §4 P-03; api-sprint-04 §3.1). Coaching
// context, follow-through side: a `DoneOp` {op_id, session_id} is the player's "this session is
// done", kept on the device until the API has it. One op per session (pressing twice stores one);
// the sync replays it with the same op id, so a replay is idempotent on the server (ST-062).
// Framework-free: the store (IndexedDB, plan-outbox-idb.ts) and the sender (the HTTP client,
// plan-outbox-api.ts) are ports.

export interface DoneOp {
  op_id: string;
  session_id: string;
}

/** Ops by session id. */
export interface OutboxStore {
  get(sessionId: string): Promise<DoneOp | undefined>;
  put(op: DoneOp): Promise<void>;
  delete(sessionId: string): Promise<void>;
  all(): Promise<DoneOp[]>;
}

/**
 * The sender's answer for one op. The domain owns this port's result; the HTTP adapter
 * (plan-outbox-api.ts) maps each status to one of these.
 */
export type DoneResult =
  | { kind: 'done'; planVersion: number; replayed: boolean }
  | { kind: 'not_found' }
  | { kind: 'key_reused' }
  | { kind: 'plan_conflict' }
  | { kind: 'signed_out' }
  | { kind: 'failed'; supportRef: string | null };

export type SendDone = (op: DoneOp) => Promise<DoneResult>;

/** What one sync did, by session id. */
export interface SyncReport {
  /** The API has them (done or replayed): removed. */
  synced: string[];
  /** The session is no longer in the plan (404): removed, and the loss is shown. */
  dropped: string[];
  /** Still on the device for the next sync. */
  kept: string[];
  /** A 409 `plan_conflict`: read the plan again, then sync once more. */
  planChanged: boolean;
  /** A 401: nothing more was sent. */
  signedOut: boolean;
}

export interface Outbox {
  queueDone(sessionId: string): Promise<DoneOp>;
  cancel(sessionId: string): Promise<void>;
  pending(): Promise<DoneOp[]>;
  sync(send: SendDone): Promise<SyncReport>;
}

const randomOpId = () => globalThis.crypto.randomUUID();

export function createOutbox(store: OutboxStore, newOpId: () => string = randomOpId): Outbox {
  async function sendOne(op: DoneOp, send: SendDone, report: SyncReport): Promise<void> {
    let result = await send(op);
    if (result.kind === 'key_reused') {
      // The op id was used for another session (a client fault): a new id, sent once more.
      op = { op_id: newOpId(), session_id: op.session_id };
      await store.put(op);
      result = await send(op);
    }
    switch (result.kind) {
      case 'done':
        await store.delete(op.session_id);
        report.synced.push(op.session_id);
        return;
      case 'not_found':
        await store.delete(op.session_id);
        report.dropped.push(op.session_id);
        return;
      case 'plan_conflict':
        report.planChanged = true;
        break;
      case 'signed_out':
        report.signedOut = true;
        break;
      default:
        break;
    }
    report.kept.push(op.session_id);
  }

  // Writes from presses run one after another, so a double tap reads the op the first one stored.
  let writes: Promise<unknown> = Promise.resolve();
  function serial<T>(step: () => Promise<T>): Promise<T> {
    const next = writes.then(step, step);
    writes = next.catch(() => undefined);
    return next;
  }

  return {
    queueDone: (sessionId) =>
      serial(async () => {
        const queued = await store.get(sessionId);
        if (queued) return queued;
        const op = { op_id: newOpId(), session_id: sessionId };
        await store.put(op);
        return op;
      }),
    cancel: (sessionId) => serial(() => store.delete(sessionId)),
    pending: () => store.all(),
    async sync(send) {
      const report: SyncReport = { synced: [], dropped: [], kept: [], planChanged: false, signedOut: false };
      const ops = await store.all();
      for (const op of ops) {
        if (report.signedOut) {
          report.kept.push(op.session_id);
          continue;
        }
        await sendOne(op, send, report);
      }
      return report;
    },
  };
}

/** An outbox store in memory: for a browser without IndexedDB (the op lives until the page goes). */
export function memoryOutboxStore(): OutboxStore {
  const ops = new Map<string, DoneOp>();
  return {
    get: async (id) => ops.get(id),
    put: async (op) => void ops.set(op.session_id, op),
    delete: async (id) => void ops.delete(id),
    all: async () => [...ops.values()],
  };
}
