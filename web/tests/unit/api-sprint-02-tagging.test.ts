// ST-027 FE slice 2: the typed client for the Sprint 2 tagging routes. Route and field names
// follow scripts/measure/tagcontract.py until api-sprint-02.md exists (decision-log 2026-10-05).
// Negative cases first: unknown shapes are refused (fail closed), and the optimistic lock
// version is always sent.
import { describe, expect, it, vi } from 'vitest';
import { createApiClient } from '@/lib/api/client';

const ID = '0b8f6c1e-3f3a-4c55-9a51-8d1f0e7d2a10';
const RALLY = '7d0c6c1e-3f3a-4c55-9a51-8d1f0e7d2a10';
const json = (status: number, body: unknown, headers: Record<string, string> = {}) =>
  new Response(JSON.stringify(body), { status, headers: { 'content-type': 'application/json', ...headers } });

const row = {
  rally_id: RALLY, number: 1, game: 1, start_ms: 0, end_ms: 7999, serving_side: 'A',
  score_before: '0-0-2', score_after: '1-0-2', winning_side: 'A', ending: 'winner',
  responsible_player: 'A1', fault_kind: null, marker: null, corrected_by_user: false,
};
const sheet = {
  rules_version: 'PROVISIONAL-UNVERIFIED', unofficial: true,
  label: 'unofficial scoring (rules not yet verified)', rows: [row],
};

function clientWith(...responses: Response[]) {
  const fetchFn = vi.fn<typeof fetch>();
  for (const r of responses) fetchFn.mockResolvedValueOnce(r);
  return { client: createApiClient({ baseUrl: '/api', fetch: fetchFn }), fetchFn };
}

describe('score sheet (GET /matches/{id}/score-sheet)', () => {
  it('refuses a row with an unknown ending', async () => {
    const { client } = clientWith(json(200, { ...sheet, rows: [{ ...row, ending: 'let' }] }));
    await expect(client.getScoreSheet(ID)).rejects.toMatchObject({ code: 'invalid_response' });
  });

  it('refuses a row whose score is not a call', async () => {
    const { client } = clientWith(json(200, { ...sheet, rows: [{ ...row, score_after: '<b>1</b>' }] }));
    await expect(client.getScoreSheet(ID)).rejects.toMatchObject({ code: 'invalid_response' });
  });

  it('refuses a sheet without the unofficial flag', async () => {
    const { rules_version, label, rows } = sheet;
    const { client } = clientWith(json(200, { rules_version, label, rows }));
    await expect(client.getScoreSheet(ID)).rejects.toMatchObject({ code: 'invalid_response' });
  });

  it('reads rows, the label and the version (body, else ETag, else unknown)', async () => {
    const { client, fetchFn } = clientWith(
      json(200, { ...sheet, version: 7 }),
      json(200, sheet, { etag: 'W/"8"' }),
      json(200, sheet),
    );
    const a = await client.getScoreSheet(ID);
    expect(fetchFn.mock.calls[0]![0]).toBe(`/api/matches/${ID}/score-sheet`);
    expect(a.version).toBe(7);
    expect(a.sheet.rows[0]).toEqual(row);
    expect(a.sheet.label).toBe('unofficial scoring (rules not yet verified)');
    expect((await client.getScoreSheet(ID)).version).toBe(8);
    expect((await client.getScoreSheet(ID)).version).toBeNull();
  });

  it('reads a conflict row (needs your decision) with no score', async () => {
    const conflict = { ...row, serving_side: null, score_before: null, score_after: null, marker: 'needs_decision' };
    const { client } = clientWith(json(200, { ...sheet, rows: [conflict] }));
    expect((await client.getScoreSheet(ID)).sheet.rows[0]!.marker).toBe('needs_decision');
  });

  it('refuses a bad match id before any request', async () => {
    const { client, fetchFn } = clientWith();
    await expect(client.getScoreSheet('../x')).rejects.toMatchObject({ code: 'not_found' });
    expect(fetchFn).not.toHaveBeenCalled();
  });
});

describe('commands carry If-Match and return the new version and sheet', () => {
  it('tag: POST /matches/{id}/rallies with If-Match, returns the rally id', async () => {
    const { client, fetchFn } = clientWith(json(201, { version: 4, rally_id: RALLY, sheet }));
    const tag = { start_ms: 0, end_ms: 7999, winning_side: 'A' as const, ending: 'winner' as const, responsible_player: 'A1' as const, fault_kind: null };
    const r = await client.tagRally(ID, 3, tag);
    const [url, init] = fetchFn.mock.calls[0]!;
    expect(url).toBe(`/api/matches/${ID}/rallies`);
    expect(init?.method).toBe('POST');
    expect(new Headers(init?.headers).get('if-match')).toBe('3');
    expect(JSON.parse(init?.body as string)).toEqual(tag);
    expect(r).toEqual({ version: 4, rallyId: RALLY, sheet: { ...sheet } });
  });

  it('a 409 stale_match is an ApiError with that code (top-level or enveloped)', async () => {
    const { client } = clientWith(
      json(409, { code: 'stale_match' }),
      json(409, { error: { code: 'stale_match', support_ref: 'ref_0123456789abcdef' } }),
    );
    const tag = { start_ms: 0, end_ms: 1, winning_side: 'A' as const, ending: 'winner' as const, responsible_player: null, fault_kind: null };
    await expect(client.tagRally(ID, 1, tag)).rejects.toMatchObject({ status: 409, code: 'stale_match' });
    await expect(client.tagRally(ID, 1, tag)).rejects.toMatchObject({ code: 'stale_match', supportRef: 'ref_0123456789abcdef' });
  });

  it('a 409 match_not_ready and a 422 invalid_outcome keep their codes', async () => {
    const { client } = clientWith(json(409, { code: 'match_not_ready' }), json(422, { error: { code: 'invalid_outcome' } }));
    const tag = { start_ms: 0, end_ms: 1, winning_side: 'A' as const, ending: 'winner' as const, responsible_player: null, fault_kind: null };
    await expect(client.tagRally(ID, 0, tag)).rejects.toMatchObject({ code: 'match_not_ready' });
    await expect(client.tagRally(ID, 0, tag)).rejects.toMatchObject({ code: 'invalid_outcome' });
  });

  it('start game, correct, undo', async () => {
    const { client, fetchFn } = clientWith(
      json(201, { version: 1, sheet: { ...sheet, rows: [] } }),
      json(200, { version: 5, sheet }),
      json(200, { version: 6, sheet }),
    );
    expect((await client.startGame(ID, 0, { first_serving_side: 'A', ends_switched: false })).version).toBe(1);
    expect(fetchFn.mock.calls[0]![0]).toBe(`/api/matches/${ID}/games`);
    expect((await client.correctRally(ID, 4, RALLY, 'winning_side', 'B')).version).toBe(5);
    const [url, init] = fetchFn.mock.calls[1]!;
    expect(url).toBe(`/api/matches/${ID}/rallies/${RALLY}`);
    expect(init?.method).toBe('PATCH');
    expect(JSON.parse(init?.body as string)).toEqual({ field: 'winning_side', value: 'B' });
    expect((await client.undo(ID, 5)).version).toBe(6);
    expect(fetchFn.mock.calls[2]![0]).toBe(`/api/matches/${ID}/undo`);
    expect(new Headers(fetchFn.mock.calls[2]![1]?.headers).get('if-match')).toBe('5');
  });

  it('refuses a rally id that is not a public id', async () => {
    const { client } = clientWith();
    await expect(client.correctRally(ID, 1, 'x/../y', 'ending', 'fault')).rejects.toMatchObject({ code: 'not_found' });
  });

  it('refuses a command response without a version', async () => {
    const { client } = clientWith(json(200, { sheet }));
    await expect(client.undo(ID, 1)).rejects.toMatchObject({ code: 'invalid_response' });
  });
});

describe('correction history and rally media', () => {
  it('reads history items and refuses an unknown kind', async () => {
    const item = { id: RALLY, kind: 'correction', rally_id: RALLY, rally_number: 2, field: 'winning_side', old_value: 'B', new_value: 'A', undoes: null, at: '2026-10-05T10:00:00Z' };
    const { client } = clientWith(json(200, { items: [item] }), json(200, { items: [{ ...item, kind: 'delete' }] }));
    expect(await client.corrections(ID)).toEqual([item]);
    await expect(client.corrections(ID)).rejects.toMatchObject({ code: 'invalid_response' });
  });

  it('media: refuses a URL that is not https or same-origin path, or a TTL over 15 minutes', async () => {
    const { client } = clientWith(
      json(200, { url: 'javascript:alert(1)', expires_in_s: 600, start_ms: 0 }),
      json(200, { url: '/media/x', expires_in_s: 901, start_ms: 0 }),
      json(200, { url: 'https://localhost:3000/media/racket-media/x?X-Amz-Signature=ab', expires_in_s: 600, start_ms: 14000 }),
    );
    await expect(client.rallyMedia(ID, RALLY)).rejects.toMatchObject({ code: 'invalid_response' });
    await expect(client.rallyMedia(ID, RALLY)).rejects.toMatchObject({ code: 'invalid_response' });
    expect(await client.rallyMedia(ID, RALLY)).toEqual({
      url: 'https://localhost:3000/media/racket-media/x?X-Amz-Signature=ab', expiresInS: 600, startMs: 14000,
    });
  });
});

describe('match video for the tagging screen', () => {
  it('GET /matches/{id}/media with the same safety checks as a rally link', async () => {
    const { client, fetchFn } = clientWith(
      json(200, { url: 'data:video/mp4;base64,AAAA', expires_in_s: 600, start_ms: 0 }),
      json(200, { url: '/media/racket-media/x?sig=1', expires_in_s: 600, start_ms: 0 }),
    );
    await expect(client.matchMedia(ID)).rejects.toMatchObject({ code: 'invalid_response' });
    expect(fetchFn.mock.calls[0]![0]).toBe(`/api/matches/${ID}/media`);
    expect((await client.matchMedia(ID)).url).toBe('/media/racket-media/x?sig=1');
  });
});
