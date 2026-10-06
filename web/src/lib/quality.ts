// Footage quality report, R1 facts (ST-019; FR-025). Pure. Each finding is a fact read from the
// file (no inference, no confidence needed) stated as its consequence, plus what is unaffected
// (FR-025 example; HAX G16). Thresholds follow the capture guide's 1080p60 advice (judgment).
import { formatFps, formatResolution } from '@/lib/format';
import type { MediaFacts } from '@/lib/api/types';

const UNAFFECTED = 'Your score and rally stats are unaffected.';
const GOOD_FPS = 50;
const GOOD_SHORT_SIDE = 1080;

export function qualityFindings(media: Pick<MediaFacts, 'fps' | 'width' | 'height' | 'vfr'>): string[] {
  const findings: string[] = [];
  if (media.fps < GOOD_FPS) {
    findings.push(
      `Recorded at ${formatFps(Math.round(media.fps))}: some later results, such as shot types, may be less accurate. ${UNAFFECTED}`,
    );
  }
  if (Math.min(media.width, media.height) < GOOD_SHORT_SIDE) {
    findings.push(
      `Recorded at ${formatResolution(media.width, media.height)}: some later results may be less accurate. ${UNAFFECTED}`,
    );
  }
  if (media.vfr) {
    findings.push(`Variable frame rate: timings in later results may be slightly less precise. ${UNAFFECTED}`);
  }
  return findings;
}
