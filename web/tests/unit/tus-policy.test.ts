// tus 1.0.0 client policy (ST-010 with ST-008; AQS/STACK-06; api-sprint-00 §6, §8).
import { describe, expect, it } from 'vitest';
import {
  CHUNK_SIZE,
  clearStoredUploads,
  shouldRetryUpload,
  uploadEndpointFor,
  uploadErrorDetail,
  uploadProblemFor,
} from '@/lib/upload/tus-policy';

const MATCH_ID = '0b8f6c1e-3f3a-4c55-9a51-8d1f0e7d2a10';

describe('shouldRetryUpload', () => {
  it('does not retry creation when the match already has an upload (409 on POST)', () => {
    expect(shouldRetryUpload({ method: 'POST', status: 409, online: true })).toBe(false);
  });

  it('does not retry client errors such as 404 (not yours), 413 or 415', () => {
    for (const status of [400, 401, 403, 404, 412, 413, 415, 422]) {
      expect(shouldRetryUpload({ method: 'PATCH', status, online: true })).toBe(false);
    }
  });

  it('does not retry while the device is offline', () => {
    expect(shouldRetryUpload({ method: 'PATCH', status: 0, online: false })).toBe(false);
  });

  it('retries an offset mismatch on PATCH (tus-js-client asks HEAD for the offset first)', () => {
    expect(shouldRetryUpload({ method: 'PATCH', status: 409, online: true })).toBe(true);
  });

  it('retries a dropped connection, a lock and server errors', () => {
    expect(shouldRetryUpload({ method: 'PATCH', status: 0, online: true })).toBe(true);
    expect(shouldRetryUpload({ method: 'PATCH', status: 423, online: true })).toBe(true);
    expect(shouldRetryUpload({ method: 'HEAD', status: 503, online: true })).toBe(true);
  });
});

describe('uploadEndpointFor', () => {
  it('refuses an ID that is not a UUID', () => {
    expect(() => uploadEndpointFor('../../dev/sign-in')).toThrow();
  });

  it('builds the same-origin creation URL', () => {
    expect(uploadEndpointFor(MATCH_ID)).toBe(`/api/matches/${MATCH_ID}/uploads`);
  });
});

describe('chunk size', () => {
  it('is 8 MiB per the contract', () => {
    expect(CHUNK_SIZE).toBe(8 * 1024 * 1024);
  });
});

describe('clearStoredUploads', () => {
  it('removes only tus entries from storage (sign-out, ASVS 14.3.1)', () => {
    const store = new Map<string, string>([
      ['tus::fp-1::1', '{}'],
      ['tus::fp-2::2', '{}'],
      ['theme', 'dark'],
    ]);
    const storage = {
      get length() {
        return store.size;
      },
      key: (i: number) => [...store.keys()][i] ?? null,
      removeItem: (k: string) => void store.delete(k),
    };
    expect(clearStoredUploads(storage)).toBe(2);
    expect([...store.keys()]).toEqual(['theme']);
  });

  it('does not throw when storage is unavailable', () => {
    expect(clearStoredUploads(null)).toBe(0);
  });
});

// PE-R3-03 / PD-R3-02: a 429 is told apart by its error code (api-sprint-01 §6.3 checks 5 and 6).
describe('uploadProblemFor 429', () => {
  it('does not call a creation-rate limit a quota refusal', () => {
    expect(uploadProblemFor(429, { code: 'rate_limited', retryAt: '2026-10-05T14:32:00Z' })).toBe('rate_limited');
  });

  it('treats a 429 with a retry time as a rate limit even without a known code', () => {
    expect(uploadProblemFor(429, { code: null, retryAt: '2026-10-05T14:32:00Z' })).toBe('rate_limited');
  });

  it('keeps the unfinished-upload quota for upload_quota_exceeded and for a bare 429', () => {
    expect(uploadProblemFor(429, { code: 'upload_quota_exceeded', retryAt: null })).toBe('quota');
    expect(uploadProblemFor(429)).toBe('quota');
  });
});

describe('uploadErrorDetail', () => {
  it('ignores a body that is not the error envelope, and a malformed retry time', () => {
    expect(uploadErrorDetail('<html>proxy</html>')).toEqual({ code: null, retryAt: null, supportRef: null });
    expect(uploadErrorDetail(JSON.stringify({ error: { code: 7, retry_at: 'soon', support_ref: 'x' } }))).toEqual({
      code: null,
      retryAt: null,
      supportRef: null,
    });
  });

  it('reads the code, retry time and reference of the API error envelope', () => {
    const body = JSON.stringify({
      error: { code: 'rate_limited', retry_at: '2026-10-05T14:32:00Z', support_ref: 'ref_0123456789abcdef' },
    });
    expect(uploadErrorDetail(body)).toEqual({
      code: 'rate_limited',
      retryAt: '2026-10-05T14:32:00Z',
      supportRef: 'ref_0123456789abcdef',
    });
  });
});
