// @vitest-environment node
// Binds web/tests/features/plan_offline_read.feature (ST-063c-part2-part2; P-01 Offline). The real
// service worker (public/sw.js) answers the real plan read (createPlanApi); only the network and
// the Cache Storage are fakes. The first test checks that every scenario in the file is bound.
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { offlineAsOf } from '@/components/plan/PlanViewWords';
import { createPlanApi, type PlanRead } from '@/lib/api/plan';
import { clearClientData } from '@/lib/session/clear';
import { ORIGIN, PLAN_CACHE, dispatch, fakeCaches, loadWorker, request } from '../unit/fixtures/sw';
import { planBody } from '../unit/fixtures/plan';

const FEATURE = readFileSync(path.join(path.dirname(fileURLToPath(import.meta.url)), 'plan_offline_read.feature'), 'utf8');
const SCENARIOS = {
  nothingKept: 'Offline with no plan kept, the plan cannot be read',
  kept: 'The last plan is read offline, saying when it was kept',
  fullStorage: 'A full device storage still shows the live plan',
  signOut: 'After sign-out the plan cannot be read offline',
};

/** A device: the worker, its caches, and a network that is up or down. */
function device(fail: Parameters<typeof fakeCaches>[1] = {}) {
  const caches = fakeCaches({}, fail);
  const net = { up: true };
  const network = async () => {
    if (!net.up) throw new TypeError('offline');
    return new Response(JSON.stringify(planBody()), { status: 200, headers: { 'content-type': 'application/json' } });
  };
  const sw = loadWorker(caches.api, network);
  // The page's fetch goes through the worker, as a controlled page's does.
  const viaWorker = async (url: string) => {
    const response = (await dispatch(sw, request(new URL(url, ORIGIN).href)))!;
    if (response.type === 'error') throw new TypeError('Failed to fetch');
    return response;
  };
  const api = createPlanApi({ baseUrl: `${ORIGIN}/api`, fetch: viaWorker as typeof fetch });
  const read = async (online: boolean): Promise<PlanRead> => ((net.up = online), api.getPlan());
  return { caches, read };
}

async function readOnlineAt(d: ReturnType<typeof device>, iso: string) {
  vi.useFakeTimers({ toFake: ['Date'] });
  vi.setSystemTime(new Date(iso));
  expect(await d.read(true)).toMatchObject({ kind: 'plan' });
  vi.useRealTimers();
}

afterEach(() => vi.useRealTimers());

describe('Feature: The last plan can be read offline', () => {
  it('binds every scenario of the feature file', () => {
    const inFile = [...FEATURE.matchAll(/^\s*Scenario: (.+)$/gm)].map((m) => m[1]!.trim()).sort();
    expect(inFile).toEqual(Object.values(SCENARIOS).sort());
  });

  it(`Scenario: ${SCENARIOS.nothingKept}`, async () => {
    const d = device();
    expect(await d.read(false)).toEqual({ kind: 'error', supportRef: null });
    expect(d.caches.store.get(PLAN_CACHE)?.size ?? 0).toBe(0);
  });

  it(`Scenario: ${SCENARIOS.kept}`, async () => {
    const d = device();
    await readOnlineAt(d, '2026-10-18T09:30:00Z');
    const read = await d.read(false);
    expect(read).toMatchObject({ kind: 'plan', plan: { id: planBody().id } });
    expect(offlineAsOf((read as { offlineAsOf: string }).offlineAsOf, 'UTC')).toBe('18 Oct 2026, 09:30');
  });

  it(`Scenario: ${SCENARIOS.fullStorage}`, async () => {
    const d = device({ put: new DOMException('quota', 'QuotaExceededError') });
    const read = await d.read(true);
    expect(read).toMatchObject({ kind: 'plan', plan: { id: planBody().id } });
    expect(read).not.toHaveProperty('offlineAsOf');
  });

  it(`Scenario: ${SCENARIOS.signOut}`, async () => {
    const d = device();
    await readOnlineAt(d, '2026-10-18T09:30:00Z');
    await clearClientData({ caches: d.caches.api });
    expect(await d.read(false)).toEqual({ kind: 'error', supportRef: null });
  });
});
