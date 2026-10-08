// Binds tests/features/e2e_route_isolation.feature (CI-WEBKIT-PD-R3S2-02) against real files:
// specs written to a temporary E2E directory, and the repository's own web/e2e tree.
import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { afterEach, describe, expect, it } from 'vitest';
import { checkSpecs } from '../../e2e/helpers/route-isolation';

const E2E_DIR = path.join(path.dirname(fileURLToPath(import.meta.url)), '../../e2e');
const FAKED_HISTORY = [
  "import { expect, test } from '@playwright/test';",
  "test('PD-R3S2-02 a failed history reload says so', async ({ page }) => {",
  "  await page.route('**/api/matches/m_1/corrections**', (route) => route.fulfill({ status: 503 }));",
  "  await page.goto('/matches/m_1/sheet');",
  '});',
];

let dirs: string[] = [];
afterEach(() => {
  for (const d of dirs) rmSync(d, { recursive: true, force: true });
  dirs = [];
});

/** Given an E2E directory holding one spec in sprint-03/ (the layout of web/e2e). */
function e2eDirWith(lines: string[]): string {
  const dir = mkdtempSync(path.join(tmpdir(), 'route-isolation-'));
  dirs.push(dir);
  mkdirSync(path.join(dir, 'sprint-03'));
  writeFileSync(path.join(dir, 'sprint-03', 'fe-minors.spec.ts'), lines.join('\n'));
  writeFileSync(path.join(dir, 'sprint-03', 'notes.md'), "page.route('**/x') in a non-spec file is not read");
  return dir;
}

describe('Feature: An E2E spec that fakes a response sees it in every browser', () => {
  it('Scenario: A spec that routes a request without blocking service workers is refused', () => {
    const dir = e2eDirWith(FAKED_HISTORY);
    expect(checkSpecs(dir)).toEqual([{ file: 'sprint-03/fe-minors.spec.ts', line: 3 }]);
  });

  it('Scenario: A spec that routes a request and blocks service workers passes', () => {
    const [imports, ...rest] = FAKED_HISTORY;
    const dir = e2eDirWith([imports!, '', "test.use({ serviceWorkers: 'block' });", ...rest]);
    expect(checkSpecs(dir)).toEqual([]);
  });

  it('Scenario: A spec that routes nothing needs no service worker setting', () => {
    const dir = e2eDirWith(FAKED_HISTORY.filter((l) => !l.includes('.route(')));
    expect(checkSpecs(dir)).toEqual([]);
  });

  it("Scenario: Every E2E spec in the repository routes only with service workers blocked", () => {
    // Positive control first: the tree is read at all (it holds specs that do route).
    expect(checkSpecs(e2eDirWith(FAKED_HISTORY))).toHaveLength(1);
    expect(
      checkSpecs(E2E_DIR),
      "these specs route a request without test.use({ serviceWorkers: 'block' }), so the route does not apply in WebKit",
    ).toEqual([]);
  });
});
