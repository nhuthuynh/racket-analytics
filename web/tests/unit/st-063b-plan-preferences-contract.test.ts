// Contract test (ST-063b IT level): the P-02 client against the backend's OpenAPI operation
// `POST /me/plan` (fixtures/openapi-post-me-plan.json, generated from the FastAPI app) and the
// api-sprint-04 §2.1/§2.2 refusals. A fake fetch answers; the request the client sends is checked
// against the operation's request schema. Negative first: every refusal is an outcome, never a throw.
import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import { createPlanPreferencesApi } from '@/components/plan/PlanPreferencesApi';
import type { PlanPreferences } from '@/components/plan/PlanPreferencesModel';

type Schema = {
  type?: string; minimum?: number; maximum?: number; enum?: unknown[]; items?: Schema; anyOf?: Schema[];
  properties?: Record<string, Schema>; required?: string[]; additionalProperties?: boolean;
};
const op = JSON.parse(readFileSync(new URL('./fixtures/openapi-post-me-plan.json', import.meta.url), 'utf8')) as {
  path: string;
  post: { requestBody: { content: { 'application/json': { schema: Schema } } }; responses: Record<string, unknown> };
};
const requestSchema = op.post.requestBody.content['application/json'].schema;

/** The JSON Schema keywords the generated operation uses; returns the paths that break it. */
function violations(value: unknown, s: Schema, at = '$'): string[] {
  if (s.anyOf) return s.anyOf.some((alt) => violations(value, alt, at).length === 0) ? [] : [at];
  if (s.enum && !s.enum.includes(value)) return [at];
  if (s.type === 'integer' && !Number.isInteger(value)) return [at];
  if (s.type === 'string' && typeof value !== 'string') return [at];
  if (s.type === 'null' && value !== null) return [at];
  if (typeof value === 'number' && ((s.minimum ?? -Infinity) > value || (s.maximum ?? Infinity) < value)) return [at];
  if (s.type === 'array') {
    if (!Array.isArray(value)) return [at];
    return value.flatMap((v, i) => violations(v, s.items ?? {}, `${at}[${i}]`));
  }
  if (s.type === 'object') {
    if (typeof value !== 'object' || value === null) return [at];
    const obj = value as Record<string, unknown>;
    const missing = (s.required ?? []).filter((k) => !(k in obj)).map((k) => `${at}.${k}`);
    const extra = s.additionalProperties === false ? Object.keys(obj).filter((k) => !s.properties?.[k]).map((k) => `${at}.${k}`) : [];
    const inner = Object.entries(obj).flatMap(([k, v]) => (s.properties?.[k] ? violations(v, s.properties[k], `${at}.${k}`) : []));
    return [...missing, ...extra, ...inner];
  }
  return [];
}

const solo: PlanPreferences = { minutesPerSession: 30, sessionsPerWeek: 3, playersAvailable: 1, equipment: ['wall'], level: 'intermediate' };

function answering(status: number, body: unknown) {
  const seen: { url: string; init: RequestInit }[] = [];
  const fetch = (async (url: string, init: RequestInit) => {
    seen.push({ url, init });
    return new Response(body === undefined ? null : JSON.stringify(body), { status, headers: { 'content-type': 'application/json' } });
  }) as unknown as typeof globalThis.fetch;
  return { api: createPlanPreferencesApi({ baseUrl: 'http://api.test/api', fetch }), seen };
}
const envelope = (code: string, extra: Record<string, unknown> = {}) => ({ error: { code, message: 'm', ...extra } });

describe('POST /me/plan contract (negative first)', () => {
  it('the validator refuses a body that breaks the generated schema (positive control)', () => {
    expect(violations({ minutes_per_session: 10, sessions_per_week: 3, players_available: 1, equipment: ['rocket'], level: 'x', extra: 1 }, requestSchema))
      .toEqual(['$.extra', '$.minutes_per_session', '$.equipment[0]', '$.level']);
  });

  it.each([
    ['no_tagged_match', { kind: 'no_tagged_match' }],
    ['no_plan_fits', { kind: 'no_plan_fits' }],
    ['plan_conflict', { kind: 'plan_conflict' }],
  ])('409 %s is its own outcome', async (code, outcome) => {
    expect(Object.keys(op.post.responses)).toContain('409');
    expect(await answering(409, envelope(code)).api.generatePlan(solo)).toEqual(outcome);
  });

  it('422 field codes become field errors; 422 without a known field is a general error', async () => {
    expect(Object.keys(op.post.responses)).toContain('422');
    const fields = [{ field: 'minutes_per_session', code: 'out_of_range' }];
    expect(await answering(422, envelope('validation_failed', { fields })).api.generatePlan(solo)).toEqual({
      kind: 'invalid', errors: [{ field: 'minutes-per-session', message: 'Enter a number between 15 and 180' }],
    });
    expect(await answering(422, envelope('validation_failed', { fields: [{ field: null, code: 'unknown_field' }] })).api.generatePlan(solo))
      .toEqual({ kind: 'error', supportRef: null });
  });

  it('401 is signed out; 5xx carries the support reference; a dropped connection is an error', async () => {
    expect(await answering(401, envelope('unauthenticated')).api.generatePlan(solo)).toEqual({ kind: 'signed_out' });
    expect(await answering(500, envelope('internal_error', { support_ref: 'ref_0123456789abcdef' })).api.generatePlan(solo))
      .toEqual({ kind: 'error', supportRef: 'ref_0123456789abcdef' });
    const fetch = (async () => { throw new TypeError('offline'); }) as unknown as typeof globalThis.fetch;
    expect(await createPlanPreferencesApi({ baseUrl: '/api', fetch }).generatePlan(solo)).toEqual({ kind: 'error', supportRef: null });
  });

  it('201 sends a body the generated schema accepts, as JSON, to the documented path', async () => {
    expect(Object.keys(op.post.responses)).toContain('201');
    const { api, seen } = answering(201, { id: 'p' });
    expect(await api.generatePlan({ ...solo, equipment: ['ball_machine', 'wall'] })).toEqual({ kind: 'created' });
    expect(seen).toHaveLength(1);
    expect(seen[0]!.url).toBe(`http://api.test/api${op.path}`);
    expect(seen[0]!.init.method).toBe('POST');
    expect(new Headers(seen[0]!.init.headers).get('content-type')).toBe('application/json');
    expect(violations(JSON.parse(String(seen[0]!.init.body)), requestSchema)).toEqual([]);
  });
});

describe('GET /me/plan for the last preferences (api-sprint-04 §2.2)', () => {
  it('404 no_plan is a first visit; 401 is signed out; a broken body or 5xx is an error', async () => {
    expect(await answering(404, envelope('no_plan')).api.lastPreferences()).toEqual({ kind: 'none' });
    expect(await answering(401, envelope('unauthenticated')).api.lastPreferences()).toEqual({ kind: 'signed_out' });
    expect(await answering(200, { preferences: { level: 'pro' } }).api.lastPreferences()).toEqual({ kind: 'error' });
    expect(await answering(503, envelope('unavailable')).api.lastPreferences()).toEqual({ kind: 'error' });
  });

  it('200 reads the plan preferences', async () => {
    const preferences = { minutes_per_session: 45, sessions_per_week: 2, weekly_minutes: 90, players_available: 2, equipment: [], level: 'advanced' };
    expect(await answering(200, { id: 'p', preferences }).api.lastPreferences()).toEqual({
      kind: 'preferences',
      preferences: { minutesPerSession: 45, sessionsPerWeek: 2, playersAvailable: 2, equipment: [], level: 'advanced' },
    });
  });
});
