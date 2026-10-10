'use client';

// E-01 "Show me" (ST-047; FR-103, FR-027; NFR-038; flows-sprint-03 §3): up to 10 rallies behind one
// metric and side, each a link that opens the score sheet with that rally's video (ADR 0043,
// R3-4), "See all n" past 10, and the states: loading (busy region with reserved rows), error
// (alert with "Try again"), empty, gone (404), and stale (another sheet version than the stats).
import Link from 'next/link';
import { useCallback, useEffect, useState } from 'react';
import type { Evidence, Metric } from '@/lib/stats/types';
import type { Side } from '@/lib/tagging/types';
import { EvidenceList } from './EvidenceList';
import { isStatus, loadProblem } from './messages';
import type { StatsApi } from './StatsDashboard';

/** E-01 shows at most this many; more opens E-02 (FR-103 "up to 10"). */
const EVIDENCE_PAGE = 10;

type State =
  | { kind: 'loading' }
  | { kind: 'error'; message: string; retrying: boolean }
  | { kind: 'gone' }
  | { kind: 'loaded'; evidence: Evidence };

export function evidencePath(matchId: string, metricId: string, side: Side): string {
  return `/matches/${matchId}/stats/${metricId}/evidence?side=${side}`;
}

export function EvidencePanel({
  id,
  matchId,
  metric,
  side,
  sideWords,
  sheetVersion,
  api,
  onReload,
}: {
  id: string;
  matchId: string;
  metric: Metric;
  side: Side;
  sideWords: string;
  sheetVersion: number;
  api: StatsApi;
  onReload: () => void;
}) {
  const [state, setState] = useState<State>({ kind: 'loading' });
  const title = `Rallies behind “${metric.entry.name}”, ${sideWords}`;

  const load = useCallback(async () => {
    try {
      setState({ kind: 'loaded', evidence: await api.evidence(matchId, metric.entry.id, side) });
    } catch (e) {
      if (isStatus(e, 404)) return setState({ kind: 'gone' });
      setState({ kind: 'error', message: loadProblem(e, 'The rallies for this stat'), retrying: false });
    }
  }, [api, matchId, metric.entry.id, side]);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <div id={id} className="stack evidence-panel">
      <h3>{title}</h3>
      {state.kind === 'loading' ? (
        <div aria-busy="true" className="evidence-panel__reserved">
          <p role="status">Loading the rallies…</p>
        </div>
      ) : state.kind === 'error' ? (
        <>
          <p role="alert" className="notice notice--error">
            {state.message}
          </p>
          <p>
            <button
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
        </>
      ) : state.kind === 'gone' ? (
        <>
          <p role="alert" className="notice notice--error">
            This stat is no longer available. Reload the stats.
          </p>
          <p>
            <button type="button" className="button button--secondary" onClick={onReload}>
              Reload the stats
            </button>
          </p>
        </>
      ) : (
        <>
          {state.evidence.sheetVersion !== sheetVersion ? (
            <div className="stack">
              <p>These stats changed since you opened this page. Reload the stats to see the new numbers.</p>
              <p>
                <button type="button" className="button button--secondary" onClick={onReload}>
                  Reload the stats
                </button>
              </p>
            </div>
          ) : null}
          <EvidenceList matchId={matchId} items={state.evidence.items} label={title} />
          {state.evidence.total > EVIDENCE_PAGE ? (
            <p>
              <Link href={evidencePath(matchId, metric.entry.id, side)} className="touch-link">
                {`See all ${state.evidence.total}`}
              </Link>
            </p>
          ) : null}
        </>
      )}
    </div>
  );
}
