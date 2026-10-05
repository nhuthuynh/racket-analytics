'use client';

// Key map K-01 (ST-028a; FR-051; DES FR-UX-61): every tagging shortcut and what it does, and
// the switch that turns single-key shortcuts off (SC 2.1.4). A modal dialog: focus moves to it
// on open and back to the control that opened it on close (component checklist, dialogs).
import { useEffect, useRef } from 'react';
import { keyMapRows } from '@/lib/tagging/keymap';

export function KeyMapDialog({
  playerNames,
  singleKeys,
  onSingleKeys,
  onClose,
}: {
  playerNames: readonly string[];
  singleKeys: boolean;
  onSingleKeys: (on: boolean) => void;
  onClose: () => void;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  const close = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    const d = dialog.current;
    if (d && typeof d.showModal === 'function' && !d.open) d.showModal();
    else d?.setAttribute('open', '');
    close.current?.focus();
  }, []);

  return (
    <dialog
      ref={dialog}
      className="dialog"
      aria-labelledby="key-map-title"
      onCancel={(event) => {
        event.preventDefault();
        onClose();
      }}
    >
      <div className="stack">
        <h2 id="key-map-title">Keyboard shortcuts</h2>
        <table className="key-map">
          <caption className="visually-hidden">Tagging shortcuts</caption>
          <thead>
            <tr>
              <th scope="col">Key</th>
              <th scope="col">What it does</th>
            </tr>
          </thead>
          <tbody>
            {keyMapRows(playerNames).map((row) => (
              <tr key={row.key}>
                <th scope="row">
                  <kbd>{row.key}</kbd>
                </th>
                <td>{row.does}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <div className="choice">
          <input
            id="single-keys"
            type="checkbox"
            checked={singleKeys}
            aria-describedby="single-keys-hint"
            onChange={(e) => onSingleKeys(e.target.checked)}
          />
          <label htmlFor="single-keys">Use single-key shortcuts</label>
        </div>
        <p id="single-keys-hint" className="field__hint">
          When this is off, only Space and Esc work as shortcuts. You can still tag with Tab and Enter.
        </p>
        <div className="dialog__actions">
          <button ref={close} type="button" className="button" onClick={onClose}>
            Close
          </button>
        </div>
      </div>
    </dialog>
  );
}
