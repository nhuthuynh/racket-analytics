# CI-NOTICE-CANCELLED decisions

Per-ticket decision file (working-agreement §3, "Daily sync"). Ticket: CI-NOTICE-CANCELLED, story PRC-05 "The process rules are enforced by checks", atomic items PRC-1.1, PRC-1.2, PRC-1.3. Owner: sre-devops-engineer. Review tier 1 (ADR 0056): principal-engineer plus the senior-qa-engineer test review plus green CI.

## Root cause: Flaky-test report hang (PRC-1.3)

Bisect by step timings, scheduled run 41622904539 (`888760df`, 2026-11-03, `cancelled`) against 41434196891 (`16a7e0b4`, 2026-11-02, `success`). Source: `gh api repos/nhuthuynh/racket-analytics/actions/runs/<id>/jobs`, `gh api .../actions/jobs/<job>/logs`, `gh api .../check-runs/125872862168/annotations`.

| Step of `flaky-report` | 41434196891 (good) | 41622904539 (bad) |
|---|---|---|
| Set up, checkout, setup-python, uv | 11:07:10 → 11:07:15 (5 s) | 10:52:48 → 10:52:53 (5 s) |
| Install ffprobe | 21 s | 16 s |
| Compose up + bucket init | 34 s | 32 s |
| Suites, pass 1 tests (to `[100%]`) | 11:08:10 → 11:15:04 (6 m 54 s) | 10:53:41 → 10:59:31 (5 m 50 s) |
| Pass 1 failure report printed | 11:15:04 → 11:15:11, ~45,700 lines | 10:59:31 → **10:59:33, log ends at line 38,441 mid-traceback** |
| Passes 2 and 3 | 11:15:11 → 11:28:46 | never started (no output for 48 min) |
| Job end | 11:28:51 `success` (21 m 41 s) | 11:47:48 `cancelled`, annotation "The job has exceeded the maximum execution time of 45m0s" (55 m 00 s) |

Findings:

1. **The tests did not hang.** Pass 1 ran as fast as on the good day; every step before the suites matches within seconds. The stall is in writing pass 1's failure report to the job log: the last line is 2 s into the report, in the middle of a traceback, and nothing follows for 48 min.
2. **The report is huge.** Every pass in both runs ends `396 failed, 3542 passed, 1 skipped, 22 deselected, 250 errors` (the same counts on all 3 passes of 41434196891, so these are broken tests in this job's setup, not flaky ones; the first error is `tus.py:74 HEAD failed: 404`). With the captured JSON logs of each failure that is ~7.7 MB per pass (good job log: 23.2 MB, 138,703 lines). The bad job log stops at 6.3 MB.
3. **Cause (judgment, from 1 and 2):** pytest blocked writing that burst to the step's stdout pipe once the runner stopped draining it, so the `for` loop never reached pass 2; with no step or pass limit the job sat until the 45 min job timeout, and the runner took another 10 min to stop (55 m 00 s). GitHub reports a job timeout as a `cancelled` run, which the notice treated as `none` (PRC-1.1), so nobody saw it.
4. The 396 + 250 broken tests in this job (the `integration` job passes the same selection) are a separate defect: they make the flaky report meaningless. Not fixed here (out of scope, ci.yml shared-file order); proposed as a follow-up ticket.

Fix and bound (`.github/workflows/ci.yml`, flaky-report job only): each pass writes to `reports/run-<i>.log` (only its last line goes to the job log), runs under `timeout --kill-after=30s "$PASS_TIMEOUT"` with `PASS_TIMEOUT: 12m` (a pass takes ~7 min), the step has `timeout-minutes: 40` (3 × 12 m 30 s = 37.5 min ≤ 40), and the logs are uploaded with `if: always()`. Setup takes ~1 min, so the job ends inside 45 min even if every pass hangs.

## Decisions

| Date | Who | Decision | Evidence | Why |
|---|---|---|---|---|
| 2026-11-03 | sre-devops-engineer | **`cancelled` is red** (`RED` adds `cancelled`); `success` closes; `skipped`, `neutral`, `action_required`, `stale` send nothing | `test_every_scheduled_conclusion_has_one_decided_action` (one row per conclusion); scenarios "a cancelled scheduled run is red", "a timed-out scheduled run is red", "a skipped scheduled run changes nothing" | Run 41622904539: a job timeout reports the run as `cancelled`. The ADR-0053-0049 reason for `none` ("superseded by a newer one (concurrency)") does not hold for scheduled runs: `ci.yml` cancels in progress only for `pull_request`. A cancel by a person is rare and still worth one comment |
| 2026-11-03 | sre-devops-engineer | **Same title for cancelled** (`[CI-RED] scheduled <workflow> run failed`); the body of a cancelled notice says a job timeout reports `cancelled` | `test_the_cancelled_body_says_a_job_timeout_reports_cancelled` | The title is the key the notice workflow uses to find the open issue (one per workflow); changing it would open a second issue |
| 2026-11-03 | sre-devops-engineer | **Bound per pass plus a step timeout, and stop streaming the suite output** (not only a step timeout) | scenario "a hanging pass of the suites is stopped and the job moves on" (real step, hanging `uv` stand-in, `PASS_TIMEOUT=2s`: 3 passes, `rc=124`, < 20 s); scenario "the suite step's limits add up to less than the job's" | A step timeout alone ends the job but loses passes 2 and 3; a per-pass limit keeps the report. Writing to a file removes the stalled-pipe path that hung run 41622904539 |

## Test change request (TCR), decided by the senior-qa-engineer

| Date | Test | Change | Why | Decision |
|---|---|---|---|---|
| 2026-11-03 | `infra/tests/test_scheduled_red_notice.py::test_a_scheduled_run_that_neither_failed_nor_passed_changes_nothing` | `cancelled` removed from the parameters (`stale` added) | The accepted rule "cancelled sends nothing" is reversed by PRC-1.1 (sprint 5 requirements breakdown); `cancelled` now runs in `test_a_red_scheduled_run_opens_a_notice` | **Open: senior-qa-engineer** |
| 2026-11-03 | `infra/tests/test_scheduled_red_notice.py::test_main_writes_the_action_and_only_the_files_it_needs` | row `("cancelled", "none", ...)` becomes `("cancelled", "open", ...)`; row `("skipped", "none", ...)` added so the `none` path keeps its case | Same | **Open: senior-qa-engineer** |

No test is deleted or skipped; `infra/tests/` is not a path `check_test_immutability.py` protects, so the TCR rows are the record.

## Evidence

- Red (commit `0d7702d7`): `cd infra && uv run --no-sync pytest -q --tb=line tests/test_scheduled_red_notice.py tests/test_scheduled_red_notice_scenarios.py` → `9 failed, 35 passed`: `cancelled` decided `none` (no issue created, `expected 1, got 0`), the hanging suite step ran past 120 s (`subprocess.TimeoutExpired`), the suite step had no `timeout-minutes` (`KeyError`).
- Green and refactor: see the PR description.
- QA dry run on the recorded payload of 41622904539 (`gh api .../actions/runs/41622904539 --jq '{name,event,conclusion,html_url,head_sha,run_started_at}'`): this branch `scheduled_red_notice: CI schedule cancelled -> open`, title `[CI-RED] scheduled CI run failed`; `origin/main` `-> none`.
- Still to confirm live (QA): the next scheduled CI run's `Flaky-test report (NFR-074)` duration (< 45 min) after merge.
