# PLAN-06 decisions (engineering-manager, 2026-11-13)

Ticket: PLAN-06, branch `s06/plan` from `origin/main` `e7ed7d9d`. Docs and process text, plus `docs/sprints/06/ticket-owners.json` (the merge gate's author-role input, so this PR is **tier 2** by `review_tiers.py`, as PLAN-05 was).

## Why TDD does not apply

This PR adds planning text and one data file. It has no executable behaviour, so there is no red test to write. The doc checks below stand in for it, plus the existing drift test between `sprint-06.md` §15 and `ticket-owners.json` (`infra/tests/test_merge_ready_tiers.py::test_ticket_owner_map_matches_plan_section_15`).

## Doc checks run

Results are recorded in the PR body with the exact commands (`check_docs.py`, `check_atomic_breakdown.py`, the §15 drift test).

## Planning-time evidence

| What | Command | Result |
|---|---|---|
| CI on `main` (push) | `gh api 'repos/nhuthuynh/racket-analytics/actions/runs?branch=main&per_page=60'` | 43334586810 `e7ed7d9d` success; 43281846173 `1c3b648c` failure (2026-11-12 18:37Z), next push 43297649333 `b4161068` success |
| CI on `main` (schedule) | `gh api 'repos/nhuthuynh/racket-analytics/actions/runs?event=schedule&per_page=10'` | CI 43206773425 `2f947974` success (11-12); CI 43007950254 `b7bf0b7f` **failure** (11-11, perf); Nightly quality 43198871753 success; Dependency audit success daily |
| Open PRs | `gh api 'repos/nhuthuynh/racket-analytics/pulls?state=open'` | 13: #201, #218, #220, #224, #226, #230, #231, #232, #234 (draft), #235, #236, #238, #239 |
| Sprint 5 ledger | `python3 scripts/measure/open_defects.py docs/sprints/05/review-rounds.md` | rc 1, `"open": 5` (SEC-S5-TM-01 blocker first) |
| Flow and cost (G06-10 data source) | `SSL_CERT_FILE=/root/.ccr/ca-bundle.crt python3 scripts/measure/flow_metrics.py --repo nhuthuynh/racket-analytics --since 2026-11-03 --decisions docs/sprints/05/decisions --json <scratch>` | rc 1 "measured, incomplete": throughput 39; cycle time median 2.2 h, max 182.6 h; CI 1295.9 min; cost tables 9 of 39 (23 %); oldest open: #201 218.5 h |
| Atomic breakdown | `python3 scripts/ci/check_atomic_breakdown.py docs/sprints/06/requirements-breakdown.md` | rc 0, "0 problem(s)" (first run rc 1: the assumptions table used an `Id` header, renamed to `Ref`) |
| Sprint 5 report | `git show origin/main:docs/sprints/05/sprint-report.md` | "does not exist": Sprint 5 not closed |
| Disk | `df -h /` | 14 GB free (below the 16 GB build floor); 25 worktrees under `/home/user/wt` |

## Stage counts at planning (WIP)

In progress 1 (this PR) · in review 12 (limit 3, **breach**: the Sprint 5 PRs waiting on reviews and merges) · awaiting QA not computed · awaiting merge not computed. Breach reason: Sprint 5 PRs opened faster than the merge step ran between sessions (2026-11-05 to 2026-11-12 no merge). Action: the drain wave and QA-WIP-GATE.

## Small decisions

| # | Decision | Reason |
|---|---|---|
| 1 | No new `ci_fix` ticket pre-empts planning | push and the latest scheduled CI on `main` are green; the 2026-11-11 scheduled red is CI-NIGHTLY-PERF #232 (Sprint 5) |
| 2 | Required ADR 0056 tickets are **extensions** (CI-TIERS-06, CI-DOC-CHECK-06) | the base tickets (CI-TIERS-a/b, CI-DOC-CHECK) merged in Sprint 5 (#188, #193, #189); re-doing them would be churn |
| 3 | New P-ids P21 (S6/S7 order) and P22 (secondary statistics) | one id per human question |
| 4 | New FR group FR-170..FR-174; next free ADRs 0061, 0062 | FR-150..FR-162 is the highest range in use; ADR 0060 is the latest |
| 5 | Process ids continue at PRC-9 (Sprint 5 used PRC-1..8); demo ids `DEMO-6.<n>`; spike ids `SPK-<n>.<k>` | parseable by `measurelib._FINDING_ID` |
| 6 | 25 % of capacity reserved for the Sprint 5 drain | 13 open PRs plus VERIFY-05 and RETRO-05 |
| 7 | The roadmap §2 dates, §4 release map and §7 spike table are not renumbered in this PR | they change only if the PO confirms P21; renumbering now would write a PO decision the PO has not made (retro 3 M7) |

## Cost per PR (ADR 0056 decision 1)

| Round | wall_time_min | total_cost_usd | Note |
|---|---|---|---|
| Author build (planning) | not measured | not measured | the session does not expose per-ticket wall time or cost to the agent |

## Review round 1 (2026-11-13, head `94f46ff8`)

Reviews: principal-engineer 5884845775, senior-qa-engineer 5884863089.

| Finding | Severity | Fix |
|---|---|---|
| PE-PLAN06-01, QA06-PLAN-01 | blocker | The QA-DOR-CHECK scenarios pick their planted rows from the current breakdown (`first_nfr_row_with`, `first_fr_rule_with_negative`, `first_prc_id` in `infra/tests/atomic_breakdown_fixtures.py`); new `infra/tests/test_atomic_breakdown_pickers.py` runs them on every sprint's breakdown. TCR row 1 in `docs/sprints/06/test-change-requests.md` (QA decision pending) |
| PE-PLAN06-02 | major | `better_direction` (`higher` / `lower` / `inside_band`) in FR-170.R1, the COACH-6a catalogue fields and the ST-170a schema; FR-172.R1 defines the worse side from it, with Examples below band, above band, better side not ranked, and a `lower` pattern |
| PE-PLAN06-03 | major | FR-171.R4 states the AN-13 interval: distribution-free order-statistic CI for the median (`order_statistic_median`), none below n = 6; `interval_method` is a `PatternMeasure` field (FR-171.R1 `wilson`); won dink rallies counted as `n_censored`, and COACH-6a must justify the error-ended sample or switch to a censored estimate |
| PE-PLAN06-04 | minor | Measure snapshot key (subject, pattern id, match version, rules_version, definition version) split from the gap-result key (+ reference_version) in ST-171e and PE-6a |
| PE-PLAN06-05 | minor | PE-6a / ADR 0061 settles one owner: sport-plugin content read by Coaching through the ACL |
| PE-PLAN06-06 | minor | Roadmap §2 S7 row: "Go port or R2, pending P21" |
| PE-PLAN06-07 | nit | FR-172.R4 defines the gap and the width (interval width for a point reference) |

TDD for the test change: red first (the 6 scenario failures on `94f46ff8`, and the picker tests' `ImportError` before the pickers existed), then the pickers. The evidence commands and results are in the PR thread replies.

## PR policy decision (2026-11-13, head `9346a3d4`)

Decided by the PR-policy step: senior-qa-engineer for test immutability, engineering-manager for size (working-agreement §5).

Failing check: CI job 131632764796 "PR policy (test immutability, size)", step "Test and gold immutability": `check_test_immutability.py --base origin/main --head HEAD` → rc 1, `modified: tests/features/atomic_breakdown.feature`. The later steps were skipped, so they were run locally on the same head.

| Check | Command (worktree at `9346a3d4`) | Result | Decision |
|---|---|---|---|
| Test immutability | CI log of job 131632764796 | rc 1, one accepted test modified | **`qa-approved-test-change` granted** (TCR row 1, reasons below) |
| PR size | `python3 scripts/ci/check_pr_size.py --base origin/main --head HEAD` | rc 0, "0 changed lines of production code (target ~100, limit 400); 1691 excluded lines" | **No `size-waiver`**: the gate passes, nothing to waive |
| Red first | `python3 scripts/ci/check_red_first.py --base origin/main --head HEAD` | rc 0, "ok, 4 commit(s) checked" | none needed |
| Decisions joined to the ledger | `python3 scripts/measure/reconcile_due.py --pr --base origin/main --head HEAD` | rc 1, "3 problems": PE-PLAN06-01 (blocker), PE-PLAN06-02 (major), PE-PLAN06-03 (major) "has no ledger row" | **Not waivable** (no label waives it). Author action: add the review-round rows to the Sprint 6 ledger (`docs/sprints/06/review-rounds.md`), then CI re-runs |
| Scenario and picker tests | `cd infra && uv run pytest -q tests/test_atomic_breakdown_scenarios.py tests/test_atomic_breakdown_pickers.py` | 17 passed in 0.77s | — |

Why the test change is approved (it does not weaken the check):

1. It is required, not convenient: the Background step reads the *current* sprint's breakdown, and this PR makes that `06/requirements-breakdown.md`, which has none of the fixed Sprint 5 ids. Red recorded on `94f46ff8`: 6 failed, 1 passed (`row NFR-041.3 not found` ×4, `('PRC-7.1', 0)`, FR-124.R1 rc 0).
2. Same strength: 7 scenarios, the same Examples table, the same three break kinds, and every assertion unchanged (rc 1 and a `FAIL` line naming the planted item and the attribute word). Only the choice of the row moved from a literal to a picker.
3. No vacuous pass: each picker raises `AssertionError` when it finds nothing (`test_the_pickers_refuse_a_breakdown_without_a_matching_item`), the NFR picker only picks a row whose four cells are filled, and each picker's break is shown to change the text and turn the check red on every sprint's real breakdown (05 and 06).
4. It is the fix review 5884863089 (QA06-PLAN-01) named as the better option, and it stops the next plan PR stranding the scenarios again.

Residual note (not a blocker): the pickers take the *first* matching row, so the scenarios always exercise one row per sprint; the per-sprint unit tests cover the other breakdowns. Acceptable for a doc-check guard.
