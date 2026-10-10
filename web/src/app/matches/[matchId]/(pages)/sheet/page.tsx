// Score sheet S-01 (ST-030). Server component: the match and its projected sheet. Not yours
// and not found are the same not-found page (api-sprint-00 §5.2).
import Link from 'next/link';
import { notFound, redirect } from 'next/navigation';
import { PageTitle } from '@/components/PageTitle';
import { ScoreSheetView } from '@/components/score-sheet/ScoreSheetView';
import { ApiError } from '@/lib/api/client';
import { getMatchForRequest, serverApi } from '@/lib/api/server';
import type { Match } from '@/lib/api/types';
import type { ScoreSheet } from '@/lib/tagging/types';

type Props = {
  params: Promise<{ matchId: string }>;
  /** `play`: a rally to open on arrival, from "Show me" on the stats (ST-047, ADR 0043). */
  searchParams?: Promise<{ play?: string | string[] }>;
};

function onApiError(e: unknown): never {
  if (e instanceof ApiError && e.status === 404) notFound();
  if (e instanceof ApiError && e.status === 401) redirect('/');
  throw e;
}

export default async function SheetPage({ params, searchParams }: Props) {
  const { matchId } = await params;
  const play = (await searchParams)?.play;
  let match: Match;
  let loaded: { version: number | null; sheet: ScoreSheet };
  try {
    match = await getMatchForRequest(matchId);
    loaded = await (await serverApi()).getScoreSheet(match.id);
  } catch (e) {
    onApiError(e);
  }
  return (
    <div className="stack">
      <PageTitle>{`Score sheet: ${match.title}`}</PageTitle>
      <p>
        <Link href={`/matches/${match.id}`} className="back-link">
          Back to the match
        </Link>
      </p>
      <h1>Score sheet</h1>
      <p>{match.title}</p>
      <ScoreSheetView
        match={match}
        initialSheet={loaded.sheet}
        initialVersion={loaded.version ?? 0}
        initialPlay={typeof play === 'string' ? play : undefined}
      />
      <p>
        <Link href={`/matches/${match.id}/stats`} className="touch-link">
          See the stats
        </Link>
      </p>
    </div>
  );
}
