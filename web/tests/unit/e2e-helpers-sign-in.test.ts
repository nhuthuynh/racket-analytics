// QA-VERIFY04R3-05/-06: the shared sign-in helper (e2e/helpers/sprint-01.ts) must finish sign-in
// on a stack with the age question on (FEATURE_AGE_GATE), where a new account lands on A-10
// `/welcome/age` before `/welcome`. `signInStep` tells the helper where the browser is after the
// link opens; the binding check keeps tests/features/e2e_flags_on.feature and the flag-on specs
// together. Negative cases first.
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';
import { readSpecs, scenariosOf, unboundScenarios } from '../../e2e/helpers/scenario-binding';
import { AGE_QUESTION_URL, SIGNED_IN_URL, signInStep } from '../../e2e/helpers/sprint-01';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const FEATURE = readFileSync(path.join(HERE, '../../../tests/features/e2e_flags_on.feature'), 'utf8');
const FLAGS_ON_DIR = path.join(HERE, '../../e2e/sprint-04/flags-on');

describe('signInStep (where the browser is after the sign-in link opens)', () => {
  it('is still pending on the callback page, the start page or an unrelated path', () => {
    for (const url of [
      'https://localhost:3000/auth/callback#token=abc',
      'https://localhost:3000/',
      'https://localhost:3000/welcomeback',
      'https://localhost:3000/welcome/agenda',
      'https://localhost:3000/matches-archive',
    ]) {
      expect(signInStep(url), url).toBe('pending');
    }
  });

  it('is the age question on A-10, with or without a query or fragment', () => {
    for (const url of ['https://localhost:3000/welcome/age', 'https://localhost:3000/welcome/age?next=1', 'https://localhost:3000/welcome/age#q']) {
      expect(signInStep(url), url).toBe('age-question');
    }
  });

  it('is signed in on the first-run page or the match list', () => {
    for (const url of ['https://localhost:3000/welcome', 'https://localhost:3000/matches', 'https://localhost:3000/matches?x=1']) {
      expect(signInStep(url), url).toBe('signed-in');
    }
  });

  it('never counts the age question as signed in (the gate must be answered first)', () => {
    expect(SIGNED_IN_URL.test('https://localhost:3000/welcome/age')).toBe(false);
    expect(AGE_QUESTION_URL.test('https://localhost:3000/welcome')).toBe(false);
  });
});

describe('Feature binding: flag-on screens (e2e_flags_on.feature)', () => {
  it('reads the three scenarios: privacy settings, match limit and storage full', () => {
    expect(scenariosOf(FEATURE).map((s) => s.ids)).toEqual([['E2E-04-07'], ['E2E-04-08'], ['E2E-04-08']]);
  });

  it('every scenario is bound by a flag-on browser test titled with its id and name', () => {
    expect(unboundScenarios(FEATURE, readSpecs(FLAGS_ON_DIR))).toEqual([]);
  });
});
