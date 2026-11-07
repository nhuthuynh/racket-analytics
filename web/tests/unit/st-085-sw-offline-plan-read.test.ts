// @vitest-environment node
// ST-085 (FR-124.R3/.R4 at the service-worker level; requirements-breakdown §2 "FR-124 offline
// part"): public/sw.js with a mocked network and Cache Storage. The kept plan is stamped with the
// device time of the online read that kept it (the page's "as of" line reads that stamp), and the
// worker never answers, keeps or replays a "Mark done": the page's outbox is the only sync queue,
// so the worker cannot add a second request. Negative first.
import { describe, expect, it, vi } from 'vitest';
import { OFFLINE_COPY } from '@/lib/api/plan';
import { ORIGIN, PLAN_CACHE, dispatch, fakeCaches, loadWorker, request } from './fixtures/sw';

const PLAN = `${ORIGIN}/api/me/plan`;
const DONE = `${ORIGIN}/api/me/plan/sessions/s1/done`;
const planJson = () =>
  new Response(JSON.stringify({ id: 'p1' }), { status: 200, headers: { 'content-type': 'application/json' } });

/** A worker over a network that is up or down. */
function worker(c = fakeCaches()) {
  const net = { up: true };
  const fetch = vi.fn(async () => {
    if (!net.up) throw new TypeError('offline');
    return planJson();
  });
  return { c, net, fetch, sw: loadWorker(c.api, fetch) };
}

async function readAt(w: ReturnType<typeof worker>, at: Date) {
  vi.useFakeTimers({ toFake: ['Date'] });
  vi.setSystemTime(at);
  try {
    return await (await dispatch(w.sw, request(PLAN)))!;
  } finally {
    vi.useRealTimers();
  }
}

describe('FR-124.R3 at the worker: the kept plan says when it was kept (negative first)', () => {
  it('offline with no plan kept: no made-up plan and no stamp, only a network error', async () => {
    const w = worker();
    w.net.up = false;
    const answer = await (await dispatch(w.sw, request(PLAN)))!;
    expect(answer.type).toBe('error');
    expect(answer.headers.get(OFFLINE_COPY)).toBeNull();
  });

  it('a live answer passed to the page carries no stamp (only the kept copy does)', async () => {
    const live = await readAt(worker(), new Date('2026-10-18T18:05:00Z'));
    expect(live.headers.get(OFFLINE_COPY)).toBeNull();
  });

  it('the offline answer is stamped with the time of the online read that kept it (18:05)', async () => {
    const w = worker();
    await readAt(w, new Date('2026-10-18T18:05:00Z'));
    w.net.up = false;
    const offline = await readAt(w, new Date('2026-10-18T21:40:00Z'));
    expect(await offline.json()).toEqual({ id: 'p1' });
    expect(offline.headers.get(OFFLINE_COPY)).toBe('2026-10-18T18:05:00.000Z');
  });

  it('a later online read replaces the stamp with its own time', async () => {
    const w = worker();
    await readAt(w, new Date('2026-10-18T18:05:00Z'));
    await readAt(w, new Date('2026-10-19T07:15:00Z'));
    w.net.up = false;
    expect((await readAt(w, new Date('2026-10-19T09:00:00Z'))).headers.get(OFFLINE_COPY)).toBe('2026-10-19T07:15:00.000Z');
  });
});

describe('FR-124.R4 at the worker: a "Mark done" is never queued or replayed by it (negative first)', () => {
  it('offline, the worker leaves the "done" POST to the network and keeps nothing of it', async () => {
    const w = worker();
    w.net.up = false;
    expect(await dispatch(w.sw, request(DONE, 'cors', 'POST'))).toBeUndefined();
    expect(w.fetch).not.toHaveBeenCalled();
    expect([...w.c.store.values()].every((cache) => cache.size === 0)).toBe(true);
  });

  it('when the connection drops and returns twice, the worker sends no "done" of its own', async () => {
    const w = worker();
    for (const up of [true, false, true, false, true]) {
      w.net.up = up;
      expect(await dispatch(w.sw, request(DONE, 'cors', 'POST'))).toBeUndefined();
      await (await dispatch(w.sw, request(PLAN)))!; // a plan read on each reconnect
    }
    const sent = w.fetch.mock.calls as unknown as [{ url: string; method: string }][];
    expect(sent.filter(([r]) => r.method === 'POST')).toEqual([]);
    expect([...w.c.store.get(PLAN_CACHE)!.keys()]).toEqual([PLAN]);
  });
});
