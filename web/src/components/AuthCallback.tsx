'use client';

// A-03 "Signing you in…" (ST-013; flows-sprint-01 §2; api-sprint-01 §2.2). The token arrives in
// the URL fragment, is removed from the address bar with history.replaceState BEFORE the
// request (NFR-055, T-ML-4) and is never stored on the device. An expired, used or unknown
// link shows A-04, which does not say which of the three it was (D-4).
import { useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import { PageTitle } from '@/components/PageTitle';
import { SignInForm } from '@/components/SignInForm';
import { ApiError, type ApiClient } from '@/lib/api/client';
import { browserApi } from '@/lib/api/browser';

type Api = Pick<ApiClient, 'exchangeLink' | 'requestLink'>;

type State =
  | { kind: 'signing-in'; slow: boolean }
  | { kind: 'expired' }
  | { kind: 'offline' }
  | { kind: 'server'; supportRef: string | null };

const SLOW_AFTER_MS = 5_000;

/** Reads and removes `#token=…`; returns the token or null. */
function takeTokenFromUrl(): string | null {
  const hash = window.location.hash.startsWith('#') ? window.location.hash.slice(1) : '';
  const token = new URLSearchParams(hash).get('token');
  if (window.location.hash || window.location.search) {
    window.history.replaceState(null, '', '/auth/callback');
  }
  return token;
}

function defaultNavigate(path: string) {
  window.location.replace(path);
}

export function AuthCallback({
  api = browserApi,
  navigate = defaultNavigate,
}: {
  api?: Api;
  navigate?: (path: string) => void;
}) {
  const [state, setState] = useState<State>({ kind: 'signing-in', slow: false });
  const started = useRef(false);

  useEffect(() => {
    // Strict mode runs effects twice; the token is single-use, so exchange it once.
    if (started.current) return;
    started.current = true;
    const token = takeTokenFromUrl();
    if (!token) {
      setState({ kind: 'expired' });
      return;
    }
    const slow = setTimeout(() => setState((s) => (s.kind === 'signing-in' ? { ...s, slow: true } : s)), SLOW_AFTER_MS);
    api
      .exchangeLink(token)
      .then(({ newAccount }) => navigate(newAccount ? '/welcome' : '/matches'))
      .catch((e: unknown) => {
        const error = e instanceof ApiError ? e : new ApiError(0, 'network_error');
        if (error.status === 401 || error.status === 422) setState({ kind: 'expired' });
        else if (error.status === 0) setState({ kind: 'offline' });
        else setState({ kind: 'server', supportRef: error.supportRef });
      })
      .finally(() => clearTimeout(slow));
  }, [api, navigate]);

  if (state.kind === 'expired') return <SignInForm api={api} variant="expired" />;

  if (state.kind === 'signing-in') {
    return (
      <div className="stack">
        <PageTitle>Signing you in</PageTitle>
        <h1>Signing you in…</h1>
        <p role="status">{state.slow ? 'This is taking longer than usual.' : 'Signing you in…'}</p>
      </div>
    );
  }

  return (
    <div className="stack">
      <PageTitle>Sign-in problem</PageTitle>
      <h1>We could not sign you in</h1>
      {state.kind === 'offline' ? (
        <p role="alert">You&apos;re offline. Connect and open the link again.</p>
      ) : (
        <>
          <p role="alert">
            {`Sorry, we could not sign you in. Request a new link.${
              state.supportRef ? ` Reference: ${state.supportRef}` : ''
            }`}
          </p>
          <p>
            <Link href="/" className="button">
              Send a new link
            </Link>
          </p>
        </>
      )}
    </div>
  );
}
