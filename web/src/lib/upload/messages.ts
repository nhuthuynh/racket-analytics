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
