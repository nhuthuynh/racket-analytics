// Binds web/tests/features/plan_not_for_me_ui.feature (ST-063c; FR-124). Each scenario below is
// named as in the feature file, and the first test checks that the two lists match, so a scenario
// added to the file without a binding fails here. The API is a fake at the follow-through client's port.
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { PlanView } from '@/components/plan/PlanView';
import { parsePlan } from '@/lib/api/plan';
import type { FollowThroughApi } from '@/lib/plan-outbox-api';
import { planBody } from '../unit/fixtures/plan';

const FEATURE = readFileSync(
  path.join(path.dirname(fileURLToPath(import.meta.url)), 'plan_not_for_me_ui.feature'),
  'utf8',
);
const SCENARIOS = {
  noAlternative: 'No other drill fits',
  swap: 'Swap a drill',
};
let online: boolean;

beforeEach(() => {
  online = true;
  vi.spyOn(navigator, 'onLine', 'get').mockImplementation(() => online);
});

function followApi(over: Partial<FollowThroughApi> = {}): FollowThroughApi {
  return {
    markDone: vi.fn(async () => ({ kind: 'done' as const, planVersion: 2, replayed: false })),
    undoDone: vi.fn(async () => ({ kind: 'undone' as const, planVersion: 3 })),
    swap: vi.fn(async () => ({ kind: 'no_alternative' as const })),
    ...over,
  };
}

// Given a plan whose first session is "Session 1 of 3" with the drill "Serve to a target"
async function givenPlan(api: FollowThroughApi) {
  const getPlan = vi.fn(async () => ({ kind: 'plan' as const, plan: parsePlan(planBody()) }));
  render(<PlanView api={{ getPlan }} followApi={api} evidenceApi={{ stats: vi.fn(), evidence: vi.fn() }} />);
  await screen.findByText('Serve to a target');
  return { getPlan };
}

async function notForMe(reason = '') {
  const user = userEvent.setup();
  await user.click(screen.getByRole('button', { name: 'Not for me, Serve to a target' }));
  const dialog = screen.getByRole('dialog', { name: 'Swap Serve to a target?' });
  if (reason) await user.type(within(dialog).getByLabelText('Why not? (optional)'), reason);
  await user.click(within(dialog).getByRole('button', { name: 'Swap drill' }));
  return dialog;
}

describe('Feature: Swapping a drill, on the plan page', () => {
  it('binds every scenario of the feature file', () => {
    const inFile = [...FEATURE.matchAll(/^\s*Scenario: (.+)$/gm)].map((m) => m[1]!.trim()).sort();
    expect(inFile).toEqual(Object.values(SCENARIOS).sort());
  });

  it(`Scenario: ${SCENARIOS.noAlternative}`, async () => {
    const api = followApi();
    const { getPlan } = await givenPlan(api);
    const dialog = await notForMe('too hard');
    expect(
      await within(dialog).findByText('No other drill fits your setup for this. Your plan is unchanged.'),
    ).toBeVisible();
    expect(api.swap).toHaveBeenCalledWith('00000000-0000-4000-8000-000000000102', 'too hard');
    // And the plan still has "Serve to a target": its row is unchanged and the plan was not read again
    const row = screen.getByRole('button', { name: 'Not for me, Serve to a target' }).closest('li')!;
    expect(within(row).getByText('Serve to a target', { selector: 'strong' })).toBeVisible();
    expect(getPlan).toHaveBeenCalledTimes(1);
  });

  it(`Scenario: ${SCENARIOS.swap}`, async () => {
    const s = (planBody().sessions as Record<string, unknown>[])[0]!;
    const row = (s.assignments as Record<string, unknown>[])[0]!;
    row.drill = { id: 'pb.wall.serve-deep', version: 1, name: 'Deep serves', players: 1, needs: ['wall'], skills: ['serve'] };
    const swapped = parsePlan({ ...planBody(), sessions: [s] }).sessions[0]!;
    const api = followApi({ swap: vi.fn(async () => ({ kind: 'swapped' as const, session: swapped, planVersion: 2 })) });
    await givenPlan(api);
    await notForMe();
    const item = (await screen.findByText('Deep serves')).closest('li')!;
    await waitFor(() => expect(item).toHaveFocus());
    expect(screen.getByText('Swapped for Deep serves.')).toBeVisible();
    expect(screen.queryByRole('dialog')).toBeNull();
    expect(within(item).queryByText('Serve to a target')).toBeNull();
    expect(api.swap).toHaveBeenCalledWith('00000000-0000-4000-8000-000000000102', '');
  });
});
