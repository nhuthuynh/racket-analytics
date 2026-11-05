// @vitest-environment node
// Binds web/tests/features/playwright_projects.feature (ST-079; NFR-024.1-.3; G05-04). Each scenario
// runs the real Playwright CLI on the real web/playwright.config.ts with `--list`, which loads the
// config and every spec but launches no browser. The first test checks every scenario is bound.
import { spawnSync } from 'node:child_process';
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

const WEB = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const FEATURE = readFileSync(path.join(WEB, 'tests/features/playwright_projects.feature'), 'utf8');
const PLAYWRIGHT = path.join(WEB, 'node_modules/.bin/playwright');
const PROJECTS = ['chromium', 'webkit', 'android-chrome'];
const SCENARIOS = {
  listed: 'The critical journeys are listed in the "<project>" project',
  unknown: 'An unknown project name is refused (negative)',
};

interface Listed {
  file: string;
  title: string;
  project: string;
}

/** `PW_PROJECTS=<names> playwright test --list --grep @critical --reporter json`. */
function listCritical(names: string) {
  const env: NodeJS.ProcessEnv = { ...process.env, PW_PROJECTS: names };
  delete env.CI;
  const run = spawnSync(PLAYWRIGHT, ['test', '--list', '--grep', '@critical', '--reporter', 'json'], {
    cwd: WEB, env, encoding: 'utf8', timeout: 120_000,
  });
  return { status: run.status, stderr: `${run.stdout}\n${run.stderr}`, tests: run.status === 0 ? flatten(JSON.parse(run.stdout)) : [] };
}

interface Suite {
  file?: string;
  suites?: Suite[];
  specs?: { file: string; title: string; tests: { projectName: string }[] }[];
}

function flatten(report: { suites?: Suite[] }): Listed[] {
  const out: Listed[] = [];
  const walk = (s: Suite) => {
    for (const spec of s.specs ?? []) for (const t of spec.tests) out.push({ file: spec.file, title: spec.title, project: t.projectName });
    for (const child of s.suites ?? []) walk(child);
  };
  for (const s of report.suites ?? []) walk(s);
  return out;
}

describe('Feature: The browser matrix projects list the critical journeys', () => {
  it('binds every scenario of playwright_projects.feature', () => {
    const names = [...FEATURE.matchAll(/^\s*Scenario(?: Outline)?: (.+)$/gm)].map((m) => m[1]);
    expect(names).toEqual(Object.values(SCENARIOS));
  });

  describe.each(PROJECTS)(`Scenario: ${SCENARIOS.listed.replace('<project>', '%s')}`, (project) => {
    it(`lists E2E-04-01..05, sign-in and upload resume in ${project} only`, () => {
      const { status, stderr, tests } = listCritical(project);
      expect(status, stderr).toBe(0);
      expect(new Set(tests.map((t) => t.project))).toEqual(new Set([project]));
      for (const id of ['E2E-04-01', 'E2E-04-02', 'E2E-04-03', 'E2E-04-04', 'E2E-04-05', 'E2E-01-02']) {
        expect(tests.some((t) => t.title.includes(id)), `${id} listed in ${project}`).toBe(true);
      }
      expect(tests.some((t) => t.file.endsWith('sign-in.spec.ts')), `sign-in listed in ${project}`).toBe(true);
      expect(tests.every((t) => !t.file.includes('flags-on')), 'no flag-on spec').toBe(true);
    }, 120_000);
  });

  it(`Scenario: ${SCENARIOS.unknown}`, () => {
    const { status, stderr } = listCritical('android-firefox');
    expect(status).not.toBe(0);
    expect(stderr).toContain('android-firefox');
  }, 120_000);
});
