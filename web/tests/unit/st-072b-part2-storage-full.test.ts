// ST-072b-part2 Q-10 storage words (flows-sprint-04 §7; interim-wording-sprint-04 §5 W-Q03, W-Q04;
// FR-160). Negative first: a refusal without a readable `quota` still gets a safe, plain message,
// never a raw code or a made-up number. Match-limit words: ST-072b.
import { describe, expect, it } from 'vitest';
import { formatGb, parseStorageQuota, storageFullMessage } from '@/lib/api/storage-quota';

const GIB = 2 ** 30;

describe('storageFullMessage (429 storage_quota_exceeded at upload start)', () => {
  it('missing quota still shows a safe message without numbers', () => {
    const text = storageFullMessage(null);
    expect(text).toBe("This video won't fit in your storage. Delete a match you no longer need, then try again.");
    expect(text).not.toMatch(/\d/);
  });

  it('says how much is used of the limit, from the API (W-Q03, W-Q04)', () => {
    expect(storageFullMessage({ usedBytes: 18.2 * GIB, limitBytes: 20 * GIB, requestedBytes: 3 * GIB })).toBe(
      "This video won't fit in your storage. You have used 18.2 of 20 GB. Delete a match you no longer need, then try again.",
    );
  });
});

describe('parseStorageQuota', () => {
  it('refuses anything that is not three non-negative byte counts with a positive limit', () => {
    for (const raw of [
      undefined,
      null,
      'x',
      {},
      { used_bytes: 1, limit_bytes: 0, requested_bytes: 1 },
      { used_bytes: -1, limit_bytes: 10, requested_bytes: 1 },
      { used_bytes: '1', limit_bytes: 10, requested_bytes: 1 },
      { used_bytes: 1.5, limit_bytes: 10, requested_bytes: 1 },
    ]) {
      expect(parseStorageQuota(raw)).toBeNull();
    }
  });

  it('reads the api-sprint-04 §7 quota key', () => {
    expect(parseStorageQuota({ used_bytes: 60000, limit_bytes: 100000, requested_bytes: 40001 })).toEqual({
      usedBytes: 60000,
      limitBytes: 100000,
      requestedBytes: 40001,
    });
  });
});

describe('formatGb', () => {
  it('one decimal, no trailing ".0" (GB as the API counts it, 2^30 bytes)', () => {
    expect(formatGb(0)).toBe('0');
    expect(formatGb(20 * GIB)).toBe('20');
    expect(formatGb(19.54 * GIB)).toBe('19.5');
    expect(formatGb(100000)).toBe('0.1');
  });
});
