// @vitest-environment node
// Contract test (ST-071 IT level): the R-01 client against the backend's OpenAPI operations
// (openapi-me-privacy.json, from the FastAPI app) and real bodies captured on Postgres
// (live-privacy.json; api-sprint-04 §1 rule 3, §5, §6), over real `fetch` with MSW answering.
// Negative first: errors, broken bodies and a dropped connection never become a setting.
import { readFileSync } from 'node:fs';
import { http, HttpResponse, type JsonBodyType } from 'msw';
import { setupServer } from 'msw/node';
import { afterAll, afterEach, beforeAll, describe, expect, it } from 'vitest';
import { createPrivacySettingsApi } from '@/components/settings/PrivacySettingsApi';

type Op = { operationId: string; responses: string[] };
const openapi = JSON.parse(readFileSync(new URL('./openapi-me-privacy.json', import.meta.url), 'utf8')) as {
  paths: Record<string, Record<'get' | 'put', Op>>;
};
type Live = { status: number; body: JsonBodyType };
const live = JSON.parse(readFileSync(new URL('./live-privacy.json', import.meta.url), 'utf8')) as Record<string, Live>;
const BASE = 'http://api.test/api';
const server = setupServer();
const api = createPrivacySettingsApi({ baseUrl: BASE });
const seen: { method: string; url: string; body: unknown }[] = [];

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }));
afterEach(() => {
  server.resetHandlers();
  seen.length = 0;
});
afterAll(() => server.close());

function answer(method: 'get' | 'put', path: string, { status, body }: Live) {
  expect(openapi.paths[path]?.[method], `${method} ${path} is in the OpenAPI document`).toBeDefined();
  server.use(
    http[method](`${BASE}${path}`, async ({ request }) => {
      seen.push({ method: request.method, url: request.url, body: method === 'put' ? await request.json() : null });
      return HttpResponse.json(body, { status });
    }),
  );
}

describe('R-01 contract (negative first)', () => {
  it('a 422 on save is an error, never the value that was sent', async () => {
    expect(openapi.paths['/me/retention']!.put.responses).toContain('422');
    answer('put', '/me/retention', live.retention_put_unknown!);
    expect(await api.saveRetention(30)).toEqual({ kind: 'error', supportRef: 'ref_512b29ae3446e8ae' });
  });

  it('a 401 is signed out, for reads and saves', async () => {
    answer('get', '/me/retention', live.signed_out!);
    answer('put', '/me/training-consent', live.signed_out!);
    expect(await api.retention()).toEqual({ kind: 'signed_out' });
    expect(await api.saveConsent(true)).toEqual({ kind: 'signed_out' });
  });

  it('a body that breaks the representation is an error', async () => {
    answer('get', '/me/retention', { status: 200, body: { review_video_days: 7, choices: [30, 90, 365, null] } });
    answer('get', '/me/training-consent', { status: 200, body: { opt_in: 'yes' } });
    expect(await api.retention()).toEqual({ kind: 'error', supportRef: null });
    expect(await api.consent()).toEqual({ kind: 'error', supportRef: null });
  });

  it('a dropped connection is an error', async () => {
    server.use(http.put(`${BASE}/me/training-consent`, () => HttpResponse.error()));
    expect(await api.saveConsent(false)).toEqual({ kind: 'error', supportRef: null });
  });

  it('the flags read as off when the public config cannot be read', async () => {
    server.use(http.get(`${BASE}/config/public`, () => HttpResponse.error()));
    expect(await api.features()).toEqual({ retention: false, consent: false });
  });
});

describe('R-01 contract (live bodies)', () => {
  it('reads both flags from GET /config/public', async () => {
    answer('get', '/config/public', live.config!);
    expect(await api.features()).toEqual({ retention: true, consent: true });
  });

  it('reads and saves the retention choice with the closed body', async () => {
    answer('get', '/me/retention', live.retention_get!);
    expect(await api.retention()).toEqual({ kind: 'ok', value: { days: 90, choices: [30, 90, 365, null] } });
    answer('put', '/me/retention', live.retention_put_null!);
    expect(await api.saveRetention(null)).toEqual({ kind: 'ok', value: { days: null, choices: [30, 90, 365, null] } });
    expect(seen.at(-1)).toMatchObject({ method: 'PUT', body: { review_video_days: null } });
  });

  it('reads and saves the training consent with the closed body', async () => {
    answer('get', '/me/training-consent', live.consent_get!);
    expect(await api.consent()).toEqual({ kind: 'ok', value: { optIn: false } });
    answer('put', '/me/training-consent', live.consent_put_on!);
    expect(await api.saveConsent(true)).toEqual({ kind: 'ok', value: { optIn: true } });
    expect(seen.at(-1)).toMatchObject({ method: 'PUT', body: { opt_in: true } });
  });

  it('lists only matches with a video, with each review video deletion date', async () => {
    answer('get', '/matches', live.matches_30!);
    expect(await api.reviewVideos()).toEqual({
      kind: 'ok',
      value: [{ matchId: '6647c07e-7c78-41a1-86c4-a49d73f2a69b', title: 'Demo match', deleteAt: '2026-11-28T13:06:46.371Z' }],
    });
    answer('get', '/matches', live.matches_null!);
    expect(await api.reviewVideos()).toMatchObject({ kind: 'ok', value: [{ title: 'Demo match', deleteAt: null }] });
  });
});
