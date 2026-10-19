'use client';

// P-03 "Not for me" (ST-063c; FR-124; flows-sprint-04 §4; HAX G8, G15). `NotForMeDialog` is the
// swap dialog (native modal <dialog>, Cancel focused on open); `useOnline` keeps the buttons that
// need the server in step with the connection.
import { useEffect, useRef, useState, useSyncExternalStore } from 'react';
import type { SwapResult } from '@/lib/plan-outbox-api';
import { swapRateLimitMessage } from './PlanViewWords';

export const WORDS = {
  needsConnection: 'Needs a connection',
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
