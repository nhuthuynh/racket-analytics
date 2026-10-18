// @vitest-environment node
// Service worker plan cache (ST-063c; flows-sprint-04 §2 P-01 Offline; NFR-067). Only the plan
// page shell (`/plan`) and the last `GET /api/me/plan` answer are kept, in their own cache, network
// first; nothing else of the API or of the pages is stored, and sign-out clears the plan cache.
// Negative first: offline with nothing kept is a network error, never a made-up plan.
import { describe, expect, it, vi } from 'vitest';
import { clearClientData } from '@/lib/session/clear';
import { ORIGIN, PLAN_CACHE, dispatch, fakeCaches, loadWorker, request } from './fixtures/sw';

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

describe('service worker plan cache: storage failures never break the page (review PE-1)', () => {
  const quota = () => new DOMException('quota', 'QuotaExceededError');
  const page = () => new Response('<h1>Your training plan</h1>', { status: 200 });

  it.each([
    ['put', 'plan read', `${ORIGIN}/api/me/plan`, 'cors', planJson, 200],
    ['put', '/plan navigation', `${ORIGIN}/plan`, 'navigate', page, 200],
    ['open', 'plan read', `${ORIGIN}/api/me/plan`, 'cors', planJson, 200],
    ['delete', 'refused plan read', `${ORIGIN}/api/me/plan`, 'cors', () => new Response('{}', { status: 401 }), 401],
  ] as const)('a failing cache %s still passes the network answer of the %s on', async (call, _what, url, mode, net, status) => {
    const sw = loadWorker(fakeCaches({}, { [call]: quota() }).api, () => Promise.resolve(net()));
    expect((await (await dispatch(sw, request(url, mode)))!).status).toBe(status);
  });

  it('offline with a failing cache read: the plan read is a network error, the navigation the offline page', async () => {
    const offline = () => Promise.reject(new TypeError('offline'));
    const api = loadWorker(fakeCaches({}, { match: quota() }).api, offline);
    expect((await (await dispatch(api, request(`${ORIGIN}/api/me/plan`)))!).type).toBe('error');
    const kept = { 'ra-static-v1': { [`${ORIGIN}/offline.html`]: new Response('You are offline') } };
    const nav = loadWorker(fakeCaches(kept, { open: quota() }).api, offline);
    expect(await (await dispatch(nav, request(`${ORIGIN}/plan`, 'navigate')))!.text()).toBe('You are offline');
  });
});
