// ST-063b P-02 (FR-121; flows-sprint-04 §3; api-sprint-04 §2.1): the player's practice setup
// in the Coaching context's words (PlanPreferences). Pure functions, no React, no network.
// Negative first: invalid minutes, then the other unanswered questions, then the happy path.
import { describe, expect, it } from 'vitest';
import {
  EMPTY_DRAFT,
  checkDraft,
  draftFrom,
  fieldErrorsFrom422,
  preferencesFrom,
  toRequestBody,
  type PreferencesDraft,
} from '@/components/plan/PlanPreferencesModel';

const complete: PreferencesDraft = {
  minutes: '30', sessionsPerWeek: 3, playersAvailable: 1, equipment: ['wall'], level: 'intermediate',
};

describe('checkDraft (negative first)', () => {
  it.each(['10', '181', '14', '30.5', '-30', 'thirty', '1e2'])('refuses %s minutes with the range message', (m) => {
    const check = checkDraft({ ...complete, minutes: m });
    expect(check).toEqual({
      ok: false,
      errors: [{ field: 'minutes-per-session', message: 'Enter a number between 15 and 180' }],
    });
  });

  it('asks for the minutes when none were entered', () => {
    expect(checkDraft({ ...complete, minutes: '  ' })).toEqual({
      ok: false,
      errors: [{ field: 'minutes-per-session', message: 'Enter the minutes for each session' }],
    });
  });

  it('names every unanswered question in page order, the equipment being optional', () => {
    expect(checkDraft(EMPTY_DRAFT)).toEqual({
      ok: false,
      errors: [
        { field: 'minutes-per-session', message: 'Enter the minutes for each session' },
        { field: 'sessions-per-week-1', message: 'Choose how many sessions a week' },
        { field: 'players-available-1', message: 'Choose how many players' },
        { field: 'level-beginner', message: 'Choose your level' },
      ],
    });
  });

  it('accepts the edges 15 and 180 and no equipment', () => {
    expect(checkDraft({ ...complete, minutes: '15', equipment: [] })).toMatchObject({ ok: true });
    expect(checkDraft({ ...complete, minutes: ' 180 ' })).toEqual({
      ok: true,
      preferences: { minutesPerSession: 180, sessionsPerWeek: 3, playersAvailable: 1, equipment: ['wall'], level: 'intermediate' },
    });
  });
});

describe('the POST /me/plan body and the last preferences', () => {
  it('writes the closed api-sprint-04 §2.1 body, equipment in catalogue order without repeats', () => {
    const check = checkDraft({ ...complete, equipment: ['ball_machine', 'wall', 'ball_machine'] });
    if (!check.ok) throw new Error('expected a complete setup');
    expect(toRequestBody(check.preferences)).toEqual({
      minutes_per_session: 30, sessions_per_week: 3, players_available: 1,
      equipment: ['wall', 'ball_machine'], level: 'intermediate',
    });
  });

  it('reads nothing from a preferences object that breaks the contract', () => {
    expect(preferencesFrom(null)).toBeNull();
    expect(preferencesFrom({ minutes_per_session: 30 })).toBeNull();
    expect(preferencesFrom({ minutes_per_session: 30, sessions_per_week: 3, players_available: 1, equipment: ['rocket'], level: 'pro' })).toBeNull();
  });

  // Each case breaks one integer or range rule of api-sprint-04 §2.3 and nothing else.
  const valid = { minutes_per_session: 30, sessions_per_week: 3, players_available: 1, equipment: ['wall'], level: 'intermediate' };
  it.each([
    ['minutes_per_session', 14], ['minutes_per_session', 181], ['minutes_per_session', 30.5], ['minutes_per_session', '30'],
    ['sessions_per_week', 0], ['sessions_per_week', 8], ['sessions_per_week', 2.5],
    ['players_available', 0], ['players_available', 5], ['players_available', 1.5],
  ])('reads nothing when %s is %j', (field, value) => {
    expect(preferencesFrom({ ...valid, [field]: value })).toBeNull();
  });

  it('reads the edges 15 and 180 minutes, 1 and 7 sessions, 1 and 4 players', () => {
    expect(preferencesFrom({ ...valid, minutes_per_session: 15, sessions_per_week: 1, players_available: 1 })).toMatchObject({
      minutesPerSession: 15, sessionsPerWeek: 1, playersAvailable: 1,
    });
    expect(preferencesFrom({ ...valid, minutes_per_session: 180, sessions_per_week: 7, players_available: 4 })).toMatchObject({
      minutesPerSession: 180, sessionsPerWeek: 7, playersAvailable: 4,
    });
  });

  it('prefills the draft from the last preferences', () => {
    const last = preferencesFrom({
      minutes_per_session: 45, sessions_per_week: 2, weekly_minutes: 90, players_available: 2,
      equipment: ['ball_machine'], level: 'advanced',
    });
    expect(draftFrom(last)).toEqual({ minutes: '45', sessionsPerWeek: 2, playersAvailable: 2, equipment: ['ball_machine'], level: 'advanced' });
    expect(draftFrom(null)).toEqual(EMPTY_DRAFT);
  });
});

describe('fieldErrorsFrom422', () => {
  it('maps unknown fields to nothing, so the caller shows a general error instead', () => {
    expect(fieldErrorsFrom422([{ field: null, code: 'unknown_field' }])).toEqual([]);
  });

  it('maps the server codes to the same messages the page uses', () => {
    expect(fieldErrorsFrom422([
      { field: 'minutes_per_session', code: 'out_of_range' },
      { field: 'level', code: 'required' },
      { field: 'equipment', code: 'unknown_value' },
    ])).toEqual([
      { field: 'minutes-per-session', message: 'Enter a number between 15 and 180' },
      { field: 'level-beginner', message: 'Choose your level' },
      { field: 'equipment-wall', message: 'Choose only from the list of what you have' },
    ]);
  });
});
