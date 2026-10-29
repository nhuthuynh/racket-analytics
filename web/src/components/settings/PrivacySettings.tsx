'use client';

// R-01 Privacy settings (ST-071; FR-008, FR-009; flows-sprint-04 §6). Two sections, each only with
// its own flag and each saved on its own, so one choice never saves the other. States: loading
// (no control until the stored values arrive), load error (alert, "Try again", reference, no
// controls), save error (alert; the control shows the old value again), offline (read-only).
import { useCallback, useEffect, useId, useState, type FormEvent } from 'react';
import { LocalDateLine } from '@/components/LocalDate';
import { privacySettingsApi, type Outcome, type PrivacySettingsApi } from './PrivacySettingsApi';
import {
  WORDS,
  retentionChoiceLabel,
  reviewVideoLine,
  type PrivacyFeatures,
  type RetentionSetting,
  type ReviewVideo,
  type TrainingConsent,
} from './PrivacySettingsModel';

type Loaded = { retention: RetentionSetting | null; videos: ReviewVideo[]; consent: TrainingConsent | null };
type State = { kind: 'loading' } | { kind: 'error'; supportRef: string | null } | { kind: 'loaded'; data: Loaded };
type Notice = { text: string; supportRef: string | null };
/** A save outcome: a confirmation, or an alert (the save failed, or it worked but a follow-up read did not). */
type Message = { ok: true; text: string } | { ok: false; alert: Notice } | null;
interface SectionProps {
  api: PrivacySettingsApi;
  online: boolean;
  onSignedOut: () => void;
}

function signIn() {
  window.location.assign('/');
}

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

function SaveResult({ message }: { message: Message }) {
  return (
    <>
      <p role="status">{message?.ok ? message.text : ''}</p>
      {message && !message.ok ? (
        <div role="alert" className="notice notice--error">
          <p>{message.alert.text}</p>
          {message.alert.supportRef ? <p>{`Reference: ${message.alert.supportRef}`}</p> : null}
        </div>
      ) : null}
    </>
  );
}

/**
 * Runs a save: the stored value and what the section says about it on success; on any refusal the
 * caller's old value is shown again with one alert (ST-071 negative test).
 */
async function saving<T>(save: Promise<Outcome<T>>, props: SectionProps, onSaved: (v: T) => Promise<Message> | Message, onFailed: () => void): Promise<Message> {
  const r = await save;
  if (r.kind === 'ok') return onSaved(r.value);
  onFailed();
  if (r.kind === 'signed_out') props.onSignedOut();
  return { ok: false, alert: { text: WORDS.saveFailed, supportRef: r.kind === 'error' ? r.supportRef : null } };
}

function RetentionSection({ initial, videos, timeZone, ...props }: SectionProps & { initial: RetentionSetting; videos: ReviewVideo[]; timeZone?: string }) {
  const id = useId();
  const [saved, setSaved] = useState(initial.days);
  const [draft, setDraft] = useState(initial.days);
  // null: the dates after a save could not be read, so none is shown (an old one would be wrong).
  const [list, setList] = useState<ReviewVideo[] | null>(videos);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<Message>(null);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setMessage(null);
    setMessage(await saving(props.api.saveRetention(draft), props, async (v) => {
      setSaved(v.days);
      setDraft(v.days);
      const dates = await props.api.reviewVideos();
      if (dates.kind === 'ok') {
        setList(dates.value);
        return { ok: true, text: WORDS.retentionSaved };
      }
      setList(null);
      if (dates.kind === 'signed_out') props.onSignedOut();
      return { ok: false, alert: { text: WORDS.datesUnread, supportRef: dates.kind === 'error' ? dates.supportRef : null } };
    }, () => setDraft(saved)));
    setBusy(false);
  }

  return (
    <section className="stack" aria-labelledby={`${id}-h`}>
      <h2 id={`${id}-h`}>{WORDS.retentionHeading}</h2>
      <p>{WORDS.retentionIntro}</p>
      <p>{WORDS.systemRule}</p>
      <form className="stack" onSubmit={(e) => void submit(e)}>
        <fieldset className="fieldset" disabled={!props.online}>
          <legend className="visually-hidden">{WORDS.retentionHeading}</legend>
          <div className="radios">
            {initial.choices.map((days) => (
              <div key={String(days)} className="radios__item">
                <input id={`${id}-${days}`} className="radios__input" type="radio" name={`${id}-days`}
                  checked={draft === days} onChange={() => setDraft(days)} />
                <label htmlFor={`${id}-${days}`} className="radios__label">{retentionChoiceLabel(days)}</label>
              </div>
            ))}
          </div>
        </fieldset>
        <p>
          <button type="submit" className="button" disabled={busy || !props.online} aria-busy={busy || undefined}>
            {WORDS.saveRetention}
          </button>
        </p>
      </form>
      <SaveResult message={message} />
      <h3 id={`${id}-dates`}>{WORDS.datesHeading}</h3>
      {list === null ? null : list.length === 0 ? (
        <p>{WORDS.noVideos}</p>
      ) : (
        <ul className="stack" aria-labelledby={`${id}-dates`}>
          {list.map((v) => {
            const line = reviewVideoLine(v);
            return (
              <li key={v.matchId}>
                <p>{v.title}</p>
                {'text' in line ? <p>{line.text}</p> : <LocalDateLine prefix={line.prefix} iso={line.iso} timeZone={timeZone} />}
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}

function ConsentSection({ initial, ...props }: SectionProps & { initial: TrainingConsent }) {
  const id = useId();
  const [saved, setSaved] = useState(initial.optIn);
  const [draft, setDraft] = useState(initial.optIn);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<Message>(null);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setMessage(null);
    setMessage(await saving(props.api.saveConsent(draft), props, (v) => {
      setSaved(v.optIn);
      setDraft(v.optIn);
      return { ok: true, text: v.optIn ? WORDS.consentOn : WORDS.consentOff };
    }, () => setDraft(saved)));
    setBusy(false);
  }

  return (
    <section className="stack" aria-labelledby={`${id}-h`}>
      <h2 id={`${id}-h`}>{WORDS.consentHeading}</h2>
      <form className="stack" onSubmit={(e) => void submit(e)}>
        <div className="choice">
          <input id={`${id}-opt-in`} type="checkbox" checked={draft} disabled={!props.online}
            aria-describedby={`${id}-explain`} onChange={(e) => setDraft(e.target.checked)} />
          <label htmlFor={`${id}-opt-in`}>{WORDS.consentLabel}</label>
        </div>
        <div id={`${id}-explain`} className="stack">
          <p>{WORDS.consentExplain}</p>
          <p>{WORDS.consentTurnOff}</p>
        </div>
        <p>
          <button type="submit" className="button" disabled={busy || !props.online} aria-busy={busy || undefined}>
            {WORDS.saveConsent}
          </button>
        </p>
      </form>
      <SaveResult message={message} />
    </section>
  );
}

export function PrivacySettings({
  features,
  api = privacySettingsApi,
  timeZone,
  onSignedOut = signIn,
}: {
  features: PrivacyFeatures;
  api?: PrivacySettingsApi;
  /** Fixes the date zone for tests; the viewer's zone otherwise. */
  timeZone?: string;
  onSignedOut?: () => void;
}) {
  const [state, setState] = useState<State>({ kind: 'loading' });
  const online = useOnline();

  const load = useCallback(async () => {
    setState({ kind: 'loading' });
    const none = Promise.resolve(null);
    const [retention, videos, consent] = await Promise.all([
      features.retention ? api.retention() : none,
      features.retention ? api.reviewVideos() : none,
      features.consent ? api.consent() : none,
    ]);
    const outcomes = [retention, videos, consent].filter((o) => o !== null);
    if (outcomes.some((o) => o.kind === 'signed_out')) {
      onSignedOut();
      return;
    }
    const failed = outcomes.find((o) => o.kind === 'error');
    if (failed) {
      setState({ kind: 'error', supportRef: failed.supportRef });
      return;
    }
    setState({
      kind: 'loaded',
      data: {
        retention: retention?.kind === 'ok' ? retention.value : null,
        videos: videos?.kind === 'ok' ? videos.value : [],
        consent: consent?.kind === 'ok' ? consent.value : null,
      },
    });
  }, [api, features.retention, features.consent, onSignedOut]);

  useEffect(() => {
    void load();
  }, [load]);

  const section = { api, online, onSignedOut };
  return (
    <div className="stack">
      <h1>{WORDS.title}</h1>
      {state.kind === 'loading' ? (
        <div className="stack" aria-busy="true">
          <p role="status">{WORDS.loading}</p>
        </div>
      ) : null}
      {state.kind === 'error' ? (
        <>
          <div role="alert" className="notice notice--error">
            <p>{WORDS.loadFailed}</p>
            {state.supportRef ? <p>{`Reference: ${state.supportRef}`}</p> : null}
          </div>
          <p>
            <button type="button" className="button button--secondary" onClick={() => void load()}>
              Try again
            </button>
          </p>
        </>
      ) : null}
      {state.kind === 'loaded' ? (
        <>
          {online ? null : <p className="notice notice--info">{WORDS.offline}</p>}
          {state.data.retention ? (
            <RetentionSection initial={state.data.retention} videos={state.data.videos} timeZone={timeZone} {...section} />
          ) : null}
          {state.data.consent ? <ConsentSection initial={state.data.consent} {...section} /> : null}
        </>
      ) : null}
    </div>
  );
}
