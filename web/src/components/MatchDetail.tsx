'use client';

// Match detail (ST-010): status, upload and probe facts. The server component renders the
// first state; this component refreshes it until the probe has a result.
import { useCallback, useEffect, useState } from 'react';
import { MatchFacts } from '@/components/MatchFacts';
import { UploadPanel } from '@/components/UploadPanel';
import type { ApiClient } from '@/lib/api/client';
import { browserApi } from '@/lib/api/browser';
import type { Match } from '@/lib/api/types';
import type { StartUpload } from '@/lib/upload/tus-upload';

type Api = Pick<ApiClient, 'getMatch'>;

const DEFAULT_POLL_MS = 2_000;

function needsRefresh(match: Match): boolean {
  return match.status === 'uploading' || (match.status === 'video_received' && match.media === null);
}

export function MatchDetail({
  initialMatch,
  api = browserApi,
  pollMs = DEFAULT_POLL_MS,
  startUpload,
}: {
  initialMatch: Match;
  api?: Api;
  pollMs?: number;
  startUpload?: StartUpload;
}) {
  const [match, setMatch] = useState(initialMatch);
  const [uploadStartedHere, setUploadStartedHere] = useState(false);
  const [resuming] = useState(initialMatch.status === 'uploading');

  const refresh = useCallback(async () => {
    try {
      setMatch(await api.getMatch(initialMatch.id));
    } catch {
      // Keep the last known state; the next tick tries again.
    }
  }, [api, initialMatch.id]);

  const polling = needsRefresh(match);
  useEffect(() => {
    if (!polling) return;
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout>;
    const loop = () => {
      timer = setTimeout(async () => {
        await refresh();
        if (!cancelled) loop();
      }, pollMs);
    };
    loop();
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [polling, pollMs, refresh]);

  const showUpload =
    uploadStartedHere || match.status === 'awaiting_upload' || match.status === 'uploading';

  return (
    <div className="stack">
      <h1>{match.title}</h1>
      <MatchFacts match={match} />
      {showUpload ? (
        <UploadPanel
          matchId={match.id}
          startUpload={startUpload}
          resuming={resuming}
          onStarted={() => {
            setUploadStartedHere(true);
            setMatch((m) => (m.status === 'awaiting_upload' ? { ...m, status: 'uploading' } : m));
          }}
          onUploaded={() => void refresh()}
        />
      ) : null}
    </div>
  );
}
