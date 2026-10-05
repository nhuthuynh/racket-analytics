// Binds tests/features/first_run_and_capture_guide.feature (ST-015; sprint-01 §7.2, §14.3.3;
// FR-004, FR-020; NFR-033, NFR-035). Copy: flows F-01, G-01 and capture-guide-wording.md.
// Red until ST-015.
import { expect, test, type Page } from '@playwright/test';
import { expectNoBlockingA11yViolations } from '../helpers/axe';
import { signInByLink } from '../helpers/sprint-01';

async function openGuide(page: Page): Promise<void> {
  await signInByLink(page);
  await page.getByRole('link', { name: 'Show me how to film' }).or(page.getByRole('button', { name: 'Show me how to film' })).first().click();
  await expect(page.getByRole('heading', { level: 1, name: 'How to film your match' })).toBeVisible();
}

test.describe('First run and capture guide', () => {
  test('New user sees capabilities and limits', async ({ page }, testInfo) => {
    await signInByLink(page);
    await expect(page.getByRole('heading', { level: 1, name: 'What Racket Analytics does' })).toBeVisible();
    await expect(page.getByText("We can't make line calls or referee your match from one phone.")).toBeVisible();
    await expect(page.getByText('Only you can see your videos.')).toBeVisible();
    await expectNoBlockingA11yViolations(page, testInfo, 'F-01');
    await page.getByRole('link', { name: 'Show me how to film' }).or(page.getByRole('button', { name: 'Show me how to film' })).first().click();
    await expect(page.getByRole('heading', { level: 1, name: 'How to film your match' })).toBeVisible();
  });

  test('Read the guide without playing the video', async ({ page }, testInfo) => {
    await openGuide(page);
    const items = page.locator('main ol > li');
    const count = await items.count();
    expect(count).toBeGreaterThan(0);
    expect(count).toBeLessThanOrEqual(6);
    for (let i = 0; i < count; i += 1) {
      const item = items.nth(i);
      expect((await item.innerText()).trim().length).toBeGreaterThan(10);
      const img = item.locator('img, svg[role="img"]');
      await expect(img.first()).toBeVisible();
      const alt = (await img.first().getAttribute('alt')) ?? (await img.first().getAttribute('aria-label')) ?? '';
      expect(alt.trim().length, `illustration ${i + 1} needs purpose alt text (NFR-035)`).toBeGreaterThan(0);
    }
    await expectNoBlockingA11yViolations(page, testInfo, 'G-01');
  });

  test('Watch the guide video', async ({ page }) => {
    await openGuide(page);
    const video = page.locator('video');
    await expect(video).toHaveCount(1);
    await expect(video.locator('track[kind="captions"][default]')).toHaveCount(1);
    expect(await video.getAttribute('autoplay')).toBeNull();
    await video.evaluate((v: HTMLVideoElement) => v.play().catch(() => undefined));
    await expect
      .poll(() => video.evaluate((v: HTMLVideoElement) => v.textTracks[0]?.mode))
      .toBe('showing');
  });

  test('The app does not claim to score automatically', async ({ page }) => {
    await signInByLink(page);
    const main = page.locator('main');
    await expect(main).toContainText('mark who won each rally');
    await expect(main).toContainText('keep the score');
    await expect(main).toContainText('not yet checked against the official rulebook');
    await expect(main).toContainText('unofficial');
  });

  test('Guide video cannot load', async ({ page }) => {
    await page.route(/\.(mp4|webm|mov)(\?|$)/, (route) => route.abort());
    await openGuide(page);
    await expect(page.getByText(/Everything in it is in the checklist above/)).toBeVisible();
    await expect(page.locator('main ol > li').first()).toBeVisible();
  });
});
