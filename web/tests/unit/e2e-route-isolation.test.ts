// CI-WEBKIT-PD-R3S2-02: a Playwright spec that fakes a response with page.route must block
// service workers. public/sw.js has a fetch handler and claims open pages, so in WebKit the
// page's fetches go through the worker and the route never sees them; Chromium still routes
// them, which is why fe-minors.spec.ts:24 (PD-R3S2-02) failed in WebKit only on CI.
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
});
