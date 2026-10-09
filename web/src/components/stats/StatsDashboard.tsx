'use client';

// D-01 stats, the client part (ST-048; FR-100, FR-101, FR-102, FR-055; flows-sprint-03 §2). The
// numbers are fetched in the browser (no-store) so each visit is current with the score sheet and
// the states can be shown: empty (decided by the server page from the match and its sheet, no
// request), loading (a busy region whose reserved cards keep the layout still, NFR-039), error
// (one alert with "Try again"), nothing published, and the cards.
import Link from 'next/link';
import { useCallback, useEffect, useRef, useState } from 'react';
import type { ApiClient } from '@/lib/api/client';
import { browserApi } from '@/lib/api/browser';
import type { Match } from '@/lib/api/types';
import type { Stats } from '@/lib/stats/types';
import { sideNames } from '@/lib/tagging/view';
import { isStatus, loadProblem } from './messages';
import { MetricCard, type OpenEvidence } from './MetricCard';

export type StatsApi = Pick<ApiClient, 'stats' | 'evidence'>;

/** Reserved cards while loading: the dictionary has seven entries (AN-01..AN-07). */
const RESERVED_CARDS = 7;

type State =
  | { kind: 'idle' }
  | { kind: 'loading' }
  | { kind: 'error'; message: string; retrying: boolean }
  | { kind: 'gone' }
  | { kind: 'loaded'; stats: Stats };

function signIn() {
  window.location.assign('/');
}

export function StatsDashboard({
  match,
  rallyCount,
  api = browserApi,
  onSignedOut = signIn,
}: {
  match: Match;
  /** Rallies on the score sheet (server page); 0 shows the empty state without asking for stats. */
  rallyCount: number;
  api?: StatsApi;
  onSignedOut?: () => void;
}) {
  const hasVideo = match.status === 'video_received';
  const empty = !hasVideo || rallyCount === 0;
  // 'idle' in the server HTML: the space is reserved, but nothing claims to load until the browser
  // has asked (E2E-03-09 checks that the busy region means a request is under way).
  const [state, setState] = useState<State>({ kind: 'idle' });
  const [open, setOpen] = useState<OpenEvidence | null>(null);
  const retry = useRef<HTMLButtonElement>(null);

  const load = useCallback(async () => {
    setState((s) => (s.kind === 'idle' ? { kind: 'loading' } : s));
    try {
      const stats = await api.stats(match.id);
      setState({ kind: 'loaded', stats });
    } catch (e) {
      if (isStatus(e, 401)) return onSignedOut();
      if (isStatus(e, 404)) return setState({ kind: 'gone' });
      setState({ kind: 'error', message: loadProblem(e, 'Your stats'), retrying: false });
    }
  }, [api, match.id, onSignedOut]);

  useEffect(() => {
    if (!empty) void load();
  }, [empty, load]);

  if (!hasVideo) {
    return (
      <div className="stack">
        <p>You can see stats once this match&apos;s video is received and rallies are tagged.</p>
        <p>
          <Link href={`/matches/${match.id}`} className="touch-link">
            Back to the match
          </Link>
        </p>
      </div>
    );
  }
  if (rallyCount === 0) {
    return (
      <div className="stack">
        <p>No rallies are tagged yet, so there are no stats to show.</p>
        <p>
          <Link href={`/matches/${match.id}/tag`} className="button">
            Tag rallies
          </Link>
        </p>
      </div>
    );
  }

  if (state.kind === 'idle' || state.kind === 'loading') {
    const busy = state.kind === 'loading';
    return (
      <div key="loading" className="stats-cards" aria-busy={busy ? 'true' : undefined}>
        <p role={busy ? 'status' : undefined}>Loading your stats…</p>
        {Array.from({ length: RESERVED_CARDS }, (_, i) => (
          <div key={i} className="stat-card stat-card--reserved" aria-hidden="true" />
        ))}
      </div>
    );
  }
  if (state.kind === 'error') {
    return (
      <div key="error" className="stack">
        <p role="alert" className="notice notice--error">
          {state.message}
        </p>
        <p>
          <button
            ref={retry}
            type="button"
            className="button button--secondary"
            aria-busy={state.retrying}
            onClick={() => {
              if (state.retrying) return;
              setState({ ...state, retrying: true });
              void load();
            }}
          >
            Try again
          </button>
        </p>
      </div>
    );
  }
  if (state.kind === 'gone') {
    return (
      <div key="gone" className="stack">
        <p role="alert" className="notice notice--error">
          This match is no longer available.
        </p>
        <p>
          <Link href="/matches" className="touch-link">
            Go to your matches
          </Link>
        </p>
      </div>
    );
  }

  const { stats } = state;
  if (stats.metrics.length === 0) {
    return (
      <div key="none" className="stack">
        <p>No stats are ready to show yet. Each stat appears once our coach has checked how it is measured.</p>
        <p>
          <Link href={`/matches/${match.id}`} className="touch-link">
            Back to the match
          </Link>
        </p>
      </div>
    );
  }
  const names = sideNames(match);
  return (
    <div key="cards" className="stats-cards">
      {stats.unofficial ? (
        <p className="notice notice--warning">{'unofficial scoring (rules not yet verified)'}</p>
      ) : null}
      {stats.metrics.map((metric) => (
        <MetricCard
          key={metric.entry.id}
          matchId={match.id}
          metric={metric}
          stats={stats}
          names={names}
          open={open}
          onToggle={(which) =>
            setOpen((now) => (now && now.metricId === which.metricId && now.side === which.side ? null : which))
          }
          api={api}
          onReload={() => {
            setOpen(null);
            setState({ kind: 'loading' });
            void load();
          }}
        />
      ))}
    </div>
  );
}
