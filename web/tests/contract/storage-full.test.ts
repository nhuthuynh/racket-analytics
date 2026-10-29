// @vitest-environment node
// Contract test (ST-072b-part2 IT level): the Q-10 storage refusal of api-sprint-04 §7 exactly
// as the backend sends it (live-storage-full.json, captured from the API over real Postgres and
// the object store), read by the real tus error reader the upload panel uses. Negative first:
// today's unfinished-upload quota never turns into a storage message.
import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import { storageFullMessage } from '@/lib/api/storage-quota';
import { uploadErrorDetail, uploadProblemFor } from '@/lib/upload/tus-policy';

type Captured = { status: number; body: { error: Record<string, unknown> } };
const live = JSON.parse(readFileSync(new URL('./live-storage-full.json', import.meta.url), 'utf8')) as {
  storage_quota_exceeded: Captured;
};

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
