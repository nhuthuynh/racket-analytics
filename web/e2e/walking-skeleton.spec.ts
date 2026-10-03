// E2E-00-01 walking skeleton (sprint-00 §6; tests/features/walking_skeleton.feature, UI level).
// dev sign-in -> new match -> upload the synthetic fixture -> match page shows
// "Duration 1:00 · 60 fps · 1920×1080", with axe on every page (NFR-027).
// Written first by QA (ST-012): RED until ST-010 (with ST-008, ST-009) lands.
import { expect, test } from '@playwright/test';
import { expectNoBlockingA11yViolations } from './helpers/axe';
import { FIXTURE_CLIP, createMatch, signInAs } from './helpers/journey';

test.describe('@M0 @story-ST-010 walking skeleton', () => {
  test('upload the fixture clip and see its facts', async ({ page }, testInfo) => {
    test.slow(); // upload plus probe of a 60 s clip

    await page.goto('/');
    await expectNoBlockingA11yViolations(page, testInfo, 'sign-in');

    await signInAs(page, 'Ivy');
    await expect(page.getByText(/no matches yet/i)).toBeVisible(); // empty state (DoD UI)
    await expectNoBlockingA11yViolations(page, testInfo, 'matches-empty');

    await page.getByRole('link', { name: /new match/i }).click();
    await expectNoBlockingA11yViolations(page, testInfo, 'new-match');
    await page.goBack();

    await createMatch(page, 'Skeleton test');
    await page.getByLabel(/match video/i).setInputFiles(FIXTURE_CLIP);

    const progress = page.getByRole('progressbar', { name: /upload/i });
    await expect(progress).toBeVisible();
    await expect(page.getByText(/\d+(\.\d+)? of \d+(\.\d+)? MB/)).toBeVisible(); // % and MB
    await expectNoBlockingA11yViolations(page, testInfo, 'uploading');

    await expect(page.getByText('Video received')).toBeVisible({ timeout: 120_000 });
    await expect(page.getByText('Duration 1:00 · 60 fps · 1920×1080')).toBeVisible({
      timeout: 120_000,
    });
    await expectNoBlockingA11yViolations(page, testInfo, 'match-detail');
  });

  test('progress never exceeds 100% and the page survives a reload mid-upload', async ({
    page,
  }) => {
    await signInAs(page, 'Ivy');
    await createMatch(page, 'Reload test');
    await page.getByLabel(/match video/i).setInputFiles(FIXTURE_CLIP);
    const progress = page.getByRole('progressbar', { name: /upload/i });
    await expect(progress).toBeVisible();

    const now = Number(await progress.getAttribute('aria-valuenow'));
    expect(now).toBeGreaterThanOrEqual(0);
    expect(now).toBeLessThanOrEqual(100);

    await page.reload();
    await expect(page.getByText(/uploading|video received/i)).toBeVisible();
  });
});
