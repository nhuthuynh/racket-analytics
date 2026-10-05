// Binds tests/features/sign_in.feature (ST-013; sprint-01 §7.1, §14.3.1) in the browser,
// E2E-01-01 first step. Copy: docs/design/flows-sprint-01.md A-01..A-04. Written before ST-013
// (red until it lands). Needs the stack with Mailpit (MAILPIT_API_URL).
import { expect, test } from '@playwright/test';
import { expectNoBlockingA11yViolations } from '../helpers/axe';
import {
  expectErrorSummary,
  latestSignInLink,
  openSignInLink,
  requestLink,
  signInByLink,
  uniqueEmail,
} from '../helpers/sprint-01';

test.describe('Sign in without a memorised password', () => {
  test('Sign up with an email sign-in link', async ({ page }, testInfo) => {
    await signInByLink(page);
    await expect(page.getByText('Record your first match').first()).toBeVisible();
    await expect(page).not.toHaveURL(/token=/); // NFR-055, T-ML-4
    expect(await page.evaluate(() => location.href)).not.toMatch(/token=/);
    await expectNoBlockingA11yViolations(page, testInfo, 'after-sign-in');
  });

  test('A link that can no longer be used: was already used', async ({ page, browser }, testInfo) => {
    const email = uniqueEmail();
    await requestLink(page, email);
    const link = new URL(await latestSignInLink(email));
    await openSignInLink(page, link); // the first page has spent the link (QA-R1-01)

    // axe needs a page from browser.newContext() (TCR: sign-in.spec.ts:29).
    const otherContext = await browser.newContext();
    const other = await otherContext.newPage();
    await other.goto(`${link.pathname}${link.hash}`);
    await expect(other.getByRole('heading', { level: 1, name: 'This link has expired' })).toBeVisible();
    await expect(other.getByRole('button', { name: 'Send a new link' })).toBeVisible();
    await expect(other.getByLabel('Email address')).toHaveValue(''); // never from the URL (A-04)
    await expectNoBlockingA11yViolations(other, testInfo, 'A-04');
    await otherContext.close();
  });

  test('A link that can no longer be used: is 16 minutes old', async () => {
    test.skip(true, 'Needs a 16-minute wait; bound at API level with MAGIC_LINK_TTL_SECONDS=2 (backend/tests/features/test_sign_in.py)');
  });

  test('Too many link requests', async ({ page }) => {
    const email = uniqueEmail();
    for (let i = 0; i < 5; i += 1) await requestLink(page, email);
    await page.goto('/');
    await page.getByLabel('Email address').fill(email);
    await page.getByRole('button', { name: 'Send me a link' }).click();
    await expectErrorSummary(page, /You can ask for a new link at \d{1,2}:\d{2}/);
  });

  test('Link requested for an unknown address', async ({ page }) => {
    const known = await signInByLink(page);
    await page.context().clearCookies();
    await requestLink(page, uniqueEmail('new'));
    const unknownText = (await page.locator('main').innerText()).replace(/\S+@example\.com/, '<email>');
    await requestLink(page, known);
    const knownText = (await page.locator('main').innerText()).replace(/\S+@example\.com/, '<email>');
    expect(unknownText).toBe(knownText); // T-ML-6: no account-existence oracle
  });

  test('The sign-in page asks only for an email address', async ({ page }, testInfo) => {
    await page.goto('/');
    await expect(page.getByRole('textbox')).toHaveCount(1);
    await expect(page.locator('input[type="password"]')).toHaveCount(0);
    const field = page.getByLabel('Email address');
    await expect(field).toHaveAttribute('type', 'email');
    await expect(field).toHaveAttribute('autocomplete', 'email');
    const pasteBlocked = await field.evaluate((el) => {
      const data = new DataTransfer();
      data.setData('text/plain', 'ivy@example.com');
      const event = new ClipboardEvent('paste', { clipboardData: data, bubbles: true, cancelable: true });
      return !el.dispatchEvent(event);
    });
    expect(pasteBlocked, 'paste must not be prevented (SC 3.3.8, NFR-032)').toBe(false);
    await expectNoBlockingA11yViolations(page, testInfo, 'A-01');
  });
});
