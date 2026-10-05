// tus 1.0.0 client policy (api-sprint-00 §6, §8; AQS/STACK-06). Pure: no tus-js-client import,
// so the rules are unit-testable without a network.
import { isPublicId } from '@/lib/api/types';

/** api-sprint-00 §6: `chunkSize: 8 * 1024 * 1024`. Since Sprint 1 only the fallback when
 * GET /upload-policy cannot be read; the bounds come from the policy (api-sprint-01 §6.1). */
export const CHUNK_SIZE = 8 * 1024 * 1024;

/** Each chunk should take about this long at the measured rate (NFR-016, judgment). */
export const TARGET_CHUNK_MS = 10_000;

/**
 * The next chunk size from the last chunk's measured rate, within the policy bounds
 * (NFR-016: 5-50 MB). `ms` 0 means nothing was measured: keep the size.
 */
export function nextChunkSize(lastBytes: number, ms: number, bounds: { min: number; max: number }): number {
  const target = ms > 0 ? Math.round((lastBytes / ms) * TARGET_CHUNK_MS) : lastBytes;
  return Math.min(bounds.max, Math.max(bounds.min, target));
}

/** Why an upload stopped, in the terms the panel explains (flows U-01, U-03, U-04). */
export type UploadProblem =
  | 'network'
  | 'not_a_video'
  | 'too_large'
  | 'expired'
  | 'conflict'
  | 'quota'
  | 'rate_limited'
  | 'not_found'
  | 'server';

/** What the API's error envelope said about a failed tus request (api-sprint-00 §5). */
export interface UploadErrorDetail {
  code: string | null;
  /** RFC 3339; only on 429, null when waiting does not help (quota). */
  retryAt: string | null;
  supportRef: string | null;
}

const CODE_RE = /^[a-z][a-z_]{0,63}$/;
const RETRY_AT_RE = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})$/;
const SUPPORT_REF_RE = /^ref_[0-9a-f]{16}$/;

/** Reads `{"error": {code, retry_at, support_ref}}` from a response body; anything else is null. */
export function uploadErrorDetail(body: string | null | undefined): UploadErrorDetail {
  const detail: UploadErrorDetail = { code: null, retryAt: null, supportRef: null };
  try {
    const error = (JSON.parse(body ?? '') as { error?: Record<string, unknown> } | null)?.error;
    if (typeof error?.code === 'string' && CODE_RE.test(error.code)) detail.code = error.code;
    if (typeof error?.retry_at === 'string' && RETRY_AT_RE.test(error.retry_at)) detail.retryAt = error.retry_at;
    if (typeof error?.support_ref === 'string' && SUPPORT_REF_RE.test(error.support_ref)) {
      detail.supportRef = error.support_ref;
    }
  } catch {
    // Not JSON (a proxy page, an empty body): nothing is known beyond the status.
  }
  return detail;
}

/**
 * The problem for a final failure. A 429 at creation is either the unfinished-upload quota
 * (`upload_quota_exceeded`, `retry_at: null`) or the creation rate (`rate_limited`, `retry_at`
 * set): api-sprint-01 §6.3 checks 5 and 6 (PE-R3-03).
 */
export function uploadProblemFor(status: number, detail?: Partial<UploadErrorDetail>): UploadProblem {
  if (status === 0) return 'network';
  if (status === 415) return 'not_a_video';
  if (status === 413) return 'too_large';
  if (status === 410) return 'expired';
  if (status === 409) return 'conflict';
  if (status === 429) {
    if (detail?.code === 'rate_limited') return 'rate_limited';
    if (detail?.code !== 'upload_quota_exceeded' && detail?.retryAt) return 'rate_limited';
    return 'quota';
  }
  if (status === 404 || status === 401) return 'not_found';
  return 'server';
}

/** Back-off between retries in ms (FE choice, api-sprint-00 §6). */
export const RETRY_DELAYS = [0, 1_000, 3_000, 5_000, 10_000, 20_000];

/** tus-js-client's localStorage key prefix. */
export const TUS_STORAGE_PREFIX = 'tus::';

export function uploadEndpointFor(matchId: string): string {
  if (!isPublicId(matchId)) throw new Error('not a match ID');
  return `/api/matches/${matchId}/uploads`;
}

export interface RetryInput {
  method: string;
  /** HTTP status; 0 when the request never got a response. */
  status: number;
  online: boolean;
}

export function shouldRetryUpload({ method, status, online }: RetryInput): boolean {
  if (!online) return false;
  if (status === 0 || status >= 500 || status === 423) return true;
  // 460 checksum_mismatch: the chunk was damaged on the way and nothing was stored; tus-js-client
  // asks HEAD for the offset and sends it again (api-sprint-01 §6.5, IT-01-06).
  if (status === 460) return method.toUpperCase() === 'PATCH';
  // 409 on PATCH is an offset mismatch: retrying makes tus-js-client HEAD for the offset and
  // continue from there. 409 on creation means the match already has an upload (Sprint 0
  // allows one), so retrying cannot help.
  if (status === 409) return method.toUpperCase() !== 'POST';
  return false;
}

export interface MinimalStorage {
  readonly length: number;
  key(index: number): string | null;
  removeItem(key: string): void;
}

/** Removes stored tus upload URLs, e.g. on sign-out (ASVS 14.3.1). Returns how many. */
export function clearStoredUploads(storage: MinimalStorage | null | undefined): number {
  if (!storage) return 0;
  const keys: string[] = [];
  for (let i = 0; i < storage.length; i += 1) {
    const key = storage.key(i);
    if (key?.startsWith(TUS_STORAGE_PREFIX)) keys.push(key);
  }
  for (const key of keys) storage.removeItem(key);
  return keys.length;
}
