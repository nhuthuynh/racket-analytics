// Match detail (ST-010). "Not yours" and "does not exist" both render the same not-found page:
// the API returns the same 404 for both (api-sprint-00 §5.2), and so does this page.
import Link from 'next/link';
import { notFound, redirect } from 'next/navigation';
import { MatchDetail } from '@/components/MatchDetail';
import { PageTitle } from '@/components/PageTitle';
import { ApiError } from '@/lib/api/client';
import { getMatchForRequest } from '@/lib/api/server';
import type { Match } from '@/lib/api/types';

type Props = { params: Promise<{ matchId: string }> };

async function loadMatch(id: string): Promise<Match> {
  try {
    return await getMatchForRequest(id);
  } catch (e) {
    if (e instanceof ApiError && e.status === 404) notFound();
    if (e instanceof ApiError && e.status === 401) redirect('/');
    throw e;
  }
}

export default async function MatchPage({ params }: Props) {
  const { matchId } = await params;
  const match = await loadMatch(matchId);
  return (
    <div className="stack">
      <PageTitle>{match.title}</PageTitle>
      <p>
        <Link href="/matches" className="back-link">
          Back to your matches
        </Link>
      </p>
      <MatchDetail initialMatch={match} />
    </div>
  );
}
