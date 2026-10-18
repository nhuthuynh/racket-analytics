// The training plan read (ST-063a; api-sprint-04 §2.2, §2.3; Coaching context, coaching-plan.md).
// `GET /me/plan` → a `PlanRead`: the plan in the Coaching context's words (TrainingPlan, Weakness,
// Session, DrillAssignment, Citation), or why there is none. The client keeps only what P-01 shows.
// A citation that breaks the contract spoils only its own drill row (`citation: null`, shown as an
// error in that row, HAX G11); any other break of the representation is an error for the page.
// Authorisation is the API's (`/me/plan` is the session's own plan) [AQS/SEC-03].
import type { Side } from '@/lib/tagging/types';

export interface Weakness {
  id: string;
  name: string;
  metricId: string;
  rank: number;
  perGame: number;
  onServePerGame: number;
  onReceivePerGame: number;
  concededPerGame: number;
}

export interface EvidenceLink {
  matchId: string;
  side: Side;
  n: number;
}

/** Why a drill was chosen: the player's own metric value and its n (FR-122). */
export interface Citation {
  metricId: string;
  side: Side;
  value: number;
  n: number;
  lowSample: boolean;
  evidence: EvidenceLink[];
  /** "Serve faults: 29% of 7 serves" (the metric dictionary's words, from the API). */
  why: string;
}

export interface Drill {
  id: string;
  name: string;
  players: number;
  needs: string[];
}

export interface DrillAssignment {
  id: string;
  position: number;
  drill: Drill;
  minutes: number;
  weaknessId: string | null;
  warmUp: boolean;
  /** null when the API's citation is missing or broken: the row says so (QD-PL-04, G11). */
  citation: Citation | null;
}

export interface Session {
  id: string;
  week: number;
  index: number;
  minutesBudget: number;
  done: boolean;
  /** In position order: the warm-up first (QD-PL-03). */
  assignments: DrillAssignment[];
}

export interface TrainingPlan {
  id: string;
  version: number;
  createdAt: string;
  unofficial: boolean;
  label: string;
  drillsVerified: boolean;
  preferences: { minutesPerSession: number; sessionsPerWeek: number };
  ranking: { unit: string; sideOutVerified: boolean; games: number; weaknesses: Weakness[] };
  limitedData: { rallies: number } | null;
  unfitted: { weaknessId: string; reason: string }[];
  sessions: Session[];
}

export type PlanRead =
  /** `offlineAsOf`: the service worker's kept copy, answered offline (ST-063c). */
  | { kind: 'plan'; plan: TrainingPlan; offlineAsOf?: string }
  | { kind: 'no_plan' }
  | { kind: 'no_tagged_match' }
  | { kind: 'signed_out' }
  | { kind: 'error'; supportRef: string | null };

export class PlanShapeError extends Error {
  constructor(where: string) {
    super(`plan representation: ${where}`);
    this.name = 'PlanShapeError';
  }
}

type Obj = Record<string, unknown>;

function obj(v: unknown, where: string): Obj {
  if (typeof v !== 'object' || v === null || Array.isArray(v)) throw new PlanShapeError(where);
  return v as Obj;
}

function arr(v: unknown, where: string): unknown[] {
  if (!Array.isArray(v)) throw new PlanShapeError(where);
  return v;
}

function str(v: unknown, where: string): string {
  if (typeof v !== 'string' || v.length === 0) throw new PlanShapeError(where);
  return v;
}

function num(v: unknown, where: string): number {
  if (typeof v !== 'number' || !Number.isFinite(v)) throw new PlanShapeError(where);
  return v;
}

function int(v: unknown, where: string, min = 0): number {
  const n = num(v, where);
  if (!Number.isInteger(n) || n < min) throw new PlanShapeError(where);
  return n;
}

function bool(v: unknown, where: string): boolean {
  if (typeof v !== 'boolean') throw new PlanShapeError(where);
  return v;
}

function side(v: unknown, where: string): Side {
  if (v !== 'A' && v !== 'B') throw new PlanShapeError(where);
  return v;
}

function parseCitation(raw: unknown, why: unknown): Citation | null {
  try {
    const c = obj(raw, 'citation');
    return {
      metricId: str(c.metric_id, 'citation.metric_id'),
      side: side(c.side, 'citation.side'),
      value: num(c.value, 'citation.value'),
      n: int(c.n, 'citation.n', 1),
      lowSample: bool(c.low_sample, 'citation.low_sample'),
      evidence: arr(c.evidence, 'citation.evidence').map((e) => {
        const link = obj(e, 'citation.evidence[]');
        return {
          matchId: str(link.match_id, 'evidence.match_id'),
          side: link.side === undefined ? side(c.side, 'citation.side') : side(link.side, 'evidence.side'),
          n: int(link.n, 'evidence.n'),
        };
      }),
      why: str(why, 'why'),
    };
  } catch (e) {
    if (e instanceof PlanShapeError) return null;
    throw e;
  }
}

function parseAssignment(raw: unknown): DrillAssignment {
  const a = obj(raw, 'assignment');
  const d = obj(a.drill, 'assignment.drill');
  return {
    id: str(a.id, 'assignment.id'),
    position: int(a.position, 'assignment.position', 1),
    drill: {
      id: str(d.id, 'drill.id'),
      name: str(d.name, 'drill.name'),
      players: int(d.players, 'drill.players', 1),
      needs: arr(d.needs, 'drill.needs').map((x) => str(x, 'drill.needs[]')),
    },
    minutes: int(a.minutes, 'assignment.minutes', 1),
    weaknessId: a.weakness_id === null ? null : str(a.weakness_id, 'assignment.weakness_id'),
    warmUp: bool(a.warm_up, 'assignment.warm_up'),
    citation: parseCitation(a.citation, a.why),
  };
}

function parseSession(raw: unknown): Session {
  const s = obj(raw, 'session');
  return {
    id: str(s.id, 'session.id'),
    week: int(s.week, 'session.week', 1),
    index: int(s.index, 'session.index', 1),
    minutesBudget: int(s.minutes_budget, 'session.minutes_budget', 1),
    done: bool(s.done, 'session.done'),
    assignments: arr(s.assignments, 'session.assignments')
      .map(parseAssignment)
      .sort((x, y) => x.position - y.position),
  };
}

function parseWeakness(raw: unknown): Weakness {
  const w = obj(raw, 'weakness');
  return {
    id: str(w.id, 'weakness.id'),
    name: str(w.name, 'weakness.name'),
    metricId: str(w.metric_id, 'weakness.metric_id'),
    rank: int(w.rank, 'weakness.rank', 1),
    perGame: num(w.per_game, 'weakness.per_game'),
    onServePerGame: num(w.on_serve_per_game, 'weakness.on_serve_per_game'),
    onReceivePerGame: num(w.on_receive_per_game, 'weakness.on_receive_per_game'),
    concededPerGame: num(w.conceded_per_game, 'weakness.conceded_per_game'),
  };
}

/** The §2.3 body as a `TrainingPlan`; throws `PlanShapeError` when it breaks the contract. */
export function parsePlan(raw: unknown): TrainingPlan {
  const p = obj(raw, 'plan');
  const prefs = obj(p.preferences, 'preferences');
  const ranking = obj(p.ranking, 'ranking');
  const limited = p.limited_data === null ? null : obj(p.limited_data, 'limited_data');
  return {
    id: str(p.id, 'id'),
    version: int(p.version, 'version', 1),
    createdAt: str(p.created_at, 'created_at'),
    unofficial: bool(p.unofficial, 'unofficial'),
    label: str(p.label, 'label'),
    drillsVerified: bool(p.drills_verified, 'drills_verified'),
    preferences: {
      minutesPerSession: int(prefs.minutes_per_session, 'preferences.minutes_per_session', 1),
      sessionsPerWeek: int(prefs.sessions_per_week, 'preferences.sessions_per_week', 1),
    },
    ranking: {
      unit: str(ranking.unit, 'ranking.unit'),
      sideOutVerified: bool(ranking.side_out_verified, 'ranking.side_out_verified'),
      games: int(ranking.games, 'ranking.games'),
      weaknesses: arr(ranking.weaknesses, 'ranking.weaknesses')
        .map(parseWeakness)
        .sort((x, y) => x.rank - y.rank),
    },
    limitedData: limited === null ? null : { rallies: int(limited.rallies, 'limited_data.rallies') },
    unfitted: arr(p.unfitted, 'unfitted').map((u) => {
      const o = obj(u, 'unfitted[]');
      return { weaknessId: str(o.weakness_id, 'unfitted.weakness_id'), reason: str(o.reason, 'unfitted.reason') };
    }),
    sessions: arr(p.sessions, 'sessions').map(parseSession),
  };
}

const SUPPORT_REF_RE = /^ref_[0-9a-f]{16}$/;

async function errorCode(response: Response): Promise<{ code: string | null; supportRef: string | null }> {
  try {
    const body = obj(await response.json(), 'error body');
    const e = obj(body.error ?? body, 'error');
    const ref = typeof e.support_ref === 'string' && SUPPORT_REF_RE.test(e.support_ref) ? e.support_ref : null;
    return { code: typeof e.code === 'string' ? e.code : null, supportRef: ref };
  } catch {
    return { code: null, supportRef: null }; // not JSON (a proxy page, an empty body)
  }
}

export function createPlanApi({ baseUrl, fetch: fetchFn }: { baseUrl: string; fetch?: typeof fetch }) {
  const base = baseUrl.replace(/\/+$/, '');
  return {
    /** P-01: the session account's current plan (api-sprint-04 §2.2). */
    async getPlan(): Promise<PlanRead> {
      let response: Response;
      try {
        response = await (fetchFn ?? globalThis.fetch)(`${base}/me/plan`, {
          method: 'GET',
          headers: { accept: 'application/json' },
          credentials: 'same-origin',
          cache: 'no-store',
          redirect: 'error',
        });
      } catch {
        return { kind: 'error', supportRef: null };
      }
      if (response.ok) {
        try {
          return { kind: 'plan', plan: parsePlan(await response.json()) };
        } catch {
          return { kind: 'error', supportRef: null };
        }
      }
      if (response.status === 401) return { kind: 'signed_out' };
      const { code, supportRef } = await errorCode(response);
      if (response.status === 404 && code === 'no_plan') return { kind: 'no_plan' };
      if (response.status === 409 && code === 'no_tagged_match') return { kind: 'no_tagged_match' };
      return { kind: 'error', supportRef };
    },
  };
}

export type PlanApi = ReturnType<typeof createPlanApi>;

export const planApi = createPlanApi({ baseUrl: '/api' });
