// The player's practice setup (ST-063b P-02; FR-121) in the Coaching context's words:
// PlanPreferences as `POST /me/plan` takes them (api-sprint-04 §2.1). Pure: no React, no network.
// The server re-checks every rule; the page checks first so the player gets the fix at once.
import type { FieldError } from '@/components/ErrorSummary';

export const EQUIPMENT = ['wall', 'half_court', 'full_court', 'ball_machine', 'partner_feeder'] as const;
export const LEVELS = ['beginner', 'intermediate', 'advanced'] as const;
export type Equipment = (typeof EQUIPMENT)[number];
export type Level = (typeof LEVELS)[number];

export const MIN_MINUTES = 15;
export const MAX_MINUTES = 180;
export const SESSION_CHOICES = [1, 2, 3, 4, 5, 6, 7] as const;
export const PLAYER_CHOICES = [1, 2, 3, 4] as const;

export interface PlanPreferences {
  minutesPerSession: number;
  sessionsPerWeek: number;
  playersAvailable: number;
  equipment: Equipment[];
  level: Level;
}

/** What the form holds: minutes as typed, and nothing chosen until the player chooses (PD-4). */
export interface PreferencesDraft {
  minutes: string;
  sessionsPerWeek: number | null;
  playersAvailable: number | null;
  equipment: Equipment[];
  level: Level | null;
}

export const EMPTY_DRAFT: PreferencesDraft = { minutes: '', sessionsPerWeek: null, playersAvailable: null, equipment: [], level: null };

/** Words per flows-sprint-04 §3 (drill-schema `needs`; level words per coach). */
export const EQUIPMENT_WORDS: Record<Equipment, string> = {
  wall: 'A wall', half_court: 'Half a court', full_court: 'A full court',
  ball_machine: 'A ball machine', partner_feeder: 'Someone to feed balls',
};
export const LEVEL_WORDS: Record<Level, string> = { beginner: 'Beginner', intermediate: 'Intermediate', advanced: 'Advanced' };

/** The input each question's error links to: the field, or a group's first option. */
export const FIELD_IDS = {
  minutes: 'minutes-per-session',
  sessions: 'sessions-per-week-1',
  players: 'players-available-1',
  equipment: 'equipment-wall',
  level: 'level-beginner',
} as const;
export type Question = keyof typeof FIELD_IDS;

export const MESSAGES = {
  minutesRequired: 'Enter the minutes for each session',
  minutesRange: `Enter a number between ${MIN_MINUTES} and ${MAX_MINUTES}`,
  sessions: 'Choose how many sessions a week',
  players: 'Choose how many players',
  equipment: 'Choose only from the list of what you have',
  level: 'Choose your level',
} as const;

const error = (q: Question, message: string): FieldError => ({ field: FIELD_IDS[q], message });

export type PreferencesCheck = { ok: true; preferences: PlanPreferences } | { ok: false; errors: FieldError[] };

/** Checks a draft in page order; a complete draft becomes PlanPreferences. */
export function checkDraft(draft: PreferencesDraft): PreferencesCheck {
  const errors: FieldError[] = [];
  const typed = draft.minutes.trim();
  const minutes = /^\d{1,3}$/.test(typed) ? Number(typed) : NaN;
  if (typed === '') errors.push(error('minutes', MESSAGES.minutesRequired));
  else if (!(minutes >= MIN_MINUTES && minutes <= MAX_MINUTES)) errors.push(error('minutes', MESSAGES.minutesRange));
  if (draft.sessionsPerWeek === null) errors.push(error('sessions', MESSAGES.sessions));
  if (draft.playersAvailable === null) errors.push(error('players', MESSAGES.players));
  if (draft.level === null) errors.push(error('level', MESSAGES.level));
  if (errors.length > 0 || draft.sessionsPerWeek === null || draft.playersAvailable === null || draft.level === null) {
    return { ok: false, errors };
  }
  return {
    ok: true,
    preferences: {
      minutesPerSession: minutes,
      sessionsPerWeek: draft.sessionsPerWeek,
      playersAvailable: draft.playersAvailable,
      equipment: EQUIPMENT.filter((e) => draft.equipment.includes(e)),
      level: draft.level,
    },
  };
}

/** The closed `POST /me/plan` body; `weekly_minutes` is left to its default (PD-4 R4-3). */
export function toRequestBody(p: PlanPreferences) {
  return {
    minutes_per_session: p.minutesPerSession,
    sessions_per_week: p.sessionsPerWeek,
    players_available: p.playersAvailable,
    equipment: EQUIPMENT.filter((e) => p.equipment.includes(e)),
    level: p.level,
  };
}

const isInt = (v: unknown, lo: number, hi: number): v is number => Number.isInteger(v) && (v as number) >= lo && (v as number) <= hi;

/** The plan's `preferences` (api-sprint-04 §2.3), or null when they break the contract. */
export function preferencesFrom(raw: unknown): PlanPreferences | null {
  const p = raw as Record<string, unknown> | null;
  if (typeof p !== 'object' || p === null) return null;
  const { minutes_per_session: m, sessions_per_week: s, players_available: n, equipment: eq, level } = p;
  if (!isInt(m, MIN_MINUTES, MAX_MINUTES) || !isInt(s, 1, 7) || !isInt(n, 1, 4)) return null;
  if (!Array.isArray(eq) || !eq.every((e) => (EQUIPMENT as readonly unknown[]).includes(e))) return null;
  if (!(LEVELS as readonly unknown[]).includes(level)) return null;
  return { minutesPerSession: m, sessionsPerWeek: s, playersAvailable: n, equipment: eq as Equipment[], level: level as Level };
}

export function draftFrom(p: PlanPreferences | null): PreferencesDraft {
  if (!p) return EMPTY_DRAFT;
  return {
    minutes: String(p.minutesPerSession), sessionsPerWeek: p.sessionsPerWeek,
    playersAvailable: p.playersAvailable, equipment: [...p.equipment], level: p.level,
  };
}

const SERVER_FIELDS: Record<string, (code: string) => FieldError> = {
  minutes_per_session: (c) => error('minutes', c === 'required' ? MESSAGES.minutesRequired : MESSAGES.minutesRange),
  weekly_minutes: () => error('minutes', MESSAGES.minutesRange),
  sessions_per_week: () => error('sessions', MESSAGES.sessions),
  players_available: () => error('players', MESSAGES.players),
  equipment: () => error('equipment', MESSAGES.equipment),
  level: () => error('level', MESSAGES.level),
};

/** A 422's field codes as the page's own messages; a field the page has not got maps to nothing. */
export function fieldErrorsFrom422(fields: readonly { field: string | null; code: string }[]): FieldError[] {
  const out: FieldError[] = [];
  for (const f of fields) {
    const make = f.field && Object.hasOwn(SERVER_FIELDS, f.field) ? SERVER_FIELDS[f.field] : undefined;
    const e = make?.(f.code);
    if (e && !out.some((o) => o.field === e.field)) out.push(e);
  }
  return out;
}
