// G01-10 (NFR-027, NFR-028; DPA/DESIGN-14): axe (WCAG 2.2 AA, 0 serious/critical) and the 24x24
// target check on the error and transient states that no other spec measured: Q-03 error,
// U-03, U-04 (return visit and different file), A-03 and A-05. PD-V1-01: the scorecard took
// G01-10 from a report that only measured Q-01 without an error, so PD-R1-03 (error-summary links
// below 24 px) could not show. Copy: docs/design/flows-sprint-01.md.
import { expect, test, type Page, type TestInfo } from '@playwright/test';
import { expectNoBlockingA11yViolations, expectTargetsAtLeast24 } from '../helpers/axe';
import {
  answerSetup,
  createAndUpload,
  expectErrorSummary,
  latestSignInLink,
  LONG_CLIP,
  paddedClip,
  PDF_BYTES,
  requestLink,
  signInByLink,
  uniqueEmail,
  writeBytes,
} from '../helpers/sprint-01';

// page.route does not see requests of a service-worker-controlled page in WebKit; routing
// specs block the worker (TCR 2026-10-05, W-01 WebKit family). The worker keeps its own
// coverage in security-headers.spec.ts and the unit tests.
test.use({ serviceWorkers: 'block' });

async function measure(page: Page, testInfo: TestInfo, label: string): Promise<void> {
  await expectNoBlockingA11yViolations(page, testInfo, label);
  await expectTargetsAtLeast24(page, testInfo, label);
}

test.describe('Accessibility of error and transient states (G01-10)', () => {
  test('Q-03 error: wrong number of players', async ({ page }, testInfo) => {
    await signInByLink(page);
    await page.getByRole('link', { name: 'Record your first match' }).first().click();
    await page.getByRole('radio', { name: 'Doubles' }).check();
    await page.getByRole('button', { name: 'Continue' }).click();
    await page.getByRole('radio', { name: 'Side-out scoring (traditional)' }).check();
    await page.getByRole('button', { name: 'Continue' }).click();
    const boxes = page.getByRole('textbox');
    for (const [i, name] of ['Ivy', 'Dana', 'Carlos'].entries()) await boxes.nth(i).fill(name);
    await page.getByRole('button', { name: 'Continue' }).click();
    await expectErrorSummary(page, 'Each side needs two players');
    await measure(page, testInfo, 'Q-03-error');
  });

  test('U-03: video not accepted', async ({ page }, testInfo) => {
    const file = await writeBytes(testInfo.outputPath('media'), 'match.mp4', PDF_BYTES);
    await signInByLink(page);
    await answerSetup(page, { format: 'Singles', players: ['Ivy', 'Carlos'], me: 'Ivy', file });
    await page.getByRole('button', { name: 'Create match and upload' }).click();
    await expectErrorSummary(page, 'This file is not a video we can read');
    await measure(page, testInfo, 'U-03');
  });

  test('U-04: return visit and a different file chosen', async ({ page, context }, testInfo) => {
    const file = await paddedClip(testInfo.outputPath('media'), 16);
    // The first chunk goes through (the match shows an unfinished upload), the rest never do.
    let patches = 0;
    await page.route('**/uploads/**', async (route) => {
      if (route.request().method() === 'PATCH' && (patches += 1) > 1) return route.abort();
      await route.continue();
    });
    await signInByLink(page);
    await answerSetup(page, { format: 'Singles', players: ['Ivy', 'Carlos'], me: 'Ivy', file });
    await createAndUpload(page);
    await expect.poll(() => patches, { timeout: 30_000 }).toBeGreaterThan(1);
    await page.close();

    const again = await context.newPage();
    await again.goto('/');
    await expect(again.getByRole('button', { name: 'Resume upload' })).toBeVisible();
    await measure(again, testInfo, 'U-04-banner');
    await again.getByRole('button', { name: 'Resume upload' }).click();
    await again.getByLabel('Choose video').setInputFiles(LONG_CLIP);
    await expect(again.getByText(/This is not the same video/)).toBeVisible();
    await measure(again, testInfo, 'U-04-different-file');
  });

  test('A-03: signing you in', async ({ page }, testInfo) => {
    const email = uniqueEmail();
    await requestLink(page, email);
    const link = new URL(await latestSignInLink(email));
    let release: () => void = () => undefined;
    const held = new Promise<void>((r) => { release = r; });
    await page.route('**/auth/exchange', async (route) => {
      await held; // hold the exchange so A-03 stays on screen while it is measured
      await route.continue();
    });
    await page.goto(`${link.pathname}${link.hash}`);
    await page.waitForLoadState('load'); // axe must not race A-03's own navigation (W-01)
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
    await measure(page, testInfo, 'A-03');
    release();
  });

  test('A-05: signed out', async ({ page }, testInfo) => {
    await signInByLink(page);
    await page.getByRole('button', { name: 'Your account' }).click();
    await page.getByRole('menuitem', { name: 'Sign out' }).or(page.getByRole('button', { name: 'Sign out' })).first().click();
    await expect(page.getByRole('heading', { level: 1, name: 'You have signed out' })).toBeVisible();
    await measure(page, testInfo, 'A-05');
  });
});
