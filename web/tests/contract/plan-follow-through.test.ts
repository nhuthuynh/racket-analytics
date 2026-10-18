// @vitest-environment node
// Contract test (ST-063c IT level): the follow-through client ("Mark done", undo, "Not for me")
// against the backend's OpenAPI operations (openapi-me-plan-follow-through.json, generated from
// the FastAPI app) and api-sprint-04 §3.1-§3.4, over real `fetch` with MSW answering. Negative
// first: a dropped connection or a 5xx is `failed` (the op stays queued), never a done.
import { readFileSync } from 'node:fs';
import { http, HttpResponse, type JsonBodyType } from 'msw';
import { setupServer } from 'msw/node';
import { afterAll, afterEach, beforeAll, describe, expect, it } from 'vitest';
import { createFollowThroughApi } from '@/lib/plan-outbox-api';
import { createOutbox, memoryOutboxStore } from '@/lib/plan-outbox';
import { planBody } from '../unit/fixtures/plan';

const openapi = JSON.parse(
  readFileSync(new URL('./openapi-me-plan-follow-through.json', import.meta.url), 'utf8'),
) as { paths: Record<string, Record<string, { responses: Record<string, unknown>; parameters?: { name: string }[] }>> };
const DONE = '/me/plan/sessions/{session_id}/done';
const SWAP = '/me/plan/assignments/{assignment_id}/swap';
const BASE = 'http://api.test/api';
const SESSION = '00000000-0000-4000-8000-000000000010';
const ASSIGNMENT = '00000000-0000-4000-8000-000000000102';
const DONE_URL = `${BASE}${DONE.replace('{session_id}', SESSION)}`;
const SWAP_URL = `${BASE}${SWAP.replace('{assignment_id}', ASSIGNMENT)}`;
const server = setupServer();
const api = createFollowThroughApi({ baseUrl: BASE });
const seen: { request: Request; body: string }[] = [];

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }));
afterEach(() => {
  server.resetHandlers();
  seen.length = 0;
});
afterAll(() => server.close());

const envelope = (code: string, extra: Record<string, unknown> = {}) => ({ error: { code, message: 'm', ...extra } });

function answer(method: 'post' | 'delete', url: string, status: number, body: JsonBodyType) {
  server.use(
    http[method](url, async ({ request }) => {
      seen.push({ request, body: await request.text() });
      return HttpResponse.json(body, { status });
    }),
  );
}

/** A 200 whose body is not JSON (a captive portal or proxy page) or is empty. */
function page(method: 'post' | 'delete', url: string, body: string | null) {
  server.use(http[method](url, () => new HttpResponse(body, { status: 200, headers: { 'content-type': 'text/html' } })));
}

function session() {
  return (planBody().sessions as Record<string, unknown>[])[0]!;
}

describe('POST /me/plan/sessions/{id}/done contract (negative first)', () => {
  it('a dropped connection is failed, not done', async () => {
    server.use(http.post(DONE_URL, () => HttpResponse.error()));
    expect(await api.markDone({ op_id: 'op-1', session_id: SESSION })).toEqual({ kind: 'failed', supportRef: null });
  });

  it('an undocumented 5xx is failed with the reference', async () => {
    expect(Object.keys(openapi.paths[DONE]!.post!.responses)).not.toContain('500');
    answer('post', DONE_URL, 500, envelope('internal_error', { support_ref: 'ref_0123456789abcdef' }));
    expect(await api.markDone({ op_id: 'op-1', session_id: SESSION })).toEqual({
      kind: 'failed',
      supportRef: 'ref_0123456789abcdef',
    });
  });

  it.each([
    ['a proxy page', '<html>proxy</html>'],
    ['an empty body', null],
  ])('a 200 with %s is failed, not a TypeError (review F1)', async (_what, body) => {
    page('post', DONE_URL, body);
    await expect(api.markDone({ op_id: 'op-1', session_id: SESSION })).resolves.toEqual({ kind: 'failed', supportRef: null });
  });

  it('a 200 proxy page keeps every queued op and the sync still reports (review F1)', async () => {
    const S2 = '00000000-0000-4000-8000-000000000011';
    page('post', DONE_URL, '<html>proxy</html>');
    page('post', `${BASE}${DONE.replace('{session_id}', S2)}`, '<html>proxy</html>');
    const box = createOutbox(memoryOutboxStore(), () => 'op-new');
    await box.queueDone(SESSION);
    await box.queueDone(S2);
    await expect(box.sync((op) => api.markDone(op))).resolves.toMatchObject({ synced: [], dropped: [], kept: [SESSION, S2] });
    expect((await box.pending()).map((op) => op.session_id)).toEqual([SESSION, S2]);
  });

  it('sends the op id as Idempotency-Key and reads the documented 200', async () => {
    expect(openapi.paths[DONE]!.post!.parameters!.map((p) => p.name)).toContain('Idempotency-Key');
    answer('post', DONE_URL, 200, {
      session_id: SESSION, done: true, done_at: '2026-10-18T10:00:00Z', plan_version: 2, replayed: true,
    });
    expect(await api.markDone({ op_id: 'op-offline-1', session_id: SESSION })).toEqual({
      kind: 'done',
      planVersion: 2,
      replayed: true,
    });
    expect(seen[0]!.request.headers.get('idempotency-key')).toBe('op-offline-1');
  });

  it.each([
    [404, 'not_found', { kind: 'not_found' }],
    [409, 'idempotency_key_reused', { kind: 'key_reused' }],
    [409, 'plan_conflict', { kind: 'plan_conflict' }],
    [401, 'unauthenticated', { kind: 'signed_out' }],
  ])('%i %s is documented and read', async (status, code, expected) => {
    expect(Object.keys(openapi.paths[DONE]!.post!.responses)).toContain(String(status));
    answer('post', DONE_URL, status, envelope(code));
    expect(await api.markDone({ op_id: 'op-1', session_id: SESSION })).toEqual(expected);
  });
});

describe('DELETE /me/plan/sessions/{id}/done contract (undo)', () => {
  it('a dropped connection is failed', async () => {
    server.use(http.delete(DONE_URL, () => HttpResponse.error()));
    expect(await api.undoDone(SESSION)).toEqual({ kind: 'failed', supportRef: null });
  });

  it('a 200 proxy page is failed, not undone', async () => {
    page('delete', DONE_URL, '<html>proxy</html>');
    await expect(api.undoDone(SESSION)).resolves.toEqual({ kind: 'failed', supportRef: null });
  });

  it('200 is undone', async () => {
    expect(Object.keys(openapi.paths[DONE]!.delete!.responses)).toContain('200');
    answer('delete', DONE_URL, 200, { session_id: SESSION, done: false, done_at: null, plan_version: 3 });
    expect(await api.undoDone(SESSION)).toEqual({ kind: 'undone', planVersion: 3 });
  });
});

describe('POST /me/plan/assignments/{id}/swap contract (negative first)', () => {
  it('409 no_alternative is read; the reason is sent in the closed body', async () => {
    expect(Object.keys(openapi.paths[SWAP]!.post!.responses)).toContain('409');
    answer('post', SWAP_URL, 409, envelope('no_alternative'));
    expect(await api.swap(ASSIGNMENT, '  too fast  ')).toEqual({ kind: 'no_alternative' });
    expect(JSON.parse(seen[0]!.body)).toEqual({ reason: 'too fast' });
  });

  it.each([
    ['session_done', { kind: 'session_done' }],
    ['plan_conflict', { kind: 'plan_conflict' }],
  ])('409 %s is read', async (code, expected) => {
    answer('post', SWAP_URL, 409, envelope(code));
    expect(await api.swap(ASSIGNMENT, '')).toEqual(expected);
  });

  it('a blank reason sends an empty body object', async () => {
    answer('post', SWAP_URL, 409, envelope('no_alternative'));
    await api.swap(ASSIGNMENT, '   ');
    expect(JSON.parse(seen[0]!.body)).toEqual({});
  });

  it('5xx is failed with the reference; 404 is not_found', async () => {
    answer('post', SWAP_URL, 503, envelope('unavailable', { support_ref: 'ref_0123456789abcdef' }));
    expect(await api.swap(ASSIGNMENT, '')).toEqual({ kind: 'failed', supportRef: 'ref_0123456789abcdef' });
    answer('post', SWAP_URL, 404, envelope('not_found'));
    expect(await api.swap(ASSIGNMENT, '')).toEqual({ kind: 'not_found' });
  });

  it('429 rate_limited is documented and read with its retry_at', async () => {
    expect(Object.keys(openapi.paths[SWAP]!.post!.responses)).toContain('429');
    answer('post', SWAP_URL, 429, envelope('rate_limited', { retry_at: '2026-10-18T14:05:00Z' }));
    expect(await api.swap(ASSIGNMENT, '')).toEqual({ kind: 'rate_limited', retryAt: '2026-10-18T14:05:00Z' });
  });

  it('429 without a readable retry_at is rate_limited with no time', async () => {
    answer('post', SWAP_URL, 429, envelope('rate_limited', { retry_at: 'soon' }));
    expect(await api.swap(ASSIGNMENT, '')).toEqual({ kind: 'rate_limited', retryAt: null });
  });

  it('200 is the updated session (§2.3 session object) and the plan version', async () => {
    const s = session();
    (s.assignments as Record<string, unknown>[])[0]!.drill = {
      id: 'pb.wall.serve-deep', version: 1, name: 'Deep serves', players: 1, needs: ['wall'], skills: ['serve'],
    };
    answer('post', SWAP_URL, 200, { plan_version: 4, session: s as JsonBodyType });
    const r = await api.swap(ASSIGNMENT, '');
    expect(r.kind).toBe('swapped');
    if (r.kind !== 'swapped') return;
    expect(r.planVersion).toBe(4);
    expect(r.session.id).toBe(SESSION);
    expect(r.session.assignments.find((a) => a.id === ASSIGNMENT)!.drill.name).toBe('Deep serves');
  });

  it('a 200 proxy page is failed, not a swap', async () => {
    page('post', SWAP_URL, '<html>proxy</html>');
    await expect(api.swap(ASSIGNMENT, '')).resolves.toEqual({ kind: 'failed', supportRef: null });
  });

  it('a 200 that breaks the session representation is failed, not a swap', async () => {
    answer('post', SWAP_URL, 200, { plan_version: 4, session: { id: SESSION } });
    expect(await api.swap(ASSIGNMENT, '')).toEqual({ kind: 'failed', supportRef: null });
  });
});
