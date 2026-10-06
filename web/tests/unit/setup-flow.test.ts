// Match setup state machine Q-01..Q-07 (ST-016; sprint-01 §5 front-end TDD list; flows §5).
// Pure reducer: one question per page, errors per page, Back keeps answers, Change returns to
// the check page.
import { describe, expect, it } from 'vitest';
import {
  initialSetup,
  participantsFor,
  setupReducer,
  type SetupAction,
  type SetupState,
} from '@/lib/setup/flow';

const TODAY = { year: 2026, month: 10, day: 5 };
const POLICY = { maxBytes: 10_000_000_000 };
const VIDEO = { name: 'Sat doubles.mp4', size: 3_000_000_000, lastModified: 1, type: 'video/mp4' };

function run(...actions: SetupAction[]): SetupState {
  return actions.reduce(setupReducer, initialSetup(TODAY));
}
const next: SetupAction = { type: 'continue', today: TODAY, policy: POLICY };

function doublesToCheck(): SetupAction[] {
  return [
    { type: 'answer', patch: { format: 'doubles' } },
    next,
    { type: 'answer', patch: { scoring: 'side_out' } },
    next,
    { type: 'answer', patch: { players: { A1: 'Ivy', A2: 'Dana', B1: 'Carlos', B2: 'Sam' } } },
    next,
    { type: 'answer', patch: { me: 'A1' } },
    next,
    next,
    { type: 'answer', patch: { file: VIDEO } },
    next,
  ];
}

describe('setupReducer', () => {
  it('1. Continue without an answer stays on the page with an error', () => {
    const s = run(next);
    expect(s.step).toBe('format');
    expect(s.errors).toEqual([{ field: 'format-doubles', message: 'Select doubles or singles' }]);
  });

  it('clears the error once the page is answered', () => {
    const s = run(next, { type: 'answer', patch: { format: 'singles' } }, next);
    expect(s.step).toBe('scoring');
    expect(s.errors).toEqual([]);
  });

  it('2. Back keeps answers', () => {
    const s = run(
      { type: 'answer', patch: { format: 'doubles' } },
      next,
      { type: 'answer', patch: { scoring: 'side_out' } },
      next,
      { type: 'back' },
      { type: 'back' },
    );
    expect(s.step).toBe('format');
    expect(s.answers.format).toBe('doubles');
    expect(s.answers.scoring).toBe('side_out');
  });

  it('3. "Change" returns to the check page after Continue', () => {
    const atCheck = run(...doublesToCheck());
    expect(atCheck.step).toBe('check');
    const s = run(...doublesToCheck(), { type: 'change', step: 'date' }, next);
    expect(s.step).toBe('check');
  });

  it('never accepts rally scoring (FR-043)', () => {
    const s = run({ type: 'answer', patch: { format: 'doubles' } }, next, { type: 'answer', patch: { scoring: 'rally' as never } }, next);
    expect(s.step).toBe('scoring');
    expect(s.answers.scoring).toBeNull();
    expect(s.errors[0]?.message).toBe('Select a scoring system');
  });

  it('doubles with three nicknames: "Each side needs two players"', () => {
    const s = run(
      { type: 'answer', patch: { format: 'doubles' } }, next,
      { type: 'answer', patch: { scoring: 'side_out' } }, next,
      { type: 'answer', patch: { players: { A1: 'Ivy', A2: 'Dana', B1: 'Carlos', B2: '  ' } } }, next,
    );
    expect(s.step).toBe('players');
    expect(s.errors).toEqual([{ field: 'player-B2', message: 'Each side needs two players' }]);
  });

  it('singles with a side empty: "Each side needs one player"', () => {
    const s = run(
      { type: 'answer', patch: { format: 'singles' } }, next,
      { type: 'answer', patch: { scoring: 'side_out' } }, next,
      { type: 'answer', patch: { players: { A1: 'Ivy', A2: '', B1: '', B2: '' } } }, next,
    );
    expect(s.errors).toEqual([{ field: 'player-B1', message: 'Each side needs one player' }]);
  });

  it('refuses a nickname over 30 characters, but not one that looks like contact details', () => {
    const base: SetupAction[] = [
      { type: 'answer', patch: { format: 'singles' } }, next,
      { type: 'answer', patch: { scoring: 'side_out' } }, next,
    ];
    const long = run(...base, { type: 'answer', patch: { players: { A1: 'x'.repeat(31), A2: '', B1: 'Carlos', B2: '' } } }, next);
    expect(long.errors).toEqual([{ field: 'player-A1', message: 'Nickname must be 30 characters or fewer' }]);
    const contact = run(...base, { type: 'answer', patch: { players: { A1: 'carlos@example.com', A2: '', B1: 'Ivy', B2: '' } } }, next);
    expect(contact.step).toBe('me');
  });

  it('asks who "me" is', () => {
    const s = run(
      { type: 'answer', patch: { format: 'singles' } }, next,
      { type: 'answer', patch: { scoring: 'side_out' } }, next,
      { type: 'answer', patch: { players: { A1: 'Ivy', A2: '', B1: 'Carlos', B2: '' } } }, next,
      next,
    );
    expect(s.errors).toEqual([{ field: 'me-A1', message: 'Choose one player as "me"' }]);
  });

  it('defaults the date to today and refuses a future or impossible date', () => {
    expect(initialSetup(TODAY).answers.date).toEqual({ day: '5', month: '10', year: '2026' });
    const toDate: SetupAction[] = [
      { type: 'answer', patch: { format: 'singles' } }, next,
      { type: 'answer', patch: { scoring: 'side_out' } }, next,
      { type: 'answer', patch: { players: { A1: 'Ivy', A2: '', B1: 'Carlos', B2: '' } } }, next,
      { type: 'answer', patch: { me: 'A1' } }, next,
    ];
    const future = run(...toDate, { type: 'answer', patch: { date: { day: '6', month: '10', year: '2026' } } }, next);
    expect(future.errors).toEqual([{ field: 'date-day', message: 'The date must be today or in the past' }]);
    const impossible = run(...toDate, { type: 'answer', patch: { date: { day: '31', month: '2', year: '2026' } } }, next);
    expect(impossible.errors).toEqual([{ field: 'date-day', message: 'Enter a real date' }]);
    const blank = run(...toDate, { type: 'answer', patch: { date: { day: '', month: '10', year: '2026' } } }, next);
    expect(blank.errors[0]?.message).toBe('Enter a real date');
  });

  it('needs a video and refuses one above the size cap from the policy', () => {
    const toVideo = doublesToCheck().slice(0, -2);
    expect(run(...toVideo, next).errors).toEqual([{ field: 'video', message: 'Choose a video file' }]);
    const huge = run(...toVideo, { type: 'answer', patch: { file: { ...VIDEO, size: 12_000_000_000 } } }, next);
    expect(huge.errors).toEqual([{ field: 'video', message: 'Videos must be 10 GB or smaller' }]);
  });

  it('changing the format from the check page drops players that no longer fit', () => {
    const s = run(
      ...doublesToCheck(),
      { type: 'change', step: 'format' },
      { type: 'answer', patch: { format: 'singles' } },
      next,
    );
    expect(s.step).toBe('check');
    expect(s.answers.players).toEqual({ A1: '', A2: '', B1: '', B2: '' });
    expect(s.answers.me).toBeNull();
  });

  it('keeps the players when the same format is chosen again', () => {
    const s = run(...doublesToCheck(), { type: 'change', step: 'format' }, { type: 'answer', patch: { format: 'doubles' } }, next);
    expect(s.answers.players.B2).toBe('Sam');
  });

  it('builds the API participants in slot order with exactly one "me"', () => {
    const s = run(...doublesToCheck());
    expect(participantsFor(s.answers)).toEqual([
      { slot: 'A1', nickname: 'Ivy', is_me: true },
      { slot: 'A2', nickname: 'Dana', is_me: false },
      { slot: 'B1', nickname: 'Carlos', is_me: false },
      { slot: 'B2', nickname: 'Sam', is_me: false },
    ]);
  });
});
