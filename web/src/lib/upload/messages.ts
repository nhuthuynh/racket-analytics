// U-03 copy (ST-018; flows §6 U-03; Gherkin §7.5). Caps come from the upload policy, never from
// constants in copy (flows D-5).
import { formatDurationCap, formatSizeCap } from '@/lib/format';
import type { RejectionCode, UploadPolicy } from '@/lib/api/types';

export const NOT_A_VIDEO = 'This file is not a video we can read';
export const NOTHING_SAVED = 'Nothing from this file was saved.';

export function rejectionMessage(
  code: RejectionCode | 'probe_failed',
  policy: Pick<UploadPolicy, 'maxBytes' | 'maxDurationMs'>,
): string {
  switch (code) {
    case 'too_large':
      return `Videos must be ${formatSizeCap(policy.maxBytes)} or smaller`;
    case 'too_long':
      return `Videos must be ${formatDurationCap(policy.maxDurationMs)} or shorter`;
    case 'not_a_video':
    case 'unsupported_video':
    case 'probe_failed':
      return NOT_A_VIDEO;
  }
}

/**
 * 429 `rate_limited` at upload creation (api-sprint-01 §6.3 check 6; PE-R3-03, PD-R3-02). Gives
 * the retry time like A-01 does (sign-in `rateLimitMessage`). Interim copy until the designer's
 * flows §6 rate-limit state (PD-R3-05); see decision-log.
 */
export function uploadRateLimitMessage(retryAt: string | null, timeZone?: string): string {
  const at = retryAt ? new Date(retryAt) : null;
  if (!at || Number.isNaN(at.getTime())) {
    return 'You have started too many uploads in a short time. Try again in a few minutes.';
  }
  const time = new Intl.DateTimeFormat('en-GB', {
    hour: '2-digit',
    minute: '2-digit',
    hourCycle: 'h23',
    ...(timeZone ? { timeZone } : {}),
  }).format(at);
  return `You have started too many uploads in a short time. You can try again at ${time}.`;
}
