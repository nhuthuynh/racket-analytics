// D-01 Stats (ST-048; FR-100..FR-102, FR-055; flows-sprint-03 §2). Server component: the match
// (its title, the side names, and the not-found page for another player's, a deleted or a missing
// match, NFR-051) and how many rallies the sheet has (the empty state needs no stats request).
// The numbers themselves are fetched in the browser by StatsDashboard, so every visit is current.
import Link from 'next/link';
import { notFound, redirect } from 'next/navigation';
import { PageTitle } from '@/components/PageTitle';
import { StatsDashboard } from '@/components/stats/StatsDashboard';
import { ApiError } from '@/lib/api/client';
import { getMatchForRequest, serverApi } from '@/lib/api/server';
import type { Match } from '@/lib/api/types';

type Props = { params: Promise<{ matchId: string }> };

function onApiError(e: unknown): never {
  if (e instanceof ApiError && e.status === 404) notFound();
  if (e instanceof ApiError && e.status === 401) redirect('/');
  throw e;
}

export default async function StatsPage({ params }: Props) {
  const { matchId } = await params;
  let match: Match;
  let rallyCount = 0;
  try {
    match = await getMatchForRequest(matchId);
    if (match.status === 'video_received') {
      rallyCount = (await (await serverApi()).getScoreSheet(match.id)).sheet.rows.length;
    }
  } catch (e) {
    onApiError(e);
  }
  return (
    <div className="stack">
      <PageTitle>{`Stats: ${match.title}`}</PageTitle>
      <p>
        <Link href={`/matches/${match.id}`} className="back-link">
          Back to the match
        </Link>
      </p>
      <h1>Stats</h1>
      <p>{match.title}</p>
      <p>
        These stats come from the rallies you tagged. Change a rally on the{' '}
        <Link href={`/matches/${match.id}/sheet`} className="inline-target">
          score sheet
        </Link> and they change too.
      </p>
      <StatsDashboard match={match} rallyCount={rallyCount} />
    </div>
  );
}
