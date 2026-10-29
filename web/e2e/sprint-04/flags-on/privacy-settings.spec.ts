// E2E-04-07 privacy settings R-01 (ST-071; FR-008, FR-009; api-sprint-04 §10). Runs only in the
// `flags-on` project (PW_PROJECTS=flags-on, added by ST-065) against a stack started with
// FEATURE_RETENTION_SETTING=1 FEATURE_TRAINING_CONSENT=1; nightly and by the verifier (G04-07).
// Keyboard only from the radios to the confirmation; axe and 24 px targets; 320/360 px.
import { expect, test } from '@playwright/test';
import { expectNoBlockingA11yViolations, expectTargetsAtLeast24 } from '../../helpers/axe';
import { signInByLink, uniqueEmail } from '../../helpers/sprint-01';

test.describe('@M5 @story-ST-071 Privacy settings (flags on)', () => {
  test.beforeEach(({}, testInfo) => {
    test.skip(testInfo.project.name !== 'flags-on', 'flag-on spec: runs in the flags-on project only');
  });

  test('E2E-04-07 retention choice with deletion dates and training use, by keyboard, at 320 and 360 px', async ({ page }, testInfo) => {
    test.setTimeout(120_000);
    await signInByLink(page, uniqueEmail('ivy'));
    await page.goto('/settings/privacy');
    await expect(page.getByRole('heading', { level: 1 })).toHaveText('Privacy settings');
    const consent = page.getByRole('checkbox', { name: 'Use my matches to improve the app' });
    await expect(consent).not.toBeChecked();
    await expect(page.getByRole('radio', { name: '90 days (default)' })).toBeChecked();
    await expectNoBlockingA11yViolations(page, testInfo, 'R-01');
    await expectTargetsAtLeast24(page, testInfo, 'R-01');

    await page.getByRole('radio', { name: '90 days (default)' }).focus();
    await page.keyboard.press('ArrowUp');
    await page.keyboard.press('Tab');
    await expect(page.getByRole('button', { name: 'Save video setting' })).toBeFocused();
    await page.keyboard.press('Enter');
    await expect(page.getByText('Saved. The new deletion dates are shown below.')).toBeVisible();
    expect((await (await page.request.get('/api/me/retention')).json()).review_video_days).toBe(30);

    await consent.focus();
    await page.keyboard.press('Space');
    await page.keyboard.press('Tab');
    await page.keyboard.press('Enter');
    await expect(page.getByText('Turned on. You can turn it off here at any time.')).toBeVisible();
    expect((await (await page.request.get('/api/me/training-consent')).json()).opt_in).toBe(true);

    for (const width of [320, 360]) {
      await page.setViewportSize({ width, height: 740 });
      await page.reload();
      await expect(page.getByRole('radio', { name: '30 days' })).toBeChecked();
      expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(width);
      await expectNoBlockingA11yViolations(page, testInfo, `R-01-${width}`); // G04-08 (a), (d)
      await expectTargetsAtLeast24(page, testInfo, `R-01-${width}`); // G04-08 (b)
    }
  });
});
