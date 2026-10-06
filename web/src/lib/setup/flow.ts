// Match setup flow Q-01..Q-07 (ST-016; FR-021, FR-005, FR-043; flows-sprint-01 §5;
// api-sprint-01 §5). A pure reducer: no React, no I/O. One question per step [DPA/DESIGN-12];
// each step validates only its own answer; "Change" from the check page returns there.
// Messages are the exact flows/Gherkin strings. The server re-validates everything (ADR 0024).
import { formatSizeCap } from '@/lib/format';

export const STEPS = ['format', 'scoring', 'players', 'me', 'date', 'video', 'check'] as const;
export type Step = (typeof STEPS)[number];

export type Format = 'doubles' | 'singles';
export type Slot = 'A1' | 'A2' | 'B1' | 'B2';
export const SLOTS_FOR: Readonly<Record<Format, readonly Slot[]>> = {
  doubles: ['A1', 'A2', 'B1', 'B2'],
  singles: ['A1', 'B1'],
};
export const NICKNAME_MAX = 30;

export interface DateParts {
  year: number;
  month: number;
  day: number;
}

export interface ChosenFile {
  name: string;
  size: number;
  lastModified: number;
  type: string;
}

export interface Answers {
  format: Format | null;
  scoring: 'side_out' | null;
  players: Record<Slot, string>;
  me: Slot | null;
  date: { day: string; month: string; year: string };
  file: ChosenFile | null;
}

export interface StepError {
  /** id of the control the error-summary link focuses */
  field: string;
  message: string;
}

export interface SetupState {
  step: Step;
  answers: Answers;
  errors: StepError[];
  /** Set by "Change" on the check page: Continue goes back there. */
  returnToCheck: boolean;
}

export type SetupAction =
  | { type: 'answer'; patch: Partial<Answers> }
  | { type: 'continue'; today: DateParts; policy: { maxBytes: number } }
  | { type: 'back' }
  | { type: 'change'; step: Exclude<Step, 'check'> }
  | { type: 'go'; step: Step }
  | { type: 'errors'; errors: StepError[] };

const EMPTY_PLAYERS: Record<Slot, string> = { A1: '', A2: '', B1: '', B2: '' };

export function initialSetup(today: DateParts): SetupState {
  return {
    step: 'format',
    answers: {
      format: null,
      scoring: null,
      players: { ...EMPTY_PLAYERS },
      me: null,
      date: { day: String(today.day), month: String(today.month), year: String(today.year) },
      file: null,
    },
    errors: [],
    returnToCheck: false,
  };
}

// --- validation per step -------------------------------------------------------------------

/** "YYYY-MM-DD" for a real calendar date from 2000-01-01, else null. */
export function isoDate(date: Answers['date']): string | null {
  if (![date.day, date.month, date.year].every((p) => /^\d{1,4}$/.test(p.trim()))) return null;
  const [d, m, y] = [Number(date.day), Number(date.month), Number(date.year)];
  if (y < 2000 || m < 1 || m > 12 || d < 1) return null;
  const real = new Date(Date.UTC(y, m - 1, d));
  if (real.getUTCMonth() !== m - 1 || real.getUTCDate() !== d) return null;
  return `${y}-${String(m).padStart(2, '0')}-${String(d).padStart(2, '0')}`;
}

function sideMessage(format: Format): string {
  return format === 'doubles' ? 'Each side needs two players' : 'Each side needs one player';
}

function validatePlayers(answers: Answers): StepError[] {
  const format = answers.format ?? 'doubles';
  const errors: StepError[] = [];
  for (const side of ['A', 'B'] as const) {
    const slots = SLOTS_FOR[format].filter((s) => s.startsWith(side));
    const missing = slots.find((s) => answers.players[s].trim() === '');
    if (missing) errors.push({ field: `player-${missing}`, message: sideMessage(format) });
  }
  for (const slot of SLOTS_FOR[format]) {
    const nickname = answers.players[slot].trim();
    if (nickname.length > NICKNAME_MAX) {
      errors.push({ field: `player-${slot}`, message: `Nickname must be ${NICKNAME_MAX} characters or fewer` });
    } else if (/[\u0000-\u001f\u007f]/.test(nickname)) {
      errors.push({ field: `player-${slot}`, message: 'Nickname must only use letters, numbers and punctuation' });
    }
  }
  return errors;
}

export function validateStep(
  step: Step,
  answers: Answers,
  today: DateParts,
  policy: { maxBytes: number },
): StepError[] {
  switch (step) {
    case 'format':
      return answers.format ? [] : [{ field: 'format-doubles', message: 'Select doubles or singles' }];
    case 'scoring':
      return answers.scoring === 'side_out'
        ? []
        : [{ field: 'scoring-side_out', message: 'Select a scoring system' }];
    case 'players':
      return validatePlayers(answers);
    case 'me': {
      const slots = SLOTS_FOR[answers.format ?? 'doubles'];
      return answers.me && slots.includes(answers.me)
        ? []
        : [{ field: `me-${slots[0]}`, message: 'Choose one player as "me"' }];
    }
    case 'date': {
      const iso = isoDate(answers.date);
      if (!iso) return [{ field: 'date-day', message: 'Enter a real date' }];
      const todayIso = isoDate({ day: String(today.day), month: String(today.month), year: String(today.year) });
      return todayIso && iso > todayIso
        ? [{ field: 'date-day', message: 'The date must be today or in the past' }]
        : [];
    }
    case 'video':
      if (!answers.file) return [{ field: 'video', message: 'Choose a video file' }];
      return answers.file.size > policy.maxBytes
        ? [{ field: 'video', message: `Videos must be ${formatSizeCap(policy.maxBytes)} or smaller` }]
        : [];
    case 'check':
      return [];
  }
}

/** The first page whose answer is missing or wrong, for the check page. */
export function firstInvalidStep(
  answers: Answers,
  today: DateParts,
  policy: { maxBytes: number },
): Exclude<Step, 'check'> | null {
  for (const step of STEPS) {
    if (step === 'check') return null;
    if (validateStep(step, answers, today, policy).length > 0) return step;
  }
  return null;
}

// --- reducer -------------------------------------------------------------------------------

function applyAnswer(answers: Answers, patch: Partial<Answers>): Answers {
  const next = { ...answers, ...patch };
  if (patch.scoring !== undefined && patch.scoring !== 'side_out') next.scoring = answers.scoring; // FR-043
  if (patch.format !== undefined && patch.format !== answers.format && answers.format !== null) {
    // The players and "me" were for the other format: ask again (flows §14.3.4 "Change one answer").
    next.players = { ...EMPTY_PLAYERS };
    next.me = null;
  }
  return next;
}

export function setupReducer(state: SetupState, action: SetupAction): SetupState {
  switch (action.type) {
    case 'answer':
      return { ...state, answers: applyAnswer(state.answers, action.patch) };
    case 'errors':
      return { ...state, errors: action.errors };
    case 'continue': {
      if (state.step === 'check') return state;
      const errors = validateStep(state.step, state.answers, action.today, action.policy);
      if (errors.length > 0) return { ...state, errors };
      const index = STEPS.indexOf(state.step);
      const step = state.returnToCheck ? 'check' : STEPS[index + 1]!;
      return { ...state, step, errors: [], returnToCheck: step === 'check' ? false : state.returnToCheck };
    }
    case 'back': {
      const index = STEPS.indexOf(state.step);
      if (state.returnToCheck) return { ...state, step: 'check', errors: [], returnToCheck: false };
      return index === 0 ? state : { ...state, step: STEPS[index - 1]!, errors: [] };
    }
    case 'change':
      return { ...state, step: action.step, errors: [], returnToCheck: true };
    case 'go':
      return { ...state, step: action.step, errors: [] };
  }
}

export interface ParticipantInput {
  slot: Slot;
  nickname: string;
  is_me: boolean;
}

/** The API's `participants` (api-sprint-01 §5.1), in slot order. */
export function participantsFor(answers: Answers): ParticipantInput[] {
  return SLOTS_FOR[answers.format ?? 'doubles'].map((slot) => ({
    slot,
    nickname: answers.players[slot].trim(),
    is_me: answers.me === slot,
  }));
}
