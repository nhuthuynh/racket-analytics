// @vitest-environment node
// Contract test (ST-068b IT level; FR-003; api-sprint-04 §4, ST-067 `GET /config/public`): the age
// client calls against the bodies captured from the real backend on Postgres with
// FEATURE_AGE_GATE on and off (live-age.json; how they were captured: docs/sprints/04/decisions/
// ST-068b.md), over real `fetch` with MSW answering. Negative first: "No" is never an account.
import { readFileSync } from 'node:fs';
import { http, HttpResponse, type JsonBodyType } from 'msw';
import { setupServer } from 'msw/node';
import { afterAll, afterEach, beforeAll, describe, expect, it } from 'vitest';
import { ApiError, createApiClient, needsAgeAnswer } from '@/lib/api/client';

type Live = Record<string, { status: number; body: JsonBodyType }>;
const LIVE = JSON.parse(readFileSync(new URL('./live-age.json', import.meta.url), 'utf8')) as Live;
const BASE = 'http://api.test/api';
const server = setupServer();
// `fetch` is looked up per call, so MSW (patched in beforeAll) answers.
const api = createApiClient({ baseUrl: BASE, fetch: (input, init) => fetch(input, init) });
const sent: { method: string; path: string; body: string }[] = [];

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }));
afterEach(() => {
  server.resetHandlers();
  sent.length = 0;
});
afterAll(() => server.close());

function answer(method: 'get' | 'post', path: string, key: string) {
  const live = LIVE[key]!;
  server.use(
    http[method](`${BASE}${path}`, async ({ request }) => {
      sent.push({ method: request.method, path: new URL(request.url).pathname, body: await request.text() });
      return HttpResponse.json(live.body, { status: live.status });
    }),
  );
}

describe('POST /me/age-confirmation', () => {
  it('"No" on a pending sign-in is under_age (403), never an account', async () => {
    answer('post', '/me/age-confirmation', 'under_age');
    await expect(api.confirmAge(false)).resolves.toBe('under_age');
    expect(sent).toEqual([{ method: 'POST', path: '/api/me/age-confirmation', body: '{"is_adult":false}' }]);
  });

  it('"No" on an existing account is a step (422 confirmation_required), nothing deleted', async () => {
    answer('post', '/me/age-confirmation', 'existing_no');
    await expect(api.confirmAge(false)).resolves.toBe('confirmation_required');
    expect(sent[0]!.body).toBe('{"is_adult":false}'); // never `confirm` from this page
  });

  it('a session that ended (401) and a flag turned off (404) stay errors for the page', async () => {
    answer('post', '/me/age-confirmation', 'after_under_age');
    await expect(api.confirmAge(true)).rejects.toMatchObject({ status: 401, code: 'unauthenticated' });
    answer('post', '/me/age-confirmation', 'route_off');
    await expect(api.confirmAge(true)).rejects.toMatchObject({ status: 404, code: 'not_found' });
  });

  it('a 5xx or a dropped connection is an error with its reference, not an outcome', async () => {
    server.use(
      http.post(`${BASE}/me/age-confirmation`, () =>
        HttpResponse.json({ error: { code: 'internal_error', support_ref: 'ref_0123456789abcdef' } }, { status: 500 }),
      ),
    );
    await expect(api.confirmAge(true)).rejects.toMatchObject({ status: 500, supportRef: 'ref_0123456789abcdef' });
    server.use(http.post(`${BASE}/me/age-confirmation`, () => HttpResponse.error()));
    await expect(api.confirmAge(true)).rejects.toMatchObject({ status: 0, code: 'network_error' });
  });

  it('"Yes" is the adult outcome (200 with age_confirmed_at)', async () => {
    answer('post', '/me/age-confirmation', 'adult');
    await expect(api.confirmAge(true)).resolves.toBe('adult');
    expect(sent[0]!.body).toBe('{"is_adult":true}');
  });
});

describe('GET /me while the gate is on', () => {
  it('a pending sign-in and an unconfirmed account both need the age answer; a 401 does not', async () => {
    for (const key of ['me_pending', 'me_unconfirmed']) {
      answer('get', '/me', key);
      const error = await api.me().catch((e: unknown) => e);
      expect(error).toBeInstanceOf(ApiError);
      expect(needsAgeAnswer(error)).toBe(true);
    }
    answer('get', '/me', 'after_under_age');
    expect(needsAgeAnswer(await api.me().catch((e: unknown) => e))).toBe(false);
    expect(needsAgeAnswer(new Error('age_confirmation_required'))).toBe(false);
  });
});

describe('GET /config/public', () => {
  it('a body without the features is a shape error, never "gate on"', async () => {
    server.use(http.get(`${BASE}/config/public`, () => HttpResponse.json({ features: { age_gate: 'yes' } })));
    await expect(api.publicConfig()).rejects.toMatchObject({ code: 'invalid_response' });
  });

  it('reads the age gate flag as the backend serves it', async () => {
    answer('get', '/config/public', 'config_off');
    await expect(api.publicConfig()).resolves.toEqual({ ageGate: false });
    answer('get', '/config/public', 'config_on');
    await expect(api.publicConfig()).resolves.toEqual({ ageGate: true });
  });
});
