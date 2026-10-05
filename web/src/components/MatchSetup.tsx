'use client';

// Match setup Q-01..Q-07 (ST-016; flows-sprint-01 §5; FR-021, FR-005, FR-043; NFR-028, NFR-034,
// NFR-037). One question per page [DPA/DESIGN-12], errors summarised at the top with links to
// the fields [DPA/DESIGN-13], answers kept in memory until "Create match and upload". The flow
// logic is the pure reducer in src/lib/setup/flow.ts; this component only renders it.
import Link from 'next/link';
import { useEffect, useReducer, useRef, useState, type ReactNode } from 'react';
import { ErrorSummary } from '@/components/ErrorSummary';
import { PageTitle } from '@/components/PageTitle';
import { ApiError, type ApiClient } from '@/lib/api/client';
import { browserApi } from '@/lib/api/browser';
import type { ApiFieldError, UploadPolicy } from '@/lib/api/types';
import { formatBytes, formatDurationCap, formatSizeCap } from '@/lib/format';
import { looksLikeContactDetails } from '@/lib/setup/contact';
import {
  firstInvalidStep,
  initialSetup,
  isoDate,
  NICKNAME_MAX,
  participantsFor,
  setupReducer,
  SLOTS_FOR,
  validateStep,
  type Answers,
  type DateParts,
  type Slot,
  type Step,
  type StepError,
} from '@/lib/setup/flow';
import { handOff } from '@/lib/upload/handoff';

type Api = Pick<ApiClient, 'createMatch'>;

const QUESTIONS: Record<Step, string> = {
  format: 'Is this a doubles or singles match?',
  scoring: 'Which scoring system did you play?',
  players: 'Who played?',
  me: 'Which player are you?',
  date: 'When was the match played?',
  video: 'Choose the match video',
  check: 'Check your answers',
};

const SIDE_LABEL = { A: 'Side A', B: 'Side B' } as const;
const sideOf = (slot: Slot) => SIDE_LABEL[slot[0] as 'A' | 'B'];

function defaultNavigate(path: string) {
  window.location.assign(path);
}

export function todayParts(now = new Date()): DateParts {
  return { year: now.getFullYear(), month: now.getMonth() + 1, day: now.getDate() };
}

/** Server field codes (api-sprint-01 §4.2) → the page and the flows copy. */
function fromServerFields(fields: readonly ApiFieldError[], answers: Answers): StepError[] {
  const side = answers.format === 'singles' ? 'Each side needs one player' : 'Each side needs two players';
  const copy: Record<string, [Step, string]> = {
    format_required: ['format', 'Select doubles or singles'],
    format_invalid: ['format', 'Select doubles or singles'],
    scoring_system_invalid: ['scoring', 'Select a scoring system'],
    scoring_system_unavailable: ['scoring', 'Select a scoring system'],
    played_on_invalid: ['date', 'Enter a real date'],
    played_on_in_future: ['date', 'The date must be today or in the past'],
    side_needs_two_players: ['players', 'Each side needs two players'],
    side_needs_one_player: ['players', 'Each side needs one player'],
    invalid_slot: ['players', side],
    participants_without_format: ['players', side],
    nickname_required: ['players', side],
    nickname_too_long: ['players', `Nickname must be ${NICKNAME_MAX} characters or fewer`],
    nickname_invalid: ['players', 'Nickname must only use letters, numbers and punctuation'],
    choose_one_me: ['me', 'Choose one player as "me"'],
  };
  const seen = new Set<string>();
  const errors: StepError[] = [];
  for (const f of fields) {
    const [step, message] = copy[f.code] ?? ['format', 'Check your answers and try again'];
    const key = `${step}:${message}`;
    if (seen.has(key)) continue;
    seen.add(key);
    errors.push({ field: `change-${step}`, message });
  }
  return errors;
}

export function MatchSetup({
  api = browserApi,
  today = todayParts(),
  policy,
  navigate = defaultNavigate,
}: {
  api?: Api;
  today?: DateParts;
  policy: UploadPolicy;
  navigate?: (path: string) => void;
}) {
  const [state, dispatch] = useReducer(setupReducer, today, initialSetup);
  const [file, setFile] = useState<File | null>(null);
  const [general, setGeneral] = useState<string | undefined>();
  const [creating, setCreating] = useState(false);
  // Every submit is an attempt: the same errors again move focus to the summary (PD-R3-01).
  const [attempt, setAttempt] = useState(0);
  const [offline, setOffline] = useState(false);
  const heading = useRef<HTMLHeadingElement>(null);
  const firstRender = useRef(true);
  const { step, answers, errors } = state;
  const limits = { maxBytes: policy.maxBytes };

  // Browser Back moves between questions (one history entry per page).
  useEffect(() => {
    const onPop = (event: PopStateEvent) => {
      const target = (event.state as { setupStep?: Step } | null)?.setupStep ?? 'format';
      dispatch({ type: 'go', step: target });
    };
    window.addEventListener('popstate', onPop);
    return () => window.removeEventListener('popstate', onPop);
  }, []);

  useEffect(() => {
    if (firstRender.current) {
      firstRender.current = false;
      return;
    }
    if ((window.history.state as { setupStep?: Step } | null)?.setupStep !== step) {
      window.history.pushState({ ...(window.history.state ?? {}), setupStep: step }, '');
    }
    setGeneral(undefined);
    heading.current?.focus();
  }, [step]);

  useEffect(() => {
    const update = () => setOffline(navigator.onLine === false);
    update();
    window.addEventListener('online', update);
    window.addEventListener('offline', update);
    return () => {
      window.removeEventListener('online', update);
      window.removeEventListener('offline', update);
    };
  }, []);

  const answer = (patch: Partial<Answers>) => dispatch({ type: 'answer', patch });
  const errorFor = (prefix: string) => errors.find((e) => e.field.startsWith(prefix));

  async function create() {
    if (creating) return;
    const invalid = firstInvalidStep(answers, today, limits);
    if (invalid) {
      const problems = (['format', 'scoring', 'players', 'me', 'date', 'video'] as const)
        .flatMap((s) => validateStep(s, answers, today, limits).slice(0, 1).map((e) => ({ ...e, field: `change-${s}` })));
      dispatch({ type: 'errors', errors: problems });
      return;
    }
    if (!file) return;
    setCreating(true);
    setGeneral(undefined);
    try {
      const match = await api.createMatch({
        format: answers.format!,
        scoring_system: 'side_out',
        played_on: isoDate(answers.date)!,
        participants: participantsFor(answers),
      });
      handOff(match.id, file);
      navigate(`/matches/${match.id}`);
    } catch (e) {
      const error = e instanceof ApiError ? e : new ApiError(0, 'network_error');
      if (error.status === 422 && error.fields.length > 0) {
        dispatch({ type: 'errors', errors: fromServerFields(error.fields, answers) });
      } else if (error.status === 401) {
        navigate('/');
      } else {
        setGeneral(
          error.status === 0
            ? "You're offline. Connect to create the match and start the upload."
            : `Sorry, we could not create your match. Your answers are kept. Try again.${
                error.supportRef ? ` Reference: ${error.supportRef}` : ''
              }`,
        );
      }
      setCreating(false);
    }
  }

  const question = QUESTIONS[step];
  const h1 = (
    <h1 ref={heading} tabIndex={-1}>
      {question}
    </h1>
  );

  return (
    <div className="stack">
      <PageTitle error={errors.length > 0 || general !== undefined}>{question}</PageTitle>
      <p>
        {step === 'format' && !state.returnToCheck ? (
          <Link href="/matches" className="back-link">
            Back
          </Link>
        ) : (
          <a
            href="#"
            className="back-link"
            onClick={(event) => {
              event.preventDefault();
              dispatch({ type: 'back' });
            }}
          >
            Back
          </a>
        )}
      </p>
      {errors.length > 0 || general ? <ErrorSummary errors={errors} general={general} attempt={attempt} /> : null}
      <form
        className="stack"
        noValidate
        onSubmit={(event) => {
          event.preventDefault();
          setAttempt((n) => n + 1);
          if (step === 'check') void create();
          else dispatch({ type: 'continue', today, policy: limits });
        }}
      >
        {step === 'format' ? (
          <RadioQuestion
            legend={h1}
            name="format"
            error={errorFor('format')}
            value={answers.format}
            options={[
              { value: 'doubles', label: 'Doubles' },
              { value: 'singles', label: 'Singles' },
            ]}
            onChange={(v) => answer({ format: v as Answers['format'] })}
          />
        ) : null}
        {step === 'scoring' ? (
          <RadioQuestion
            legend={h1}
            name="scoring"
            error={errorFor('scoring')}
            value={answers.scoring}
            options={[
              { value: 'side_out', label: 'Side-out scoring (traditional)' },
              {
                value: 'rally',
                label: 'Rally scoring (provisional)',
                disabled: true,
                hint: (
                  <span className="warning-hint">
                    <span>Not available yet.</span> <span>It becomes available once the rules are verified.</span>
                  </span>
                ),
              },
            ]}
            onChange={(v) => answer({ scoring: v === 'side_out' ? 'side_out' : answers.scoring })}
          />
        ) : null}
        {step === 'players' ? <PlayersQuestion legend={h1} answers={answers} errors={errors} onAnswer={answer} /> : null}
        {step === 'me' ? (
          <RadioQuestion
            legend={h1}
            name="me"
            error={errorFor('me')}
            value={answers.me}
            options={SLOTS_FOR[answers.format ?? 'doubles'].map((slot) => ({
              value: slot,
              label: `${answers.players[slot].trim()} (${sideOf(slot)})`,
            }))}
            onChange={(v) => answer({ me: v as Slot })}
          />
        ) : null}
        {step === 'date' ? <DateQuestion legend={h1} answers={answers} error={errorFor('date')} onAnswer={answer} /> : null}
        {step === 'video' ? (
          <VideoQuestion
            heading={h1}
            policy={policy}
            error={errorFor('video')}
            chosen={answers.file}
            onFile={(f) => {
              setFile(f);
              answer({ file: f ? { name: f.name, size: f.size, lastModified: f.lastModified, type: f.type } : null });
            }}
          />
        ) : null}
        {step === 'check' ? (
          <CheckAnswers heading={h1} answers={answers} today={today} limits={limits} onChange={(s) => dispatch({ type: 'change', step: s })} />
        ) : null}
        {step !== 'check' ? (
          <button type="submit" className="button">
            Continue
          </button>
        ) : offline ? (
          <p className="notice notice--warning" role="status">
            You&apos;re offline. Connect to create the match and start the upload.
          </p>
        ) : (
          <button type="submit" className="button" aria-busy={creating}>
            {creating ? 'Creating…' : 'Create match and upload'}
          </button>
        )}
      </form>
    </div>
  );
}

function FieldErrorText({ id, error }: { id: string; error?: StepError }) {
  if (!error) return null;
  return (
    <p id={id} className="field__error">
      <span className="visually-hidden">Error: </span>
      {error.message}
    </p>
  );
}

interface Option {
  value: string;
  label: string;
  disabled?: boolean;
  hint?: ReactNode;
}

function RadioQuestion({
  legend,
  name,
  options,
  value,
  error,
  onChange,
}: {
  legend: ReactNode;
  name: string;
  options: Option[];
  value: string | null;
  error?: StepError;
  onChange: (value: string) => void;
}) {
  return (
    <div className={`field${error ? ' field--error' : ''}`}>
      <fieldset className="fieldset" aria-describedby={error ? `${name}-error` : undefined}>
        <legend className="fieldset__legend">{legend}</legend>
        <FieldErrorText id={`${name}-error`} error={error} />
        <div className="radios">
          {options.map((o) => (
            <div key={o.value} className="radios__item">
              <input
                id={`${name}-${o.value}`}
                className="radios__input"
                type="radio"
                name={name}
                value={o.value}
                checked={value === o.value}
                aria-disabled={o.disabled ? true : undefined}
                aria-describedby={o.hint ? `${name}-${o.value}-hint` : undefined}
                onClick={(event) => {
                  if (o.disabled) event.preventDefault();
                }}
                onChange={() => {
                  if (!o.disabled) onChange(o.value);
                }}
              />
              <label htmlFor={`${name}-${o.value}`} className="radios__label">
                {o.label}
              </label>
              {o.hint ? (
                <p id={`${name}-${o.value}-hint`} className="radios__hint">
                  {o.hint}
                </p>
              ) : null}
            </div>
          ))}
        </div>
      </fieldset>
    </div>
  );
}

function PlayersQuestion({
  legend,
  answers,
  errors,
  onAnswer,
}: {
  legend: ReactNode;
  answers: Answers;
  errors: StepError[];
  onAnswer: (patch: Partial<Answers>) => void;
}) {
  const [touched, setTouched] = useState<Partial<Record<Slot, boolean>>>({});
  const doubles = answers.format !== 'singles';
  const hint = 'Use a first name or nickname. Do not enter contact details.';

  const input = (slot: Slot, label: string) => {
    const error = errors.find((e) => e.field === `player-${slot}`);
    const warn = touched[slot] && looksLikeContactDetails(answers.players[slot]);
    const describedBy = [`players-${slot[0]}-hint`, error ? `player-${slot}-error` : '', warn ? `player-${slot}-warning` : '']
      .filter(Boolean)
      .join(' ');
    return (
      <div className={`field${error ? ' field--error' : ''}`} key={slot}>
        <label htmlFor={`player-${slot}`} className="field__label">
          {label}
        </label>
        <FieldErrorText id={`player-${slot}-error`} error={error} />
        <input
          id={`player-${slot}`}
          className="input"
          type="text"
          autoComplete="off"
          spellCheck={false}
          maxLength={60}
          value={answers.players[slot]}
          aria-describedby={describedBy}
          aria-invalid={error ? true : undefined}
          onChange={(e) => onAnswer({ players: { ...answers.players, [slot]: e.target.value } })}
          onBlur={() => setTouched((t) => ({ ...t, [slot]: true }))}
        />
        {warn ? (
          <p id={`player-${slot}-warning`} className="field__warning">
            This looks like contact details. Use a nickname instead.
          </p>
        ) : null}
      </div>
    );
  };

  return (
    <div className="stack">
      {legend}
      {(['A', 'B'] as const).map((side) => (
        <fieldset key={side} className="fieldset stack" aria-describedby={`players-${side}-hint`}>
          <legend className="fieldset__legend fieldset__legend--side">{SIDE_LABEL[side]}</legend>
          <p id={`players-${side}-hint`} className="field__hint">
            {hint}
          </p>
          {doubles
            ? [input(`${side}1` as Slot, 'Player 1'), input(`${side}2` as Slot, 'Player 2')]
            : input(`${side}1` as Slot, `${SIDE_LABEL[side]} player`)}
        </fieldset>
      ))}
    </div>
  );
}

function DateQuestion({
  legend,
  answers,
  error,
  onAnswer,
}: {
  legend: ReactNode;
  answers: Answers;
  error?: StepError;
  onAnswer: (patch: Partial<Answers>) => void;
}) {
  const part = (key: 'day' | 'month' | 'year', label: string, width: string) => (
    <div className="date-input__item">
      <label htmlFor={`date-${key}`} className="field__label">
        {label}
      </label>
      <input
        id={`date-${key}`}
        className={`input ${width}`}
        type="text"
        inputMode="numeric"
        autoComplete="off"
        value={answers.date[key]}
        aria-invalid={error ? true : undefined}
        onChange={(e) => onAnswer({ date: { ...answers.date, [key]: e.target.value } })}
      />
    </div>
  );
  return (
    <div className={`field${error ? ' field--error' : ''}`}>
      <fieldset className="fieldset" aria-describedby={`date-hint${error ? ' date-error' : ''}`}>
        <legend className="fieldset__legend">{legend}</legend>
        <p id="date-hint" className="field__hint">
          For example, 27 3 2026
        </p>
        <FieldErrorText id="date-error" error={error} />
        <div className="date-input">
          {part('day', 'Day', 'input--2ch')}
          {part('month', 'Month', 'input--2ch')}
          {part('year', 'Year', 'input--4ch')}
        </div>
      </fieldset>
    </div>
  );
}

function VideoQuestion({
  heading,
  policy,
  error,
  chosen,
  onFile,
}: {
  heading: ReactNode;
  policy: UploadPolicy;
  error?: StepError;
  chosen: Answers['file'];
  onFile: (file: File | null) => void;
}) {
  return (
    <div className="stack">
      {heading}
      <div className={`field${error ? ' field--error' : ''}`}>
        <label htmlFor="video" className="field__label">
          Choose video
        </label>
        <p id="video-hint" className="field__hint">
          {`MP4 or MOV, up to ${formatSizeCap(policy.maxBytes)} and ${formatDurationCap(policy.maxDurationMs)}.`}
        </p>
        <FieldErrorText id="video-error" error={error} />
        <input
          id="video"
          className="file-input"
          type="file"
          accept="video/mp4,video/quicktime"
          aria-describedby={error ? 'video-hint video-error' : 'video-hint'}
          aria-invalid={error ? true : undefined}
          onChange={(e) => onFile(e.target.files?.[0] ?? null)}
        />
        {chosen ? <p>{`Chosen: ${chosen.name} (${formatBytes(chosen.size)})`}</p> : null}
      </div>
      <p>Only you can see this video.</p>
    </div>
  );
}

function CheckAnswers({
  heading,
  answers,
  today,
  limits,
  onChange,
}: {
  heading: ReactNode;
  answers: Answers;
  today: DateParts;
  limits: { maxBytes: number };
  onChange: (step: Exclude<Step, 'check' | never>) => void;
}) {
  const format = answers.format ?? 'doubles';
  const playersOk = validateStep('players', answers, today, limits).length === 0;
  const meOk = validateStep('me', answers, today, limits).length === 0;
  const names = (side: 'A' | 'B') =>
    SLOTS_FOR[format].filter((s) => s.startsWith(side)).map((s) => answers.players[s].trim()).join(', ');
  const iso = isoDate(answers.date);
  const rows: { key: Exclude<Step, 'check'>; label: string; hidden: string; value: ReactNode }[] = [
    { key: 'format', label: 'Format', hidden: 'format', value: answers.format === 'singles' ? 'Singles' : answers.format === 'doubles' ? 'Doubles' : 'Not answered' },
    { key: 'scoring', label: 'Scoring system', hidden: 'scoring system', value: answers.scoring ? 'Side-out scoring (traditional)' : 'Not answered' },
    {
      key: 'players',
      label: 'Players',
      hidden: 'players',
      value: playersOk ? (
        <>
          <span className="block">{`Side A: ${names('A')}`}</span>
          <span className="block">{`Side B: ${names('B')}`}</span>
        </>
      ) : (
        <span className="field__warning">{format === 'singles' ? 'Enter one player per side' : 'Enter two players per side'}</span>
      ),
    },
    {
      key: 'me',
      label: 'You',
      hidden: 'which player you are',
      value: meOk && answers.me ? `${answers.players[answers.me].trim()} (${sideOf(answers.me)})` : 'Choose which player you are',
    },
    {
      key: 'date',
      label: 'Date',
      hidden: 'date',
      value: iso
        ? new Intl.DateTimeFormat('en-GB', { day: 'numeric', month: 'long', year: 'numeric', timeZone: 'UTC' }).format(new Date(`${iso}T00:00:00Z`))
        : 'Not answered',
    },
    {
      key: 'video',
      label: 'Video',
      hidden: 'video',
      value: answers.file ? `${answers.file.name} (${formatBytes(answers.file.size)})` : 'Not chosen',
    },
  ];
  return (
    <div className="stack">
      {heading}
      <dl className="summary-list">
        {rows.map((row) => (
          <div key={row.key} className="summary-list__row summary-list__row--action">
            <dt>{row.label}</dt>
            <dd>{row.value}</dd>
            <dd className="summary-list__action">
              <a
                id={`change-${row.key}`}
                href="#"
                className="inline-target"
                onClick={(event) => {
                  event.preventDefault();
                  onChange(row.key);
                }}
              >
                Change<span className="visually-hidden"> {row.hidden}</span>
              </a>
            </dd>
          </div>
        ))}
      </dl>
    </div>
  );
}
