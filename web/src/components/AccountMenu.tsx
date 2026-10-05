'use client';

// Account menu with "Sign out" (ST-014; flows-sprint-01 §2 "Sign-out and A-05"; FR-011).
// Sign-out always clears the device, even if the server cannot be reached, then opens A-05 with
// a full page load so no in-memory page data survives. While an upload runs in this tab, the
// user is asked first ("Your upload will stop"), with "Keep uploading" focused.
import { useEffect, useRef, useState, useSyncExternalStore } from 'react';
import Link from 'next/link';
import type { ApiClient } from '@/lib/api/client';
import { browserApi } from '@/lib/api/browser';
import { browserStores, clearClientData } from '@/lib/session/clear';
import { getActiveUpload, subscribeActiveUpload } from '@/lib/upload/activity';

type Api = Pick<ApiClient, 'signOut'>;

function defaultNavigate(path: string) {
  window.location.replace(path);
}

function defaultClear() {
  return clearClientData(browserStores());
}

export function AccountMenu({
  api = browserApi,
  navigate = defaultNavigate,
  clear = defaultClear,
}: {
  api?: Api;
  navigate?: (path: string) => void;
  clear?: () => Promise<void>;
}) {
  const [open, setOpen] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [signingOut, setSigningOut] = useState(false);
  const upload = useSyncExternalStore(subscribeActiveUpload, getActiveUpload, () => null);
  const menu = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setOpen(false);
    };
    const onPointer = (event: PointerEvent) => {
      if (!menu.current?.contains(event.target as Node)) setOpen(false);
    };
    document.addEventListener('keydown', onKey);
    document.addEventListener('pointerdown', onPointer);
    return () => {
      document.removeEventListener('keydown', onKey);
      document.removeEventListener('pointerdown', onPointer);
    };
  }, [open]);

  async function signOut() {
    if (signingOut) return;
    setSigningOut(true);
    getActiveUpload()?.stop();
    let reached = true;
    try {
      await api.signOut();
    } catch {
      reached = false; // the session ends on its own (api-sprint-01 §2.3 lifetimes)
    }
    await clear();
    navigate(reached ? '/signed-out' : '/signed-out?server=unreachable');
  }

  function chooseSignOut() {
    setOpen(false);
    if (getActiveUpload()) setConfirming(true);
    else void signOut();
  }

  return (
    <div className="account-menu" ref={menu}>
      <button
        type="button"
        className="button button--secondary account-menu__toggle"
        aria-expanded={open}
        aria-controls="account-menu-items"
        onClick={() => setOpen((o) => !o)}
      >
        Your account
      </button>
      {open ? (
        <ul id="account-menu-items" className="account-menu__items">
          <li>
            <Link href="/guide" className="touch-link">
              How to film your match
            </Link>
          </li>
          <li>
            <button type="button" className="button button--secondary" onClick={chooseSignOut}>
              Sign out
            </button>
          </li>
        </ul>
      ) : null}
      {signingOut ? (
        <p role="status" className="account-menu__status">
          Signing out…
        </p>
      ) : null}
      {confirming && upload ? (
        <UploadWillStop
          title={upload.title}
          percent={upload.percent}
          onKeep={() => setConfirming(false)}
          onSignOut={() => {
            setConfirming(false);
            void signOut();
          }}
        />
      ) : null}
    </div>
  );
}

function UploadWillStop({
  title,
  percent,
  onKeep,
  onSignOut,
}: {
  title: string;
  percent: number;
  onKeep: () => void;
  onSignOut: () => void;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  const keep = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    const d = dialog.current;
    if (d && typeof d.showModal === 'function' && !d.open) d.showModal();
    else d?.setAttribute('open', '');
    keep.current?.focus();
  }, []);

  return (
    <dialog
      ref={dialog}
      className="dialog"
      aria-labelledby="upload-will-stop-title"
      onCancel={(event) => {
        event.preventDefault();
        onKeep();
      }}
    >
      <div className="stack">
        <h1 id="upload-will-stop-title">Your upload will stop</h1>
        <p>
          {`'${title}' is ${percent}% uploaded. If you sign out now, the upload stops. You can resume it later from the match page by choosing the same video.`}
        </p>
        <div className="dialog__actions">
          <button ref={keep} type="button" className="button" onClick={onKeep}>
            Keep uploading
          </button>
          <button type="button" className="button button--secondary" onClick={onSignOut}>
            Sign out anyway
          </button>
        </div>
      </div>
    </dialog>
  );
}
