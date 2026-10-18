// @vitest-environment node
// Contract test (ST-063a IT level): the P-01 plan client against the backend's OpenAPI operation
// `GET /me/plan` (openapi-me-plan.json, generated from the FastAPI app) and the api-sprint-04 §2.3
// representation, over real `fetch` with MSW answering. Negative first: an undocumented status and
// a body that breaks the representation are errors, never a half-drawn plan.
import { readFileSync } from 'node:fs';
import { http, HttpResponse, type JsonBodyType } from 'msw';
import { setupServer } from 'msw/node';
import { afterAll, afterEach, beforeAll, describe, expect, it } from 'vitest';
import { createPlanApi } from '@/lib/api/plan';
import { MATCH_ID, planBody, withFirstAssignment } from '../unit/fixtures/plan';

const openapi = JSON.parse(readFileSync(new URL('./openapi-me-plan.json', import.meta.url), 'utf8')) as {
  path: string;
  get: { responses: Record<string, unknown> };
};
// A real 200 body: GET /me/plan on Postgres after tagging the worked example (st.tagged_example)
// and POST /me/plan solo, wall, 30 min, 3 a week, intermediate (decisions ST-063a, 2026-10-18).
const live = JSON.parse(readFileSync(new URL('./live-plan.json', import.meta.url), 'utf8')) as JsonBodyType;
const BASE = 'http://api.test/api';
const URL_ = `${BASE}${openapi.path}`;
const server = setupServer();
const api = createPlanApi({ baseUrl: BASE });
const seen: Request[] = [];

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }));
afterEach(() => {
  server.resetHandlers();
  seen.length = 0;
});
afterAll(() => server.close());

function answer(status: number, body: JsonBodyType) {
  server.use(
    http.get(URL_, ({ request }) => {
      seen.push(request);
      return HttpResponse.json(body, { status });
    }),
  );
}

const envelope = (code: string, extra: Record<string, unknown> = {}) => ({ error: { code, message: 'm', ...extra } });

describe('GET /me/plan contract (negative first)', () => {
  it('an undocumented status without a plan code is an error with the support reference', async () => {
    expect(Object.keys(openapi.get.responses)).not.toContain('500');
    answer(500, envelope('internal_error', { support_ref: 'ref_0123456789abcdef' }));
    expect(await api.getPlan()).toEqual({ kind: 'error', supportRef: 'ref_0123456789abcdef' });
  });

  it('a 200 body that breaks the §2.3 representation is an error, not a plan', async () => {
    answer(200, { ...planBody(), sessions: 'none' });
    expect(await api.getPlan()).toEqual({ kind: 'error', supportRef: null });
  });

  it('a dropped connection is an error', async () => {
    server.use(http.get(URL_, () => HttpResponse.error()));
    expect(await api.getPlan()).toEqual({ kind: 'error', supportRef: null });
  });

  it('a citation that breaks the representation spoils only its own row', async () => {
    answer(200, withFirstAssignment((a) => { a.citation = { metric_id: 'AN-05' }; }));
    const read = await api.getPlan();
    if (read.kind !== 'plan') throw new Error(`expected a plan, got ${read.kind}`);
    const rows = read.plan.sessions[0]!.assignments;
    expect(rows.find((a) => a.drill.name === 'Serve to a target')?.citation).toBeNull();
    expect(rows.find((a) => a.drill.name === 'Wall dinks warm-up')?.citation).not.toBeNull();
  });
});

describe('GET /me/plan contract: every documented status', () => {
  it('documents exactly 200, 401 and 404', () => {
    expect(Object.keys(openapi.get.responses).sort()).toEqual(['200', '401', '404']);
  });

  it('asks GET on the documented path, for JSON, with the session cookie and no cache', async () => {
    answer(200, planBody());
    await api.getPlan();
    expect(seen).toHaveLength(1);
    const request = seen[0]!;
    expect(request.method).toBe('GET');
    expect(new URL(request.url).pathname).toBe(`/api${openapi.path}`);
    expect(request.headers.get('accept')).toBe('application/json');
    expect(request.credentials).toBe('same-origin');
    expect(request.cache).toBe('no-store');
  });

  it('200: the §2.3 plan in the ubiquitous language', async () => {
    answer(200, planBody());
    const read = await api.getPlan();
    if (read.kind !== 'plan') throw new Error(`expected a plan, got ${read.kind}`);
    const { plan } = read;
    expect(plan.createdAt).toBe('2026-10-17T09:00:00Z');
    expect(plan.unofficial).toBe(true);
    expect(plan.drillsVerified).toBe(false);
    expect(plan.limitedData).toEqual({ rallies: 14 });
    expect(plan.ranking.unit).toBe('rallies_lost_per_game');
    expect(plan.ranking.weaknesses.map((w) => [w.id, w.rank, w.perGame])).toEqual([
      ['unforced_errors', 1, 2],
      ['serve_faults', 2, 1],
    ]);
    expect(plan.preferences.sessionsPerWeek).toBe(3);
    // Drills in position order: the warm-up first.
    expect(plan.sessions[0]!.assignments.map((a) => [a.position, a.warmUp])).toEqual([[1, true], [2, false]]);
    expect(plan.sessions[0]!.assignments[1]!.citation).toEqual({
      metricId: 'AN-05', side: 'A', value: 0.2857, n: 7, lowSample: true,
      evidence: [{ matchId: MATCH_ID, side: 'A', n: 7 }], why: 'Serve faults: 29% of 7 serves',
    });
  });

  it('200: the body the backend really sends parses, every drill cited, the unfitted weakness kept', async () => {
    answer(200, live);
    const read = await api.getPlan();
    if (read.kind !== 'plan') throw new Error(`expected a plan, got ${read.kind}`);
    const drills = read.plan.sessions.flatMap((s) => s.assignments);
    expect(read.plan.sessions).toHaveLength(6);
    expect(drills.length).toBeGreaterThan(0);
    expect(drills.filter((a) => a.citation === null)).toEqual([]);
    expect(read.plan.sessions.every((s) => s.assignments[0]?.warmUp)).toBe(true);
    expect(read.plan.ranking.weaknesses.map((w) => w.rank)).toEqual([1, 2, 3]);
    expect(read.plan.unfitted).toEqual([{ weaknessId: 'serve_faults', reason: 'no_drill_fits' }]);
    expect(read.plan.limitedData).toEqual({ rallies: 13 });
  });

  it('401: signed out', async () => {
    answer(401, envelope('unauthenticated'));
    expect(await api.getPlan()).toEqual({ kind: 'signed_out' });
  });

  it('404 no_plan: no plan yet', async () => {
    answer(404, envelope('no_plan'));
    expect(await api.getPlan()).toEqual({ kind: 'no_plan' });
  });

  it('409 no_tagged_match (the POST refusal, api-sprint-04 §9) reads as no tagged match', async () => {
    answer(409, envelope('no_tagged_match'));
    expect(await api.getPlan()).toEqual({ kind: 'no_tagged_match' });
  });
});
