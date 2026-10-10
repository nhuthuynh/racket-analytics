// ST-052 review round 1, PE-ST052-R1-M1: a hit or bounce belongs to the rally being labelled only
// when its frame lies inside that rally's span. The server files an event under whichever rally
// holds its frame (api-sprint-03 §5.2), so a mark outside the span would land in a saved rally,
// which cannot be changed in Sprint 3. Pure rules of the rally being labelled; negative cases first.
import { describe, expect, it } from 'vitest';
import { endProblem, markProblem, startProblem } from '@/lib/label/span';

const hit = (frame: number) => ({ type: 'hit' as const, frame, hitter: 'B1', facets: {} });

describe('markProblem: a mark must lie inside the rally being labelled', () => {
  it('before Rally start is refused, naming both frames', () => {
    expect(markProblem(10, 100, null)).toBe('Frame 10 is before Rally start (frame 100). Tag hits and bounces inside the rally.');
  });

  it('after Rally end is refused, naming both frames', () => {
    expect(markProblem(161, 100, 160)).toBe('Frame 161 is after Rally end (frame 160). Tag hits and bounces inside the rally.');
  });

  it('with no Rally start it asks for one', () => {
    expect(markProblem(10, null, null)).toBe('Press Rally start first.');
  });

  it('on the start, inside, on the end, or after the start with no end yet is fine', () => {
    expect(markProblem(100, 100, 160)).toBeNull();
    expect(markProblem(130, 100, 160)).toBeNull();
    expect(markProblem(160, 100, 160)).toBeNull();
    expect(markProblem(900, 100, null)).toBeNull();
  });
});

describe('startProblem and endProblem: moving the span never leaves a mark outside it', () => {
  it('Rally start after the first mark is refused', () => {
    expect(startProblem(120, [hit(110), hit(130)])).toBe('Rally start must be at or before the first hit or bounce (frame 110).');
  });

  it('Rally end before the last mark is refused', () => {
    expect(endProblem(120, [hit(110), hit(130)])).toBe('Rally end must be at or after the last hit or bounce (frame 130).');
  });

  it('a span that still holds every mark, or no marks, is fine', () => {
    expect(startProblem(110, [hit(110), hit(130)])).toBeNull();
    expect(endProblem(130, [hit(110), hit(130)])).toBeNull();
    expect(startProblem(500, [])).toBeNull();
    expect(endProblem(0, [])).toBeNull();
  });
});
