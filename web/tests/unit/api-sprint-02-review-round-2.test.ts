// Review round 2 (BE-RV1-FE-01 a-d, QA-RV2-11): the client follows api-sprint-02 §2.2, §3, §4.
// Negative cases first: a code the contract added must not parse to "unknown"; a field code of
// §4.2 must not be dropped; the history must not stop at the first page.
import { describe, expect, it, vi } from 'vitest';
import { createApiClient } from '@/lib/api/client';

const ID = '0b8f6c1e-3f3a-4c55-9a51-8d1f0e7d2a10';
const RALLY = '7d0c6c1e-3f3a-4c55-9a51-8d1f0e7d2a10';
const json = (status: number, body: unknown) =>
  new Response(JSON.stringify(body), { status, headers: { 'content-type': 'application/json' } });
const sheet = { rules_version: 'PROVISIONAL-UNVERIFIED', unofficial: true, label: 'unofficial scoring (rules not yet verified)', rows: [] };
const err = (status: number, code: string, fields?: unknown) => json(status, { error: { code, support_ref: null, ...(fields ? { fields } : {}) } });

function clientWith(...responses: Response[]) {
  const fetchFn = vi.fn<typeof fetch>();
  for (const r of responses) fetchFn.mockResolvedValueOnce(r);
  return { client: createApiClient({ baseUrl: '/api', fetch: fetchFn }), fetchFn };
}

const item = (n: number) => ({
  id: `7d0c6c1e-3f3a-4c55-9a51-8d1f0e7d${String(n).padStart(4, '0')}`, kind: 'correction', rally_id: RALLY, rally_number: 1,
  field: 'winning_side', old_value: 'A', new_value: 'B', undoes: null, at: '2026-10-06T10:00:00Z',
});

describe('(a, e) Sprint 2 error codes', () => {
  it('409 rules_unavailable and 422 scorebook_full keep their codes and the cap field code', async () => {
    const { client } = clientWith(
      err(409, 'rules_unavailable'),
      err(422, 'scorebook_full', [{ field: null, code: 'too_many_rallies' }]),
    );
    await expect(client.startGame(ID, 0, { first_serving_side: 'A', ends_switched: false })).rejects.toMatchObject({ code: 'rules_unavailable' });
    await expect(
      client.tagRally(ID, 1, { start_ms: 0, end_ms: 1, winning_side: 'A', ending: 'winner', responsible_player: null, fault_kind: null }),
    ).rejects.toMatchObject({ code: 'scorebook_full', fields: [{ field: null, code: 'too_many_rallies' }] });
  });
});

describe('(b) §4.2 field codes are kept', () => {
  it.each([
    ['end_ms', 'time_after_video'],
    ['start_ms', 'out_of_game_order'],
    ['start_ms', 'overlaps_rally'],
    ['end_ms', 'end_before_start'],
    ['start_ms', 'time_invalid'],
    ['responsible_player', 'must_be_on_losing_side'],
    ['decision', 'previous_game_over'],
    ['decision', 'not_first_in_game'],
    ['value', 'unchanged'],
  ])('%s/%s', async (field, code) => {
    const { client } = clientWith(err(422, 'invalid_rally', [{ field, code }]));
    await expect(client.undo(ID, 1)).rejects.toMatchObject({ fields: [{ field, code }] });
  });
});

describe('(c) move_to_previous_game', () => {
  it('sends the decision with If-Match', async () => {
    const { client, fetchFn } = clientWith(json(200, { version: 5, sheet }));
    await client.resolveRally(ID, 4, RALLY, 'move_to_previous_game');
    const [url, init] = fetchFn.mock.calls[0]!;
    expect(url).toBe(`/api/matches/${ID}/rallies/${RALLY}/resolution`);
    expect(JSON.parse(init?.body as string)).toEqual({ decision: 'move_to_previous_game' });
    expect(new Headers(init?.headers).get('if-match')).toBe('4');
  });
});

describe('(d) the history follows next_cursor', () => {
  it('refuses a next_cursor that is not a string or null', async () => {
    const { client } = clientWith(json(200, { items: [item(1)], next_cursor: 7 }));
    await expect(client.corrections(ID)).rejects.toMatchObject({ code: 'invalid_response' });
  });

  it('reads every page, in order, passing the cursor (URL-encoded)', async () => {
    const { client, fetchFn } = clientWith(
      json(200, { items: [item(1), item(2)], next_cursor: 'c/2+' }),
      json(200, { items: [item(3)], next_cursor: 'c3' }),
      json(200, { items: [item(4)], next_cursor: null }),
    );
    const all = await client.corrections(ID);
    expect(all.map((i) => i.id)).toEqual([item(1).id, item(2).id, item(3).id, item(4).id]);
    expect(fetchFn.mock.calls.map((c) => c[0])).toEqual([
      `/api/matches/${ID}/corrections?limit=200`,
      `/api/matches/${ID}/corrections?limit=200&cursor=c%2F2%2B`,
      `/api/matches/${ID}/corrections?limit=200&cursor=c3`,
    ]);
  });

  it('stops on a cursor the server repeats (no endless loop)', async () => {
    const { client, fetchFn } = clientWith(
      json(200, { items: [item(1)], next_cursor: 'same' }),
      json(200, { items: [item(2)], next_cursor: 'same' }),
    );
    await expect(client.corrections(ID)).rejects.toMatchObject({ code: 'invalid_response' });
    expect(fetchFn).toHaveBeenCalledTimes(2);
  });
});
