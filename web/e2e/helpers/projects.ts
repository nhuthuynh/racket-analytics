// Playwright projects (ST-004 browser matrix; ST-065 `flags-on`, PE-4 §10). Per PR, CI runs
// `chromium` (Google Chrome on CI, browser-channel.ts) and `webkit`; neither runs the flag-on
// specs. `flags-on` runs only the specs under e2e/sprint-04/flags-on/, only when PW_PROJECTS
// names it, against a stack started with the four FEATURE_* variables (nightly, verifier).
// `android-chrome` (ST-079, NFR-024.3) emulates a Pixel 7 in the same Chrome as `chromium`; the
// nightly browser matrix runs it with the other two (goal-scorecard G05-04).
import { devices, type PlaywrightTestProject as Project } from '@playwright/test';

export const FLAGS_ON = 'flags-on';
/** The public config's flag names (GET /config/public `features`, ST-067). */
export const FLAG_NAMES = ['age_gate', 'retention_setting', 'training_consent', 'quotas'] as const;
const FLAG_SPECS = /[\\/]sprint-04[\\/]flags-on[\\/][^\\/]+\.spec\.ts$/;

export const ANDROID_CHROME = 'android-chrome';
export const PROJECT_NAMES = ['chromium', 'webkit', ANDROID_CHROME, FLAGS_ON] as const;

/** PW_PROJECTS as a list; default the per-PR pair. A name that is no project fails (a typo would run nothing). */
export function projectNames(env: Record<string, string | undefined>): string[] {
  const names = (env.PW_PROJECTS ?? 'chromium,webkit').split(',').map((p) => p.trim()).filter(Boolean);
  const unknown = names.filter((n) => !(PROJECT_NAMES as readonly string[]).includes(n));
  if (unknown.length > 0) {
    throw new Error(`PW_PROJECTS names no such project: ${unknown.join(', ')} (projects: ${PROJECT_NAMES.join(', ')})`);
  }
  return names;
}

export function e2eProjects({ names, channel, chromiumArgs }: { names: string[]; channel?: string; chromiumArgs: string[] }): Project[] {
  const chromeOf = (device: (typeof devices)[string]) => ({
    ...device,
    ...(channel ? { channel } : {}),
    launchOptions: { args: chromiumArgs },
  });
  const chrome = chromeOf(devices['Desktop Chrome']);
  const all: Project[] = [
    { name: 'chromium', use: chrome, testIgnore: FLAG_SPECS },
    { name: 'webkit', use: { ...devices['iPhone 13'] }, testIgnore: FLAG_SPECS },
    { name: ANDROID_CHROME, use: chromeOf(devices['Pixel 7']), testIgnore: FLAG_SPECS },
    { name: FLAGS_ON, use: chrome, testMatch: FLAG_SPECS },
  ];
  return all.filter((p) => names.includes(p.name ?? ''));
}
