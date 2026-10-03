'use client';

// Sign out: ends the server session and clears stored upload URLs (ASVS 14.3.1; api §2.3, §8).
import { useRouter } from 'next/navigation';
import { useState } from 'react';
import type { ApiClient } from '@/lib/api/client';
import { browserApi } from '@/lib/api/browser';
import { safeLocalStorage } from '@/lib/upload/storage';
import { clearStoredUploads } from '@/lib/upload/tus-policy';

export function SignOutButton({ api = browserApi }: { api?: Pick<ApiClient, 'signOut'> }) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);

  async function signOut() {
    if (busy) return;
    setBusy(true);
    try {
      await api.signOut();
    } catch {
      // Sign-out is idempotent on the server; clear local data either way.
    }
    clearStoredUploads(safeLocalStorage());
    router.push('/');
    router.refresh();
  }

  return (
    <button
      type="button"
      className="button button--secondary"
      aria-busy={busy}
      onClick={() => void signOut()}
    >
      Sign out
    </button>
  );
}
