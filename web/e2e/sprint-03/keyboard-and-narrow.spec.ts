// E2E-03-06 keyboard-only stats and evidence; 320 and 360 px with no sideways scroll (ST-048,
// ST-047; NFR-030, NFR-033, NFR-034; WCAG 2.1.1, 1.4.10). Tab reaches "Show me" on the first
// card, Enter opens the evidence, Tab reaches its first rally link and Enter opens the video. The
// not-found page that stands in for stats a player may not see keeps the same 24x24 rule (NFR-028).
import { expect, test } from '@playwright/test';
import { expectNoBlockingA11yViolations, expectTargetsAtLeast24 } from '../helpers/axe';
import { signInByLink } from '../helpers/sprint-01';
import { receivedMatch } from '../helpers/sprint-02';
import { PUBLISHED, SCREEN, noSidewaysScroll, statsPath, tagWorkedExampleByApi } from '../helpers/sprint-03';

test.describe('@M0 @story-ST-048 @nfr-034 Keyboard and narrow screens', { tag: '@red-until-ST-048' }, () => {
  test('E2E-03-06 keyboard-only stats and evidence', async ({ page }, testInfo) => {
    expect(PUBLISHED.length, 'no coach-reviewed metric (COACH-1)').toBeGreaterThan(0);
    const matchId = await receivedMatch(page, 'E2E-03-06 keyboard');
    await tagWorkedExampleByApi(page, matchId);
    await page.goto(statsPath(matchId));
    await expect(page.getByRole('heading', { level: 1 })).toContainText(/stats/i);
    let reached = false;
    for (let i = 0; i < 80 && !reached; i += 1) {
      await page.keyboard.press('Tab');
      reached = await page.evaluate(() => /Show me/.test(document.activeElement?.textContent ?? ''));
    }
    expect(reached, 'Tab never reached a "Show me"').toBe(true);
    await page.keyboard.press('Enter');
    let link = false;
    for (let i = 0; i < 40 && !link; i += 1) {
      await page.keyboard.press('Tab');
      link = await page.evaluate(() => document.activeElement?.tagName === 'A' && /Rally \d+/.test(document.activeElement.textContent ?? ''));
    }
    expect(link, 'Tab never reached a rally link in the evidence').toBe(true);
    await page.keyboard.press('Enter');
    await expect(page.locator('video')).toBeVisible();
    await expectNoBlockingA11yViolations(page, testInfo, `${SCREEN.evidence}-keyboard`);
  });

  for (const width of [320, 360]) {
    test(`E2E-03-06 stats and evidence at ${width} px without sideways scrolling`, async ({ page }, testInfo) => {
      expect(PUBLISHED.length, 'no coach-reviewed metric (COACH-1)').toBeGreaterThan(0);
      const matchId = await receivedMatch(page, `E2E-03-06 ${width}`);
      await tagWorkedExampleByApi(page, matchId);
      await page.setViewportSize({ width, height: 740 });
      await page.goto(statsPath(matchId));
      await expect(page.getByRole('heading', { level: 1 })).toContainText(/stats/i); // D-01, not a not-found page
      await noSidewaysScroll(page);
      await expectTargetsAtLeast24(page, testInfo, `${SCREEN.dashboard}-${width}`);
      await page.getByRole('button', { name: /Show me/ }).first().click();
      await noSidewaysScroll(page);
      await expectTargetsAtLeast24(page, testInfo, `${SCREEN.evidence}-${width}`);
    });
  }
});

test.describe('@M0 @story-ST-048 @nfr-028 Not found instead of stats', () => {
  // Another player's stats, a deleted match's stats and a mistyped id all get the one not-found
  // page (no existence oracle, NFR-051), so it is part of the D family at narrow widths too.
  for (const width of [320, 360]) {
    test(`E2E-03-06 the not-found page for stats at ${width} px: no sideways scroll, 24x24 targets`, async ({ page }, testInfo) => {
      await signInByLink(page);
      await page.setViewportSize({ width, height: 740 });
      const answer = await page.goto(statsPath('00000000-0000-4000-8000-000000000000'));
      expect(answer?.status()).toBe(404);
      await expect(page.getByRole('heading', { level: 1 })).toHaveText('Page not found');
      await noSidewaysScroll(page);
      await expectTargetsAtLeast24(page, testInfo, `${SCREEN.dashboard}-not-found-${width}`);
    });
  }
});
