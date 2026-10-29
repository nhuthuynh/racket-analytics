// E2E-04-03 offline "Mark done" survives a reload (ST-065; flows-sprint-04 §2 P-01 Offline, §4).
// The service worker keeps the /plan shell and the last plan read (public/sw.js, ST-063c) and the
// op waits in the device outbox (IndexedDB), so a reload while offline still shows the plan with
// the session "Saved on this device, will sync"; back online it syncs once.
// No page.route here: the service worker must see every request (e2e_route_isolation.feature).
// The "as of" line is not asserted: Chromium's offline emulation does not reach service-worker
// fetches, so there the reload is answered by the network (decisions/ST-065.md); the outbox is
// what must survive, and it is checked in every browser.
import { expect, test } from '@playwright/test';
import { PLAN_COPY, PLAN_PATH, planRead, planReadyAccount, sessionOf, untilPlanKeptOffline } from '../helpers/sprint-04';

test.describe('@M0 @story-ST-065 Offline done', () => {
  test('E2E-04-03 a session marked done offline survives a reload and syncs once back online', async ({ page, context }) => {
    await planReadyAccount(page);
    await page.goto(PLAN_PATH);
    await untilPlanKeptOffline(page);

    await context.setOffline(true);
    await sessionOf(page, 1).getByRole('button', { name: 'Mark done' }).click();
    await expect(sessionOf(page, 1).getByText(PLAN_COPY.queued)).toBeVisible();

    await page.reload();
    await expect(page.getByRole('heading', { level: 2, name: 'Your sessions' })).toBeVisible();
    await expect(sessionOf(page, 1).getByText(PLAN_COPY.queued)).toBeVisible();
    await expect(sessionOf(page, 2).getByRole('button', { name: 'Mark done' })).toBeVisible();
    expect(await page.evaluate(() => navigator.onLine)).toBe(false);

    await context.setOffline(false);
    await expect(page.getByRole('status').filter({ hasText: PLAN_COPY.synced(1) })).toBeVisible({ timeout: 15_000 });
    await expect(sessionOf(page, 1).getByText('Done', { exact: true })).toBeVisible();
    const plan = await planRead(page);
    expect(plan.sessions.map((s) => s.done)).toEqual(plan.sessions.map((_, i) => i === 0));
  });
});
