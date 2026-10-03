'use client';

// Development sign-in picker (ST-006 dev identity provider; replaced by real sign-in in
// Sprint 1). No password or puzzle, SC 3.3.8 [DPA/DESIGN-06].
import { useRouter } from 'next/navigation';
import { useState } from 'react';
import type { ApiClient } from '@/lib/api/client';
import { browserApi } from '@/lib/api/browser';
import type { DevUser } from '@/lib/api/types';
import { clearStoredUploads } from '@/lib/upload/tus-policy';
import { safeLocalStorage } from '@/lib/upload/storage';

type Api = Pick<ApiClient, 'signIn'>;

export function SignInPicker({ users, api = browserApi }: { users: DevUser[]; api?: Api }) {
  const router = useRouter();
  const [pending, setPending] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);

  if (users.length === 0) {
    return <p>No test players are available. Development sign-in may be switched off.</p>;
  }

  async function signIn(username: string) {
    if (pending) return;
    setPending(username);
    setFailed(false);
    try {
      await api.signIn(username);
      // A new session must not see a previous player's upload URLs (ASVS 14.3.1).
      clearStoredUploads(safeLocalStorage());
      router.push('/matches');
      router.refresh();
    } catch {
      setPending(null);
      setFailed(true);
    }
  }

  return (
    <>
      {failed ? (
        <p role="alert" className="notice notice--error">
          <span className="visually-hidden">Error: </span>
          We could not sign you in. Try again.
        </p>
      ) : null}
      <ul className="button-list">
        {users.map((u) => (
          <li key={u.username}>
            <button
              type="button"
              className="button"
              aria-busy={pending === u.username}
              onClick={() => void signIn(u.username)}
            >
              {`Sign in as ${u.display_name}`}
            </button>
          </li>
        ))}
      </ul>
    </>
  );
}
