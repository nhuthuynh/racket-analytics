// Binds tests/features/e2e_settled_read.feature (CI-E2E-MAIN-RED) against real files:
// specs written to a temporary E2E directory, and the repository's own web/e2e tree.
import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { afterEach, describe, expect, it } from 'vitest';
import { checkSpecs } from '../../e2e/helpers/settled-read';

const E2E_DIR = path.join(path.dirname(fileURLToPath(import.meta.url)), '../../e2e');
const OPEN_IVYS_MATCH = [
  "import { expect, test } from '@playwright/test';",
  "test('Carlos cannot open Ivy\\'s match', async ({ browser }) => {",
  '  const carlos = await (await browser.newContext()).newPage();',
  '  await carlos.goto(ivysMatch);',
];
const READ = "  const notYours = (await carlos.getByRole('main').innerText()).trim();";
const ASSERT_READ = '  expect(notYours).toMatch(/not found/i);';
const WAIT = "  await expect(carlos.getByRole('heading', { level: 1 })).toHaveText('Page not found');";

let dirs: string[] = [];
afterEach(() => {
  for (const d of dirs) rmSync(d, { recursive: true, force: true });
  dirs = [];
});

/** Given an E2E directory holding one spec at its root (the layout of web/e2e). */
function e2eDirWith(lines: string[]): string {
  const dir = mkdtempSync(path.join(tmpdir(), 'settled-read-'));
  dirs.push(dir);
  mkdirSync(path.join(dir, 'helpers'));
  writeFileSync(path.join(dir, 'object-level-authorisation.spec.ts'), [...lines, '});'].join('\n'));
  writeFileSync(path.join(dir, 'helpers', 'journey.ts'), [...OPEN_IVYS_MATCH, READ, '});'].join('\n'));
  return dir;
}

describe('Feature: An E2E spec reads a page only after the page has settled', () => {
  it('Scenario: A spec that reads the page text straight after a navigation is refused', () => {
    const dir = e2eDirWith([...OPEN_IVYS_MATCH, READ]);
    expect(checkSpecs(dir)).toEqual([{ file: 'object-level-authorisation.spec.ts', line: 5 }]);
  });

  it('Scenario: A spec that waits for the not-found heading before it reads passes', () => {
    const dir = e2eDirWith([...OPEN_IVYS_MATCH, WAIT, READ]);
    expect(checkSpecs(dir)).toEqual([]);
  });

  it('Scenario: A plain assertion on a value read earlier is not a wait', () => {
    const dir = e2eDirWith([...OPEN_IVYS_MATCH, READ, ASSERT_READ]);
    expect(checkSpecs(dir)).toEqual([{ file: 'object-level-authorisation.spec.ts', line: 5 }]);
  });

  it("Scenario: Every E2E spec in the repository reads a page only after it has settled", () => {
    // Positive control first: the check refuses a known-bad spec, so an empty result below means
    // the tree passed, not that the check is blind.
    expect(checkSpecs(e2eDirWith([...OPEN_IVYS_MATCH, READ]))).toHaveLength(1);
    expect(
      checkSpecs(E2E_DIR),
      'these specs read page text straight after a navigation; wait for the expected content first (web-first assertion)',
    ).toEqual([]);
  });
});
