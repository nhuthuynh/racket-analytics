# PLAN-05 decisions (engineering-manager, 2026-11-03)

Ticket: PLAN-05, branch `s05/plan` from `origin/main` `04c6a826`. Tier 0 (docs and process text).

## Why TDD does not apply

This PR adds planning text only (`docs/sprints/sprint-05.md`, `docs/sprints/05/*.md`). It has no executable behaviour, so there is no red test to write. The doc checks below stand in for it until CI-DOC-CHECK merges.

## Doc checks run

| Check | Command | Result |
|---|---|---|
| Referenced existing repo paths exist | a shell loop over every backticked path in the new files: `[ -e "$p" ]` | Every path that should already exist does. The misses were 1 wrong path (`.github/workflows/pr-policy.yml`: the `pr-policy` job is in `ci.yml`), corrected, plus `racket/demo`, `racket/eval` and `tests/unit/eval`, corrected to `scripts/demo/` and `racket/dataset/`. All other misses are files the named tickets create (planned outputs) |
| Citations resolve | `grep` of `[ASB/...]`, `[EP/...]` ids in the new files against `docs/research/agentic-sdlc-best-practices.md` | ASB/REQ-01, REQ-07, REQ-12, REQ-19 and AGL-02 are the ids the DoR and working-agreement §10 already cite. EP/ENG-18 is in working-agreement §2 |
| Front matter | no `.claude/agents` file changed | n/a |

## Planning-time evidence

| What | Command | Result |
|---|---|---|
| CI on `main` (push) | `gh api 'repos/nhuthuynh/racket-analytics/actions/runs?branch=main&event=push&per_page=3'` | 41643389454 `04c6a826` success; 41639406875 `785b4ab4` success |
| CI on `main` (schedule) | `gh api 'repos/nhuthuynh/racket-analytics/actions/runs?event=schedule&per_page=6'` | 41622904539 `888760df` **cancelled** (Flaky-test report over its 45 min limit), so CI-NOTICE-CANCELLED (`ci_fix`) is the first ticket |
| Open PRs | `gh api 'repos/nhuthuynh/racket-analytics/pulls?state=open' --jq length` | 0 |
| Sprint 4 ledger | `python3 scripts/measure/open_defects.py docs/sprints/04/review-rounds.md` | `open 0`, rc 0 |
| REST PR list (G05-11 dry-run of the data source) | `gh api 'repos/nhuthuynh/racket-analytics/pulls?state=closed&per_page=100' --jq length` | 100, rc 0 |
| Disk | `df -h /` | 30 GB free |

## Small decisions

| # | Decision | Reason |
|---|---|---|
| 1 | The in-progress WIP limit is 4 this sprint, not working-agreement §3's 5 | This sprint's brief asks for 4. It is stricter than §3, so it needs no change to the agreement (judgment) |
| 2 | New P-ids P17 (SLO and error-budget acceptance), P18 (RC sign-off), P19 (residual-risk ADR) and P20 (real devices, OQ-17) | Each human item gets one id, so EM-ESC-05 can ask for each one once |
| 3 | The perf, restore and android-chrome gates run nightly. Only promtool runs on every PR | Integration already uses 432.6 s of its 600 s budget. Adding variance-sensitive gates to PR checks could turn `main` red (PE and SRE risk) |
| 4 | QA owns QA-FLOW-METRICS (`scripts/measure`), not the SRE | The SRE lane is at its cap (10 of 9.6 units) |
| 5 | Process ids `PRC-<story>.<n>`, release ids `REL-1.<n>`, demo ids `DEMO-1.<n>` | Parseable by `measurelib._FINDING_ID` (retro 4 M15) |
| 6 | The working dates are re-baselined to the compressed session from 2026-11-03. The calendar review stays 2026-12-22 | EM kickoff risk "calendar drift" |

## Stage counts at planning

In progress 0 · in review 0 · awaiting QA 0 · awaiting merge 0. PLAN-05 itself goes into review once it is ready.

## Cost per PR (ADR 0056 decision 1)

| Round | Wall time (min) | total_cost_usd / tokens |
|---|---|---|
| Author build (planning) | about 45 | not measured (this invocation does not expose `total_cost_usd`) |

## Review round 1 (principal-engineer, PR #186)

| Finding | Severity | Fix |
|---|---|---|
| PE-PLAN05-01 | major | CI-TIERS-a no longer uses an ordered glob. A file gets the highest tier of every rule it matches, and the PR gets the highest tier over its files. An executable file (`*.py`, `*.sh`, `*.js`, `*.ts`, `.github/workflows/*`, `Makefile`, `Dockerfile*`, a shebang line or the executable bit) is at least tier 1 wherever it lives. So `docs/security/tools/*.py`, `docs/design/tools/*.py`, `docs/domain/tools/*.py` and `docs/sprints/*/close-checks/*` are tier 1, and `docs/architecture/api-*.md` stays tier 2. PRC-2.1 and PRC-2.2 now carry these negative cases, and the CI-TIERS-a test list names them |
| PE-PLAN05-02 | major | CI-TIERS-b and PRC-2.6 require the security-privacy-engineer APPROVE on every tier 2 PR, whatever made it tier 2 (kickoff SEC-1). This now also covers migration-only, API-contract-only and unmatched-path-only PRs, with one negative test each. PRC-2.7 computes the author role from the head branch's row in the §15 ticket map, cross-checked with `status.json` `ticket_prs`. The PR body, labels and author comments are never read for it. A head branch with no matching row fails closed |
| PE-PLAN05-03 | major | `RA_FAULT_INJECTION` is gone. The new ticket ST-075d (senior-backend-engineer, tier 2, security-privacy-engineer + principal-engineer, XS) adds one value, `api:5xx_on_header`, to the existing ADR 0012 seam `RACKET_FAULT_INJECTION`. That seam is kept only under `APP_ENV=test` (`settings.py` line 248, pinned by `test_settings.py::test_fault_injection_is_dropped_outside_test`). ST-075c is now tier 2 with no `backend/src` change. It gets `APP_ENV=test` from the shell for its own Compose project, plus a drill-only override `infra/compose.fault-drill.yaml`. A test pins `infra/env.example` at `APP_ENV=dev` and keeps the seam out of `infra/compose.yaml`. New items: NFR-041.6 and IT-05-12. BE lane 6 → 6.5 units, total 46 tickets / 26 units |

Why TDD does not apply: this round still changes planning text only, so the doc checks were re-run (below).
