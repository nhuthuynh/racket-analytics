// E2E-04-03 offline "Mark done" survives a reload (ST-065; flows-sprint-04 §2 P-01 Offline, §4).
// The op waits in the device outbox (IndexedDB): after a reload while offline the session still
// says "Saved on this device, will sync"; back online it syncs once. No page.route here: the
// service worker must see every request (e2e_route_isolation.feature). "Mark done" is pressed
// under context.setOffline; the reload cannot be (decisions/ST-065.md: WebKit's emulation fails
// every load before the service worker, Chromium's skips it), so for the reload the device
// reports itself offline (navigator.onLine false) while the page loads, in every browser.
import { expect, test, type Page } from '@playwright/test';
import { PLAN_COPY, PLAN_PATH, planRead, planReadyAccount, sessionOf, untilPlanKeptOffline } from '../helpers/sprint-04';

const OFFLINE_FLAG = 'e2e-device-offline';

/** navigator.onLine is false while sessionStorage holds the flag; otherwise the browser's own. */
function deviceReportsOffline(flag: string): void {
  const own = Object.getOwnPropertyDescriptor(Navigator.prototype, 'onLine')!.get!;
  Object.defineProperty(Navigator.prototype, 'onLine', {
    configurable: true,
    get(this: Navigator) {
      return sessionStorage.getItem(flag) === '1' ? false : own.call(this);
    },
  });
}

async function setDeviceOffline(page: Page, offline: boolean): Promise<void> {
  await page.evaluate(([flag, off]) => {
    if (off) return sessionStorage.setItem(flag, '1');
    sessionStorage.removeItem(flag);
    window.dispatchEvent(new Event('online'));
  }, [OFFLINE_FLAG, offline] as const);
}

test.describe('@M0 @story-ST-065 Offline done', () => {
  test('E2E-04-03 a session marked done offline survives a reload and syncs once back online', async ({ page, context }) => {
    await planReadyAccount(page);
    await page.addInitScript(deviceReportsOffline, OFFLINE_FLAG);
    await page.goto(PLAN_PATH);
    await untilPlanKeptOffline(page);

    await context.setOffline(true);
    await sessionOf(page, 1).getByRole('button', { name: 'Mark done' }).click();
    await expect(sessionOf(page, 1).getByText(PLAN_COPY.queued)).toBeVisible();

    await setDeviceOffline(page, true);
    await context.setOffline(false); // the "online" event finds the device still offline: no sync
    await page.reload();
    await expect(page.getByRole('heading', { level: 2, name: 'Your sessions' })).toBeVisible();
    await expect(sessionOf(page, 1).getByText(PLAN_COPY.queued)).toBeVisible();
    await expect(sessionOf(page, 2).getByRole('button', { name: 'Mark done' })).toBeVisible();
    expect(await page.evaluate(() => navigator.onLine)).toBe(false);
    expect((await planRead(page)).sessions.some((s) => s.done)).toBe(false); // nothing sent yet

    await setDeviceOffline(page, false);
    await expect(page.getByRole('status').filter({ hasText: PLAN_COPY.synced(1) })).toBeVisible({ timeout: 15_000 });
    await expect(sessionOf(page, 1).getByText('Done', { exact: true })).toBeVisible();
    const plan = await planRead(page);
    expect(plan.sessions.map((s) => s.done)).toEqual(plan.sessions.map((_, i) => i === 0));
  });
});
