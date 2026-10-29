// ST-072b Q-10 match-limit words (flows-sprint-04 §7; interim-wording-sprint-04 §5 W-Q01, W-Q02;
// FR-160). Negative first: a refusal without a readable `retry_at` still gets a safe, plain
// message, never a raw code or a made-up time. Storage words: ST-072b-part2.
import { describe, expect, it } from 'vitest';
import { matchLimitMessage } from '@/lib/api/quota';

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
