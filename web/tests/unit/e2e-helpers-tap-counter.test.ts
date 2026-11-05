// ST-080 (NFR-036.4; scorecard G05-05): the tap/key counter behind e2e/sprint-05/fix-call-taps.spec.ts.
// A fix counts each tap or key that acts; moving focus does not count. The planted 3-step path
// (docs/domain/fix-call-types.md §4: a CT-3 fix through a confirmation step) must be counted as 3
// and fail the budget of 2. The binding check keeps tests/features/fix_call_taps.feature and the
// spec together. Negative cases first.
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import type { Locator, Page, TestInfo } from '@playwright/test';
import { describe, expect, it, vi } from 'vitest';
import { readSpecs, scenariosOf, unboundScenarios } from '../../e2e/helpers/scenario-binding';
import { budgetProblem, countSteps, FIX_BUDGET, TapCounter, type Step } from '../../e2e/helpers/tap-counter';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const FEATURE = readFileSync(path.join(HERE, '../../../tests/features/fix_call_taps.feature'), 'utf8');
const SPRINT_05_DIR = path.join(HERE, '../../e2e/sprint-05');

/** The planted path: open "Change ending", press "Fault", then confirm (COACH-5 §4). */
const PLANTED: Step[] = [
  { kind: 'tap', what: 'Change ending, rally 2' },
  { kind: 'tap', what: 'Fault' },
  { kind: 'tap', what: 'Confirm the change' },
];

function fakePage() {
  const press = vi.fn(async () => {});
  return { page: { keyboard: { press } } as unknown as Page, press };
}

function fakeLocator() {
  const click = vi.fn(async () => {});
  return { locator: { click } as unknown as Locator, click };
}

describe('countSteps and budgetProblem (the planted 3-step path)', () => {
  it('counts the planted 3-step path as 3', () => {
    expect(countSteps(PLANTED)).toBe(3);
  });

  it('reports the planted path as over the budget of 2', () => {
    expect(FIX_BUDGET).toBe(2);
    expect(budgetProblem(countSteps(PLANTED))).toBe('3 taps or keys, over the budget of 2');
  });

  it('counts keys that act like taps, and never counts a move', () => {
    const steps: Step[] = [
      { kind: 'move', what: 'Tab' },
      { kind: 'key', what: 'Enter' },
      { kind: 'move', what: 'Tab' },
      { kind: 'move', what: 'ArrowDown' },
      { kind: 'key', what: 'Enter' },
    ];
    expect(countSteps(steps)).toBe(2);
    expect(budgetProblem(countSteps(steps))).toBeNull();
  });

  it('accepts 0, 1 and 2 steps and rejects every count above 2', () => {
    expect([0, 1, 2].map((n) => budgetProblem(n))).toEqual([null, null, null]);
    expect(budgetProblem(4)).toBe('4 taps or keys, over the budget of 2');
  });
});

describe('TapCounter (records what the spec does in the browser)', () => {
  it('refuses to record a key that acts as a move, so a fix cannot hide a step', async () => {
    const { page, press } = fakePage();
    const counter = new TapCounter(page);
    for (const key of ['Enter', ' ', 'z', 'f']) {
      await expect(counter.move(key), key).rejects.toThrow(`"${key}" is not a move`);
    }
    expect(press).not.toHaveBeenCalled();
    expect(counter.count).toBe(0);
  });

  it('counts a planted 3-tap detour as 3 and its budget check fails', async () => {
    const { page } = fakePage();
    const { locator, click } = fakeLocator();
    const counter = new TapCounter(page);
    await counter.tap(locator, 'Change player, rally 2');
    await counter.tap(locator, 'Change ending, rally 2');
    await counter.tap(locator, 'Fault');
    expect(click).toHaveBeenCalledTimes(3);
    expect(counter.count).toBe(3);
    expect(counter.problem()).toBe('3 taps or keys, over the budget of 2');
    expect(() => counter.expectWithinBudget()).toThrow(/over the budget of 2/);
  });

  it('presses keys and moves on the page; only the keys count', async () => {
    const { page, press } = fakePage();
    const counter = new TapCounter(page);
    await counter.key('Enter', 'open Change ending');
    await counter.move('Tab');
    await counter.move('Shift+Tab');
    await counter.move('ArrowRight');
    await counter.key('Enter', 'Fault');
    expect(press.mock.calls.map((c) => (c as unknown[])[0])).toEqual(['Enter', 'Tab', 'Shift+Tab', 'ArrowRight', 'Enter']);
    expect(counter.steps.map((s) => s.kind)).toEqual(['key', 'move', 'move', 'move', 'key']);
    expect(counter.count).toBe(2);
    expect(() => counter.expectWithinBudget()).not.toThrow();
  });

  it('annotates the count as a bare number under "taps" (the G05-05 jq reads it with tonumber)', async () => {
    const { page } = fakePage();
    const { locator } = fakeLocator();
    const info = { annotations: [] as { type: string; description?: string }[] } as unknown as TestInfo;
    const counter = new TapCounter(page);
    await counter.tap(locator, 'Switch winner, rally 2');
    counter.report(info, 'CT-1 by taps: Switch winner, rally 2');
    expect(info.annotations).toEqual([
      { type: 'taps', description: '1' },
      { type: 'fix', description: 'CT-1 by taps: Switch winner, rally 2 (1: tap Switch winner, rally 2)' },
    ]);
  });

  it('annotates a planted path under its own type, so it never raises the G05-05 maximum', async () => {
    const { page } = fakePage();
    const { locator } = fakeLocator();
    const info = { annotations: [] as { type: string; description?: string }[] } as unknown as TestInfo;
    const counter = new TapCounter(page);
    for (const what of ['a', 'b', 'c']) await counter.tap(locator, what);
    counter.report(info, 'planted CT-3 detour', 'planted-taps');
    expect(info.annotations.map((a) => a.type)).toEqual(['planted-taps', 'fix']);
    expect(info.annotations[0]?.description).toBe('3');
  });
});

describe('Feature binding: fix a call quickly (fix_call_taps.feature)', () => {
  it('reads the three scenarios, each tagged E2E-05-80', () => {
    expect(scenariosOf(FEATURE).map((s) => s.ids)).toEqual([['E2E-05-80'], ['E2E-05-80'], ['E2E-05-80']]);
  });

  it('every scenario is bound by a browser test titled with its id and name', () => {
    expect(unboundScenarios(FEATURE, readSpecs(SPRINT_05_DIR))).toEqual([]);
  });
});
