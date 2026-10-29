// @vitest-environment node
// Contract test (ST-072b IT level): the two Q-10 refusals of api-sprint-04 §7 exactly as the
// backend sends them (live-over-limit.json, captured from the API over real Postgres and the
// object store), read by the real clients: `createMatch` over real `fetch` with MSW answering,
// and the tus error reader the upload panel uses. Negative first: a 429 that is not one of the
// two codes never turns into a Q-10 message.
import { readFileSync } from 'node:fs';
import { http, HttpResponse, type JsonBodyType } from 'msw';
import { setupServer } from 'msw/node';
import { afterAll, afterEach, beforeAll, describe, expect, it } from 'vitest';
import { ApiError, createApiClient } from '@/lib/api/client';
import { matchLimitMessage, storageFullMessage } from '@/lib/api/quota';
import { uploadErrorDetail, uploadProblemFor } from '@/lib/upload/tus-policy';

type Captured = { status: number; body: JsonBodyType & { error: Record<string, unknown> } };
const live = JSON.parse(readFileSync(new URL('./live-over-limit.json', import.meta.url), 'utf8')) as {
  rate_limited: Captured;
  storage_quota_exceeded: Captured;
};
const BASE = 'http://api.test/api';
const server = setupServer();
// Late-bound fetch: MSW patches globalThis.fetch in beforeAll, after this module loads.
const api = createApiClient({ baseUrl: BASE, fetch: (input, init) => fetch(input, init) });
const NEW = { format: 'singles', scoring_system: 'side_out', played_on: '2026-10-29', participants: [] } as const;

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

async function refusal(status: number, body: JsonBodyType): Promise<ApiError> {
  server.use(http.post(`${BASE}/matches`, () => HttpResponse.json(body, { status })));
  return api.createMatch(NEW as never).then(
    () => expect.fail('createMatch resolved'),
    (e: unknown) => e as ApiError,
  );
}

describe('POST /matches 429 rate_limited (negative first)', () => {
  it('a 429 without the rate_limited code carries no time', async () => {
    const e = await refusal(429, { error: { code: 'teapot', retry_at: 'soon' } });
    expect([e.code, e.retryAt]).toEqual(['unknown', null]);
  });

  it('the live refusal gives retry_at, which becomes the local start time', async () => {
    expect(live.rate_limited.status).toBe(429);
    const e = await refusal(429, live.rate_limited.body);
    expect(e).toBeInstanceOf(ApiError);
    expect([e.status, e.code, e.retryAt]).toEqual([429, 'rate_limited', live.rate_limited.body.error.retry_at]);
    expect(matchLimitMessage(e.retryAt, { timeZone: 'UTC', now: new Date(e.retryAt!) })).toMatch(
      /You can start a new match at \d{2}:\d{2}\./,
    );
  });
});

describe('POST /matches/{id}/uploads 429 storage_quota_exceeded (negative first)', () => {
  it("today's unfinished-upload quota is not a storage refusal", () => {
    const detail = uploadErrorDetail(JSON.stringify({ error: { code: 'upload_quota_exceeded', retry_at: null } }));
    expect(uploadProblemFor(429, detail)).toBe('quota');
    expect(detail.quota ?? null).toBeNull();
  });

  it('the live refusal is read with its quota key into "used X of Y GB"', () => {
    const { status, body } = live.storage_quota_exceeded;
    expect(Object.keys(body.error).sort()).toEqual(['code', 'message', 'quota', 'retry_at', 'support_ref']);
    const detail = uploadErrorDetail(JSON.stringify(body));
    expect(uploadProblemFor(status, detail)).toBe('storage_full');
    expect(storageFullMessage(detail.quota ?? null)).toBe(
      "This video won't fit in your storage. You have used 18.2 of 20 GB. Delete a match you no longer need, then try again.",
    );
  });
});
