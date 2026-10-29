// E2E-04-06 (ST-068b; FR-003; flows-sprint-04 §5 A-10/A-11 and the footage notice; api-sprint-04
// §10): runs only in the `flags-on` project (PW_PROJECTS=flags-on) against a stack started with
// FEATURE_AGE_GATE=1, nightly and by the verifier (G04-07). Negative first: the under-18 path.
import { expect, test, type Page } from '@playwright/test';
import { expectNoBlockingA11yViolations, expectTargetsAtLeast24 } from '../../helpers/axe';
import { latestSignInLink, requestLink, uniqueEmail } from '../../helpers/sprint-01';

const NOTICE = "Don't upload matches with anyone under 18. Film only people who agree to be filmed.";

/** A new address signs in with a link and lands on A-10 (no account yet). */
async function newAddressSignsIn(page: Page): Promise<void> {
  const email = uniqueEmail('age');
  await requestLink(page, email);
  const link = new URL(await latestSignInLink(email));
  await page.goto(`${link.pathname}${link.hash}`);
  await expect(page).toHaveURL(/\/welcome\/age$/, { timeout: 15_000 });
  await expect(page.getByRole('heading', { level: 1, name: 'Are you 18 or over?' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Continue' })).toBeEnabled(); // hydrated
}

test.describe('E2E-04-06 The age question after sign-in (flag on)', () => {
  test('Under-age applicant: keyboard only, at 320 px, no account and no way back in', async ({ page }, testInfo) => {
    await page.setViewportSize({ width: 320, height: 640 });
    await newAddressSignsIn(page);
    await expectNoBlockingA11yViolations(page, testInfo, 'A-10');
    await expectTargetsAtLeast24(page, testInfo, 'A-10');
    await page.getByRole('radio', { name: 'Yes, I am 18 or over' }).focus();
    await page.keyboard.press('ArrowDown'); // radio group: arrow keys move the choice
    await expect(page.getByRole('radio', { name: 'No, I am under 18' })).toBeChecked();
    await page.keyboard.press('Enter'); // submits the form
    await expect(page.getByRole('heading', { level: 1, name: "You can't have an account yet" })).toBeVisible();
    await expect(page.getByText('You are welcome to come back when you turn 18.')).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(320);
    await expectNoBlockingA11yViolations(page, testInfo, 'A-11');
    await page.goto('/matches');
    await expect(page).toHaveURL(/\/$/); // signed out: the pending sign-in is gone
  });

  test('Adult confirms: first-run page and the upload page show the footage notice, at 360 px', async ({ page }, testInfo) => {
    await page.setViewportSize({ width: 360, height: 740 });
    await newAddressSignsIn(page);
    await page.getByRole('button', { name: 'Continue' }).click();
    await expect(page.getByRole('alert').filter({ hasText: 'There is a problem' })).toBeFocused();
    await expect(page.getByRole('link', { name: 'Choose yes or no' })).toBeVisible();
    await page.getByText('Yes, I am 18 or over').click();
    await page.getByRole('button', { name: 'Continue' }).click();
    await expect(page).toHaveURL(/\/welcome$/);
    await expect(page.getByText(NOTICE)).toBeVisible();
    await page.goto('/matches/new');
    await page.getByText('Singles', { exact: true }).click();
    await page.getByRole('button', { name: 'Continue' }).click();
    await page.getByText('Side-out scoring (traditional)').click();
    await page.getByRole('button', { name: 'Continue' }).click();
    await page.getByLabel('Side A player').fill('Ivy');
    await page.getByLabel('Side B player').fill('Carlos');
    await page.getByRole('button', { name: 'Continue' }).click();
    await page.getByText('Ivy (Side A)').click();
    await page.getByRole('button', { name: 'Continue' }).click();
    await page.getByRole('button', { name: 'Continue' }).click();
    await expect(page.getByLabel('Choose video')).toBeVisible();
    await expect(page.getByRole('heading', { level: 2, name: 'Before you upload' })).toBeVisible();
    await expect(page.getByText(NOTICE)).toBeVisible();
    await expectNoBlockingA11yViolations(page, testInfo, 'Q-06-notice');
  });
});
