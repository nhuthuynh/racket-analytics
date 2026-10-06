// Binds tests/features/evidence_deep_link.feature in the browser (QA-ACC for ST-037; FR-027,
// NFR-014, NFR-055) and E2E-02-04: from a score-sheet row, the video plays from the rally's start.
// Needs SRE-MEDIA (the presigned link served through the web origin, which the page CSP allows)
// and a browser that decodes the H.264 original (blockers.md 2026-10-06: Playwright Chromium does
// not; WebKit on CI or a Chrome channel does). The 1.5 s p95 on the throttled profile is measured
// by timing.spec.ts (G02-06 c).
import { expect, test, type Page } from '@playwright/test';
import { expectNoBlockingA11yViolations } from '../helpers/axe';
import { decodableStandIn, decodesH264, rangeResponse, receivedMatch, sheetOf, tagJourneyByApi } from '../helpers/sprint-02';

// Some tests route the media request; block the service worker so the route sees it in WebKit
// too (TCR 2026-10-05).
test.use({ serviceWorkers: 'block' });

async function openSheet(page: Page): Promise<{ matchId: string; start: number }> {
  const matchId = await receivedMatch(page);
  await tagJourneyByApi(page, matchId);
  const start = (await sheetOf(page, matchId)).rows[2]!.start_ms;
  await page.goto(`/matches/${matchId}/sheet`);
  return { matchId, start };
}

async function expectPlayingFrom(page: Page, startMs: number): Promise<void> {
  const video = page.getByRole('region', { name: 'Rally 3 video' }).locator('video');
  await expect
    .poll(() => video.evaluate((v: HTMLVideoElement) => v.readyState >= 2 && !v.error), { timeout: 15_000 })
    .toBe(true);
  const at = await video.evaluate((v: HTMLVideoElement) => v.currentTime);
  expect(Math.abs(at - startMs / 1000)).toBeLessThan(1.0);
  await expect(page.getByText('This video link no longer works')).toHaveCount(0);
}

test.describe('@M0 @story-ST-037 Jump to the video moment', () => {
  test('E2E-02-04 a rally row opens the real video playing from the rally start', async ({ page }, testInfo) => {
    const { start } = await openSheet(page);
    expect(await decodesH264(page), 'this browser cannot decode the H.264 original (blockers.md 2026-10-06)').toBe(true);
    const media = page.waitForResponse((r) => /X-Amz-Signature=/.test(r.url()));
    await page.getByRole('button', { name: 'Watch rally 3' }).click();
    const response = await media;
    expect(new URL(response.url()).origin).toBe(new URL(page.url()).origin); // through the web origin (SRE-MEDIA)
    await expectPlayingFrom(page, start);
    await expectNoBlockingA11yViolations(page, testInfo, 'V-01');
  });

  test('V-01 seeks to the rally start and plays (decodable stand-in for the presigned link)', async ({ page }, testInfo) => {
    const { start } = await openSheet(page);
    const body = await decodableStandIn();
    const asked: string[] = [];
    await page.route(/X-Amz-Signature=/, async (route) => {
      asked.push(route.request().url());
      await route.fulfill(rangeResponse(route.request().headers()['range'], body));
    });
    await page.getByRole('button', { name: 'Watch rally 3' }).click();
    await expectPlayingFrom(page, start);
    expect(asked.length).toBeGreaterThan(0);
    const url = new URL(asked[0]!);
    expect(url.searchParams.get('X-Amz-Expires')).not.toBeNull();
    expect(Number(url.searchParams.get('X-Amz-Expires'))).toBeLessThanOrEqual(900); // NFR-055
    await expectNoBlockingA11yViolations(page, testInfo, 'V-01-stand-in');
  });

  test('An old or changed video link stops working, and reopening the rally still works', async ({ page }) => {
    const { start } = await openSheet(page);
    const body = await decodableStandIn();
    let first = true;
    await page.route(/X-Amz-Signature=/, async (route) => {
      if (first) {
        first = false; // the store refuses an expired or changed signature with 403
        await route.fulfill({ status: 403, body: 'SignatureDoesNotMatch' });
        return;
      }
      await route.fulfill(rangeResponse(route.request().headers()['range'], body));
    });
    await page.getByRole('button', { name: 'Watch rally 3' }).click();
    await expect(page.getByRole('alert').filter({ hasText: /\S/ })).toHaveText(
      "This video link no longer works. Choose 'Watch rally 3' again.",
    );
    await page.getByRole('button', { name: 'Watch rally 3' }).click();
    await expectPlayingFrom(page, start);
  });
});
