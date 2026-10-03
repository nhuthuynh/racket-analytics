'use client';

// Upload a match video (ST-010 with ST-008). A file picker button is the only required
// input, so no dragging is needed (SC 2.5.7 [DPA/DESIGN-05]). Progress announcements are
// throttled to 10% steps (component checklist §6).
import { useEffect, useReducer, useRef, useState, type ChangeEvent } from 'react';
import { UploadProgressView } from '@/components/UploadProgressView';
import {
  initialUploadProgress,
  percentOf,
  uploadProgressReducer,
} from '@/lib/upload/progress';
import { failureFor } from '@/lib/upload/tus-policy';
import { startTusUpload, type StartUpload, type UploadHandle } from '@/lib/upload/tus-upload';

export function UploadPanel({
  matchId,
  onUploaded,
  startUpload = startTusUpload,
  resuming = false,
  onStarted,
}: {
  matchId: string;
  onUploaded: () => void;
  onStarted?: () => void;
  startUpload?: StartUpload;
  /** The server already has an upload session for this match (after a reload). */
  resuming?: boolean;
}) {
  const [progress, dispatch] = useReducer(uploadProgressReducer, initialUploadProgress);
  const [fileError, setFileError] = useState<string | null>(null);
  const [announcement, setAnnouncement] = useState('');
  const handle = useRef<UploadHandle | null>(null);
  const lastAnnouncedTen = useRef(0);

  useEffect(() => () => handle.current?.abort(), []);

  const percent = percentOf(progress);
  useEffect(() => {
    if (progress.phase !== 'uploading') return;
    const ten = Math.floor(percent / 10);
    if (ten > lastAnnouncedTen.current && percent < 100) {
      lastAnnouncedTen.current = ten;
      setAnnouncement(`Upload ${ten * 10}% done`);
    }
  }, [percent, progress.phase]);

  function onFile(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    if (!file.type.startsWith('video/')) {
      setFileError('Choose a video file, for example an MP4 or MOV from your camera app.');
      return;
    }
    setFileError(null);
    lastAnnouncedTen.current = 0;
    dispatch({ type: 'started', bytesTotal: file.size });
    setAnnouncement('Upload started');
    onStarted?.();
    handle.current = startUpload(file, matchId, {
      onProgress: (sent, total) => dispatch({ type: 'progressed', bytesSent: sent, bytesTotal: total }),
      onSuccess: () => {
        dispatch({ type: 'completed' });
        setAnnouncement('Upload complete');
        onUploaded();
      },
      onError: (status) => {
        dispatch({ type: 'failed', reason: failureFor(status) });
        setAnnouncement('Upload interrupted');
      },
    });
  }

  function onRetry() {
    dispatch({ type: 'retried' });
    setAnnouncement('Upload restarted');
    handle.current?.retry();
  }

  const choosing = progress.phase === 'idle';

  return (
    <section aria-labelledby="upload-title" className="stack panel">
      <h2 id="upload-title">Upload the video</h2>
      {choosing ? (
        <div className={`field${fileError ? ' field--error' : ''}`}>
          <label htmlFor="match-video" className="field__label">
            Match video
          </label>
          <p id="match-video-hint" className="field__hint">
            {resuming
              ? 'An upload was started earlier. Choose the same video file to continue from where it stopped.'
              : 'Choose the video from your phone or computer. The upload starts straight away and carries on if the connection drops.'}
          </p>
          {fileError ? (
            <p id="match-video-error" className="field__error">
              <span className="visually-hidden">Error: </span>
              {fileError}
            </p>
          ) : null}
          <input
            id="match-video"
            name="match-video"
            type="file"
            accept="video/*"
            className="file-input"
            onChange={onFile}
            aria-describedby={fileError ? 'match-video-hint match-video-error' : 'match-video-hint'}
            aria-invalid={fileError ? true : undefined}
          />
        </div>
      ) : null}
      <UploadProgressView progress={progress} onRetry={onRetry} />
      <p className="visually-hidden" aria-live="polite" data-testid="upload-announcer">
        {announcement}
      </p>
    </section>
  );
}
