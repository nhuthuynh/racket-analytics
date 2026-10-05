// Binds tests/features/sign_out.feature (ST-014; sprint-01 §7.1, §14.3.2; FR-011, NFR-067).
// Copy: flows A-05 and the "Your upload will stop" interruption. Red until ST-014.
import { expect, test, type Page } from '@playwright/test';
import { answerSetup, signInByLink } from '../helpers/sprint-01';

async function signOut(page: Page): Promise<void> {
  await page.getByRole('button', { name: /account/i }).click();
  await page.getByRole('menuitem', { name: 'Sign out' }).or(page.getByRole('button', { name: 'Sign out' })).first().click();
}

async function cachedMediaOrApi(page: Page): Promise<string[]> {
  return page.evaluate(async () => {
    const found: string[] = [];
    for (const name of await caches.keys()) {
      const cache = await caches.open(name);
      for (const request of await cache.keys()) {
        const response = await cache.match(request);
        const type = response?.headers.get('content-type') ?? '';
        if (type.startsWith('video/') || type.startsWith('application/json') || /\/api\//.test(request.url)) {
          found.push(request.url);
        }
      }
    }
    return found;
  });
}

test.describe('Signing out leaves nothing behind', () => {
  test('Shared device', async ({ page, context }) => {
    await signInByLink(page);
    await answerSetup(page, { format: 'Doubles', players: ['Ivy', 'Dana', 'Carlos', 'Sam'], me: 'Ivy' });
    await page.getByRole('button', { name: 'Create match and upload' }).click();
    await expect(page.getByText('Video received')).toBeVisible({ timeout: 60_000 });

    await signOut(page);
    await expect(page.getByRole('heading', { level: 1, name: 'You have signed out' })).toBeVisible();
    await context.setOffline(true);
    await page.goto('/').catch(() => undefined);
    await expect(page.getByText(/Doubles ·/)).toHaveCount(0);
    await expect(page.getByText('Video received')).toHaveCount(0);
    expect(await page.evaluate(() => localStorage.length + sessionStorage.length)).toBe(0);
    expect(await cachedMediaOrApi(page)).toEqual([]);
    await context.setOffline(false);
  });

  test('Upload in progress', async ({ page }) => {
    await signInByLink(page);
    await page.route('**/uploads/**', async (route) => {
      if (route.request().method() === 'PATCH') return; // hold the upload mid-way
      await route.continue();
    });
    await answerSetup(page, { format: 'Singles', players: ['Ivy', 'Carlos'], me: 'Ivy' });
    await page.getByRole('button', { name: 'Create match and upload' }).click();
    await expect(page.getByText('Uploading', { exact: true })).toBeVisible();

    await signOut(page);
    await expect(page.getByRole('heading', { level: 1, name: 'Your upload will stop' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Keep uploading' })).toBeFocused();
    await page.getByRole('button', { name: 'Keep uploading' }).click();
    await expect(page.getByText('Uploading', { exact: true })).toBeVisible();
  });

  test('Video watched, then signed out', async ({ page }) => {
    await signInByLink(page);
    await answerSetup(page, { format: 'Singles', players: ['Ivy', 'Carlos'], me: 'Ivy' });
    await page.getByRole('button', { name: 'Create match and upload' }).click();
    await expect(page.getByText('Video received')).toBeVisible({ timeout: 60_000 });
    const video = page.locator('video');
    if (await video.count()) await video.first().evaluate((v: HTMLVideoElement) => v.play().catch(() => undefined));

    await signOut(page);
    await expect(page.getByRole('heading', { level: 1, name: 'You have signed out' })).toBeVisible();
    expect(await cachedMediaOrApi(page)).toEqual([]);
  });
});
