// Unit tests for the Playwright projects (ST-065, PE-4 §10): the per-PR projects (chromium,
// webkit) never run the flag-on specs, and the `flags-on` project runs only them, only when named.
import { devices } from '@playwright/test';
import { describe, expect, it } from 'vitest';
import { FLAGS_ON, e2eProjects, projectNames } from '../../e2e/helpers/projects';

const FLAG_SPEC = '/repo/web/e2e/sprint-04/flags-on/age-gate.spec.ts';
const JOURNEY_SPEC = '/repo/web/e2e/sprint-04/journey-v3.spec.ts';

function matches(pattern: unknown, file: string): boolean {
  const list = Array.isArray(pattern) ? pattern : [pattern];
  return list.some((p) => p instanceof RegExp && p.test(file));
}

describe('Playwright projects', () => {
  it('does not run the flags-on project by default (CI per PR runs chromium and webkit only)', () => {
    expect(projectNames({})).toEqual(['chromium', 'webkit']);
    expect(e2eProjects({ names: projectNames({}), chromiumArgs: [] }).map((p) => p.name)).toEqual(['chromium', 'webkit']);
  });

  it('keeps the flag-on specs out of the per-PR projects', () => {
    for (const p of e2eProjects({ names: ['chromium', 'webkit'], chromiumArgs: [] })) {
      expect(matches(p.testIgnore, FLAG_SPEC), `${p.name} ignores flag-on specs`).toBe(true);
      expect(matches(p.testIgnore, JOURNEY_SPEC), `${p.name} runs the journey`).toBe(false);
    }
  });

  it('runs only the flag-on specs in the flags-on project, when PW_PROJECTS names it', () => {
    const names = projectNames({ PW_PROJECTS: ' flags-on ' });
    expect(names).toEqual([FLAGS_ON]);
    const [flags] = e2eProjects({ names, channel: 'chrome', chromiumArgs: ['--x'] });
    expect(flags?.name).toBe('flags-on');
    expect(matches(flags?.testMatch, FLAG_SPEC)).toBe(true);
    expect(matches(flags?.testMatch, JOURNEY_SPEC)).toBe(false);
    expect(flags?.use?.channel).toBe('chrome');
    expect(flags?.use?.launchOptions?.args).toEqual(['--x']);
  });

  it('passes the Chrome channel and the dev-certificate arguments to chromium only', () => {
    const [chromium, webkit] = e2eProjects({ names: ['chromium', 'webkit'], channel: 'chrome', chromiumArgs: ['--a'] });
    expect(chromium?.use?.channel).toBe('chrome');
    expect(chromium?.use?.launchOptions?.args).toEqual(['--a']);
    expect(webkit?.use?.channel).toBeUndefined();
    expect(webkit?.use?.defaultBrowserType).toBe('webkit');
  });
});

// ST-079 (NFR-024.3; G05-04): the Android phone project of the browser matrix, and PW_PROJECTS
// refusing a name that is not a project (BA-5 negative scenario: "android-firefox").
describe('Playwright projects: android-chrome (ST-079)', () => {
  it('emulates a Pixel 7 (mobile, touch, its viewport and user agent) in Chromium', () => {
    const [android] = e2eProjects({ names: ['android-chrome'], chromiumArgs: ['--a'] });
    expect(android?.name).toBe('android-chrome');
    expect(android?.use?.defaultBrowserType).toBe('chromium');
    expect(android?.use?.isMobile).toBe(true);
    expect(android?.use?.hasTouch).toBe(true);
    expect(android?.use?.viewport).toEqual(devices['Pixel 7'].viewport);
    expect(android?.use?.userAgent).toBe(devices['Pixel 7'].userAgent);
    expect(android?.use?.launchOptions?.args).toEqual(['--a']);
    expect(android?.use?.channel).toBeUndefined();
  });

  it('launches Google Chrome when the Chrome channel is given (CI), as chromium does', () => {
    const [android] = e2eProjects({ names: ['android-chrome'], channel: 'chrome', chromiumArgs: [] });
    expect(android?.use?.channel).toBe('chrome');
  });

  it('keeps the flag-on specs out, like the other per-browser projects', () => {
    const [android] = e2eProjects({ names: ['android-chrome'], chromiumArgs: [] });
    expect(matches(android?.testIgnore, FLAG_SPEC)).toBe(true);
    expect(matches(android?.testIgnore, JOURNEY_SPEC)).toBe(false);
  });

  it('resolves the three matrix projects named in PW_PROJECTS, in that order', () => {
    const names = projectNames({ PW_PROJECTS: 'chromium,webkit,android-chrome' });
    expect(e2eProjects({ names, chromiumArgs: [] }).map((p) => p.name)).toEqual(['chromium', 'webkit', 'android-chrome']);
  });

  it('refuses a PW_PROJECTS name that is not a project, naming it', () => {
    expect(() => projectNames({ PW_PROJECTS: 'android-firefox' })).toThrow(/android-firefox/);
    expect(() => projectNames({ PW_PROJECTS: 'chromium,andriod-chrome' })).toThrow(/andriod-chrome/);
  });
});
