// CI-STALL-SCENARIO-RACE (NFR-074): when the gated E2E step reaches its global timeout,
// Playwright 1.56.1 prints the summary and exits without waiting for the worker to report the
// test it was running, so the `list` reporter's line for that test may never appear (main run
// 38103354166). This reporter names every test that began and had not ended when the run ends
// with status `timedout`.
import type { FullConfig, FullResult, Suite, TestCase, TestResult } from '@playwright/test/reporter';
import { describe, expect, it } from 'vitest';
import InterruptedTestsReporter, { interruptedLine } from '../../e2e/helpers/interrupted-tests-reporter';

const ROOT = '/repo/web/e2e';

function suite(type: Suite['type'], title: string, parent?: Suite): Suite {
  return { type, title, parent } as unknown as Suite;
}

function testCase(id: string, title: string, file: string, line: number, describes: string[] = []): TestCase {
  let parent = suite('file', file.slice(ROOT.length + 1), suite('project', '', suite('root', '')));
  for (const d of describes) parent = suite('describe', d, parent);
  return { id, title, parent, location: { file, line, column: 5 } } as unknown as TestCase;
}

function reporter(): { lines: string[]; r: InterruptedTestsReporter } {
  const lines: string[] = [];
  const r = new InterruptedTestsReporter({ write: (s: string) => lines.push(s) });
  r.onBegin({ rootDir: ROOT } as FullConfig, suite('root', ''));
  return { lines, r };
}

const result = {} as TestResult;
const end = (status: FullResult['status']) => ({ status }) as FullResult;

const first = testCase('1', 'first test passes', `${ROOT}/stall.spec.ts`, 3);
const second = testCase('2', 'second test waits', `${ROOT}/stall.spec.ts`, 5);

describe('InterruptedTestsReporter', () => {
  it.each(['passed', 'failed', 'interrupted'] as const)(
    'prints nothing when the run ends %s, even with a test still running',
    (status) => {
      const { lines, r } = reporter();
      r.onTestBegin(second, result);
      r.onEnd(end(status));
      expect(lines).toEqual([]);
    },
  );

  it('does not name a test that began and ended before the global timeout', () => {
    const { lines, r } = reporter();
    r.onTestBegin(first, result);
    r.onTestEnd(first, result);
    r.onEnd(end('timedout'));
    expect(lines).toEqual([]);
  });

  it('names the test still running when the run reaches its global timeout', () => {
    const { lines, r } = reporter();
    r.onTestBegin(first, result);
    r.onTestEnd(first, result);
    r.onTestBegin(second, result);
    r.onEnd(end('timedout'));
    expect(lines).toEqual(['Interrupted by the global timeout: stall.spec.ts:5:5 › second test waits\n']);
  });

  it('names every running test, one per worker, in the order they began', () => {
    const { lines, r } = reporter();
    const nested = testCase('3', 'opens the sheet', `${ROOT}/sprint-03/stats.spec.ts`, 12, ['Stats', 'AN-04']);
    r.onTestBegin(nested, result);
    r.onTestBegin(second, result);
    r.onEnd(end('timedout'));
    expect(lines).toEqual([
      'Interrupted by the global timeout: sprint-03/stats.spec.ts:12:5 › Stats › AN-04 › opens the sheet\n',
      'Interrupted by the global timeout: stall.spec.ts:5:5 › second test waits\n',
    ]);
  });

  it('keeps a retried test named once, by its latest attempt', () => {
    const { lines, r } = reporter();
    r.onTestBegin(second, result);
    r.onTestEnd(second, result);
    r.onTestBegin(second, result);
    r.onEnd(end('timedout'));
    expect(lines).toHaveLength(1);
  });

  it('prints to stdio, so Playwright does not add a default reporter for it', () => {
    expect(new InterruptedTestsReporter().printsToStdio()).toBe(true);
  });
});

describe('interruptedLine', () => {
  it('uses the path relative to the root directory, the location and the title path', () => {
    expect(interruptedLine(second, ROOT)).toBe('Interrupted by the global timeout: stall.spec.ts:5:5 › second test waits');
  });
});
