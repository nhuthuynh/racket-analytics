// CI-FLAKE-RESUMABLE (blockers.md 2026-10-08, CI run 37715576115): E2E-01 "Return after closing
// the tab" closed the tab while the last chunk was already on its way, so the server finished the
// upload and no banner was due. The E2E now holds the first chunk that starts at or after the
// chosen point, so the tab closes with that chunk unsent. `holdsAt` decides which chunk that is.
import { describe, expect, it } from 'vitest';
import { holdsAt } from '../../e2e/helpers/upload-hold';

const MIB = 1024 * 1024;
const SIZE = 50 * MIB;

describe('holdsAt (which tus PATCH the E2E holds back)', () => {
  it('lets through a chunk that starts before the chosen point', () => {
    expect(holdsAt('0', SIZE, 30)).toBe(false);
    expect(holdsAt(String(15 * MIB - 1), SIZE, 30)).toBe(false);
  });

  it('lets through a request that has no usable Upload-Offset, so it never holds the wrong thing', () => {
    expect(holdsAt(undefined, SIZE, 30)).toBe(false);
    expect(holdsAt('', SIZE, 30)).toBe(false);
    expect(holdsAt('-5', SIZE, 30)).toBe(false);
    expect(holdsAt('12abc', SIZE, 30)).toBe(false);
  });

  it('lets through an offset at or past the end: that chunk is not part of an unfinished upload', () => {
    expect(holdsAt(String(SIZE), SIZE, 30)).toBe(false);
    expect(holdsAt(String(SIZE + 1), SIZE, 30)).toBe(false);
  });

  it('refuses a meaningless size or point instead of holding every chunk', () => {
    expect(holdsAt(String(20 * MIB), 0, 30)).toBe(false);
    expect(() => holdsAt('0', SIZE, 0)).toThrow(/between 1 and 99/);
    expect(() => holdsAt('0', SIZE, 100)).toThrow(/between 1 and 99/);
  });

  it('holds the first chunk that starts at or after the chosen point', () => {
    expect(holdsAt(String(15 * MIB), SIZE, 30)).toBe(true);
    expect(holdsAt(String(30 * MIB), SIZE, 30)).toBe(true);
    expect(holdsAt(String(SIZE - 1), SIZE, 30)).toBe(true);
  });
});
