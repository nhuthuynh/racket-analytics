// Binds web/tests/features/drill_rationale_ui.feature (ST-063a; FR-122). Each scenario below is
// named as in the feature file, and the first test checks that the two lists match, so a scenario
// added to the file without a binding fails here.
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { PlanView } from '@/components/plan/PlanView';
import { parsePlan } from '@/lib/api/plan';
import { MATCH_ID, RALLY_ID, planBody, withFirstAssignment } from '../unit/fixtures/plan';

const FEATURE = readFileSync(path.join(path.dirname(fileURLToPath(import.meta.url)), 'drill_rationale_ui.feature'), 'utf8');
const SCENARIOS = {
  missing: 'A drill whose citation is missing shows an error, not a blank',
  why: 'Why this drill, on the plan page',
  showMe: 'Show me the rallies behind the reason',
};

// Given a plan whose drill "Serve to a target" targets "serve faults" (Background; fixture).
function givenPlan(citationMissing = false) {
  return citationMissing ? withFirstAssignment((a) => { a.citation = null; }) : planBody();
}

// When the player opens their training plan
async function whenOpened(body: Record<string, unknown>) {
  const evidence = vi.fn(async () => ({
    metricId: 'AN-05', side: 'A' as const, total: 1, sheetVersion: 1, nextCursor: null,
    items: [{ number: 7, rally_id: RALLY_ID, game: 1, start_ms: 0, end_ms: 1 }],
  }));
  const getPlan = vi.fn(async () => ({ kind: 'plan' as const, plan: parsePlan(body) }));
  render(<PlanView api={{ getPlan }} evidenceApi={{ stats: vi.fn(), evidence }} />);
  await screen.findByText('Serve to a target');
  return { evidence };
}

function row(name: string): HTMLElement {
  const li = screen.getByText(name).closest('li');
  if (!li) throw new Error(`no row ${name}`);
  return li;
}

describe('Feature: Every drill says why, on the plan page', () => {
  it('binds every scenario of the feature file', () => {
    const inFile = [...FEATURE.matchAll(/^\s*Scenario: (.+)$/gm)].map((m) => m[1]!.trim()).sort();
    expect(inFile).toEqual(Object.values(SCENARIOS).sort());
  });

  it(`Scenario: ${SCENARIOS.missing}`, async () => {
    await whenOpened(givenPlan(true));
    expect(within(row('Serve to a target')).getByText('We could not show why this drill was chosen.')).toBeVisible();
    expect(within(row('Serve to a target')).queryByRole('button', { name: /^Show me/ })).toBeNull();
  });

  it(`Scenario: ${SCENARIOS.why}`, async () => {
    await whenOpened(givenPlan());
    expect(within(row('Serve to a target')).getByText('Why: Serve faults: 29% of 7 serves')).toBeVisible();
    expect(within(row('Serve to a target')).getByText('low sample')).toBeVisible();
  });

  it(`Scenario: ${SCENARIOS.showMe}`, async () => {
    const { evidence } = await whenOpened(givenPlan());
    await userEvent.click(screen.getByRole('button', { name: 'Show me the rallies behind Serve faults, 29%' }));
    expect(evidence).toHaveBeenCalledWith(MATCH_ID, 'AN-05', 'A');
    expect(await screen.findByRole('link', { name: /Rally 7/ })).toBeVisible();
  });
});
