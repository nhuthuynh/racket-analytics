// Your matches (ST-010): list with an empty state. Only the caller's matches are returned by
// the API; the client never filters for authorisation [AQS/SEC-03].
import Link from 'next/link';
import { redirect } from 'next/navigation';
import { PageTitle } from '@/components/PageTitle';
import { ApiError } from '@/lib/api/client';
import { serverApi } from '@/lib/api/server';
import { FORMAT_LABELS, STATUS_LABELS, type Match } from '@/lib/api/types';

const dateFormat = new Intl.DateTimeFormat('en-GB', {
  day: 'numeric',
  month: 'short',
  year: 'numeric',
  timeZone: 'UTC',
});

async function loadMatches(): Promise<Match[]> {
  try {
    return await (await serverApi()).listMatches();
  } catch (e) {
    if (e instanceof ApiError && e.status === 401) redirect('/');
    throw e;
  }
}

export default async function MatchesPage() {
  const matches = await loadMatches();
  return (
    <div className="stack">
      <PageTitle>Your matches</PageTitle>
      <h1>Your matches</h1>
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
              <p className="match-list__meta">
                {FORMAT_LABELS[m.format]} · {STATUS_LABELS[m.status]} · Created{' '}
                {dateFormat.format(new Date(m.created_at))}
              </p>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
