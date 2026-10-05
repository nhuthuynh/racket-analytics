// Sprint 1 match representation, creation body and upload policy (api-sprint-01 §5, §6.1).
import { describe, expect, it, vi } from 'vitest';
import { createApiClient } from '@/lib/api/client';

const ID = '0b8f6c1e-3f3a-4c55-9a51-8d1f0e7d2a10';
const json = (status: number, body: unknown) =>
  new Response(JSON.stringify(body), { status, headers: { 'content-type': 'application/json' } });

const sprint1Match = {
  id: ID,
  title: 'Doubles · 3 Oct 2026',
  format: 'doubles',
  status: 'uploading',
  scoring_system: 'side_out',
  rules_version: 'PROVISIONAL-UNVERIFIED',
  played_on: '2026-10-03',
  participants: [
    { slot: 'A1', nickname: 'Ivy', is_me: true },
    { slot: 'B1', nickname: 'Carlos', is_me: false },
  ],
  upload: {
    state: 'receiving',
    offset: 2040109465,
    length: 3187671040,
    expires_at: '2026-10-06T09:12:44Z',
    resume_url: '/api/uploads/5d0c6c1e-3f3a-4c55-9a51-8d1f0e7d2a10',
    file_name: 'Sat doubles.mp4',
    file_last_modified_ms: 1759480000000,
    head_sha256: 'a'.repeat(64),
  },
  rejection: null,
  media: null,
  created_at: '2026-10-05T09:12:44Z',
  updated_at: '2026-10-05T09:12:44Z',
};

function clientWith(...responses: Response[]) {
  const fetchFn = vi.fn<typeof fetch>();
  for (const r of responses) fetchFn.mockResolvedValueOnce(r);
  return { client: createApiClient({ baseUrl: '/api', fetch: fetchFn }), fetchFn };
}

describe('match representation (api-sprint-01 §5.2)', () => {
  it('reads participants, the upload resume state and the rejection', async () => {
    const { client } = clientWith(json(200, sprint1Match));
    const m = await client.getMatch(ID);
    expect(m.participants).toEqual(sprint1Match.participants);
    expect(m.upload).toEqual({
      state: 'receiving',
      offset: 2040109465,
      length: 3187671040,
      expiresAt: '2026-10-06T09:12:44Z',
      resumeUrl: '/api/uploads/5d0c6c1e-3f3a-4c55-9a51-8d1f0e7d2a10',
      fileName: 'Sat doubles.mp4',
      fileLastModifiedMs: 1759480000000,
      headSha256: 'a'.repeat(64),
    });
    expect(m.rejection).toBeNull();
    expect(m.played_on).toBe('2026-10-03');
  });

  it('accepts a Sprint 0 shaped match (fields absent) with empty defaults', async () => {
    const { client } = clientWith(
      json(200, { id: ID, title: 't', format: 'singles', status: 'awaiting_upload', media: null, created_at: 'x', updated_at: 'x' }),
    );
    const m = await client.getMatch(ID);
    expect(m.participants).toEqual([]);
    expect(m.upload).toBeNull();
    expect(m.rejection).toBeNull();
  });

  it('refuses a resume URL that is not a same-origin upload path', async () => {
    const { client } = clientWith(json(200, { ...sprint1Match, upload: { ...sprint1Match.upload, resume_url: 'https://evil.example/api/uploads/x' } }));
    await expect(client.getMatch(ID)).rejects.toMatchObject({ code: 'invalid_response' });
  });

  it('reads a rejection code and refuses an unknown one', async () => {
    const { client } = clientWith(
      json(200, { ...sprint1Match, status: 'awaiting_upload', upload: null, rejection: { code: 'too_long', at: '2026-10-05T10:00:00Z' } }),
      json(200, { ...sprint1Match, upload: null, rejection: { code: 'mystery', at: 'x' } }),
    );
    expect((await client.getMatch(ID)).rejection).toEqual({ code: 'too_long', at: '2026-10-05T10:00:00Z' });
    await expect(client.getMatch(ID)).rejects.toMatchObject({ code: 'invalid_response' });
  });
});

describe('POST /matches with the setup answers (api-sprint-01 §5.1)', () => {
  it('sends format, scoring system, date and participants, and no title', async () => {
    const { client, fetchFn } = clientWith(json(201, sprint1Match));
    await client.createMatch({
      format: 'singles',
      scoring_system: 'side_out',
      played_on: '2026-10-03',
      participants: [
        { slot: 'A1', nickname: 'Ivy', is_me: true },
        { slot: 'B1', nickname: 'Carlos', is_me: false },
      ],
    });
    expect(JSON.parse(String(fetchFn.mock.calls[0]![1]?.body))).toEqual({
      format: 'singles',
      scoring_system: 'side_out',
      played_on: '2026-10-03',
      participants: [
        { slot: 'A1', nickname: 'Ivy', is_me: true },
        { slot: 'B1', nickname: 'Carlos', is_me: false },
      ],
    });
  });
});

describe('GET /upload-policy (api-sprint-01 §6.1)', () => {
  it('reads the caps and chunk bounds', async () => {
    const { client } = clientWith(
      json(200, {
        max_bytes: 10000000000,
        max_duration_ms: 9000000,
        containers: ['mp4', 'mov'],
        video_codecs: ['h264', 'hevc'],
        chunk_min_bytes: 5242880,
        chunk_max_bytes: 8388608,
        checksum_algorithms: ['sha256', 'sha1'],
        expires_after_s: 86400,
      }),
    );
    await expect(client.uploadPolicy()).resolves.toEqual({
      maxBytes: 10000000000,
      maxDurationMs: 9000000,
      chunkMinBytes: 5242880,
      chunkMaxBytes: 8388608,
      expiresAfterS: 86400,
    });
  });
});
