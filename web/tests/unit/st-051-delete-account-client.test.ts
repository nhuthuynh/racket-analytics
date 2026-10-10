// ST-051 (FR-007, NFR-066): the client half of the X-02 contract with the API,
// api-sprint-03 §4.2 `DELETE /me` with `{"confirm":"delete"}` answering 202.
// Negative cases first: a refusal or a dropped connection never resolves, so X-02 never clears
// the device or shows X-03 on them.
import { describe, expect, it, vi } from 'vitest';
import { createApiClient } from '@/lib/api/client';

const json = (status: number, body: unknown) =>
  new Response(JSON.stringify(body), { status, headers: { 'content-type': 'application/json' } });

function clientWith(response: Response | Error) {
  const fetchFn = vi.fn<typeof fetch>();
  if (response instanceof Error) fetchFn.mockRejectedValueOnce(response);
  else fetchFn.mockResolvedValueOnce(response);
  return { client: createApiClient({ baseUrl: '/api', fetch: fetchFn }), fetchFn };
}

describe('deleteAccount (DELETE /me, api-sprint-03 §4.2)', () => {
  it('signed out or already deleted (401) rejects with unauthenticated', async () => {
    const { client } = clientWith(json(401, { error: { code: 'unauthenticated' } }));
    await expect(client.deleteAccount()).rejects.toMatchObject({ status: 401, code: 'unauthenticated' });
  });

  it('a server failure (500) rejects with its code and reference', async () => {
    const { client } = clientWith(json(500, { error: { code: 'internal', support_ref: 'ref_0123456789abcdef' } }));
    await expect(client.deleteAccount()).rejects.toMatchObject({ status: 500, supportRef: 'ref_0123456789abcdef' });
  });

  it('a dropped connection rejects with network_error', async () => {
    const { client } = clientWith(new TypeError('Failed to fetch'));
    await expect(client.deleteAccount()).rejects.toMatchObject({ status: 0, code: 'network_error' });
  });

  it('sends DELETE /me with the confirmation body and resolves on 202 Accepted', async () => {
    const { client, fetchFn } = clientWith(new Response(null, { status: 202 }));
    await expect(client.deleteAccount()).resolves.toBeUndefined();
    expect(fetchFn).toHaveBeenCalledTimes(1);
    const [url, init] = fetchFn.mock.calls[0]!;
    expect(url).toBe('/api/me');
    expect(init?.method).toBe('DELETE');
    expect(JSON.parse(String(init?.body))).toEqual({ confirm: 'delete' });
    expect(new Headers(init?.headers).get('content-type')).toBe('application/json');
  });
});
