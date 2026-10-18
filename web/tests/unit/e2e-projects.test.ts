// FIX-04-1f (G04-07; api-sprint-04 §1 "Flag-on E2E"): which Playwright projects run, and which
// specs each runs. The flags-on project runs web/e2e/sprint-04/flags-on/*.spec.ts only, against
// a stack started with every FEATURE_* on; the per-PR chromium and webkit projects never do.
// Negative cases first.
import type { Project } from '@playwright/test';
import { describe, expect, it } from 'vitest';
import { e2eProjects, isFlagOnSpec, selectedProjects } from '../../e2e/helpers/projects';

const SPEC_ROOT = '/repo/web/e2e';
const FLAG_ON = `${SPEC_ROOT}/sprint-04/flags-on/age.spec.ts`;
const PLAIN = `${SPEC_ROOT}/sprint-04/journey-v3.spec.ts`;

/** Whether a project's testMatch/testIgnore (each a RegExp here) lets Playwright run the file. */
function runs(project: Project | undefined, file: string): boolean {
  const { testMatch, testIgnore } = project ?? {};
  if (testIgnore instanceof RegExp && testIgnore.test(file)) return false;
  return testMatch instanceof RegExp ? testMatch.test(file) : testMatch === undefined;
}

describe('selectedProjects', () => {
  it('refuses an unknown project name and names the known ones', () => {
    expect(() => selectedProjects({ PW_PROJECTS: 'chromuim' })).toThrow(
      /PW_PROJECTS=chromuim.*chromium, webkit, flags-on/,
    );
  });

  it('refuses an empty selection instead of running nothing', () => {
    expect(() => selectedProjects({ PW_PROJECTS: ' , ' })).toThrow(/PW_PROJECTS/);
  });

  it('runs the per-PR browsers by default, never the flag-on project', () => {
    expect(selectedProjects({})).toEqual(['chromium', 'webkit']);
  });

  it('accepts flags-on, with spaces around names', () => {
    expect(selectedProjects({ PW_PROJECTS: ' flags-on ' })).toEqual(['flags-on']);
    expect(selectedProjects({ PW_PROJECTS: 'chromium, flags-on' })).toEqual(['chromium', 'flags-on']);
  });
});

describe('isFlagOnSpec', () => {
  it('is false for a spec outside a flags-on directory, even with flags-on in its name', () => {
    expect(isFlagOnSpec(PLAIN)).toBe(false);
    expect(isFlagOnSpec(`${SPEC_ROOT}/sprint-04/flags-on-notes.spec.ts`)).toBe(false);
    expect(isFlagOnSpec(`${SPEC_ROOT}/sprint-04/flags-on/helpers.ts`)).toBe(false);
  });

  it('is true for a spec in sprint-04/flags-on/, with either path separator', () => {
    expect(isFlagOnSpec(FLAG_ON)).toBe(true);
    expect(isFlagOnSpec('C:\\repo\\web\\e2e\\sprint-04\\flags-on\\settings.spec.ts')).toBe(true);
  });
});

describe('e2eProjects', () => {
  const opts = { channel: 'chrome', chromiumArgs: ['--ignore-certificate-errors'] };

  it('keeps flag-on specs out of the chromium and webkit projects', () => {
    const projects = e2eProjects({ PW_PROJECTS: 'chromium,webkit' }, opts);
    expect(projects.map((p) => p.name)).toEqual(['chromium', 'webkit']);
    for (const p of projects) {
      expect(runs(p, FLAG_ON)).toBe(false);
      expect(runs(p, PLAIN)).toBe(true);
    }
  });

  it('runs only flag-on specs in the flags-on project', () => {
    const [flagsOn] = e2eProjects({ PW_PROJECTS: 'flags-on' }, opts);
    expect(flagsOn?.name).toBe('flags-on');
    expect(runs(flagsOn, FLAG_ON)).toBe(true);
    expect(runs(flagsOn, PLAIN)).toBe(false);
  });

  it('runs the flags-on project in the same desktop Chrome as the chromium project', () => {
    const [chromium, flagsOn] = e2eProjects({ PW_PROJECTS: 'chromium,flags-on' }, opts);
    expect(flagsOn?.use).toEqual(chromium?.use);
    expect(flagsOn?.use).toMatchObject({
      channel: 'chrome',
      defaultBrowserType: 'chromium',
      launchOptions: { args: ['--ignore-certificate-errors'] },
    });
  });

  it('omits the channel when none is chosen (the bundled Chromium)', () => {
    const projects = e2eProjects({ PW_PROJECTS: 'chromium' }, { chromiumArgs: [] });
    expect(projects[0]?.use).not.toHaveProperty('channel');
  });
});
