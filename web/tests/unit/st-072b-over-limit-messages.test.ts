// ST-072b Q-10 over-limit words (flows-sprint-04 §7; interim-wording-sprint-04 §5 W-Q01..W-Q04;
// FR-160). Negative first: a refusal without `retry_at` or without `quota` still gets a safe,
// plain message, never a raw code or a made-up number.
import { describe, expect, it } from 'vitest';
import { formatGb, matchLimitMessage, parseStorageQuota, storageFullMessage } from '@/lib/api/quota';

const GIB = 2 ** 30;
const NOW = new Date('2026-10-29T13:10:00Z');

describe('matchLimitMessage (429 rate_limited at POST /matches)', () => {
  it('missing retry_at still shows a safe message (W-Q02), answers kept', () => {
    expect(matchLimitMessage(null, { timeZone: 'UTC', now: NOW })).toBe(
      'You have started a lot of matches in the last hour. You can start a new match within the hour. Your answers are kept.',
    );
  });

  it('an unreadable retry_at is treated as missing', () => {
    expect(matchLimitMessage('not a time', { timeZone: 'UTC', now: NOW })).toMatch(/within the hour\./);
  });

  it('gives the local 24-hour time when the player can start a new match (W-Q01)', () => {
    expect(matchLimitMessage('2026-10-29T14:05:00Z', { timeZone: 'UTC', now: NOW })).toBe(
      'You have started a lot of matches in the last hour. You can start a new match at 14:05. Your answers are kept.',
    );
    expect(matchLimitMessage('2026-10-29T14:05:00Z', { timeZone: 'Australia/Sydney', now: NOW })).toMatch(
      /start a new match at 01:05\./,
    );
  });

  it('says "tomorrow at" when the local date of the time differs from today', () => {
    const late = new Date('2026-10-29T23:30:00Z');
    expect(matchLimitMessage('2026-10-30T00:10:00Z', { timeZone: 'UTC', now: late })).toMatch(
      /You can start a new match tomorrow at 00:10\./,
    );
  });
});

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
