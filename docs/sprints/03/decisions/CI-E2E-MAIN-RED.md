# CI-E2E-MAIN-RED decisions

Small decisions for ticket CI-E2E-MAIN-RED (root-cause the E2E failure on main run 37905693381, merge of PR #43 at `bfe6f33`, job 113748522312), one dated row each. One file per ticket (PO rule 2026-10-07).

| Date | Who | Decision | Evidence | Reasoning |
|---|---|---|---|---|
| 2026-10-09 | senior-frontend-engineer | **Cause: the spec reads the page before the streamed not-found has replaced the Loading fallback; not a product defect.** `web/src/app/matches/loading.tsx` puts every `/matches/*` page in a Suspense boundary, so the server sends the shell with "Loading…" first. For another player's match (and a missing one) the API answers 404 and the page calls `notFound()` after the shell is sent: the response is HTTP 200, the HTML holds only the fallback, and the stream carries `NEXT_HTTP_ERROR_FALLBACK;404`, which React turns into "Page not found" once it runs in the browser. `page.goto` resolves on the load event, which can come before that, so `getByRole('main').innerText()` read straight after it gets "Loading…" when the browser is slow (WebKit on a shared CI runner). Same response for both cases, so the no-existence-oracle property (ST-006) holds | CI log, job 113748522312: `[webkit] e2e/object-level-authorisation.spec.ts:26 … Expected pattern: /not found/i Received string: "Loading…"`, 1 failed / 211 passed. Local stack (`docker compose -p racket-cie2e … up -d --build --wait` at `149e28e`, HTTPS on :3000): `carlos.request.get('/matches/00000000-…')` → status 200, `NEXT_HTTP_ERROR_FALLBACK;404` in the body, no `<h1>Page not found</h1>` in the server markup, "Loading…" present. Scratch spec (not committed) = the ST-006 body with Chromium CPU throttled 8x (`Emulation.setCPUThrottlingRate`), `--repeat-each=20 --retries=0`: as on main 17 failed / 3 passed (16 × Received "Loading…", 1 × `toEqual` with the second page still loading); with the TCR wait 20/20 passed | The artifact 11606501528 could not be downloaded here (egress proxy refuses `productionresultssa1.blob.core.windows.net`, 403), so the log and the local reproduction are the evidence. WebKit is not installed under `/opt/pw-browsers` (only chromium-1194; `playwright install` is not allowed), hence CPU throttling in Chromium to make the same race deterministic; WebKit evidence comes from the E2E repeat workflow on CI |
| 2026-10-09 | senior-frontend-engineer | **Fix in two parts, neither a retry, skip, timeout or browser exclusion.** (1) A guard, `web/e2e/helpers/settled-read.ts`, bound by `tests/features/e2e_settled_read.feature` (Vitest, runs in web-checks): after `goto`/`reload`/`goBack`/`goForward` in one function body, a `*.spec.ts` must wait (awaited `expect(...)` chain, or `waitFor`/`waitForURL`/`waitForResponse`/`waitForSelector`/`waitForFunction`) before it reads page text (`innerText`, `textContent`, `allInnerTexts`, `allTextContents`, `innerHTML`). A read on a locator that names its text (`getByText`, `getByLabel`, `{ name }`, `{ hasText }`) counts as a wait, because it resolves only once that text exists. `waitForLoadState` and `waitForTimeout` do not count. (2) The one spec change, as a TCR row (`test-change-requests.md` 2026-10-09), committed only after the senior-qa-engineer decides it | Red first: `d1c7948` stub → `pnpm exec vitest run tests/unit/e2e-settled-read.test.ts tests/unit/e2e-settled-read-scenarios.test.ts` → 8 failed / 6 passed. Green (`348c9da`): 14 passed / 1 failed, the failing one being the repository scenario naming `object-level-authorisation.spec.ts` lines 21 and 24, and nothing else (`sprint-01/resumable-upload.spec.ts:132` reads `getByText(/is NN% done/)`, which waits). With the TCR change applied in the working tree: 15/15, full web suite `pnpm exec vitest run` → 65 files, 517 passed; `pnpm lint` and `pnpm typecheck` clean | Alternatives rejected: (a) drop `/matches/loading.tsx` for the detail route (route group) so `notFound()` runs before the shell and returns a real 404: a product and design change to the C-30 loading state, needs the principal-designer, and is not what broke CI (judgment; offered as a follow-up below). (b) `waitForLoadState('networkidle')`: does not wait for React's render, and Playwright discourages it. (c) Retries, timeouts, WebKit exclusion: forbidden and hide the race. A static guard over every spec keeps the same mistake out of new specs, as the route-isolation guard did for CI-WEBKIT-PD-R3S2-02 |
| 2026-10-09 | senior-frontend-engineer | **Follow-up, not in this ticket:** a not-found under `/matches/*` answers HTTP 200 and needs JavaScript to show "Page not found" (without JS the page stays on "Loading…"). Raise with principal-designer and principal-engineer whether the detail route should resolve the match before the Suspense boundary | Local probe above (status 200, fallback-only markup) | Product behaviour, not the CI cause; recorded so it is not lost (judgment) |
| 2026-10-09 | engineering-manager | **Size waiver for PR #49 granted (`size-waiver`).** `check_pr_size.py` counted 411 changed lines on `b097522` (limit 400); with the accepted spec change and these decision rows it is about 420. Composition (`git diff --numstat origin/main...HEAD`): guard `settled-read.ts` 141, its unit and scenario tests 198 plus the feature 35, the ST-006 spec +5, decisions and TCR rows the rest. Splitting the guard from its tests or from the spec fix would leave one PR red or untested, so one PR is the smaller risk | CI job `PR policy (test immutability, size)` on `b097522`: `pr-size: 411 changed lines (target ~100, limit 400)` | Over the limit by ~5% and mostly tests; the production-free change stays one concern (the E2E settle fix and the guard that keeps it fixed) |

## Spec change (TCR 2026-10-09; accepted by the senior-qa-engineer and committed on PR #49)

```diff
diff --git a/web/e2e/object-level-authorisation.spec.ts b/web/e2e/object-level-authorisation.spec.ts
index 086d366..faf05be 100644
--- a/web/e2e/object-level-authorisation.spec.ts
+++ b/web/e2e/object-level-authorisation.spec.ts
@@ -17,10 +17,15 @@ test('@M0 @story-ST-006 Carlos cannot open Ivy\'s match', async ({ browser }, te
 
   const carlos = await (await browser.newContext()).newPage();
   await signInAs(carlos, 'Carlos');
+  // The match page streams (/matches/loading.tsx): "Page not found" replaces the Loading…
+  // fallback after page.goto resolves, so wait for it before reading (CI-E2E-MAIN-RED).
+  const heading = carlos.getByRole('heading', { level: 1 });
   await carlos.goto(ivysMatch);
+  await expect(heading).toHaveText('Page not found');
   const notYours = (await carlos.getByRole('main').innerText()).trim();
 
   await carlos.goto(ivysMatch.replace(/[0-9a-f-]{36}/i, '00000000-0000-4000-8000-000000000000'));
+  await expect(heading).toHaveText('Page not found');
   const missing = (await carlos.getByRole('main').innerText()).trim();
 
   expect(notYours).toMatch(/not found/i);
```
