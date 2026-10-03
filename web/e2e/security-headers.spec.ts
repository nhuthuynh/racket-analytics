// IT-00-14, HTML part (NFR-061, NFR-067; AQS/STACK-04): security headers on HTML responses.
// The JSON and error parts are in backend/tests/integration/test_it_00_14_security_headers.py.
import { expect, test } from '@playwright/test';

for (const route of ['/', '/matches', '/this-page-does-not-exist']) {
  test(`@M0 @story-ST-010 security headers on ${route}`, async ({ request }) => {
    const response = await request.get(route, { maxRedirects: 0 });
    const headers = response.headers();

    expect(headers['x-content-type-options']).toBe('nosniff');
    expect(headers['x-frame-options']).toBe('DENY');
    expect(headers['content-security-policy'] ?? '').toContain("default-src 'self'");
    expect(headers['content-security-policy'] ?? '').toContain("frame-ancestors 'none'");
  });
}

test('@M0 @story-ST-010 the service worker never caches media or API responses', async ({
  page,
}) => {
  await page.goto('/');
  const cached = await page.evaluate(async () => {
    const urls: string[] = [];
    for (const name of await caches.keys()) {
      const cache = await caches.open(name);
      urls.push(...(await cache.keys()).map((r) => r.url));
    }
    return urls;
  });

  expect(cached.filter((u) => /\.(mp4|mov|webm)(\?|$)|\/api\/|\/matches\/|\/uploads\//.test(u))).toEqual([]);
});
