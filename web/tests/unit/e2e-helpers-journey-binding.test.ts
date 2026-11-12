// Binds tests/features/e2e_journey.feature (ST-065; QD §7) to its browser test: every scenario
// carries an E2E id and a Playwright test whose title starts with that id and the scenario name,
// not skipped. The browser test itself (web/e2e/sprint-04/journey-v3.spec.ts) is the scenario's
// integration level; this check stops the two drifting apart. Negative cases first.
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';
import { CRITICAL_JOURNEYS, CRITICAL_TAG, untaggedCriticalJourneys } from '../../e2e/helpers/critical-journeys';
import { readSpecs, scenariosOf, unboundScenarios } from '../../e2e/helpers/scenario-binding';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const FEATURE = readFileSync(path.join(HERE, '../../../tests/features/e2e_journey.feature'), 'utf8');
const E2E_DIR = path.join(HERE, '../../e2e');

const ONE = ['Feature: R1 journey', '', '  @E2E-04-01', '  Scenario: Upload to plan', '    Given Ivy signs in'].join('\n');
const spec = (text: string) => [{ file: 'sprint-04/journey-v3.spec.ts', text }];

describe('Feature binding: R1 journey (e2e_journey.feature)', () => {
  it('reports a scenario with no E2E id', () => {
    const feature = ['Feature: R1 journey', '  @M0', '  Scenario: Upload to plan', '    Given x'].join('\n');
    expect(unboundScenarios(feature, spec("test('E2E-04-01 Upload to plan', async () => {});"))).toEqual([
      { scenario: 'Upload to plan', reason: 'no @E2E-nn-nn tag' },
    ]);
  });

  it('reports a scenario whose browser test is missing, skipped or named otherwise', () => {
    for (const text of [
      '',
      "test.skip('E2E-04-01 Upload to plan', async () => {});",
      "test.fixme('E2E-04-01 Upload to plan', async () => {});",
      "test('E2E-04-01 something else', async () => {});",
      "test('E2E-04-011 Upload to plan', async () => {});",
    ]) {
      expect(unboundScenarios(ONE, spec(text)), text).toEqual([
        { scenario: 'Upload to plan', reason: 'no test titled "E2E-04-01 ... Upload to plan"' },
      ]);
    }
  });

  it('accepts a scenario bound by a test titled with its id and name', () => {
    expect(unboundScenarios(ONE, spec('test(\n  "E2E-04-01 Upload to plan: sign in to swap", async () => {});'))).toEqual([]);
  });

  it('reads the scenarios and their E2E ids, tags on the line above', () => {
    expect(scenariosOf(ONE)).toEqual([{ name: 'Upload to plan', ids: ['E2E-04-01'] }]);
  });

  it('Scenario: Upload to plan is bound by a browser test in web/e2e', () => {
    expect(scenariosOf(FEATURE).map((s) => s.name)).toEqual(['Upload to plan']);
    expect(unboundScenarios(FEATURE, readSpecs(E2E_DIR))).toEqual([]);
  });
});

// ST-079 (NFR-024.1-.3; G05-04): the browser matrix runs `--grep @critical`, so every critical
// journey (E2E-04-01..05, sign-in, upload resume) must carry the tag in its spec. Negative first.
describe('Critical journeys carry the @critical tag (ST-079)', () => {
  const RESUME = 'sprint-01/resumable-upload.spec.ts';
  const SIGN_IN = 'sprint-01/sign-in.spec.ts';

  it('reports a journey whose spec has no @critical tag, or whose spec is missing', () => {
    const specs = [
      { file: SIGN_IN, text: "test.describe('Sign in without a memorised password', () => {});" },
      { file: RESUME, text: "test('Connection drops mid-upload (E2E-01-02)', { tag: '@critical' }, async () => {});" },
    ];
    const ids = untaggedCriticalJourneys(specs).map((j) => j.id);
    expect(ids).toContain('sign-in');
    expect(ids).not.toContain('upload-resume');
    expect(ids).toContain('E2E-04-01'); // its spec file is missing from the list
  });

  it('reports the upload resume journey when only another test of its spec is tagged', () => {
    const text = [
      "test('Connection drops mid-upload (E2E-01-02)', async () => {});",
      "test('Upload page wording', { tag: '@critical' }, async () => {});",
    ].join('\n');
    expect(untaggedCriticalJourneys([{ file: RESUME, text }]).map((j) => j.id)).toContain('upload-resume');
  });

  it('names seven journeys: E2E-04-01..05, sign-in and upload resume', () => {
    expect(CRITICAL_JOURNEYS.map((j) => j.id)).toEqual([
      'E2E-04-01', 'E2E-04-02', 'E2E-04-03', 'E2E-04-04', 'E2E-04-05', 'sign-in', 'upload-resume',
    ]);
    expect(CRITICAL_TAG).toBe('@critical');
  });

  it('every critical journey in web/e2e carries @critical', () => {
    expect(untaggedCriticalJourneys(readSpecs(E2E_DIR))).toEqual([]);
  });
});
