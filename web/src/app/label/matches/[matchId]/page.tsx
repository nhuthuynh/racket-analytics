// L-01 Full Tag (ST-052; FR-150; api-sprint-03 §5.1; flows-sprint-03 §6). Server component. The
// label route decides access first: a player, a labeller on another account's match and a deleted
// or unknown match all get the one not-found page (404, FR-150 "not available"; no existence
// oracle). A labeller's own match without a consent record or without a probed video is refused in
// words (409), with no video, no tag bar and never the consent reference (T-LB-4).
import { notFound, redirect } from 'next/navigation';
import { FullTag } from '@/components/label/FullTag';
import { PageTitle } from '@/components/PageTitle';
import { ApiError } from '@/lib/api/client';
import { getMatchForRequest, serverApi } from '@/lib/api/server';
import type { Match } from '@/lib/api/types';
import type { LabelSession } from '@/lib/label/types';

type Props = { params: Promise<{ matchId: string }> };

const REFUSALS: Readonly<Record<string, string>> = {
  no_consent: 'This match has no consent record for labelling. Nothing can be labelled until the team records consent.',
  match_not_ready: "This match's video is not ready for frame-by-frame labelling.",
};

function onApiError(e: unknown): never {
  if (e instanceof ApiError && e.status === 404) notFound();
  if (e instanceof ApiError && e.status === 401) redirect('/');
  throw e;
}

export default async function FullTagPage({ params }: Props) {
  const { matchId } = await params;
  let session: LabelSession | null = null;
  let refusal: string | null = null;
  try {
    session = await (await serverApi()).labelSession(matchId);
  } catch (e) {
    if (e instanceof ApiError && e.status === 409 && REFUSALS[e.code]) refusal = REFUSALS[e.code] ?? null;
    else onApiError(e);
  }
  let match: Match;
  try {
    match = await getMatchForRequest(matchId);
  } catch (e) {
    onApiError(e);
  }
  const title = `Full Tag: ${match.title}`;
  return (
    <div className="stack">
      <PageTitle>{title}</PageTitle>
      <h1>{title}</h1>
      {refusal || !session ? (
        <p role="alert" className="notice notice--error">
          {refusal}
        </p>
      ) : (
        <FullTag match={match} initial={session} />
      )}
    </div>
  );
}
