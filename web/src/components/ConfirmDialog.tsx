'use client';

// A confirmation dialog that states the consequences (X-01, X-02; flows-sprint-03 §0 "Dialogs";
// FR-006, FR-007; DES FR-UX-90; ADR 0043: no typed word). Modal (native <dialog>, so focus stays
// inside), labelled by its <h2>, focus on Cancel when it opens (the safe choice); Esc is Cancel.
// While the action runs the button says the busy words and ignores more presses; a failure is an
// alert inside the dialog and focus goes back to the action button, so one more press retries.
import { useEffect, useRef, useState, type ReactNode } from 'react';

export function ConfirmDialog({
  id,
  title,
  children,
  confirmLabel,
  busyLabel,
  onConfirm,
  onCancel,
}: {
  id: string;
  title: string;
  children: ReactNode;
  confirmLabel: string;
  busyLabel: string;
  /** Runs the action; resolves to a problem to show, or null when the page moves on. */
  onConfirm: () => Promise<string | null>;
  onCancel: () => void;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  const cancel = useRef<HTMLButtonElement>(null);
  const confirm = useRef<HTMLButtonElement>(null);
  const [busy, setBusy] = useState(false);
  const [problem, setProblem] = useState<string | null>(null);

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
    if (problem) confirm.current?.focus();
  }, [problem]);

  async function run() {
    if (busy) return;
    setBusy(true);
    setProblem(null);
    const why = await onConfirm();
    setBusy(false);
    if (why) setProblem(why);
  }

  return (
    <dialog
      ref={dialog}
      className="dialog"
      aria-labelledby={`${id}-title`}
      onCancel={(event) => {
        event.preventDefault();
        onCancel();
      }}
    >
      <div className="stack">
        <h2 id={`${id}-title`}>{title}</h2>
        {problem ? (
          <p role="alert" className="notice notice--error">
            {problem}
          </p>
        ) : null}
        {children}
        <div className="dialog__actions">
          <button ref={cancel} type="button" className="button button--secondary" onClick={onCancel}>
            Cancel
          </button>
          <button
            ref={confirm}
            type="button"
            className="button button--danger"
            aria-busy={busy}
            onClick={() => void run()}
          >
            {busy ? busyLabel : confirmLabel}
          </button>
        </div>
      </div>
    </dialog>
  );
}
