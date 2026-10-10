'use client';

// E-02 All rallies behind a stat (ST-047; FR-103; flows-sprint-03 §3): the same items as E-01,
// 10 a page through the API's cursor, with the position in words ("Rallies 11 to 20 of 23"),
// "Next 10 rallies" / "Previous 10 rallies", and the load states (busy region, alert with
// "Try again", nothing behind the stat).
import Link from 'next/link';
import { useCallback, useEffect, useRef, useState } from 'react';
import { PageTitle } from '@/components/PageTitle';
import type { ApiClient } from '@/lib/api/client';
import { browserApi } from '@/lib/api/browser';
import type { Match } from '@/lib/api/types';
import type { Evidence } from '@/lib/stats/types';
import type { Side } from '@/lib/tagging/types';
import { sideNames } from '@/lib/tagging/view';
import { EvidenceList } from './EvidenceList';
import { loadProblem } from './messages';

type State =
  | { kind: 'loading' }
  | { kind: 'error'; message: string }
  | { kind: 'loaded'; evidence: Evidence };

export function EvidenceAll({
  match,
  metricId,
  metricName,
  lowSample = false,
  side,
  api = browserApi,
}: {
  match: Match;
  metricId: string;
  metricName: string;
  lowSample?: boolean;
  side: Side;
  api?: Pick<ApiClient, 'evidence'>;
}) {
  const [state, setState] = useState<State>({ kind: 'loading' });
  /** Cursors of the pages shown so far; the last one is the current page (null: the first). */
  const [cursors, setCursors] = useState<(string | null)[]>([null]);
  const list = useRef<HTMLDivElement>(null);
  const cursor = cursors[cursors.length - 1] ?? null;
  const names = sideNames(match);
  const title = `Rallies behind “${metricName}”`;
  const sideWords = side === names.mySide ? 'your side' : 'other side';

  const load = useCallback(async () => {
    setState({ kind: 'loading' });
    try {
      setState({ kind: 'loaded', evidence: await api.evidence(match.id, metricId, side, cursor) });
    } catch (e) {
      setState({ kind: 'error', message: loadProblem(e, 'The rallies for this stat') });
    }
  }, [api, cursor, match.id, metricId, side]);

  useEffect(() => {
    void load();
  }, [load]);

  const first = (cursors.length - 1) * 10 + 1;
  return (
    <div className="stack">
      <PageTitle>{`${title}: ${match.title}`}</PageTitle>
      <p>
        <Link href={`/matches/${match.id}/stats`} className="back-link">
          Back to the stats
        </Link>
      </p>
      <h1>{title}</h1>
      {state.kind === 'loaded' ? (
        <p>{`${names.label(side)} · ${state.evidence.total} ${state.evidence.total === 1 ? 'rally' : 'rallies'}`}</p>
      ) : (
        <p>{names.label(side)}</p>
      )}
      {lowSample ? (
        <p>
          <span className="tag tag--warning">low sample</span>
        </p>
      ) : null}
      <div ref={list} className="stack" tabIndex={-1}>
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
              <button type="button" className="button button--secondary" onClick={() => void load()}>
                Try again
              </button>
            </p>
          </>
        ) : (
          <>
            {state.evidence.items.length > 0 ? (
              <p>{`Rallies ${first} to ${first + state.evidence.items.length - 1} of ${state.evidence.total}`}</p>
            ) : null}
            <EvidenceList matchId={match.id} items={state.evidence.items} label={`${title}, ${sideWords}`} />
            <div className="button-row">
              {cursors.length > 1 ? (
                <button type="button" className="button button--secondary" onClick={() => setCursors((c) => c.slice(0, -1))}>
                  Previous 10 rallies
                </button>
              ) : null}
              {state.evidence.nextCursor !== null ? (
                <button
                  type="button"
                  className="button button--secondary"
                  onClick={() => {
                    const next = state.evidence.nextCursor;
                    setCursors((c) => [...c, next]);
                  }}
                >
                  Next 10 rallies
                </button>
              ) : null}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
