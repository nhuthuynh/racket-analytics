// Your matches (ST-010): list with an empty state. Only the caller's matches are returned by
// the API; the client never filters for authorisation [AQS/SEC-03].
import Link from 'next/link';
import { redirect } from 'next/navigation';
import { PageTitle } from '@/components/PageTitle';
import { DeletedNotice } from '@/components/DeletedNotice';
import { ResumeBanner } from '@/components/ResumeBanner';
import { ApiError } from '@/lib/api/client';
import { serverApi } from '@/lib/api/server';
import { LocalDateLine } from '@/components/LocalDate';
import { FORMAT_LABELS, type Match } from '@/lib/api/types';
import { matchStatusLine } from '@/lib/format';

async function loadMatches(): Promise<Match[]> {
  try {
    return await (await serverApi()).listMatches();
  } catch (e) {
    if (e instanceof ApiError && e.status === 401) redirect('/');
    // The error page shows the API's support reference (C-30): Next keeps an existing digest.
    if (e instanceof ApiError && e.supportRef) Object.assign(e, { digest: e.supportRef });
    throw e;
  }
}

type Props = { searchParams?: Promise<{ deleted?: string | string[] }> };

export default async function MatchesPage({ searchParams }: Props = {}) {
  const matches = await loadMatches();
  const deleted = (await searchParams)?.deleted;
  return (
    <div className="stack">
      <PageTitle>Your matches</PageTitle>
      <h1 tabIndex={-1}>Your matches</h1>
      <DeletedNotice which={typeof deleted === 'string' ? deleted : undefined} />
      <ResumeBanner matches={matches} />
      {matches.length === 0 ? (
        <div className="empty-state">
          {/* Not a heading: the page has one h1 and the empty state is a message (flows M-01). */}
          <p className="empty-state__title">No matches yet</p>
          <p>
            <Link href="/matches/new" className="button">
              Record your first match
            </Link>
          </p>
          <p>
            <Link href="/guide" className="inline-target">
              How to film your match
            </Link>
          </p>
        </div>
      ) : (
        <p>
          <Link href="/matches/new" className="button">
            New match
          </Link>
        </p>
      )}
      {matches.length === 0 ? null : (
        <ul className="match-list">
          {matches.map((m) => (
            <li key={m.id} className="match-list__item">
              <Link href={`/matches/${m.id}`} className="match-list__link">
                {m.title}
              </Link>
              <LocalDateLine
                className="match-list__meta"
                prefix={`${FORMAT_LABELS[m.format]} · ${matchStatusLine(m)} · Created `}
                iso={m.created_at}
              />
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
