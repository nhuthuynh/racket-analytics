// Binds web/tests/features/plan_follow_through_ui.feature (ST-063c; FR-124). Each scenario below is
// named as in the feature file, and the first test checks that the two lists match, so a scenario
// added to the file without a binding fails here. The outbox is the real IndexedDB one
// (fake-indexeddb); the API is a fake at the follow-through client's port.
import 'fake-indexeddb/auto';
import { IDBFactory } from 'fake-indexeddb';
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { act, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { browserOutbox } from '@/components/plan/PlanFollowThrough';
import { PlanView } from '@/components/plan/PlanView';
import { parsePlan } from '@/lib/api/plan';
import { createOutbox, type Outbox } from '@/lib/plan-outbox';
import { idbOutboxStore } from '@/lib/plan-outbox-idb';
import type { FollowThroughApi } from '@/lib/plan-outbox-api';
import { planBody } from '../unit/fixtures/plan';

const FEATURE = readFileSync(
  path.join(path.dirname(fileURLToPath(import.meta.url)), 'plan_follow_through_ui.feature'),
  'utf8',
);
const SCENARIOS = {
  syncFails: 'Mark done offline, and the sync fails',
  twice: 'Mark done offline twice',
  blocked: 'Mark done when the browser blocks IndexedDB',
  undoFails: 'Undo of a done session fails',
};
const SESSION_1 = '00000000-0000-4000-8000-000000000010';

let online: boolean;
let outbox: Outbox;

beforeEach(() => {
  online = true;
  vi.spyOn(navigator, 'onLine', 'get').mockImplementation(() => online);
  outbox = createOutbox(idbOutboxStore(new IDBFactory()));
});
afterEach(() => vi.unstubAllGlobals());

function followApi(over: Partial<FollowThroughApi> = {}): FollowThroughApi {
  return {
    markDone: vi.fn(async () => ({ kind: 'done' as const, planVersion: 2, replayed: false })),
    undoDone: vi.fn(async () => ({ kind: 'undone' as const, planVersion: 3 })),
    swap: vi.fn(async () => ({ kind: 'no_alternative' as const })),
    ...over,
  };
}

// Given a plan whose first session is "Session 1 of 3" with the drill "Serve to a target"
async function givenPlan(api: FollowThroughApi, body = planBody()) {
  const getPlan = vi.fn(async () => ({ kind: 'plan' as const, plan: parsePlan(body) }));
  render(<PlanView api={{ getPlan }} followApi={api} outbox={outbox} evidenceApi={{ stats: vi.fn(), evidence: vi.fn() }} />);
  await screen.findByText('Serve to a target');
}

function session1(): HTMLElement {
  return screen.getByRole('region', { name: /^Session 1 of 3/ });
}

async function backOnline() {
  online = true;
  await act(async () => {
    window.dispatchEvent(new Event('online'));
  });
}

describe('Feature: Following the plan through, on the plan page', () => {
  it('binds every scenario of the feature file', () => {
    const inFile = [...FEATURE.matchAll(/^\s*Scenario: (.+)$/gm)].map((m) => m[1]!.trim()).sort();
    expect(inFile).toEqual(Object.values(SCENARIOS).sort());
  });

  it(`Scenario: ${SCENARIOS.syncFails}`, async () => {
    const api = followApi({ markDone: vi.fn(async () => ({ kind: 'failed' as const, supportRef: null })) });
    await givenPlan(api);
    online = false;
    await userEvent.setup().click(within(session1()).getByRole('button', { name: 'Mark done' }));
    await within(session1()).findByText('Saved on this device, will sync');
    await backOnline();
    expect(
      await within(session1()).findByText("We could not save 'done'. It stays on this device and will sync."),
    ).toBeVisible();
    expect(await outbox.pending()).toEqual([{ op_id: expect.any(String), session_id: SESSION_1 }]);
  });

  it(`Scenario: ${SCENARIOS.twice}`, async () => {
    const api = followApi();
    await givenPlan(api);
    online = false;
    const user = userEvent.setup();
    // Two presses before the row changes (a double tap): one op.
    await user.dblClick(within(session1()).getByRole('button', { name: 'Mark done' }));
    await within(session1()).findByText('Saved on this device, will sync');
    const ops = await outbox.pending();
    expect(ops).toHaveLength(1);
    expect(api.markDone).not.toHaveBeenCalled();
    await backOnline();
    expect(await screen.findByText('Session 1 synced.')).toBeVisible();
    expect(api.markDone).toHaveBeenCalledTimes(1);
    expect(api.markDone).toHaveBeenCalledWith(ops[0]);
    await waitFor(async () => expect(await outbox.pending()).toEqual([]));
    expect(within(session1()).getByText('Done')).toBeVisible();
  });

  it(`Scenario: ${SCENARIOS.blocked}`, async () => {
    // Given this browser blocks IndexedDB (storage blocked: open throws SecurityError)
    vi.stubGlobal('indexedDB', {
      open: () => {
        throw new DOMException('blocked', 'SecurityError');
      },
    });
    outbox = browserOutbox();
    const api = followApi();
    await givenPlan(api);
    await userEvent.setup().click(within(session1()).getByRole('button', { name: 'Mark done' }));
    expect(await within(session1()).findByText('Done')).toBeVisible();
    expect(api.markDone).toHaveBeenCalledTimes(1);
    expect(api.markDone).toHaveBeenCalledWith({ op_id: expect.any(String), session_id: SESSION_1 });
  });

  it(`Scenario: ${SCENARIOS.undoFails}`, async () => {
    // Given "Session 1 of 3" is done
    const body = planBody();
    (body.sessions as Record<string, unknown>[])[0]!.done = true;
    const api = followApi({ undoDone: vi.fn(async () => ({ kind: 'failed' as const, supportRef: null })) });
    await givenPlan(api, body);
    await userEvent.setup().click(within(session1()).getByRole('button', { name: 'Undo' }));
    expect(await within(session1()).findByRole('alert')).toHaveTextContent("We could not undo 'done'. Try again.");
    expect(within(session1()).getByText('Done')).toBeVisible();
    expect(api.undoDone).toHaveBeenCalledWith(SESSION_1);
  });
});
