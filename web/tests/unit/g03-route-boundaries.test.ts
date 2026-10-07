// G03-06 / G03-10 (E2E-03-06 "the not-found page for stats", E2E-03-05 "a player gets 404"; NFR-051):
// a route whose not-found answer must carry HTTP 404 may not sit under a loading.tsx boundary.
// With a loading boundary above it, Next streams the loading UI with 200 before the page decides,
// so notFound() renders "Page not found" under status 200 (live stack, Chrome for Testing 141:
// `page.goto('/matches/<unknown id>/stats')` → 200). The lists and match pages keep their loading
// state (C-30) through route groups, which do not change any address.
import { existsSync } from 'node:fs';
import path from 'node:path';
import { describe, expect, it } from 'vitest';

const APP = path.resolve(process.cwd(), 'src/app');

function loadingAbove(route: string): string[] {
  const found: string[] = [];
  let dir = path.join(APP, route);
  for (;;) {
    if (existsSync(path.join(dir, 'loading.tsx'))) found.push(path.relative(APP, path.join(dir, 'loading.tsx')));
    if (dir === APP) break;
    dir = path.dirname(dir);
  }
  return found;
}

describe('loading boundaries and 404 status', () => {
  it('stats (D-01), evidence (E-02) and Full Tag (L-01) have no loading boundary above them', () => {
    for (const route of ['matches/[matchId]/stats', 'matches/[matchId]/stats/[metricId]/evidence', 'label/matches/[matchId]']) {
      expect(existsSync(path.join(APP, route, 'page.tsx')), route).toBe(true);
      expect(loadingAbove(route), route).toEqual([]);
    }
  });

  it('the matches list and the match pages keep their loading state (C-30)', () => {
    for (const route of ['matches/(list)', 'matches/(list)/new', 'matches/[matchId]/(pages)', 'matches/[matchId]/(pages)/sheet', 'matches/[matchId]/(pages)/tag']) {
      expect(existsSync(path.join(APP, route, 'page.tsx')), route).toBe(true);
      expect(loadingAbove(route).length, route).toBeGreaterThan(0);
    }
  });
});
