// NFR-067.2-.3 in the browser (ST-078e; G05-06 `PW_PROJECTS=chromium,webkit npx playwright test
// e2e/sprint-05/logout-hygiene.spec.ts`; AQS/SEC-05 14.3.1-14.3.3). Binds the sign-out rule of
// web/tests/features/client_hygiene.feature. No page.route: the service worker sees every request,
// so the caches listed after sign-out are the worker's real ones (W-01 WebKit family).
import { expect, test, type Page } from '@playwright/test';
import { signInByLink } from '../helpers/sprint-01';

const SEED = 'e2e-hygiene';
/** Paths sign-out may keep: content-hashed app files and the offline page (lib/session/clear.ts). */
const KEPT = /^\/(_next\/static\/|offline\.(html|css)$)/;
const MEDIA_PATH = /\.(mp4|mov|m4v|webm|mkv|avi|3gp|mp3|m4a|aac|wav|ogg|oga|ogv|opus|flac)$/i;

async function signOut(page: Page): Promise<void> {
  await page.getByRole('button', { name: /account/i }).click();
  await page.getByRole('menuitem', { name: 'Sign out' }).or(page.getByRole('button', { name: 'Sign out' })).first().click();
  await expect(page.getByRole('heading', { level: 1, name: 'You have signed out' })).toBeVisible();
}

/** Signed in, on a page the service worker controls. */
async function signedInAndControlled(page: Page): Promise<void> {
  await signInByLink(page);
  await page.goto('/matches');
  await page.evaluate(async () => {
    await navigator.serviceWorker.ready;
  });
  await page.reload();
  await expect.poll(() => page.evaluate(() => navigator.serviceWorker.controller !== null)).toBe(true);
}

/** Every Cache Storage entry: cache name, URL path and stored content type. */
async function cacheEntries(page: Page): Promise<{ cache: string; path: string; type: string }[]> {
  return page.evaluate(async () => {
    const found: { cache: string; path: string; type: string }[] = [];
    for (const cache of await caches.keys()) {
      const opened = await caches.open(cache);
      for (const request of await opened.keys()) {
        const response = await opened.match(request);
        found.push({ cache, path: new URL(request.url).pathname, type: response?.headers.get('content-type') ?? '' });
      }
    }
    return found;
  });
}

test.describe('@M5 @story-ST-078 Sign-out empties the device (NFR-067.2-.3)', () => {
  test('Sign-out empties local storage, session storage, IndexedDB and the account caches', async ({ page }) => {
    await signedInAndControlled(page);
    await page.evaluate(async (name) => {
      localStorage.setItem(name, 'Ivy');
      sessionStorage.setItem(name, 'Ivy');
      await new Promise<void>((resolve, reject) => {
        const open = indexedDB.open(name, 1);
        open.onupgradeneeded = () => open.result.createObjectStore('rows');
        open.onerror = () => reject(open.error);
        open.onsuccess = () => {
          const tx = open.result.transaction('rows', 'readwrite');
          tx.objectStore('rows').put({ player: 'Ivy' }, 1);
          tx.oncomplete = () => (open.result.close(), resolve());
        };
      });
      const plan = await caches.open('ra-plan-v1');
      await plan.put('/api/me/plan', new Response('{"plan":"Ivy"}', { headers: { 'content-type': 'application/json' } }));
    }, SEED);
    expect((await cacheEntries(page)).map((e) => e.path)).toContain('/api/me/plan'); // the seed took

    await signOut(page);

    expect(await page.evaluate(() => localStorage.length + sessionStorage.length)).toBe(0);
    const databases = await page.evaluate(async () => (await indexedDB.databases()).map((d) => d.name));
    expect(databases).toEqual([]);
    const left = await cacheEntries(page);
    expect(left.filter((e) => e.cache !== 'ra-static-v1' || !KEPT.test(e.path))).toEqual([]);
  });

  test('Sign-out removes media even from the app-file cache', async ({ page }) => {
    await signedInAndControlled(page);
    await page.evaluate(async () => {
      // What an older worker could have stored before the media rule covered this path.
      const shell = await caches.open('ra-static-v1');
      await shell.put('/_next/static/media/legacy.0a1b2c.mp4', new Response('not really video', { headers: { 'content-type': 'video/mp4' } }));
    });
    expect((await cacheEntries(page)).map((e) => e.path)).toContain('/_next/static/media/legacy.0a1b2c.mp4');

    await signOut(page);

    const media = (await cacheEntries(page)).filter((e) => MEDIA_PATH.test(e.path) || /^(video|audio)\//i.test(e.type));
    expect(media).toEqual([]);
  });
});
