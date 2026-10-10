// E2E-03-09 dashboard and evidence states (ST-048, ST-047; FR-100, FR-103; NFR-027, NFR-028,
// NFR-033; PD-R1S3-03). The ST-048 card asks for "empty, loading, error and low-sample states;
// 360 px": low sample is E2E-03-03 (definitions.spec.ts). Here, on the stack under test:
// - D-01 empty: a match with its video received and no rally tagged says so and links to tagging;
// - D-01 and E-01 loading: while the API request is held, a busy region is shown, then the numbers;
// - D-01 and E-01 error: when the API request fails, an alert says so with "Try again", which
//   loads the numbers once the API answers again;
// - D-01 nothing published: the API answers with no metric (none coach-reviewed yet, FR-102); the
//   page says so in words, with no alert and no number;
// - "Show me" opens S-01 at the rally: a rally link of E-01 opens the score sheet with V-01 for that
//   rally, starting at its time; a play id that is no rally of the sheet opens no video.
// Binds tests/features/stats_dashboard_states.feature (ST-048; PE-R2-ST048-02, QA-048-R2-02).
// Every state is checked with axe (0 serious/critical, NFR-027) and the 24x24 target rule
// (NFR-028), and the empty and error states at 360 px without sideways scroll (NFR-033).
// UI assumptions (copy, roles, browser-side fetch): e2e/helpers/sprint-03.ts STATE_COPY.
import { expect, test, type Page, type Route } from '@playwright/test';
import { expectNoBlockingA11yViolations, expectTargetsAtLeast24 } from '../helpers/axe';
import { playableVideo, receivedMatch } from '../helpers/sprint-02';
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
      body: JSON.stringify({ error: { code: 'unavailable', message: 'Service unavailable.', support_ref: 'e2e-03-09' } }),
    });
  };
  await page.route(url, handler);
  return { restore: () => page.unroute(url, handler), seen: () => seen };
}

/** Answer every matching request with the real answer, but with no metric published. */
async function nothingPublished(page: Page, url: RegExp): Promise<{ seen: () => number }> {
  let seen = 0;
  await page.route(url, async (route: Route) => {
    seen += 1;
    const real = await route.fetch();
    const body = (await real.json()) as Record<string, unknown>;
    await route.fulfill({ response: real, json: { ...body, metrics: {} } });
  });
  return { seen: () => seen };
}

const firstCardName = (): string => METRIC_NAMES[PUBLISHED[0]?.id ?? ''] ?? '';

test.describe('@M0 @story-ST-048 @nfr-027 @nfr-028 Dashboard and evidence states', () => {
  // ---------------------------------------------------------------- negative cases first
  test('E2E-03-09 D-01 error: an alert with "Try again", no numbers; Try again loads them', async ({ page }, testInfo) => {
    expect(PUBLISHED.length, 'no coach-reviewed metric (COACH-1)').toBeGreaterThan(0);
    const matchId = await receivedMatch(page, 'E2E-03-09 D error');
    await tagWorkedExampleByApi(page, matchId);
    const failing = await fail(page, statsApi(matchId));
    await page.setViewportSize({ width: 360, height: 740 });
    await page.goto(statsPath(matchId));
    await expect(page.getByRole('heading', { level: 1 })).toContainText(/stats/i);
    const alert = page.getByRole('alert').filter({ hasText: STATE_COPY.error });
    await expect(alert).toBeVisible();
    expect(failing.seen(), 'D-01 never asked the API for its numbers in the browser').toBeGreaterThan(0);
    await expect(page.getByRole('button', { name: /Show me/ }), 'numbers shown although the request failed').toHaveCount(0);
    await expect(alert).not.toContainText(/e2e-03-09|unavailable|503/i); // fixed copy, no raw error
    await noSidewaysScroll(page);
    await expectNoBlockingA11yViolations(page, testInfo, `${SCREEN.dashboard}-error`);
    await expectTargetsAtLeast24(page, testInfo, `${SCREEN.dashboard}-error`);

    await failing.restore();
    await page.getByRole('button', { name: STATE_COPY.retry }).click();
    await expect(page.getByRole('heading', { name: firstCardName(), exact: true })).toBeVisible();
    await expect(page.getByRole('alert').filter({ hasText: STATE_COPY.error })).toHaveCount(0);
  });

  test('E2E-03-09 E-01 error: an alert with "Try again", no rally links; Try again lists them', async ({ page }, testInfo) => {
    expect(PUBLISHED.length, 'no coach-reviewed metric (COACH-1)').toBeGreaterThan(0);
    const matchId = await receivedMatch(page, 'E2E-03-09 E error');
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

  test('E2E-03-09 D-01 empty: no rally tagged yet, a link to tagging, no metric numbers', async ({ page }, testInfo) => {
    const matchId = await receivedMatch(page, 'E2E-03-09 empty');
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

  test('E2E-03-09 D-01 nothing published: says stats appear once the coach has checked them, no alert, no numbers', async ({ page }, testInfo) => {
    const matchId = await receivedMatch(page, 'E2E-03-09 nothing published');
    await tagWorkedExampleByApi(page, matchId);
    const answered = await nothingPublished(page, statsApi(matchId));
    await page.setViewportSize({ width: 360, height: 740 });
    await page.goto(statsPath(matchId));
    await expect(page.getByRole('heading', { level: 1 })).toContainText(/stats/i);
    await expect(page.getByText(STATE_COPY.nothingPublished)).toBeVisible();
    expect(answered.seen(), 'D-01 never asked the API for its numbers in the browser').toBeGreaterThan(0);
    await expect(page.getByRole('alert').filter({ hasText: STATE_COPY.error }), 'nothing published is not an error').toHaveCount(0);
    await expect(page.getByRole('button', { name: /Show me/ })).toHaveCount(0);
    await expect(page.getByText(/n = \d+/)).toHaveCount(0);
    await noSidewaysScroll(page);
    await expectNoBlockingA11yViolations(page, testInfo, `${SCREEN.dashboard}-nothing-published`);
    await expectTargetsAtLeast24(page, testInfo, `${SCREEN.dashboard}-nothing-published`);
  });

  test('E2E-03-09 S-01 opened with a play id that is no rally of the sheet opens no video', async ({ page }) => {
    const matchId = await receivedMatch(page, 'E2E-03-09 wrong play id');
    await tagWorkedExampleByApi(page, matchId);
    const asked: string[] = [];
    page.on('request', (r) => { if (/\/rallies\/[^/]+\/media/.test(r.url())) asked.push(r.url()); });
    await page.goto(`/matches/${matchId}/sheet?play=00000000-0000-4000-8000-000000000000`);
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
    await expect(page.getByRole('table').first()).toBeVisible();
    // S-01 asks for a rally's video on arrival only when the id is one of its rallies; wait until
    // the page is hydrated and quiet, so a wrong fallback would have asked by now.
    await page.waitForLoadState('networkidle');
    expect(asked, 'S-01 asked for a rally video although the play id is no rally of the sheet').toEqual([]);
    await expect(page.getByRole('heading', { name: /^Rally \d+ video$/ })).toHaveCount(0);
    await expect(page.locator('video')).toHaveCount(0);
  });

  // ---------------------------------------------------------------- loading
  test('E2E-03-09 D-01 and E-01 loading: a busy region while the request is held, then the numbers', async ({ page }, testInfo) => {
    expect(PUBLISHED.length, 'no coach-reviewed metric (COACH-1)').toBeGreaterThan(0);
    const matchId = await receivedMatch(page, 'E2E-03-09 loading');
    await tagWorkedExampleByApi(page, matchId);

    const stats = await hold(page, statsApi(matchId));
    await page.goto(statsPath(matchId));
    await expect(loadingRegion(page)).toBeVisible();
    // The route sees the request a moment after the page made it, so wait for it (no fixed sleep).
    await expect.poll(() => stats.seen(), { message: 'D-01 never asked the API for its numbers in the browser' }).toBeGreaterThan(0);
    await expect(page.getByRole('button', { name: /Show me/ })).toHaveCount(0);
    await expectNoBlockingA11yViolations(page, testInfo, `${SCREEN.dashboard}-loading`);
    await expectTargetsAtLeast24(page, testInfo, `${SCREEN.dashboard}-loading`);
    stats.release();
    await expect(page.getByRole('heading', { name: firstCardName(), exact: true })).toBeVisible();
    await expect(page.locator('main [aria-busy="true"]')).toHaveCount(0);

    const evidence = await hold(page, evidenceApi(matchId));
    await metricCard(page, PUBLISHED[0]?.id ?? '').getByRole('button', { name: /Show me/ }).first().click();
    await expect(loadingRegion(page)).toBeVisible();
    // The route sees the request a moment after the page made it, so wait for it (no fixed sleep).
    await expect.poll(() => evidence.seen(), { message: 'E-01 never asked the API for its rallies in the browser' }).toBeGreaterThan(0);
    await expectNoBlockingA11yViolations(page, testInfo, `${SCREEN.evidence}-loading`);
    await expectTargetsAtLeast24(page, testInfo, `${SCREEN.evidence}-loading`);
    evidence.release();
    await expect(page.getByRole('link', { name: /Rally \d+/ }).first()).toBeVisible();
    await expect(page.locator('main [aria-busy="true"]')).toHaveCount(0);
  });

  // ---------------------------------------------------------------- Show me opens S-01
  test('E2E-03-09 "Show me" then a rally opens S-01 with that rally\'s video, at its start', async ({ page }, testInfo) => {
    expect(PUBLISHED.length, 'no coach-reviewed metric (COACH-1)').toBeGreaterThan(0);
    const matchId = await receivedMatch(page, 'E2E-03-09 show me');
    await tagWorkedExampleByApi(page, matchId);
    await playableVideo(page);
    await page.goto(statsPath(matchId));
    await metricCard(page, PUBLISHED[0]?.id ?? '').getByRole('button', { name: /Show me/ }).first().click();
    const rally = page.getByRole('link', { name: /Rally \d+/ }).first();
    await expect(rally).toBeVisible();
    const words = (await rally.textContent()) ?? '';
    const [, number, clock] = /Rally (\d+) · game \d+ · (\d+:\d{2})/.exec(words) ?? [];
    expect(number, `rally link reads "${words}"`).toBeTruthy();
    const href = (await rally.getAttribute('href')) ?? '';
    expect(href).toMatch(new RegExp(`^/matches/${matchId}/sheet\\?play=[0-9a-f-]{36}$`));

    await rally.click();
    await expect(page).toHaveURL(new RegExp(`/matches/${matchId}/sheet\\?play=`));
    const video = page.getByRole('region', { name: `Rally ${number} video` });
    await expect(video).toBeVisible();
    await expect(video).toContainText(`Starts at ${clock}`);
    await expect
      .poll(() => page.evaluate(() => { const v = document.querySelector('video'); return v ? v.readyState : -1; }), { timeout: 15_000 })
      .toBeGreaterThanOrEqual(2);
    await expectNoBlockingA11yViolations(page, testInfo, 'S-01-from-show-me');
    await expectTargetsAtLeast24(page, testInfo, 'S-01-from-show-me');
  });
});
