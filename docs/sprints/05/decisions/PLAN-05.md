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

## Review round 3: one disposition per finding, all rounds (working-agreement §7.3b; fix iteration 3)

Author: engineering-manager, with principal-engineer and senior-qa-engineer as co-authors. Fresh context, fix iteration 3 (working-agreement §7 step 5: the last iteration before escalation to the PO).

Why TDD does not apply: this round still changes planning text only (`sprint-05.md`, `05/*.md`, this file). The doc checks and the G05-06 dry-run below stand in for a red test.

**Finding ids (source: every review on PR #186).** The reviewers gave ids to every finding except the three principal-engineer nits of round 1, which get `PE-PLAN05-NIT-1..3` here. Repeated nits in later rounds re-check those ids or PLAN05-QA-01/02 and add no new id. The senior-qa-engineer's F-labels are aliases: round 2 F1 = PLAN05-QA-04, F2 = PLAN05-QA-05, F3 = PLAN05-QA-06; round 3 F1 = PLAN05-QA-07, F2 = PLAN05-QA-08.

| Round, review | Ids |
|---|---|
| 1, principal-engineer 5753329182 | PE-PLAN05-01, -02, -03, -04, -05, -06, -07, PE-PLAN05-NIT-1, -NIT-2, -NIT-3 (10) |
| 1, senior-qa-engineer 5753350564 | PLAN05-QA-01, -02, -03 (3) |
| 2, principal-engineer 5753520871 | PE-PLAN05-R2-01, -R2-02, -R2-03, -R2-04 (4) |
| 2, senior-qa-engineer 5753529573 | PLAN05-QA-04, -05, -06 (3) |
| 3, senior-qa-engineer 5753632703 | PLAN05-QA-07, -08 (2) |
| 3, principal-engineer 5753648007 | PE-PLAN05-R3-01, -R3-02, -R3-03 (3) |
| **Total** | **25 ids** |

| # | Finding | Severity | Disposition | Evidence (this head unless a commit is named) |
|---|---|---|---|---|
| 1 | PE-PLAN05-01 | major | **Fixed** in `6c3ffcdd` | CI-TIERS-a: highest tier wins, executable floor, `api-*.md` tier 2, negatives in PRC-2.2. Both reviewers confirmed it fixed in round 2 |
| 2 | PE-PLAN05-02 | major | **Fixed** in `6c3ffcdd` and `244b8053` | security APPROVE on every tier 2 PR with 4 negatives (`6c3ffcdd`); author-role source moved to the tier 2 `ticket-owners.json` (`244b8053`, R2-02); bootstrap gap closed by R3-01 (row 23) |
| 3 | PE-PLAN05-03 | major | **Fixed** in `6c3ffcdd` | ST-075d reuses `RACKET_FAULT_INJECTION` under `APP_ENV=test`; ST-075c tier 2; env and compose pin. Both reviewers confirmed it in round 2 |
| 4 | PE-PLAN05-04 | minor | **Fixed** | `test_bola_routes_complete` is dropped. ST-078d, NFR-050.6, the §5 TDD table, IT-05-07 (retired) and the G05-07 method now use the existing `backend/tests/regression/test_bola_matrix.py::test_endpoint_inventory_has_no_route_missing_from_the_matrix` (line 145) and its negative `test_a_route_without_a_probe_is_reported` (line 158). ST-078d's red-first test is the `no-store` IT. `grep -rn bola_routes_complete docs/sprints` → only this table |
| 5 | PE-PLAN05-05 | minor | **Fixed** | ST-076b: `corrections_fingerprint(session)` lives in `racket/matches/scorebook/integrity.py` (Match & Scoring owns corrections, context map C4; `racket/scoring/` holds only `__init__.py`) and is published through the context port `racket.matches.public`. The `racket-integrity` CLI in `racket.platform.integrity` imports only that port; a unit test fails on a direct `racket.matches.scorebook` import. §15 files updated |
| 6 | PE-PLAN05-06 | minor | **Fixed** | ST-077 `depends_on` = SEC-5, ST-076a in §3.3, §3.8 DoR and §15. IT-05-05 and NFR-063.1 add the negative "zero backup artefacts found → fail", so the test cannot pass empty |
| 7 | PE-PLAN05-07 | minor | **Fixed**, dry-run recorded | G05-06 runs every `cd` inside a `( … )` subshell, so `junit_rate.py` runs from the root. Dry-run in scorecard §6 (G05-06 row) and below |
| 8 | PE-PLAN05-NIT-1 (process count 12 vs 11) | nit | **Fixed** | sprint-05 §2 "11 of 46 tickets (5 CI-*, 4 QA, 2 EM-*)"; kickoff PM-3 the same. Units stay 7.5 of 26 |
| 9 | PE-PLAN05-NIT-2 (`inject_5xx.py` and `--flags` defaults) | nit | **Fixed** | G05-02's clean run now passes `--base-url` and `--prom` explicitly; G05-03's planted run passes `--flags on` |
| 10 | PE-PLAN05-NIT-3 (`.claude/agents` `tools:` at tier 0) | nit | **Fixed** | CI-TIERS-a: a `.claude/agents/*.md` change to the front matter `tools:` line is tier 2; body-only edits stay tier 0. Fixtures for both; PRC-2.2 negative added |
| 11 | PLAN05-QA-01 (62 vs 56 NFR rows) | nit | **Fixed** | §0.6 says "56 atomic NFR items" with the counting command; `grep -cE '^\| NFR-[0-9]+\.[0-9]' 05/requirements-breakdown.md` → 56 on this head |
| 12 | PLAN05-QA-02 (12 vs 11) | nit | **Fixed** | same edit as row 8 |
| 13 | PLAN05-QA-03 (shared files, not disjoint) | nit | **Fixed** | §3.6 item 4 names the shared files and their merge order (`ci.yml`: CI-NOTICE-CANCELLED → CI-DOC-CHECK → CI-RECON-ON-PR; `infra/compose.yaml`: ST-075b → ST-076a; `nightly-quality.yml`: ST-074 → ST-079 → ST-084b); the later PR merges `origin/main` and re-runs checks first. The §15 header no longer says "disjoint per lane" |
| 14 | PE-PLAN05-R2-01 | major | **Fixed** in `244b8053` | `COMPOSE_PROJECT_NAME` exported for the G05-02 block; red/green dry-run in round 2 evidence. Both reviewers confirmed it in round 3 |
| 15 | PE-PLAN05-R2-02 | major | **Fixed** in `244b8053` | `ticket-owners.json` (46 rows) is the gate's only input, tier 2, drift test planned. Both reviewers confirmed it in round 3; its bootstrap gap is row 23 |
| 16 | PE-PLAN05-R2-03 | minor | **Fixed** | ST-075d: the fault middleware is registered before `app.add_middleware(HttpMetricsMiddleware)` (`app.py` line 83), so it sits inside it. Unit test pins the order (negative: fault middleware outermost fails). IT-05-12 and NFR-041.6 assert, with an `InMemoryMetricReader` (as `test_slis.py`), that the injected 500 is recorded in `http.server.request.duration` with `http.response.status_code=500` |
| 17 | PE-PLAN05-R2-04 | minor | **Fixed** | ST-075c lists five test-mode differences on the drill stack: cookie not `__Host-`/Secure; `DEV_IDENTITY_ENABLED` default on in `Settings` (`settings.py` line 184) but set explicitly by `compose.yaml` line 11 from `.env`, with dev users seeded when on (`app.py` line 44); OpenAPI docs public (`app.py` line 63); no migrate-on-start (`app.py` line 42; the `migrate` service runs); the seam itself. SEC-5 and the security reviewer judge the stack on that list |
| 18 | PLAN05-QA-04 | major | **Fixed** in `244b8053` | migration glob `backend/src/racket/migrations/**` + glob liveness test. Both reviewers confirmed it in round 3 |
| 19 | PLAN05-QA-05 | minor | **Fixed** in `244b8053` | same fix as row 14; QA confirmed it in round 3 |
| 20 | PLAN05-QA-06 (§7.3b, round 2) | minor | **Fixed** | this table: one row per id of every round |
| 21 | PLAN05-QA-07 (§7.3b, round 3) | major | **Fixed** | this table; the count check is below |
| 22 | PLAN05-QA-08 (G05-06 path) | major | **Fixed**, dry-run recorded | as row 7. The dry-run also found that the old `--require a,b,c` form failed from the root as well (author-found AF-PLAN05-01, below) |
| 23 | PE-PLAN05-R3-01 (owner-file bootstrap) | major | **Fixed** | CI-TIERS-b and PRC-2.7: fixed `BOOTSTRAP_OWNERS` table in `scripts/ci/review_tiers.py` (tier 2) read first: (a) `s<nn>/plan` → engineering-manager; (b) `s<nn>/ci-fix-<slug>` → sre-devops-engineer, `s<nn>/owners-<slug>` → engineering-manager for a mid-sprint ticket's row; (c) `docs/<slug>` → engineering-manager at tier 0 only, and close PRs such as `s05/retro-05` keep their Sprint 5 row because the lookup uses the branch's sprint number and owner files are never deleted. A missing owner file without a bootstrap shape fails closed naming "merge s<nn>/plan first"; a conflicting JSON row fails closed; a PR adding its own row is still checked against `main`. One positive and one negative fixture per case |
| 24 | PE-PLAN05-R3-02 (§7.3b, round 3) | major | **Fixed** | this table (rows 4-13, 16, 17, 19, 20 had no row before) |
| 25 | PE-PLAN05-R3-03 (RETRO-05 tier vs `status.json`) | minor | **Fixed** | `docs/sprints/*/status.json` leaves the tier 2 list (no gate reads it since the cross-check was dropped) and is an explicit tier 0 data rule, so RETRO-05 stays tier 0 truthfully. Fixture "status.json only → 0"; PRC-2.2, PRC-2.3, §3.4 and §15 RETRO-05 rows updated. `ticket-owners.json` stays tier 2. (The round 2 table above says status.json is tier 2; that is superseded here) |

**Count check (§7.3b):** 25 finding ids from the six reviews; 25 rows in this table (rows 1-25, one per id). Fixed 25, deferred 0, rejected 0. Open blocker/major after this round: 0 by the author's count, pending the reviewers' round 4 re-check.

**Author-found (not reviewer ids, so not in the count):**

| Id | Severity | Disposition |
|---|---|---|
| AF-PLAN05-01 | major | **Fixed.** `junit_rate.py` needs `--include` and takes one regex per `--require`, so the G05-06 form `--require data_classification,no_store,pii_labels` failed even from the root (rc 2). Now `--include 'test_it_05_' --require data_classification --require no_store --require pii_labels` |
| AF-PLAN05-02 | minor | **Fixed.** The `cd` defect of PE-PLAN05-07 was also in G05-04 (`browser_matrix.py` ran from `web/`), G05-07 and G05-09 (`unofficial_notice.py`, `rollback_drill.py` ran from `web/`). Every `cd` in §4 now sits in a subshell |

The structured ticket list changed in one dependency (ST-077 + ST-076a) and one file list (ST-076b). `ticket-owners.json` holds only `{id, branch, owner}`, and no id, branch or owner changed, so it needs no edit; the drift check below confirms it still equals §15.

### Round 3 evidence

| Check | Command | Result |
|---|---|---|
| G05-06 old form (red) | from `web/`: `python3 scripts/measure/junit_rate.py reports/g06-be.xml --require data_classification,no_store,pii_labels` | rc 2: can't open `web/scripts/measure/junit_rate.py` |
| G05-06 old arguments from the root (red) | same command from the root | rc 2: "the following arguments are required: --include" |
| G05-06 step 1 (corrected) | `(cd backend && uv run pytest -q tests/integration/test_it_05_data_classification.py tests/integration/test_it_05_no_store.py tests/integration/test_it_05_pii_labels.py --junitxml ../reports/g06-be.xml)` | rc 4 (files are planned outputs); `reports/g06-be.xml` written at the root; `pwd` still the root afterwards |
| G05-06 step 3 on that report | `python3 scripts/measure/junit_rate.py reports/g06-be.xml --include 'test_it_05_' --require data_classification --require no_store --require pii_labels` | rc 1 (`selected 0`, 3 missing), as expected before the tickets |
| G05-06 step 3 on a passing fixture | same command, fixture JUnit with the 3 IT files passing | **rc 0** (`selected 3, passed 3, ok true`) |
| G05-06 planted failure | the same plus `--require missing_suite` | rc 1 |
| Existing paths named this round | `[ -e ]` on `backend/tests/regression/test_bola_matrix.py`, `backend/tests/regression/bola.py`, `backend/src/racket/matches/public.py`, `backend/src/racket/matches/scorebook/`, `backend/src/racket/platform/app.py`, `backend/src/racket/platform/settings.py`, `backend/src/racket/platform/slis.py`, `backend/tests/unit/platform/test_slis.py`, `infra/compose.yaml`, `scripts/measure/junit_rate.py`, `docs/architecture/context-map.md` | all exist |
| Code facts behind the fixes | `app.py` lines 42, 44, 63, 83; `settings.py` line 184; `compose.yaml` line 11; `test_bola_matrix.py` lines 145, 158; `bola.py` `EXEMPT`/`uncovered_routes`; context map C4 | as cited in rows 4, 5, 16, 17 |
| Owner file vs §15 | JSON parse; owners ∈ `.claude/agents/*.md` stems; §15 `(id, branch)` set == JSON set | 46 JSON rows, 46 §15 rows, 0 bad owners, 46 unique branches, sets equal (drift none) |
| Citations | no new `[ASB/…]` or `[EP/…]` id added this round | unchanged |

### Cost per PR (ADR 0056 decision 1), review rounds

| Round | Wall time (min) | total_cost_usd / tokens |
|---|---|---|
| Fix round 1 (`6c3ffcdd`) | not measured | not measured |
| Fix round 2 (`244b8053`) | not measured | not measured |
| Fix round 3 (this head) | about 40 | not measured (this invocation does not expose `total_cost_usd`) |
