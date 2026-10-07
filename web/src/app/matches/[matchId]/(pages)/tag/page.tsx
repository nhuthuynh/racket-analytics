// Quick Tag T-01 (ST-027). Server component: loads the match, its score sheet with the version
// for If-Match, and a short-lived video URL. Not yours / not found → the one not-found page
// (api-sprint-00 §5.2). No video yet → the player is told to wait (NFR-060; sprint-02 §14.3.5).
import Link from 'next/link';
import { notFound, redirect } from 'next/navigation';
import { PageTitle } from '@/components/PageTitle';
import { QuickTag } from '@/components/tagging/QuickTag';
import { ApiError } from '@/lib/api/client';
import { getMatchForRequest, serverApi } from '@/lib/api/server';
import type { Match } from '@/lib/api/types';

type Props = { params: Promise<{ matchId: string }> };

function onApiError(e: unknown): never {
  if (e instanceof ApiError && e.status === 404) notFound();
  if (e instanceof ApiError && e.status === 401) redirect('/');
  throw e;
}

export default async function TagPage({ params }: Props) {
  const { matchId } = await params;
  let match: Match;
  try {
    match = await getMatchForRequest(matchId);
  } catch (e) {
    onApiError(e);
  }
  const back = (
    <p>
      <Link href={`/matches/${match.id}`} className="back-link">
        Back to the match
      </Link>
    </p>
  );
  if (match.status !== 'video_received') {
    return (
      <div className="stack">
        <PageTitle>{`Tag rallies: ${match.title}`}</PageTitle>
        {back}
        <h1>Tag rallies</h1>
        <p>You can tag this match once its video is received.</p>
      </div>
    );
  }
  const api = await serverApi();
  let loaded: Awaited<ReturnType<typeof api.getScoreSheet>>;
  try {
    loaded = await api.getScoreSheet(match.id);
  } catch (e) {
    onApiError(e);
  }
  const media = await api.matchMedia(match.id).catch(() => null);
  return (
    <div className="stack">
      <PageTitle>{`Tag rallies: ${match.title}`}</PageTitle>
      {back}
      <h1>Tag rallies</h1>
      <p className="quick-tag__match">{match.title}</p>
      <QuickTag
        match={match}
        initialSheet={loaded.sheet}
        initialVersion={loaded.version ?? 0}
        videoSrc={media?.url ?? null}
      />
    </div>
  );
}
