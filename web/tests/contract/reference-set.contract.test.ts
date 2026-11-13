// @vitest-environment node
// Contract test (ST-170b; FR-170.R4, FR-170.R5; SEC-6 T6-PL-3, T6-PL-4): the reference read API
// the reference browser (ST-170c, flows-sprint-06 V-10, V-11, C-10) consumes. Pinned against the
// backend's OpenAPI operations (openapi-reference-set.json, from the FastAPI app) and real bodies
// captured on Postgres from the test reference tree (live-reference-set.json; how they were
// captured: docs/sprints/06/decisions/ST-170b.md). ST-170c's client must parse every body here;
// until it exists the agreed shape is the `isEntry` guard below (field names replace the
// flows-sprint-06 placeholders, PD-FL6-01).
// Negative first: a draft fetched by id is the 404 of an unknown id and never an entry.
import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';

type Live = { status: number; body: unknown };
const live = JSON.parse(readFileSync(new URL('./live-reference-set.json', import.meta.url), 'utf8')) as Record<
  string,
  Live
>;
const openapi = JSON.parse(readFileSync(new URL('./openapi-reference-set.json', import.meta.url), 'utf8')) as {
  paths: Record<string, Record<string, { responses: string[] }>>;
};

const CURRENT = '/reference-sets/current';
const ENTRY = '/reference-sets/{version}/entries/{entry_id}';
const DRAFT_ID = 'REF-AN09-D-BEG';
const LABELS: Record<string, string> = {
  judgment: 'coach judgment, not measured from pro matches',
  published: 'published source',
  measured: 'measured from licensed footage',
};
const FIELDS = [
  'band', 'better_direction', 'citation_id', 'definition_version', 'format', 'id', 'interval',
  'interval_method', 'k', 'level_band', 'n', 'pattern_id', 'provenance_label', 'source_type',
  'status', 'value', 'version',
];

type Entry = {
  id: string;
  pattern_id: string;
  status: 'coach-reviewed' | 'verified';
  source_type: string;
  provenance_label: string;
  citation_id: string | null;
  version: number;
  band: [number, number] | null;
  interval: [number, number] | null;
  value: number | null;
  n: number | null;
};

const isPair = (v: unknown) => v === null || (Array.isArray(v) && v.length === 2 && v.every((x) => typeof x === 'number'));

function isEntry(v: unknown): v is Entry {
  if (typeof v !== 'object' || v === null) return false;
  const e = v as Record<string, unknown>;
  return (
    JSON.stringify(Object.keys(e).sort()) === JSON.stringify(FIELDS) &&
    typeof e.id === 'string' &&
    /^AN-\d{2}$/.test(String(e.pattern_id)) &&
    (e.status === 'coach-reviewed' || e.status === 'verified') &&
    typeof e.source_type === 'string' &&
    LABELS[e.source_type] === e.provenance_label &&
    (e.citation_id === null || typeof e.citation_id === 'string') &&
    Number.isInteger(e.version) &&
    isPair(e.band) &&
    isPair(e.interval) &&
    (e.value === null || typeof e.value === 'number') &&
    (e.n === null || Number.isInteger(e.n))
  );
}

const withoutSupportRef = (body: unknown) => {
  const b = body as { error?: Record<string, unknown> };
  if (!b?.error) return body;
  const { support_ref: _ignored, ...error } = b.error;
  return { ...b, error };
};

describe('reference read API contract (negative first)', () => {
  it('a draft fetched by id is the 404 of an unknown id, never an entry', () => {
    expect(live.draft_by_id!.status).toBe(404);
    expect(withoutSupportRef(live.draft_by_id!.body)).toEqual(withoutSupportRef(live.unknown_by_id!.body));
    expect(isEntry(live.draft_by_id!.body)).toBe(false);
    expect(JSON.stringify(live.current!.body)).not.toContain(DRAFT_ID);
    // positive control: a reviewed entry of the same version is served
    expect(live.reviewed_by_id!.status).toBe(200);
  });

  it('a signed-out caller gets 401 unauthenticated', () => {
    expect(live.signed_out!.status).toBe(401);
    expect(live.signed_out!.body).toMatchObject({ error: { code: 'unauthenticated' } });
  });

  it('the OpenAPI document has the two read operations and no write operation', () => {
    expect(Object.keys(openapi.paths).sort()).toEqual([ENTRY, CURRENT].sort());
    for (const path of [CURRENT, ENTRY]) {
      expect(Object.keys(openapi.paths[path]!)).toEqual(['get']);
      expect(openapi.paths[path]!.get!.responses).toEqual(expect.arrayContaining(['200', '401', '404']));
    }
  });
});

describe('reference read API contract (live bodies)', () => {
  it('the current set lists only coach-reviewed or verified entries, each saying where it comes from', () => {
    expect(live.current!.status).toBe(200);
    const body = live.current!.body as { set: string; version: number; entries: unknown[] };
    expect(typeof body.set).toBe('string');
    expect(Number.isInteger(body.version)).toBe(true);
    expect(body.entries.length).toBeGreaterThan(0);
    for (const entry of body.entries) expect(isEntry(entry), JSON.stringify(entry)).toBe(true);
  });

  it('an entry by id is the listed entry plus its set name', () => {
    const listed = (live.current!.body as { entries: Entry[] }).entries;
    const one = live.reviewed_by_id!.body as Entry & { set: string };
    const { set, ...entry } = one;
    expect(set).toBe((live.current!.body as { set: string }).set);
    expect(isEntry(entry)).toBe(true);
    expect(listed).toContainEqual(entry);
  });
});
