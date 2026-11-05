'use client';

// P-03 Mark done (offline) and "Not for me" (ST-063c; FR-124; flows-sprint-04 §4; HAX G8, G15).
// `usePlanFollowThrough` keeps the outbox in step with the page: a press queues a `DoneOp`, the
// sync runs at once when online, on the `online` event and on page load, and its report becomes
// the row texts and one polite status. `SessionDone` is a session's "Mark done"/"Done"/"Undo";
// `NotForMeDialog` is the swap dialog (native modal <dialog>, Cancel focused on open).
import { useCallback, useEffect, useRef, useState, useSyncExternalStore } from 'react';
import type { Session } from '@/lib/api/plan';
import { createOutbox, memoryOutboxStore, type Outbox, type OutboxStore } from '@/lib/plan-outbox';
import type { FollowThroughApi, SwapResult } from '@/lib/plan-outbox-api';
import { idbOutboxStore } from '@/lib/plan-outbox-idb';
import { swapRateLimitMessage } from './PlanViewWords';

export const WORDS = {
  queued: 'Saved on this device, will sync',
  sendFailed: "We could not save 'done'. It stays on this device and will sync.",
  dropped: "We could not save 'done' for a session that is no longer in your plan.",
  undoFailed: "We could not undo 'done'. Try again.",
  needsConnection: 'Needs a connection',
  synced: (index: number) => `Session ${index} synced.`,
  swapped: (name: string) => `Swapped for ${name}.`,
} as const;

function subscribe(onChange: () => void) {
  window.addEventListener('online', onChange);
  window.addEventListener('offline', onChange);
  return () => {
    window.removeEventListener('online', onChange);
    window.removeEventListener('offline', onChange);
  };
}

/** navigator.onLine, kept current by the `online`/`offline` events. */
export function useOnline(): boolean {
  return useSyncExternalStore(subscribe, () => navigator.onLine, () => true);
}

/**
 * `primary` until one of its calls fails, then `fallback` for the rest of the page, the failed call
 * included. IndexedDB opens lazily, so a blocked, disabled or broken one only fails here.
 */
function failOver(primary: OutboxStore, fallback: OutboxStore): OutboxStore {
  let failed = false;
  async function attempt<T>(act: (s: OutboxStore) => Promise<T>): Promise<T> {
    if (!failed) {
      try {
        return await act(primary);
      } catch {
        failed = true;
      }
    }
    return act(fallback);
  }
  return {
    get: (id) => attempt((s) => s.get(id)),
    put: (op) => attempt((s) => s.put(op)),
    delete: (id) => attempt((s) => s.delete(id)),
    all: () => attempt((s) => s.all()),
  };
}

/** The device's outbox: IndexedDB while it works, else memory (lost with the page). */
export function browserOutbox(): Outbox {
  const memory = memoryOutboxStore();
  const idb = typeof indexedDB !== 'undefined' && indexedDB ? idbOutboxStore(indexedDB) : null;
  return createOutbox(idb ? failOver(idb, memory) : memory);
}

const without = (set: ReadonlySet<string>, ids: readonly string[]) => new Set([...set].filter((x) => !ids.includes(x)));

export interface FollowThrough {
  pending: ReadonlySet<string>;
  sendFailed: ReadonlySet<string>;
  /** Done marks the server has confirmed (true) or undone (false) since the plan was read. */
  doneNow: Readonly<Record<string, boolean>>;
  undoFailed: string | null;
  status: string | null;
  dropped: boolean;
  markDone(sessionId: string): Promise<void>;
  undo(sessionId: string, serverDone: boolean): Promise<void>;
  /** Sets the polite status; null clears it (a new swap starts clean). */
  say(status: string | null): void;
}

export function usePlanFollowThrough({
  outbox,
  api,
  sessionIndex,
  reload,
  onSignedOut,
}: {
  outbox: Outbox;
  api: FollowThroughApi;
  /** The session's number on the page ("Session 2"), or null when it is not in the plan. */
  sessionIndex: (sessionId: string) => number | null;
  /** Reads the plan again; `changed` adds the polite "plan changed" status. */
  reload: (changed: boolean) => Promise<void>;
  onSignedOut: () => void;
}): FollowThrough {
  const [pending, setPending] = useState<ReadonlySet<string>>(new Set());
  const [sendFailed, setSendFailed] = useState<ReadonlySet<string>>(new Set());
  const [doneNow, setDoneNow] = useState<Record<string, boolean>>({});
  const [undoFailed, setUndoFailed] = useState<string | null>(null);
  const [status, setStatus] = useState<string | null>(null);
  const [dropped, setDropped] = useState(false);
  const syncing = useRef(false);
  const again = useRef(false);
  /** Ops sent by a press while online: "Done" at once, no "synced" status. */
  const direct = useRef(new Set<string>());
  const index = useRef(sessionIndex);
  index.current = sessionIndex;
  const readAgain = useCallback(
    async (changed: boolean) => {
      await reload(changed);
      setDoneNow({}); // the plan just read is the truth now
    },
    [reload],
  );

  const sync = useCallback(
    async function run(afterReload = false): Promise<void> {
      if (!navigator.onLine) return;
      if (syncing.current) {
        again.current = true;
        return;
      }
      syncing.current = true;
      let retry = false;
      try {
        const report = await outbox.sync(api.markDone);
        const settled = [...report.synced, ...report.dropped];
        setPending((p) => without(p, settled));
        setSendFailed((f) => {
          const next = without(f, settled);
          if (!report.planChanged && !report.signedOut) report.kept.forEach((id) => next.add(id));
          return next;
        });
        if (report.synced.length > 0) {
          setDoneNow((d) => ({ ...d, ...Object.fromEntries(report.synced.map((id) => [id, true])) }));
          const told = report.synced.filter((id) => !direct.current.has(id));
          const n = told.map((id) => index.current(id)).find((x) => x !== null);
          if (n !== undefined && n !== null) setStatus(WORDS.synced(n));
        }
        report.synced.forEach((id) => direct.current.delete(id));
        if (report.signedOut) onSignedOut();
        else if (report.dropped.length > 0) {
          setDropped(true);
          await readAgain(false);
        } else if (report.planChanged && !afterReload) {
          report.kept.forEach((id) => direct.current.delete(id));
          await readAgain(true);
          retry = true;
        }
      } finally {
        syncing.current = false;
      }
      if (retry) await run(true);
      else if (again.current) {
        again.current = false;
        await run();
      }
    },
    [outbox, api, readAgain, onSignedOut],
  );

  // Page load: what an earlier visit left on the device, then one sync; and every reconnect.
  useEffect(() => {
    let live = true;
    void outbox.pending().then((ops) => {
      if (!live) return;
      setPending(new Set(ops.map((o) => o.session_id)));
      void sync();
    });
    const onOnline = () => void sync();
    window.addEventListener('online', onOnline);
    return () => {
      live = false;
      window.removeEventListener('online', onOnline);
    };
  }, [outbox, sync]);

  return {
    pending,
    sendFailed,
    doneNow,
    undoFailed,
    status,
    dropped,
    say: setStatus,
    async markDone(sessionId) {
      setUndoFailed(null);
      await outbox.queueDone(sessionId);
      setPending((p) => new Set(p).add(sessionId));
      if (navigator.onLine) {
        direct.current.add(sessionId);
        await sync();
      }
    },
    async undo(sessionId, serverDone) {
      setUndoFailed(null);
      if (pending.has(sessionId)) {
        await outbox.cancel(sessionId);
        setPending((p) => without(p, [sessionId]));
        setSendFailed((f) => without(f, [sessionId]));
        if (!serverDone) return;
      }
      const r = await api.undoDone(sessionId);
      if (r.kind === 'undone') setDoneNow((d) => ({ ...d, [sessionId]: false }));
      else if (r.kind === 'signed_out') onSignedOut();
      else if (r.kind === 'not_found') {
        setDropped(true);
        await readAgain(false);
      } else if (r.kind === 'plan_conflict') await readAgain(true);
      else setUndoFailed(sessionId);
    },
  };
}

/** "Mark done" / "Saved on this device, will sync" / "Done" with "Undo" for one session. */
export function SessionDone({
  session,
  follow,
  online,
}: {
  session: Session;
  follow: FollowThrough;
  online: boolean;
}) {
  const id = session.id;
  const serverDone = follow.doneNow[id] ?? session.done;
  const queued = follow.pending.has(id);
  if (!queued && !serverDone) {
    return (
      <p>
        <button type="button" className="button" onClick={() => void follow.markDone(id)}>
          Mark done
        </button>
      </p>
    );
  }
  const canUndo = queued || online;
  return (
    <div className="stack">
      <p>
        <span aria-hidden="true">✓ </span>
        {queued ? (
          <span>{follow.sendFailed.has(id) ? WORDS.sendFailed : WORDS.queued}</span>
        ) : (
          <strong>Done</strong>
        )}
      </p>
      <p>
        <button
          type="button"
          className="button button--secondary"
          disabled={!canUndo}
          onClick={() => void follow.undo(id, serverDone)}
        >
          Undo
        </button>
        {canUndo ? null : <span>{` ${WORDS.needsConnection}`}</span>}
      </p>
      {follow.undoFailed === id ? (
        <p role="alert" className="notice notice--error">
          {WORDS.undoFailed}
        </p>
      ) : null}
    </div>
  );
}

const REASON_MAX = 200;

type Problem =
  | { kind: 'no_alternative' | 'session_done' | 'plan_conflict' }
  | { kind: 'failed'; supportRef: string | null }
  | { kind: 'rate_limited'; retryAt: string | null };

/** The dialog stays open with the form (and the reason) for these; the others close it. */
const KEEPS_FORM: ReadonlySet<Problem['kind']> = new Set(['failed', 'rate_limited']);

const PROBLEM_TEXT: Record<Exclude<Problem['kind'], 'rate_limited'>, string> = {
  no_alternative: 'No other drill fits your setup for this. Your plan is unchanged.',
  session_done: 'This session is already done, so its drills cannot be swapped. Your plan is unchanged.',
  plan_conflict: 'Your plan changed on another device. Nothing was swapped.',
  failed: 'We could not swap the drill. Try again.',
};

/** P-03 "Not for me": swap a drill for another that works on the same thing (FR-124). */
export function NotForMeDialog({
  id,
  drillName,
  onSwap,
  onClose,
}: {
  id: string;
  drillName: string;
  onSwap: (reason: string) => Promise<SwapResult>;
  /** Closes the dialog; `reload` when the plan must be read again (session done, plan changed). */
  onClose: (reload: boolean) => void;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  const cancel = useRef<HTMLButtonElement>(null);
  const alert = useRef<HTMLDivElement>(null);
  const [reason, setReason] = useState('');
  const [busy, setBusy] = useState(false);
  const [problem, setProblem] = useState<Problem | null>(null);
  const online = useOnline();

  useEffect(() => {
    const d = dialog.current;
    if (d && typeof d.showModal === 'function' && !d.open) d.showModal();
    else d?.setAttribute('open', '');
    cancel.current?.focus();
    return () => {
      if (d?.open && typeof d.close === 'function') d.close();
    };
  }, []);

  useEffect(() => {
    if (problem) alert.current?.focus();
  }, [problem]);

  async function swap() {
    if (busy) return;
    setBusy(true);
    setProblem(null);
    const r = await onSwap(reason);
    setBusy(false);
    if (r.kind === 'no_alternative' || r.kind === 'session_done' || r.kind === 'plan_conflict') setProblem({ kind: r.kind });
    else if (r.kind === 'failed' || r.kind === 'rate_limited') setProblem(r);
  }

  const closing = problem && !KEEPS_FORM.has(problem.kind);
  return (
    <dialog
      ref={dialog}
      className="dialog"
      aria-labelledby={`${id}-title`}
      onCancel={(event) => {
        event.preventDefault();
        onClose(problem?.kind === 'session_done' || problem?.kind === 'plan_conflict');
      }}
    >
      <div className="stack">
        <h2 id={`${id}-title`}>{`Swap ${drillName}?`}</h2>
        {problem ? (
          <div ref={alert} role="alert" tabIndex={-1} className="notice notice--error">
            <p>{problem.kind === 'rate_limited' ? swapRateLimitMessage(problem.retryAt) : PROBLEM_TEXT[problem.kind]}</p>
            {problem.kind === 'failed' && problem.supportRef ? <p>{`Reference: ${problem.supportRef}`}</p> : null}
          </div>
        ) : null}
        {closing ? (
          <div className="dialog__actions">
            <button type="button" className="button" onClick={() => onClose(problem.kind !== 'no_alternative')}>
              {problem.kind === 'plan_conflict' ? 'Reload plan' : 'Close'}
            </button>
          </div>
        ) : (
          <>
            <p>We will pick another drill that works on the same thing and fits your session.</p>
            <p>
              <label htmlFor={`${id}-reason`}>Why not? (optional)</label>
            </p>
            <textarea
              id={`${id}-reason`}
              className="input"
              maxLength={REASON_MAX}
              rows={3}
              value={reason}
              aria-describedby={`${id}-count`}
              onChange={(e) => setReason(e.target.value)}
            />
            <p id={`${id}-count`}>{`${reason.length} of ${REASON_MAX} characters`}</p>
            <div className="dialog__actions">
              <button ref={cancel} type="button" className="button button--secondary" onClick={() => onClose(false)}>
                Cancel
              </button>
              <button
                type="button"
                className="button"
                aria-busy={busy}
                aria-describedby={online ? undefined : `${id}-offline`}
                disabled={busy || !online}
                onClick={() => void swap()}
              >
                {busy ? 'Swapping…' : 'Swap drill'}
              </button>
            </div>
            {online ? null : <p id={`${id}-offline`}>{WORDS.needsConnection}</p>}
          </>
        )}
      </div>
    </dialog>
  );
}
