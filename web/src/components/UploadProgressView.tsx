// Upload progress (component checklist §6; FR-022 core). Presentational only.
import { formatProgressBytes } from '@/lib/format';
import { percentOf, type UploadProgress } from '@/lib/upload/progress';

const FAILURE_TEXT = {
  network: 'The upload stopped. Check your connection, then try again. It continues where it stopped.',
  unknown: 'The upload stopped because of a problem on our side. Try again in a moment.',
  rejected: 'The upload was not accepted. Check that the file is a match video, then reload the page.',
  conflict:
    'This match already has an upload in progress. Continue it on the device that started it.',
} as const;

export function UploadProgressView({
  progress,
  onRetry,
}: {
  progress: UploadProgress;
  onRetry: () => void;
}) {
  if (progress.phase === 'idle') return null;

  const percent = percentOf(progress);
  const bytes = formatProgressBytes(progress.bytesSent, progress.bytesTotal);
  const retryable = progress.failure === 'network' || progress.failure === 'unknown';

  return (
    <div className="upload-progress">
      <p className="upload-progress__label" id="upload-progress-label">
        {progress.phase === 'complete' ? 'Upload complete' : 'Upload progress'}
      </p>
      <div
        role="progressbar"
        className="progress"
        aria-labelledby="upload-progress-label"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={percent}
        aria-valuetext={`${percent}%, ${bytes}`}
      >
        <div className="progress__fill" style={{ inlineSize: `${percent}%` }} />
      </div>
      <p className="upload-progress__text">{`${percent}% · ${bytes}`}</p>
      {progress.phase === 'failed' && progress.failure ? (
        <div className="upload-progress__failure">
          <p className="field__error">
            <span className="visually-hidden">Error: </span>
            {FAILURE_TEXT[progress.failure]}
          </p>
          {retryable ? (
            <button type="button" className="button button--secondary" onClick={onRetry}>
              Try the upload again
            </button>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
