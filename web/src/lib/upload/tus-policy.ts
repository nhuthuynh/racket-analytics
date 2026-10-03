// tus 1.0.0 client policy (api-sprint-00 §6, §8; AQS/STACK-06). Pure: no tus-js-client import,
// so the rules are unit-testable without a network.
import { isPublicId } from '@/lib/api/types';
import type { UploadFailure } from './progress';

/** api-sprint-00 §6: `chunkSize: 8 * 1024 * 1024`. */
export const CHUNK_SIZE = 8 * 1024 * 1024;

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
  // 409 on PATCH is an offset mismatch: retrying makes tus-js-client HEAD for the offset and
  // continue from there. 409 on creation means the match already has an upload (Sprint 0
  // allows one), so retrying cannot help.
  if (status === 409) return method.toUpperCase() !== 'POST';
  return false;
}

export function failureFor(status: number): UploadFailure {
  if (status === 0) return 'network';
  if (status === 409) return 'conflict';
  if (status >= 400 && status < 500) return 'rejected';
  return 'unknown';
}

export interface FileIdentity {
  name: string;
  size: number;
  lastModified: number;
  type: string;
}

/**
 * Identifies "this file for this match" for resuming. Deliberately excludes the file name,
 * which may contain personal data, so browser storage holds none (api-sprint-00 §8).
 */
export function uploadFingerprint(file: FileIdentity, matchId: string): string {
  return ['ra1', matchId, file.size, file.lastModified, file.type || 'unknown'].join('-');
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
