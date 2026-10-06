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

## Next

Push the branch head with C-11, C-18, C-29, SRE-MEDIA, C-13, ST-039 and W-01, dispatch `ci.yml`, and record the run here: expected remaining reds are SRE-S2-04 (stale markers, QA), SRE-S2-05 (H.264 in CI Chromium, QA) and anything the Locust job shows on a clean runner.
