// CI-WEBKIT-PD-R3S2-02: a Playwright spec that fakes a response with page.route must block
// service workers. public/sw.js has a fetch handler and claims open pages, so in WebKit the
// page's fetches go through the worker and the route never sees them; Chromium still routes
// them, which is why fe-minors.spec.ts:24 (PD-R3S2-02) failed in WebKit only on CI.
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';
import { unisolatedRoutes } from '../../e2e/helpers/route-isolation';

// The PD-R3S2-02 spec as it failed in WebKit (sprint-03 web/e2e/sprint-03/fe-minors.spec.ts:24-29).
const ROUTES_WITHOUT_BLOCK = [
  "import { expect, test } from '@playwright/test';",
  '',
  "test('PD-R3S2-02 a failed history reload says so', async ({ page }) => {",
  '  let failing = true;',
  '  await page.route(`**/api/matches/${matchId}/corrections**`, (route) =>',
  "    failing ? route.fulfill({ status: 503 }) : route.continue(),",
  '  );',
  '});',
].join('\n');

const BLOCK = "test.use({ serviceWorkers: 'block' });";

describe('unisolatedRoutes', () => {
  it('names the line of a page.route in a spec that does not block service workers', () => {
    expect(unisolatedRoutes(ROUTES_WITHOUT_BLOCK)).toEqual([5]);
  });

  it('names every route call: page.route, context.route and routeFromHAR', () => {
    const source = [
      "await page.route('**/api/a', handler);",
      "await context.route(/X-Amz-Signature=/, handler);",
      "await page.routeFromHAR('fixtures/api.har');",
    ].join('\n');
    expect(unisolatedRoutes(source)).toEqual([1, 2, 3]);
  });

  it("still names the route when service workers are allowed or the block is only in a comment", () => {
    expect(unisolatedRoutes(`test.use({ serviceWorkers: 'allow' });\n${ROUTES_WITHOUT_BLOCK}`)).toEqual([6]);
    expect(unisolatedRoutes(`// ${BLOCK}\n${ROUTES_WITHOUT_BLOCK}`)).toEqual([6]);
    expect(unisolatedRoutes(`/*\n${BLOCK}\n*/\n${ROUTES_WITHOUT_BLOCK}`)).toEqual([8]);
  });

  it('ignores a route call that is only in a comment', () => {
    expect(unisolatedRoutes("// page.route('**/api/a', handler) is not used here\n/* context.route(x) */")).toEqual([]);
  });

  it('names nothing when the spec blocks service workers, with either quote style', () => {
    expect(unisolatedRoutes(`${BLOCK}\n${ROUTES_WITHOUT_BLOCK}`)).toEqual([]);
    expect(unisolatedRoutes(`test.use({ serviceWorkers: "block" }); // routes the API\n${ROUTES_WITHOUT_BLOCK}`)).toEqual([]);
  });

  it('names nothing when the spec routes no request (unroute and route handlers do not count)', () => {
    expect(unisolatedRoutes("await page.unroute(url, handler);\nawait route.fulfill({ status: 200 });\nconst router = 1;")).toEqual([]);
  });

  // Review round 1 (PE-R1-01, F1): "/*" and "*/" inside strings are not comments.
  it('names a route that follows a glob holding "/*" (negative case first)', () => {
    const source = [
      "const ALL = '**/api/**';",
      "test('x', async ({ page }) => {",
      "  await page.route('**/api/matches/m_1/corrections', (r) => r.fulfill({ status: 503 }));",
      '});',
    ].join('\n');
    expect(unisolatedRoutes(source)).toEqual([3]);
    expect(unisolatedRoutes("await page.route('**/api/a/**', h);\nawait page.route('**/api/b', h);")).toEqual([1, 2]);
    expect(unisolatedRoutes("await page.waitForURL('**/matches/**');\nawait page.route('**/x', h);")).toEqual([2]);
  });

  it('treats comment markers in template literals and regex literals as code, not comments', () => {
    expect(unisolatedRoutes('const a = `**/api/**`;\nawait page.route(`**/api/${id}`, h);')).toEqual([2]);
    expect(unisolatedRoutes('const re = /a\\/*b/;\nawait page.route(re, h);')).toEqual([2]);
  });

  it('sees a block that sits between two globs', () => {
    const source = ["await page.route('**/uploads/**', h);", BLOCK, "await page.goto('**/x');"].join('\n');
    expect(unisolatedRoutes(source)).toEqual([]);
  });

  it('names every route of a real spec once its block is changed to allow', () => {
    const e2e = path.join(path.dirname(fileURLToPath(import.meta.url)), '../../e2e');
    for (const [spec, lines] of [
      ['sprint-01/resumable-upload.spec.ts', [18, 67, 88, 151]],
      ['walking-skeleton.spec.ts', [46, 89]],
    ] as const) {
      const source = readFileSync(path.join(e2e, spec), 'utf8');
      expect(unisolatedRoutes(source), spec).toEqual([]);
      expect(unisolatedRoutes(source.replace("serviceWorkers: 'block'", "serviceWorkers: 'allow'")), spec).toEqual(lines);
    }
  });
});
