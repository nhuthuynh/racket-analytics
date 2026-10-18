// @vitest-environment node
// Service worker plan cache (ST-063c; flows-sprint-04 §2 P-01 Offline; NFR-067). Only the plan
// page shell (`/plan`) and the last `GET /api/me/plan` answer are kept, in their own cache, network
// first; nothing else of the API or of the pages is stored, and sign-out clears the plan cache.
// Negative first: offline with nothing kept is a network error, never a made-up plan.
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import vm from 'node:vm';
import { describe, expect, it, vi } from 'vitest';
import { clearClientData } from '@/lib/session/clear';

const testDir = path.dirname(fileURLToPath(import.meta.url));
const source = readFileSync(path.join(testDir, '../../public/sw.js'), 'utf8');
const ORIGIN = 'https://app.example';
const PLAN_CACHE = 'ra-plan-v1';

type Listener = (event: unknown) => void;

/** A Cache Storage with real Responses, keyed by cache name and URL. */
function fakeCaches(seed: Record<string, Record<string, Response>> = {}) {
  const store = new Map<string, Map<string, Response>>(
    Object.entries(seed).map(([name, entries]) => [name, new Map(Object.entries(entries))]),
  );
  const key = (r: string | { url: string }) => (typeof r === 'string' ? new URL(r, ORIGIN).href : r.url);
  const open = async (name: string) => {
    if (!store.has(name)) store.set(name, new Map());
    const c = store.get(name)!;
    return {
      match: async (r: string | { url: string }) => c.get(key(r))?.clone(),
      put: async (r: string | { url: string }, res: Response) => void c.set(key(r), res),
      delete: async (r: string | { url: string }) => c.delete(key(r)),
      addAll: async () => undefined,
      keys: async () => [...c.keys()].map((url) => ({ url })),
    };
  };
  return {
    store,
    api: {
      open,
      keys: async () => [...store.keys()],
      delete: async (name: string) => store.delete(name),
      match: async (r: string) => {
        for (const c of store.values()) {
          const hit = c.get(key(r));
          if (hit) return hit.clone();
        }
        return undefined;
      },
    },
  };
}

function loadWorker(caches: unknown, fetch: unknown) {
  const listeners: Record<string, Listener> = {};
  const self = {
    location: { origin: ORIGIN },
    addEventListener: (type: string, fn: Listener) => {
      listeners[type] = fn;
    },
    skipWaiting: () => Promise.resolve(),
    clients: { claim: () => Promise.resolve() },
  };
  vm.runInNewContext(source, { self, URL, caches, fetch, Response, Headers, Date });
  return listeners;
}

function request(url: string, mode = 'cors', method = 'GET') {
  return { url, method, mode, headers: { has: () => false } };
}

async function dispatch(listeners: Record<string, Listener>, req: ReturnType<typeof request>) {
  let response: Promise<Response> | undefined;
  listeners.fetch!({ request: req, respondWith: (r: Promise<Response>) => (response = r) });
  return response;
}

const planJson = () =>
  new Response(JSON.stringify({ id: 'p1' }), { status: 200, headers: { 'content-type': 'application/json' } });

describe('service worker plan cache (negative first)', () => {
  it('offline with no plan kept: the plan read is a network error', async () => {
    const c = fakeCaches();
    const sw = loadWorker(c.api, () => Promise.reject(new TypeError('offline')));
    const response = await dispatch(sw, request(`${ORIGIN}/api/me/plan`));
    expect(response).toBeDefined();
    expect((await response!).type).toBe('error');
  });

  it('leaves every other API call to the network, including the plan commands', async () => {
    const sw = loadWorker(fakeCaches().api, vi.fn());
    expect(await dispatch(sw, request(`${ORIGIN}/api/me/plan/sessions/s1/done`, 'cors', 'POST'))).toBeUndefined();
    expect(await dispatch(sw, request(`${ORIGIN}/api/me/plan`, 'cors', 'POST'))).toBeUndefined();
    expect(await dispatch(sw, request(`${ORIGIN}/api/matches`))).toBeUndefined();
  });

  it('keeps the last plan read and answers with it offline, saying when it was kept', async () => {
    const c = fakeCaches();
    let up = true;
    const sw = loadWorker(c.api, () => (up ? Promise.resolve(planJson()) : Promise.reject(new TypeError('offline'))));
    expect((await (await dispatch(sw, request(`${ORIGIN}/api/me/plan`)))!).status).toBe(200);
    up = false;
    const offline = await (await dispatch(sw, request(`${ORIGIN}/api/me/plan`)))!;
    expect(await offline.json()).toEqual({ id: 'p1' });
    expect(Number.isNaN(Date.parse(offline.headers.get('x-ra-offline-copy') ?? ''))).toBe(false);
  });

  it('a refused plan read (401, 404) removes the kept plan', async () => {
    const c = fakeCaches({ [PLAN_CACHE]: { [`${ORIGIN}/api/me/plan`]: planJson() } });
    const sw = loadWorker(c.api, () => Promise.resolve(new Response('{}', { status: 401 })));
    expect((await (await dispatch(sw, request(`${ORIGIN}/api/me/plan`)))!).status).toBe(401);
    expect(c.store.get(PLAN_CACHE)!.size).toBe(0);
  });

  it('a server error (5xx) is passed on and keeps the kept plan', async () => {
    const c = fakeCaches({ [PLAN_CACHE]: { [`${ORIGIN}/api/me/plan`]: planJson() } });
    const sw = loadWorker(c.api, () => Promise.resolve(new Response('{}', { status: 502 })));
    expect((await (await dispatch(sw, request(`${ORIGIN}/api/me/plan`)))!).status).toBe(502);
    expect(c.store.get(PLAN_CACHE)!.size).toBe(1);
  });

  it('keeps the /plan shell and serves it to an offline navigation', async () => {
    const c = fakeCaches();
    let up = true;
    const sw = loadWorker(c.api, () =>
      up ? Promise.resolve(new Response('<h1>Your training plan</h1>', { status: 200 })) : Promise.reject(new TypeError('offline')),
    );
    await (await dispatch(sw, request(`${ORIGIN}/plan`, 'navigate')))!;
    up = false;
    expect(await (await dispatch(sw, request(`${ORIGIN}/plan`, 'navigate')))!.text()).toBe('<h1>Your training plan</h1>');
  });

  it('still stores no other page', async () => {
    const c = fakeCaches();
    const sw = loadWorker(c.api, () => Promise.resolve(new Response('<h1>Matches</h1>', { status: 200 })));
    await (await dispatch(sw, request(`${ORIGIN}/matches`, 'navigate')))!;
    expect(c.store.get(PLAN_CACHE)?.size ?? 0).toBe(0);
  });

  it('activate keeps the plan cache and the static cache, and drops old ones', async () => {
    const c = fakeCaches({ [PLAN_CACHE]: {}, 'ra-static-v1': {}, 'ra-static-v0': {} });
    const sw = loadWorker(c.api, vi.fn());
    let done: Promise<unknown> | undefined;
    sw.activate!({ waitUntil: (p: Promise<unknown>) => (done = p) });
    await done;
    expect([...c.store.keys()].sort()).toEqual([PLAN_CACHE, 'ra-static-v1']);
  });

  it('sign-out clears the plan cache (no plan survives on the device)', async () => {
    const c = fakeCaches({ [PLAN_CACHE]: { [`${ORIGIN}/api/me/plan`]: planJson() } });
    await clearClientData({ caches: c.api });
    expect(c.store.has(PLAN_CACHE)).toBe(false);
  });
});
