// Sprint 1 tus client rules (ST-017, ST-018; api-sprint-01 §6; NFR-016).
import { describe, expect, it } from 'vitest';
import { nextChunkSize, shouldRetryUpload, uploadProblemFor } from '@/lib/upload/tus-policy';

const LIMITS = { min: 5 * 1024 * 1024, max: 50 * 1024 * 1024 };

describe('nextChunkSize (NFR-016: 5-50 MB, adapts to the measured rate)', () => {
  it('never leaves the policy bounds', () => {
    expect(nextChunkSize(LIMITS.max, 1, LIMITS)).toBe(LIMITS.max);
    expect(nextChunkSize(LIMITS.min, 600_000, LIMITS)).toBe(LIMITS.min);
  });

  it('aims for about 10 s per chunk', () => {
    // 2 MB/s measured → 20 MB
    expect(nextChunkSize(8_000_000, 4_000, LIMITS)).toBe(20_000_000);
  });

  it('keeps the size when nothing was measured', () => {
    expect(nextChunkSize(8_000_000, 0, LIMITS)).toBe(8_000_000);
  });
});

describe('shouldRetryUpload, Sprint 1 statuses', () => {
  it('re-sends a damaged chunk (460 checksum_mismatch) from the server offset', () => {
    expect(shouldRetryUpload({ method: 'PATCH', status: 460, online: true })).toBe(true);
  });
  it('does not retry an expired upload, a refused file or a size refusal', () => {
    for (const status of [410, 415, 413]) {
      expect(shouldRetryUpload({ method: 'PATCH', status, online: true })).toBe(false);
    }
  });
});

describe('uploadProblemFor', () => {
  it('maps refusals to the U-03 reasons', () => {
    expect(uploadProblemFor(415)).toBe('not_a_video');
    expect(uploadProblemFor(413)).toBe('too_large');
    expect(uploadProblemFor(410)).toBe('expired');
    expect(uploadProblemFor(409)).toBe('conflict');
    expect(uploadProblemFor(429)).toBe('quota');
    expect(uploadProblemFor(404)).toBe('not_found');
    expect(uploadProblemFor(0)).toBe('network');
    expect(uploadProblemFor(503)).toBe('server');
  });
});
