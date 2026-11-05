// The R1 critical journeys of the browser matrix (ST-079; NFR-024.1-.3; goal-scorecard G05-04):
// E2E-04-01..05, sign-in (E2E-01-01's first step) and upload resume (E2E-01-02). The matrix runs
// `--grep @critical`, so a journey without the tag would silently drop out of it; the binding test
// (tests/unit/e2e-helpers-journey-binding.test.ts) checks the tags from source text, no browser.
// scripts/measure/browser_matrix.py names the same seven journeys in the reports.
import type { SpecSource } from './scenario-binding';

export const CRITICAL_TAG = '@critical';

export interface CriticalJourney {
  id: string;
  file: string;
  /** Text in the tagged test's title; absent: the spec's `test.describe` carries the tag. */
  test?: string;
}

export const CRITICAL_JOURNEYS: CriticalJourney[] = [
  { id: 'E2E-04-01', file: 'sprint-04/journey-v3.spec.ts' },
  { id: 'E2E-04-02', file: 'sprint-04/plan-states.spec.ts' },
  { id: 'E2E-04-03', file: 'sprint-04/offline-done.spec.ts' },
  { id: 'E2E-04-04', file: 'sprint-04/swap-no-alternative.spec.ts' },
  { id: 'E2E-04-05', file: 'sprint-04/keyboard-and-narrow.spec.ts' },
  { id: 'sign-in', file: 'sprint-01/sign-in.spec.ts' },
  { id: 'upload-resume', file: 'sprint-01/resumable-upload.spec.ts', test: '(E2E-01-02)' },
];

const escape = (s: string) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');

function tagged(journey: CriticalJourney, text: string): boolean {
  const call = journey.test ? `(?<![.\\w])test\\(\\s*(['"\`])[^'"\`]*${escape(journey.test)}` : `test\\.describe\\(\\s*(['"\`])[^'"\`]*`;
  return new RegExp(`${call}\\1,\\s*\\{\\s*tag:\\s*'${CRITICAL_TAG}'`).test(text);
}

/** The critical journeys whose spec is missing or does not tag them `@critical`. */
export function untaggedCriticalJourneys(specs: SpecSource[]): CriticalJourney[] {
  return CRITICAL_JOURNEYS.filter((j) => {
    const spec = specs.find((s) => s.file === j.file);
    return !spec || !tagged(j, spec.text);
  });
}
