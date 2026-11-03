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

## Review round 2 (principal-engineer and senior-qa-engineer, PR #186)

| Finding | Severity | Fix |
|---|---|---|
| PE-PLAN05-R2-01 | major | Accepted. G05-02 now does `export COMPOSE_PROJECT_NAME=racket-obs05` for the whole block, so `make demo` copies `web-tls` from the drill project. G05-01 had the same defect (`make up FLAGS=on COMPOSE_PROJECT_NAME=... && make demo`: `make demo` ran without the project name, and make has no `FLAGS` variable). It now exports the project name and the four `FEATURE_*=true` values from the shell, which override `infra/.env`. Sprint plan §12 step 1 had the same defect (`FLAGS=on PROFILES=obs`) and now uses `COMPOSE_PROJECT_NAME`/`COMPOSE_PROFILES` and `FEATURE_*` exports. The dry-run is below and is in the scorecard §6 |
| PE-PLAN05-R2-02 | major | Accepted. The branch-to-owner map moves to `docs/sprints/05/ticket-owners.json` (this PR creates it from §15: 46 rows, each `{id, branch, owner}`, `owner` a role file name). CI-TIERS-a classifies `docs/sprints/*/ticket-owners.json` and `docs/sprints/*/status.json` as tier 2. CI-TIERS-b reads only the JSON and fails closed when a row is missing, duplicated or names a bad role. The `status.json` cross-check is dropped because `ticket_prs` holds no owner or branch. A drift test keeps the §15 table equal to the JSON. New fixtures: owner-file-only PR → tier 2; §15-only PR → tier 0, author role unchanged, drift test fails. PRC-2.3 and PRC-2.7 are updated |
| PLAN05-QA-04 | major | Accepted. The tier 2 migration glob is now `backend/src/racket/migrations/**` (`git ls-files` → 24 paths; `backend/migrations/**` → 0). The CI-TIERS-b negative fixture uses `versions/`. A glob liveness test (`test_every_tier2_glob_matches_a_tracked_path`) fails on any tier 2 glob that matches no tracked path, except `PENDING_GLOBS` entries that name the ticket that creates the path. It is red first against the old glob |

Note: by the CI-TIERS-a rules this PR would be tier 2, because it adds `ticket-owners.json`. It merges under the interim rule (sprint-05 §11 rule 1). The engineering-manager asks the security-privacy-engineer to read the owner file. That read is not a merge gate.

### Round 2 evidence

| Check | Command | Result |
|---|---|---|
| Wrong project, round 2 form (red) | `docker compose -f infra/compose.yaml -p racket-obs05 up -d --no-deps web-tls` (rc 0), then `env -u COMPOSE_PROJECT_NAME make demo` | rc 2: "make demo: the stack's web-tls service is not reachable; run 'make up' first" |
| Project name exported (green on the `cp` step) | `COMPOSE_PROJECT_NAME=racket-obs05 make demo` | `root.crt` was copied from `racket-obs05-web-tls-1`. make rc 2 only at `seed_demo.py` (`GET /dev/users: HTTP 502`), because only `web-tls` was started. The obs profile and `compose.fault-drill.yaml` do not exist until ST-075b/c |
| Project-name resolution | `docker compose -f infra/compose.yaml config --format json \| jq -r .name` with and without `COMPOSE_PROJECT_NAME=racket-obs05` | `racket-analytics` / `racket-obs05` |
| Teardown | `docker compose -f infra/compose.yaml -p racket-obs05 down -v --rmi local` | rc 0 |
| Migration glob | `git ls-files 'backend/src/racket/migrations/**' \| wc -l`; `git ls-files 'backend/migrations/**' \| wc -l` | 24; 0 |
| Owner file parses, roles valid, no drift | `python3 -c 'json.load(...)'`; each `owner` ∈ `.claude/agents/*.md` stems; §15 `(id, branch, owner)` set == JSON set | 46 rows; all owners valid; drift none |
| Paths exist | `[ -e "$p" ]` over the newly referenced paths | all exist (`backend/migrations` absent, as the finding says) |
