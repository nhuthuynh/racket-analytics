// Q-10 storage-full words (ST-072b-part2; FR-160; flows-sprint-04 §7; api-sprint-04 §7). Interim
// texts W-Q03/W-Q04 of interim-wording-sprint-04 §5, pending legal review (NFR-070, P16) and the
// storage size (P8). Numbers come from the API only (PM-4 rule 2). Match-limit words: quota.ts
// (ST-072b).

/** api-sprint-04 §7 `quota` key of a 429 `storage_quota_exceeded`, in bytes. */
export interface StorageQuota {
  usedBytes: number;
  limitBytes: number;
  requestedBytes: number;
}

const GIB = 2 ** 30; // the API's GB (settings.py `GIB`)
const NO_ROOM = "This video won't fit in your storage.";
const WHAT_TO_DO = 'Delete a match you no longer need, then try again.';

const count = (v: unknown): v is number => typeof v === 'number' && Number.isSafeInteger(v) && v >= 0;

export function parseStorageQuota(raw: unknown): StorageQuota | null {
  const q = raw as { used_bytes?: unknown; limit_bytes?: unknown; requested_bytes?: unknown } | null;
  if (typeof q !== 'object' || q === null) return null;
  const { used_bytes: used, limit_bytes: limit, requested_bytes: requested } = q;
  if (!count(used) || !count(limit) || !count(requested) || limit === 0) return null;
  return { usedBytes: used, limitBytes: limit, requestedBytes: requested };
}

/** GB with one decimal and no trailing ".0"; a non-zero amount never reads as 0. */
export function formatGb(bytes: number): string {
  const tenths = Math.round((bytes / GIB) * 10);
  return String((bytes > 0 ? Math.max(tenths, 1) : 0) / 10);
}

/** 429 `storage_quota_exceeded` at upload start (W-Q03 + W-Q04; no numbers without `quota`). */
export function storageFullMessage(quota: StorageQuota | null): string {
  const used = quota ? ` You have used ${formatGb(quota.usedBytes)} of ${formatGb(quota.limitBytes)} GB.` : '';
  return `${NO_ROOM}${used} ${WHAT_TO_DO}`;
}
