// C-22 (PD-R2R-08; NFR-027a, NFR-028; DPA/DESIGN-14): axe (WCAG 2.2 AA, 0 serious/critical) and
// the 24x24 target check on the Sprint 1 states no other spec measured: A-02 "Check your email",
// the two 429 states (A-01 too many link requests; U-01 too many unfinished uploads), U-01 paused
// (waiting for connection), U-01 trouble (retrying after server errors) and M-02 with the footage
// quality report. U-01 stopped is measured in sprint-02/upload-recovery.spec.ts.
// Copy: docs/design/flows-sprint-01.md (A-02, U-01, §6 states; R-5 for the quota state).
import { expect, test, type Page, type TestInfo } from '@playwright/test';
import path from 'node:path';
import { expectNoBlockingA11yViolations, expectTargetsAtLeast24 } from '../helpers/axe';
import {
  answerSetup,
  createAndUpload,
  expectErrorSummary,
  paddedClip,
  requestLink,
  signInByLink,
  uniqueEmail,
  uploadPercent,
} from '../helpers/sprint-01';
import { PEOPLE } from '../helpers/sprint-02';

// The specs below route PATCH requests; page.route does not see requests of a
// service-worker-controlled page in WebKit (TCR 2026-10-05, W-01 WebKit family).
test.use({ serviceWorkers: 'block' });

const CLIP_1080P30 = path.resolve(__dirname, '../../../fixtures/clips/phone-profiles-v1/h264-mp4-1080p30.mp4');
const OPEN_UPLOAD_QUOTA = 3; // NFR-023 (C-02: 8 parallel creations -> exactly 3 x 201)

async function measure(page: Page, testInfo: TestInfo, label: string): Promise<void> {
  await expectNoBlockingA11yViolations(page, testInfo, label);
  await expectTargetsAtLeast24(page, testInfo, label);
}

test.describe('Accessibility of the remaining Sprint 1 states (C-22)', () => {
  test('A-02: check your email', async ({ page }, testInfo) => {
    await requestLink(page, uniqueEmail());
    await expect(page.getByRole('button', { name: 'send a new link' })).toBeVisible();
    await measure(page, testInfo, 'A-02');
  });

  test('A-01 429: too many link requests', async ({ page }, testInfo) => {
    const email = uniqueEmail();
    for (let i = 0; i < 5; i += 1) await requestLink(page, email);
    await page.goto('/');
    await page.getByLabel('Email address').fill(email);
    await page.getByRole('button', { name: 'Send me a link' }).click();
    await expectErrorSummary(page, /You can ask for a new link at \d{1,2}:\d{2}/);
    await measure(page, testInfo, 'A-01-429');
  });

  test('U-01 paused: waiting for connection', async ({ page, context }, testInfo) => {
    const file = await paddedClip(testInfo.outputPath('media'), 24);
    await page.route('**/uploads/**', async (route) => {
      if (route.request().method() === 'PATCH') await new Promise((r) => setTimeout(r, 400));
      await route.fallback();
    });
    await signInByLink(page);
    await answerSetup(page, { format: 'Singles', players: ['Ivy', 'Carlos'], me: 'Ivy', file });
    await createAndUpload(page);
    await expect.poll(() => uploadPercent(page), { timeout: 60_000 }).toBeGreaterThan(0);

    await context.setOffline(true);
    await expect(page.getByText('Paused: waiting for connection')).toBeVisible();
    await measure(page, testInfo, 'U-01-paused');
    await context.setOffline(false);
    await expect(page.getByText('Video received')).toBeVisible({ timeout: 120_000 });
  });

  test('U-01 trouble: the server keeps failing, the client retries', async ({ page }, testInfo) => {
    test.slow(); // the tus client waits between retries
    const file = await paddedClip(testInfo.outputPath('media'), 12);
    let stored = 0;
    let failing = true;
    await page.route('**/uploads/**', async (route) => {
      if (route.request().method() !== 'PATCH' || !failing) return route.fallback();
      if (stored === 0) {
        stored += 1;
        return route.fallback(); // the first chunk is stored, so the panel shows progress
      }
      return route.fulfill({
        status: 503,
        contentType: 'application/json',
        body: JSON.stringify({ error: { code: 'unavailable', message: 'Please try again.', support_ref: 'ref_c22c22c22c22c22c' } }),
      });
    });
    await signInByLink(page);
    await answerSetup(page, { format: 'Singles', players: ['Ivy', 'Carlos'], me: 'Ivy', file });
    await createAndUpload(page);

    await expect(page.getByText("Paused: we're having trouble sending your video. Retrying…")).toBeVisible({ timeout: 60_000 });
    await measure(page, testInfo, 'U-01-trouble');
    failing = false; // the next retry goes through and the upload finishes
    await expect(page.getByText('Video received')).toBeVisible({ timeout: 120_000 });
  });

  test('U-01 429: too many unfinished uploads', async ({ page }, testInfo) => {
    await signInByLink(page);
    // OPEN_UPLOAD_QUOTA matches with an upload created and no byte sent: all of them open.
    for (let i = 0; i < OPEN_UPLOAD_QUOTA; i += 1) {
      const created = await page.request.post('/api/matches', {
        data: { title: `Open upload ${i + 1}`, format: 'doubles', participants: PEOPLE },
      });
      expect(created.status(), await created.text()).toBe(201);
      const matchId = String(((await created.json()) as { id: string }).id);
      const upload = await page.request.post(`/api/matches/${matchId}/uploads`, {
        headers: { 'Tus-Resumable': '1.0.0', 'Upload-Length': '1048576' },
      });
      expect(upload.status(), await upload.text()).toBe(201);
    }
    await page.goto('/matches');
    await answerSetup(page, { format: 'Singles', players: ['Ivy', 'Carlos'], me: 'Ivy' });
    await page.getByRole('button', { name: 'Create match and upload' }).click();

    await expectErrorSummary(page, 'You have too many unfinished uploads. Finish one of them from Your matches, then try again.');
    await expect(page.getByText('No video yet')).toBeVisible(); // nothing started (R-5)
    await measure(page, testInfo, 'U-01-quota-429');
  });

  test('M-02 with the footage quality report', async ({ page }, testInfo) => {
    test.slow(); // upload plus probe
    await signInByLink(page);
    await answerSetup(page, { format: 'Singles', players: ['Ivy', 'Carlos'], me: 'Ivy', file: CLIP_1080P30 });
    await createAndUpload(page);
    await expect(page.getByText('Video received')).toBeVisible({ timeout: 120_000 });
    await expect(page.getByRole('region', { name: 'Footage quality' })).toContainText('Recorded at 30 fps', { timeout: 120_000 });
    await measure(page, testInfo, 'M-02-report');
  });
});
