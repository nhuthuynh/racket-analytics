'use client';

// X-00 "Delete your account" section and X-02 dialog (ST-051; FR-007, NFR-066; flows-sprint-03 §5).
// Only the dialog's button sends `{"confirm": "delete"}` to `DELETE /me` (api-sprint-03 §4.2).
// After 202 the device is cleared exactly as at sign-out (FR-UX-91), then X-03. Other devices
// get 401 on their next request and follow the existing signed-out path.
import { useEffect, useRef, useState } from 'react';
import { ApiError, type ApiClient } from '@/lib/api/client';
import { browserApi } from '@/lib/api/browser';
import { browserStores, clearClientData } from '@/lib/session/clear';
import { getActiveUpload } from '@/lib/upload/activity';
import { ConfirmDialog } from './ConfirmDialog';
import { deleteProblem } from './DeleteMatch';

function go(path: string) {
  window.location.replace(path);
}

function clearDevice() {
  return clearClientData(browserStores());
}

export function DeleteAccount({
  api = browserApi,
  navigate = go,
  clear = clearDevice,
}: {
  api?: Pick<ApiClient, 'deleteAccount'>;
  navigate?: (path: string) => void;
  clear?: () => Promise<void>;
}) {
  const [open, setOpen] = useState(false);
  const opener = useRef<HTMLButtonElement>(null);
  const wasOpen = useRef(false);
  useEffect(() => {
    if (!open && wasOpen.current) opener.current?.focus();
    wasOpen.current = open;
  }, [open]);

  async function confirm(): Promise<string | null> {
    try {
      await api.deleteAccount();
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) {
        navigate('/');
        return null;
      }
      return deleteProblem(e, 'Your account');
    }
    getActiveUpload()?.stop();
    await clear();
    navigate('/signed-out?deleted=1');
    return null;
  }

  return (
    <section className="stack delete-section" aria-labelledby="delete-account-title">
      <h2 id="delete-account-title">Delete your account</h2>
      <p>This deletes your account and all your matches.</p>
      <p>
        <button ref={opener} type="button" className="button button--danger" onClick={() => setOpen(true)}>
          Delete my account
        </button>
      </p>
      {open ? (
        <ConfirmDialog
          id="delete-account-dialog"
          title="Delete your account?"
          confirmLabel="Delete my account"
          busyLabel="Deleting…"
          onConfirm={confirm}
          onCancel={() => setOpen(false)}
        >
          <ul className="consequences">
            <li>This deletes your account and all your matches: every video, tag, score sheet and stat.</li>
            <li>You will be signed out on every device.</li>
            <li>It cannot be undone.</li>
            <li>Stored files are removed within 7 days.</li>
            <li>If you sign in again with the same email address, you start with a new, empty account.</li>
          </ul>
        </ConfirmDialog>
      ) : null}
    </section>
  );
}
