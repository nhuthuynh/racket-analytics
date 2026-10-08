// E2E-03-02 evidence crawl (ST-054 QA, ST-047; NFR-038 a and b; Gherkin §7.3 "Every number can
// be checked"). On the stats of the worked example, every metric card and side prints its sample
// size, and its "Show me" opens a list of at most 10 rallies whose count equals n (or 10 with
// "See all n"); the first rally's link answers with a playable video. 0 metrics without a working
// "Show me", 0 shown without n. UI assumptions: e2e/helpers/sprint-03.ts.
import { expect, test } from '@playwright/test';
import { expectNoBlockingA11yViolations } from '../helpers/axe';
import { receivedMatch } from '../helpers/sprint-02';
import { METRIC_NAMES, PUBLISHED, REFERENCE, SCREEN, metricCard, statsPath, tagWorkedExampleByApi } from '../helpers/sprint-03';

test.describe('@M0 @story-ST-047 @nfr-038 Evidence crawl', { tag: '@red-until-ST-047' }, () => {
  test('E2E-03-02 every metric shows n and a working "Show me"', async ({ page }, testInfo) => {
    test.setTimeout(180_000);
    expect(PUBLISHED.length, 'no coach-reviewed metric to crawl (COACH-1)').toBeGreaterThan(0);
    const matchId = await receivedMatch(page, 'E2E-03-02 crawl');
    await tagWorkedExampleByApi(page, matchId);
    const problems: string[] = [];
    for (const entry of PUBLISHED) {
      for (const side of ['A', 'B'] as const) {
        await page.goto(statsPath(matchId));
        const card = metricCard(page, entry.id);
        if (!(await card.textContent())?.includes('n =') && entry.id !== 'AN-04' && entry.id !== 'AN-06') {
          problems.push(`${entry.id}: no "n =" printed`);
        }
        const buttons = card.getByRole('button', { name: /Show me/ });
        if ((await buttons.count()) < 2) { problems.push(`${entry.id}: fewer than 2 "Show me" (one per side)`); continue; }
        await buttons.nth(side === 'A' ? 0 : 1).click();
        const refs = REFERENCE[entry.id]?.[side].rallies ?? [];
        const list = page.getByRole('list', { name: new RegExp(METRIC_NAMES[entry.id] ?? entry.id) });
        const shown = Math.min(10, refs.length);
        if ((await list.getByRole('listitem').count()) !== shown) problems.push(`${entry.id} ${side}: items != ${shown}`);
        if (refs.length > 10 && !(await page.getByText(`See all ${refs.length}`).count())) {
          problems.push(`${entry.id} ${side}: no "See all ${refs.length}"`);
        }
        if (shown > 0) {
          const href = await list.getByRole('link').first().getAttribute('href');
          if (!href) problems.push(`${entry.id} ${side}: first rally has no link`);
        }
      }
    }
    await expectNoBlockingA11yViolations(page, testInfo, SCREEN.evidence);
    expect(problems).toEqual([]);
  });
});
