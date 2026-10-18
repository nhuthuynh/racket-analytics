// Binds web/tests/features/plan_preferences_ui.feature (ST-063b; FR-121 UI step) to the P-02
// component with a fake plan API. The first test keeps the binding honest: every scenario in the
// feature file has a test here with the same name, and no test binds a scenario that is not there.
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { PlanPreferences } from '@/components/plan/PlanPreferences';
import type { GenerateOutcome } from '@/components/plan/PlanPreferencesApi';
import type { PlanPreferences as Preferences } from '@/components/plan/PlanPreferencesModel';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const FEATURE = readFileSync(path.join(HERE, '../features/plan_preferences_ui.feature'), 'utf8');
const BOUND = [
  'Minutes outside 15 to 180 are refused before any request',
  'Without a tagged match she is sent to tag one and her answers stay',
  'Solo player with 30 minutes, 3 sessions a week and a wall',
  'Changing the setup starts from the last answers',
];

/** Given Ivy is on "Your practice setup" (first visit when `last` is null). */
function ivyOnPracticeSetup(outcome: GenerateOutcome, last: Preferences | null = null) {
  const generatePlan = vi.fn(async () => outcome);
  const navigate = vi.fn();
  render(<PlanPreferences initial={last} api={{ generatePlan }} navigate={navigate} />);
  return { generatePlan, navigate, user: userEvent.setup() };
}

/** When she enters <m> minutes per session and answers the other questions (solo, 3 a week, a wall, intermediate). */
async function sheEntersAndAnswers(user: ReturnType<typeof userEvent.setup>, minutes: string) {
  await user.type(screen.getByLabelText('How long is each session?'), minutes);
  await user.click(within(screen.getByRole('group', { name: 'How many sessions a week?' })).getByLabelText('3'));
  await user.click(within(screen.getByRole('group', { name: 'How many players, including you?' })).getByLabelText('1'));
  await user.click(screen.getByLabelText('A wall'));
  await user.click(screen.getByLabelText('Intermediate'));
  await user.click(screen.getByRole('button', { name: 'Make my plan' }));
}

describe('Feature: The player tells the app her practice setup and asks for a plan', () => {
  it('binds every scenario of the feature file, and only those', () => {
    const scenarios = [...FEATURE.matchAll(/^\s*Scenario: (.+)$/gm)].map((m) => m[1]!.trim());
    expect(scenarios).toEqual(BOUND);
  });

  it(`Scenario: ${BOUND[0]}`, async () => {
    const { generatePlan, user } = ivyOnPracticeSetup({ kind: 'created' });
    await sheEntersAndAnswers(user, '10');
    expect(within(screen.getByRole('alert')).getByRole('link', { name: 'Enter a number between 15 and 180' })).toBeVisible();
    expect(generatePlan).not.toHaveBeenCalled();
  });

  it(`Scenario: ${BOUND[1]}`, async () => {
    const { user, navigate } = ivyOnPracticeSetup({ kind: 'no_tagged_match' });
    await sheEntersAndAnswers(user, '30');
    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent('Tag a match first. Your plan is built from the rallies you tag.');
    expect(within(alert).getByRole('link', { name: 'Your matches' })).toHaveAttribute('href', '/matches');
    expect(screen.getByLabelText('How long is each session?')).toHaveValue('30');
    expect(screen.getByLabelText('A wall')).toBeChecked();
    expect(navigate).not.toHaveBeenCalled();
  });

  it(`Scenario: ${BOUND[2]}`, async () => {
    const { generatePlan, navigate, user } = ivyOnPracticeSetup({ kind: 'created' });
    await sheEntersAndAnswers(user, '30');
    expect(generatePlan).toHaveBeenCalledExactlyOnceWith({
      minutesPerSession: 30, sessionsPerWeek: 3, playersAvailable: 1, equipment: ['wall'], level: 'intermediate',
    });
    expect(navigate).toHaveBeenCalledWith('/plan');
  });

  it(`Scenario: ${BOUND[3]}`, () => {
    ivyOnPracticeSetup({ kind: 'created' }, {
      minutesPerSession: 45, sessionsPerWeek: 2, playersAvailable: 2, equipment: ['ball_machine'], level: 'advanced',
    });
    expect(screen.getByLabelText('How long is each session?')).toHaveValue('45');
    expect(within(screen.getByRole('group', { name: 'How many sessions a week?' })).getByLabelText('2')).toBeChecked();
    expect(within(screen.getByRole('group', { name: 'How many players, including you?' })).getByLabelText('2')).toBeChecked();
    expect(screen.getByLabelText('A ball machine')).toBeChecked();
    expect(screen.getByLabelText('Advanced')).toBeChecked();
    expect(screen.getByText('This replaces your current plan.')).toBeInTheDocument();
  });
});
