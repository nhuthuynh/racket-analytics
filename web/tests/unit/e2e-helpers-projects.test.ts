// Unit tests for the Playwright projects (ST-065, PE-4 §10): the per-PR projects (chromium,
// webkit) never run the flag-on specs, and the `flags-on` project runs only them, only when named.
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
