// A device for ST-085 (FR-124.R3/.R4): the real public/sw.js (fixtures/sw.ts) in front of a fake
// network, with the real plan and follow-through HTTP clients fetching through it, as a controlled
// page does. Only the network and Cache Storage are fakes; every swap answers 409 no_alternative. The network can go down and come back,
// and a "Mark done" answer can be held, so a test can drop the connection while a send is in flight.
import { createPlanApi } from '@/lib/api/plan';
import { createFollowThroughApi } from '@/lib/plan-outbox-api';
import { ORIGIN, dispatch, fakeCaches, loadWorker, request } from './sw';
import { planBody } from './plan';

type Held = { release: () => void };

export function device() {
  const caches = fakeCaches();
  const net = { up: true, hold: false };
  const held: Held[] = [];
  /** Every "Mark done" POST that reached the API, by URL. */
  const doneRequests: string[] = [];

  const answerDone = () =>
    new Response(JSON.stringify({ plan_version: 2, replayed: false }), {
      status: 200,
      headers: { 'content-type': 'application/json' },
    });

  const network = async (req: { url: string; method: string }) => {
    if (!net.up) throw new TypeError('offline');
    const url = new URL(req.url);
    if (req.method === 'POST' && url.pathname.endsWith('/done')) {
      doneRequests.push(url.pathname);
      if (net.hold) await new Promise<void>((release) => held.push({ release }));
      return answerDone();
    }
    if (req.method === 'POST' && url.pathname.endsWith('/swap')) {
      return new Response(JSON.stringify({ error: { code: 'no_alternative' } }), { status: 409 });
    }
    if (req.method === 'GET' && url.pathname === '/api/me/plan') {
      return new Response(JSON.stringify(planBody()), { status: 200, headers: { 'content-type': 'application/json' } });
    }
    return new Response('{}', { status: 404 });
  };

  const sw = loadWorker(caches.api, network);

  /** The page's fetch: the worker answers what it handles, the rest goes to the network. */
  const viaWorker = async (input: string, init: { method?: string } = {}) => {
    const href = new URL(input, ORIGIN).href;
    const req = request(href, 'cors', init.method ?? 'GET');
    const answered = await dispatch(sw, req);
    if (answered === undefined) return network(req);
    const response = await answered;
    if (response.type === 'error') throw new TypeError('Failed to fetch');
    return response;
  };

  return {
    caches,
    net,
    doneRequests,
    /** Lets every held "Mark done" answer go. */
    releaseHeld: () => held.splice(0).forEach((h) => h.release()),
    planApi: createPlanApi({ baseUrl: `${ORIGIN}/api`, fetch: viaWorker as typeof fetch }),
    followApi: createFollowThroughApi({ baseUrl: `${ORIGIN}/api`, fetch: viaWorker as typeof fetch }),
  };
}
