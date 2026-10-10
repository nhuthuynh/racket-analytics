'use client';

// L-02 Full Tag keys (ST-052; flows-sprint-03 §6; DR-03 R3-8 FE amendments): the key list and the
// single-key switch of SC 2.1.4. A modal dialog: focus on Close when it opens, back to the
// opener on close (component checklist, dialogs). Keys are matched by KeyboardEvent.key, so
// "<" and ">" are listed as such (Shift+, is "<" only on some layouts).
import { useEffect, useRef } from 'react';

export const FULL_TAG_KEYS: readonly { key: string; does: string }[] = [
  { key: ',', does: 'Previous frame' },
  { key: '.', does: 'Next frame' },
  { key: '<', does: 'Back 1 second' },
  { key: '>', does: 'Forward 1 second' },
  { key: 'Space', does: 'Play or pause' },
  { key: 'S', does: 'Rally start' },
  { key: 'E', does: 'Rally end' },
  { key: 'H', does: 'Hit' },
  { key: 'B', does: 'Bounce' },
  { key: '1', does: 'Won by your side' },
  { key: '2', does: 'Won by the other side' },
  { key: '3 to 6', does: 'Players, in slot order (who hit it, or who ended the rally)' },
  { key: 'Esc', does: 'Drop the unsaved rally (asks first)' },
  { key: '?', does: 'This list' },
];

export function FullTagKeys({
  singleKeys,
  onSingleKeys,
  onClose,
}: {
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
    return () => {
      if (d?.open && typeof d.close === 'function') d.close();
    };
  }, []);

  return (
    <dialog
      ref={dialog}
      className="dialog"
      aria-labelledby="full-tag-keys-title"
      onCancel={(event) => {
        event.preventDefault();
        onClose();
      }}
    >
      <div className="stack">
        <h2 id="full-tag-keys-title">Full Tag keys</h2>
        <table className="key-table">
          <caption className="visually-hidden">Keys and what they do</caption>
          <thead>
            <tr>
              <th scope="col">Key</th>
              <th scope="col">Does</th>
            </tr>
          </thead>
          <tbody>
            {FULL_TAG_KEYS.map((k) => (
              <tr key={k.key}>
                <th scope="row">
                  <kbd>{k.key}</kbd>
                </th>
                <td>{k.does}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <p className="checkbox">
          <input
            id="full-tag-single-keys"
            type="checkbox"
            checked={singleKeys}
            onChange={(e) => onSingleKeys(e.currentTarget.checked)}
          />
          <label htmlFor="full-tag-single-keys">Use single-key shortcuts</label>
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
