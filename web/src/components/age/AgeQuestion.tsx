'use client';

// A-10 Are you 18 or over? and its outcome A-11 (ST-068b; FR-003; flows-sprint-04 §5; question
// page [DPA/DESIGN-12], error summary [DPA/DESIGN-13]). One question, no "Back" (there is no
// earlier page). The answer goes to the API, which decides; the page only shows what it said.
import { useEffect, useState } from 'react';
import Link from 'next/link';
import { ErrorSummary } from '@/components/ErrorSummary';
import { PageTitle } from '@/components/PageTitle';
import { SignInForm } from '@/components/SignInForm';
import { ApiError, type ApiClient } from '@/lib/api/client';
import { browserApi } from '@/lib/api/browser';
import { AGE_WORDING as W, type AgeOutcome } from '@/lib/identity/age';

type Api = Pick<ApiClient, 'confirmAge' | 'requestLink'>;
type View = 'question' | 'saving' | 'expired' | Exclude<AgeOutcome, 'adult'>;

export function AgeQuestion({
  api = browserApi,
  navigate = (path: string) => window.location.replace(path),
}: {
  api?: Api;
  navigate?: (path: string) => void;
}) {
  const [choice, setChoice] = useState<'yes' | 'no' | null>(null);
  const [view, setView] = useState<View>('question');
  const [missing, setMissing] = useState(false);
  const [failure, setFailure] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);
  const [offline, setOffline] = useState(false);

  useEffect(() => {
    const update = () => setOffline(!navigator.onLine);
    update();
    window.addEventListener('online', update);
    window.addEventListener('offline', update);
    return () => {
      window.removeEventListener('online', update);
      window.removeEventListener('offline', update);
    };
  }, []);

  async function submit() {
    setAttempt((n) => n + 1);
    if (choice === null) return setMissing(true);
    setMissing(false);
    setFailure(null);
    setView('saving');
    try {
      const outcome = await api.confirmAge(choice === 'yes');
      if (outcome === 'adult') return navigate('/welcome');
      setView(outcome);
    } catch (e) {
      const error = e instanceof ApiError ? e : new ApiError(0, 'network_error');
      if (error.status === 401 || error.status === 404) return setView('expired');
      setFailure(`We could not save your answer. Try again.${error.supportRef ? ` Reference: ${error.supportRef}` : ''}`);
      setView('question');
    }
  }

  if (view === 'expired') return <SignInForm api={api} variant="expired" />;
  if (view === 'under_age' || view === 'confirmation_required') {
    // A pending sign-in is gone (no account was made); an existing account stays gated, unchanged.
    const why = view === 'under_age' ? `${W.underWhy} ${W.noAccountMade}` : W.underWhy;
    return (
      <div className="stack">
        <PageTitle>{W.underHeading}</PageTitle>
        <h1>{W.underHeading}</h1>
        <p>{why}</p>
        <p>{W.underInstead}</p>
        <p>
          <Link href="/" className="touch-link">
            Close and return to the start
          </Link>
        </p>
      </div>
    );
  }

  const saving = view === 'saving';
  return (
    <div className="stack">
      <PageTitle error={missing}>{W.question}</PageTitle>
      {missing ? <ErrorSummary errors={[{ field: 'age-yes', message: W.nothingChosen }]} attempt={attempt} /> : null}
      {failure ? <p role="alert" className="notice notice--error">{failure}</p> : null}
      <form
        className="stack"
        noValidate
        onSubmit={(event) => {
          event.preventDefault();
          void submit();
        }}
      >
        <div className={`field${missing ? ' field--error' : ''}`}>
          <fieldset className="fieldset" aria-describedby={missing ? 'age-hint age-error' : 'age-hint'}>
            <legend className="fieldset__legend">
              <h1>{W.question}</h1>
            </legend>
            <p id="age-hint" className="field__hint">{W.hint}</p>
            {missing ? <p id="age-error" className="field__error"><span className="visually-hidden">Error: </span>{W.nothingChosen}</p> : null}
            <div className="radios">
              {(['yes', 'no'] as const).map((value) => (
                <div key={value} className="radios__item">
                  <input
                    id={`age-${value}`}
                    className="radios__input"
                    type="radio"
                    name="age"
                    value={value}
                    checked={choice === value}
                    onChange={() => setChoice(value)}
                  />
                  <label htmlFor={`age-${value}`} className="radios__label">
                    {W[value]}
                  </label>
                </div>
              ))}
            </div>
          </fieldset>
        </div>
        {offline ? <p role="status">You are offline. Connect to continue.</p> : <p role="status">{saving ? 'Checking…' : ''}</p>}
        <p>
          <button type="submit" className="button" disabled={saving || offline} aria-busy={saving || undefined}>
            {saving ? 'Checking…' : 'Continue'}
          </button>
        </p>
      </form>
    </div>
  );
}
