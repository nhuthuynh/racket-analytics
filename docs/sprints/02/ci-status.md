# Sprint 2 CI status (W-01)

Owner: sre-devops-engineer (sprint-02 §3 row W-01; retro 1 A1). Every CI failure goes to its owner as a row in `review-rounds.md`; this file keeps the per-run, per-job record. Read with `mcp__github__actions_list list_workflow_jobs <run>` and `mcp__github__get_job_logs` (the blob log and artifact URLs are refused by the sandbox proxy, 403, so logs are read through the MCP tool).

Branch rule (PO addendum 2026-10-06, `po-input-2026-10-05.md` P1): agents may push `sprint-*` branches without force and dispatch CI. `nightly-quality.yml` can be dispatched only once it is on `main` (still not: `main` = `2b9c6ca`).

## Runs on the Sprint 1 PR before Sprint 2 code (context)

| Run | Head | Result | Triage |
|---|---|---|---|
| 37377206126 | `sprint-01` `9808296` | failure: E2E 8 `[webkit]` failures, integration 3 red, PR policy labels | `docs/sprints/01/ci-status.md` (release section) |
| 37426849974 | `sprint-01` `2b97fa0` | failure: E2E `6 failed, 12 skipped, 98 passed`, all `[webkit]`; integration S-08 + ST-025 | `docs/sprints/01/ci-status.md` (re-check) |
| 37429011095 | `sprint-01` `d1ce633` (docs only after `2b97fa0`) | failure: same jobs as 37426849974 (integration, E2E) | Same causes; no new triage |

## Run 37434214390: first CI run of the Sprint 2 code (2026-10-06)

`git push origin sprint-02` (`37848f6..7470a7b`, fast-forward), then `workflow_dispatch` of `ci.yml` on `sprint-02`. Head `7470a7b` (C-15). Conclusion **failure**. <https://github.com/nhuthuynh/racket-analytics/actions/runs/37434214390>

| Job | Result | Cause | Owner | Action |
|---|---|---|---|---|
| Workflow lint, Ruff, mypy, fixtures, infra tests, web checks, secrets/audit, SBOM | success | — | — | — |
| Flaky-test report | success | dispatch runs it (3 repeats of the backend suites) | — | — |
| PR policy | skipped | not a PR event (allowed by ci-gate) | — | — |
| Python unit suites | **failure** | `budget: 'uv run --no-sync pytest -q -m unit tests/unit' exceeded its time budget of 10s` (rc 124) at 91%. `DOMAIN_TEST_PATHS=tests/unit` measured the whole backend unit suite (1,262 tests; 8.2 s locally) against the 10 s domain budget, not NFR-073's "rules + domain unit suite" | sre-devops-engineer | **Fixed (W-01 commit):** `DOMAIN_TEST_PATHS` = `tests/unit/{sports,matches,players,video_ingest}` (1,002 tests, 5.98 s locally); the whole suite keeps its 60 s budget |
| Integration on Compose | **failure** | `21 failed, 1869 passed, 1 skipped, 1 deselected in 383.13s`. All 21 carry `red_until`: `test_nightly_quality::test_nightly_run_completes` (ST-024, S-08: no nightly on `main`), `test_phone_fixtures::test_coverage_of_the_set`, `::test_probe_every_fixture` (ST-025, PO item P3), 18 × `test_side_out_singles_provisional` SOS-01..SOS-18 (ST-035, stretch) | sre-devops-engineer (selection); senior-qa-engineer (markers) | **Fixed (W-01 commit):** the gate selects `… and not nightly and not red_until` (sprint-02 §8 "listed separately", as G02-07 already does); a new step lists the red-until rows per story with `scripts/ci/red_until_report.py` and **fails on a stale marker**. Local run of that step: 5 passing tests carry a module-level marker (SRE-S2-04 to QA, TCR), so the job stays red until QA moves those markers |
| E2E (Chromium + WebKit) | **failure** | `6 failed, 12 skipped, 142 passed (10.7m)`. **The 8 Sprint 1 `[webkit]` failures are gone** (QA's TCR: service workers blocked in routing specs; A-03 waits for `load`). All 6 failures are `sprint-02/rally-video.spec.ts`, both browsers: (a) 4 × `spawnSync ffmpeg ENOENT` (the VP9 stand-in needs `ffmpeg`, the E2E runner has none); (b) `[chromium]` E2E-02-04 `this browser cannot decode the H.264 original` (Playwright Chromium has no H.264; QA blocker 2026-10-06); (c) `[webkit]` E2E-02-04 `page.waitForResponse` timeout: at `7470a7b` the presigned link pointed at `http://localhost:8333` from an https page | (a) sre-devops-engineer; (b) senior-qa-engineer (`playwright.config.ts`: Chrome channel on CI, the runner image ships Google Chrome); (c) sre-devops-engineer | (a) **Fixed (W-01 commit):** E2E job installs `ffmpeg`. (b) Routed: SRE-S2-05. (c) **Fixed by SRE-MEDIA `03ab524`** (links on the web origin); to confirm on the next run |
| Locust baseline | n/a | job added after this run (ST-039, `1ef2dd7`) | — | First result on the next run |
| ci-gate | **failure** | aggregates unit, integration, E2E | — | — |

Evidence: `mcp__github__actions_list list_workflow_jobs 37434214390`; `mcp__github__get_job_logs` for jobs 112171939162 (unit, tail 75), 112171939109 (integration pytest summary) and 112171939346 (Playwright summary and the six error blocks).

## Run 37438997898: head `ffce41d` (all SRE stories through W-01), 2026-10-06

`git push origin sprint-02` (`7470a7b..ffce41d`), dispatch `ci.yml`. Conclusion **failure**; the gates that were red for platform reasons are green. <https://github.com/nhuthuynh/racket-analytics/actions/runs/37438997898>

| Job | Result | Detail | Owner |
|---|---|---|---|
| actionlint, Ruff, mypy, fixtures, infra, web checks, secrets/audit, SBOM, flaky report | success | — | — |
| Python unit suites | **success** (was failure) | domain step 4 s (08:52:19 → 08:52:23) on the NFR-073 paths; property 22 s; whole unit 6 s | — |
| Locust baseline (new) | **success** | 2,964 requests, 0 failures, availability 1.0, 51.18 RPS, correction p95 410 ms (gate ≤ 1,500), restored byte-identical. **Baseline (not gated):** score sheet p50/p95/p99 290/460/510 ms, history 310/490/580, match 260/390/420, correct 210/410/450, undo 140/330/360. The reads run beside one correction user writing the same match; the read-only open loop (`tag_latency.py` through the origin, sandbox) gave p50 17 ms, so writes on the same match may slow the reads: observation SRE-S2-06 | sre-devops-engineer (baseline); principal-engineer / senior-backend-engineer (SRE-S2-06) |
| Integration | failure, **gate step green** | `Backend suites with coverage` success (selection `not red_until`); the new red-until step fails as designed on the 5 stale markers (SRE-S2-04) | senior-qa-engineer |
| E2E | failure | `9 failed, 12 skipped, 161 passed (14.0m)`. Fixed since the last run: the 4 `ffmpeg ENOENT` (stand-in specs pass in both browsers) and **`[webkit]` E2E-02-04 passes: the real H.264 video plays through the web origin (SRE-MEDIA)**. Left: (1) `[chromium]` E2E-02-04 and `timing.spec.ts:210` seek-first-frame, no H.264 in Playwright Chromium (SRE-S2-05); (2) `[webkit]` new Sprint 2 specs: `announcements.spec.ts:8` E2E-02-03 (`Expected: "Rally 1: us. Score 1-0-2."`), `quick-tag.spec.ts:15` (`toBeVisible` failed), `:42` (`toContainText "The player who made the error must be on the side"` failed), `:66` (two devices, `toBeVisible` failed), `timing.spec.ts:97` (`no change seen for end-1 in 10 s`): SRE-S2-07, WebKit first to the FE for product-or-test analysis, as in Sprint 1; (3) `[webkit]` `timing.spec.ts:210` and `:219`: `browserContext.newCDPSession: CDP session is only available in Chromium` (test defect; ST-039 card: WebKit timings out of scope): SRE-S2-08 | (1) senior-qa-engineer; (2) senior-frontend-engineer then senior-qa-engineer; (3) senior-qa-engineer |
| ci-gate | failure | integration (stale markers), E2E | — |

Evidence: `mcp__github__actions_list list_workflow_jobs 37438997898`; `mcp__github__get_job_logs` for jobs 112187797489 (Locust, verdict JSON) and 112187797479 (Playwright summary and the nine error lines).

## Run 37452407537: head `78c52ef` (review round 1, QA-RV1-01), 2026-10-06

`git push origin sprint-02` (`0ab3b93..78c52ef`, fast-forward), then `workflow_dispatch` of `ci.yml` on `sprint-02`. This is the first run after `ffce41d`: 20 commits (`git log --format=%h ffce41d..78c52ef | wc -l` → 20), among them `77a7201`, `442f7b3` and the review-round-1 fixes `8af0f77`, `b5ee957`, `d9fba85`, `7bdfd21` (QA-RV1-05). Conclusion **failure**. <https://github.com/nhuthuynh/racket-analytics/actions/runs/37452407537>

| Job | Result | Detail | Owner |
|---|---|---|---|
| actionlint, mypy, fixtures, infra, web checks, secrets/audit, SBOM, flaky report, Locust baseline | success | flaky report: 3 repeats of the backend suites green | — |
| Python unit suites | success | domain step 9 s (10:50:43 → 10:50:52, budget 10 s; was 4 s at `ffce41d`, watch); property 41 s; whole unit 12 s | — |
| **Python lint (Ruff)** | **failure (new regression)** | `backend/tests/tools/test_live_tagging_error_code.py:18:5: PT018 Assertion should be broken down into multiple parts` and `:53:9: UP031 Use format specifiers instead of percent format`. File added in `8af0f77` (review round 1, QA-RV1-02). Reproduced locally: `cd backend && uv run ruff check .` → `Found 2 errors.` Routed as SRE-S2-10 | principal-engineer |
| Integration | failure, **gate step green** | `Backend suites with coverage`: `2046 passed, 1 skipped, 27 deselected in 393.62s` (selection `not nightly and not red_until`). Red-until step: `21 failed, 5 passed`; `red_until_report.py` rc 1 on the same 5 stale markers (SRE-S2-04, unchanged since `ffce41d`: no commit touched `backend/tests/features/`) | senior-qa-engineer |
| E2E | failure | `10 failed, 12 skipped, 160 passed (11.9m)`. Same 9 as run 37438997898 (SRE-S2-05 `[chromium]` `rally-video.spec.ts:34` E2E-02-04 and `timing.spec.ts:210`; SRE-S2-07 `[webkit]` `announcements.spec.ts:8`, `quick-tag.spec.ts:15`, `:42`, `:66`, `timing.spec.ts:97`; SRE-S2-08 `[webkit]` `timing.spec.ts:210`, `:219`), plus **`[chromium]` `timing.spec.ts:219` stand-in seek: `page.evaluate: Error: no change seen for seek in 10 s`**: the smoke-2 flake SRE-S2-09 now also seen on CI (passed on run 37438997898) | senior-qa-engineer (SRE-S2-05, -08, -09); senior-frontend-engineer then senior-qa-engineer (SRE-S2-07) |
| ci-gate | failure | Ruff, integration (stale markers), E2E | — |

Evidence: `mcp__github__actions_list list_workflow_runs ci.yml branch=sprint-02` (run 37452407537, `head_sha` `78c52efe9f10…`); `list_workflow_jobs 37452407537`; `mcp__github__get_job_logs` for jobs 112231850146 (Ruff annotations), 112231850190 (pytest summaries and the red-until report) and 112231850486 (Playwright summary and the ten error blocks). The artifact download URL is refused by the sandbox proxy (`CONNECT tunnel failed, response 403`), as before.

## Run 37461758337: head `fe156e7` (review round 2: SRE-S2-10 Ruff, SEC-S2-TM-03 edge headers), 2026-10-06

`git push origin sprint-02` (`c62c1b0..fe156e7`), then `workflow_dispatch` of `ci.yml` on `sprint-02`. First run after the round-1 fixes `c3b042a` (QA-RV1-06), `a3ec48b` (QA-RV1-08), `f737e00` (Chrome channel on CI, QA-RV1-07), `29c1e68` (V-01) and the round-2 fixes up to `063c2f4` (Ruff) and `fe156e7` (edge headers). Conclusion **failure, E2E only**. <https://github.com/nhuthuynh/racket-analytics/actions/runs/37461758337>

| Job | Result | Detail | Owner |
|---|---|---|---|
| actionlint, **Ruff** (was red), mypy, fixtures, infra (incl. the new live Caddy header test), web checks, secrets/audit, SBOM, unit, Locust baseline, flaky report | success | Ruff: SRE-S2-10 closed on CI | — |
| **Integration** | **success** (was failure) | gate step and the red-until step both green: the stale markers are gone (QA-RV1-06 / SRE-S2-04 closed on CI) | — |
| E2E | failure | `10 failed, 14 skipped, 174 passed (15.6m)`. **No longer failing since run 37452407537** (the `github` reporter lists failures only; skipped went 12 → 14, exactly the two named WebKit CDP skips, so the others below passed): `[chromium]` E2E-02-04 and `seek-first-frame (real video link)` (Chrome channel plays the H.264 original: QA-RV1-07 / SRE-S2-05 CI part), `[webkit]` CDP seek tests now skipped (+2 skipped: QA-RV1-08 / SRE-S2-08), `[chromium]` stand-in seek flake did not recur (SRE-S2-09, 1 run). **Left:** the SRE-S2-07 family, now in **both** browsers: `announcements.spec.ts:8` (`Expected: "Rally 1: us. Score 1-0-2." Received: ""`), `quick-tag.spec.ts:15`, `:66` (`toBeVisible` failed), `:42` (`Received string: "Mark the rally end first."`), `timing.spec.ts:97` (`no change seen for end-1 in 10 s`). With real Chrome the video is playable, so the 5 ms rally (`waitForTimeout(5)`) fails in Chromium as it did in WebKit. These specs are at `fd363fa` (QA's fix for SRE-S2-07, QA-RV2-03), which landed after this head | senior-qa-engineer (SRE-S2-07, closed by `fd363fa` if the next run is green) |
| ci-gate | failure | `e2e: failure`; every other need `success` | — |

Evidence: `mcp__github__actions_list list_workflow_jobs 37461758337` (all jobs but E2E `success`); `mcp__github__get_job_logs` job 112270228204 (ci-gate: `e2e: failure`) and job 112262804591 (Playwright summary and the ten error blocks, log lines 2840-3232). The log blob URL is refused by the sandbox proxy (`CONNECT tunnel failed, response 403`); the content came through the MCP tool.

## Run 37464553177: head `fd363fa` (review round 2, QA's SRE-S2-07 fix), 2026-10-06: **ci-gate green**

`git push origin sprint-02` (`fe156e7..fd363fa`: `aa763ed`, `48bb9de`, `456f1de`, `26c7be4` FE round 2; `d4f2a6b` PO; `6c59633`, `fd363fa` QA round 2), then `workflow_dispatch` of `ci.yml` on `sprint-02`. Conclusion **success**: the first fully green Sprint 2 run. <https://github.com/nhuthuynh/racket-analytics/actions/runs/37464553177>

| Job | Result | Detail |
|---|---|---|
| actionlint, Ruff, mypy, fixtures, infra (incl. live Caddy header test), web checks, secrets/audit, SBOM, unit (domain step 8 s, budget 10 s), Locust baseline, flaky report (3 repeats) | success | — |
| Integration | success | gate step and the red-until step (no stale marker) |
| E2E, Chromium (Google Chrome channel) + WebKit, https, fresh Compose stack | **success** | `Running 198 tests using 1 worker` → **`184 passed, 14 skipped` (12.7m), 0 failed, 0 flaky**. The SRE-S2-07 family passes in both browsers. Skips: the 12 Sprint 1 API-bound skips and the 2 named WebKit CDP skips (QA-RV1-08) |
| ci-gate | **success** | "All gates green" |

Evidence: `mcp__github__actions_get get_workflow_run 37464553177` → `conclusion: success`, `head_sha fd363fae0aa1…`; `list_workflow_jobs 37464553177` → every job `success` (PR policy `skipped`, allowed outside PRs), ci-gate job 112278570278 `success`; `mcp__github__get_job_logs` job 112272206181 (Playwright summary lines above).

## Next

`ci-gate` is green at `fd363fa` (run 37464553177), so the W-01 / QA-R1-06 family closes on CI. Still open outside CI: the local-evidence part of SRE-S2-05 (no H.264 in local Playwright Chromium; PO/EM decision whether the CI Chrome run is the G02-05/G02-06 (c) evidence, blockers.md). SRE-S2-09 (stand-in seek flake) did not recur in two runs; it stays watched by the flaky report. The SRE re-dispatches CI at each later head that changes code and records it here.

## Release: PR #2 (`sprint-02` → `main`), 2026-10-06

`git push -u origin sprint-02` (`3461f77..c01d0dd`), then PR #2 opened (<https://github.com/nhuthuynh/racket-analytics/pull/2>, base `main`; stacks on PR #1, fork point `2b97fa0`). Labels: **none**. `qa-approved-test-change` needs 0 pending rows in `test-change-requests.md`; 5 rows (lines 24-28) have an empty QA decision. `size-waiver`: the EM recorded only commit-level waivers, none for this PR (po-input 2026-10-06 addendum).

### Run 37505286086: head `c01d0dd` (pull_request), conclusion failure

| Job | Result | Detail | Owner |
|---|---|---|---|
| actionlint, Ruff, mypy, fixtures, infra, web checks, secrets/audit, SBOM, unit, integration, E2E | success | — | — |
| Flaky-test report | skipped | runs on schedule/dispatch only | — |
| **PR policy** | **failure** | `check_test_immutability.py`: modified accepted tests (e.g. `backend/tests/support/*.py`, `web/e2e/walking-skeleton.spec.ts`) without the `qa-approved-test-change` label; size step skipped after it (would fail too: `check_pr_size.py` locally → `52633 changed lines`, no `size-waiver`) | senior-qa-engineer (decide TCR rows 24-28, then label); engineering-manager (PR size waiver) |
| **Locust baseline** | **failure (new)** | `perf_verdict.py`: `restored_byte_identical: false`, all other gates true (availability 1.0, correction p95 500 ms, 50.5 RPS). Cause: the `-t 60s` limit killed the correction user with a PATCH in flight; the API committed it (`match.rally_corrected` version 122 at 17:42:52.414, shutdown at 17:42:52.230) and no undo followed. Harness defect, not a product defect | sre-devops-engineer: **fixed `3ee3af1`** (test-first: `infra/tests/test_perf_restore.py` red on collection, then 5 passed; infra suite `477 passed`) |
| ci-gate | failure | pr-policy, perf-baseline | — |

Evidence: `mcp__github__pull_request_read get_check_runs 2`; `mcp__github__get_job_logs` jobs 112412274591 (PR policy list of modified accepted tests) and 112412274471 (Locust summary and the verdict JSON).

### Run 37507959925: head `3ee3af1` (pull_request), conclusion failure: PR policy only

| Job | Result |
|---|---|
| actionlint, Ruff, mypy, fixtures, infra, web checks, secrets/audit, SBOM, unit, integration, E2E (Chromium + WebKit), **Locust baseline (fixed)** | success |
| Flaky-test report | skipped (by design outside schedule/dispatch) |
| **PR policy** | **failure**: same as run 37505286086 (no `qa-approved-test-change` label) |
| ci-gate | **failure** (`pr-policy: failure`) |

Evidence: `mcp__github__pull_request_read get_check_runs 2` (head `3ee3af1`).

**Merge decision:** not merged. `ci-gate` is red on the PR head because of the PR-policy label gate, which only QA (test-change decisions) and the EM (size waiver) can clear; the SRE does not apply labels without that evidence and does not bypass the gate. Blocker row 2026-10-06 (sre-devops-engineer, release) in `blockers.md`.
