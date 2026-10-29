// Playwright projects (ST-004 browser matrix; ST-065 `flags-on`, PE-4 §10). Per PR, CI runs
// `chromium` (Google Chrome on CI, browser-channel.ts) and `webkit`; neither runs the flag-on
// specs. `flags-on` runs only the specs under e2e/sprint-04/flags-on/, only when PW_PROJECTS
// names it, against a stack started with the four FEATURE_* variables (nightly, verifier).
import { devices, type PlaywrightTestProject as Project } from '@playwright/test';

export const FLAGS_ON = 'flags-on';
/** The public config's flag names (GET /config/public `features`, ST-067). */
export const FLAG_NAMES = ['age_gate', 'retention_setting', 'training_consent', 'quotas'] as const;
const FLAG_SPECS = /[\\/]sprint-04[\\/]flags-on[\\/][^\\/]+\.spec\.ts$/;

/** PW_PROJECTS as a list; default the per-PR pair. */
export function projectNames(env: Record<string, string | undefined>): string[] {
  return (env.PW_PROJECTS ?? 'chromium,webkit').split(',').map((p) => p.trim()).filter(Boolean);
}

export function e2eProjects({ names, channel, chromiumArgs }: { names: string[]; channel?: string; chromiumArgs: string[] }): Project[] {
  const chrome = {
    ...devices['Desktop Chrome'],
    ...(channel ? { channel } : {}),
    launchOptions: { args: chromiumArgs },
  };
  const all: Project[] = [
    { name: 'chromium', use: chrome, testIgnore: FLAG_SPECS },
    { name: 'webkit', use: { ...devices['iPhone 13'] }, testIgnore: FLAG_SPECS },
    { name: FLAGS_ON, use: chrome, testMatch: FLAG_SPECS },
  ];
  return all.filter((p) => names.includes(p.name ?? ''));
}
