'use client';

// P-01 Your training plan, the client part (ST-063a; FR-120, FR-122, FR-123; flows-sprint-04 §2).
// Fetched in the browser (no-store) so every visit shows the current plan, with the states:
// loading (busy region with reserved lines, NFR-039), error (one alert with "Try again" and the
// reference), empty (no tagged match / no plan yet), not found (a cited match is gone: the plan is
// read again), and the plan: notices once before the first card, the weaknesses, the sessions and
// each drill's "why" with "Show me" (the E-01 EvidencePanel for that metric and side, HAX G11).
// P-03 (ST-063c): each session's "Mark done" through the device outbox, each drill's "Not for me",
// and the offline state (the service worker's kept plan, or none on this device).
import Link from 'next/link';
import { Fragment, useCallback, useEffect, useRef, useState } from 'react';
import { browserApi } from '@/lib/api/browser';
import {
  planApi,
  type DrillAssignment,
  type PlanApi,
  type PlanRead,
  type Session,
  type TrainingPlan,
} from '@/lib/api/plan';
import { EvidencePanel } from '@/components/stats/EvidencePanel';
import type { StatsApi } from '@/components/stats/StatsDashboard';
import type { Outbox } from '@/lib/plan-outbox';
import { followThroughApi, type FollowThroughApi } from '@/lib/plan-outbox-api';
import {
  NotForMeDialog,
  SessionDone,
  WORDS,
  browserOutbox,
  useOnline,
  usePlanFollowThrough,
  type FollowThrough,
} from './PlanFollowThrough';
import { factsLine, madeOn, offlineAsOf, showMeName, splitLine, weaknessRate, whyParts } from './PlanViewWords';

const COACH_NOTICE =
  'These drills have not yet been checked by a human coach. Warm up first, and stop any drill that hurts.';
const CHANGED = 'Your plan changed on another device. Showing your current plan.';
/** Reserved lines while loading: header, notices and the top 3 weaknesses (flows-sprint-04 §2). */
const RESERVED_LINES = 5;

type State = { kind: 'loading' } | { kind: 'read'; read: PlanRead; changed: boolean };

function signIn() {
  window.location.assign('/');
}

export function PlanView({
  api = planApi,
  evidenceApi = browserApi,
  onSignedOut = signIn,
  followApi = followThroughApi,
  outbox,
}: {
  api?: Pick<PlanApi, 'getPlan'>;
  evidenceApi?: StatsApi;
  onSignedOut?: () => void;
  followApi?: FollowThroughApi;
  /** The device's "Mark done" outbox (default: IndexedDB). */
  outbox?: Outbox;
}) {
  const [state, setState] = useState<State>({ kind: 'loading' });
  const [box] = useState(() => outbox ?? browserOutbox());
  const online = useOnline();
  const plan = useRef<TrainingPlan | null>(null);
  plan.current = state.kind === 'read' && state.read.kind === 'plan' ? state.read.plan : null;

  const load = useCallback(
    async (changed = false) => {
      setState({ kind: 'loading' });
      setState({ kind: 'read', read: await api.getPlan(), changed });
    },
    [api],
  );

  useEffect(() => {
    void load();
  }, [load]);

  const follow = usePlanFollowThrough({
    outbox: box,
    api: followApi,
    sessionIndex: (id) => plan.current?.sessions.find((s) => s.id === id)?.index ?? null,
    reload: load,
    onSignedOut,
  });

  /** A swap's answer: the whole updated session replaces the old one (api-sprint-04 §3.3). */
  const replaceSession = useCallback((session: Session) => {
    setState((now) =>
      now.kind === 'read' && now.read.kind === 'plan'
        ? {
            ...now,
            changed: false,
            read: {
              ...now.read,
              plan: { ...now.read.plan, sessions: now.read.plan.sessions.map((s) => (s.id === session.id ? session : s)) },
            },
          }
        : now,
    );
  }, []);

  const read = state.kind === 'read' ? state.read : null;
  useEffect(() => {
    if (read?.kind === 'signed_out') onSignedOut();
  }, [read, onSignedOut]);

  if (state.kind === 'loading') {
    return (
      <div className="stack" aria-busy="true">
        <p role="status">Loading your plan…</p>
        {Array.from({ length: RESERVED_LINES }, (_, i) => (
          <div key={i} className="stat-card stat-card--reserved" aria-hidden="true" />
        ))}
      </div>
    );
  }
  const r = state.read;
  if (r.kind === 'signed_out') return null;
  if (r.kind === 'error' && !online) {
    return (
      <div className="stack">
        <p role="status" className="notice notice--info">
          You are offline and this plan is not saved on this device yet.
        </p>
      </div>
    );
  }
  if (r.kind === 'error') {
    return (
      <div className="stack">
        <div role="alert" className="notice notice--error">
          <p>We could not load your plan. Try again.</p>
          {r.supportRef ? <p>{`Reference: ${r.supportRef}`}</p> : null}
        </div>
        <p>
          <button type="button" className="button button--secondary" onClick={() => void load()}>
            Try again
          </button>
        </p>
      </div>
    );
  }
  if (r.kind === 'no_tagged_match' || r.kind === 'no_plan') {
    return (
      <div className="empty-state stack">
        {r.kind === 'no_plan' ? (
          <>
            <p className="empty-state__title">You have no plan yet.</p>
            <p>
              <Link href="/plan/new" className="button">
                Make my plan
              </Link>
            </p>
            <p>The plan is built from the rallies you tag.</p>
          </>
        ) : (
          <p className="empty-state__title">Tag a match to get a plan. The plan is built from the rallies you tag.</p>
        )}
        <p>
          <Link href="/matches" className="touch-link">
            Your matches
          </Link>
        </p>
      </div>
    );
  }
  return (
    <PlanBody
      plan={r.plan}
      offlineAsOf={r.offlineAsOf ?? null}
      changed={state.changed}
      evidenceApi={evidenceApi}
      onPlanChanged={() => void load(true)}
      follow={follow}
      followApi={followApi}
      online={online}
      onSwapped={replaceSession}
      onSignedOut={onSignedOut}
    />
  );
}

function PlanBody({
  plan,
  offlineAsOf: keptAt,
  changed,
  evidenceApi,
  onPlanChanged,
  follow,
  followApi,
  online,
  onSwapped,
  onSignedOut,
}: {
  plan: TrainingPlan;
  offlineAsOf: string | null;
  changed: boolean;
  evidenceApi: StatsApi;
  onPlanChanged: () => void;
  follow: FollowThrough;
  followApi: FollowThroughApi;
  online: boolean;
  onSwapped: (session: Session) => void;
  onSignedOut: () => void;
}) {
  const [open, setOpen] = useState<string | null>(null);
  const [swapping, setSwapping] = useState<DrillAssignment | null>(null);
  const [focusId, setFocusId] = useState<string | null>(null);
  useEffect(() => {
    if (focusId) document.getElementById(`drill-${focusId}`)?.focus();
  }, [focusId, plan]);

  async function swap(a: DrillAssignment, reason: string) {
    const r = await followApi.swap(a.id, reason);
    if (r.kind === 'swapped') {
      setSwapping(null);
      onSwapped(r.session);
      const name = r.session.assignments.find((x) => x.id === a.id)?.drill.name ?? a.drill.name;
      follow.say(WORDS.swapped(name));
      setFocusId(a.id);
    } else if (r.kind === 'not_found') {
      setSwapping(null);
      onPlanChanged();
    } else if (r.kind === 'signed_out') onSignedOut();
    return r;
  }

  const unfitted = new Set(plan.unfitted.map((u) => u.weaknessId));
  const weeks = [...new Set(plan.sessions.map((s) => s.week))].sort((a, b) => a - b);
  return (
    <div className="stack plan">
      {keptAt && !online ? (
        <p className="notice notice--info">{`You are offline. This is your plan as of ${offlineAsOf(keptAt)}.`}</p>
      ) : null}
      <p role="status">{follow.status ?? (changed ? CHANGED : '')}</p>
      {follow.dropped ? <p className="notice notice--error">{WORDS.dropped}</p> : null}
      <p>{madeOn(plan)}</p>
      <p>
        <SetupLink online={online} />
      </p>
      {plan.unofficial ? <p className="notice notice--warning">{plan.label}</p> : null}
      {plan.drillsVerified ? null : <p className="notice notice--warning">{COACH_NOTICE}</p>}
      {plan.limitedData ? (
        <p className="notice notice--warning">
          {`Based on limited data from ${plan.limitedData.rallies} rallies. Tag more matches for a firmer plan.`}
        </p>
      ) : null}

      <h2 id="plan-weaknesses">What the plan works on</h2>
      <ol aria-labelledby="plan-weaknesses" className="stack">
        {plan.ranking.weaknesses.map((w) => (
          <li key={w.id}>
            <p>
              <strong>{w.name}</strong>
              {weaknessRate(w.perGame, plan.ranking.unit, plan.ranking.games)}
            </p>
            <p>{splitLine(w)}</p>
            {unfitted.has(w.id) ? (
              <p>
                No drill fits your setup for this one. <SetupLink online={online} />
              </p>
            ) : null}
          </li>
        ))}
      </ol>
      {plan.ranking.sideOutVerified ? null : <p>The split between serve and receive is not yet verified.</p>}

      <h2>Your sessions</h2>
      {weeks.map((week) => (
        <Fragment key={week}>
          <h3>{`Week ${week}`}</h3>
          {plan.sessions
            .filter((s) => s.week === week)
            .sort((a, b) => a.index - b.index)
            .map((s) => {
              const title = `Session ${s.index} of ${plan.preferences.sessionsPerWeek} · ${s.minutesBudget} minutes`;
              return (
                <section key={s.id} aria-labelledby={`session-${s.id}`} className="stack">
                  <h4 id={`session-${s.id}`}>{title}</h4>
                  <SessionDone session={s} follow={follow} online={online} />
                  <ol aria-labelledby={`session-${s.id}`} className="stack">
                    {s.assignments.map((a) => (
                      <DrillRow
                        key={a.id}
                        assignment={a}
                        open={open === a.id}
                        onToggle={() => setOpen((now) => (now === a.id ? null : a.id))}
                        evidenceApi={evidenceApi}
                        onPlanChanged={onPlanChanged}
                        online={online}
                        onNotForMe={() => setSwapping(a)}
                      />
                    ))}
                  </ol>
                </section>
              );
            })}
        </Fragment>
      ))}
      {swapping ? (
        <NotForMeDialog
          id={`swap-${swapping.id}`}
          drillName={swapping.drill.name}
          onSwap={(reason) => swap(swapping, reason)}
          onClose={(reload) => {
            const id = swapping.id;
            setSwapping(null);
            if (reload) onPlanChanged();
            else document.getElementById(`not-for-me-${id}`)?.focus();
          }}
        />
      ) : null}
    </div>
  );
}

/** "Change my setup" (→ P-02); offline it is text with "Needs a connection" (flows-sprint-04 §2). */
function SetupLink({ online }: { online: boolean }) {
  if (!online) return <span>{`Change my setup. ${WORDS.needsConnection}`}</span>;
  return (
    <Link href="/plan/new" className="touch-link">
      Change my setup
    </Link>
  );
}

function DrillRow({
  assignment: a,
  open,
  onToggle,
  evidenceApi,
  onPlanChanged,
  online,
  onNotForMe,
}: {
  assignment: DrillAssignment;
  open: boolean;
  onToggle: () => void;
  evidenceApi: StatsApi;
  onPlanChanged: () => void;
  online: boolean;
  onNotForMe: () => void;
}) {
  const c = a.citation;
  const panelId = `evidence-${a.id}`;
  return (
    <li className="stack" id={`drill-${a.id}`} tabIndex={-1}>
      <p>
        <strong>{a.drill.name}</strong>
        {a.warmUp ? ' · Warm-up' : null}
      </p>
      <p>{factsLine(a)}</p>
      {c === null ? (
        <p className="notice notice--error">We could not show why this drill was chosen.</p>
      ) : (
        <>
          <p>
            <span>{`Why: ${c.why}`}</span>
            {c.lowSample ? (
              <>
                {' '}
                <span className="tag tag--warning">low sample</span>
              </>
            ) : null}
          </p>
          <p>
            <button
              type="button"
              className="button button--secondary"
              aria-label={showMeName(c)}
              aria-expanded={open}
              aria-controls={open ? panelId : undefined}
              disabled={!online}
              onClick={onToggle}
            >
              Show me
            </button>
          </p>
          {open ? (
            <div id={panelId} className="stack">
              {c.evidence.map((e, i) => (
                <EvidencePanel
                  key={e.matchId}
                  id={`${panelId}-${i}`}
                  matchId={e.matchId}
                  metric={{ entry: { id: c.metricId, name: whyParts(c.why).metric } }}
                  side={e.side}
                  sideWords={c.evidence.length > 1 ? `your side, match ${i + 1} of ${c.evidence.length}` : 'your side'}
                  sheetVersion={null}
                  api={evidenceApi}
                  onReload={onPlanChanged}
                />
              ))}
            </div>
          ) : null}
        </>
      )}
      <p>
        <button
          id={`not-for-me-${a.id}`}
          type="button"
          className="button button--secondary"
          aria-label={`Not for me, ${a.drill.name}`}
          disabled={!online}
          onClick={onNotForMe}
        >
          Not for me
        </button>
        {/* One line for the row's two buttons that need the server ("Show me", "Not for me"). */}
        {online ? null : <span>{` ${WORDS.needsConnection}`}</span>}
      </p>
    </li>
  );
}
