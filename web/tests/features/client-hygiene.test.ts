// @vitest-environment node
// Binds web/tests/features/client_hygiene.feature (ST-078e). Each scenario names the test that is
// its integration level (the browser test, the web-origin IT) or its handler-level check (SW,
// sign-out clear, hydration lock); this check fails when a scenario is added without a binding,
// or when the bound test is renamed, skipped or removed.
import { existsSync, readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

const WEB = path.join(path.dirname(fileURLToPath(import.meta.url)), '../..');
const FEATURE = readFileSync(path.join(WEB, 'tests/features/client_hygiene.feature'), 'utf8');

/** Scenario -> [file from web/, a title the file must hold in an active test]. */
const BINDINGS: Record<string, [string, string][]> = {
  'Sign-out empties local storage, session storage, IndexedDB and the account caches': [
    ['e2e/sprint-05/logout-hygiene.spec.ts', 'Sign-out empties local storage, session storage, IndexedDB and the account caches'],
  ],
  'Sign-out removes media even from the app-file cache': [
    ['e2e/sprint-05/logout-hygiene.spec.ts', 'Sign-out removes media even from the app-file cache'],
    ['tests/unit/sign-out-hygiene.test.ts', 'removes media files from the app-file cache and keeps the hashed app files'],
  ],
  'A media file under the app-file path is never stored': [
    ['tests/unit/sw-cache.test.ts', 'leaves a .%s file under the app-file path to the network'],
  ],
  'A media answer is never stored, whatever its path': [
    ['tests/unit/sw-cache.test.ts', 'passes on a %s answer under an app-file path without storing it'],
  ],
  'A partial answer is never stored': [['tests/unit/sw-cache.test.ts', 'passes on a 206 partial answer without storing it']],
  'Pages, app files, the service worker and the manifest carry the security headers': [
    ['../backend/tests/integration/test_it_05_security_headers.py', 'def test_every_web_answer_has_csp_nosniff_and_frame_denial'],
  ],
  'Every form with a submit handler is locked in the server HTML': [
    ['tests/unit/hydration-lock.test.tsx', 'every source file with an onSubmit form is covered here'],
  ],
};

const scenarios = [...FEATURE.matchAll(/^\s*Scenario: (.+)$/gm)].map((m) => m[1]!.trim());

describe('Feature binding: client hygiene (client_hygiene.feature)', () => {
  it('every scenario has a binding, and every binding a scenario', () => {
    expect(scenarios.length).toBeGreaterThan(0);
    expect([...scenarios].sort()).toEqual(Object.keys(BINDINGS).sort());
  });

  it.each(Object.entries(BINDINGS))('%s is bound to an active test', (_scenario, bindings) => {
    for (const [file, title] of bindings) {
      const full = path.join(WEB, file);
      expect(existsSync(full), file).toBe(true);
      const text = readFileSync(full, 'utf8');
      expect(text, `${file} holds "${title}"`).toContain(title);
      expect(text, `${file} skips nothing`).not.toMatch(/\b(it|test|describe)\.(skip|fixme|todo)\(|pytest\.mark\.skip/);
    }
  });
});
