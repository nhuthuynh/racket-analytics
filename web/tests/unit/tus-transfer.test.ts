// tus 1.0.0 transfer for Sprint 1 (ST-017; api-sprint-01 §6.3-§6.5; AQS/STACK-06): creation
// metadata, checksum on every PATCH, resume from the server's URL, adaptive chunk size, pause.
// tus-js-client is replaced by a recording fake; the protocol runs for real in E2E-01-02.
import { beforeEach, describe, expect, it, vi } from 'vitest';

type Options = Record<string, any>; // eslint-disable-line @typescript-eslint/no-explicit-any

const created: { options: Options; start: ReturnType<typeof vi.fn>; abort: ReturnType<typeof vi.fn> }[] = [];
const innerRequests: { method: string; headers: Record<string, string>; sent: unknown }[] = [];

vi.mock('tus-js-client', () => ({
  Upload: class {
    options: Options;
    start = vi.fn();
    abort = vi.fn(() => Promise.resolve());
    constructor(_file: unknown, options: Options) {
      this.options = options;
      created.push(this);
    }
  },
  DefaultHttpStack: class {
    createRequest(method: string) {
      const record = { method, headers: {} as Record<string, string>, sent: undefined as unknown };
      innerRequests.push(record);
      return {
        getMethod: () => method,
        setHeader: (k: string, v: string) => {
          record.headers[k] = v;
        },
        send: async (body: unknown) => {
          record.sent = body;
          return { getStatus: () => 204 };
        },
      };
    }
    getName() {
      return 'fake';
    }
  },
}));

const { startTransfer } = await import('@/lib/upload/transfer');

const MATCH_ID = '0b8f6c1e-3f3a-4c55-9a51-8d1f0e7d2a10';
const RESUME = '/api/uploads/5d0c6c1e-3f3a-4c55-9a51-8d1f0e7d2a10';
const POLICY = { chunkMinBytes: 5 * 1024 * 1024, chunkMaxBytes: 50 * 1024 * 1024 };
const file = new File([new Uint8Array(10).fill(1)], 'Sat doubles.mp4', { type: 'video/mp4', lastModified: 1759480000000 });
const callbacks = () => ({ onProgress: vi.fn(), onSuccess: vi.fn(), onError: vi.fn(), onRetrying: vi.fn() });
const flush = async () => {
  for (let i = 0; i < 5; i += 1) await new Promise((r) => setTimeout(r, 0));
};

beforeEach(() => {
  created.length = 0;
  innerRequests.length = 0;
});

describe('startTransfer', () => {
  it('refuses a match ID that is not a UUID and a resume URL that is not an upload path', () => {
    expect(() => startTransfer({ file, matchId: '../x', policy: POLICY, callbacks: callbacks() })).toThrow();
    expect(() => startTransfer({ file, resumeUrl: 'https://evil.example/u', policy: POLICY, callbacks: callbacks() })).toThrow();
  });

  it('creates with the contract metadata, the minimum chunk and no URL kept on the device', async () => {
    startTransfer({ file, matchId: MATCH_ID, policy: POLICY, callbacks: callbacks() });
    await flush();
    const { options, start } = created[0]!;
    expect(options.endpoint).toBe(`/api/matches/${MATCH_ID}/uploads`);
    expect(options.metadata).toEqual({
      filename: 'Sat doubles.mp4',
      last_modified: '1759480000000',
      head_sha256: expect.stringMatching(/^[0-9a-f]{64}$/),
    });
    expect(options.chunkSize).toBe(POLICY.chunkMinBytes);
    expect(options.storeFingerprintForResuming).toBe(false);
    expect(start).toHaveBeenCalledOnce();
  });

  it('resumes from the server URL without an endpoint, so an expired upload is never silently recreated', async () => {
    startTransfer({ file, resumeUrl: RESUME, policy: POLICY, callbacks: callbacks() });
    await flush();
    expect(created[0]!.options.uploadUrl).toBe(RESUME);
    expect(created[0]!.options.endpoint).toBeUndefined();
  });

  it('sends a sha256 Upload-Checksum with every PATCH body, and none on other requests', async () => {
    startTransfer({ file, matchId: MATCH_ID, policy: POLICY, callbacks: callbacks() });
    await flush();
    const stack = created[0]!.options.httpStack;
    const patch = stack.createRequest('PATCH', RESUME);
    await patch.send(new Blob(['abc']));
    const head = stack.createRequest('HEAD', RESUME);
    await head.send(null);
    expect(innerRequests[0]!.headers['Upload-Checksum']).toBe('sha256 ungWv48Bz+pBQUDeXa4iI7ADYaOWF3qctBD/YfIAFa0=');
    expect(innerRequests[1]!.headers['Upload-Checksum']).toBeUndefined();
  });

  it('adapts the chunk size to the measured rate within the policy bounds', async () => {
    const now = vi.spyOn(performance, 'now');
    startTransfer({ file, matchId: MATCH_ID, policy: POLICY, callbacks: callbacks() });
    await flush();
    const { options } = created[0]!;
    now.mockReturnValue(1_000);
    await options.onBeforeRequest({ getMethod: () => 'PATCH' });
    now.mockReturnValue(3_500); // 5 MiB in 2.5 s → ~2 MiB/s → ~20 MiB per 10 s
    options.onChunkComplete(POLICY.chunkMinBytes, POLICY.chunkMinBytes, 100 * 1024 * 1024);
    expect(options.chunkSize).toBe(20 * 1024 * 1024);
  });

  it('tells the panel about a retry (damaged chunk) and maps the final failure status', async () => {
    const cb = callbacks();
    startTransfer({ file, matchId: MATCH_ID, policy: POLICY, callbacks: cb });
    await flush();
    const { options } = created[0]!;
    const err = (status: number) => ({ originalRequest: { getMethod: () => 'PATCH' }, originalResponse: { getStatus: () => status } });
    expect(options.onShouldRetry(err(460))).toBe(true);
    expect(cb.onRetrying).toHaveBeenCalledWith(460);
    options.onError(err(415));
    expect(cb.onError).toHaveBeenCalledWith(415);
  });

  it('PE-R3-03: passes the error code and retry time of a refused creation to the panel', async () => {
    const cb = callbacks();
    startTransfer({ file, matchId: MATCH_ID, policy: POLICY, callbacks: cb });
    await flush();
    const { options } = created[0]!;
    const body = JSON.stringify({ error: { code: 'rate_limited', retry_at: '2026-10-05T14:32:00Z', support_ref: null } });
    options.onError({
      originalRequest: { getMethod: () => 'POST' },
      originalResponse: { getStatus: () => 429, getBody: () => body },
    });
    expect(cb.onError).toHaveBeenCalledWith(429, { code: 'rate_limited', retryAt: '2026-10-05T14:32:00Z', supportRef: null });
  });

  it('PD-R3-03: tells the panel when the server accepted a chunk, apart from bytes merely sent', async () => {
    const cb = { ...callbacks(), onChunkAccepted: vi.fn() };
    startTransfer({ file, matchId: MATCH_ID, policy: POLICY, callbacks: cb });
    await flush();
    const { options } = created[0]!;
    options.onChunkComplete(5, 5, 10);
    expect(cb.onChunkAccepted).toHaveBeenCalledWith(5);
  });

  it('pauses without terminating and resumes from the server offset', async () => {
    const handle = startTransfer({ file, matchId: MATCH_ID, policy: POLICY, callbacks: callbacks() });
    await flush();
    const upload = created[0]!;
    handle.pause();
    expect(upload.abort).toHaveBeenCalledWith(false);
    handle.resume();
    expect(upload.start).toHaveBeenCalledTimes(2);
  });
});
