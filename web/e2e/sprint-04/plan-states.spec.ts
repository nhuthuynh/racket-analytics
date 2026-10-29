// E2E-04-02 P-01 plan states (ST-065; flows-sprint-04 §2 table, §3, §4): empty, limited data,
// loading, error and not found, each with axe (0 serious/critical, NFR-027) and the 24x24 target
// check (NFR-028). Loading and error hold or fail the browser's own plan read with page.route, so
// service workers are blocked here (e2e_route_isolation.feature); the offline states need the
// service worker and live in offline-done.spec.ts. Words: e2e/helpers/sprint-04.ts.
import { expect, test, type Page, type TestInfo } from '@playwright/test';
import { expectNoBlockingA11yViolations, expectTargetsAtLeast24 } from '../helpers/axe';
import { signInByLink } from '../helpers/sprint-01';
import { PLAN_COPY, PLAN_PATH, SCREEN_P, SWAPPABLE, answerPlanSetup, drillRow, planReadyAccount } from '../helpers/sprint-04';

test.use({ serviceWorkers: 'block' });

const PLAN_API = /\/api\/me\/plan$/;

async function checked(page: Page, testInfo: TestInfo, label: string): Promise<void> {
  await expectNoBlockingA11yViolations(page, testInfo, label);
  await expectTargetsAtLeast24(page, testInfo, label);
}

test.describe('@M0 @story-ST-065 Plan states', () => {
  test('E2E-04-02 empty: no plan yet, and P-02 without a tagged match says to tag one first', async ({ page }, testInfo) => {
    await signInByLink(page);
    await page.goto(PLAN_PATH);
    await expect(page.getByText(PLAN_COPY.noPlan)).toBeVisible();
    await expect(page.getByRole('link', { name: 'Your matches' })).toBeVisible();
    await checked(page, testInfo, `${SCREEN_P.plan}-empty`);

    await page.getByRole('link', { name: 'Make my plan' }).click();
    await answerPlanSetup(page);
    await page.getByRole('button', { name: 'Make my plan' }).click();
    const alert = page.getByRole('alert').filter({ hasText: PLAN_COPY.tagFirst });
    await expect(alert).toBeVisible();
    await expect(alert).toBeFocused();
    await expect(page.getByLabel('How long is each session?')).toHaveValue('30'); // answers kept
    await checked(page, testInfo, `${SCREEN_P.setup}-no-tagged-match`);
  });

  test('E2E-04-02 limited data: the banner names the rallies and every cited value says low sample', async ({ page }, testInfo) => {
    const { plan } = await planReadyAccount(page);
    expect(plan.limited_data, 'the worked example is limited data (FR-123)').not.toBeNull();
    await page.goto(PLAN_PATH);
    await expect(page.getByText(PLAN_COPY.limited(plan.limited_data?.rallies ?? -1))).toBeVisible();
    const rows = page.locator('li[id^="drill-"]');
    await expect(rows.first()).toBeVisible();
    const lowSample = plan.sessions.flatMap((s) => s.assignments).filter((a) => a.citation?.low_sample).length;
    await expect(page.locator('li[id^="drill-"] .tag', { hasText: 'low sample' })).toHaveCount(lowSample);
    await checked(page, testInfo, `${SCREEN_P.plan}-limited`);
  });

  test('E2E-04-02 loading: a busy region while the plan read is held, then the plan', async ({ page }, testInfo) => {
    await planReadyAccount(page);
    let release: () => void = () => {};
    const held = new Promise<void>((done) => (release = done));
    await page.route(PLAN_API, async (route) => {
      if (route.request().method() !== 'GET') return route.continue();
      await held;
      await route.continue();
    });
    await page.goto(PLAN_PATH);
    const busy = page.locator('main [aria-busy="true"]');
    await expect(busy).toBeVisible();
    await expect(busy.getByRole('status')).toHaveText(PLAN_COPY.loading);
    await checked(page, testInfo, `${SCREEN_P.plan}-loading`);
    release();
    await expect(busy).toHaveCount(0);
    await expect(page.getByRole('heading', { level: 2, name: 'Your sessions' })).toBeVisible();
  });

  test('E2E-04-02 error: one alert with the reference, and "Try again" loads the plan', async ({ page }, testInfo) => {
    await planReadyAccount(page);
    const ref = 'ref_0123456789abcdef';
    await page.route(PLAN_API, (route) =>
      route.request().method() === 'GET'
        ? route.fulfill({ status: 503, contentType: 'application/json', body: JSON.stringify({ error: { code: 'unavailable', message: 'x', support_ref: ref } }) })
        : route.continue(),
    );
    await page.goto(PLAN_PATH);
    const alert = page.getByRole('main').getByRole('alert'); // not Next's route announcer
    await expect(alert).toContainText(PLAN_COPY.error);
    await expect(alert).toContainText(`Reference: ${ref}`);
    await checked(page, testInfo, `${SCREEN_P.plan}-error`);
    await page.unroute(PLAN_API);
    await page.getByRole('button', { name: 'Try again' }).click();
    await expect(page.getByRole('heading', { level: 2, name: 'Your sessions' })).toBeVisible();
    await expect(page.getByRole('main').getByRole('alert')).toHaveCount(0);
  });

  test('E2E-04-02 not found: a drill gone on another device re-reads the plan; an unknown sub-route is not found', async ({ page }, testInfo) => {
    await planReadyAccount(page);
    await page.route(/\/api\/me\/plan\/assignments\/[^/]+\/swap$/, (route) =>
      route.fulfill({ status: 404, contentType: 'application/json', body: JSON.stringify({ error: { code: 'not_found', message: 'x' } }) }),
    );
    await page.goto(PLAN_PATH);
    await drillRow(page, SWAPPABLE).getByRole('button', { name: `Not for me, ${SWAPPABLE}` }).click();
    await page.getByRole('dialog').getByRole('button', { name: 'Swap drill' }).click();
    await expect(page.getByRole('dialog')).toHaveCount(0);
    await expect(page.getByRole('status').filter({ hasText: PLAN_COPY.changed })).toBeVisible();
    await expect(drillRow(page, SWAPPABLE)).toBeVisible(); // the current plan, read again
    await checked(page, testInfo, `${SCREEN_P.plan}-not-found`);

    await page.goto(`${PLAN_PATH}/no-such-page`);
    await expect(page.getByRole('heading', { level: 1, name: 'Page not found' })).toBeVisible();
    await checked(page, testInfo, `${SCREEN_P.plan}-unknown-route`);
  });
});
