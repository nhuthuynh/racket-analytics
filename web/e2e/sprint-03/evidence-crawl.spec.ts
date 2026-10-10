// E2E-03-02 evidence crawl (ST-054 QA, ST-047; NFR-038 a and b; Gherkin §7.3 "Every number can
// be checked"). On the stats of the worked example, every metric card and side prints its sample
// size, and its "Show me" opens a list of at most 10 rallies whose count equals n (or 10 with
// "See all n"); the first rally's link opens a video that plays. 0 metrics without a working
// "Show me", 0 shown without n. The checks retry and are collected (e2e/helpers/evidence-crawl.ts,
// self-tested by evidence-crawl-harness.spec.ts). UI assumptions: e2e/helpers/sprint-03.ts.
import { expect, test } from '@playwright/test';
import { expectNoBlockingA11yViolations } from '../helpers/axe';
import { crawlSide, openEvidence } from '../helpers/evidence-crawl';
import { playableVideo, receivedMatch } from '../helpers/sprint-02';
import { PUBLISHED, REFERENCE, SCREEN, statsPath, tagWorkedExampleByApi } from '../helpers/sprint-03';

// playableVideo may route the media request; block the service worker so a route applies in WebKit too.
test.use({ serviceWorkers: 'block' });

test.describe('@M0 @story-ST-047 @nfr-038 Evidence crawl', () => {
  test('E2E-03-02 every metric shows n and a working "Show me"', async ({ page }, testInfo) => {
    test.setTimeout(300_000); // 14 sides, each opening one rally's video
    expect(PUBLISHED.length, 'no coach-reviewed metric to crawl (COACH-1)').toBeGreaterThan(0);
    const matchId = await receivedMatch(page, 'E2E-03-02 crawl');
    await tagWorkedExampleByApi(page, matchId);
    await playableVideo(page); // Playwright Chromium cannot decode the H.264 original (sprint-02 helper)
    const problems: string[] = [];
    for (const entry of PUBLISHED) {
      for (const side of ['A', 'B'] as const) problems.push(...(await crawlSide(page, matchId, entry.id, side)));
    }
    // E-01 open with its rallies listed, for axe.
    const first = PUBLISHED[0]!.id;
    await page.goto(statsPath(matchId));
    const list = await openEvidence(page, first, 'A');
    await expect(list.getByRole('listitem')).toHaveCount(Math.min(10, REFERENCE[first]?.A.rallies.length ?? -1));
    await expectNoBlockingA11yViolations(page, testInfo, SCREEN.evidence);
    expect(problems).toEqual([]);
  });
});
