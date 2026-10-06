// Caps in human units (ST-016 Q-06 hint, ST-018 U-03 messages; flows D-5: from config, never
// hard-coded in copy).
import { describe, expect, it } from 'vitest';
import { formatSizeCap, formatDurationCap } from '@/lib/format';

describe('formatSizeCap', () => {
  it('uses whole SI gigabytes, the phone convention', () => {
    expect(formatSizeCap(10_000_000_000)).toBe('10 GB');
    expect(formatSizeCap(2_500_000_000)).toBe('2.5 GB');
    expect(formatSizeCap(500_000_000)).toBe('500 MB');
  });
  it('refuses nonsense', () => {
    expect(() => formatSizeCap(0)).toThrow(RangeError);
  });
});

describe('formatDurationCap', () => {
  it('says hours and minutes in words', () => {
    expect(formatDurationCap(9_000_000)).toBe('2 hours 30 minutes');
    expect(formatDurationCap(3_600_000)).toBe('1 hour');
    expect(formatDurationCap(5_400_000)).toBe('1 hour 30 minutes');
    expect(formatDurationCap(60_000)).toBe('1 minute');
  });
});
