// E-02 All rallies behind a stat (ST-047; FR-103; flows-sprint-03 §3). Server component: checks the
// metric id and side before any request, loads the match and its stats (the not-found page for
// another player's, a deleted or a missing match, and for a metric that is not published,
// NFR-051, FR-102), and names the stat. The list itself is fetched in the browser, 10 a page.
import { notFound, redirect } from 'next/navigation';
import { EvidenceAll } from '@/components/stats/EvidenceAll';
import { ApiError } from '@/lib/api/client';
import { getMatchForRequest, serverApi } from '@/lib/api/server';
import type { Match } from '@/lib/api/types';
import type { Metric } from '@/lib/stats/types';

type Props = {
  params: Promise<{ matchId: string; metricId: string }>;
  searchParams: Promise<{ side?: string | string[] }>;
};

export default async function EvidencePage({ params, searchParams }: Props) {
  const { matchId, metricId } = await params;
  const { side } = await searchParams;
  if (!/^AN-\d{2}$/.test(metricId) || (side !== 'A' && side !== 'B')) notFound();
  let match: Match;
  let metric: Metric | undefined;
  try {
    match = await getMatchForRequest(matchId);
    metric = (await (await serverApi()).stats(match.id)).metrics.find((m) => m.entry.id === metricId);
  } catch (e) {
    if (e instanceof ApiError && e.status === 404) notFound();
    if (e instanceof ApiError && e.status === 401) redirect('/');
    throw e;
  }
  if (!metric) notFound();
  return (
    <EvidenceAll match={match} metricId={metricId} metricName={metric.entry.name} lowSample={metric[side].low_sample} side={side} />
  );
}
