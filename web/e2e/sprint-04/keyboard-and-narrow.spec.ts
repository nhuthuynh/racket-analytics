// E2E-04-05 keyboard-only plan journey and P-01/P-02 at 320 and 360 px (ST-065; WCAG 2.1.1,
// 2.4.3, 1.4.10; NFR-028, NFR-030; flows-sprint-04 §2-§4). Only the keyboard: P-02 answered with
// Tab, arrows and Space and sent with Enter; on P-01 Enter opens "Show me", marks a session done
// and opens "Not for me", whose Cancel has focus; Tab, Enter swap the drill and the new one has
// focus. Narrow: no sideways scrolling and 24x24 targets on P-01, the swap dialog and P-02.
import { expect, test, type Locator, type Page } from '@playwright/test';
import { expectNoBlockingA11yViolations, expectTargetsAtLeast24 } from '../helpers/axe';
import { receivedMatch } from '../helpers/sprint-02';
import { noSidewaysScroll, tagWorkedExampleByApi } from '../helpers/sprint-03';
import {
  CITED, PLAN_NEW_PATH, PLAN_PATH, SCREEN_P, SWAPPABLE, drillRow, planReadyAccount, sessionOf, tabUntil,
} from '../helpers/sprint-04';

async function tabTo(page: Page, target: Locator, name: string): Promise<void> {
  await tabUntil(
    () => page.keyboard.press('Tab'),
    () => target.evaluate((el) => el === document.activeElement),
    { target: name, max: 150 },
  );
}

test.describe('@M0 @story-ST-065 @nfr-034 Plan by keyboard and on narrow screens', () => {
  test('E2E-04-05 keyboard-only: P-02 answered and sent, then Show me, Mark done and Not for me', async ({ page }, testInfo) => {
    test.setTimeout(120_000);
    const matchId = await receivedMatch(page, 'E2E-04-05 keyboard');
    await tagWorkedExampleByApi(page, matchId);

    await page.goto(PLAN_NEW_PATH);
    await tabTo(page, page.getByLabel('How long is each session?'), 'minutes');
    await page.keyboard.type('30');
    const answer = async (first: Locator, name: string, arrows: number) => {
      await tabTo(page, first, name);
      for (let i = 0; i < arrows; i++) await page.keyboard.press('ArrowRight');
      if (arrows === 0) await page.keyboard.press('Space');
    };
    await answer(page.locator('#sessions-per-week-1'), 'sessions a week', 1);
    await expect(page.locator('#sessions-per-week-2')).toBeChecked();
    await answer(page.locator('#players-available-1'), 'players', 1);
    await expect(page.locator('#players-available-2')).toBeChecked();
    await answer(page.getByLabel('A wall'), 'A wall', 0);
    await answer(page.getByLabel('Half a court'), 'Half a court', 0);
    await answer(page.locator('#level-beginner'), 'level', 1);
    await expect(page.getByLabel('Intermediate')).toBeChecked();
    await tabTo(page, page.getByRole('button', { name: 'Make my plan' }), 'Make my plan');
    await page.keyboard.press('Enter');
    await expect(page).toHaveURL(/\/plan(\?|#|$)/);
    await expect(page.getByRole('heading', { level: 2, name: 'Your sessions' })).toBeVisible();

    const show = drillRow(page, CITED).getByRole('button', { name: /^Show me the rallies behind/ });
    await tabTo(page, show, 'Show me');
    await page.keyboard.press('Enter');
    await expect(show).toHaveAttribute('aria-expanded', 'true');
    await expect(drillRow(page, CITED).getByRole('list').first().getByRole('listitem').first()).toBeVisible();

    await tabTo(page, sessionOf(page, 2).getByRole('button', { name: 'Mark done' }), 'Mark done');
    await page.keyboard.press('Enter');
    await expect(sessionOf(page, 2).getByText('Done', { exact: true })).toBeVisible();

    await tabTo(page, drillRow(page, SWAPPABLE).getByRole('button', { name: `Not for me, ${SWAPPABLE}` }), 'Not for me');
    await page.keyboard.press('Enter');
    const dialog = page.getByRole('dialog', { name: `Swap ${SWAPPABLE}?` });
    await expect(dialog.getByRole('button', { name: 'Cancel' })).toBeFocused();
    await page.keyboard.press('Tab');
    await expect(dialog.getByRole('button', { name: 'Swap drill' })).toBeFocused();
    await page.keyboard.press('Enter');
    await expect(page.getByRole('status').filter({ hasText: /^Swapped for .+\.$/ })).toBeVisible();
    await expect(page.locator('li[id^="drill-"]:focus')).toHaveCount(1);
    await expectNoBlockingA11yViolations(page, testInfo, `${SCREEN_P.plan}-keyboard`);
  });

  for (const width of [320, 360]) {
    test(`E2E-04-05 P-01, the swap dialog and P-02 at ${width} px without sideways scrolling`, async ({ page }, testInfo) => {
      await planReadyAccount(page);
      await page.setViewportSize({ width, height: 740 });
      await page.goto(PLAN_PATH);
      await expect(page.getByRole('heading', { level: 2, name: 'Your sessions' })).toBeVisible();
      await drillRow(page, CITED).getByRole('button', { name: /^Show me the rallies behind/ }).click();
      await expect(drillRow(page, CITED).getByRole('list').first()).toBeVisible();
      await noSidewaysScroll(page);
      await expectTargetsAtLeast24(page, testInfo, `${SCREEN_P.plan}-${width}`);

      await drillRow(page, SWAPPABLE).getByRole('button', { name: `Not for me, ${SWAPPABLE}` }).click();
      await expect(page.getByRole('dialog')).toBeVisible();
      await noSidewaysScroll(page);
      await expectTargetsAtLeast24(page, testInfo, `${SCREEN_P.swap}-${width}`);
      await page.getByRole('dialog').getByRole('button', { name: 'Cancel' }).click();

      await page.goto(PLAN_NEW_PATH);
      await expect(page.getByRole('heading', { level: 1, name: 'Your practice setup' })).toBeVisible();
      await noSidewaysScroll(page);
      await expectTargetsAtLeast24(page, testInfo, `${SCREEN_P.setup}-${width}`);
    });
  }
});
