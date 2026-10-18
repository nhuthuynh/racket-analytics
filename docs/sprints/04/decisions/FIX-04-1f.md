# FIX-04-1f decisions

This is the decision file for this ticket (PO rule 2026-10-07). Ticket: meet goal metric G04-07, the E2E pass rate (goal-scorecard row G04-07; api-sprint-04 §1 "Flag-on E2E"; PE-4 decisions row 18). Context: the web test harness (`web/playwright.config.ts`, `web/e2e/helpers/`). No domain bounded context is touched. Owner: senior-qa-engineer.

## Root cause (VERIFY-04-r1 reported G04-07 as "Not run: no stack")

G04-07 cannot pass on `main` at `3c4be05`. There are two causes.

1. **The E2E-04-01..05 specs do not exist.** `git grep -l 'E2E-04-0' origin/main -- web` finds nothing. These specs belong to ST-065, and ST-065 depends on ST-063b and ST-063c. Those depend on ST-062 and ST-063a, which depend on ST-061b (PR #111, open). None of the plan UI routes (P-01..P-03) is on `main`: `ls web/src/app` shows `auth error.tsx … matches … settings signed-out welcome`, with no `plan`. Writing the journey specs now would mean guessing at screens that are not built. That is ST-065's scope, after its dependencies merge. This ticket does not write them.
2. **The flag-on command measured nothing, and nothing kept flag-on specs out of the per-PR legs.** `web/playwright.config.ts` had no `flags-on` project. The G04-07 flag-on step (`PW_PROJECTS=flags-on playwright test`, goal-scorecard §4) therefore selected zero projects. Before this ticket, `PW_PROJECTS=flags-on pnpm exec playwright test --list` printed `Total: 0 tests in 0 files` / `Error: No tests found`. A typo such as `chromuim` gave the same output. Also, a spec placed in `web/e2e/sprint-04/flags-on/` (the path in api-sprint-04 §1) would have run in the per-PR `chromium` and `webkit` CI legs, against a stack with every `FEATURE_*` off. The red listing showed `[chromium] › sprint-04/flags-on/age.spec.ts … E2E-04-06 age question` and the same line for `[webkit]`. ST-068b, ST-071 and ST-072b each add one of these specs (E2E-04-06..08). Each would have turned CI red, or been skipped to keep it green.

This ticket fixes cause 2. Cause 1 stays a dependency, so G04-07 stays **not met**. It can be met only after ST-061b → ST-062/ST-063a → ST-063b/ST-063c → ST-065 merge (and ST-068b/ST-071/ST-072b for the flag-on 3 of 3).

## Decisions

| Date | Who | Decision | Evidence | Why |
|---|---|---|---|---|
| 2026-10-18 | senior-qa-engineer | **Add a `flags-on` project** that runs only `**/flags-on/*.spec.ts`, in the same desktop Chrome `use` as `chromium` (channel and dev-certificate args included). `chromium` and `webkit` get `testIgnore` on the same pattern | `infra/tests/test_e2e_projects_scenarios.py` 3 passed; `web/tests/unit/e2e-projects.test.ts` 10 passed | api-sprint-04 §1 names the project and the directory. The G04-07 row says "Chrome for Testing", which is the chromium project's browser |
| 2026-10-18 | senior-qa-engineer | **Leave `flags-on` out of the default `PW_PROJECTS`** (still `chromium,webkit`) | Unit test "runs the per-PR browsers by default, never the flag-on project" | PE-4 row 18: flag-on E2E runs nightly and by the verifier, not per PR. CI passes `--project=<matrix>`, which is unchanged |
| 2026-10-18 | senior-qa-engineer | **Refuse an unknown or empty `PW_PROJECTS`** with `PW_PROJECTS=<value> must name Playwright projects from: chromium, webkit, flags-on`, instead of selecting no project | Scenario "An unknown project name is refused" | Fail closed (ADR 0014, no vacuous pass). "No tests found" reads like a missing spec, not a misspelt project |
| 2026-10-18 | senior-qa-engineer | **Match on the path segment `flags-on/` with either separator**, not on a filename suffix | Unit tests for `isFlagOnSpec`, with `sprint-04/flags-on-notes.spec.ts` and `flags-on/helpers.ts` as negatives | The directory is the published contract (api-sprint-04 §1). Helpers in that directory are not specs |
| 2026-10-18 | senior-qa-engineer | **Bind the scenarios with the real Playwright `--list`** through the real `web/playwright.config.ts`. A stand-in config imports it and only changes `testDir`, so the test needs no browser and no stack | Same harness approach as `ci_e2e_stall_report.feature` (infra-tests job has `web/node_modules`) | The integration level here is "config ↔ Playwright's project resolution". A unit test of the helper alone would not catch a config that ignores it |
| 2026-10-18 | senior-qa-engineer | **No live G04-07 run on the Compose stack in this ticket** | `git grep -l 'E2E-04-0' origin/main -- web` gives nothing; `df -h /` gives 12G free, and the Compose image build plus the 278-test run would take the disk under the 10 GB floor | Without the E2E-04 ids, the `--require E2E-04-0[1-5]` step fails whatever the stack does, so a live run could not change the verdict. The verifier (VERIFY-04) measures live once ST-065 has merged |
| 2026-10-18 | senior-qa-engineer | **No test change needs a TCR.** Only new test files are added. No accepted test is edited | `git diff --stat origin/main` | Test immutability rule |

## Evidence

- Red (commit `5daf743`), run from `infra/`: `uv run pytest -q tests/test_e2e_projects_scenarios.py` gave `3 failed`. The failures were: `assert 'PW_PROJECTS' in '…Error: No tests found'`; `assert {'chromium', 'webkit'} == set()` (the flag-on spec was listed in both per-PR browsers); and `assert 1 == 0` with `No tests found` for `PW_PROJECTS=flags-on`. Run from `web/`: `pnpm exec vitest run tests/unit/e2e-projects.test.ts` gave `Failed to resolve import "../../e2e/helpers/projects"`.
- Green (commit `c449796`, refactor `656c156`): the same two commands gave `3 passed` and `Tests 10 passed (10)`.
- No regression in the real tree: `pnpm exec playwright test --list` gives `Total: 278 tests in 42 files`, both before and after the change. `PW_PROJECTS=flags-on … --list` gives `Total: 0 tests in 0 files`, which is correct because no flag-on spec exists yet.
