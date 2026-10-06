// Upload time estimate (ST-017; FR-022; flows U-01). Pure: callers pass the time.
// Shown only after 10 s of measured transfer, and changed at most every 5 s (judgment, flows),
// so the number does not flicker. A pause restarts the measurement (createEstimate again).
import { formatDurationCap } from '@/lib/format';

export const MEASURE_BEFORE_MS = 10_000;
export const UPDATE_EVERY_MS = 5_000;

export interface Estimate {
  readonly startedAt: number;
  readonly startBytes: number;
  readonly shownAt: number | null;
  readonly shownBytes: number;
  /** bytes per ms at the last update */
  readonly shownRate: number | null;
}

export function createEstimate(now: number, bytes: number): Estimate {
  return { startedAt: now, startBytes: bytes, shownAt: null, shownBytes: bytes, shownRate: null };
}

export function recordProgress(e: Estimate, now: number, bytes: number): Estimate {
  const elapsed = now - e.startedAt;
  if (elapsed < MEASURE_BEFORE_MS) return e;
  if (e.shownAt !== null && now - e.shownAt < UPDATE_EVERY_MS) return e;
  const rate = (bytes - e.startBytes) / elapsed;
  return { ...e, shownAt: now, shownBytes: bytes, shownRate: rate > 0 ? rate : null };
}

/** Milliseconds left at the last measured rate, or null while still measuring. */
export function remainingMs(e: Estimate, totalBytes: number): number | null {
  if (e.shownRate === null) return null;
  return Math.max(0, Math.round((totalBytes - e.shownBytes) / e.shownRate));
}

export function estimateText(ms: number): string {
  if (ms < 60_000) return 'Less than a minute left';
  return `About ${formatDurationCap(ms)} left`;
}
