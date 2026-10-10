// The span of the rally being labelled in L-01 (ST-052; PE-ST052-R1-M1). The server files a hit or
// bounce under whichever rally holds its frame (api-sprint-03 §5.2), and saved labels cannot be
// changed in Sprint 3, so every mark stays inside [start, end] of the rally being labelled: a mark
// is refused outside it, and the start or end is refused where it would leave a mark outside.
// Pure; each function says why in words, or returns null.
import type { EventLabel } from './types';

const INSIDE = 'Tag hits and bounces inside the rally.';

export function markProblem(frame: number, start: number | null, end: number | null): string | null {
  if (start === null) return 'Press Rally start first.';
  if (frame < start) return `Frame ${frame} is before Rally start (frame ${start}). ${INSIDE}`;
  if (end !== null && frame > end) return `Frame ${frame} is after Rally end (frame ${end}). ${INSIDE}`;
  return null;
}

/** `marks` are in frame order. */
export function startProblem(frame: number, marks: readonly EventLabel[]): string | null {
  const first = marks[0];
  return first && frame > first.frame ? `Rally start must be at or before the first hit or bounce (frame ${first.frame}).` : null;
}

/** `marks` are in frame order. */
export function endProblem(frame: number, marks: readonly EventLabel[]): string | null {
  const last = marks.at(-1);
  return last && frame < last.frame ? `Rally end must be at or after the last hit or bounce (frame ${last.frame}).` : null;
}
