/* Racket Analytics service worker (ST-010; NFR-067; AQS/STACK-04; api-sprint-00 §8).
 *
 * Cache rule: content-hashed build assets under /_next/static/ are cached, cache-first; the plan
 * page and the plan read are the one exception (below). Everything else goes straight to the
 * network and is never stored: pages (they depend on the
 * session), /api/* responses, uploads and any media file. Tests: tests/unit/service-worker.test.ts
 * and web/e2e/security-headers.spec.ts.
 *
 * Offline (ST-014, flows A-05): a navigation that cannot reach the network is answered with the
 * precached static /offline.html (the A-01 offline banner). It holds no account data, so it
 * survives sign-out; no other page is ever stored.
 *
 * Plan (ST-063c, flows-sprint-04 §2 P-01 Offline): the /plan page shell and the last
 * GET /api/me/plan answer are kept in their own cache, network first, so the plan can be read
 * offline. A refused plan read (401, 404, ...) removes the kept copy, a 5xx keeps it; sign-out
 * deletes the whole cache (lib/session/clear.ts). Tests: tests/unit/service-worker-plan.test.ts.
 */
const CACHE_NAME = 'ra-static-v1';
const PLAN_CACHE = 'ra-plan-v1';
const PLAN_PAGE = '/plan';
const PLAN_API = '/api/me/plan';
const OFFLINE_COPY = 'x-ra-offline-copy';
const OFFLINE_PAGE = '/offline.html';
const PRECACHE = [OFFLINE_PAGE, '/offline.css'];
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
  event.waitUntil(
    caches
      .open(CACHE_NAME)
      .then((cache) => cache.addAll(PRECACHE))
      .catch(() => undefined) // the offline page is a nicety; never block the update
      .then(() => self.skipWaiting()),
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(keys.filter((k) => k !== CACHE_NAME && k !== PLAN_CACHE).map((k) => caches.delete(k))),
      )
      .then(() => self.clients.claim()),
  );
});

/** Network first; a good answer is kept (stamped with when), a refused one (4xx: signed out,
 * no plan) removes the copy, a server error leaves it for the next offline read. */
function planNetworkFirst(request, fallback) {
  return caches.open(PLAN_CACHE).then((cache) =>
    fetch(request).then(
      async (response) => {
        if (response.ok && response.type !== 'opaque') {
          const headers = new Headers(response.headers);
          headers.set(OFFLINE_COPY, new Date().toISOString());
          const body = await response.clone().arrayBuffer();
          await cache.put(request, new Response(body, { status: response.status, headers }));
        } else if (response.status >= 400 && response.status < 500) {
          await cache.delete(request);
        }
        return response;
      },
      () => cache.match(request).then((kept) => kept || fallback()),
    ),
  );
}

function isPlanRequest(request, url) {
  return request.method === 'GET' && url.origin === self.location.origin;
}

self.addEventListener('fetch', (event) => {
  const request = event.request;
  const url = new URL(request.url);
  if (isPlanRequest(request, url) && url.pathname === PLAN_API && request.mode !== 'navigate') {
    event.respondWith(planNetworkFirst(request, () => Response.error()));
    return;
  }
  if (isPlanRequest(request, url) && url.pathname === PLAN_PAGE && request.mode === 'navigate') {
    event.respondWith(
      planNetworkFirst(request, () => caches.match(OFFLINE_PAGE).then((page) => page || Response.error())),
    );
    return;
  }
  if (request.mode === 'navigate' && request.method === 'GET') {
    event.respondWith(
      fetch(request).catch(() =>
        caches.match(OFFLINE_PAGE).then((page) => page || Response.error()),
      ),
    );
    return;
  }
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
