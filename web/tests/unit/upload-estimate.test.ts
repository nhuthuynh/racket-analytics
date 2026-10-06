// Upload time estimate (ST-017; FR-022; sprint-01 §5 front-end list; Gherkin "Time estimate
// appears only after measuring"). Pure: time is passed in.
import { describe, expect, it } from 'vitest';
import { createEstimate, estimateText, recordProgress, remainingMs } from '@/lib/upload/estimate';

describe('upload estimate', () => {
  it('1. gives no estimate before 10 s of transfer have been measured', () => {
    let e = createEstimate(0, 0);
    e = recordProgress(e, 9_999, 50_000_000);
    expect(remainingMs(e, 100_000_000)).toBeNull();
  });

  it('gives an estimate from the measured rate after 10 s', () => {
    let e = createEstimate(0, 0);
    e = recordProgress(e, 10_000, 10_000_000); // 1 MB/s
    expect(remainingMs(e, 70_000_000)).toBe(60_000);
  });

  it('2. updates the estimate as the rate changes, at most every 5 s', () => {
    let e = createEstimate(0, 0);
    e = recordProgress(e, 10_000, 10_000_000);
    const first = remainingMs(e, 70_000_000);
    e = recordProgress(e, 12_000, 30_000_000); // faster, but only 2 s later
    expect(remainingMs(e, 70_000_000)).toBe(first);
    e = recordProgress(e, 15_000, 45_000_000);
    expect(remainingMs(e, 70_000_000)).not.toBe(first);
  });

  it('restarts measuring after a pause (no time counted while offline)', () => {
    let e = createEstimate(0, 0);
    e = recordProgress(e, 10_000, 10_000_000);
    e = createEstimate(70_000, 10_000_000); // resumed at the same offset
    e = recordProgress(e, 75_000, 15_000_000);
    expect(remainingMs(e, 70_000_000)).toBeNull();
  });

  it('says the time in plain words', () => {
    expect(estimateText(12 * 60_000)).toBe('About 12 minutes left');
    expect(estimateText(60_000)).toBe('About 1 minute left');
    expect(estimateText(30_000)).toBe('Less than a minute left');
    expect(estimateText(90 * 60_000)).toBe('About 1 hour 30 minutes left');
  });
});
