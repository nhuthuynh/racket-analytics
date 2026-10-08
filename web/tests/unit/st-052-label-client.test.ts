// ST-052 label client and response parser (api-sprint-03 §5.2-§5.4; NFR-052: the export file is
// rebuilt from `full-tag-labels/v1` fields only). The API is a recording fetch (QA-PR14-02/-03).
// Negative cases first: a body off the contract is refused, never passed on to the export file.
import { describe, expect, it, vi } from 'vitest';
import { ApiError, createApiClient } from '@/lib/api/client';
import { reconcile, sameEvent, sameOutcome } from '@/lib/label/reconcile';
import type { LabelSession } from '@/lib/label/types';

const ID = '0b8f6c1e-3f3a-4c55-9a51-8d1f0e7d2a10';
const OUTCOME = { ending: 'unforced_error', winning_side: 'A', responsible_player: 'B2', fault_kind: null };
const HIT = { type: 'hit', frame: 150, hitter: 'B1', facets: { contact: 'volley' } };
const BOUNCE = { type: 'bounce', frame: 160, visible: true, court_xy_m: [3.1, 12.4] };
const doc = (over: Record<string, unknown> = {}) => ({
  schema: 'full-tag-labels/v1', clip: `match:${ID}`, fps: 60, frame_count: 3600, players: ['A1', 'A2', 'B1', 'B2'],
  rallies: [{ id: 'r1', start_frame: 100, end_frame: 400, outcome: OUTCOME, events: [HIT, BOUNCE] }],
  ...over,
});
const sessionBody = (over: Record<string, unknown> = {}) => ({
  match_id: ID, fps: 60, frame_count: 3600, players: ['A1', 'A2', 'B1', 'B2'], version: 3, document: doc(), ...over,
});
const json = (status: number, body: unknown) =>
  new Response(JSON.stringify(body), { status, headers: { 'content-type': 'application/json' } });

function clientWith(...responses: Response[]) {
  const fetchFn = vi.fn<typeof fetch>();
  for (const r of responses) fetchFn.mockResolvedValueOnce(r);
  return { client: createApiClient({ baseUrl: '/api', fetch: fetchFn }), fetchFn };
}

describe('labelSession: GET /label/matches/{id}', () => {
  it.each([
    ['a schema other than full-tag-labels/v1', sessionBody({ document: doc({ schema: 'full-tag-labels/v2' }) })],
    ['fps of 0', sessionBody({ fps: 0 })],
    ['a negative version', sessionBody({ version: -1 })],
    ['a fractional frame', sessionBody({ document: doc({ rallies: [{ id: 'r1', start_frame: 1.5, end_frame: 4, outcome: OUTCOME, events: [] }] }) })],
    ['a nickname where a slot belongs', sessionBody({ players: ['Ivy', 'A2', 'B1', 'B2'] })],
    ['a hitter that is not a slot', sessionBody({ document: doc({ rallies: [{ id: 'r1', start_frame: 1, end_frame: 4, outcome: OUTCOME, events: [{ ...HIT, hitter: 'Carlos' }] }] }) })],
    ['an unknown ending', sessionBody({ document: doc({ rallies: [{ id: 'r1', start_frame: 1, end_frame: 4, outcome: { ...OUTCOME, ending: 'let' }, events: [] }] }) })],
    ['an unknown fault kind', sessionBody({ document: doc({ rallies: [{ id: 'r1', start_frame: 1, end_frame: 4, outcome: { ...OUTCOME, fault_kind: 'net' }, events: [] }] }) })],
    ['an unknown event type', sessionBody({ document: doc({ rallies: [{ id: 'r1', start_frame: 1, end_frame: 4, outcome: OUTCOME, events: [{ type: 'net', frame: 2 }] }] }) })],
    ['a court position with one number', sessionBody({ document: doc({ rallies: [{ id: 'r1', start_frame: 1, end_frame: 4, outcome: OUTCOME, events: [{ ...BOUNCE, frame: 2, court_xy_m: [3] }] }] }) })],
    ['a court position that is not a number', sessionBody({ document: doc({ rallies: [{ id: 'r1', start_frame: 1, end_frame: 4, outcome: OUTCOME, events: [{ ...BOUNCE, frame: 2, court_xy_m: [3, '1'] }] }] }) })],
    ['a facet value that is not text', sessionBody({ document: doc({ rallies: [{ id: 'r1', start_frame: 1, end_frame: 4, outcome: OUTCOME, events: [{ ...HIT, frame: 2, facets: { contact: 1 } }] }] }) })],
  ])('refuses %s as invalid_response', async (_why, body) => {
    const { client } = clientWith(json(200, body));
    await expect(client.labelSession(ID)).rejects.toMatchObject({ code: 'invalid_response' });
  });

  it('a non-labeller gets the not-found error, and an id that is not a UUID is never sent', async () => {
    const { client, fetchFn } = clientWith(json(404, { error: { code: 'not_found', message: 'x' } }));
    await expect(client.labelSession(ID)).rejects.toMatchObject({ status: 404, code: 'not_found' });
    await expect(client.labelSession('../me')).rejects.toBeInstanceOf(ApiError);
    expect(fetchFn).toHaveBeenCalledTimes(1);
  });

  it('keeps only the schema facets (contact, trajectory, intent, technique); others are dropped (PE-ST052-R1-05)', async () => {
    const facets = { contact: 'volley', position: 'kitchen', nickname: 'Carlos' };
    const body = sessionBody({ document: doc({ rallies: [{ id: 'r1', start_frame: 1, end_frame: 400, outcome: OUTCOME, events: [{ ...HIT, facets }] }] }) });
    const { client } = clientWith(json(200, body));
    const s = await client.labelSession(ID);
    expect(s.document.rallies[0]?.events[0]).toEqual({ type: 'hit', frame: 150, hitter: 'B1', facets: { contact: 'volley' } });
  });

  it('reads the session; unknown fields are dropped and missing optional ones are filled', async () => {
    const extra = doc({
      consent_ref: 'CR-1',
      rallies: [{
        id: 'r1', start_frame: 100, end_frame: 400, note: 'x',
        outcome: { ending: 'replay', winning_side: null },
        events: [{ type: 'hit', frame: 150, hitter: 'B1', nickname: 'Carlos' }, { type: 'bounce', frame: 160, visible: false, court_xy_m: null }],
      }],
    });
    const { client, fetchFn } = clientWith(json(200, sessionBody({ document: extra })));
    const s = await client.labelSession(ID);
    expect(fetchFn.mock.calls[0]?.[0]).toBe(`/api/label/matches/${ID}`);
    expect(s).toEqual({
      matchId: ID, fps: 60, frameCount: 3600, players: ['A1', 'A2', 'B1', 'B2'], version: 3,
      document: {
        schema: 'full-tag-labels/v1', clip: `match:${ID}`, fps: 60, frame_count: 3600, players: ['A1', 'A2', 'B1', 'B2'],
        rallies: [{
          id: 'r1', start_frame: 100, end_frame: 400,
          outcome: { ending: 'replay', winning_side: null, responsible_player: null, fault_kind: null },
          events: [{ type: 'hit', frame: 150, hitter: 'B1', facets: {} }, { type: 'bounce', frame: 160, visible: false, court_xy_m: null }],
        }],
      },
    });
  });
});

describe('labelEvent: POST /label/matches/{id}/events', () => {
  it('a refused label carries its field codes', async () => {
    const fields = [{ field: 'frame', code: 'out_of_order' }];
    const { client } = clientWith(json(422, { error: { code: 'invalid_label', message: 'This label is not valid.', fields } }));
    await expect(client.labelEvent(ID, { type: 'hit', frame: 1, hitter: 'A1', facets: {} })).rejects.toMatchObject({
      status: 422, code: 'invalid_label', fields,
    });
  });

  it('refuses a count that is not a whole number', async () => {
    const { client } = clientWith(json(201, { version: 1, rallies: 1, events: -1 }));
    await expect(client.labelEvent(ID, { type: 'hit', frame: 1, hitter: 'A1', facets: {} })).rejects.toMatchObject({ code: 'invalid_response' });
  });

  it('sends one label as JSON and reads the new version and counts', async () => {
    const { client, fetchFn } = clientWith(json(201, { version: 4, rallies: 1, events: 2, extra: true }));
    const label = { type: 'rally' as const, start_frame: 100, end_frame: 400, outcome: { ending: 'winner' as const, winning_side: 'A' as const, responsible_player: null, fault_kind: null } };
    expect(await client.labelEvent(ID, label)).toEqual({ version: 4, rallies: 1, events: 2 });
    const [url, init] = fetchFn.mock.calls[0] ?? [];
    expect(url).toBe(`/api/label/matches/${ID}/events`);
    expect(init?.method).toBe('POST');
    expect(JSON.parse(String(init?.body))).toEqual(label);
  });
});

describe('labelExport: GET /label/matches/{id}/export', () => {
  it('refuses a document that is not full-tag-labels/v1', async () => {
    const { client } = clientWith(json(200, doc({ schema: undefined })));
    await expect(client.labelExport(ID)).rejects.toMatchObject({ code: 'invalid_response' });
  });

  it('returns exactly the schema fields (no consent reference, no nicknames)', async () => {
    const { client, fetchFn } = clientWith(json(200, doc({ consent_ref: 'CR-1' })));
    const d = await client.labelExport(ID);
    expect(fetchFn.mock.calls[0]?.[0]).toBe(`/api/label/matches/${ID}/export`);
    expect(d).toEqual(doc());
    expect(JSON.stringify(d)).not.toContain('CR-1');
  });
});

describe('reconcile: what the server already holds of the rally being saved', () => {
  const session = (rallies: unknown[], version = 2): LabelSession =>
    ({ matchId: ID, fps: 60, frameCount: 3600, players: ['A1', 'A2', 'B1', 'B2'], version, document: { ...doc(), rallies } }) as LabelSession;
  const hit = { type: 'hit' as const, frame: 150, hitter: 'B1', facets: {} };
  const bounce = { type: 'bounce' as const, frame: 160, visible: true, court_xy_m: [3.1, 12.4] as [number, number] };

  it('a rally the server does not hold: nothing held, every mark still to send', () => {
    const r = reconcile(session([{ id: 'r1', start_frame: 500, end_frame: 900, outcome: OUTCOME, events: [] }]), { start: 100, end: 400 }, [hit, bounce]);
    expect(r).toMatchObject({ version: 2, held: null, rest: [hit, bounce] });
    expect(r.others.map((x) => x.id)).toEqual(['r1']);
  });

  it('a held rally: only the marks it does not hold are left, and it is not among the others', () => {
    const r = reconcile(session([{ id: 'r2', start_frame: 500, end_frame: 900, outcome: OUTCOME, events: [] }, { id: 'r1', start_frame: 100, end_frame: 400, outcome: OUTCOME, events: [hit] }]), { start: 100, end: 400 }, [hit, bounce]);
    expect(r.held?.id).toBe('r1');
    expect(r.rest).toEqual([bounce]);
    expect(r.others.map((x) => x.id)).toEqual(['r2']);
  });

  it('events and outcomes match on every field the label carries', () => {
    expect(sameEvent(hit, { ...hit, hitter: 'B2' })).toBe(false);
    expect(sameEvent(hit, { ...hit, frame: 151 })).toBe(false);
    expect(sameEvent(hit, bounce)).toBe(false);
    expect(sameEvent(bounce, { ...bounce, visible: false })).toBe(false);
    expect(sameEvent(bounce, { ...bounce, court_xy_m: null })).toBe(false);
    expect(sameEvent(bounce, { ...bounce, court_xy_m: [3.1, 12.4] })).toBe(true);
    expect(sameEvent(hit, { ...hit, facets: { contact: 'volley' } })).toBe(true);
    const o = { ending: 'fault' as const, winning_side: 'B' as const, responsible_player: 'A1', fault_kind: 'nvz' as const };
    expect(sameOutcome(o, { ...o })).toBe(true);
    expect(sameOutcome(o, { ...o, fault_kind: 'foot' })).toBe(false);
    expect(sameOutcome(o, { ...o, responsible_player: null })).toBe(false);
    expect(sameOutcome(o, { ...o, winning_side: 'A' })).toBe(false);
    expect(sameOutcome(o, { ...o, ending: 'winner' })).toBe(false);
  });
});
