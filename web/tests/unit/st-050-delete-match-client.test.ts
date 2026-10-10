// ST-050 (FR-006, NFR-066; ADR 0043): the client half of the X-01 contract with the API,
// api-sprint-03 §4.1 `DELETE /matches/{id}` with `{"confirm":"delete"}` answering 202.
// Negative cases first: a refusal, a malformed id and a dropped connection never resolve.
import { describe, expect, it, vi } from 'vitest';
import { createApiClient } from '@/lib/api/client';

const ID = '0b8f6c1e-3f3a-4c55-9a51-8d1f0e7d2a10';
const json = (status: number, body: unknown) =>
  new Response(JSON.stringify(body), { status, headers: { 'content-type': 'application/json' } });

function clientWith(response: Response | Error) {
  const fetchFn = vi.fn<typeof fetch>();
  if (response instanceof Error) fetchFn.mockRejectedValueOnce(response);
  else fetchFn.mockResolvedValueOnce(response);
  return { client: createApiClient({ baseUrl: '/api', fetch: fetchFn }), fetchFn };
}

describe('deleteMatch (DELETE /matches/{id}, api-sprint-03 §4.1)', () => {
  it('someone else\'s or an already deleted match (404) rejects with not_found and its reference', async () => {
    const { client } = clientWith(json(404, { error: { code: 'not_found', support_ref: 'ref_0123456789abcdef' } }));
    await expect(client.deleteMatch(ID)).rejects.toMatchObject({
      status: 404,
      code: 'not_found',
      supportRef: 'ref_0123456789abcdef',
    });
  });

  it('signed out (401) rejects with unauthenticated', async () => {
    const { client } = clientWith(json(401, { error: { code: 'unauthenticated' } }));
    await expect(client.deleteMatch(ID)).rejects.toMatchObject({ status: 401, code: 'unauthenticated' });
  });

  it('a malformed id is refused before any request is sent', async () => {
    const { client, fetchFn } = clientWith(new Response(null, { status: 202 }));
    await expect(client.deleteMatch('../me')).rejects.toMatchObject({ code: 'not_found' });
    expect(fetchFn).not.toHaveBeenCalled();
  });

  it('a dropped connection rejects with network_error', async () => {
    const { client } = clientWith(new TypeError('Failed to fetch'));
    await expect(client.deleteMatch(ID)).rejects.toMatchObject({ status: 0, code: 'network_error' });
  });

  it('sends DELETE with the confirmation body and resolves on 202 Accepted', async () => {
    const { client, fetchFn } = clientWith(new Response(null, { status: 202 }));
    await expect(client.deleteMatch(ID)).resolves.toBeUndefined();
    expect(fetchFn).toHaveBeenCalledTimes(1);
    const [url, init] = fetchFn.mock.calls[0]!;
    expect(url).toBe(`/api/matches/${ID}`);
    expect(init?.method).toBe('DELETE');
    expect(JSON.parse(String(init?.body))).toEqual({ confirm: 'delete' });
    expect(new Headers(init?.headers).get('content-type')).toBe('application/json');
  });
});
