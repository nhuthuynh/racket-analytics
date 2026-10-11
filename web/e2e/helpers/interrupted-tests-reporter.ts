// CI-STALL-SCENARIO-RACE (NFR-074): names the tests a global timeout interrupted.
//
// When a run reaches `--global-timeout`, Playwright 1.56.1 runs its teardown against the deadline
// that has already passed, prints the summary and exits without waiting for the worker to report
// the test it was running. The `list` reporter's line for that test therefore appears only when
// the worker answers first (main run 38103354166: it did not). This reporter remembers which tests
// began and have not ended, and names them when the run ends with status `timedout`, before
// Playwright exits. It is on the gated E2E step in ci.yml.
import path from 'node:path';
import type { FullConfig, FullResult, Reporter, Suite, TestCase } from '@playwright/test/reporter';

export const INTERRUPTED = 'Interrupted by the global timeout';

type Options = { write?: (text: string) => void };

/** `<file relative to rootDir>:<line>:<column> › <describe titles…> › <test title>`, as `list` prints a test. */
export function interruptedLine(test: TestCase, rootDir: string): string {
  const titles: string[] = [test.title];
  for (let suite: Suite | undefined = test.parent; suite?.type === 'describe'; suite = suite.parent)
    titles.unshift(suite.title);
  const { file, line, column } = test.location;
  const where = `${path.relative(rootDir, file).split(path.sep).join('/')}:${line}:${column}`;
  return `${INTERRUPTED}: ${[where, ...titles].join(' › ')}`;
}

export default class InterruptedTestsReporter implements Reporter {
  private readonly running = new Map<string, TestCase>();
  private readonly write: (text: string) => void;
  private rootDir = process.cwd();

  constructor(options: Options = {}) {
    this.write = options.write ?? ((text) => process.stdout.write(text));
  }

  onBegin(config: FullConfig): void {
    this.rootDir = config.rootDir;
  }

  onTestBegin(test: TestCase): void {
    this.running.delete(test.id); // a retry is named once, in the order of its latest attempt
    this.running.set(test.id, test);
  }

  onTestEnd(test: TestCase): void {
    this.running.delete(test.id);
  }

  onEnd(result: FullResult): void {
    if (result.status !== 'timedout') return;
    for (const test of this.running.values()) this.write(`${interruptedLine(test, this.rootDir)}\n`);
  }

  printsToStdio(): boolean {
    return true;
  }
}
