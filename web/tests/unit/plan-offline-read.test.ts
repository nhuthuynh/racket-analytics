// The plan read of the service worker's kept copy (ST-063c-part2-part2; flows-sprint-04 §2 P-01
// Offline). public/sw.js stamps a plan answered from its cache with `x-ra-offline-copy: <ISO time>`;
// the client read turns it into `offlineAsOf`, and `offlineAsOf()` words that time for the page.
// Negative first: a live answer (no stamp) is never reported as an offline copy.
import { describe, expect, it } from 'vitest';
import { OFFLINE_COPY, createPlanApi } from '@/lib/api/plan';
import { offlineAsOf } from '@/components/plan/PlanViewWords';
import { planBody } from './fixtures/plan';

function apiAnswering(headers: Record<string, string>) {
  const fetch = async () =>
    new Response(JSON.stringify(planBody()), {
      status: 200,
      headers: { 'content-type': 'application/json', ...headers },
    });
  return createPlanApi({ baseUrl: 'https://app.example/api', fetch });
}

describe('plan read of the offline copy (negative first)', () => {
  it('a live answer has no offlineAsOf', async () => {
    const read = await apiAnswering({}).getPlan();
    expect(read.kind).toBe('plan');
    expect(read).not.toHaveProperty('offlineAsOf');
  });

  it('a kept copy carries the time the service worker stamped on it', async () => {
    const read = await apiAnswering({ [OFFLINE_COPY]: '2026-10-18T09:30:00.000Z' }).getPlan();
    expect(read).toMatchObject({ kind: 'plan', offlineAsOf: '2026-10-18T09:30:00.000Z' });
  });

  it('reads the same header name the service worker writes', () => {
    expect(OFFLINE_COPY).toBe('x-ra-offline-copy');
  });
});

describe('offlineAsOf words', () => {
  it('an unreadable time is shown as given, never as "Invalid Date"', () => {
    expect(offlineAsOf('not-a-time')).toBe('not-a-time');
  });

  it('words the kept time as a medium date and a short time', () => {
    expect(offlineAsOf('2026-10-18T09:30:00Z', 'UTC')).toBe('18 Oct 2026, 09:30');
  });
});
