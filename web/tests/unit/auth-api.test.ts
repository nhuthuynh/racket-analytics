// Sprint 1 auth calls of the typed client (ST-013; api-sprint-01 §1.1, §2). Faked fetch only.
import { describe, expect, it, vi } from 'vitest';
import { ApiError, createApiClient } from '@/lib/api/client';

const json = (status: number, body: unknown, headers: Record<string, string> = {}) =>
  new Response(JSON.stringify(body), { status, headers: { 'content-type': 'application/json', ...headers } });

function clientWith(...responses: Response[]) {
  const fetchFn = vi.fn<typeof fetch>();
  for (const r of responses) fetchFn.mockResolvedValueOnce(r);
  return { client: createApiClient({ baseUrl: '/api', fetch: fetchFn }), fetchFn };
}

const TOKEN = 'a'.repeat(43);

describe('error body, Sprint 1 keys (api-sprint-01 §1.1)', () => {
  it('drops field errors whose code is not in the closed list', async () => {
    const { client } = clientWith(
      json(422, {
        error: {
          code: 'validation_failed',
          message: 'x',
          support_ref: 'ref_5c1e0f3a9b7d4e21',
          fields: [
            { field: 'email', code: '<img src=x>' },
            { field: 'participants.side_b', code: 'side_needs_two_players' },
          ],
        },
      }),
    );
    const err = (await client.requestLink('ivy@example.com').catch((e: unknown) => e)) as ApiError;
    expect(err.fields).toEqual([{ field: 'participants.side_b', code: 'side_needs_two_players' }]);
  });

  it('has no fields and no retry time on other errors', async () => {
    const { client } = clientWith(json(500, { error: { code: 'internal_error', message: 'x' } }));
    const err = (await client.requestLink('ivy@example.com').catch((e: unknown) => e)) as ApiError;
    expect(err.fields).toEqual([]);
    expect(err.retryAt).toBeNull();
  });

  it('reads retry_at on 429 and ignores a malformed one', async () => {
    const { client } = clientWith(
      json(429, { error: { code: 'rate_limited', message: 'x', retry_at: '2026-10-05T14:32:00Z' } }),
      json(429, { error: { code: 'rate_limited', message: 'x', retry_at: 'soon' } }),
    );
    const first = (await client.requestLink('a@b.co').catch((e: unknown) => e)) as ApiError;
    expect(first.retryAt).toBe('2026-10-05T14:32:00Z');
    const second = (await client.requestLink('a@b.co').catch((e: unknown) => e)) as ApiError;
    expect(second.retryAt).toBeNull();
  });
});

describe('POST /auth/links', () => {
  it('posts only the email and accepts 202 without a body', async () => {
    const { client, fetchFn } = clientWith(new Response(null, { status: 202 }));
    await client.requestLink('ivy@example.com');
    const [url, init] = fetchFn.mock.calls[0]!;
    expect(url).toBe('/api/auth/links');
    expect(init?.method).toBe('POST');
    expect(JSON.parse(String(init?.body))).toEqual({ email: 'ivy@example.com' });
  });
});

describe('POST /auth/exchange', () => {
  it('refuses a malformed token without calling the API', async () => {
    const { client, fetchFn } = clientWith();
    await expect(client.exchangeLink('short')).rejects.toMatchObject({ status: 401, code: 'link_expired' });
    expect(fetchFn).not.toHaveBeenCalled();
  });

  it('maps the expired/used refusal to link_expired', async () => {
    const { client } = clientWith(json(401, { error: { code: 'link_expired', message: 'x' } }));
    await expect(client.exchangeLink(TOKEN)).rejects.toMatchObject({ status: 401, code: 'link_expired' });
  });

  it('returns whether the account is new', async () => {
    const { client, fetchFn } = clientWith(
      json(200, { account: { id: 'x', display_name: null }, new_account: true }),
    );
    await expect(client.exchangeLink(TOKEN)).resolves.toEqual({ newAccount: true });
    expect(JSON.parse(String(fetchFn.mock.calls[0]![1]?.body))).toEqual({ token: TOKEN });
  });
});

describe('GET /me', () => {
  it('accepts a null display name (magic-link accounts)', async () => {
    const { client } = clientWith(json(200, { id: 'x', display_name: null }));
    await expect(client.me()).resolves.toEqual({ id: 'x', display_name: null });
  });
});
