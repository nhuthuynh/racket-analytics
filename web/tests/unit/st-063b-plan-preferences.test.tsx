// ST-063b P-02 "Your practice setup" (FR-121; flows-sprint-04 §3, §10, §11). Component tests,
// negative first: invalid minutes never reach the API; then the 409 refusals and errors keep the
// answers; then the keyboard path, the regenerate visit and the loading and offline states.
import { act, render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { PlanPreferences } from '@/components/plan/PlanPreferences';
import type { GenerateOutcome } from '@/components/plan/PlanPreferencesApi';

function setup(outcome: GenerateOutcome = { kind: 'created' }, initial: Parameters<typeof PlanPreferences>[0]['initial'] = null) {
  const generatePlan = vi.fn(async () => outcome);
  const navigate = vi.fn();
  render(<PlanPreferences initial={initial} api={{ generatePlan }} navigate={navigate} />);
  return { generatePlan, navigate, user: userEvent.setup() };
}

async function answerAll(user: ReturnType<typeof userEvent.setup>, minutes = '30') {
  await user.type(screen.getByLabelText('How long is each session?'), minutes);
  await user.click(within(screen.getByRole('group', { name: 'How many sessions a week?' })).getByLabelText('3'));
  await user.click(within(screen.getByRole('group', { name: 'How many players, including you?' })).getByLabelText('1'));
  await user.click(screen.getByLabelText('A wall'));
  await user.click(screen.getByLabelText('Intermediate'));
}

const makeMyPlan = () => screen.getByRole('button', { name: 'Make my plan' });

afterEach(() => vi.useRealTimers());

describe('P-02 validation (negative first)', () => {
  it('invalid minutes: the error summary links to the field, the value stays, nothing is sent', async () => {
    const { generatePlan, user } = setup();
    await answerAll(user, '10');
    await user.click(makeMyPlan());
    const summary = screen.getByRole('alert');
    expect(summary).toHaveFocus();
    const link = within(summary).getByRole('link', { name: 'Enter a number between 15 and 180' });
    await user.click(link);
    expect(screen.getByLabelText('How long is each session?')).toHaveFocus();
    expect(screen.getByLabelText('How long is each session?')).toHaveValue('10');
    expect(screen.getByLabelText('How long is each session?')).toHaveAccessibleDescription(/Enter a number between 15 and 180/);
    expect(generatePlan).not.toHaveBeenCalled();
    expect(document.title).toMatch(/^Error: Your practice setup/);
  });

  it('an empty first visit names each unanswered question and chooses nothing for the player', async () => {
    const { generatePlan, user } = setup();
    expect(screen.queryAllByRole('radio', { checked: true })).toHaveLength(0);
    await user.click(makeMyPlan());
    const links = within(screen.getByRole('alert')).getAllByRole('link').map((l) => l.textContent);
    expect(links).toEqual(['Enter the minutes for each session', 'Choose how many sessions a week', 'Choose how many players', 'Choose your level']);
    expect(generatePlan).not.toHaveBeenCalled();
  });
});

describe('P-02 refusals keep the answers', () => {
  it('409 no_tagged_match: the reason with a link to tag a match, focus on the alert', async () => {
    const { user, navigate } = setup({ kind: 'no_tagged_match' });
    await answerAll(user);
    await user.click(makeMyPlan());
    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent('Tag a match first. Your plan is built from the rallies you tag.');
    expect(within(alert).getByRole('link', { name: 'Your matches' })).toHaveAttribute('href', '/matches');
    expect(alert).toHaveFocus();
    expect(screen.getByLabelText('How long is each session?')).toHaveValue('30');
    expect(screen.getByLabelText('Intermediate')).toBeChecked();
    expect(navigate).not.toHaveBeenCalled();
  });

  it('409 no_plan_fits on a regenerate visit says the current plan is unchanged', async () => {
    const { user } = setup({ kind: 'no_plan_fits' }, { minutesPerSession: 15, sessionsPerWeek: 1, playersAvailable: 4, equipment: [], level: 'beginner' });
    await user.click(makeMyPlan());
    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent('No plan fits these settings. Try more minutes, more sessions or more equipment.');
    expect(alert).toHaveTextContent('Your current plan is unchanged.');
  });

  it('409 plan_conflict links to the current plan', async () => {
    const { user } = setup({ kind: 'plan_conflict' });
    await answerAll(user);
    await user.click(makeMyPlan());
    expect(within(await screen.findByRole('alert')).getByRole('link', { name: 'See your current plan' })).toHaveAttribute('href', '/plan');
  });

  it('a server error shows the reference', async () => {
    const { user } = setup({ kind: 'error', supportRef: 'ref_0123456789abcdef' });
    await answerAll(user);
    await user.click(makeMyPlan());
    expect(await screen.findByRole('alert')).toHaveTextContent('Reference: ref_0123456789abcdef');
  });
});

describe('P-02 makes the plan', () => {
  it('keyboard only: answers, submits with Enter, sends the preferences and opens the plan', async () => {
    const { generatePlan, navigate, user } = setup();
    await user.tab();
    expect(screen.getByLabelText('How long is each session?')).toHaveFocus();
    await user.keyboard('45');
    await user.tab();
    await user.keyboard(' '); // sessions: first radio "1"
    await user.keyboard('{ArrowRight}'); // "2"
    await user.tab();
    await user.keyboard(' {ArrowRight}'); // players "2"
    await user.tab();
    await user.keyboard(' '); // "A wall"
    for (let i = 0; i < 5; i += 1) await user.tab(); // past the other four checkboxes to the level radios
    await user.keyboard(' ');
    await user.keyboard('{Enter}');
    expect(generatePlan).toHaveBeenCalledWith({ minutesPerSession: 45, sessionsPerWeek: 2, playersAvailable: 2, equipment: ['wall'], level: 'beginner' });
    expect(navigate).toHaveBeenCalledWith('/plan');
  });

  it('a regenerate visit starts from the last preferences and says it replaces the plan', async () => {
    const { generatePlan, user } = setup({ kind: 'created' }, { minutesPerSession: 45, sessionsPerWeek: 2, playersAvailable: 2, equipment: ['ball_machine'], level: 'advanced' });
    expect(screen.getByLabelText('How long is each session?')).toHaveValue('45');
    expect(screen.getByLabelText('A ball machine')).toBeChecked();
    expect(screen.getByLabelText('Advanced')).toBeChecked();
    expect(screen.getByText('This replaces your current plan.')).toBeInTheDocument();
    await user.click(makeMyPlan());
    expect(generatePlan).toHaveBeenCalledWith({ minutesPerSession: 45, sessionsPerWeek: 2, playersAvailable: 2, equipment: ['ball_machine'], level: 'advanced' });
  });

  it('while the plan is made the button is busy and disabled; after 10 s it says it is still working', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    let finish: (o: GenerateOutcome) => void = () => {};
    const generatePlan = vi.fn(() => new Promise<GenerateOutcome>((r) => { finish = r; }));
    render(<PlanPreferences initial={{ minutesPerSession: 30, sessionsPerWeek: 3, playersAvailable: 1, equipment: [], level: 'beginner' }} api={{ generatePlan }} navigate={vi.fn()} />);
    await userEvent.setup({ advanceTimers: vi.advanceTimersByTime }).click(makeMyPlan());
    const busy = screen.getByRole('button', { name: 'Making your plan…' });
    expect(busy).toBeDisabled();
    expect(busy).toHaveAttribute('aria-busy', 'true');
    expect(screen.getByRole('status')).toHaveTextContent('Making your plan…');
    await act(async () => { vi.advanceTimersByTime(10_000); });
    expect(screen.getByRole('status')).toHaveTextContent('Still working…');
    await act(async () => { finish({ kind: 'no_plan_fits' }); });
    expect(makeMyPlan()).toBeEnabled();
  });

  it('offline: the form stays editable and "Make my plan" says it needs a connection', async () => {
    const spy = vi.spyOn(navigator, 'onLine', 'get').mockReturnValue(false);
    const { generatePlan, user } = setup();
    expect(makeMyPlan()).toBeDisabled();
    expect(makeMyPlan()).toHaveAccessibleDescription('Needs a connection to make your plan.');
    await user.type(screen.getByLabelText('How long is each session?'), '30');
    expect(screen.getByLabelText('How long is each session?')).toHaveValue('30');
    spy.mockReturnValue(true);
    await act(async () => { window.dispatchEvent(new Event('online')); });
    expect(makeMyPlan()).toBeEnabled();
    expect(generatePlan).not.toHaveBeenCalled();
  });
});
