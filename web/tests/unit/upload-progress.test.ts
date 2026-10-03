// sprint-00 §5 front-end TDD list: upload progress reducer
// (1. offset regression is ignored; 2. % never exceeds 100).
import { describe, expect, it } from 'vitest';
import {
  initialUploadProgress,
  percentOf,
  uploadProgressReducer,
  type UploadProgress,
} from '@/lib/upload/progress';

const started = (total: number): UploadProgress =>
  uploadProgressReducer(initialUploadProgress, { type: 'started', bytesTotal: total });

describe('uploadProgressReducer', () => {
  it('ignores an offset that goes backwards', () => {
    const at60 = uploadProgressReducer(started(100), {
      type: 'progressed',
      bytesSent: 60,
      bytesTotal: 100,
    });
    const regressed = uploadProgressReducer(at60, {
      type: 'progressed',
      bytesSent: 40,
      bytesTotal: 100,
    });
    expect(regressed.bytesSent).toBe(60);
    expect(percentOf(regressed)).toBe(60);
  });

  it('never reports more than 100%', () => {
    const over = uploadProgressReducer(started(100), {
      type: 'progressed',
      bytesSent: 150,
      bytesTotal: 100,
    });
    expect(over.bytesSent).toBe(100);
    expect(percentOf(over)).toBe(100);
  });

  it('ignores negative or non-finite progress', () => {
    const s = started(100);
    expect(
      uploadProgressReducer(s, { type: 'progressed', bytesSent: -5, bytesTotal: 100 }),
    ).toEqual(s);
    expect(
      uploadProgressReducer(s, { type: 'progressed', bytesSent: Number.NaN, bytesTotal: 100 }),
    ).toEqual(s);
  });

  it('ignores progress before the upload has started', () => {
    expect(
      uploadProgressReducer(initialUploadProgress, {
        type: 'progressed',
        bytesSent: 10,
        bytesTotal: 100,
      }),
    ).toEqual(initialUploadProgress);
  });

  it('rejects a start with a non-positive size', () => {
    expect(() =>
      uploadProgressReducer(initialUploadProgress, { type: 'started', bytesTotal: 0 }),
    ).toThrow(RangeError);
  });

  it('starts at 0% in the uploading phase', () => {
    const s = started(1_724_207);
    expect(s.phase).toBe('uploading');
    expect(s.bytesSent).toBe(0);
    expect(percentOf(s)).toBe(0);
  });

  it('can resume from a server offset', () => {
    const s = uploadProgressReducer(initialUploadProgress, {
      type: 'started',
      bytesTotal: 100,
      bytesSent: 64,
    });
    expect(percentOf(s)).toBe(64);
  });

  it('floors the percentage so 100% means complete', () => {
    const almost = uploadProgressReducer(started(1000), {
      type: 'progressed',
      bytesSent: 999,
      bytesTotal: 1000,
    });
    expect(percentOf(almost)).toBe(99);
  });

  it('completes at 100% of the total', () => {
    const done = uploadProgressReducer(started(100), { type: 'completed' });
    expect(done.phase).toBe('complete');
    expect(done.bytesSent).toBe(100);
    expect(percentOf(done)).toBe(100);
  });

  it('keeps the offset when the upload fails, and a failure can be retried', () => {
    const at30 = uploadProgressReducer(started(100), {
      type: 'progressed',
      bytesSent: 30,
      bytesTotal: 100,
    });
    const failed = uploadProgressReducer(at30, { type: 'failed', reason: 'network' });
    expect(failed.phase).toBe('failed');
    expect(failed.bytesSent).toBe(30);
    expect(failed.failure).toBe('network');
    const retried = uploadProgressReducer(failed, { type: 'retried' });
    expect(retried.phase).toBe('uploading');
    expect(retried.failure).toBeNull();
  });

  it('ignores progress after completion', () => {
    const done = uploadProgressReducer(started(100), { type: 'completed' });
    expect(
      uploadProgressReducer(done, { type: 'progressed', bytesSent: 10, bytesTotal: 100 }),
    ).toEqual(done);
  });

  it('reports 0% when nothing has started', () => {
    expect(percentOf(initialUploadProgress)).toBe(0);
  });
});
