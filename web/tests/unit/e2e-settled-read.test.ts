// CI-E2E-MAIN-RED: a Playwright spec must not read page text straight after a navigation.
// The match page streams (/matches/loading.tsx), so "Page not found" replaces the "Loading…"
// fallback only after React runs; page.goto resolves on the load event, which can come first.
// object-level-authorisation.spec.ts:26 read "Loading…" in WebKit on main run 37905693381.
import { describe, expect, it } from 'vitest';
import { unsettledReads } from '../../e2e/helpers/settled-read';

// The ST-006 spec as it failed in WebKit (web/e2e/object-level-authorisation.spec.ts:18-26 at bfe6f33).
const READ_AFTER_GOTO = [
  "import { expect, test } from '@playwright/test';",
  "test('Carlos cannot open Ivy\\'s match', async ({ browser }) => {",
  '  const carlos = await (await browser.newContext()).newPage();',
  '  await carlos.goto(ivysMatch);',
  "  const notYours = (await carlos.getByRole('main').innerText()).trim();",
  "  await carlos.goto(ivysMatch.replace(/[0-9a-f-]{36}/i, MISSING));",
  "  const missing = (await carlos.getByRole('main').innerText()).trim();",
  '  expect(notYours).toMatch(/not found/i);',
  '});',
].join('\n');

const WAIT = "  await expect(carlos.getByRole('heading', { level: 1 })).toHaveText('Page not found');";

describe('unsettledReads', () => {
  it('names the line of every text read that follows a navigation with no wait', () => {
    expect(unsettledReads(READ_AFTER_GOTO)).toEqual([5, 7]);
  });

  it('names innerText, textContent, allInnerTexts, allTextContents and innerHTML reads', () => {
    const source = [
      "test('x', async ({ page }) => {",
      "  await page.goto('/a');",
      "  await page.locator('main').textContent();",
      "  await page.locator('li').allInnerTexts();",
      "  await page.locator('li').allTextContents();",
      "  await page.locator('main').innerHTML();",
      '});',
    ].join('\n');
    expect(unsettledReads(source)).toEqual([3, 4, 5, 6]);
  });

  it('treats reload, goBack and goForward as navigations too', () => {
    const source = [
      "test('x', async ({ page }) => {",
      '  await page.reload();',
      "  const a = await page.locator('main').innerText();",
      '  await page.goBack();',
      "  const b = await page.locator('main').innerText();",
      '  await page.goForward();',
      "  const c = await page.locator('main').innerText();",
      '});',
    ].join('\n');
    expect(unsettledReads(source)).toEqual([3, 5, 7]);
  });

  it('accepts a read after an awaited web-first assertion', () => {
    const lines = READ_AFTER_GOTO.split('\n');
    const waited = [...lines.slice(0, 4), WAIT, lines[4], lines[5], WAIT, ...lines.slice(6)].join('\n');
    expect(unsettledReads(waited)).toEqual([]);
  });

  it('accepts a read after an explicit wait: waitFor, waitForURL, waitForResponse, waitForSelector, waitForFunction', () => {
    for (const wait of [
      "await page.locator('h1').waitFor();",
      "await page.waitForURL('**/matches/**');",
      "await page.waitForResponse('**/api/matches/**');",
      "await page.waitForSelector('h1');",
      'await page.waitForFunction(() => document.readyState === "complete");',
    ]) {
      const source = ["await page.goto('/a');", wait, "await page.locator('main').innerText();"].join('\n');
      expect(unsettledReads(source), wait).toEqual([]);
    }
  });

  it('does not count waitForLoadState or waitForTimeout as a wait (neither waits for the content)', () => {
    for (const wait of ["await page.waitForLoadState('networkidle');", 'await page.waitForTimeout(500);']) {
      const source = ["await page.goto('/a');", wait, "await page.locator('main').innerText();"].join('\n');
      expect(unsettledReads(source), wait).toEqual([3]);
    }
  });

  it('does not count a plain assertion on a value read earlier as a wait', () => {
    const source = [
      "await page.goto('/a');",
      "const title = await page.title();",
      'expect(title).toBe("x");',
      "await page.locator('main').innerText();",
    ].join('\n');
    expect(unsettledReads(source)).toEqual([4]);
  });

  it('names nothing in a spec that reads text without navigating in that function', () => {
    const source = [
      "test('x', async ({ page }) => {",
      '  await requestLink(page, email);',
      "  const text = await page.locator('main').innerText();",
      '});',
    ].join('\n');
    expect(unsettledReads(source)).toEqual([]);
  });

  it('keeps each function apart: a navigation in one test does not taint another', () => {
    const source = [
      "test('a', async ({ page }) => { await page.goto('/a'); });",
      "test('b', async ({ page }) => {",
      "  const text = await page.locator('main').innerText();",
      '});',
    ].join('\n');
    expect(unsettledReads(source)).toEqual([]);
  });

  it('ignores reads and navigations in comments and strings', () => {
    const source = [
      "// await page.goto('/a');",
      "const doc = \"await page.goto('/a')\";",
      "await page.locator('main').innerText();",
    ].join('\n');
    expect(unsettledReads(source)).toEqual([]);
  });
});
