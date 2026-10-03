/* Racket Analytics service worker (ST-010; NFR-067; AQS/STACK-04; api-sprint-00 §8).
 *
 * Cache rule: ONLY content-hashed build assets under /_next/static/ are cached, cache-first.
 * Everything else goes straight to the network and is never stored: pages (they depend on the
 * session), /api/* responses, uploads and any media file. Tests: tests/unit/service-worker.test.ts
 * and web/e2e/security-headers.spec.ts.
 */
const CACHE_NAME = 'ra-static-v1';
const MEDIA = /\.(mp4|mov|m4v|webm|mkv|avi|3gp)(\?|$)/i;

function isCacheable(request) {
  if (request.method !== 'GET') return false;
  if (request.headers.has('range')) return false;
  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return false;
  if (MEDIA.test(url.pathname)) return false;
  return url.pathname.startsWith('/_next/static/');
}

self.addEventListener('install', (event) => {
  event.waitUntil(self.skipWaiting());
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k))))
      .then(() => self.clients.claim()),
  );
});

self.addEventListener('fetch', (event) => {
  const request = event.request;
  if (!isCacheable(request)) return; // network only, nothing stored
  event.respondWith(
    caches.open(CACHE_NAME).then(async (cache) => {
      const hit = await cache.match(request);
      if (hit) return hit;
      const response = await fetch(request);
      const cacheControl = response.headers.get('cache-control') || '';
      if (response.ok && response.type === 'basic' && !/no-store|private/i.test(cacheControl)) {
        await cache.put(request, response.clone());
      }
      return response;
    }),
  );
});
