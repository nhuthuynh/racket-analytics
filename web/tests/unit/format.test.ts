// sprint-00 §5 front-end TDD list: formatBytes / formatDuration
// (1. negative input rejected; 2. human units). Plus the media-facts wording that
// E2E-00-01 asserts: "Duration 1:00 · 60 fps · 1920×1080".
import { describe, expect, it } from 'vitest';
import {
  formatBytes,
  formatDuration,
  formatFps,
  formatMediaSummary,
  formatProgressBytes,
  formatResolution,
} from '@/lib/format';

describe('formatBytes', () => {
  it('rejects negative input', () => {
    expect(() => formatBytes(-1)).toThrow(RangeError);
  });

  it('rejects values that are not finite numbers', () => {
    expect(() => formatBytes(Number.NaN)).toThrow(RangeError);
    expect(() => formatBytes(Number.POSITIVE_INFINITY)).toThrow(RangeError);
  });

  it('uses human units with one decimal (SI, 1 kB = 1000 B)', () => {
    expect(formatBytes(0)).toBe('0 B');
    expect(formatBytes(999)).toBe('999 B');
    expect(formatBytes(1_500)).toBe('1.5 KB');
    expect(formatBytes(1_724_207)).toBe('1.7 MB');
    expect(formatBytes(3_000_000_000)).toBe('3.0 GB');
  });
});

describe('formatProgressBytes', () => {
  it('rejects negative input', () => {
    expect(() => formatProgressBytes(-1, 10)).toThrow(RangeError);
    expect(() => formatProgressBytes(1, -10)).toThrow(RangeError);
  });

  it('shows sent and total in the unit of the total', () => {
    expect(formatProgressBytes(1_100_000, 1_724_207)).toBe('1.1 of 1.7 MB');
    expect(formatProgressBytes(0, 1_724_207)).toBe('0.0 of 1.7 MB');
    expect(formatProgressBytes(1_900_000_000, 3_000_000_000)).toBe('1.9 of 3.0 GB');
    expect(formatProgressBytes(10, 500)).toBe('10 of 500 B');
  });

  it('never shows more sent than the total', () => {
    expect(formatProgressBytes(2_000_000, 1_724_207)).toBe('1.7 of 1.7 MB');
  });
});

describe('formatDuration', () => {
  it('rejects negative input', () => {
    expect(() => formatDuration(-1)).toThrow(RangeError);
  });

  it('rejects values that are not finite numbers', () => {
    expect(() => formatDuration(Number.NaN)).toThrow(RangeError);
  });

  it('shows m:ss under an hour', () => {
    expect(formatDuration(0)).toBe('0:00');
    expect(formatDuration(60_000)).toBe('1:00');
    expect(formatDuration(65_000)).toBe('1:05');
    expect(formatDuration(59_600)).toBe('1:00');
  });

  it('shows h:mm:ss from an hour', () => {
    expect(formatDuration(3_725_000)).toBe('1:02:05');
  });
});

describe('formatFps', () => {
  it('rejects zero and negative frame rates', () => {
    expect(() => formatFps(0)).toThrow(RangeError);
    expect(() => formatFps(-30)).toThrow(RangeError);
  });

  it('drops trailing zeros like Python {fps:g}', () => {
    expect(formatFps(60)).toBe('60 fps');
    expect(formatFps(59.94)).toBe('59.94 fps');
    expect(formatFps(29.97)).toBe('29.97 fps');
    expect(formatFps(30.0)).toBe('30 fps');
  });
});

describe('formatResolution', () => {
  it('rejects non-positive sizes', () => {
    expect(() => formatResolution(0, 1080)).toThrow(RangeError);
    expect(() => formatResolution(1920, -1)).toThrow(RangeError);
  });

  it('uses the multiplication sign', () => {
    expect(formatResolution(1920, 1080)).toBe('1920×1080');
  });
});

describe('formatMediaSummary', () => {
  it('matches the walking-skeleton wording', () => {
    expect(
      formatMediaSummary({ duration_ms: 60_000, fps: 60, width: 1920, height: 1080 }),
    ).toBe('Duration 1:00 · 60 fps · 1920×1080');
  });
});
