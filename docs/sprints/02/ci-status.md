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

## Next

The remaining reds are all owned outside the platform lane: SRE-S2-04, SRE-S2-05, SRE-S2-07, SRE-S2-08. The SRE re-dispatches CI after each of those lands and records the run here.
