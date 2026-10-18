'use client';

// P-02 "Your practice setup" (ST-063b; FR-121; flows-sprint-04 §3). One page, five questions,
// nothing chosen on a first visit; a regenerate visit starts from the last preferences. The page
// checks the answers first (error summary [DPA/DESIGN-13]); the API's refusals are one alert at the
// top with the fix; the answers stay in every case.
import Link from 'next/link';
import { useEffect, useRef, useState, type FormEvent, type ReactNode } from 'react';
import { ErrorSummary, type FieldError } from '@/components/ErrorSummary';
import { PageTitle } from '@/components/PageTitle';
import type { GenerateOutcome, PlanPreferencesApi } from './PlanPreferencesApi';
import {
  EQUIPMENT,
  EQUIPMENT_WORDS,
  FIELD_IDS,
  LEVELS,
  LEVEL_WORDS,
  PLAYER_CHOICES,
  SESSION_CHOICES,
  checkDraft,
  draftFrom,
  type PlanPreferences as Preferences,
  type PreferencesDraft,
} from './PlanPreferencesModel';
import styles from './PlanPreferences.module.css';

type Refusal = Extract<GenerateOutcome, { kind: 'no_tagged_match' | 'no_plan_fits' | 'plan_conflict' | 'error' }>;

const SLOW_AFTER_MS = 10_000;

function useOnline(): boolean {
  const [online, setOnline] = useState(true);
  useEffect(() => {
    const update = () => setOnline(navigator.onLine);
    update();
    window.addEventListener('online', update);
    window.addEventListener('offline', update);
    return () => {
      window.removeEventListener('online', update);
      window.removeEventListener('offline', update);
    };
  }, []);
  return online;
}

function FieldErrorText({ error }: { error?: FieldError }) {
  if (!error) return null;
  return (
    <p id={`${error.field}-error`} className="field__error">
      <span className="visually-hidden">Error: </span>
      {error.message}
    </p>
  );
}

function NumberQuestion({ legend, name, choices, value, error, onChange }: {
  legend: string; name: string; choices: readonly number[]; value: number | null; error?: FieldError;
  onChange: (n: number) => void;
}) {
  return (
    <div className={`field${error ? ' field--error' : ''}`}>
      <fieldset className="fieldset" aria-describedby={error ? `${error.field}-error` : undefined}>
        <legend className="fieldset__legend field__label">{legend}</legend>
        <FieldErrorText error={error} />
        <div className={styles.row}>
          {choices.map((n) => (
            <div key={n} className={styles.number}>
              <input id={`${name}-${n}`} className="radios__input" type="radio" name={name} value={n}
                checked={value === n} onChange={() => onChange(n)} />
              <label htmlFor={`${name}-${n}`}>{n}</label>
            </div>
          ))}
        </div>
      </fieldset>
    </div>
  );
}

function RefusalAlert({ refusal, regenerate }: { refusal: Refusal; regenerate: boolean }) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => ref.current?.focus(), [refusal]);
  let body: ReactNode;
  if (refusal.kind === 'no_tagged_match') {
    body = (<>
      <p>Tag a match first. Your plan is built from the rallies you tag.</p>
      <p><Link href="/matches" className="inline-target">Your matches</Link></p>
    </>);
  } else if (refusal.kind === 'no_plan_fits') {
    body = (<>
      <p>No plan fits these settings. Try more minutes, more sessions or more equipment.</p>
      {regenerate ? <p>Your current plan is unchanged.</p> : null}
    </>);
  } else if (refusal.kind === 'plan_conflict') {
    body = (<>
      <p>Your plan changed on another device, so this one was not saved. Your answers are kept.</p>
      <p><Link href="/plan" className="inline-target">See your current plan</Link></p>
    </>);
  } else {
    body = (<>
      <p>We could not make your plan. Try again.</p>
      {refusal.supportRef ? <p>Reference: {refusal.supportRef}</p> : null}
    </>);
  }
  return <div ref={ref} className="notice notice--error stack" role="alert" tabIndex={-1}>{body}</div>;
}

export function PlanPreferences({ initial, api, navigate }: {
  /** The last preferences on a regenerate visit; null on a first visit. */
  initial: Preferences | null;
  api: Pick<PlanPreferencesApi, 'generatePlan'>;
  navigate: (path: string) => void;
}) {
  const regenerate = initial !== null;
  const [draft, setDraft] = useState<PreferencesDraft>(() => draftFrom(initial));
  const [errors, setErrors] = useState<FieldError[]>([]);
  const [attempt, setAttempt] = useState(0);
  const [refusal, setRefusal] = useState<Refusal | null>(null);
  const [busy, setBusy] = useState(false);
  const [slow, setSlow] = useState(false);
  const online = useOnline();

  useEffect(() => {
    if (!busy) return undefined;
    const timer = setTimeout(() => setSlow(true), SLOW_AFTER_MS);
    return () => {
      clearTimeout(timer);
      setSlow(false);
    };
  }, [busy]);

  const errorFor = (field: string) => errors.find((e) => e.field === field);
  const change = (part: Partial<PreferencesDraft>) => setDraft((d) => ({ ...d, ...part }));

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (busy || !online) return;
    setRefusal(null);
    const check = checkDraft(draft);
    if (!check.ok) {
      setErrors(check.errors);
      setAttempt((a) => a + 1);
      return;
    }
    setErrors([]);
    setBusy(true);
    const outcome = await api.generatePlan(check.preferences);
    setBusy(false);
    if (outcome.kind === 'created') navigate('/plan');
    else if (outcome.kind === 'signed_out') navigate('/');
    else if (outcome.kind === 'invalid') {
      setErrors(outcome.errors);
      setAttempt((a) => a + 1);
    } else setRefusal(outcome);
  }

  const minutesError = errorFor(FIELD_IDS.minutes);
  const status = busy ? (slow ? 'Still working…' : 'Making your plan…') : '';

  return (
    <div className="stack">
      <PageTitle error={errors.length > 0 || refusal !== null}>Your practice setup</PageTitle>
      {refusal ? <RefusalAlert refusal={refusal} regenerate={regenerate} /> : null}
      <ErrorSummary errors={errors} attempt={attempt} />
      <h1>Your practice setup</h1>
      <form className="stack" noValidate onSubmit={submit}>
        <div className={`field${minutesError ? ' field--error' : ''}`}>
          <label htmlFor={FIELD_IDS.minutes} className="field__label">How long is each session?</label>
          <p id="minutes-per-session-hint" className="field__hint">Between 15 and 180.</p>
          <FieldErrorText error={minutesError} />
          <span className={styles.number}>
            <input id={FIELD_IDS.minutes} className={`input ${styles.minutes}`} type="text" inputMode="numeric"
              autoComplete="off" value={draft.minutes} aria-invalid={minutesError ? true : undefined}
              aria-describedby={`minutes-per-session-hint${minutesError ? ' minutes-per-session-error' : ''}`}
              onChange={(e) => change({ minutes: e.target.value })} />
            minutes
          </span>
        </div>
        <NumberQuestion legend="How many sessions a week?" name="sessions-per-week" choices={SESSION_CHOICES}
          value={draft.sessionsPerWeek} error={errorFor(FIELD_IDS.sessions)} onChange={(n) => change({ sessionsPerWeek: n })} />
        <NumberQuestion legend="How many players, including you?" name="players-available" choices={PLAYER_CHOICES}
          value={draft.playersAvailable} error={errorFor(FIELD_IDS.players)} onChange={(n) => change({ playersAvailable: n })} />
        <div className={`field${errorFor(FIELD_IDS.equipment) ? ' field--error' : ''}`}>
          <fieldset className="fieldset">
            <legend className="fieldset__legend field__label">What do you have?</legend>
            <p className="field__hint">Choose all that apply, or none.</p>
            <FieldErrorText error={errorFor(FIELD_IDS.equipment)} />
            {EQUIPMENT.map((e) => (
              <div key={e} className="choice">
                <input id={`equipment-${e}`} type="checkbox" checked={draft.equipment.includes(e)}
                  onChange={(ev) => change({ equipment: ev.target.checked ? [...draft.equipment, e] : draft.equipment.filter((x) => x !== e) })} />
                <label htmlFor={`equipment-${e}`}>{EQUIPMENT_WORDS[e]}</label>
              </div>
            ))}
          </fieldset>
        </div>
        <div className={`field${errorFor(FIELD_IDS.level) ? ' field--error' : ''}`}>
          <fieldset className="fieldset" aria-describedby={errorFor(FIELD_IDS.level) ? `${FIELD_IDS.level}-error` : undefined}>
            <legend className="fieldset__legend field__label">Your level</legend>
            <FieldErrorText error={errorFor(FIELD_IDS.level)} />
            <div className="radios">
              {LEVELS.map((l) => (
                <div key={l} className="radios__item">
                  <input id={`level-${l}`} className="radios__input" type="radio" name="level" value={l}
                    checked={draft.level === l} onChange={() => change({ level: l })} />
                  <label htmlFor={`level-${l}`} className="radios__label">{LEVEL_WORDS[l]}</label>
                </div>
              ))}
            </div>
          </fieldset>
        </div>
        <div className="stack">
          <button type="submit" className={`button ${styles.submit}`} disabled={busy || !online}
            aria-busy={busy ? true : undefined} aria-describedby={online ? undefined : 'plan-needs-connection'}>
            {busy ? 'Making your plan…' : 'Make my plan'}
          </button>
          {online ? null : <p id="plan-needs-connection">Needs a connection to make your plan.</p>}
          {regenerate ? <p>This replaces your current plan.</p> : null}
          <p role="status" className={status ? undefined : 'visually-hidden'}>{status}</p>
        </div>
      </form>
    </div>
  );
}
