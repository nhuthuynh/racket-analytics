'use client';

// Upload panel U-01..U-04 (ST-017, ST-018; flows-sprint-01 §6; FR-022, FR-023).
// U-01 progress with % and amount as text, a plain state line and an estimate only after 10 s;
// pauses offline and resumes from the server offset. U-02 "Checking video…". U-03 refusals in
// the error-summary pattern. U-04 resume from the server's unfinished upload by choosing the
// same video. Copy never promises the upload continues after the tab is closed (OQ-18).
// A file button is the only way to choose a video: no dragging needed (SC 2.5.7, NFR-030).
import { useCallback, useEffect, useRef, useState, type ChangeEvent } from 'react';
import { ErrorSummary } from '@/components/ErrorSummary';
import type { Match, UploadPolicy } from '@/lib/api/types';
import { formatBytes, formatDurationCap, formatProgressAmount, formatSizeCap } from '@/lib/format';
import { setActiveUpload } from '@/lib/upload/activity';
import { createEstimate, estimateText, recordProgress, remainingMs, type Estimate } from '@/lib/upload/estimate';
import { NOT_A_VIDEO, NOTHING_SAVED, rejectionMessage, uploadRateLimitMessage } from '@/lib/upload/messages';
import { checkSameVideo } from '@/lib/upload/same-file';
import { uploadProblemFor } from '@/lib/upload/tus-policy';
import { startTransfer as defaultStartTransfer, type StartTransfer, type TransferHandle } from '@/lib/upload/transfer';

type Mode = 'uploading' | 'paused-offline' | 'paused-user' | 'resuming' | 'trouble' | 'stopped';

type View =
  | { kind: 'idle' }
  | { kind: 'transfer'; mode: Mode; sent: number; total: number }
  | { kind: 'checking' };

interface Problem {
  message: string;
  /** U-03 refusals: nothing was kept from the file. */
  nothingSaved: boolean;
  /** The summary link goes to this page instead of the file input. */
  href?: string;
}

const STATE_TEXT: Record<Mode, string> = {
  uploading: 'Uploading',
  'paused-offline': 'Paused: waiting for connection',
  'paused-user': 'Paused',
  resuming: 'Resuming',
  trouble: "Paused: we're having trouble sending your video. Retrying…",
  stopped: 'Stopped',
};

const FILE_INPUT = 'video-file';
const TROUBLE_AFTER_RETRIES = 3;
const LARGE_FILE_BYTES = 1_000_000_000;

const expiryFormat = new Intl.DateTimeFormat('en-GB', {
  day: 'numeric',
  month: 'long',
  hour: '2-digit',
  minute: '2-digit',
  hourCycle: 'h23',
});

function percent(sent: number, total: number): number {
  return total > 0 ? Math.min(100, Math.floor((sent / total) * 100)) : 0;
}

export function MatchUpload({
  match,
  policy,
  initialFile = null,
  startTransfer = defaultStartTransfer,
  onUploaded,
  onProblem,
}: {
  match: Match;
  policy: UploadPolicy;
  /** The file chosen on Q-06, handed over after "Create match and upload". */
  initialFile?: File | null;
  startTransfer?: StartTransfer;
  onUploaded: () => void;
  /** Tells the page whether an error summary is shown (title prefix "Error: "). */
  onProblem: (shown: boolean) => void;
}) {
  const [view, setView] = useState<View>({ kind: 'idle' });
  const [problem, setProblemState] = useState<Problem | null>(null);
  // Counts every reported problem, so a repeated identical one moves focus again (PD-R3-01).
  const [attempt, setAttempt] = useState(0);
  const setProblem = useCallback((next: Problem | null) => {
    setProblemState(next);
    if (next) setAttempt((n) => n + 1);
  }, []);
  const [announcement, setAnnouncement] = useState('');
  const [tipHidden, setTipHidden] = useState(false);
  const [, setEstimateTick] = useState(0);
  const handle = useRef<HTMLInputElement>(null);
  const transfer = useRef<TransferHandle | null>(null);
  const estimate = useRef<Estimate | null>(null);
  const retries = useRef(0);
  const lastTen = useRef(0);
  const started = useRef(false);
  const progressed = useRef(false);
  /** Bytes the server has stored (resume offset or last accepted chunk), not merely sent. */
  const accepted = useRef(0);
  const viewRef = useRef(view);
  viewRef.current = view;

  const serverRejection = match.rejection && view.kind === 'idle' && !problem ? match.rejection : null;
  const shownProblem: Problem | null =
    problem ?? (serverRejection ? { message: rejectionMessage(serverRejection.code, policy), nothingSaved: true } : null);

  const hasProblem = shownProblem !== null;
  useEffect(() => {
    onProblem(hasProblem);
  }, [hasProblem, onProblem]);

  const stopTracking = useCallback(() => {
    setActiveUpload(null);
  }, []);

  useEffect(
    () => () => {
      transfer.current?.abort();
      setActiveUpload(null);
    },
    [],
  );

  const begin = useCallback(
    (file: File, from: { resumeUrl?: string; offset?: number }) => {
      if (file.size > policy.maxBytes) {
        setProblem({ message: rejectionMessage('too_large', policy), nothingSaved: true });
        return;
      }
      setProblem(null);
      retries.current = 0;
      lastTen.current = 0;
      progressed.current = false;
      const offset = from.offset ?? 0;
      accepted.current = offset;
      estimate.current = createEstimate(performance.now(), offset);
      setView({ kind: 'transfer', mode: 'uploading', sent: offset, total: file.size });
      const h = startTransfer({
        file,
        ...(from.resumeUrl ? { resumeUrl: from.resumeUrl } : { matchId: match.id }),
        policy,
        callbacks: {
          onProgress: (sent, total) => {
            // Bytes sent are not progress the server kept: a PATCH can send every byte and then
            // fail with 500. Only onChunkAccepted resets the retry count (PD-R3-03).
            progressed.current = true;
            if (estimate.current) estimate.current = recordProgress(estimate.current, performance.now(), sent);
            setEstimateTick((n) => n + 1);
            setView((v) => {
              if (v.kind !== 'transfer') return v;
              const mode = v.mode === 'resuming' ? 'uploading' : v.mode;
              return { ...v, mode, sent: Math.max(v.sent, sent), total };
            });
            const ten = Math.floor(percent(sent, total) / 10);
            if (ten > lastTen.current && ten < 10) {
              lastTen.current = ten;
              setAnnouncement(`Upload ${ten * 10}% done`);
            }
            setActiveUpload({ title: match.title, percent: percent(sent, total), stop: () => transfer.current?.abort() });
          },
          onChunkAccepted: (bytesAccepted) => {
            retries.current = 0;
            accepted.current = Math.max(accepted.current, bytesAccepted);
            setView((v) => (v.kind === 'transfer' && v.mode === 'trouble' ? { ...v, mode: 'uploading' } : v));
          },
          onSuccess: () => {
            transfer.current = null;
            stopTracking();
            setView({ kind: 'checking' });
            setAnnouncement('Upload complete');
            onUploaded();
          },
          onRetrying: () => {
            retries.current += 1;
            if (retries.current >= TROUBLE_AFTER_RETRIES) {
              setView((v) => (v.kind === 'transfer' ? { ...v, mode: 'trouble' } : v));
            }
          },
          onError: (status, detail) => {
            const reason = uploadProblemFor(status, detail);
            if (reason === 'network' && typeof navigator !== 'undefined' && navigator.onLine === false) {
              setView((v) => (v.kind === 'transfer' ? { ...v, mode: 'paused-offline' } : v));
              return;
            }
            stopTracking();
            transfer.current = null;
            if (reason === 'not_a_video' || reason === 'too_large') {
              setView({ kind: 'idle' });
              setProblem({ message: reason === 'too_large' ? rejectionMessage('too_large', policy) : NOT_A_VIDEO, nothingSaved: true });
              return;
            }
            // Refused before any byte was sent (quota, creation rate, or another upload already
            // open): nothing was started, so no progress or "leaving" copy, just the chooser
            // (PD-R2-02).
            if (reason === 'quota' || reason === 'rate_limited' || (reason === 'conflict' && !progressed.current)) {
              setView({ kind: 'idle' });
            } else {
              setView((v) => (v.kind === 'transfer' ? { ...v, mode: 'stopped' } : v));
            }
            setProblem({
              nothingSaved: false,
              ...(reason === 'quota' ? { href: '/matches' } : {}),
              message:
                reason === 'expired'
                  ? 'This upload has expired. Start the upload again.'
                  : reason === 'conflict'
                    ? 'This match already has an unfinished upload. Reload the page to continue it.'
                    : reason === 'quota'
                      ? 'You have too many unfinished uploads. Finish one of them from Your matches, then try again.'
                      : reason === 'rate_limited'
                        ? `${uploadRateLimitMessage(detail?.retryAt ?? null)}${
                            detail?.supportRef ? ` Reference: ${detail.supportRef}` : ''
                          }`
                        : reason === 'network'
                          ? 'The upload stopped. Check your connection, then try again. It continues where it stopped.'
                          : accepted.current > 0
                            ? 'Sorry, the upload stopped because of a problem on our side. Your progress is saved. Try again.'
                            : 'Sorry, the upload stopped because of a problem on our side. Try again.',
            });
          },
        },
      });
      transfer.current = h;
      setActiveUpload({ title: match.title, percent: percent(offset, file.size), stop: () => h.abort() });
    },
    [match.id, match.title, onUploaded, policy, setProblem, startTransfer, stopTracking],
  );

  // The file handed over from setup starts at once ("Create match and upload").
  useEffect(() => {
    if (initialFile && !started.current) {
      started.current = true;
      begin(initialFile, {});
    }
  }, [initialFile, begin]);

  // Offline → pause; online → resume from the server's offset (HEAD, then PATCH).
  useEffect(() => {
    const onOffline = () => {
      if (viewRef.current.kind !== 'transfer' || !transfer.current) return;
      transfer.current.pause();
      setView((v) => (v.kind === 'transfer' ? { ...v, mode: 'paused-offline' } : v));
    };
    const onOnline = () => {
      const v = viewRef.current;
      if (v.kind !== 'transfer' || v.mode !== 'paused-offline' || !transfer.current) return;
      estimate.current = createEstimate(performance.now(), v.sent);
      setView({ ...v, mode: 'resuming' });
      transfer.current.resume();
    };
    window.addEventListener('offline', onOffline);
    window.addEventListener('online', onOnline);
    return () => {
      window.removeEventListener('offline', onOffline);
      window.removeEventListener('online', onOnline);
    };
  }, []);

  async function onFile(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = '';
    if (!file) return;
    const pending = match.upload;
    if (pending?.state === 'receiving') {
      if (!(await checkSameVideo(file, pending))) {
        const named = pending.fileName ? `'${pending.fileName}' (${formatBytes(pending.length)})` : `a video of ${formatBytes(pending.length)}`;
        setProblem({ message: `This is not the same video. Choose ${named}.`, nothingSaved: false });
        return;
      }
      begin(file, { resumeUrl: pending.resumeUrl, offset: pending.offset });
      return;
    }
    begin(file, {});
  }

  function togglePause() {
    const v = viewRef.current;
    if (v.kind !== 'transfer' || !transfer.current) return;
    if (v.mode === 'paused-user') {
      estimate.current = createEstimate(performance.now(), v.sent);
      setView({ ...v, mode: 'resuming' });
      transfer.current.resume();
    } else {
      transfer.current.pause();
      setView({ ...v, mode: 'paused-user' });
    }
  }

  function tryAgain() {
    const v = viewRef.current;
    if (v.kind !== 'transfer') return;
    setProblem(null);
    if (transfer.current) {
      setView({ ...v, mode: 'resuming' });
      transfer.current.resume();
    }
  }

  const pending = match.upload ?? null;
  const showChooser = view.kind === 'idle' || (view.kind === 'transfer' && view.mode === 'stopped' && !transfer.current);
  const left =
    view.kind === 'transfer' && estimate.current && (view.mode === 'uploading')
      ? remainingMs(estimate.current, view.total)
      : null;

  return (
    <section aria-labelledby="upload-title" className="stack panel">
      <h2 id="upload-title">Video upload</h2>
      {shownProblem ? (
        <ErrorSummary
          errors={[{ field: FILE_INPUT, message: shownProblem.message, href: shownProblem.href }]}
          attempt={attempt}
        >
          {shownProblem.nothingSaved ? <p>{NOTHING_SAVED}</p> : null}
        </ErrorSummary>
      ) : null}

      {view.kind === 'transfer' ? (
        <div className="upload-progress">
          <div
            role="progressbar"
            className="progress"
            aria-label="Upload progress"
            aria-valuemin={0}
            aria-valuemax={100}
            aria-valuenow={percent(view.sent, view.total)}
            aria-valuetext={`${percent(view.sent, view.total)}%, ${formatProgressAmount(view.sent, view.total)}`}
          >
            <div className="progress__fill" style={{ inlineSize: `${percent(view.sent, view.total)}%` }} />
          </div>
          <p className="upload-progress__text">
            {`${percent(view.sent, view.total)}% · ${formatProgressAmount(view.sent, view.total)}`}
          </p>
          {/* The state line is the live region: state changes are announced politely. */}
          <p className="upload-progress__state" role="status">
            {STATE_TEXT[view.mode]}
          </p>
          {left !== null ? <p>{estimateText(left)}</p> : null}
          {view.mode !== 'stopped' ? (
            <div className="button-row">
              <button type="button" className="button button--secondary" onClick={togglePause}>
                {view.mode === 'paused-user' ? 'Resume' : 'Pause'}
              </button>
            </div>
          ) : transfer.current ? (
            <div className="button-row">
              <button type="button" className="button" onClick={tryAgain}>
                Try again
              </button>
            </div>
          ) : null}
          <p>
            You can use other pages while this tab stays open. If you close it, you can resume later
            from this page by choosing the same video.
          </p>
          {view.total > LARGE_FILE_BYTES && !tipHidden ? (
            <p className="notice notice--info">
              Keep your screen on until the upload finishes.{' '}
              <button type="button" className="link-button" onClick={() => setTipHidden(true)}>
                Hide this tip
              </button>
            </p>
          ) : null}
        </div>
      ) : null}

      {view.kind === 'checking' ? (
        <div className="stack">
          <p className="upload-progress__state" role="status">
            Checking video…
          </p>
          <p>We&apos;re reading the video&apos;s details. This usually takes less than a minute.</p>
        </div>
      ) : null}

      {showChooser ? (
        <div className="stack">
          {shownProblem?.nothingSaved ? (
            <p>
              <a
                href={`#${FILE_INPUT}`}
                className="inline-target"
                onClick={(event) => {
                  event.preventDefault();
                  handle.current?.focus();
                }}
              >
                Choose a different video
              </a>
            </p>
          ) : null}
          {pending?.state === 'receiving' ? (
            <p>
              To continue, choose the same video:{' '}
              <strong>
                {pending.fileName ? `${pending.fileName} (${formatBytes(pending.length)})` : formatBytes(pending.length)}
              </strong>
              .
            </p>
          ) : pending?.state === 'expired' ? (
            <p>{`This upload expired on ${expiryFormat.format(new Date(pending.expiresAt))}. Start the upload again.`}</p>
          ) : (
            <p className="empty-state__title">No video yet</p>
          )}
          <div className="field">
            <label htmlFor={FILE_INPUT} className="field__label">
              Choose video
            </label>
            <p id="video-file-hint" className="field__hint">
              {`MP4 or MOV, up to ${formatSizeCap(policy.maxBytes)} and ${formatDurationCap(policy.maxDurationMs)}.`}
            </p>
            <input
              ref={handle}
              id={FILE_INPUT}
              type="file"
              accept="video/mp4,video/quicktime"
              className="file-input"
              aria-describedby="video-file-hint"
              onChange={(e) => void onFile(e)}
            />
          </div>
        </div>
      ) : null}

      <p>Only you can see this video.</p>
      <p className="visually-hidden" aria-live="polite">
        {announcement}
      </p>
    </section>
  );
}
