'use client';

// Match page M-02 (ST-010; Sprint 1: ST-017, ST-018). Status and facts, plus the upload panel
// (U-01..U-04). After the last byte the page checks the video: it refreshes the match until the
// probe decides (facts, probe failure, or a refusal such as "too long"), then stops.
import { useCallback, useEffect, useState } from 'react';
import { MatchFacts } from '@/components/MatchFacts';
import { MatchUpload } from '@/components/MatchUpload';
import { PageTitle } from '@/components/PageTitle';
import type { ApiClient } from '@/lib/api/client';
import { browserApi } from '@/lib/api/browser';
import { FALLBACK_UPLOAD_POLICY, type Match, type UploadPolicy } from '@/lib/api/types';
import { peekHandOff, takeHandOff } from '@/lib/upload/handoff';
import type { StartTransfer } from '@/lib/upload/transfer';

type Api = Pick<ApiClient, 'getMatch'>;

const DEFAULT_POLL_MS = 2_000;

/** The probe has decided: facts, a probe failure, or a refusal of the file. */
function decided(match: Match): boolean {
  return (
    (match.status === 'video_received' && match.media !== null) ||
    match.status === 'probe_failed' ||
    (match.status === 'awaiting_upload' && !!match.rejection)
  );
}

export function MatchDetail({
  initialMatch,
  policy = FALLBACK_UPLOAD_POLICY,
  api = browserApi,
  pollMs = DEFAULT_POLL_MS,
  startTransfer,
  initialFile,
}: {
  initialMatch: Match;
  policy?: UploadPolicy;
  api?: Api;
  pollMs?: number;
  startTransfer?: StartTransfer;
  /** Test seam; by default the file handed over by the setup flow. */
  initialFile?: File | null;
}) {
  const [match, setMatch] = useState(initialMatch);
  const [checking, setChecking] = useState(false);
  const [problemShown, setProblemShown] = useState(false);
  const [file] = useState(() => (initialFile !== undefined ? initialFile : peekHandOff(initialMatch.id)));

  useEffect(() => {
    if (initialFile === undefined) takeHandOff(initialMatch.id);
  }, [initialFile, initialMatch.id]);

  const refresh = useCallback(async () => {
    try {
      const next = await api.getMatch(initialMatch.id);
      setMatch(next);
      if (decided(next)) setChecking(false);
    } catch {
      // Keep the last known state; the next tick tries again.
    }
  }, [api, initialMatch.id]);

  const polling = checking || (match.status === 'video_received' && match.media === null);
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

  const onUploaded = useCallback(() => setChecking(true), []);

  const showUpload =
    checking ||
    !!file ||
    match.status === 'awaiting_upload' ||
    match.status === 'uploading' ||
    (match.upload !== null && match.upload !== undefined);

  return (
    <div className="stack">
      <PageTitle error={problemShown}>{match.title}</PageTitle>
      <h1>{match.title}</h1>
      <MatchFacts match={match} />
      {showUpload ? (
        <MatchUpload
          // A refusal decided after the upload resets the panel to "choose a video".
          key={match.rejection?.at ?? 'no-rejection'}
          match={match}
          policy={policy}
          initialFile={match.rejection ? null : file}
          startTransfer={startTransfer}
          onUploaded={onUploaded}
          onProblem={setProblemShown}
        />
      ) : null}
    </div>
  );
}
