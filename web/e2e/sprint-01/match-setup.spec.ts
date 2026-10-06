// Binds tests/features/match_setup.feature (ST-016; sprint-01 §7.3, §14.3.4) in the browser,
// plus E2E-01-03 (keyboard-only setup) and the 320/360/768/1280 reflow matrix (NFR-034).
// Copy: flows Q-01..Q-07. Red until ST-016.
import { expect, test, type Page } from '@playwright/test';
import { expectNoBlockingA11yViolations } from '../helpers/axe';
import { answerSetup, expectErrorSummary, signInByLink } from '../helpers/sprint-01';

async function startSetup(page: Page): Promise<void> {
  await signInByLink(page);
  await page.getByRole('link', { name: 'Record your first match' }).first().click();
  await expect(page.getByRole('heading', { level: 1, name: 'Is this a doubles or singles match?' })).toBeVisible();
}

async function continueTo(page: Page, heading: string): Promise<void> {
  await page.getByRole('button', { name: 'Continue' }).click();
  await expect(page.getByRole('heading', { level: 1, name: heading })).toBeVisible();
}

test.describe('Match setup', () => {
  test('Missing answer', async ({ page }, testInfo) => {
    await startSetup(page);
    await page.getByRole('button', { name: 'Continue' }).click();
    await expectErrorSummary(page, 'Select doubles or singles');
    await page.getByRole('alert').getByRole('link', { name: 'Select doubles or singles' }).click();
    await expect(page.getByRole('radio', { name: 'Doubles' })).toBeFocused();
    await expectNoBlockingA11yViolations(page, testInfo, 'Q-01-error');
  });

  test('Review before upload', async ({ page }, testInfo) => {
    await signInByLink(page);
    await answerSetup(page, { format: 'Doubles', players: ['Ivy', 'Dana', 'Carlos', 'Sam'], me: 'Ivy' });
    for (const row of ['Format', 'Scoring system', 'Players', 'You', 'Date', 'Video']) {
      await expect(page.getByText(row, { exact: true })).toBeVisible();
    }
    expect(await page.getByRole('link', { name: /^Change/ }).count()).toBeGreaterThanOrEqual(6);
    await expectNoBlockingA11yViolations(page, testInfo, 'Q-07');
  });

  test('Doubles match setup', async ({ page }) => {
    await signInByLink(page);
    await answerSetup(page, { format: 'Doubles', players: ['Ivy', 'Dana', 'Carlos', 'Sam'], me: 'Ivy' });
    const main = page.locator('main');
    await expect(main).toContainText('Side A');
    await expect(main).toContainText('Side B');
    for (const name of ['Ivy', 'Dana', 'Carlos', 'Sam']) await expect(main).toContainText(name);
    await expect(main).toContainText(/Ivy \(Side A\)/);
  });

  test('Wrong participants for the format: doubles, three nicknames', async ({ page }) => {
    await startSetup(page);
    await page.getByRole('radio', { name: 'Doubles' }).check();
    await continueTo(page, 'Which scoring system did you play?');
    await page.getByRole('radio', { name: 'Side-out scoring (traditional)' }).check();
    await continueTo(page, 'Who played?');
    const boxes = page.getByRole('textbox');
    for (const [i, name] of ['Ivy', 'Dana', 'Carlos'].entries()) await boxes.nth(i).fill(name);
    await page.getByRole('button', { name: 'Continue' }).click();
    await expectErrorSummary(page, 'Each side needs two players');
  });

  test('Wrong participants for the format: singles three and two "me" rows', async () => {
    test.skip(true, 'The singles page has two fields and Q-04 uses radios, so these rows cannot be entered in the UI (flows Q-04); bound at API level in backend/tests/features/test_match_setup.py');
  });

  test('Rally scoring is not yet available', async ({ page }) => {
    await startSetup(page);
    await page.getByRole('radio', { name: 'Doubles' }).check();
    await continueTo(page, 'Which scoring system did you play?');
    await expect(page.getByRole('radio', { name: 'Side-out scoring (traditional)' })).toBeEnabled();
    const rally = page.getByRole('radio', { name: /Rally scoring \(provisional\)/ });
    await expect(rally).toHaveAttribute('aria-disabled', 'true');
    await rally.click({ force: true });
    await expect(rally).not.toBeChecked();
    await expect(page.getByText('It becomes available once the rules are verified.')).toBeVisible();
  });

  test('Change one answer', async ({ page }) => {
    await signInByLink(page);
    await answerSetup(page, { format: 'Doubles', players: ['Ivy', 'Dana', 'Carlos', 'Sam'], me: 'Ivy' });
    await page.getByRole('link', { name: /^Change\s*format/ }).click();
    await page.getByRole('radio', { name: 'Singles' }).check();
    await page.getByRole('button', { name: 'Continue' }).click();
    await expect(page.getByRole('heading', { level: 1, name: 'Check your answers' })).toBeVisible();
    await expect(page.locator('main')).toContainText(/one player per side/i);
  });

  test('A nickname that looks like an email address', async ({ page }) => {
    await startSetup(page);
    await page.getByRole('radio', { name: 'Doubles' }).check();
    await continueTo(page, 'Which scoring system did you play?');
    await page.getByRole('radio', { name: 'Side-out scoring (traditional)' }).check();
    await continueTo(page, 'Who played?');
    const boxes = page.getByRole('textbox');
    for (const [i, name] of ['Ivy', 'Dana', 'carlos@example.com', 'Sam'].entries()) await boxes.nth(i).fill(name);
    await boxes.nth(2).blur();
    await expect(page.getByText('This looks like contact details. Use a nickname instead.')).toBeVisible();
    await continueTo(page, 'Which player are you?');
  });

  test('Future match date', async ({ page }) => {
    await startSetup(page);
    await page.getByRole('radio', { name: 'Singles' }).check();
    await continueTo(page, 'Which scoring system did you play?');
    await page.getByRole('radio', { name: 'Side-out scoring (traditional)' }).check();
    await continueTo(page, 'Who played?');
    const boxes = page.getByRole('textbox');
    await boxes.nth(0).fill('Ivy');
    await boxes.nth(1).fill('Carlos');
    await continueTo(page, 'Which player are you?');
    await page.getByRole('radio', { name: /^Ivy \(Side A\)$/ }).check();
    await continueTo(page, 'When was the match played?');
    const tomorrow = new Date(Date.now() + 36 * 3600 * 1000);
    await page.getByLabel('Day').fill(String(tomorrow.getDate()));
    await page.getByLabel('Month').fill(String(tomorrow.getMonth() + 1));
    await page.getByLabel('Year').fill(String(tomorrow.getFullYear()));
    await page.getByRole('button', { name: 'Continue' }).click();
    await expectErrorSummary(page, 'The date must be today or in the past');
  });

  test('E2E-01-03 keyboard-only setup (NFR-034, NFR-030)', async ({ page }) => {
    await signInByLink(page);
    // Only Tab, Shift+Tab, Space, Enter and typing from here on.
    const tabTo = async (target: ReturnType<Page['getByRole']>) => {
      for (let i = 0; i < 40; i += 1) {
        if (await target.evaluate((el) => el === document.activeElement).catch(() => false)) return;
        await page.keyboard.press('Tab');
      }
      throw new Error('could not reach the control with Tab');
    };
    const next = async (heading: string) => {
      await tabTo(page.getByRole('button', { name: 'Continue' }));
      await page.keyboard.press('Enter');
      await expect(page.getByRole('heading', { level: 1, name: heading })).toBeVisible();
    };
    await tabTo(page.getByRole('link', { name: 'Record your first match' }).first());
    await page.keyboard.press('Enter');
    await tabTo(page.getByRole('radio', { name: 'Doubles' }));
    await page.keyboard.press('Space');
    await next('Which scoring system did you play?');
    await tabTo(page.getByRole('radio', { name: 'Side-out scoring (traditional)' }));
    await page.keyboard.press('Space');
    await next('Who played?');
    for (const [i, name] of ['Ivy', 'Dana', 'Carlos', 'Sam'].entries()) {
      await tabTo(page.getByRole('textbox').nth(i));
      await page.keyboard.type(name);
    }
    await next('Which player are you?');
    await tabTo(page.getByRole('radio', { name: /^Ivy \(Side A\)$/ }));
    await page.keyboard.press('Space');
    await next('When was the match played?');
    await next('Choose the match video');
  });

  for (const width of [320, 360, 768, 1280]) {
    test(`Setup pages reflow at ${width} px without horizontal scroll (NFR-034)`, async ({ page }) => {
      await page.setViewportSize({ width, height: 800 });
      await startSetup(page);
      const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
      expect(overflow).toBeLessThanOrEqual(0);
      const small = await page.evaluate(() =>
        [...document.querySelectorAll('a, button, input, [role="radio"]')]
          .map((el) => el.getBoundingClientRect())
          .filter((r) => r.width > 0 && r.height > 0 && (r.width < 24 || r.height < 24)).length,
      );
      expect(small, 'targets below 24x24 CSS px (NFR-028)').toBe(0);
    });
  }
});
