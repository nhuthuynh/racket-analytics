// Which Playwright projects run, and which specs each runs (FIX-04-1f; G04-07; api-sprint-04 §1
// "Flag-on E2E"). chromium and webkit are the per-PR browsers on a stack with every FEATURE_*
// off; flags-on runs web/e2e/sprint-04/flags-on/*.spec.ts (E2E-04-06..08) in the same desktop
// Chrome, on a stack started with every FEATURE_* on, nightly and by the verifier. A flag-on spec
// never runs in a per-PR browser, and an unknown PW_PROJECTS name is refused instead of
// selecting no project ("No tests found" measured nothing).
import { devices, type Project } from '@playwright/test';

export const KNOWN_PROJECTS = ['chromium', 'webkit', 'flags-on'] as const;
export type ProjectName = (typeof KNOWN_PROJECTS)[number];

const DEFAULT_PROJECTS = 'chromium,webkit';
const FLAG_ON_SPEC = /[\\/]flags-on[\\/][^\\/]+\.spec\.ts$/;

export function isFlagOnSpec(file: string): boolean {
  return FLAG_ON_SPEC.test(file);
}

export function selectedProjects(env: Record<string, string | undefined>): ProjectName[] {
  const asked = env.PW_PROJECTS ?? DEFAULT_PROJECTS;
  const names = asked.split(',').map((p) => p.trim()).filter((p) => p !== '');
  const known = KNOWN_PROJECTS.join(', ');
  const unknown = names.filter((n) => !(KNOWN_PROJECTS as readonly string[]).includes(n));
  if (names.length === 0 || unknown.length > 0) {
    throw new Error(`PW_PROJECTS=${asked} must name Playwright projects from: ${known}`);
  }
  return names as ProjectName[];
}

export interface ProjectOptions {
  channel?: string;
  chromiumArgs: string[];
}

export function e2eProjects(env: Record<string, string | undefined>, opts: ProjectOptions): Project[] {
  const desktopChrome = {
    ...devices['Desktop Chrome'],
    ...(opts.channel ? { channel: opts.channel } : {}),
    launchOptions: { args: opts.chromiumArgs },
  };
  const all: Record<ProjectName, Project> = {
    chromium: { name: 'chromium', testIgnore: FLAG_ON_SPEC, use: desktopChrome },
    webkit: { name: 'webkit', testIgnore: FLAG_ON_SPEC, use: { ...devices['iPhone 13'] } },
    'flags-on': { name: 'flags-on', testMatch: FLAG_ON_SPEC, use: desktopChrome },
  };
  return selectedProjects(env).map((name) => all[name]);
}
