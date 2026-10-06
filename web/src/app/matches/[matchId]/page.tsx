// Match detail (ST-010). "Not yours" and "does not exist" both render the same not-found page:
// the API returns the same 404 for both (api-sprint-00 §5.2), and so does this page.
import Link from 'next/link';
import { notFound, redirect } from 'next/navigation';
import { MatchDetail } from '@/components/MatchDetail';
import { ApiError } from '@/lib/api/client';
import { getMatchForRequest, serverApi } from '@/lib/api/server';
import { FALLBACK_UPLOAD_POLICY, type Match, type UploadPolicy } from '@/lib/api/types';

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

/** Caps for the U-03 copy and chunk bounds (api-sprint-01 §6.1); provisional caps if unreadable. */
async function loadPolicy(): Promise<UploadPolicy> {
  try {
    return await (await serverApi()).uploadPolicy();
  } catch {
    return FALLBACK_UPLOAD_POLICY;
  }
}

export default async function MatchPage({ params }: Props) {
  const { matchId } = await params;
  const match = await loadMatch(matchId);
  const policy = await loadPolicy();
  return (
    <div className="stack">
      <p>
        <Link href="/matches" className="back-link">
          Back to your matches
        </Link>
      </p>
      <MatchDetail initialMatch={match} policy={policy} />
    </div>
  );
}
