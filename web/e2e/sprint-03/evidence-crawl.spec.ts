// E2E-03-02 evidence crawl (ST-054 QA, ST-047; NFR-038 a and b; Gherkin §7.3 "Every number can
// be checked"). On the stats of the worked example, every metric card and side prints its sample
// size, and its "Show me" opens a list of at most 10 rallies whose count equals n (or 10 with
// "See all n"); the first rally's link answers with a playable video. 0 metrics without a working
// "Show me", 0 shown without n. UI assumptions: e2e/helpers/sprint-03.ts.
import { expect, test } from '@playwright/test';
import { expectNoBlockingA11yViolations } from '../helpers/axe';
import { receivedMatch } from '../helpers/sprint-02';
import { crawlSide } from '../helpers/evidence-crawl';
import { PUBLISHED, SCREEN, tagWorkedExampleByApi } from '../helpers/sprint-03';

test.describe('@M0 @story-ST-047 @nfr-038 Evidence crawl', { tag: '@red-until-ST-047' }, () => {
  test('E2E-03-02 every metric shows n and a working "Show me"', async ({ page }, testInfo) => {
    test.setTimeout(180_000);
    expect(PUBLISHED.length, 'no coach-reviewed metric to crawl (COACH-1)').toBeGreaterThan(0);
    const matchId = await receivedMatch(page, 'E2E-03-02 crawl');
    await tagWorkedExampleByApi(page, matchId);
    const problems: string[] = [];
    for (const entry of PUBLISHED) {
      for (const side of ['A', 'B'] as const) problems.push(...(await crawlSide(page, matchId, entry.id, side)));
    }
    await expectNoBlockingA11yViolations(page, testInfo, SCREEN.evidence);
    expect(problems).toEqual([]);
  });
});
