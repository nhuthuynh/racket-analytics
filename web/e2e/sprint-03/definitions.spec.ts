// E2E-03-03 definitions, drafts and low sample (ST-048, ST-043; FR-101, FR-102; Gherkin §7.2).
// "How is this measured?" on each shown card opens its plain-language definition from the
// dictionary; no draft entry's name appears on the page (the stack runs the shipped
// dictionary); the worked example's small samples carry "low sample" in text, never hidden.
import { expect, test } from '@playwright/test';
import { expectNoBlockingA11yViolations } from '../helpers/axe';
import { receivedMatch } from '../helpers/sprint-02';
import {
  DRAFTS, PUBLISHED, REFERENCE, SCREEN, UNOFFICIAL, definitionOf, metricCard, statsPath, tagWorkedExampleByApi,
} from '../helpers/sprint-03';

test.describe('@M0 @story-ST-043 @fr-102 Definitions and drafts', { tag: '@red-until-COACH-1' }, () => {
  test('E2E-03-03 "How is this measured?" shows the definition; drafts are not shown; low-sample text', async ({ page }, testInfo) => {
    expect(PUBLISHED.length, 'no coach-reviewed metric (COACH-1)').toBeGreaterThan(0);
    const matchId = await receivedMatch(page, 'E2E-03-03 definitions');
    await tagWorkedExampleByApi(page, matchId);
    await page.goto(statsPath(matchId));
    await expect(page.getByText(UNOFFICIAL).first()).toBeVisible();
    for (const draft of DRAFTS) await expect(page.getByRole('heading', { name: draft.name, exact: true })).toHaveCount(0);
    for (const entry of PUBLISHED) {
      const card = metricCard(page, entry.id);
      await card.getByRole('button', { name: /How is this measured\?/ }).click();
      await expect(page.getByText(definitionOf(entry.id)).first()).toBeVisible();
      if (REFERENCE[entry.id]?.A.low_sample) await expect(card).toContainText(/low sample/i);
    }
    await expectNoBlockingA11yViolations(page, testInfo, `${SCREEN.dashboard}-definitions`);
  });
});
