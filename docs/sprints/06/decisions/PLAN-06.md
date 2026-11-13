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
