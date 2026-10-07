// E2E-03-08 dashboard and evidence states (ST-048, ST-047; FR-100, FR-103; NFR-027, NFR-028,
// NFR-033; PD-R1S3-03). The ST-048 card asks for "empty, loading, error and low-sample states;
// 360 px": low sample is E2E-03-03 (definitions.spec.ts). Here, on the stack under test:
// - D-01 empty: a match with its video received and no rally tagged says so and links to tagging;
// - D-01 and E-01 loading: while the API request is held, a busy region is shown, then the numbers;
// - D-01 and E-01 error: when the API request fails, an alert says so with "Try again", which
//   loads the numbers once the API answers again.
// Every state is checked with axe (0 serious/critical, NFR-027) and the 24x24 target rule
// (NFR-028), and the empty and error states at 360 px without sideways scroll (NFR-033).
// UI assumptions (copy, roles, browser-side fetch): e2e/helpers/sprint-03.ts STATE_COPY.
import { expect, test, type Page, type Route } from '@playwright/test';
import { expectNoBlockingA11yViolations, expectTargetsAtLeast24 } from '../helpers/axe';
import { receivedMatch } from '../helpers/sprint-02';
import {
  METRIC_NAMES, PUBLISHED, SCREEN, STATE_COPY, evidenceApi, loadingRegion, metricCard, noSidewaysScroll,
  statsApi, statsPath, tagWorkedExampleByApi,
} from '../helpers/sprint-03';

// page.route does not see requests of a service-worker-controlled page in WebKit (TCR
// 2026-10-05, W-01 WebKit family), so the routed specs block the worker.
test.use({ serviceWorkers: 'block' });

/** Hold every matching request until release() is called; then let them through. */
async function hold(page: Page, url: RegExp): Promise<{ release: () => void; seen: () => number }> {
  let release = (): void => {};
  const gate = new Promise<void>((resolve) => { release = resolve; });
  let seen = 0;
  await page.route(url, async (route: Route) => {
    seen += 1;
    await gate;
    await route.continue();
  });
  return { release, seen: () => seen };
}

/** Fail every matching request with a 503 until restore() is called. */
async function fail(page: Page, url: RegExp): Promise<{ restore: () => Promise<void>; seen: () => number }> {
  let seen = 0;
  const handler = async (route: Route): Promise<void> => {
    seen += 1;
    await route.fulfill({
      status: 503,
      contentType: 'application/json',
      body: JSON.stringify({ error: { code: 'unavailable', message: 'Service unavailable.', support_ref: 'e2e-03-08' } }),
    });
  };
  await page.route(url, handler);
  return { restore: () => page.unroute(url, handler), seen: () => seen };
}

const firstCardName = (): string => METRIC_NAMES[PUBLISHED[0]?.id ?? ''] ?? '';

test.describe('@M0 @story-ST-048 @nfr-027 @nfr-028 Dashboard and evidence states', () => {
  // ---------------------------------------------------------------- negative cases first
  test('E2E-03-08 D-01 error: an alert with "Try again", no numbers; Try again loads them', async ({ page }, testInfo) => {
    expect(PUBLISHED.length, 'no coach-reviewed metric (COACH-1)').toBeGreaterThan(0);
    const matchId = await receivedMatch(page, 'E2E-03-08 D error');
    await tagWorkedExampleByApi(page, matchId);
    const failing = await fail(page, statsApi(matchId));
    await page.setViewportSize({ width: 360, height: 740 });
    await page.goto(statsPath(matchId));
    await expect(page.getByRole('heading', { level: 1 })).toContainText(/stats/i);
    const alert = page.getByRole('alert').filter({ hasText: STATE_COPY.error });
    await expect(alert).toBeVisible();
    expect(failing.seen(), 'D-01 never asked the API for its numbers in the browser').toBeGreaterThan(0);
    await expect(page.getByRole('button', { name: /Show me/ }), 'numbers shown although the request failed').toHaveCount(0);
    await expect(alert).not.toContainText(/e2e-03-08|unavailable|503/i); // fixed copy, no raw error
    await noSidewaysScroll(page);
    await expectNoBlockingA11yViolations(page, testInfo, `${SCREEN.dashboard}-error`);
    await expectTargetsAtLeast24(page, testInfo, `${SCREEN.dashboard}-error`);

    await failing.restore();
    await page.getByRole('button', { name: STATE_COPY.retry }).click();
    await expect(page.getByRole('heading', { name: firstCardName(), exact: true })).toBeVisible();
    await expect(page.getByRole('alert').filter({ hasText: STATE_COPY.error })).toHaveCount(0);
  });

  test('E2E-03-08 E-01 error: an alert with "Try again", no rally links; Try again lists them', async ({ page }, testInfo) => {
    expect(PUBLISHED.length, 'no coach-reviewed metric (COACH-1)').toBeGreaterThan(0);
    const matchId = await receivedMatch(page, 'E2E-03-08 E error');
    await tagWorkedExampleByApi(page, matchId);
    await page.goto(statsPath(matchId));
    const card = metricCard(page, PUBLISHED[0]?.id ?? '');
    await expect(card).toBeVisible();
    const failing = await fail(page, evidenceApi(matchId));
    await card.getByRole('button', { name: /Show me/ }).first().click();
    const alert = page.getByRole('alert').filter({ hasText: STATE_COPY.error });
    await expect(alert).toBeVisible();
    expect(failing.seen(), 'E-01 never asked the API for its rallies in the browser').toBeGreaterThan(0);
    await expect(page.getByRole('link', { name: /Rally \d+/ }), 'rally links shown although the request failed').toHaveCount(0);
    await expectNoBlockingA11yViolations(page, testInfo, `${SCREEN.evidence}-error`);
    await expectTargetsAtLeast24(page, testInfo, `${SCREEN.evidence}-error`);

    await failing.restore();
    await page.getByRole('button', { name: STATE_COPY.retry }).click();
    await expect(page.getByRole('link', { name: /Rally \d+/ }).first()).toBeVisible();
  });

  test('E2E-03-08 D-01 empty: no rally tagged yet, a link to tagging, no metric numbers', async ({ page }, testInfo) => {
    const matchId = await receivedMatch(page, 'E2E-03-08 empty');
    await page.setViewportSize({ width: 360, height: 740 });
    const answer = await page.goto(statsPath(matchId));
    expect(answer?.status(), 'an untagged match has a stats page, not a not-found page').toBe(200);
    await expect(page.getByRole('heading', { level: 1 })).toContainText(/stats/i);
    await expect(page.getByText(STATE_COPY.empty).first()).toBeVisible();
    await expect(page.getByRole('link', { name: STATE_COPY.tagRallies })).toBeVisible();
    await expect(page.getByRole('button', { name: /Show me/ })).toHaveCount(0);
    await expect(page.getByText(/n = \d+/)).toHaveCount(0);
    await noSidewaysScroll(page);
    await expectNoBlockingA11yViolations(page, testInfo, `${SCREEN.dashboard}-empty`);
    await expectTargetsAtLeast24(page, testInfo, `${SCREEN.dashboard}-empty`);
  });

  // ---------------------------------------------------------------- loading
  test('E2E-03-08 D-01 and E-01 loading: a busy region while the request is held, then the numbers', async ({ page }, testInfo) => {
    expect(PUBLISHED.length, 'no coach-reviewed metric (COACH-1)').toBeGreaterThan(0);
    const matchId = await receivedMatch(page, 'E2E-03-08 loading');
    await tagWorkedExampleByApi(page, matchId);

    const stats = await hold(page, statsApi(matchId));
    await page.goto(statsPath(matchId));
    await expect(loadingRegion(page)).toBeVisible();
    expect(stats.seen(), 'D-01 never asked the API for its numbers in the browser').toBeGreaterThan(0);
    await expect(page.getByRole('button', { name: /Show me/ })).toHaveCount(0);
    await expectNoBlockingA11yViolations(page, testInfo, `${SCREEN.dashboard}-loading`);
    await expectTargetsAtLeast24(page, testInfo, `${SCREEN.dashboard}-loading`);
    stats.release();
    await expect(page.getByRole('heading', { name: firstCardName(), exact: true })).toBeVisible();
    await expect(page.locator('main [aria-busy="true"]')).toHaveCount(0);

    const evidence = await hold(page, evidenceApi(matchId));
    await metricCard(page, PUBLISHED[0]?.id ?? '').getByRole('button', { name: /Show me/ }).first().click();
    await expect(loadingRegion(page)).toBeVisible();
    expect(evidence.seen(), 'E-01 never asked the API for its rallies in the browser').toBeGreaterThan(0);
    await expectNoBlockingA11yViolations(page, testInfo, `${SCREEN.evidence}-loading`);
    await expectTargetsAtLeast24(page, testInfo, `${SCREEN.evidence}-loading`);
    evidence.release();
    await expect(page.getByRole('link', { name: /Rally \d+/ }).first()).toBeVisible();
    await expect(page.locator('main [aria-busy="true"]')).toHaveCount(0);
  });
});
