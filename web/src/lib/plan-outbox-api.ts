// The follow-through client (ST-063c; api-sprint-04 §3.1-§3.4; FR-124): "Mark done" with the op id
// as `Idempotency-Key`, undo, and the "Not for me" swap. Each answer is read into the outbox's and
// P-03's words; a dropped connection or an undocumented status is `failed` (a "done" stays queued).
// Authorisation is the API's: every route is the session's own plan [AQS/SEC-03].
import { parseSession, type Session } from '@/lib/api/plan';
import type { DoneOp, DoneResult } from './plan-outbox';

export type { DoneResult };
type Failed = { kind: 'failed'; supportRef: string | null };
export type UndoResult =
  | { kind: 'undone'; planVersion: number }
  | { kind: 'not_found' }
  | { kind: 'plan_conflict' }
  | { kind: 'signed_out' }
  | Failed;
export type SwapResult =
  | { kind: 'swapped'; session: Session; planVersion: number }
  | { kind: 'no_alternative' }
  | { kind: 'session_done' }
  | { kind: 'plan_conflict' }
  | { kind: 'not_found' }
  | { kind: 'signed_out' }
  | { kind: 'rate_limited'; retryAt: string | null }
  | Failed;

export interface FollowThroughApi {
  markDone(op: DoneOp): Promise<DoneResult>;
  undoDone(sessionId: string): Promise<UndoResult>;
  swap(assignmentId: string, reason: string): Promise<SwapResult>;
}

const SUPPORT_REF_RE = /^ref_[0-9a-f]{16}$/;
/** RFC 3339 UTC `retry_at` on a 429 (api-sprint-01 §1.1); anything else is read as no time. */
const RETRY_AT_RE = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$/;
/** 409 codes each route documents (api-sprint-04 §9). */
const DONE_CODES = { idempotency_key_reused: 'key_reused', plan_conflict: 'plan_conflict' } as const;
const SWAP_CODES = { no_alternative: 'no_alternative', session_done: 'session_done', plan_conflict: 'plan_conflict' } as const;

type Answer = { status: number; body: unknown } | null;

async function read(response: Response): Promise<unknown> {
  try {
    return await response.json();
  } catch {
    return null; // not JSON (a proxy page, an empty body)
  }
}

function errorOf(body: unknown): { code: string | null; supportRef: string | null } {
  const outer = typeof body === 'object' && body !== null ? (body as Record<string, unknown>) : {};
  const e = (typeof outer.error === 'object' && outer.error !== null ? outer.error : outer) as Record<string, unknown>;
  const ref = typeof e.support_ref === 'string' && SUPPORT_REF_RE.test(e.support_ref) ? e.support_ref : null;
  return { code: typeof e.code === 'string' ? e.code : null, supportRef: ref };
}

function version(body: unknown): number | null {
  const v = typeof body === 'object' && body !== null ? (body as Record<string, unknown>).plan_version : null;
  return typeof v === 'number' && Number.isInteger(v) && v >= 1 ? v : null;
}

/** The answer shared by the three routes: 401, 404, a documented 409, or failed. */
function refused<K extends string>(a: NonNullable<Answer>, codes: Record<string, K>): { kind: K | 'signed_out' | 'not_found' } | Failed {
  const { code, supportRef } = errorOf(a.body);
  if (a.status === 401) return { kind: 'signed_out' };
  if (a.status === 404) return { kind: 'not_found' };
  if (a.status === 409 && code !== null && code in codes) return { kind: codes[code]! };
  return { kind: 'failed', supportRef };
}

export function createFollowThroughApi({ baseUrl, fetch: fetchFn }: { baseUrl: string; fetch?: typeof fetch }): FollowThroughApi {
  const base = baseUrl.replace(/\/+$/, '');
  async function call(method: string, path: string, init: { headers?: Record<string, string>; body?: string } = {}): Promise<Answer> {
    try {
      const response = await (fetchFn ?? globalThis.fetch)(`${base}${path}`, {
        method,
        headers: { accept: 'application/json', ...init.headers },
        body: init.body,
        credentials: 'same-origin',
        cache: 'no-store',
        redirect: 'error',
      });
      return { status: response.status, body: await read(response) };
    } catch {
      return null;
    }
  }
  const failed: Failed = { kind: 'failed', supportRef: null };
  const sessionPath = (id: string) => `/me/plan/sessions/${encodeURIComponent(id)}/done`;

  return {
    async markDone(op) {
      const a = await call('POST', sessionPath(op.session_id), { headers: { 'idempotency-key': op.op_id } });
      if (a === null) return failed;
      if (a.status === 200) {
        const v = version(a.body);
        const replayed = (a.body as Record<string, unknown>).replayed === true;
        return v === null ? failed : { kind: 'done', planVersion: v, replayed };
      }
      return refused(a, DONE_CODES);
    },
    async undoDone(sessionId) {
      const a = await call('DELETE', sessionPath(sessionId));
      if (a === null) return failed;
      if (a.status === 200) {
        const v = version(a.body);
        return v === null ? failed : { kind: 'undone', planVersion: v };
      }
      return refused(a, { plan_conflict: 'plan_conflict' } as const);
    },
    async swap(assignmentId, reason) {
      const trimmed = reason.trim();
      const a = await call('POST', `/me/plan/assignments/${encodeURIComponent(assignmentId)}/swap`, {
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify(trimmed ? { reason: trimmed } : {}),
      });
      if (a === null) return failed;
      if (a.status === 200) {
        const v = version(a.body);
        try {
          const session = parseSession((a.body as Record<string, unknown>).session);
          return v === null ? failed : { kind: 'swapped', session, planVersion: v };
        } catch {
          return failed;
        }
      }
      if (a.status === 429 && errorOf(a.body).code === 'rate_limited') {
        const e = (a.body as { error?: { retry_at?: unknown } } | null)?.error;
        const at = typeof e?.retry_at === 'string' && RETRY_AT_RE.test(e.retry_at) ? e.retry_at : null;
        return { kind: 'rate_limited', retryAt: at };
      }
      return refused(a, SWAP_CODES);
    },
  };
}

export const followThroughApi = createFollowThroughApi({ baseUrl: '/api' });
