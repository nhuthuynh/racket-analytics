'use client';

// A-01 "Sign in or create an account" and A-02 "Check your email" (ST-013; flows-sprint-01 §2).
// A-04 "This link has expired" is the same form with another heading (variant="expired").
// Only an email address is asked for: no password and no puzzle (SC 3.3.8, NFR-032). The
// address is kept in component state only, never in the URL or browser storage [AQS/SEC-05].
import { useEffect, useRef, useState, type FormEvent } from 'react';
import { ErrorSummary } from '@/components/ErrorSummary';
import { PageTitle } from '@/components/PageTitle';
import { ApiError, type ApiClient } from '@/lib/api/client';
import { browserApi } from '@/lib/api/browser';
import {
  EMAIL_FORMAT_MESSAGE,
  OFFLINE_SIGN_IN_MESSAGE,
  isWellFormedEmail,
  signInErrorMessage,
} from '@/lib/auth/sign-in';

type Api = Pick<ApiClient, 'requestLink'>;

const FIELD_ID = 'email';

const COPY = {
  'sign-in': { title: 'Sign in', heading: 'Sign in or create an account', button: 'Send me a link' },
  expired: { title: 'This link has expired', heading: 'This link has expired', button: 'Send a new link' },
} as const;

export function SignInForm({
  api = browserApi,
  variant = 'sign-in',
}: {
  api?: Api;
  variant?: keyof typeof COPY;
}) {
  const [email, setEmail] = useState('');
  const [sentTo, setSentTo] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  // Every submit is an attempt: the same error again moves focus to the summary (PD-R3-01).
  const [attempt, setAttempt] = useState(0);
  const [sending, setSending] = useState(false);
  const [offline, setOffline] = useState(false);
  const busy = useRef(false);

  useEffect(() => {
    const update = () => setOffline(typeof navigator !== 'undefined' && navigator.onLine === false);
    update();
    window.addEventListener('online', update);
    window.addEventListener('offline', update);
    return () => {
      window.removeEventListener('online', update);
      window.removeEventListener('offline', update);
    };
  }, []);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (busy.current) return;
    setAttempt((n) => n + 1);
    const trimmed = email.trim();
    if (!isWellFormedEmail(trimmed)) {
      setError(EMAIL_FORMAT_MESSAGE);
      return;
    }
    if (typeof navigator !== 'undefined' && navigator.onLine === false) {
      setError(OFFLINE_SIGN_IN_MESSAGE);
      return;
    }
    busy.current = true;
    setSending(true);
    try {
      await api.requestLink(trimmed);
      setError(null);
      setSentTo(trimmed);
    } catch (e) {
      setError(signInErrorMessage(e instanceof ApiError ? e : new ApiError(0, 'network_error')));
    } finally {
      busy.current = false;
      setSending(false);
    }
  }

  if (sentTo !== null) {
    return (
      <CheckYourEmail
        email={sentTo}
        onResend={() => {
          setEmail(sentTo);
          setSentTo(null);
        }}
        onDifferent={() => {
          setEmail('');
          setSentTo(null);
        }}
      />
    );
  }

  const copy = COPY[variant];
  const fieldError = error === EMAIL_FORMAT_MESSAGE;
  return (
    <div className="stack">
      <PageTitle error={error !== null}>{copy.title}</PageTitle>
      {error ? <ErrorSummary errors={[{ field: FIELD_ID, message: error }]} attempt={attempt} /> : null}
      {offline ? (
        <p className="notice notice--warning" role="status">
          {OFFLINE_SIGN_IN_MESSAGE}
        </p>
      ) : null}
      <h1>{copy.heading}</h1>
      {variant === 'expired' ? <p>Sign-in links work once and only for 15 minutes.</p> : null}
      <form className="stack" noValidate onSubmit={(e) => void onSubmit(e)}>
        <div className={`field${fieldError ? ' field--error' : ''}`}>
          <label htmlFor={FIELD_ID} className="field__label">
            Email address
          </label>
          <p id="email-hint" className="field__hint">
            We&apos;ll email you a link to sign in. No password needed.
          </p>
          {fieldError ? (
            <p id="email-error" className="field__error">
              <span className="visually-hidden">Error: </span>
              {error}
            </p>
          ) : null}
          <input
            id={FIELD_ID}
            name="email"
            type="email"
            autoComplete="email"
            spellCheck={false}
            className="input"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            aria-describedby={fieldError ? 'email-hint email-error' : 'email-hint'}
            aria-invalid={fieldError ? true : undefined}
          />
        </div>
        <button type="submit" className="button" aria-busy={sending}>
          {sending ? 'Sending…' : copy.button}
        </button>
      </form>
    </div>
  );
}

function CheckYourEmail({
  email,
  onResend,
  onDifferent,
}: {
  email: string;
  onResend: () => void;
  onDifferent: () => void;
}) {
  const heading = useRef<HTMLHeadingElement>(null);
  useEffect(() => {
    heading.current?.focus();
  }, []);
  return (
    <div className="stack">
      <PageTitle>Check your email</PageTitle>
      <h1 ref={heading} tabIndex={-1} aria-live="polite">
        Check your email
      </h1>
      <p>
        We sent a sign-in link to <strong>{email}</strong>. It works once and expires in 15 minutes.
      </p>
      <p>
        Not there? Check your spam folder or{' '}
        <button type="button" className="link-button" onClick={onResend}>
          send a new link
        </button>
        .
      </p>
      <p>
        <button type="button" className="link-button" onClick={onDifferent}>
          Use a different email address
        </button>
      </p>
    </div>
  );
}
