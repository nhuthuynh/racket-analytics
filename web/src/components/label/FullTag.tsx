'use client';

// L-01 Full Tag (ST-052; FR-150, FR-151; NFR-030; api-sprint-03 §5; flows-sprint-03 §6; ADR 0043).
// An internal tool for the team's labellers on their own consented matches. Frame stepping by
// keys (matched by KeyboardEvent.key: "," "." "<" ">") and buttons, never by dragging. A rally is
// saved only when its ending is chosen: first the rally with its outcome, then its hits and
// bounces in frame order, one request per label (§5.2). A refused label keeps the marks and says
// why. Exports the saved rallies as `full-tag-labels/v1`. Nicknames are shown; slots are sent.
import { useCallback, useEffect, useRef, useState } from 'react';
import { ApiError, type ApiClient } from '@/lib/api/client';
import { browserApi } from '@/lib/api/browser';
import type { Match } from '@/lib/api/types';
import { FAULT_KINDS, type EventLabel, type LabelDocument, type LabelFaultKind, type LabelOutcome, type LabelSession, type SavedRally } from '@/lib/label/types';
import { reconcile, sameOutcome } from '@/lib/label/reconcile';
import { ENDING_WORDS, FAULT_WORDS, exportLine, frameTime, inOrder, markLine, refusalReason, savedLine } from '@/lib/label/view';
import { ENDINGS, type Ending, type Side } from '@/lib/tagging/types';
import { sideNames } from '@/lib/tagging/view';
import { FullTagKeys } from './FullTagKeys';

export type FullTagApi = Pick<ApiClient, 'labelSession' | 'labelEvent' | 'labelExport' | 'matchMedia'>;

const SINGLE_KEYS = 'ra-full-tag-single-keys';

function readSingleKeys(): boolean {
  try {
    return window.localStorage.getItem(SINGLE_KEYS) !== 'off';
  } catch {
    return true;
  }
}

function writeSingleKeys(on: boolean) {
  try {
    window.localStorage.setItem(SINGLE_KEYS, on ? 'on' : 'off');
  } catch {
    // storage blocked: the choice lasts for this page only
  }
}

function saveFile(name: string, doc: LabelDocument) {
  const url = URL.createObjectURL(new Blob([JSON.stringify(doc, null, 2)], { type: 'application/json' }));
  const a = document.createElement('a');
  a.href = url;
  a.download = name;
  document.body.append(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1_000);
}

function plural(n: number, one: string, many: string): string {
  return `${n} ${n === 1 ? one : many}`;
}

function saveProblem(e: unknown, saved: readonly SavedRally[], span: { start: number; end: number } | null): string {
  if (e instanceof ApiError && e.code === 'invalid_label') return refusalReason(e.fields, saved, span);
  if (e instanceof ApiError && e.status === 429) return 'Too many labels in a short time. Wait a moment, then save again.';
  if (e instanceof ApiError && e.code === 'network_error') return 'The label was not saved because the connection dropped. Try again.';
  const ref = e instanceof ApiError && e.supportRef ? ` Reference: ${e.supportRef}` : '';
  return `The label was not saved. Try again.${ref}`;
}

/** A refusal (422) or the rate limit (429) stores nothing (api-sprint-03 §5.4); any other failure
 *  may have stored the label before its response was lost. */
function mayHaveLanded(e: unknown): boolean {
  return !(e instanceof ApiError && (e.status === 422 || e.status === 429));
}

type Pending = { kind: 'hit'; frame: number } | { kind: 'bounce'; frame: number } | null;

export function FullTag({
  match,
  initial,
  api = browserApi,
  download = saveFile,
}: {
  match: Match;
  initial: LabelSession;
  api?: FullTagApi;
  download?: (name: string, doc: LabelDocument) => void;
}) {
  const { fps, frameCount } = initial;
  const last = Math.max(0, frameCount - 1);
  const names = sideNames(match);
  const players = initial.players;
  const nickname = useCallback(
    (slot: string) => names.players.find((p) => p.slot === slot)?.nickname ?? slot,
    [names.players],
  );
  const otherSide: Side = names.mySide === 'A' ? 'B' : 'A';

  const [frame, setFrame] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [saved, setSaved] = useState<SavedRally[]>(inOrder(initial.document.rallies));
  const [start, setStart] = useState<number | null>(null);
  const [end, setEnd] = useState<number | null>(null);
  const [marks, setMarks] = useState<EventLabel[]>([]);
  const [pending, setPending] = useState<Pending>(null);
  const [across, setAcross] = useState('');
  const [along, setAlong] = useState('');
  const [side, setSide] = useState<Side | null>(null);
  const [responsible, setResponsible] = useState<string | null>(null);
  const [askFault, setAskFault] = useState(false);
  // The server's copy of the rally being labelled: its outcome and the events it holds (PE-ST052-R1-04).
  const [held, setHeld] = useState<LabelOutcome | null>(null);
  const [sent, setSent] = useState<EventLabel[]>([]);
  const [busy, setBusy] = useState(false);
  const [questionAlert, setQuestionAlert] = useState<string | null>(null);
  const [tagProblem, setTagProblem] = useState<string | null>(null);
  const [dropAsk, setDropAsk] = useState(false);
  const [keysOpen, setKeysOpen] = useState(false);
  const [singleKeys, setSingleKeys] = useState(true);
  const [exportStatus, setExportStatus] = useState('');
  const [exportProblem, setExportProblem] = useState<string | null>(null);
  const [said, setSaid] = useState('');
  const [videoUrl, setVideoUrl] = useState<string | null>(null);
  const [videoProblem, setVideoProblem] = useState<string | null>(null);
  const video = useRef<HTMLVideoElement>(null);
  const keysOpener = useRef<HTMLElement | null>(null);
  const playingRef = useRef(false);
  // The session version the local state matches, and whether a POST failed without telling us
  // whether it was stored. A retry reads the session first when it did.
  const known = useRef(initial.version);
  const unsure = useRef(false);
  const number = saved.length + 1;

  useEffect(() => setSingleKeys(readSingleKeys()), []);

  // The video for stepping: the owner's short-lived link (api-sprint-02 GET /matches/{id}/video).
  const loadVideo = useCallback(async () => {
    try {
      setVideoUrl((await api.matchMedia(match.id)).url);
      setVideoProblem(null);
    } catch {
      setVideoProblem('The video could not be loaded. Frame numbers still work; reload the page to try again.');
    }
  }, [api, match.id]);
  useEffect(() => {
    void loadVideo();
  }, [loadVideo]);

  // Paused: the video shows the frame in state (the middle of the frame, so rounding never shows
  // the one before). Playing: the state follows the video.
  useEffect(() => {
    const v = video.current;
    if (!v || playingRef.current || v.readyState < 1) return;
    v.currentTime = (frame + 0.5) / fps;
  }, [frame, fps, videoUrl]);

  // The readout is announced once stepping has stopped for 500 ms (no flood while a key is held).
  useEffect(() => {
    const t = setTimeout(() => setSaid(`At frame ${frame}.`), 500);
    return () => clearTimeout(t);
  }, [frame]);

  const step = useCallback((by: number) => {
    setFrame((f) => Math.min(last, Math.max(0, f + by)));
  }, [last]);

  function togglePlay() {
    const v = video.current;
    if (!v) return;
    if (v.paused) {
      playingRef.current = true;
      setPlaying(true);
      void v.play()?.catch(() => {
        playingRef.current = false;
        setPlaying(false);
      });
    } else {
      v.pause();
    }
  }

  function resetRally() {
    setStart(null);
    setEnd(null);
    setMarks([]);
    setPending(null);
    setSide(null);
    setResponsible(null);
    setAskFault(false);
    setHeld(null);
    setSent([]);
    setQuestionAlert(null);
    setDropAsk(false);
  }

  function markStart() {
    setTagProblem(null);
    setStart(frame);
    if (end !== null && end <= frame) setEnd(null);
  }

  function markEnd() {
    if (start === null) return setTagProblem('Press Rally start first.');
    if (frame <= start) return setTagProblem('Rally end must be after its start.');
    setTagProblem(null);
    setEnd(frame);
  }

  function addMark(mark: EventLabel) {
    setMarks((m) => [...m, mark].sort((a, b) => a.frame - b.frame));
    setPending(null);
    setAcross('');
    setAlong('');
  }

  function bounce(visible: boolean) {
    if (pending?.kind !== 'bounce') return;
    const x = Number(across);
    const y = Number(along);
    const xy: [number, number] | null = across.trim() && along.trim() && Number.isFinite(x) && Number.isFinite(y) ? [x, y] : null;
    addMark({ type: 'bounce', frame: pending.frame, visible, court_xy_m: xy });
  }

  async function save(ending: Ending, faultKind: LabelFaultKind | null = null) {
    if (busy || start === null || end === null) return;
    if (ending !== 'replay' && side === null) return setQuestionAlert('Choose who won the rally first.');
    if (ending === 'fault' && faultKind === null) {
      setQuestionAlert(null);
      return setAskFault(true);
    }
    setBusy(true);
    setQuestionAlert(null);
    const outcome = {
      ending,
      winning_side: ending === 'replay' ? null : side,
      responsible_player: ending === 'replay' ? null : responsible,
      fault_kind: ending === 'fault' ? faultKind : null,
    };
    const span = { start, end };
    let saving = held;
    let done = sent;
    let rest = marks;
    const local = (events: EventLabel[]): SavedRally => ({ id: `r${number}`, start_frame: start, end_frame: end, outcome: saving ?? outcome, events });

    // Read what the server holds; false when that read fails too.
    const check = async (): Promise<boolean> => {
      try {
        const s = await api.labelSession(match.id);
        unsure.current = false;
        if (s.version === known.current) return true; // nothing was stored since the state we hold
        const r = reconcile(s, span, marks);
        known.current = r.version;
        saving = r.held?.outcome ?? null;
        done = r.held?.events ?? [];
        rest = r.rest;
        setSaved(r.others);
        setHeld(saving);
        setSent(done);
        setMarks(rest);
        return true;
      } catch {
        return false;
      }
    };

    if (unsure.current && !(await check())) {
      setQuestionAlert('The label was not saved because the connection dropped. Try again.');
      setBusy(false);
      return;
    }
    if (saving && !sameOutcome(saving, outcome)) {
      const was = ENDING_WORDS[saving.ending];
      setQuestionAlert(`Rally ${number} is already saved as ${was.toLowerCase()}, and saved labels cannot be changed yet. Choose ${was} to save its events.`);
      setBusy(false);
      return;
    }
    try {
      if (!saving) {
        known.current = (await api.labelEvent(match.id, { type: 'rally', start_frame: start, end_frame: end, outcome })).version;
        saving = outcome;
        setHeld(outcome);
      }
      while (rest.length > 0) {
        const [next, ...after] = rest as [EventLabel, ...EventLabel[]];
        known.current = (await api.labelEvent(match.id, next)).version;
        done = [...done, next];
        rest = after;
        setSent(done);
        setMarks(after);
      }
    } catch (e) {
      const problem = saveProblem(e, saved, span);
      if (mayHaveLanded(e)) {
        unsure.current = true;
        await check();
      }
      if (!(saving && rest.length === 0)) {
        setQuestionAlert(problem);
        setBusy(false);
        return;
      }
    }
    await finish(local([...done, ...rest]));
    setSaid(`Rally ${number} saved.`);
  }

  /** The rally is on the server: list it as saved (the server's copy; the local one if that read fails). */
  async function finish(fallback: SavedRally) {
    try {
      const s = await api.labelSession(match.id);
      known.current = s.version;
      setSaved(inOrder(s.document.rallies));
    } catch {
      setSaved((all) => inOrder([...all, fallback]));
    }
    resetRally();
    setBusy(false);
  }

  /** Esc, then Yes: drop the unsaved marks. A rally the server already holds stays saved. */
  async function dropRally() {
    if (held === null || start === null || end === null) return resetRally();
    setBusy(true);
    await finish({ id: `r${number}`, start_frame: start, end_frame: end, outcome: held, events: sent });
  }

  async function exportLabels() {
    setExportProblem(null);
    setExportStatus('');
    try {
      const doc = await api.labelExport(match.id);
      download(`labels-${match.id}.json`, doc);
      const events = doc.rallies.reduce((n, r) => n + r.events.length, 0);
      setExportStatus(exportLine(doc.rallies.length, events, start !== null ? number : null));
    } catch (e) {
      const ref = e instanceof ApiError && e.supportRef ? ` Reference: ${e.supportRef}` : '';
      setExportProblem(`The labels could not be exported. Try again.${ref}`);
    }
  }

  const chooseSingleKeys = (on: boolean) => {
    setSingleKeys(on);
    writeSingleKeys(on);
  };

  function openKeys() {
    keysOpener.current = document.activeElement as HTMLElement | null;
    setKeysOpen(true);
  }

  // Keys (flows-sprint-03 §6, R3-8 amendments): T-01's 1/2 for "Won by" and 3-6 for players.
  const onKey = useRef<(e: KeyboardEvent) => void>(() => {});
  onKey.current = (e: KeyboardEvent) => {
    if (keysOpen || e.ctrlKey || e.metaKey || e.altKey) return;
    const t = e.target instanceof HTMLElement ? e.target : null;
    if (t && (t.closest('input, textarea, select, [contenteditable="true"]') || t.isContentEditable)) return;
    if (e.key === 'Escape') {
      if (pending) setPending(null);
      else if (start !== null && !busy) setDropAsk(true);
      return;
    }
    if (e.key === ' ') {
      if (t?.closest('button, a')) return; // Space activates the focused control
      e.preventDefault();
      togglePlay();
      return;
    }
    if (!singleKeys) return;
    const key = e.key.length === 1 ? e.key.toLowerCase() : e.key;
    const slotFor = (k: string) => players[Number(k) - 3];
    switch (key) {
      case ',':
        return step(-1);
      case '.':
        return step(1);
      case '<':
        return step(-Math.round(fps));
      case '>':
        return step(Math.round(fps));
      case 's':
        return markStart();
      case 'e':
        return markEnd();
      case 'h':
        return setPending({ kind: 'hit', frame });
      case 'b':
        return setPending({ kind: 'bounce', frame });
      case '?':
        return openKeys();
      case '1':
      case '2':
        if (end !== null) setSide(key === '1' ? names.mySide : otherSide);
        return;
      case '3':
      case '4':
      case '5':
      case '6': {
        const s = slotFor(key);
        if (!s) return;
        if (pending?.kind === 'hit') addMark({ type: 'hit', frame: pending.frame, hitter: s, facets: {} });
        else if (end !== null) setResponsible((r) => (r === s ? null : s));
        return;
      }
      default:
        return;
    }
  };
  useEffect(() => {
    const handler = (e: KeyboardEvent) => onKey.current(e);
    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, []);

  const dropQuestion = held
    ? `Rally ${number} is already saved. Drop its ${plural(marks.length, 'unsaved event', 'unsaved events')}?`
    : `Drop rally ${number} and its ${plural(marks.length, 'event', 'events')}?`;
  const bySide = (s: Side) => players.filter((p) => p.startsWith(s));
  const playerButtons = (onPick: (slot: string) => void, pressed?: string | null) =>
    [names.mySide, otherSide].map((s) => (
      <div key={s} role="group" aria-label={s === names.mySide ? 'Your side' : 'Other side'} className="button-row">
        <span className="button-row__label" aria-hidden="true">
          {s === names.mySide ? 'Your side' : 'Other side'}
        </span>
        {bySide(s).map((slot) => (
          <button
            key={slot}
            type="button"
            className="button button--secondary tag-button"
            aria-pressed={pressed === undefined ? undefined : pressed === slot}
            aria-keyshortcuts={String(players.indexOf(slot) + 3)}
            onClick={() => onPick(slot)}
          >
            {nickname(slot)}
          </button>
        ))}
      </div>
    ));

  return (
    <div className="stack full-tag">
      <p>Internal labelling tool. Labels are saved as you go.</p>
      {videoProblem ? (
        <p role="alert" className="notice notice--error">
          {videoProblem}
        </p>
      ) : null}
      {videoUrl ? (
        <video
          ref={video}
          src={videoUrl}
          muted
          playsInline
          preload="auto"
          className="quick-tag__player"
          aria-label={`Video of ${match.title}`}
          onLoadedMetadata={(e) => {
            e.currentTarget.currentTime = (frame + 0.5) / fps;
          }}
          onTimeUpdate={(e) => {
            if (playingRef.current) setFrame(Math.min(last, Math.floor(e.currentTarget.currentTime * fps)));
          }}
          onPause={(e) => {
            playingRef.current = false;
            setPlaying(false);
            setFrame(Math.min(last, Math.floor(e.currentTarget.currentTime * fps)));
          }}
          onError={() => {
            setVideoUrl(null);
            setVideoProblem('This video link no longer works. Frame numbers still work; reload the page to load the video again.');
          }}
        />
      ) : null}
      <p className="frame-readout">{`Frame ${frame} of ${frameCount} · ${frameTime(frame, fps)}`}</p>
      <p role="status" className="visually-hidden">
        {said}
      </p>
      <div role="group" aria-label="Move through the video" className="button-row">
        <button type="button" className="button button--secondary" aria-keyshortcuts="," onClick={() => step(-1)}>
          Previous frame
        </button>
        <button type="button" className="button button--secondary" aria-keyshortcuts="." onClick={() => step(1)}>
          Next frame
        </button>
        <button type="button" className="button button--secondary" aria-keyshortcuts="<" onClick={() => step(-Math.round(fps))}>
          Back 1 second
        </button>
        <button type="button" className="button button--secondary" aria-keyshortcuts=">" onClick={() => step(Math.round(fps))}>
          Forward 1 second
        </button>
        <button type="button" className="button button--secondary" aria-keyshortcuts="Space" aria-pressed={playing} onClick={togglePlay}>
          Play or pause
        </button>
      </div>

      <div role="group" aria-label="Tag at this frame" className="button-row">
        <button type="button" className="button tag-button" aria-pressed={start !== null} aria-keyshortcuts="s" onClick={markStart}>
          Rally start
        </button>
        <button type="button" className="button tag-button" aria-pressed={end !== null} aria-keyshortcuts="e" onClick={markEnd}>
          Rally end
        </button>
        <button type="button" className="button tag-button" aria-keyshortcuts="h" onClick={() => setPending({ kind: 'hit', frame })}>
          Hit
        </button>
        <button type="button" className="button tag-button" aria-keyshortcuts="b" onClick={() => setPending({ kind: 'bounce', frame })}>
          Bounce
        </button>
      </div>
      {tagProblem ? (
        <p role="alert" className="notice notice--error">
          {tagProblem}
        </p>
      ) : null}

      {pending?.kind === 'hit' ? (
        <div role="group" aria-label="Who hit it?" className="stack panel">
          <p>{`Who hit it at frame ${pending.frame}?`}</p>
          {playerButtons((slot) => addMark({ type: 'hit', frame: pending.frame, hitter: slot, facets: {} }))}
        </div>
      ) : null}
      {pending?.kind === 'bounce' ? (
        <div className="stack panel">
          <p>{`Bounce at frame ${pending.frame}. Where on the court (metres, optional):`}</p>
          <div className="button-row">
            <p className="field">
              <label htmlFor="bounce-across">Across (metres)</label>
              <input id="bounce-across" type="number" step="any" inputMode="decimal" value={across} onChange={(e) => setAcross(e.currentTarget.value)} />
            </p>
            <p className="field">
              <label htmlFor="bounce-along">Along (metres)</label>
              <input id="bounce-along" type="number" step="any" inputMode="decimal" value={along} onChange={(e) => setAlong(e.currentTarget.value)} />
            </p>
          </div>
          <div role="group" aria-label="Ball in view?" className="button-row">
            <span className="button-row__label" aria-hidden="true">
              Ball in view?
            </span>
            <button type="button" className="button button--secondary tag-button" onClick={() => bounce(true)}>
              Yes
            </button>
            <button type="button" className="button button--secondary tag-button" onClick={() => bounce(false)}>
              No
            </button>
          </div>
        </div>
      ) : null}

      {start !== null && end !== null ? (
        <div role="group" aria-label={`How did rally ${number} end?`} aria-busy={busy} className="stack panel">
          <p className="full-tag__question">{`How did rally ${number} end?`}</p>
          {questionAlert ? (
            <p role="alert" className="notice notice--error">
              {questionAlert}
            </p>
          ) : null}
          <div role="group" aria-label="Won by" className="button-row">
            <span className="button-row__label" aria-hidden="true">
              Won by
            </span>
            <button type="button" className="button button--secondary tag-button" aria-pressed={side === names.mySide} aria-keyshortcuts="1" onClick={() => setSide(names.mySide)}>
              Your side
            </button>
            <button type="button" className="button button--secondary tag-button" aria-pressed={side === otherSide} aria-keyshortcuts="2" onClick={() => setSide(otherSide)}>
              Other side
            </button>
          </div>
          <div role="group" aria-label="Who ended it (optional)" className="stack">
            <p>Who ended it (optional)</p>
            {playerButtons((slot) => setResponsible((r) => (r === slot ? null : slot)), responsible)}
          </div>
          <div role="group" aria-label="Ending (saves the rally)" className="button-row">
            {ENDINGS.map((ending) => (
              <button key={ending} type="button" className="button tag-button" onClick={() => void save(ending)}>
                {ENDING_WORDS[ending]}
              </button>
            ))}
          </div>
          {askFault ? (
            <div role="group" aria-label="Fault kind" className="button-row">
              {FAULT_KINDS.map((k) => (
                <button key={k} type="button" className="button button--secondary tag-button" onClick={() => void save('fault', k)}>
                  {FAULT_WORDS[k]}
                </button>
              ))}
            </div>
          ) : null}
        </div>
      ) : null}

      {dropAsk ? (
        <div role="group" aria-label={dropQuestion} className="stack panel">
          <p>{dropQuestion}</p>
          <div className="button-row">
            <button type="button" className="button button--secondary" onClick={() => void dropRally()}>
              Yes
            </button>
            <button type="button" className="button button--secondary" onClick={() => setDropAsk(false)}>
              No
            </button>
          </div>
        </div>
      ) : null}

      {start !== null ? (
        <section className="stack" aria-labelledby="full-tag-current">
          <h2 id="full-tag-current">{`Rally ${number} so far`}</h2>
          <p>{end === null ? `Rally ${number}: frames ${start} to …` : `Rally ${number}: frames ${start} to ${end}`}</p>
          {marks.length ? (
            <ol className="full-tag__marks">
              {marks.map((m, i) => (
                <li key={`${m.type}-${m.frame}-${i}`}>
                  <span>{markLine(m, nickname)}</span>{' '}
                  <button
                    type="button"
                    className="button button--secondary"
                    aria-label={`Remove ${m.type} at frame ${m.frame}`}
                    onClick={() => setMarks((all) => all.filter((_, j) => j !== i))}
                  >
                    Remove
                  </button>
                </li>
              ))}
            </ol>
          ) : null}
        </section>
      ) : saved.length === 0 ? (
        <p>No rallies labelled yet. Step to the first serve and press Rally start.</p>
      ) : null}

      {saved.length ? (
        <section className="stack" aria-labelledby="full-tag-saved">
          <h2 id="full-tag-saved">Saved rallies</h2>
          <ol className="full-tag__saved">
            {saved.map((r, i) => (
              <li key={r.id}>{savedLine(r, i + 1, nickname)}</li>
            ))}
          </ol>
          <p>Saved labels cannot be changed yet.</p>
        </section>
      ) : null}

      <div className="button-row">
        <button type="button" className="button button--secondary" onClick={() => void exportLabels()}>
          Export labels
        </button>
        <button type="button" className="button button--secondary" aria-keyshortcuts="?" onClick={openKeys}>
          Keys
        </button>
      </div>
      {exportProblem ? (
        <p role="alert" className="notice notice--error">
          {exportProblem}
        </p>
      ) : null}
      {exportStatus ? <p className="notice notice--info">{exportStatus}</p> : null}
      {keysOpen ? (
        <FullTagKeys
          singleKeys={singleKeys}
          onSingleKeys={chooseSingleKeys}
          onClose={() => {
            setKeysOpen(false);
            keysOpener.current?.focus?.();
          }}
        />
      ) : null}
    </div>
  );
}
