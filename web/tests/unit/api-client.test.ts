// Typed API client against docs/architecture/api-sprint-00.md (ST-010).
// The API is faked here with a recording fetch; unit tests only (no network, EP/ENG-17).
import { describe, expect, it, vi } from 'vitest';
import { ApiError, createApiClient } from '@/lib/api/client';

const MATCH_ID = '0b8f6c1e-3f3a-4c55-9a51-8d1f0e7d2a10';

const aMatch = (overrides: Record<string, unknown> = {}) => ({
  id: MATCH_ID,
  title: 'Skeleton test',
  format: 'doubles',
  status: 'awaiting_upload',
  media: null,
  created_at: '2026-10-05T09:12:44.123Z',
  updated_at: '2026-10-05T09:12:44.123Z',
  ...overrides,
});

const json = (status: number, body: unknown, headers: Record<string, string> = {}) =>
  new Response(JSON.stringify(body), {
    status,
    headers: { 'content-type': 'application/json; charset=utf-8', ...headers },
  });

const errorBody = (code: string, message = 'fixed text') => ({
  error: { code, message, support_ref: 'ref_5c1e0f3a9b7d4e21' },
});

function clientWith(...responses: Response[]) {
  const fetchFn = vi.fn<typeof fetch>();
  for (const r of responses) fetchFn.mockResolvedValueOnce(r);
  const client = createApiClient({ baseUrl: '/api', fetch: fetchFn });
  return { client, fetchFn };
}

describe('error handling', () => {
  it('turns the contract error body into an ApiError with status, code and support_ref', async () => {
    const { client } = clientWith(json(404, errorBody('not_found')));
    const err = await client.getMatch(MATCH_ID).catch((e: unknown) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect(err).toMatchObject({ status: 404, code: 'not_found', supportRef: 'ref_5c1e0f3a9b7d4e21' });
  });

  it('does not trust an unknown error code from the server', async () => {
    const { client } = clientWith(json(500, errorBody('<script>')));
    await expect(client.listMatches()).rejects.toMatchObject({ status: 500, code: 'unknown' });
  });

  it('copes with an error response that is not JSON (e.g. a proxy page)', async () => {
    const { client } = clientWith(new Response('<html>Bad gateway</html>', { status: 502 }));
    await expect(client.listMatches()).rejects.toMatchObject({ status: 502, code: 'unknown' });
  });

  it('reports a network failure as status 0', async () => {
    const fetchFn = vi.fn<typeof fetch>().mockRejectedValueOnce(new TypeError('Failed to fetch'));
    const client = createApiClient({ baseUrl: '/api', fetch: fetchFn });
    await expect(client.listMatches()).rejects.toMatchObject({ status: 0, code: 'network_error' });
  });

  it('never sends a request for a match ID that is not a UUID', async () => {
    const { client, fetchFn } = clientWith();
    await expect(client.getMatch('../me')).rejects.toMatchObject({ status: 404, code: 'not_found' });
    expect(fetchFn).not.toHaveBeenCalled();
  });

  it('rejects a 2xx body that does not match the contract', async () => {
    const { client } = clientWith(json(200, aMatch({ status: 'exploded' })));
    await expect(client.getMatch(MATCH_ID)).rejects.toMatchObject({ code: 'invalid_response' });
  });

  it('rejects media facts with the wrong types', async () => {
    const { client } = clientWith(
      json(200, aMatch({ status: 'video_received', media: { duration_ms: '60000' } })),
    );
    await expect(client.getMatch(MATCH_ID)).rejects.toMatchObject({ code: 'invalid_response' });
  });
});

describe('requests', () => {
  it('lists matches same-origin with credentials and no cache', async () => {
    const { client, fetchFn } = clientWith(json(200, { items: [aMatch()], next_cursor: null }));
    const matches = await client.listMatches();
    expect(matches).toHaveLength(1);
    expect(matches[0]?.title).toBe('Skeleton test');
    const [url, init] = fetchFn.mock.calls[0]!;
    expect(url).toBe('/api/matches?limit=50');
    expect(init).toMatchObject({ method: 'GET', credentials: 'same-origin', cache: 'no-store' });
  });

  it('creates a match with a closed JSON body', async () => {
    const { client, fetchFn } = clientWith(json(201, aMatch()));
    const match = await client.createMatch({ title: 'Skeleton test', format: 'doubles' });
    expect(match.id).toBe(MATCH_ID);
    const [url, init] = fetchFn.mock.calls[0]!;
    expect(url).toBe('/api/matches');
    expect(init?.method).toBe('POST');
    expect(new Headers(init?.headers).get('content-type')).toBe('application/json');
    expect(JSON.parse(String(init?.body))).toEqual({ title: 'Skeleton test', format: 'doubles' });
  });

  it('reads a match with its media facts', async () => {
    const media = {
      duration_ms: 60000,
      fps: 60,
      width: 1920,
      height: 1080,
      has_audio: true,
      vfr: false,
      container: 'mov,mp4,m4a,3gp,3g2,mj2',
      video_codec: 'h264',
    };
    const { client, fetchFn } = clientWith(json(200, aMatch({ status: 'video_received', media })));
    const match = await client.getMatch(MATCH_ID);
    expect(match.media).toEqual(media);
    expect(fetchFn.mock.calls[0]![0]).toBe(`/api/matches/${MATCH_ID}`);
  });

  it('drops fields the contract does not list', async () => {
    const { client } = clientWith(json(200, aMatch({ owner_id: 'secret' })));
    const match = await client.getMatch(MATCH_ID);
    expect(match).not.toHaveProperty('owner_id');
  });

  it('lists dev users and signs in with a 204', async () => {
    const { client, fetchFn } = clientWith(
      json(200, { items: [{ username: 'ivy', display_name: 'Ivy' }] }),
      new Response(null, { status: 204 }),
    );
    expect(await client.listDevUsers()).toEqual([{ username: 'ivy', display_name: 'Ivy' }]);
    await client.signIn('ivy');
    const [url, init] = fetchFn.mock.calls[1]!;
    expect(url).toBe('/api/dev/sign-in');
    expect(JSON.parse(String(init?.body))).toEqual({ username: 'ivy' });
  });

  it('signs out', async () => {
    const { client, fetchFn } = clientWith(new Response(null, { status: 204 }));
    await client.signOut();
    expect(fetchFn.mock.calls[0]![0]).toBe('/api/auth/sign-out');
    expect(fetchFn.mock.calls[0]![1]?.method).toBe('POST');
  });

  it('reads the signed-in player', async () => {
    const me = { id: '6f0c1e2a-3f3a-4c55-9a51-8d1f0e7d2a10', display_name: 'Ivy' };
    const { client } = clientWith(json(200, me));
    expect(await client.me()).toEqual(me);
  });

  it('forwards extra headers (the server side passes the session cookie through)', async () => {
    const fetchFn = vi.fn<typeof fetch>().mockResolvedValueOnce(
      json(200, { items: [], next_cursor: null }),
    );
    const client = createApiClient({
      baseUrl: 'http://api:8000',
      fetch: fetchFn,
      headers: { cookie: '__Host-racket_session=abc' },
    });
    await client.listMatches();
    const [url, init] = fetchFn.mock.calls[0]!;
    expect(url).toBe('http://api:8000/matches?limit=50');
    expect(new Headers(init?.headers).get('cookie')).toBe('__Host-racket_session=abc');
  });
});
