// The tus-js-client wiring (api-sprint-00 §6, §8). tus-js-client is replaced by a recording
// fake; the real protocol exchange is covered by the walking-skeleton E2E.
import { beforeEach, describe, expect, it, vi } from 'vitest';

type Options = Record<string, any>; // eslint-disable-line @typescript-eslint/no-explicit-any

const created: { options: Options; start: ReturnType<typeof vi.fn>; abort: ReturnType<typeof vi.fn>; resumed: unknown }[] = [];
let previousUploads: { creationTime: string; uploadUrl: string }[] = [];

vi.mock('tus-js-client', () => ({
  Upload: class {
    options: Options;
    start = vi.fn();
    abort = vi.fn(() => Promise.resolve());
    resumed: unknown = null;
    constructor(_file: unknown, options: Options) {
      this.options = options;
      created.push(this);
    }
    findPreviousUploads() {
      return Promise.resolve(previousUploads);
    }
    resumeFromPreviousUpload(p: unknown) {
      this.resumed = p;
    }
  },
}));

const { startTusUpload } = await import('@/lib/upload/tus-upload');

const MATCH_ID = '0b8f6c1e-3f3a-4c55-9a51-8d1f0e7d2a10';
const file = new File([new Uint8Array(10)], 'ivy-final.mp4', { type: 'video/mp4', lastModified: 5 });
const callbacks = () => ({ onProgress: vi.fn(), onSuccess: vi.fn(), onError: vi.fn() });
const flush = () => new Promise((r) => setTimeout(r, 0));

beforeEach(() => {
  created.length = 0;
  previousUploads = [];
});

describe('startTusUpload', () => {
  it('refuses a match ID that is not a UUID before loading anything', () => {
    expect(() => startTusUpload(file, '../me', callbacks())).toThrow();
    expect(created).toHaveLength(0);
  });

  it('does not start when aborted before tus-js-client has loaded', async () => {
    const handle = startTusUpload(file, MATCH_ID, callbacks());
    handle.abort();
    await flush();
    expect(created).toHaveLength(0);
  });

  it('sends no metadata (no file name) and uses the contract endpoint and chunk size', async () => {
    startTusUpload(file, MATCH_ID, callbacks());
    await flush();
    const { options, start } = created[0]!;
    expect(options.endpoint).toBe(`/api/matches/${MATCH_ID}/uploads`);
    expect(options.chunkSize).toBe(8 * 1024 * 1024);
    expect(options.metadata).toEqual({});
    expect(await options.fingerprint()).not.toContain('ivy');
    expect(options.removeFingerprintOnSuccess).toBe(true);
    expect(start).toHaveBeenCalledOnce();
  });

  it('resumes the most recent stored upload for the same file and match', async () => {
    previousUploads = [
      { creationTime: '2026-10-05T09:00:00Z', uploadUrl: '/api/uploads/old' },
      { creationTime: '2026-10-05T10:00:00Z', uploadUrl: '/api/uploads/new' },
    ];
    startTusUpload(file, MATCH_ID, callbacks());
    await flush();
    expect(created[0]!.resumed).toMatchObject({ uploadUrl: '/api/uploads/new' });
  });

  it('reports progress, success, and the HTTP status of a failure', async () => {
    const cb = callbacks();
    startTusUpload(file, MATCH_ID, cb);
    await flush();
    const { options } = created[0]!;
    options.onProgress(5, 10);
    options.onSuccess();
    options.onError({ originalResponse: { getStatus: () => 409 } });
    options.onError(new Error('offline'));
    expect(cb.onProgress).toHaveBeenCalledWith(5, 10);
    expect(cb.onSuccess).toHaveBeenCalledOnce();
    expect(cb.onError).toHaveBeenNthCalledWith(1, 409);
    expect(cb.onError).toHaveBeenNthCalledWith(2, 0);
  });

  it('does not retry a 409 on creation but does on PATCH', async () => {
    startTusUpload(file, MATCH_ID, callbacks());
    await flush();
    const { options } = created[0]!;
    const err = (method: string, status: number) => ({
      originalRequest: { getMethod: () => method },
      originalResponse: { getStatus: () => status },
    });
    expect(options.onShouldRetry(err('POST', 409))).toBe(false);
    expect(options.onShouldRetry(err('PATCH', 409))).toBe(true);
  });

  it('retry restarts the same upload; abort stops it', async () => {
    const handle = startTusUpload(file, MATCH_ID, callbacks());
    await flush();
    handle.retry();
    expect(created[0]!.start).toHaveBeenCalledTimes(2);
    handle.abort();
    expect(created[0]!.abort).toHaveBeenCalledOnce();
  });
});
