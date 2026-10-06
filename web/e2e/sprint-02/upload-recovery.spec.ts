// Binds tests/features/upload_recovery.feature (C-03, PD-R3V-01; card C-03 "E2E verification",
// the QA case the FE row asks for): a server error during the upload offers "Try again" with a
// support reference, never "No video yet", and trying again continues from the saved offset.
import { expect, test } from '@playwright/test';
import { answerSetup, createAndUpload, paddedClip, signInByLink, uploadPercent } from '../helpers/sprint-01';
import { expectNoBlockingA11yViolations } from '../helpers/axe';

test.use({ serviceWorkers: 'block' }); // the spec routes PATCH requests (TCR 2026-10-05)

test.describe('@M0 @story-C-03 Recover from an upload server error', () => {
  test('14.3.3 The server fails during the upload', async ({ page }, testInfo) => {
    test.slow(); // the tus client retries a 5xx before it gives up (RETRY_DELAYS, about 40 s)
    const file = await paddedClip(testInfo.outputPath('media'), 12); // about 3 chunks
    await signInByLink(page);
    await answerSetup(page, { format: 'Singles', players: ['Ivy', 'Carlos'], me: 'Ivy', file });

    // The first chunk is stored; from then on the server fails every PATCH with a 500.
    let stored = 0;
    let failing = true;
    await page.route('**/uploads/**', async (route) => {
      if (route.request().method() !== 'PATCH' || !failing) return route.fallback();
      if (stored === 0) {
        stored += 1;
        return route.fallback();
      }
      return route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({
          error: { code: 'internal_error', message: 'Something went wrong on our side.', support_ref: 'ref_0c03e2e0c03e2e00' },
        }),
      });
    });
    const posts: string[] = [];
    page.on('request', (r) => {
      if (r.method() === 'POST' && /\/uploads$/.test(new URL(r.url()).pathname)) posts.push(r.url());
    });
    await createAndUpload(page);

    await expect(page.getByRole('button', { name: 'Try again' })).toBeVisible({ timeout: 90_000 });
    await expect(page.getByText(/problem on our side\..*Try again\. Reference: ref_0c03e2e0c03e2e00/)).toBeVisible();
    await expect(page.getByText('No video yet')).toHaveCount(0);
    const percent = await uploadPercent(page);
    expect(percent).toBeGreaterThan(0);
    await expectNoBlockingA11yViolations(page, testInfo, 'U-01-stopped');

    failing = false;
    const head = page.waitForRequest((r) => r.method() === 'HEAD' && /\/uploads\//.test(r.url()));
    await page.getByRole('button', { name: 'Try again' }).click();
    await head; // continues from the server's offset, not from the start
    await expect(page.getByText('Video received')).toBeVisible({ timeout: 120_000 });
    expect(posts).toHaveLength(1); // no second upload was created
  });
});
