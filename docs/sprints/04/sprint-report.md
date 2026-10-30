# Sprint 4 report: runnable R1 prototype (rules-only plan and drill library), privacy and quotas behind flags

- **Prepared by:** engineering-manager, ticket RETRO-04, at the sprint close on 2026-10-29, and **updated at the second close on 2026-10-30**, after the fix wave (retro action C2: 12 ticket PRs, #162-#173) and SMOKE-04-r2 (#174). The review with the PO keeps its planned date, 2026-12-11 (sprint-04 header).
- **Heads measured:** (1) `origin/main` `b9d0dc3` (merge of PR #152, ST-065, the last Sprint 4 feature merge). Measured by SMOKE-04 (#159) and VERIFY-04-r3 (#160); this is the **measurement of record** for the scorecard. (2) `origin/main` **`d48f19a3`** (merge of PR #173, SRE-VERIFY04R3-03, the last fix-wave merge). Measured by **SMOKE-04-r2** (#174, sre-devops-engineer with senior-qa-engineer, folded into this PR: `smoke.md` top section, `decisions/SMOKE-04-r2.md`). No VERIFY round has run at `d48f19a3` yet (VERIFY-04-r4 is the first carry-over row, §10).
- **Sources:** `goal-scorecard.md` §2 (r3 values), `smoke.md` (SMOKE-04 and SMOKE-04-r2), `review-rounds.md` (with both RETRO-04 reconciliations), the 73 per-ticket files in `decisions/`, and GitHub REST read with the rules of `scripts/ci/merge_ready.py` (commands in §2, §7 and §11).

> **Second close in one paragraph (2026-10-30).** All 12 Sprint 4 majors and EM-PR27-01 now have a merged fix. The ledger reads **open 0** (`open_defects.py` both ledgers → rc 0). CI on `main` is green at `d48f19a3` (push run 40999590501: 17 jobs, `ci-gate` success). SMOKE-04-r2 is **green** live at `d48f19a3`, with flags off and with flags on. Steps 1-10 of the plan journey pass, including "Not for me". `GET /me/plan` holds 50 RPS at p95 24.5 ms. The flag-on E2E project passes 6 of 6, and the privacy and quota harness returns rc 0. **The goal of record is still 2 of 12, not met**: a smoke runs one pass of each method, and only a VERIFY round counts (PO rule, ADR 0055). SMOKE-04-r2 and the fix tickets' live dry-runs suggest 11 of 12 rows will pass in VERIFY-04-r4. G04-05 (e) waits on one senior-qa-engineer decision, the scoped safety grep (TCR row 2026-10-30), §1.4.

## 1. Goal and scorecard (read this first)

> **The Sprint 4 goal is NOT met** under the PO standing rule: VERIFY-04-r3 met **2 of 12** metrics live (G04-04 plan eval, G04-06 fresh-checkout prototype) on `main` at `b9d0dc3`. CI on `main` is green at that head (push run 40924867330: 17 jobs success or allowed skip, `ci-gate` success).
>
> **The prototype runs.** `make up` + `make demo` on a fresh checkout give Ivy a tagged match, her score sheet, her stats and a 2-week plan with 6 sessions and 12 cited assignments, and the demo is idempotent (G04-06). Steps 1-8 and 10 of the live journey pass in every run: sign-in, upload, Quick Tag, stats, plan generation (p95 59.5 ms against 5 s), determinism 3/3, weakness ranking, plan rules, citations, the limited-data note, offline "done" and the other-account check. Plan correctness passes in substance (golden 9/9, scenarios 39/39, property 1,000 examples, determinism 3/3). The privacy and quota behaviour is correct when the flags are on.
>
> **Why 10 rows are "no":** two product gaps, two content gaps, and seven harness, test, method or configuration defects:
> - **Product:** G04-02 (c) `GET /me/plan` reaches only 34.4 RPS (p95 3,229 ms) at a 50 RPS load; G04-11 mutation on `coaching/plan` is 0.6753 against 0.80. `GET /me/quota` is also missing (contract gap, no row fails on it alone).
> - **Content:** G04-01 step 9, "Not for me": a solo wall player has only one fitting reviewed drill per targeted metric, so every swap answers `409 no_alternative`. G04-05: one coach-reviewed footwork drill has no safety note.
> - **Tests, harness and methods:** the flag-on E2E specs never answer the age question (G04-07, and so G04-08 has no R/Q checks); `live_privacy.py` reads the error code at the wrong level (G04-09, G04-10); `junit_rate --require` matches test names, not markers (G04-03); two IT ids are not named `test_it_04_*`, and `DOMAIN_TEST_PATHS` lacks coaching (G04-11).
> - **Configuration:** `infra/compose.yaml` forwards no `FEATURE_*` or other Sprint 4 setting, so `make up` cannot start the flag-on stack.
> - **Ledger:** G04-12 (c) is open 13 after this PR's reconciliation (one Sprint 3 major, EM-PR27-01, and 12 Sprint 4 majors written from the verifiers' findings). (a) CI and (b) the post-merge verdict audit (57 of 57) pass.

### 1.1 Metrics: target against actual (VERIFY-04-r3, `b9d0dc3`, 2026-10-29)

| ID | Target | Actual | Met | Evidence | Owner if not met |
|---|---|---|---|---|---|
| G04-01 | 5 of 5 live runs pass all 10 steps | 0 of 5. Steps 1-8 and 10 pass in every run; step 9 ("Not for me") → 409 `no_alternative` (AN-04 has only `pb.drive.wall-margin` for 1 player + wall + intermediate) | no | `live_plan.py --runs 5 --determinism 3` → rc 1, `runs_passed 0`; SMOKE-04 `--runs 1` → rc 1 | pickleball-domain-coach |
| G04-02 | (a) p95 ≤ 5,000 ms n ≥ 20; (b) p95 ≤ 1,000 ms n ≥ 5; (c) 50 RPS: p95 ≤ 300, p99 ≤ 800 ms, ≥ 99.5%, ≥ 47.5 RPS | (a) 59.5 ms n 20; (b) 82.1 ms n 5; (c) p95 3,229 ms, p99 4,322 ms, 100%, 34.4 RPS (idle host, one uvicorn process) | no | `live_plan.py --load --rps 50 --duration 60` → rc 1, `achieved_rps 34.41` | senior-backend-engineer |
| G04-03 | golden 100%; scenarios 100%; property 0 over ≥ 1,000; determinism 3/3 | product passes all four (9/9 + 9 live comparisons, 39/39, 1,000/0, 3/3 ×5); method fails closed on `junit_rate --require` | no | `pytest -m weakness_golden` 9 passed; `junit_rate --require weakness_golden` → rc 1 `missing` | senior-qa-engineer |
| G04-04 | ≥ 30 cases; pass^3 100%; CI step green | 32 of 32 cases × 3 runs; CI plan-eval step success | **yes** | `racket-plan-eval --runs 3` → rc 0; run 40924867330 | — |
| G04-05 | ≥ 20 reviewed drills; lint 0; coverage 0 empty; gap fixture rc 1; safety 0 missing; CI green | 23 reviewed; lint ok; coverage rc 0; gap fixture rc 1 naming AN-05 × beginner; CI green; safety grep 6 lines (1 coach-reviewed volley drill, 5 draft fixtures) | no | G04-05 (e) grep → 6 lines | pickleball-domain-coach |
| G04-06 | fresh checkout: `make up`/`demo`/`demo`/README/`down` rc 0, idempotent | every step rc 0; plan 200 with 6 sessions, 12 cited assignments; second demo keeps plan id, matches 1 → 1; README check ok | **yes** | worktree `verify-04-r3`: `make up`, `make demo` ×2, `check_readme_quickstart.py`, `make down` → rc 0 | — |
| G04-07 | 100% non-skipped; E2E-04-01..05; ≤ 6 named skips; 0 flaky ×3; flag-on 3/3 ids | flags off 145 passed, 0 failed, 6 named skips, E2E-04-01..05 12/12, 0 flaky; flag-on project 3 of 6 (E2E-04-07, -08 stop at `/welcome/age`) | no | `PW_PROJECTS=flags-on playwright test` → 3 failed, 3 passed | senior-frontend-engineer |
| G04-08 | axe 0 and targets 0 with P, A, R, Q; keyboard; 320/360 | axe 75 checks, 0 serious/critical; targets 0; P and A covered; no R check, no Q over-limit target check, settings at 320/360 never reached | no | `jq` over `e2e.json`, `e2e-flags.json`: 0 `axe-R-*` | senior-frontend-engineer |
| G04-09 | flags off pass; flags on 3/3 accounts: age, retention, consent | product passes (flags-off routes 404; under-18 403 `under_age`, 0 rows; retention 3/3; consent 3/3); harness fails on the nested error code; flags on only via a scratch Compose override | no | `live_privacy.py --flags on --runs 3` → rc 1 `under-18 answer status 403 None` | senior-qa-engineer |
| G04-10 | 10 accepted / 40 refused; quota refused with 0 bytes; flags off pass; 6 alert rules | product passes (10 × 201, 40 × 429 with `retry_at`; over-quota 429, 0 bytes; promtool SUCCESS, 6 rules); harness fails on the same defect; `GET /me/quota` 404 | no | `live-privacy.json` burst 10 × 201 then 40 × 429 | senior-qa-engineer |
| G04-11 | IT ids 100%; changed ≥ 85%, coaching ≥ 90%, web ≥ 80%; mutation coaching ≥ 0.80, rules ≥ 0.85; budgets | IT-04 224/224 but IT-04-11/-15 not found by name; coverage 98% / 98% / 94.15%; mutation coaching/plan **0.6753**, weakness 0.8056, rules 0.8635; unit 35.6 s ok; domain with coaching > 10 s and not in `DOMAIN_TEST_PATHS`; serial IT > 600 s | no | `mutation_score.py --target src/racket/coaching/plan` → rc 1; `run_with_budget.py 10 …` → rc 124 | senior-backend-engineer |
| G04-12 | CI jobs green; 100% PR verdicts; 0 open blocker/major | (a) 17 jobs green or allowed skip, `ci-gate` success; (b) 57/57 merged PRs (56 tickets + PLAN-04) meet the review rule on the merged head; (c) verifier: 2 (Sprint 3). **After RETRO-04: 13** (EM-PR27-01 + 12 Sprint 4 majors; PD-R1S3-01 group Fixed) | no | `open_defects.py docs/sprints/03/review-rounds.md docs/sprints/04/review-rounds.md` → rc 1, `open 13`; `merged_verdict.py` rc 0 ×57 (§2) | engineering-manager |

`@needs-verification`: the serve/receive side-out part of the weakness ranking (P7) and the drill content (P15) are reported but count toward no Must FR. The plan page and stats carry the "unofficial scoring" notice.

### 1.2 Human-gated rows (PO P12 option b): not counted in the totals

| Row | Item | Status at close |
|---|---|---|
| S4-DoD-P15 | Human coach review of the starter drills (`verified`, FR-141) | not met: waiting on P15 (23 drills at `coach-reviewed`, 0 `verified`) |
| S4-DoD-P16 | Legal review (NFR-070, US + AU) of the age wording, footage notice, consent text and retention windows (values PO-accepted, ADR 0023) | not met: waiting on P16 (texts marked interim; flags default off) |
| S4-DoD-P7 | Coach verification of the side-out rule behind the serve/receive split | not met: waiting on P7 (`side_out_verified: false` in the plan) |
| S4-DoD-P8 | Storage quota size and monthly budgets (OQ-13) | not met: waiting on P8 (20 GiB and budgets are settings, judgment) |
| S4-DoD-P6 | Screen-reader pass of Sprint 1-4 screens (NFR-027 b) | not met: waiting on P6 |
| S4-DoD-P10 | Repository visibility | not met: waiting on P10 |
| S4-DoD-P11 | Footage bucket provider (gates SPIKE-02/05, Full Tag on real footage) | not met: waiting on P11 |

No PO answer to P6, P7, P8, P10, P11, P15 or P16 is recorded since planning: `grep -n '^## Addendum' docs/requirements/po-input-2026-10-05.md` → the only later addendum is the PR-size rule (2026-10-28).

### 1.3 How the goal moved

| Round | Head | Met | Note |
|---|---|---|---|
| Planning | `c170ef0` | 0 / 12 | nothing of the spine existed |
| VERIFY-04-r1 (#116, closed unmerged 2026-10-18) | `3c4be05` | 1 / 12 | ran after 27 merges, before the plan API and UI; its FIX-04-1a..1f PRs (#117-#121) were closed with it |
| VERIFY-04-r2 (#135, closed unmerged 2026-10-18) | `09d279d` | 2 / 12 | closed as "premature" with SMOKE (#134) and FIX-04-2b..2d (#136-#138), because 10 tickets were still unmerged |
| VERIFY-04-r3 (#160, folded in here) | `b9d0dc3` | **2 / 12** | after every Sprint 4 ticket merged; SMOKE-04 (#159) agrees on every overlapping row |

### 1.4 After the fix wave: SMOKE-04-r2 at `d48f19a3` (2026-10-30; not the measurement of record)

| ID | Of record (VERIFY-04-r3, `b9d0dc3`) | Fix PR(s) | Live evidence at or before `d48f19a3` | What VERIFY-04-r4 must still run |
|---|---|---|---|---|
| G04-01 | no (0 of 5; swap 409) | #166 | SMOKE-04-r2 `live_plan.py --runs 1 --determinism 3` → rc 0, `runs_passed 1/1`, swap ok; QA-VERIFY04R3-01 dry-run on Compose at `338d7d22` → `runs_passed 5`, swap 5 of 5 | 5 runs at `d48f19a3` |
| G04-02 | no ((c) 34.4 RPS, p95 3,229 ms) | #167 | SMOKE-04-r2 `--load --rps 50 --duration 60` → rc 0, 50.0 RPS, p95 24.5 ms, p99 62.9 ms, availability 1.0; generate p95 44.5 ms (n 4) | (a) n ≥ 20 and (b) n ≥ 5 on the Compose stack |
| G04-03 | no (method fails closed) | #165 | `junit_rate.py --include '.' --require weakness_golden` → rc 0 (`decisions/QA-VERIFY04R3-02-08.md`); SMOKE-04-r2 reference 9 comparisons, 0 mismatches | the four parts as written |
| G04-04 | **yes** | — | SMOKE-04-r2 `racket-plan-eval --runs 3` → pass^3 32 of 32 | re-confirm |
| G04-05 | no ((e) safety grep 6 lines) | #166, #169 | SMOKE-04-r2: 31 reviewed drills, lint ok, coverage rc 0, gap fixture rc 1; new lint rule fails a footwork drill without a safety note. The (e) grep as written still matches the 5 draft `pb.fixture.*` files (false positives) | **senior-qa-engineer decides the TCR row 2026-10-30** (scope (e) to (a)'s population); then (a)-(e) |
| G04-06 | **yes** | — | not re-run locally (disk under the 16 GB build floor); CI run 40999590501 `make demo seeds a match` success; SMOKE-04-r2 `seed_demo.py` ×2 idempotent, same plan id | fresh checkout `make up` / `demo` ×2 / `down` |
| G04-07 | no (flag-on 3 of 6) | #164 | SMOKE-04-r2: flags off 145 passed, 6 named skips, 0 failed, 0 flaky; flags on **6 passed, 0 failed**; #164 dry-run flags on ×3 green | `--repeat-each=3` both projects |
| G04-08 | no (no R, no Q target checks) | #164 | SMOKE-04-r2 flags on: `axe-R-01`, `targets-R-01` (plain, 320, 360), `axe-Q-10-*`, `targets-Q-10-*`, 0 errors | the jq counts as written |
| G04-09 | no (harness reads the wrong level) | #163, #162 | SMOKE-04-r2 `live_privacy.py --flags on --runs 3 --quotas` → rc 0 (age, consent, retention 3 of 3); `--flags off` → rc 0. Local-process topology; Compose forwarding checked at config level (`grep -c` → 5) | flags on through `make up` (running containers) |
| G04-10 | no (same harness defect; `GET /me/quota` 404) | #163, #168 | SMOKE-04-r2: burst 10 × 201 then 40 × 429; quota 429 with stored bytes unchanged; alerts ok (6 rules); #168 live dry-run of `GET /me/quota` | as G04-09 |
| G04-11 | no (plan mutation 0.6753; IT names; domain budget) | #165, #172, #173 | `mutation_score.py --target src/racket/coaching/plan` → 0.9811 (#172); weakness 0.8056; IT-04 236/236 with every id found (#165); domain step with coaching 6.2-7.3 s of 10 s (#173); integration 391 s of 600 s (run 40991209335) | coverage and the full budget set at one head |
| G04-12 | no ((c) 13 after RETRO-04) | #170 and every row above | (a) CI green at `d48f19a3`; (b) **70 of 70** merged Sprint 4 PRs meet the review rule on the merged head (§2 and §11); (c) **open 0** after this PR | re-measure (a)-(c) |

## 2. Tickets: PR, reviews, CI and merge

All 57 Sprint 4 PRs that merged (PLAN-04 and 56 ticket PRs) meet the PO rule on the merged head: the principal-engineer's and a `senior-*` engineer's latest verdicts are APPROVE on that head, and the latest `ci-gate` run on it is success. Each was merged by the gated merge step after `merge_ready.py` rc 0 (ADR 0050 rule 1). Commands:

- Verdicts: `python3 scripts/measure/merged_verdict.py --repo nhuthuynh/racket-analytics --pr N --role principal-engineer --role <senior role>` → rc 0 for all 57 (2026-10-29).
- Lines: `PR_LABELS='[]' python3 scripts/ci/check_pr_size.py --base <merge>^1 --head <merge>^2` (production code, ADR 0054) and GitHub `additions + deletions` (all files).
- `ci-gate`: GitHub `commits/<head>/check-runs`, latest `ci-gate` run → success for all 57.
- "CHANGES REQUESTED verdicts" counts the review bodies starting `Verdict: CHANGES REQUESTED`, over all roles and rounds.

The ticket list in the RETRO-04 brief has 52 ids; GitHub shows 5 more merged PRs that belong to them or to the sprint: PLAN-04 (#87), ST-063c-part2 (#140) and ST-063c-part2-part2 (#141) (slices of ST-063c), CI-OBJSTORE-PORT-RACE (#155) and ST-072b-part2 (#157).

| # | Ticket | PR | Merged (UTC) | Open → merge | Changed lines: all / production | `size-waiver` | `qa-approved-test-change` | CHANGES REQUESTED verdicts before APPROVE | APPROVE on merged head | `ci-gate` on merged head |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | PLAN-04 | #87 | 2026-10-17 11:22 | 1.1 h | 1118 / 0 | yes | — | 3 | principal-engineer + senior-qa-engineer (`8bdbd53`) | success |
| 2 | PD-4 | #88 | 2026-10-18 00:47 | 13.3 h | 314 / 0 | — | — | 3 | principal-engineer + senior-frontend-engineer (`ef33530`) | success |
| 3 | PE-4 | #89 | 2026-10-17 14:15 | 2.8 h | 322 / 0 | — | — | 2 | principal-engineer + senior-backend-engineer (`2b00882`) | success |
| 4 | SEC-4 | #90 | 2026-10-17 13:51 | 2.2 h | 251 / 0 | — | — | 0 | principal-engineer + senior-backend-engineer (`4ac1764`) | success |
| 5 | COACH-4 | #91 | 2026-10-17 14:16 | 2.6 h | 314 / 0 | — | — | 1 | principal-engineer + senior-ml-cv-engineer (`8de6ada`) | success |
| 6 | C4-G12 | #92 | 2026-10-17 13:51 | 2.2 h | 44 / 0 | — | — | 0 | principal-engineer + senior-frontend-engineer (`7ac5575`) | success |
| 7 | PM-4 | #93 | 2026-10-17 14:21 | 2.6 h | 170 / 0 | — | — | 2 | principal-engineer + senior-qa-engineer (`fddf131`) | success |
| 8 | C4-TAC5 | #94 | 2026-10-17 14:52 | 3.0 h | 247 / 0 | — | yes | 0 | principal-engineer + senior-backend-engineer (`8c24618`) | success |
| 9 | C4-CA | #95 | 2026-10-17 14:26 | 2.3 h | 400 / 19 | — | — | 0 | principal-engineer + senior-backend-engineer (`e30b53a`) | success |
| 10 | C4-LOCUST | #96 | 2026-10-17 14:27 | 2.1 h | 745 / 116 | yes | — | 0 | principal-engineer + senior-qa-engineer (`6fa4c88`) | success |
| 11 | C4-RED | #97 | 2026-10-17 13:57 | 1.4 h | 396 / 114 | — | — | 0 | principal-engineer + senior-qa-engineer (`16a55eb`) | success |
| 12 | C4-RECON | #98 | 2026-10-17 14:20 | 1.6 h | 796 / 266 | yes | — | 0 | principal-engineer + senior-backend-engineer (`04fffbb`) | success |
| 13 | ST-067 | #99 | 2026-10-17 17:26 | 2.2 h | 394 / 112 | — | — | 0 | principal-engineer + senior-qa-engineer (`4337bcc`) | success |
| 14 | ST-055 | #100 | 2026-10-17 19:21 | 4.1 h | 1307 / 440 | yes | — | 1 | principal-engineer + senior-ml-cv-engineer (`1b2c59b`) | success |
| 15 | ST-058a | #101 | 2026-10-17 17:29 | 2.1 h | 365 / 283 | — | — | 0 | principal-engineer + senior-qa-engineer (`c861255`) | success |
| 16 | ST-056 | #102 | 2026-10-17 18:14 | 2.5 h | 1755 / 544 | yes | yes | 0 | principal-engineer + senior-qa-engineer (`049edd4`) | success |
| 17 | QA-HARNESS-4a | #103 | 2026-10-17 18:33 | 2.8 h | 1099 / 569 | yes | — | 2 | principal-engineer + senior-backend-engineer (`db4fc33`) | success |
| 18 | ST-073 | #104 | 2026-10-17 18:27 | 2.5 h | 1205 / 445 | yes | — | 2 | principal-engineer + senior-backend-engineer (`62444a8`) | success |
| 19 | QA-HARNESS-4b | #105 | 2026-10-17 19:04 | 3.1 h | 1077 / 378 | yes | — | 4 | principal-engineer + senior-backend-engineer (`f829703`) | success |
| 20 | CI-SIGNIN-HYDRATION | #106 | 2026-10-17 23:20 | 4.7 h | 138 / 7 | — | — | 0 | principal-engineer + senior-qa-engineer (`f535075`) | success |
| 21 | ST-058b | #107 | 2026-10-17 20:04 | 0.6 h | 379 / 290 | — | — | 0 | principal-engineer + senior-qa-engineer (`6d7a9ec`) | success |
| 22 | ST-057 | #108 | 2026-10-17 20:58 | 1.3 h | 1154 / 380 | yes | — | 1 | principal-engineer + senior-qa-engineer (`05ca724`) | success |
| 23 | ST-061a | #109 | 2026-10-17 20:47 | 1.1 h | 1023 / 496 | yes | yes | 1 | principal-engineer + senior-qa-engineer (`a00b146`) | success |
| 24 | ST-058c | #110 | 2026-10-17 21:49 | 0.7 h | 509 / 388 | yes | — | 0 | principal-engineer + senior-qa-engineer (`e6e1fc7`) | success |
| 25 | ST-061b | #111 | 2026-10-18 06:32 | 9.2 h | 2206 / 798 | yes | yes | 2 | principal-engineer + senior-qa-engineer (`6fdfc4d`) | success |
| 26 | ST-059 | #112 | 2026-10-18 01:16 | 1.7 h | 508 / 147 | yes | — | 0 | principal-engineer + senior-backend-engineer (`8181cac`) | success |
| 27 | ST-060 | #113 | 2026-10-18 00:56 | 1.2 h | 2224 / 689 | yes | — | 0 | principal-engineer + senior-backend-engineer (`b305901`) | success |
| 28 | PD-4b | #114 | 2026-10-18 02:27 | 0.9 h | 476 / 0 | yes | — | 2 | principal-engineer + senior-frontend-engineer (`d6f1c6b`) | success |
| 29 | CI-DRAFT-SKIP | #122 | 2026-10-18 05:26 | 0.4 h | 358 / 22 | — | — | 0 | principal-engineer + senior-qa-engineer (`0b477d6`) | success |
| 30 | ST-063a | #123 | 2026-10-18 09:26 | 2.6 h | 1635 / 665 | yes | — | 0 | principal-engineer + senior-backend-engineer (`8542a63`) | success |
| 31 | ST-062 | #124 | 2026-10-18 10:06 | 3.0 h | 945 / 298 | yes | yes | 1 | principal-engineer + senior-qa-engineer (`5cfad39`) | success |
| 32 | ST-063b | #125 | 2026-10-18 10:07 | 3.0 h | 275 / 140 | — | — | 1 | principal-engineer + senior-backend-engineer (`8c5bc34`) | success |
| 33 | ST-064 | #126 | 2026-10-18 09:20 | 1.8 h | 397 / 65 | — | — | 0 | principal-engineer + senior-backend-engineer (`397c38c`) | success |
| 34 | ST-068a | #127 | 2026-10-18 10:13 | 2.7 h | 920 / 395 | yes | — | 2 | principal-engineer + senior-qa-engineer (`c7cd0eb`) | success |
| 35 | ST-062-part2 | #128 | 2026-10-18 18:02 | 10.2 h | 1556 / 489 | yes | yes | 9 | principal-engineer + senior-qa-engineer (`9877bb4`) | success |
| 36 | ST-063b-part2 | #129 | 2026-10-18 17:00 | 9.1 h | 251 / 104 | — | — | 1 | principal-engineer + senior-qa-engineer (`a6ada53`) | success |
| 37 | ST-072a | #130 | 2026-10-18 10:39 | 2.7 h | 551 / 158 | yes | — | 2 | principal-engineer + senior-qa-engineer (`3d2e5fa`) | success |
| 38 | ST-069 | #131 | 2026-10-18 12:34 | 1.6 h | 1196 / 505 | yes | — | 0 | principal-engineer + senior-qa-engineer (`b7c1dd8`) | success |
| 39 | ST-063b-part2-part2 | #132 | 2026-10-18 18:28 | 7.0 h | 657 / 308 | yes | — | 1 | principal-engineer + senior-qa-engineer (`751289b`) | success |
| 40 | ST-070 | #133 | 2026-10-18 16:59 | 4.1 h | 1173 / 520 | yes | — | 0 | principal-engineer + senior-backend-engineer (`6c7f8b4`) | success |
| 41 | ST-063c | #139 | 2026-10-18 19:40 | 1.3 h | 376 / 12 | — | — | 1 | principal-engineer + senior-backend-engineer (`eeb3634`) | success |
| 42 | ST-063c-part2 | #140 | 2026-10-18 19:40 | 1.3 h | 930 / 329 | yes | — | 2 | principal-engineer + senior-backend-engineer (`9b795d1`) | success |
| 43 | ST-063c-part2-part2 | #141 | 2026-10-18 20:30 | 1.4 h | 445 / 79 | yes | — | 2 | principal-engineer + senior-backend-engineer (`2670844`) | success |
| 44 | ST-063c-swap-ui | #145 | 2026-10-19 01:08 | 0.9 h | 624 / 278 | yes | — | 0 | principal-engineer + senior-backend-engineer (`63cd80b`) | success |
| 45 | ST-063c-outbox-ui | #146 | 2026-10-19 01:46 | 0.5 h | 772 / 335 | yes | — | 1 | principal-engineer + senior-backend-engineer (`28abf71`) | success |
| 46 | ST-066 | #147 | 2026-10-29 14:12 | 252.2 h | 270 / 47 | — | — | 0 | principal-engineer + senior-qa-engineer (`ea8d419`) | success |
| 47 | CI-CERTIFI-ADVISORY | #148 | 2026-10-22 09:28 | 0.6 h | 18 / 0 | — | — | 0 | principal-engineer + senior-qa-engineer (`16f5e38`) | success |
| 48 | CI-OTEL-ADVISORY | #149 | 2026-10-29 08:52 | 10.7 h | 129 / 4 | — | — | 0 | principal-engineer + senior-qa-engineer (`26ed6cb`) | success |
| 49 | CI-DAILY-AUDIT | #150 | 2026-10-29 12:37 | 14.3 h | 1360 / 443 | yes | — | 2 | principal-engineer + senior-qa-engineer (`a360feb`) | success |
| 50 | CI-SIZE-PROD-ONLY | #151 | 2026-10-29 16:09 | 17.7 h | 435 / 79 | — | yes | 1 | principal-engineer + senior-qa-engineer (`ab66bdd`) | success |
| 51 | ST-065 | #152 | 2026-10-29 17:48 | 4.8 h | 915 / 36 | yes | — | 0 | principal-engineer + senior-frontend-engineer (`e979f17`) | success |
| 52 | ST-068b | #153 | 2026-10-29 14:59 | 1.7 h | 859 / 309 | yes | — | 1 | principal-engineer + senior-backend-engineer (`a6e0f94`) | success |
| 53 | ST-071 | #154 | 2026-10-29 15:06 | 1.8 h | 1033 / 463 | yes | — | 1 | principal-engineer + senior-backend-engineer (`2a22967`) | success |
| 54 | CI-OBJSTORE-PORT-RACE | #155 | 2026-10-29 13:58 | 0.3 h | 559 / 100 | yes | — | 0 | principal-engineer + senior-qa-engineer (`69031aa`) | success |
| 55 | ST-072b | #156 | 2026-10-29 14:59 | 1.3 h | 269 / 29 | — | — | 0 | principal-engineer + senior-backend-engineer (`58946de`) | success |
| 56 | ST-072b-part2 | #157 | 2026-10-29 15:33 | 1.4 h | 319 / 55 | — | — | 0 | principal-engineer + senior-backend-engineer (`4d35d3a`) | success |
| 57 | CI-INFRA-BUDGET | #158 | 2026-10-29 17:09 | 0.3 h | 341 / 34 | — | — | 0 | principal-engineer + senior-qa-engineer (`5a038ee`) | success |

Summary: median open → merge 2.2 h (mean 7.7 h; max 252 h, ST-066 #147, opened 2026-10-19 and merged 2026-10-29 after the pause in §4). 29 of 57 PRs merged with no CHANGES REQUESTED verdict; the most was 9 (ST-062-part2 #128).

### 2.1 PRs not merged

| PR | Ticket | State | Why | Content now |
|---|---|---|---|---|
| #115, #134 | SMOKE-04 (rounds 1 and 2) | closed unmerged 2026-10-18 | closed by the orchestrator as premature: run before the build was complete | superseded by SMOKE-04 at `b9d0dc3` (#159, folded in here) |
| #116, #135 | VERIFY-04-r1, VERIFY-04-r2 | closed unmerged 2026-10-18 | as above; ADR 0050 rule 4 asks for each round's PR to merge before the next round (retro 4 M1) | superseded by VERIFY-04-r3 (#160, folded in here); the r1/r2 findings recur in r3 |
| #117-#121, #136-#138 | FIX-04-1a..1f, FIX-04-2b..2d | closed unmerged 2026-10-18 | closed with their verification round. #137 (FIX-04-2b) held a cheaper `GET /me/plan` read (scope key) that G04-02 (c) still needs | carry-over (§9, SRE-VERIFY04R3-01) |
| #142, #143 | ST-063c-part2-part2-part2, …-part2 | closed unmerged 2026-10-18/19 | the split for size mixed code and tests in one commit, so the red-first check (C4-RED) could not pass and pushed history may not be rewritten | rebuilt red-first as #145 and #146 (merged) |
| #144 | ST-063c-part2-part2-part2 (rebuild r2) | **open, draft** | superseded by #145 the same night and never closed | ledger EM-RETRO04-01 (minor): close with a pointer to #145 |
| #159, #160 | SMOKE-04, VERIFY-04-r3 | open → **closed with a pointer by this ticket** | evidence PRs; their commits are merged into this PR's branch unchanged (`6f7a711`, `823d70f`) | `smoke.md`; `goal-scorecard.md` §2; `decisions/SMOKE-04.md`, `decisions/VERIFY-04-r3.md` |

## 3. Committed against implemented and DoD-done (ADR 0010 units)

All 34 sized tickets (48 units) merged. "DoD-done" here means the story DoD **and** no open major of the RETRO-04 reconciliation traced to the ticket; a ticket with such a finding counts as implemented only.

| Lane | Planned | Implemented | DoD-done | Not DoD-done (finding) |
|---|---|---|---|---|
| BE | 17 | 17 | 10 | ST-056 2 (mutation 0.6753, QA-VERIFY04R3-07); ST-061b 2 (50 RPS read, SRE-VERIFY04R3-01); ST-067 1 (settings not forwarded by Compose, SRE-VERIFY04R3-02); ST-072a 2 (`GET /me/quota` missing, QA-VERIFY04R3-04) |
| FE | 10 | 10 | 7 | ST-071 2, ST-072b 1 (flag-on specs stop at the age gate, QA-VERIFY04R3-05/-06) |
| QA | 8.5 | 8.5 | 6.5 | QA-HARNESS-4b 1 (nested error code, QA-VERIFY04R3-03); VERIFY-04 1 (its round PRs were not merged until this PR) |
| SRE | 5.5 | 5.5 | 5.5 | — |
| ML | 4 | 4 | 4 | — |
| Coach content | 3 | 3 | 2 | ST-058c 1 (no safety note on a footwork drill, QA-VERIFY04R3-09; one fitting solo-wall drill per metric, QA-VERIFY04R3-01) |
| **Total** | **48** | **48 (1.00)** | **35 (0.73)** | 13 units |

Unsized work that also merged: 5 gate tickets, C4-G12, PLAN-04, 2 ticket slices of ST-063c, PD-4b, and 8 CI tickets (CI-SIGNIN-HYDRATION, CI-DRAFT-SKIP, CI-CERTIFI-ADVISORY, CI-OTEL-ADVISORY, CI-SIZE-PROD-ONLY, CI-DAILY-AUDIT, CI-OBJSTORE-PORT-RACE, CI-INFRA-BUDGET).

## 4. Gates and CI

- **CI on `main` at the close:** push run 40924867330 at `b9d0dc3`: success; 17 jobs, 15 success, `PR policy` and `Flaky-test report` skipped (PR-only), `ci-gate` success. New this sprint and green: `Red:` check (C4-RED, in `pr-policy`), drill coverage in `drill-lint` (ST-059), plan eval pass^3 (ST-060), Locust gate on stats and evidence (C4-LOCUST).
- **`main` CI runs since planning** (`actions/runs?branch=main&created>=2026-10-17`): push 47 success, 1 failure, 8 cancelled (6 superseded by a newer merge; #151's was cancelled by the infra job's 10-minute timeout); schedule 5 success, **8 failure**; Nightly quality 13/13 success.
- **Red `main` incidents (CI FIRST):**

| # | Red from | Cause | Fixed by | Green again | Time red |
|---|---|---|---|---|---|
| 1 | 2026-10-21 08:52 (schedule run 39570329619) | new advisory PYSEC-2026-4320 (certifi) in the dependency audit | CI-CERTIFI-ADVISORY #148 | 2026-10-22 09:45 (run 39755741172) | ≈ 25 h |
| 2 | 2026-10-23 08:59 (schedule run 39925422293) | new advisories: opentelemetry-api CVE-2026-114603, next GHSA-2464-fhr4-w9xw | CI-OTEL-ADVISORY #149; then CI-DAILY-AUDIT #150 (ADR 0053, Proposed) so an advisory opens an upgrade PR before `main` goes red | 2026-10-29 09:07 (run 40845308173) | **≈ 6 days** (scheduled runs red 2026-10-23..28; no agent session ran between 2026-10-19 and 2026-10-28) |
| 3 | 2026-10-29 12:52 (push run 40874800467, merge of #150) | infra job: port collision when parallel workers start object stores | CI-OBJSTORE-PORT-RACE #155 | 2026-10-29 14:12 | 1.3 h |
| 4 | 2026-10-29 16:23 (push run 40908731812, merge of #151) | infra job crept to its 10-minute budget and was cancelled | CI-INFRA-BUDGET #158 | 2026-10-29 17:23 | 1.0 h |

- **Policy labels:** `size-waiver` on 32 of 57 merged PRs (56%); `qa-approved-test-change` on 7. Applied only by the EM/QA decision step (separation of duties held). On 2026-10-28 the PO changed the size rule to count production code only (ADR 0054, CI-SIZE-PROD-ONLY #151).

## 5. Sprint-level DoD (sprint-04 §9)

| Item | Status | Evidence |
|---|---|---|
| Every scorecard row "yes", measured live by VERIFY-04 on `main` | **no** (2 of 12) | §1.1 |
| `make up` + `make demo` + README walkthrough on a fresh clone | **yes** | G04-06 |
| `merged_verdict.py` rc 0 for every merged Sprint 4 PR (B1) | **yes** (57/57) | §2 |
| ≤ 20% of PRs with `size-waiver`, median ≤ 300 lines (B4) | **no**: 56% waived; median 509 changed lines (all files). Counted as production code (ADR 0054, from 2026-10-28) the median is 140 and 13 of 57 (23%) are over 400 | §2 table |
| Each verification round's PR merged before the next round (ADR 0050 rule 4) | **no**: r1 and r2 closed unmerged; r3 merged only through this PR | §2.1 |
| Reconciliation row per round | **partly**: no row for r1 or r2; r3 and SMOKE-04 reconciled here | `review-rounds.md` "Ticket RETRO-04" |
| Traceability matrix lists the Sprint 4 feature files | **yes** (this PR) | `traceability-matrix.md` §16 |
| Retro 3 actions reviewed first in retro 4 | **yes** | `docs/retros/2026-12-11-sprint-04.md` §1 |
| CI green on `main` at the close | **yes** | run 40924867330 |
| Human-gated rows | not met: waiting on P6, P7, P8, P10, P11, P15, P16 | §1.2 |

## 6. Test counts by level (SMOKE-04 and VERIFY-04-r3 at `b9d0dc3`)

| Level | Result | Sprint 3 close |
|---|---|---|
| Backend (CI selection: unit, scenario, integration, regression) | 3,818 passed, 1 skipped (SMOKE-04); VERIFY-04-r3: 3,802 passed + 18 environment failures re-run green (22 passed) | 3,050 gated; IT 797 |
| Sprint 4 integration ids | IT-04 224/224 incl. BOLA plan routes; IT-04-10/-14 in `infra/tests` pass | — |
| Scenario (Sprint 4 features) | 39/39 across 6 plan features (G04-03) | 42/42 stats |
| Web unit (Vitest) | 118 files, 1,009 passed; `tsc`, ESLint rc 0 | 681 |
| E2E Chromium (flags off) | 145 passed, 6 named skips, 0 failed, 0 flaky ×3; E2E-04-01..05 12/12 | 127 + 6 skips |
| E2E flag-on project | 3 passed, 3 failed (QA-VERIFY04R3-05) | — |
| E2E WebKit | CI only (run 40924867330 success) | CI |
| Infra | 1,729 passed, 8 skipped | 936 |
| Plan eval (NFR-005 a) | 32 cases, pass^3 32/32 | — |
| Coverage | changed lines 98%; `racket.coaching` 98%; web 94.15% | 97%; analytics 98.34%; web 93.03% |
| Mutation | rules 0.8635; coaching/weakness 0.8056; **coaching/plan 0.6753** | rules 0.8635 |

## 7. Delivery metrics [EP/ENG-21, EP/ENG-19, EP/ENG-04]

| Measure | Sprint 4 | Sprint 3 |
|---|---|---|
| PRs merged into `main` | 57 (2026-10-17 11:22 → 2026-10-29 17:48 UTC): 23 on 10-17, 20 on 10-18, 2 on 10-19, 1 on 10-22, 11 on 10-29 | 71 |
| Lead time (PR open → merge) | median 2.2 h, mean 7.7 h, max 252 h | median 1.6 h, mean 3.3 h, max 51.8 h |
| PR size (all changed lines) | median 509; 33 of 57 over 400; 2 ≤ 100 | median 607; 46 of 71 over 400; 6 ≤ 100 |
| PR size (production code, ADR 0054) | median 140; 13 of 57 over 400 | — |
| Review rule met on the merged head | 57 / 57 | 68 / 71 |
| CHANGES REQUESTED verdicts per PR | mean 0.95, max 9; 29 PRs with none | 1-3 rounds on many PRs |
| Change failure rate (`main` push runs red) | 2 of 49 completed non-superseded push runs (4%): #150 and #151 | 5 of 71 (7%) |
| Time to restore `main` | 1.0 h, 1.3 h, 25 h, ≈ 6 days (§4) | 1.5 h to about 1 day |
| CI and pipeline tickets | 8 of 57 PRs (14%) | 18 of 71 (25%) |
| Unmerged PRs closed | 14 (12 evidence and FIX PRs of rounds 1-2; 2 split PRs rebuilt red-first); #144 still open | 4 evidence PRs (folded by RETRO-03) |

## 8. PO items

| Item | Status |
|---|---|
| P6, P7, P8, P10, P11, P15, P16 | open; no answer recorded since planning (§1.2) |
| PR size counts production code only (PO 2026-10-28) | applied: ADR 0054 Accepted, CI-SIZE-PROD-ONLY #151 |
| For the 2026-12-11 review | the goal is not met; the prototype runs (G04-06) and the 13 open majors are the Sprint 5 first wave (§9). Escalation: G04-01 step 9 needs either more solo-wall drills (coach) or a change to the scorecard's preferences (PM/EM decision row; the PO may prefer one) |

## 9. Carry-over to Sprint 5 (each row gets an owner and a Sprint 5 backlog row at planning)

Fix first, before any Sprint 5 feature ticket (the goal is not met and the PO rule puts open majors first). Every row is in `review-rounds.md` with its evidence.

**Status on 2026-10-30 (second close):** every major row below is **Fixed** by a merged ticket PR (§11), and PR #144 is closed. Still open: QA-VERIFY04R3-10 (minor) and C4-MIN (minors). The new carry-over list is §10.

| Ledger id | What | Owner | Closes |
|---|---|---|---|
| EM-PR27-01 (Sprint 3) | senior-backend-engineer verdict on PR #27 head `52582fd` | senior-backend-engineer | G04-12 (c) |
| QA-VERIFY04R3-01 | second reviewed solo-wall drill per targetable metric (or a decision row changing step 9's preferences) | pickleball-domain-coach; product-manager | G04-01, demo step 6 |
| SRE-VERIFY04R3-01 | `GET /me/plan` at 50 RPS (cheaper read, cf. #137; api process count) | senior-backend-engineer; sre-devops-engineer | G04-02 (c) |
| QA-VERIFY04R3-02 | `junit_rate` method for markers | senior-qa-engineer | G04-03 |
| QA-VERIFY04R3-03 | `live_privacy.py` reads `error.*` | senior-qa-engineer | G04-09, G04-10 |
| SRE-VERIFY04R3-02 | Compose forwards the Sprint 4 settings | sre-devops-engineer | demo step 9; G04-09/10 on `make up` |
| QA-VERIFY04R3-04 | `GET /me/quota` | senior-backend-engineer | contract api-sprint-04 §7 |
| QA-VERIFY04R3-05, -06 | flag-on specs answer the age question; R and Q a11y checks | senior-frontend-engineer | G04-07, G04-08 |
| QA-VERIFY04R3-07 | mutation on `coaching/plan` ≥ 0.80 | senior-backend-engineer | G04-11 |
| QA-VERIFY04R3-08 | IT-04-11/-15 found by the method | senior-qa-engineer | G04-11 (a) |
| SRE-VERIFY04R3-03 | `DOMAIN_TEST_PATHS` gains coaching inside 10 s; integration budget | sre-devops-engineer | G04-11 (d) |
| QA-VERIFY04R3-09 | safety note on `pb.volley.line-volleys-no-step-in` | pickleball-domain-coach | G04-05 (e) |
| QA-VERIFY04R3-10, EM-RETRO04-01 (minor) | demo script wording; close PR #144 | product-manager; orchestrator | — |
| C4-MIN (minor, Sprint 3 ledger) | not worked in Sprint 4; carried unchanged | each owner | — |
| ADR 0053 and ADR 0049 (both Proposed) | decide | sre-devops-engineer with principal-engineer | — |

## 10. Carry-over after the second close (for Sprint 5 planning, 2026-10-30)

The majors are closed. What is left before the goal can count as met is measurement, one QA decision and the human items:

| Item | What | Owner | Closes |
|---|---|---|---|
| VERIFY-04-r4 | A full verification round at the latest `main` (ADR 0055 rule 1: the build is merged; rule 3: its PR merges). It includes the flag-on stack through `make up` in running containers, which no local run has done (disk floor) | senior-qa-engineer with sre-devops-engineer | the scorecard of record (§1.4 last column) |
| G04-05 (e) TCR row 2026-10-30 | Decide whether to scope the safety grep to (a)'s population (`test-change-requests.md` row 21, "pending (senior-qa-engineer)") | senior-qa-engineer | G04-05 (e) |
| QA-VERIFY04R3-10 (minor) | Demo script says "12 rallies"; the product says 11 | product-manager | — |
| QA-VERIFY04R3-01 follow-up (minor) | A single-weakness plan can put both drills of one target in the same session | pickleball-domain-coach | — |
| BE-PR27-01..03 (minor/nit, Sprint 3 ledger) | Follow-ups of the post-merge review of PR #27 (row scope of the `jobs` grant; plaintext `ALTER ROLE` password in server logs) | senior-backend-engineer | — |
| ADR 0053 live check | First scheduled `Dependency audit` run and a real draft upgrade PR (the run needs admin setting 6, human; `decisions/ADR-0053-0049.md`) | sre-devops-engineer; PO (setting 6) | retro C4 success measure |
| Disk (blockers row 2) | 13-15 GB free; the 16 GB build floor stopped both smokes from building images | P5 standing approval (prune) | local image builds |
| C4-MIN (Sprint 3 minors) | carried unchanged | each owner | — |
| P6, P7, P8, P10, P11, P15, P16 | human-gated (§1.2) | PO | S4-DoD-P rows |

## 11. Second close: the fix wave and SMOKE-04-r2 (2026-10-29 20:36 → 2026-10-30 03:50 UTC)

The first close (#161) planned the fix wave as retro action C2: one red-first ticket per open major. It ran the same evening. Each of the 12 ticket PRs went through the full process: TDD with red first, a live dry-run of the method it fixes (ADR 0055 rule 2), principal-engineer and senior verdicts on the merged head, and the gated merge after `merge_ready.py` rc 0. Commands as in §2. The verdict rule was checked with `merged_verdict.py --repo nhuthuynh/racket-analytics --pr N --role principal-engineer --role <senior>` → `merged-verdict: met` and rc 0 for each of #161-#173 (2026-10-30). The ci-gate result is the latest `ci-gate` check run on the merged head. Lines are GitHub `additions + deletions` / `PR_LABELS='[]' check_pr_size.py --base <merge>^1 --head <merge>^2`.

| # | Ticket | PR | Merged (UTC) | Open → merge | Changed lines: all / production | `size-waiver` | `qa-approved-test-change` | CHANGES REQUESTED verdicts before APPROVE | APPROVE on merged head | `ci-gate` on merged head | Merge commit | Closes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 58 | RETRO-04 | #161 | 2026-10-29 20:36 | 0.4 h | 2252 / 0 | — | — | 0 | principal-engineer + senior-qa-engineer (`a970286`) | success | `6ec3c3fe` | first close (report, retro, ADR 0055, ledger reconciliation) |
| 59 | SRE-VERIFY04R3-02 | #162 | 2026-10-29 21:52 | 1.1 h | 374 / 15 | — | — | 0 | principal-engineer + senior-backend-engineer (`621acc2`) | success | `9dee347c` | SRE-VERIFY04R3-02 (Compose forwards the Sprint 4 settings; parity test) |
| 60 | QA-VERIFY04R3-03 | #163 | 2026-10-29 22:41 | 1.8 h | 172 / 34 | — | yes | 0 | principal-engineer + senior-backend-engineer (`490d48c`) | success | `aa24482b` | QA-VERIFY04R3-03 (`live_privacy.py` reads `error.*`) |
| 61 | QA-VERIFY04R3-05-06 | #164 | 2026-10-29 22:09 | 1.0 h | 184 / 2 | — | yes | 0 | principal-engineer + senior-qa-engineer (`3ce4eb4`) | success | `fae1b838` | QA-VERIFY04R3-05, -06 (flag-on specs answer A-10; R and Q checks) |
| 62 | QA-VERIFY04R3-02-08 | #165 | 2026-10-29 21:57 | 0.8 h | 383 / 41 | — | — | 0 | principal-engineer + senior-backend-engineer (`cf3f54b`) | success | `74cf968c` | QA-VERIFY04R3-02, -08 (`junit_rate` matches markers; IT-04-11/-15 names) |
| 63 | QA-VERIFY04R3-01 | #166 | 2026-10-30 00:51 | 1.7 h | 1060 / 467 | yes | yes | 1 | principal-engineer + senior-qa-engineer (`e3d6001`) | success | `a4eabcba` | QA-VERIFY04R3-01 (8 solo-wall drills; `solo+wall` coverage axis) |
| 64 | SRE-VERIFY04R3-01 | #167 | 2026-10-29 23:56 | 0.7 h | 822 / 251 | — | — | 0 | principal-engineer + senior-qa-engineer (`8ef1886`) | success | `60d2401c` | SRE-VERIFY04R3-01 (`GET /me/plan` at 50 RPS; Locust plan gate) |
| 65 | QA-VERIFY04R3-04 | #168 | 2026-10-30 00:06 | 0.6 h | 439 / 164 | — | — | 0 | principal-engineer + senior-qa-engineer (`339e0fd`) | success | `78b1f276` | QA-VERIFY04R3-04 (`GET /me/quota`) |
| 66 | QA-VERIFY04R3-09 | #169 | 2026-10-30 02:20 | 1.3 h | 414 / 57 | — | — | 0 | principal-engineer + senior-qa-engineer (`e5caa77`) | success | `3b36d4e2` | QA-VERIFY04R3-09 (safety note; lint rule) |
| 67 | EM-PR27-01 | #170 | 2026-10-30 02:20 | 1.2 h | 28 / 0 | — | — | 0 | principal-engineer + senior-qa-engineer (`2320743`) | success | `903eaf8b` | EM-PR27-01 (senior-backend verdict on PR #27; retro C1) |
| 68 | ADR-0053-0049 | #171 | 2026-10-30 02:21 | 1.0 h | 932 / 180 | — | — | 0 | principal-engineer + senior-backend-engineer (`375a4b5`) | success | `a955f98a` | retro C4 (ADR 0053 and ADR 0049 Accepted; PO notice on a red scheduled run) |
| 69 | QA-VERIFY04R3-07 | #172 | 2026-10-30 02:58 | 1.4 h | 991 / 0 | — | — | 0 | principal-engineer + senior-qa-engineer (`d58c6d0`) | success | `2bc9bc77` | QA-VERIFY04R3-07 (`coaching/plan` mutation 0.9811) |
| 70 | SRE-VERIFY04R3-03 | #173 | 2026-10-30 03:50 | 0.5 h | 590 / 83 | — | yes | 0 | principal-engineer + senior-backend-engineer (`ddea789`) | success | `d48f19a3` | SRE-VERIFY04R3-03 (coaching gates nightly; `DOMAIN_TEST_PATHS`; retro C5) |
| — | SMOKE-04-r2 | #174 | folded into this PR | — | 78 / 0 (docs) | — | — | — | (reviewed with this PR) | — | — | re-smoke of `d48f19a3`: **green**; commit `6184b023` merged into this branch unchanged, PR closed with a pointer (ADR 0055 rule 3) |

**Summary of the fix wave (12 ticket PRs, #162-#173):** median open → merge 1.05 h (mean 1.09 h, max 1.8 h). Median 426.5 changed lines (all files) and **49 production lines**. One PR is over 400 production lines (#166, 467, `size-waiver` from the EM/QA step). There was 1 CHANGES REQUESTED verdict in total (#166, round 1: the principal-engineer's PE-R1-1 pair-rule finding, fixed in the PR). `qa-approved-test-change` was used on 4 PRs (#163, #164, #166, #173), each with a TCR row. **`main` stayed green the whole time**: 13 push runs on `main` after #161 (`actions/runs?branch=main&created>=2026-10-29T20:30Z`), 12 success and 1 cancelled (`903eaf8b`, superseded 30 s later by the merge of #171). No scheduled run fell in the window.

**Sprint 4 totals after the second close:** 70 PRs merged into `main` (57 at the first close + #161-#173). All 70 meet the review rule on the merged head, with `ci-gate` success. `size-waiver` on 33 of 70 (47%). Open blocker/major: **0**. Units: 48 / 48 implemented. **DoD-done 48 (1.00)**: every major traced to a ticket in §3 is Fixed. The 13 units that §3 held back are DoD-done now (judgment; the goal of record is still VERIFY-04-r3's).

**SMOKE-04-r2 (#174) problems and how this close handles them** (`smoke.md`, `decisions/SMOKE-04-r2.md`):

| Problem raised | Disposition |
|---|---|
| sre-devops-engineer: no full Compose image build, app-container hardening, IT-00-10 or `make up` / `make demo` / `make down` from a fresh checkout. The disk was under the 16 GB build floor: `RA_MIN_FREE_GB=16 bash scripts/disk-precheck.sh` → rc 3, 14 GB after `docker builder prune -af` reclaimed 2.422 GB | Environment, not a product finding (blockers row 2 stays open). CI run 40999590501 on `d48f19a3` covers these: `Start the full stack`, `Worker sandbox IT-00-10` and `make demo seeds a match` all success. VERIFY-04-r4 runs them locally (§10) |
| sre-devops-engineer: the SMOKE-04-04 fix (#162) was checked at config level only | `docker compose … config \| grep -c 'FEATURE_AGE_GATE: "true"'` → 5. SRE-VERIFY04R3-02 is Fixed with this residual written in its row. The running-container check is in VERIFY-04-r4's scope (§10) |
| engineering-manager: the ledger rows of the SMOKE-04 findings still said Open | Closed by this PR (`review-rounds.md`, "Ticket RETRO-04 (second close)"). QA-VERIFY04R3-01 and -03 were already Fixed by their tickets. This PR adds the Fixed rows for -05, -06, -04 and SRE-VERIFY04R3-02, with the SMOKE-04-r2 evidence: `live_plan.py --runs 1 --determinism 3` → rc 0, flags-on Playwright 6 passed, `live_privacy.py --flags on --runs 3 --quotas` → rc 0. `open_defects.py` both ledgers → rc 0, `open 0` |
| senior-qa-engineer (minor, topology): `infra/tests/test_demo_seed_live.py:48` fails against a stack without the `web-tls` service | Topology limit, not a finding: `seed_demo.py` ×2 → rc 0 with the same plan id, and the CI `make demo` step on `d48f19a3` is success. No ledger row |

## 12. History of this report

- 2026-10-29: written at the sprint close (RETRO-04, #161), from VERIFY-04-r3 and SMOKE-04 at `b9d0dc3`, with the RETRO-04 ledger reconciliation (open 2 → 13).
- 2026-10-30: second close (RETRO-04, this PR), after the fix wave (#162-#173) and SMOKE-04-r2 (#174) at `d48f19a3`: head summary, §1.4, §9 status line, §10, §11; ledger open 4 → 0. The goal of record is unchanged (2 of 12) until VERIFY-04-r4.
