# Sprint 3 goal scorecard

- **Written:** 2026-10-06 at Sprint 3 planning by the engineering-manager, with the product-manager (goal wording, targets), principal-engineer (performance, snapshot and purge methods, contract assumptions), business-analyst (FR/NFR traceability) and senior-qa-engineer (test selection, fail-closed rules).
- **Why:** PO standing rule. A sprint is done only when its **goal is shown to work on a live local stack**, with every goal metric measured against its target. Unit tests alone never prove a goal.
- **Verifier fills in:** `Actual`, `Met` (yes / no) and `Evidence` (exact command, stack head SHA, result line or report path). Nothing else in this file changes without a decision-log row.
- **Sources:**
  - `docs/sprints/sprint-03.md` §1 (goal), §6 (IT and E2E ids), §8 (gates), §12 (demo);
  - `docs/requirements/functional-requirements.md` FR-006, FR-007, FR-024, FR-100..FR-103, FR-109, FR-140, FR-150, FR-151;
  - `docs/requirements/non-functional-requirements.md` NFR-004, 010, 011, 014, 017, 027, 028, 034, 038, 039, 051, 054, 066, 071..073, 078;
  - `docs/domain/metric-dictionary.md` (AN-01..AN-07 v0.1, §2 worked example);
  - ADR 0005 (Wilson, minimum n), ADR 0006 (deletion windows), ADR 0009 and ADR 0023 (rules stay PROVISIONAL-UNVERIFIED, "unofficial"), ADR 0029 (https dev stack), ADR 0030, 0033, 0037 (isolated, self-cleaning evidence; dry-run before handover; reconciliation);
  - retro 2 actions A1-A5.
- **Harness:** `scripts/measure/` (standard-library Python). Sprint 3 adds `statslib.py` (an independent reference for AN-01..AN-07, Wilson, low sample, evidence and the purge inventory), `statscontract.py`, `live_stats.py` and `stats_latency.py`. Tests: `cd infra && uv run pytest -q tests/test_measure_sprint03.py` (51 passed at planning, written red first; commit `75338b9`).
- **Contract assumptions:** the Sprint 3 routes and fields used by G03-01..G03-05 live only in `scripts/measure/statscontract.py` until `docs/architecture/api-sprint-03.md` exists (task PE-1). The principal-engineer updates that file with the contract (decision-log 2026-10-06).
- **The reference is not the product.** `statslib.starter_stats` follows the metric-dictionary formulas with `taglib`'s provisional side-out stepper and is pinned by tests to the coach's hand count (metric-dictionary §2). If the coach changes a definition (version bump), `statslib` and its tests change with a TCR row before the verifier runs.

## 1. Sprint goal (sprint-03 §1)

1. A player opens the stats of a tagged match and sees the 7 starter stats per side (AN-01..AN-07). Each shows n; each proportion a 95% Wilson interval; small samples are flagged "low sample" in text and never hidden. The values equal the coach's hand count, update after every tag or correction, and carry the "unofficial scoring (rules not yet verified)" notice. Only `coach-reviewed` metrics are shown, each with "How is this measured?".
2. Every stat has "Show me": up to 10 of the rallies behind it, with "see all n", each opening the video at that rally.
3. A player can delete a match or their account: gone from the account within 1 minute; the purge then leaves no row and no stored object; deleting the account signs out every session.
4. The team can Full Tag a consented match (labeller role only, frame by frame) and export the labels in the gold-set format; drill files are checked by a schema lint in CI.
5. The Sprint 2 blockers and majors that agents own are fixed first, the DR-01/DR-02 decisions are made, and no blocker or major is open at the close (human-gated items as agreed with the PO, sprint-03 §0.4).

## 2. Scorecard

| ID | What is measured | Target | Method (detail in §4) | Actual | Met | Evidence |
|---|---|---|---|---|---|---|
| G03-01 | **Goal works end to end, live (API, real time).** Runs of the full journey over https through the web origin, each as a fresh account. Every step of a run must pass:<br>1. magic-link sign-in; a doubles match; the 60 s fixture uploaded; "Video received";<br>2. the coach's worked example (14 rallies) tagged; after **each** tag the stats equal the reference for the rallies so far;<br>3. stats = reference for AN-01..AN-07 × 2 sides (k, n, value, Wilson bounds ±0.001, low-sample flag, by-player counts, run histogram, ending mix); `rules_version`, `metric_def_version` and the label "unofficial scoring (rules not yet verified)" present;<br>4. "Show me" for every metric and side with n > 0: ≤ 10 items, total = n, every item behind the metric; the first item's rally video answers Range with 206;<br>5. rally 3 corrected → stats equal the corrected reference;<br>6. a second account → 404 on stats and evidence;<br>7. DELETE the match → 404 on the match and its stats, gone from the list;<br>8. DELETE the account → the old session 401; signing in again with the same address gives an empty account | **5 of 5 runs pass (100%)** | `scripts/measure/live_stats.py --runs 5` | VR3: 5 of 5 runs passed (100%); every step of every run ok; `delete_account` per run `{status 202, old_session 401, items_after_sign_in []}` | yes | VR3, head `fb920bc`, stack `racket-goal03` (https://localhost:43000, fresh volumes and bucket): `live_stats.py --runs 5 … --purge-cmd "$DC exec -T purge python -m racket.platform.purge --once" --json reports/goal03/live-stats.json` → **rc=0 in 23 s**, `runs_passed 5`; failing-keys `jq` prints nothing; run keys `setup, tag_to_stats, stats, evidence, correction, other_account, delete_match, delete_account` all `ok true`; `stats` `diffs []`, `evidence` `problems []` |
| G03-02 | **Real-time behaviour of the goal steps, live:** (a) tag → stats current, every tag of the 5 G03-01 runs (70 samples); (b) correction → stats current (5 samples, one per run); (c) DELETE match → hidden from the owner (match 404 and not listed), 5 samples | **(a) p95 ≤ 5,000 ms, n ≥ 70 (NFR-017 analogue); (b) p95 ≤ 5,000 ms, n ≥ 5; (c) p95 ≤ 60,000 ms, n ≥ 5 (NFR-066 a, ADR 0006)** | `live_stats.py` summary `tag_to_stats`, `correction_to_stats`, `delete_hidden` | VR3: (a) p95 34.3 ms, n = 70; (b) p95 24.0 ms, n = 5; (c) p95 22.2 ms, n = 5 | yes | VR3, head `fb920bc`: `jq .summary reports/goal03/live-stats.json` → `tag_to_stats` n 70, p50 18.9, p95 34.3, max 47.6, ok true; `correction_to_stats` n 5, p95 24.0, ok true; `delete_hidden` n 5, p95 22.2, ok true |
| G03-03 | **Purge leaves nothing, live (NFR-066 b):** after the 5 runs, the purge job is run once on the stack; (a) rows in any public table whose `match_id`, `owner_id` or `account_id` column, or `matches.id` / `accounts.id`, holds a deleted match or account id; (b) rally video links taken before deletion and still within their TTL, fetched after the purge; (c) the purge job is scheduled at least daily in Compose (NFR-066 c) | **(a) 0 rows; (b) every checked link 404 (object gone), ≥ 1 link checked; (c) schedule present, interval ≤ 24 h** | `live_stats.py --psql … --purge-cmd …` summary `purge`; `grep` of the scheduler config (§4) | VR3: (a) 0 rows in all 20 columns; (b) 5 links checked, all 404; (c) `purge` service running, `PURGE_INTERVAL_S: "86400"`, first scheduled pass at start ok | yes | VR3, head `fb920bc`: `live_stats.py` `.summary.purge` → `ok true`, every `rows` value 0 (`matches.id`, `accounts.id`, `match_rallies.match_id`, `metric_snapshots.match_id`, `label_sessions.owner_id`, … 20 keys), `media [404,404,404,404,404]`, `problems []` (purge run with `exec -T purge`); `$DC config \| grep -nE 'PURGE_(INTERVAL\|SCHEDULE)'` → `351: PURGE_INTERVAL_S: "86400"`, rc=0; `$DC logs purge` → `purge.schedule.started interval_s 86400`, `purge.run run 1 status ok exit_code 0 next_run_in_s 86400` |
| G03-04 | **Integration-test pass rate** against real Postgres, the object store and Mailpit: (a) every Sprint 3 IT id IT-03-01..IT-03-14 plus the BOLA matrix with its inventory diff (NFR-051); (b) every Sprint 1 and Sprint 2 IT id (IT-01-01..13 except 11, IT-02-01..12 except 07), the upload-resume regression and the strict sandbox (no regression) | **(a) 100% passed, 0 failed, 0 skipped, every required id present; (b) 100% passed, every id present** | `pytest --junitxml`, `scripts/measure/junit_rate.py` | VR3: (a) IT-03 + BOLA 183/183 (100%), 0 failed, 0 skipped, missing none; (b) earlier 317/317 (100%), missing none; strict sandbox 10/10 | yes | VR3, head `fb920bc`, fresh dev Postgres + fresh dev object store (`RA_DEV_STATE=.local/goal03`) + goal03 Mailpit: backend IT `691 passed, 2 skipped in 390.84s`, rc=0 (the 2 skips are the strict-sandbox file's Compose-only cases, run separately); sandbox on `racket-goal03` → `10 passed`, rc=0; `junit_rate.py` IT-03 → rc=0 `selected 183, passed 183, failed 0, skipped 0, missing []`; earlier → rc=0 `selected 317, passed 317, missing []` |
| G03-05 | **API read latency and availability, live:** open loop at 50 RPS for 60 s on GET stats, GET evidence (AN-01, side A) and GET match, for a match tagged with the worked example (NFR-010 "dashboard", NFR-041) | **p95 ≤ 300 ms, p99 ≤ 800 ms, availability ≥ 99.5%, 0 unexpected 4xx, achieved rate ≥ 47.5 RPS** | `scripts/measure/stats_latency.py --rps 50 --duration 60` | VR3: p95 32.5 ms, p99 114.9 ms, availability 100% (3,000 requests), 0 unexpected, 50.01 RPS | yes | VR3, head `fb920bc`: `stats_latency.py --api http://127.0.0.1:48000 --seed-api https://localhost:43000/api … --rps 50 --duration 60 --json reports/goal03/stats-latency.json` → rc=0, `ok true`, `p50_ms 14.0`, `p95_ms 32.5`, `p99_ms 114.9`, `max_ms 345.4`, `availability 1.0`, `status_unexpected 0`, `achieved_rps 50.008`. Precondition note: still no SRE dry-run row in §6 (rule 5; VR2-S3-05 open in part) |
| G03-06 | **E2E pass rate,** Playwright in Chrome for Testing (ADR 0036) over https against the Compose stack, every spec, including:<br>- E2E-03-01 journey v2 (tag → stats = reference → Show me plays → delete match → gone);<br>- E2E-03-02 evidence crawl;<br>- E2E-03-03 definition shown, draft hidden, low-sample text;<br>- E2E-03-04 delete account;<br>- E2E-03-05 Full Tag (labeller tags and exports; player refused);<br>- E2E-03-06 keyboard-only and 320/360 px on stats and evidence;<br>- E2E-03-07 S-01 move offered only on the latest kept rally (C3-03);<br>- E2E-03-08 D-01 and E-01 empty, loading and error states with axe and 24x24 (ST-048; PD-R1S3-03);<br>- every Sprint 1 and Sprint 2 spec, root specs included (no regression) | **100% of non-skipped tests passed, 0 failed, every E2E-03 id present and not skipped; earlier skips ≤ 6, each naming its API binding; 0 flaky over 3 repeats of every spec (NFR-074)** | `playwright test` (junit, json), `junit_rate.py`, `--repeat-each=3`, `flaky_report.py` | VR3: 120 selected: 114 passed, 0 failed, 6 skipped (100% of non-skipped); missing none; 6 skip reasons, all Sprint 1, each naming its API binding; **0 flaky** over ×3 | yes | VR3, head `fb920bc`, Chrome for Testing 141.0.7390.54, `E2E_ADMIN_CMD` on `racket-goal03`: `playwright test --workers=1` → rc=0 in 533 s; `junit_rate.py … --allow-skips` → rc=0 (`selected 120, passed 114, failed 0, skipped 6, rate 1.0, missing []`); `--repeat-each=3` → rc=0, `342 passed, 18 skipped` (26.2 m); `flaky_report.py --fail-on-flaky` → "2 runs, 120 tests, 0 flaky", rc=0. WebKit is not in this count (CI only; no CI run at the head, see G03-09 c) |
| G03-07 | **Browser timings, live** (`web/e2e/sprint-03/timing.spec.ts`, ST-054; 20 samples each): (a) stats dashboard interactive, warm; (b) "Show me" rally → first video frame playing, 9/1.5 Mbit/s and 4× CPU (reference profile); (c) cumulative layout shift while the stats load (CLS × 1000) | **(a) p95 ≤ 2,000 ms (NFR-011); (b) p95 ≤ 1,500 ms (NFR-014); (c) p95 = 0 (NFR-039); each ≥ 20 samples** | `scripts/measure/pw_timings.py` on the timing JSON report | VR3: (a) p95 231 ms, n = 20; (b) p95 837 ms, n = 20; (c) CLS × 1000 p95 = 0, n = 20 | yes | VR3, head `fb920bc`: `playwright test e2e/sprint-03/timing.spec.ts --repeat-each=20` → rc=0, `40 passed (2.8m)`; `pw_timings.py … --min-n 20` → rc=0, `ok true`: dashboard-interactive n 20, p50 180.3, p95 231.2; show-me-first-frame n 20, p50 731.5, p95 837.4, max 933.6; layout-shift n 20, p95 0.0, max 0.0; `unchecked []` |
| G03-08 | **Metric correctness:**<br>(a) golden matches GS-AN-1, **v2** since `7a6ffe5` (AN-07 rule 0.3 per share, AN-06 `longest_by_game`; TCR row "GS-AN-1 v2"; v1 at planning; wording amended by the engineering-manager at the close, 2026-10-08, PE-R2S3-04-FOLLOWUP; VR3 measured v2) (3 matches × every coach-reviewed metric × 2 sides) equal the coach's hand counts exactly (NFR-004), and the manifest check passes (FR-151, NFR-078);<br>(b) FR-101 examples and ADR 0005 thresholds (8/4, 20/10, 40/22, one game) as executable scenarios;<br>(c) FR-109 attribution conservation, property suite at ≥ 1,000 generated matches;<br>(d) metric dictionary: draft entries absent, a definition change bumps the version (FR-102);<br>(e) the coach's review record lists every shown entry as `coach-reviewed` with its QD-AN-03 evidence | **(a) 100% exact, 0 mismatches, manifest rc=0; (b) 100% passed; (c) 0 violations, ≥ 1,000 examples; (d) 100% passed; (e) every entry the API shows is `coach-reviewed` or `verified` in metric-dictionary §3** | `pytest -m golden_an`, `-m "analytics and scenario"`, `-m conservation`, `racket-manifest-check`, a `grep` | VR3: (a) 31/31, 0 mismatches, manifest rc 0; (b) 15/15; (c) 1,000 examples, 0 failing; scenario 1/1; (d) draft-hidden and definition-shown passed; (e) 7 metrics returned live, 7 dated `coach-reviewed` rows | yes | VR3, head `fb920bc`, fresh dev Postgres: `pytest -m golden_an` → `31 passed`, rc=0; `-m "analytics and scenario"` → `15 passed`, rc=0; `-m conservation` → `1 passed`; property → `1000 passing, 0 failing, and 64 invalid`, `max_examples=1000`; `racket-manifest-check tests/regression/golden_matches` → `OK … GS-AN-1 v2, 6 files`, rc=0; `junit_rate.py` golden rc=0 (31/31), analytics rc=0 (15/15, missing []), conservation rc=0 (2/2); (e) grep → 7; live: 7 metrics in the stats response (demo walk §9.5). **Provisional line:** 15 of the 21 frozen-value comparisons are AN-01/02/03/05/06 (3 matches × 5, `@needs-verification`), counted from `golden-an.xml` |
| G03-09 | **Full Tag and drill lint:** (a) IT-03-11 and E2E-03-05 (labeller only; consent required; export validates against `gold-label-schema` v1 with the tagged frame and player); (b) drill lint: the valid fixture library passes and each of the 5 FR-140 negative fixtures fails naming the drill and its reason; (c) the lint runs as a CI job on the PR | **(a) passed; (b) 1 pass + 5 named failures, 0 wrong verdicts; (c) the CI job exists and was green on the last run at the head** | `junit_rate.py` on the G03-04/G03-06 reports; `racket-drill-lint` (name per ST-053) on the fixtures; `actions_list` | VR3: (a) IT-03-11 15/15 and E2E-03-05 1/1 passed; (b) 1 pass + 5 named failures, 0 wrong verdicts; (c) the `drill-lint` job exists in `ci.yml`, but **no CI run at the head** (origin `sprint-03` is `723bb7f`, 7 commits behind; latest ci.yml run 37643676432 at `09f1f67`, failure) | no | VR3, head `fb920bc`: `junit_rate.py --include test_it_03_11_` → rc=0 (15/15); `--include E2E-03-05` → rc=0 (1/1); `racket-drill-lint ../content/drills` → `ok, 0 problem(s), metric dictionary v0.1`, rc=0; 5 files in `backend/tests/fixtures/drills-invalid/` → rc=1 each (`criterion no number`, `duration over 45`, `no source`, `progression cycle`, `unknown metric: AN-99`, each naming its drill id); `grep -n drill-lint .github/workflows/ci.yml` → job at line 155, needed by `ci-gate` (line 590); `git fetch origin sprint-03` → `723bb7f`, `git rev-list --count FETCH_HEAD..HEAD` → 7; `actions_list list_workflow_runs ci.yml branch sprint-03` → 4 runs, latest 37643676432 at `09f1f67` (conclusion failure); none at `fb920bc`. Cannot run in this sandbox: a CI run needs the push and a dispatch on GitHub |
| G03-10 | **Accessibility of the Sprint 3 screens** (stats dashboard D, evidence E, deletion X, Full Tag L) and every earlier family: (a) axe serious/critical (WCAG 2.2 AA tags) on every page an E2E test checks; (b) targets below 24×24 CSS px; (c) keyboard-only stats, evidence and Full Tag (E2E-03-05, E2E-03-06); (d) stats at 320 and 360 px with no sideways scrolling (NFR-034) | **(a) 0, with ≥ 1 axe check per family D, E, X, L and per earlier family; (b) 0, with ≥ 1 target check per family D, E, X, L and on the D-01/E-01 empty, loading and error states (E2E-03-08; PD-R1S3-03); (c) passed; (d) passed** | From the G03-06 Playwright JSON report | VR3: (a) 0 serious/critical over 55 axe attachments, families D, E, X, L and every earlier family present; (b) 0 below 24×24, D, E, X, L and D-01/E-01 empty, loading, error all present; (c) E2E-03-05 and E2E-03-06 keyboard passed; (d) stats and evidence at 320/360 passed | yes | VR3, head `fb920bc`, from `reports/goal03/e2e.json`: axe attachments 55, `axe serious/critical` errors 0; axe names include `D-01`, `D-01-definitions/-empty/-loading/-error`, `E-01`, `E-01-empty/-error/-loading/-keyboard`, `E-02-empty`, `X-01`, `X-02`, `L-01` and A, F, G, H, K, M, Q, S, T, U, V families; `targets below 24x24` errors 0; `targets-` names include `D-01`, `D-01-320/360`, `D-01-empty/-loading/-error`, `D-01-not-found-320/360`, `E-01-320/360`, `E-01-empty/-error/-loading`, `E-02-empty`, `X-01`, `X-02`, `L-01`; E2E-03-05, E2E-03-06 keyboard, 320 px, 360 px and not-found 320/360 among the passed (`e2e.xml`, 0 failures). Manual screen-reader pass (NFR-027 b) is not part of this row (§4 G03-10, S3-DoD-P6) |
| G03-11 | **Test strength, coverage and speed:** (a) backend changed lines against the Sprint 2 head `ce91984`; analytics line coverage; rules and aggregates; web unit; (b) mutation score on `sports/pickleball/rules` (gate) and on the starter-stats module (first gate); (c) differential oracle; (d) fast tests: domain suite (CI's `DOMAIN_TEST_PATHS`, which must include `tests/unit/analytics`), backend unit, integration | **(a) changed lines ≥ 85%; analytics ≥ 90% line (NFR-071); rules and aggregates ≥ 95% line / ≥ 90% branch; web ≥ 80% line; (b) rules ≥ 0.85; starter stats ≥ 0.80; (c) 100,000 sequences, 0 disagreements; (d) domain < 10 s, unit ≤ 60 s, integration < 10 min, all 0 failed (NFR-073)** | `pytest --cov`, `diff-cover`, `coverage report`, `vitest --coverage`, `mutation_score.py`, `tests.oracle.differential`, `run_with_budget.py` | VR3: (a) changed lines 94% (1,758 lines, 91 missing); analytics 98.1% line (461/470); rules + aggregates 99.57% line / 98.41% branch; web 91.64% lines; (b) rules 0.8635 (386/447), starter stats 0.9251 (309/334); (c) 100,000 sequences, 0 disagreements; (d) domain 8.0 s, unit 12.2 s, integration 350.1 s, all 0 failed | yes | VR3, head `fb920bc`, fresh dev Postgres + object store: coverage run → `2664 passed, 1 skipped, 22 deselected in 664.56s`, rc=0; `diff-cover==10.6.0 … --compare-branch=ce91984 --fail-under=85` → `Coverage: 94%`, rc=0; analytics `coverage report --fail-under=90` rc=0 (`coverage-backend.json`: 461/470 lines, 100/104 branches); rules `coverage json` → lines 918/922, branches 309/314; vitest `68 files, 580 passed`, `Lines 91.64% (6677/7286)`; oracle rc=0 `{sequences: 100000, disagreements: 0}`; `mutation_score.py` rules rc=0 `status measured, score 0.8635`; starter stats rc=0 `score 0.9251`; `DOMAIN_TEST_PATHS` includes `tests/unit/analytics`; budgets: 10 → `1199 passed, 1 skipped in 6.99s`, `finished in 8.0s`, rc=0; 60 → `1833 passed … 10.89s`, `12.2s`, rc=0; 600 → `592 passed, 2 skipped in 346.16s`, `350.1s`, rc=0 |
| G03-12 | **Open defects:** blocker or major findings whose latest disposition is open in `docs/sprints/03/review-rounds.md` (which starts with the 14 carried Sprint 2 rows), plus open product-defect rows in `smoke.md` and `blockers.md` not yet in review-rounds, plus open GitHub issues labelled `bug` with `blocker` or `major` | **0** | `scripts/measure/open_defects.py`, GitHub issue search (§4) | VR3: 3 open blockers (PE-R1S3-01/QA-R1S3-04, PD-R1S3-01, PD-R1-06/DR-01/DR-02 group); GitHub 0 | no | VR3, head `fb920bc`: `open_defects.py --json reports/goal03/open-defects.json docs/sprints/03/review-rounds.md` → rc=1, `open 3` (lines 413, 414, 415/272); `search_issues` `is:open label:bug` in nhuthuynh/racket-analytics → `total_count 0`; smoke.md/blockers.md: no open product-defect row outside review-rounds. All three need roles other than the verifier (PR merge by the orchestrator/reviewers/PO; BA and PM decider cells; the FE screen walk with the chair) |

**Overall:** the Sprint 3 goal is met only when all 12 rows are "yes". A row whose method could not run is "no", never "n/a" (fail closed, ADR 0014). `@needs-verification` results never count toward a Must FR (QD-QG-P5): metrics that read the provisional score sequence (AN-01, AN-02, AN-03, AN-05, AN-06) are reported on their own line in G03-08. Human-gated rows (sprint-03 §0.4) stay in G03-12 unless the PO chose option (b) in writing before the verifier runs.

**Status note (engineering-manager, review round 1, 2026-10-07; not a verifier result):** the goal is **not met**. The stats, evidence, delete-match and delete-account routes are not served at `15a7551` (openapi: no `/stats` or `/evidence` path; `/matches/{match_id}` and `/me` have only `get`), and `api-sprint-03.md` and `flows-sprint-03.md` do not exist. The pre-review smoke at `316a514` gives `live_stats.py` rc 1, runs passed 0/1 (QA-R1S3-06). G03-12 at this step: `open_defects.py` rc=1, open 9. Under PO P12 (b), C-06, SEC-RV3-01 and BLK-GOLD-01 are sprint-DoD rows (sprint-03 §9.1), not G03-12 rows.

**Verification round 1 (2026-10-07, head `fdeeb53`; §7): met 0 / 12.** Goal not met.

**Verification round 2 (2026-10-07, head `593f7ff`; §8): met 2 / 12** (G03-02, G03-05). Goal not met. VR2's values are in §8.3.

**Verification round 3 (2026-10-08, head `fb920bc`; §9): met 10 / 12.** Goal not met: G03-09 (no CI run at the head) and G03-12 (3 open blockers). The table above holds the VR3 values.

## 3. Rules for the verifier

1. **Live stack, isolated (ADR 0030, ADR 0033).**
   - Run everything at one recorded head (`git rev-parse HEAD`), on a fresh-volume Compose project of your own, with an `RA_DEV_STATE` of your own and remapped host ports (§4.0).
   - `bash scripts/disk-precheck.sh` first (≥ 10 GB free). The live scripts refuse below the floor (rc=2); that is a "no", not a skip.
   - Hold `flock .local/evidence-e2e.lock` for Compose up/down and every Playwright evidence run; pass `--output "$GOAL/…"` to Playwright.
   - Tear down with `down -v --rmi local` at the end. Never reuse or remove another agent's stack, database or images.
2. **Fail closed.** A skipped test counts as not passed, except where a row allows named skips. If no test was selected, or a required id is missing, the row is "no" (`junit_rate.py` exits 1).
3. **No edits to make a row pass.** A test change needs a `test-change-requests.md` row decided by QA. A product defect goes to its owner as an Open row in `review-rounds.md` (working-agreement §7 step 2).
4. **Evidence** is the exact command, the head SHA and the result line. Reports go under `reports/goal03/` (git-ignored); quote the numbers in the table.
5. **Dry-run first (ADR 0033 rule 2).** Before the verifier runs, each method author has run their method end to end on an isolated stack and written the rc in `decision-log.md`. A method with no dry-run row goes back to its author.
6. **Reconciliation first (ADR 0037 rule 1).** The verifier starts only after the EM's reconciliation row for the latest review round exists in `review-rounds.md`.

## 4. Methods (exact commands)

### 4.0 Stack under test (shared by G03-01..G03-03, G03-05..G03-07, G03-10)

```bash
cd /home/user/racket-analytics
git rev-parse HEAD; bash scripts/disk-precheck.sh; echo rc=$?    # rc must be 0 (>= 10 GB free)
bash scripts/dev-chrome.sh; /opt/google/chrome/chrome --version  # C3-04 (ADR 0036); missing script or binary -> G03-06/07/10 "no"
export RA_DEV_STATE=$PWD/.local/goal03 GOAL=$PWD/reports/goal03; mkdir -p "$RA_DEV_STATE" "$GOAL"
cp infra/env.example "$RA_DEV_STATE/goal.env"
sed -i 's#^DOCKERHUB_REGISTRY=.*#DOCKERHUB_REGISTRY=mirror.gcr.io#' "$RA_DEV_STATE/goal.env"
cat >> "$RA_DEV_STATE/goal.env" <<'EOF'
AUTH_LINK_LIMIT_PER_IP=1000
AUTH_EXCHANGE_LIMIT_PER_IP=1000
WEB_HOST_PORT=43000
API_HOST_PORT=48000
MAILPIT_UI_HOST_PORT=48025
MAILPIT_SMTP_HOST_PORT=41025
POSTGRES_HOST_PORT=45432
S3_HOST_PORT=48333
TRACING_UI_HOST_PORT=46686
EOF
sed -i 's#https://localhost:3000#https://localhost:43000#g' "$RA_DEV_STATE/goal.env"     # PUBLIC_WEB_ORIGIN / ALLOWED_ORIGINS (C-18)
DC="docker compose -p racket-goal03 -f infra/compose.yaml --env-file $RA_DEV_STATE/goal.env"
flock .local/evidence-e2e.lock $DC up -d --build --wait; echo rc=$?          # all services healthy
$DC cp web-tls:/data/caddy/pki/authorities/local/root.crt "$RA_DEV_STATE/root.crt"
curl -sS -o /dev/null -w '%{http_code}\n' http://localhost:43000/                                       # 400
curl --cacert "$RA_DEV_STATE/root.crt" -sS -o /dev/null -w '%{http_code}\n' https://localhost:43000/   # 200
export WEB=https://localhost:43000 API=https://localhost:43000/api MAILPIT=http://127.0.0.1:48025
# ... all methods ...
flock .local/evidence-e2e.lock $DC down -v --rmi local --remove-orphans     # self-cleaning (ADR 0033 rule 3)
```

Start `dockerd` first if `docker info` fails; images come through `mirror.gcr.io`. Record `df -h /` before and after. **Coach-reviewed entries:** the stats response shows only `coach-reviewed` entries (FR-102). If the stack's dictionary has fewer than 7 such entries, `live_stats.py` reports the missing metrics as differences, and G03-01 is "no" until COACH-1 is done; that is the intended fail-closed behaviour, not a method defect.

### G03-01, G03-02 and G03-03: live stats journey, real time, purge

```bash
python3 scripts/measure/live_stats.py --api "$API" --origin "$WEB" --mailpit "$MAILPIT" \
  --cacert "$RA_DEV_STATE/root.crt" --file fixtures/clips/synthetic-60s/clip.mp4 --runs 5 \
  --psql "$DC exec -T postgres psql -U racket -d racket -At -F|" \
  --purge-cmd "$DC exec -T purge python -m racket.platform.purge --once" \
  --json "$GOAL/live-stats.json"; echo rc=$?
jq '.summary | {runs, runs_passed, tag_to_stats, correction_to_stats, delete_hidden, purge}' "$GOAL/live-stats.json"
jq -r '.runs[] | to_entries[] | select(.value.ok != true) | .key' "$GOAL/live-stats.json"   # must print nothing
$DC config | grep -nE 'PURGE_(INTERVAL|SCHEDULE)'                                           # G03-03 (c)
```

- **G03-01 actual:** `runs_passed`/`runs`; met only with rc=0 and 5/5. A failing step is the key printed by the second `jq`; its `diffs`/`problems` say why.
- **G03-02 actual:** `tag_to_stats.p95_ms` and `n`; `correction_to_stats.p95_ms`; `delete_hidden.p95_ms`.
- **G03-03 actual:** `purge.rows` (every value 0), `purge.media` (every checked entry 404), `purge.problems` empty; the schedule line. The purge CLI name and the schedule variable are assumptions in `statscontract.PURGE_ONCE` until PE-3 names them; the method author updates this block and `statscontract.py` together, with a decision-log row, before the dry-run.
- AN-01, AN-02, AN-03, AN-05 and AN-06 values read the provisional score sequence (`@needs-verification`); they are reported on the G03-08 provisional line, not as verified truth.

### G03-04: integration-test pass rate

```bash
eval "$(bash scripts/dev-postgres.sh start)"; eval "$(bash scripts/dev-postgres.sh url)"
eval "$(bash scripts/dev-objectstore.sh start)"; eval "$(bash scripts/dev-objectstore.sh env)"
export MAILPIT_API_URL=$MAILPIT SMTP_HOST=127.0.0.1 SMTP_PORT=41025 MAIL_SMTP_URL=smtp://127.0.0.1:41025
(cd backend && env -u APP_ENV uv run pytest -q -p no:cacheprovider -rfEs \
   tests/integration tests/regression tests/unit/sports/pickleball/test_rules_static.py \
   --ignore=tests/integration/test_it_00_10_worker_sandbox_strict.py \
   --junitxml="$GOAL/backend-it.xml"); echo rc=$?
(cd backend && COMPOSE_PROJECT_NAME=racket-goal03 COMPOSE_ENV_FILES="$RA_DEV_STATE/goal.env" env -u APP_ENV \
   uv run pytest -q -rs tests/integration/test_it_00_10_worker_sandbox_strict.py --junitxml="$GOAL/sandbox.xml"); echo rc=$?
python3 scripts/measure/junit_rate.py --include 'test_it_03_|test_bola_matrix' \
  $(for i in 01 02 03 04 05 06 07 08 09 10 11 12 13 14; do printf -- '--require test_it_03_%s_ ' $i; done) \
  --require test_bola_matrix --json "$GOAL/it03-rate.json" "$GOAL/backend-it.xml"; echo rc=$?
python3 scripts/measure/junit_rate.py --include 'test_it_0[12]_|test_rules_static|test_upload_resume|worker_sandbox_strict' \
  $(for i in 01 02 03 04 05 06 07 08 09 10 12 13; do printf -- '--require test_it_01_%s_ ' $i; done) \
  $(for i in 01 02 03 04 05 06 08 09 10 11 12; do printf -- '--require test_it_02_%s_ ' $i; done) \
  --require test_upload_resume --require worker_sandbox_strict \
  --json "$GOAL/it-earlier-rate.json" "$GOAL/backend-it.xml" "$GOAL/sandbox.xml"; echo rc=$?
```

- IT ids are in sprint-03 §6; files are named `test_it_03_<nn>_*.py`. IT-03-09 replaces IT-02-07 (ST-038 is now committed).
- **Actual:** `rate`, `selected`, `failed`, `skipped`, `missing` from both JSON files. Met only when all four commands give rc=0.

### G03-05: read latency at 50 RPS

```bash
python3 scripts/measure/stats_latency.py --api http://127.0.0.1:48000 --seed-api "$API" --origin "$WEB" \
  --cacert "$RA_DEV_STATE/root.crt" --mailpit "$MAILPIT" \
  --rps 50 --duration 60 --json "$GOAL/stats-latency.json"; echo rc=$?
```

- Server-side latency as NFR-010 defines it (the API's published port); seeding through the https origin (SRE-S2-02). The run exits 1 before any load if the seeded stats never equal the reference (so the load measures real stats, not an empty or 404 body).
- **Actual:** `p95_ms`, `p99_ms`, `availability`, `status_unexpected`, `achieved_rps`.

### G03-06: E2E pass rate (and G03-10)

```bash
# labeller-admin CLI for E2E-03-05 (QA proposal; ST-052 names it). Absolute compose path: Playwright runs it from web/
export E2E_ADMIN_CMD="docker compose -p racket-goal03 -f $PWD/infra/compose.yaml --env-file $RA_DEV_STATE/goal.env exec -T api python -m racket.dataset.admin"
cd web
flock ../.local/evidence-e2e.lock env PW_CHROMIUM_CHANNEL=chrome MAILPIT_API_URL=$MAILPIT PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers \
  BASE_URL=$WEB PW_PROJECTS=chromium \
  PLAYWRIGHT_JUNIT_OUTPUT_NAME="$GOAL/e2e.xml" PLAYWRIGHT_JSON_OUTPUT_NAME="$GOAL/e2e.json" \
  pnpm exec playwright test --workers=1 --output "$GOAL/pw-out" --reporter=line,junit,json; echo rc=$?
cd ..
python3 scripts/measure/junit_rate.py --include '.' --allow-skips \
  $(for i in 01 02 03 04 05 06 07 08; do printf -- '--require E2E-03-%s ' $i; done) \
  $(for i in 01 02 03 04 05 06; do printf -- '--require E2E-02-%s ' $i; done) \
  --require 'E2E-01-02' --require 'E2E-01-03' --require 'walking-skeleton|walking skeleton' \
  --json "$GOAL/e2e-rate.json" "$GOAL/e2e.xml"; echo rc=$?
jq -r '[.. | objects | select(has("annotations")) | .annotations[]? | select(.type=="skip") | .description] | unique | .[]' "$GOAL/e2e.json"   # each reason once (the report repeats a test's annotations per result)
(cd web && flock ../.local/evidence-e2e.lock env PW_CHROMIUM_CHANNEL=chrome MAILPIT_API_URL=$MAILPIT PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers \
  BASE_URL=$WEB PW_PROJECTS=chromium PLAYWRIGHT_JUNIT_OUTPUT_NAME="$GOAL/e2e-repeat.xml" \
  pnpm exec playwright test --repeat-each=3 --workers=1 --output "$GOAL/pw-out-repeat" --reporter=line,junit)
python3 scripts/ci/flaky_report.py --fail-on-flaky --out "$GOAL/flaky.md" "$GOAL/e2e.xml" "$GOAL/e2e-repeat.xml"; echo rc=$?
```

- **Skips:** no E2E-03 or E2E-02 test may skip. Printed skip reasons (Sprint 1 specs only) must each name their API binding; at most 6.
- **Actual:** `passed`/`failed`/`skipped`/`rate` from `e2e-rate.json`, then the flaky count. WebKit runs only on CI; its failures count in G03-12.

### G03-07: browser timings

```bash
cd web
flock ../.local/evidence-e2e.lock env PW_CHROMIUM_CHANNEL=chrome MAILPIT_API_URL=$MAILPIT PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers \
  BASE_URL=$WEB PW_PROJECTS=chromium PLAYWRIGHT_JSON_OUTPUT_NAME="$GOAL/e2e-timing.json" \
  pnpm exec playwright test e2e/sprint-03/timing.spec.ts --repeat-each=20 --workers=1 \
  --output "$GOAL/pw-out-timing" --reporter=line,json; echo rc=$?
cd ..
python3 scripts/measure/pw_timings.py "$GOAL/e2e-timing.json" --min-n 20 \
  --target dashboard-interactive=2000 --target show-me-first-frame=1500 --target layout-shift=0 \
  --json "$GOAL/timings.json"; echo rc=$?
```

- `timing.spec.ts` (senior-qa-engineer, ST-054) attaches `timing-<metric>` bodies `{"ms": n}`; `layout-shift` carries the summed CLS × 1000 of a `PerformanceObserver({type: "layout-shift", buffered: true})` from navigation until the last metric card is rendered. `show-me-first-frame` uses the throttled reference profile (9/1.5 Mbit/s, 4× CPU).
- **Actual:** each metric's `p95_ms` and `n`. Met only with rc=0.

### G03-08: metric correctness

```bash
cd backend
eval "$(bash ../scripts/dev-postgres.sh url)"; eval "$(bash ../scripts/dev-objectstore.sh env)"   # the scenarios run the API on Postgres (QA-RV3-06)
env -u APP_ENV uv run pytest -q -rs -m "golden_an" --junitxml="$GOAL/golden-an.xml"; echo rc=$?
env -u APP_ENV uv run pytest -q -rs -m "analytics and scenario" --junitxml="$GOAL/analytics-scenarios.xml"; echo rc=$?
HYPOTHESIS_PROFILE=ci env -u APP_ENV uv run pytest -q -rs -m "conservation" --junitxml="$GOAL/conservation.xml"; echo rc=$?   # the FR-109 scenario
HYPOTHESIS_PROFILE=ci env -u APP_ENV uv run pytest -q -rs tests/unit/analytics/test_attribution.py -k property \
  --hypothesis-show-statistics --junitxml="$GOAL/conservation-property.xml" | tee "$GOAL/conservation-property.txt"; echo rc=$?
grep -E '[0-9]+ passing, 0 failing|max_examples=' "$GOAL/conservation-property.txt"            # (c): >= 1,000 passing, 0 failing
env -u APP_ENV uv run racket-manifest-check tests/regression/golden_matches; echo rc=$?   # the CLI takes the set directory
cd ..
python3 scripts/measure/junit_rate.py --include '.' --require 'GS-AN-1|golden_an' --json "$GOAL/golden-an-rate.json" "$GOAL/golden-an.xml"; echo rc=$?
python3 scripts/measure/junit_rate.py --include '.' --require 'Low-sample|low_sample|lowsample' --require 'Draft metric hidden|draft' \
  --require 'Definition shown|definition' --json "$GOAL/analytics-rate.json" "$GOAL/analytics-scenarios.xml"; echo rc=$?
python3 scripts/measure/junit_rate.py --include '.' --require 'conservation' --require 'property_every_lost_rally' --json "$GOAL/conservation-rate.json" "$GOAL/conservation.xml" "$GOAL/conservation-property.xml"; echo rc=$?
grep -nE '^\| 20[0-9]{2}-' docs/domain/metric-dictionary.md | grep 'coach-reviewed' | grep -vc 'planned'   # (e): one dated row per shown entry; the undated "(planned)" row does not count
```

- The `golden_an`, `analytics`, `scenario` and `conservation` markers are registered by QA in `backend/pyproject.toml` (QA-ACC-3, ST-049); the conservation property prints its example count, which must be ≥ 1,000 under `HYPOTHESIS_PROFILE=ci`.
- **(e):** compare the entries in the G03-01 stats response (`jq '.runs[0]' "$GOAL/live-stats.json"` shows which metrics were returned) with the review-record rows; every returned entry needs a `coach-reviewed` (or `verified`) row with QD-AN-03 evidence.
- **Provisional line:** report separately how many golden comparisons involve AN-01/02/03/05/06 (rule-dependent, `@needs-verification`).
- **Actual:** passed/selected of each report; manifest rc; the conservation example count; the review-record check.

### G03-09: Full Tag and drill lint

```bash
python3 scripts/measure/junit_rate.py --include 'test_it_03_11_' --require test_it_03_11_ --json "$GOAL/fulltag-it.json" "$GOAL/backend-it.xml"; echo rc=$?
python3 scripts/measure/junit_rate.py --include 'E2E-03-05' --require 'E2E-03-05' --json "$GOAL/fulltag-e2e.json" "$GOAL/e2e.xml"; echo rc=$?
(cd backend && env -u APP_ENV uv run racket-drill-lint ../content/drills); echo "valid rc=$?"            # 0
for f in backend/tests/fixtures/drills-invalid/*.json; do
  (cd backend && env -u APP_ENV uv run racket-drill-lint "../$f"); echo "$f rc=$?"                       # each 1, naming drill and reason
done
```

- **(c):** `mcp__github__actions_list` for `ci.yml` on `sprint-03` at the head: the `drill-lint` job (name per ST-053) exists and concluded `success`.
- The CLI name and the fixture folder are set by ST-053 (ML); the method author updates this block with a decision-log row before the dry-run.
- **Actual:** the two rates; the valid rc; each negative file's rc and first line; the CI job conclusion.

### G03-10: accessibility, from the G03-06 JSON report

```bash
jq '[.. | objects | select(has("attachments")) | .attachments[] | select(.name|startswith("axe-"))] | length' "$GOAL/e2e.json"
jq '[.. | objects | select(has("errors")) | .errors[]? | .message? // "" | select(test("axe serious/critical"))] | length' "$GOAL/e2e.json"   # 0
jq -r '[.. | objects | select(has("attachments")) | .attachments[] | select(.name|startswith("axe-")) | .name] | unique | .[]' "$GOAL/e2e.json"
jq '[.. | objects | select(has("errors")) | .errors[]? | .message? // "" | select(test("targets below 24x24"))] | length' "$GOAL/e2e.json"   # 0
jq -r '[.. | objects | select(has("attachments")) | .attachments[] | select(.name|startswith("targets-")) | .name] | unique | .[]' "$GOAL/e2e.json"   # (b): D-01, E-01, X-01, X-02, L-01 and the D-01/E-01 -empty/-loading/-error names present
```

- Screen families D (dashboard), E (evidence), X (deletion), L (Full Tag) with the screen ids of `flows-sprint-03.md` (PD-1). E2E-03-05, E2E-03-06 and the 320/360 px cases must be among the passed cases of `e2e-rate.json`.
- (b) counts only when every family D, E, X, L has a `targets-` attachment and the D-01/E-01 empty, loading and error states have theirs (E2E-03-08; PD-R1S3-03, decision-log 2026-10-07); a family without one is "no", not 0.
- The manual screen-reader pass (NFR-027 b, C3-06) is a human item. Under PO P12 option (b) it is **deferred** (ADR 0030 rule 1) to sprint-DoD row S3-DoD-P6 "not met: waiting on P6" and is **not counted in G03-12** (decision-log 2026-10-07; EM reconciliation in review round 2, review-rounds.md). It is not part of G03-10's pass either: G03-10 counts only the automated checks, and NFR-027 (b) stays not met for Sprint 3.

### G03-11: test strength, coverage and speed

```bash
(cd backend && env -u APP_ENV uv run pytest -q -m "(unit or integration or scenario or regression) and not nightly and not red_until" \
   --ignore=tests/integration/test_it_00_10_worker_sandbox.py --ignore=tests/integration/test_it_00_10_worker_sandbox_strict.py \
   --deselect tests/features/test_nightly_quality.py::test_nightly_run_completes \
   --deselect tests/features/test_phone_fixtures.py::test_coverage_of_the_set \
   --deselect tests/features/test_phone_fixtures.py::test_probe_every_fixture \
   --cov --cov-branch --cov-report=xml:"$GOAL/coverage-backend.xml" --cov-report=json:"$GOAL/coverage-backend.json"); echo rc=$?
uvx --from diff-cover==10.6.0 diff-cover "$GOAL/coverage-backend.xml" --compare-branch=ce91984 --fail-under=85 \
  --markdown-report "$GOAL/diff-cover.md"; echo rc=$?
(cd backend && uv run coverage report --data-file=.coverage --include='src/racket/analytics/*' --fail-under=90); echo rc=$?
(cd backend && uv run coverage report --data-file=.coverage \
  --include='src/racket/sports/pickleball/rules/*,src/racket/matches/match_state.py,src/racket/matches/participants.py,src/racket/matches/scorebook/domain/*')
(cd web && pnpm exec vitest run --coverage --coverage.reporter=text-summary)
cd backend
env -u APP_ENV uv run python -m tests.oracle.differential --sequences 100000 --json "$GOAL/oracle.json"; echo rc=$?
mv mutants "$GOAL/mutants-stale" 2>/dev/null || true
env -u APP_ENV uv run --with mutmut==3.8.0 python ../scripts/ci/mutation_score.py --project . \
  --target src/racket/sports/pickleball/rules --tests tests/unit/sports \
  --ignore tests/unit/sports/pickleball/test_rules_static.py --out "$GOAL/mutation-rules.json"; echo rc=$?
mv mutants "$GOAL/mutants-rules" 2>/dev/null || true
env -u APP_ENV uv run --with mutmut==3.8.0 python ../scripts/ci/mutation_score.py --project . \
  --target src/racket/analytics/starter_stats.py --tests tests/unit/analytics --out "$GOAL/mutation-stats.json"; echo rc=$?
mv mutants "$GOAL/mutants-stats" 2>/dev/null || true
DOMAIN=$(uv run --project ../infra python -c "import yaml;print(yaml.safe_load(open('../.github/workflows/ci.yml'))['env']['DOMAIN_TEST_PATHS'])")
echo "$DOMAIN" | grep -q 'tests/unit/analytics' || echo "DOMAIN_TEST_PATHS lacks tests/unit/analytics -> (d) no"
env -u APP_ENV uv run pytest -q --collect-only -m unit >/dev/null   # unbudgeted warm-up, as CI
python3 ../scripts/ci/run_with_budget.py 10 -- env -u APP_ENV uv run pytest -q -m unit $DOMAIN; echo rc=$?
python3 ../scripts/ci/run_with_budget.py 60 -- env -u APP_ENV uv run pytest -q -m unit; echo rc=$?
python3 ../scripts/ci/run_with_budget.py 600 -- env -u APP_ENV uv run pytest -q -m integration tests/integration \
  --ignore=tests/integration/test_it_00_10_worker_sandbox_strict.py; echo rc=$?     # with the G03-04 env
cd ..
```

- The three `--deselect` lines are the Sprint 1 tests red only on PO input (S-07 phone clips P3; S-08 nightly on `main`). Remove a line as soon as its test can pass (C3-05 merges the nightly). No other test may be deselected.
- The starter-stats module path follows ST-044's card (`analytics/starter_stats.py`); if ST-044 names it differently, the method author changes `--target` and the analytics `--include` with a decision-log row before the dry-run.
- The analytics mutation threshold (0.80) is a first gate (judgment, decision-log 2026-10-06); the rules threshold (0.85) is NFR-072.
- **Actual:** diff-cover %; analytics TOTAL line %; rules + aggregates line and branch %; web Lines %; oracle sequences/disagreements; both mutation scores; the three budget runs' wall times and result lines.

### G03-12: open defects

```bash
python3 scripts/measure/open_defects.py --json "$GOAL/open-defects.json" docs/sprints/03/review-rounds.md; echo rc=$?
```

- The file starts with the 14 carried Sprint 2 rows (planning, 2026-10-06; `open 14`). Reviewers append Open rows for new findings (ADR 0033 rule 1); the EM reconciles after every round (ADR 0037 rule 1).
- **GitHub:** `mcp__github__search_issues` with `repo:nhuthuynh/racket-analytics is:issue is:open label:bug`; count those labelled `blocker` or `major`.
- **Smoke and blockers:** add any open product-defect rows from `docs/sprints/03/smoke.md` and `blockers.md` not yet in `review-rounds.md`.
- **Actual:** the sum, with the ids in Evidence.

## 5. Traceability of targets

| Metric | Target source |
|---|---|
| G03-01 | FR-100..FR-103, FR-006, FR-007, FR-055, NFR-051; 5 runs as G01-01/G02-01 (judgment) |
| G03-02 | (a)(b) NFR-017's 5 s used as "tag → current results" analogue (judgment, decision-log 2026-10-06); (c) NFR-066 a, ADR 0006 (≤ 1 min) |
| G03-03 | NFR-066 b, c; FR-006, FR-007; ADR 0006 |
| G03-04 | sprint-03 §6; NFR-051; DoD story level "integration tests cover each touched boundary" |
| G03-05 | NFR-010 (p95 ≤ 300 ms, p99 ≤ 800 ms at 50 RPS, "dashboard"); NFR-041 availability as G02-04 |
| G03-06 | sprint-03 §6 E2E ids; NFR-074 (0 flaky) |
| G03-07 | NFR-011 (≤ 2.0 s warm), NFR-014 (≤ 1.5 s), NFR-039 (0 shift) |
| G03-08 | NFR-004 (100% exact), FR-101, FR-102, FR-109, FR-151, NFR-078 |
| G03-09 | FR-150, FR-140, FR-151 |
| G03-10 | NFR-027 a, NFR-028, NFR-034 |
| G03-11 | NFR-071, NFR-072 (+ judgment for analytics), NFR-002 b, NFR-073 |
| G03-12 | DoD; ADR 0030, ADR 0033, ADR 0037 |

## 6. Method dry-runs (ADR 0033 rule 2)

One row per method, written by its author after an end-to-end run on an isolated stack, before the verifier runs. The rc is also logged in `decision-log.md`.

| Method | Author | Head | rc | Date | Note |
|---|---|---|---|---|---|
| G03-01..G03-03 `live_stats.py` | senior-qa-engineer with principal-engineer | `fb69a7d` | 1 | 2026-10-07 | Dry-run 1 (pre-build), `--runs 1` on the isolated stack `racket-qa03` (port 53000 for 43000). Runs end to end and fails closed: failed steps `tag_to_stats`, `stats`, `evidence`, `correction`, `delete_match`, `delete_account` (routes not built: ST-046/047/050/051); purge rows left in 11 columns and "purge command rc=1" (no `racket.platform.purge`, ST-050). Method changed: purge runs in `api` (the purge job ships in the API image, `ecee023`; ADR 0038 Proposed), not `worker` (least-privilege role, ST-042). Re-run with `--runs 5` after PE-1/PE-3 |
| G03-04 IT rates | senior-qa-engineer | `fb69a7d` | 1 | 2026-10-07 | Dry-run 1, dev Postgres + dev object store + qa03 Mailpit: earlier ITs `317/317` passed, rc=0 (no regression); strict sandbox 10 passed; IT-03 `52/161`, rc=1, missing none; every failure is an IT-03 `red_until` row or one of the 3 `golden_an` hand-count rows (COACH-1). Method unchanged |
| G03-05 `stats_latency.py` | sre-devops-engineer | | | | |
| G03-06, G03-10 E2E | senior-qa-engineer | `9c64d79` | 1 | 2026-10-07 | Dry-run 1 on `racket-qa03` (https, Chrome for Testing 141): 115 selected, 97 passed, 12 failed, 6 skipped (Sprint 1, each naming its API binding), missing none; the 12 failures are exactly the red-first E2E-03-01..06 and timing specs (COACH-1, ST-047/048/051/052; QA-R1S3-01); every Sprint 1/2 spec and E2E-03-07 passed. G03-10: 40 axe attachments, 0 serious/critical, 2 targets-below-24 (QA-R1S3-01); no D/E/X/L attachment yet. Method changed: `E2E_ADMIN_CMD` exported (E2E-03-05), skip reasons printed once (`unique`) |
| G03-07 timings | senior-qa-engineer | `9c64d79` | 1 | 2026-10-07 | Dry-run 1: `--repeat-each=20`, every sample fails at COACH-1 / missing D-01, so `pw_timings.py` reports n = 0 for all three metrics, rc=1 (fails closed, no empty pass). Method unchanged |
| G03-08 correctness | senior-qa-engineer with pickleball-domain-coach | `fb69a7d` | 1 | 2026-10-07 | Dry-run 1: `golden_an` 28/31 (3 = hand count, COACH-1); `analytics and scenario` 0/15 (routes, ST-046); conservation scenario 1/1 and the property `1000 passing, 0 failing`; manifest rc=0; (e) 0 dated `coach-reviewed` rows. Method changed (3 defects): the 1,000-example property is in `tests/unit/analytics` and was not selected by `-m conservation`; `--require 'Low-sample'` matched no test id (`test_lowsample_flag`); the (e) grep counted the undated "(planned)" row |
| G03-09 Full Tag and lint | senior-ml-cv-engineer with senior-qa-engineer | `bac3d81` | 1 | 2026-10-07 | Dry-run 1 by the QA co-author (the ML author's own row still due): (b) `racket-drill-lint ../content/drills` → `ok, 0 problem(s)`, rc=0, and each of the 5 negative fixtures rc=1 naming its drill and FR-140 reason (met at this head); (a) IT-03-11 and E2E-03-05 red until ST-052; (c) `grep -i drill .github/workflows/ci.yml` → nothing: no lint job in CI yet (SRE/ML), so (c) is "no". Method unchanged |
| G03-11 strength, coverage, speed | senior-qa-engineer | `4fff02c` | 1 | 2026-10-07 | Dry-run 1, dev Postgres + object store: coverage run `2224 passed, 1 failed` (the BOLA inventory guard, QA's own regression QA-R1S3-03, fixed in `99a711f`); diff-cover vs `ce91984` 96% of 584 lines, rc=0; analytics 99.56% line / 98.57% branch; rules + aggregates 99.57% / 98.41%; web lines 91.84% (477 tests); oracle 100,000 sequences, 0 disagreements; mutation rules 0.8635 (386/447), starter stats 0.8698 (274/315); `DOMAIN_TEST_PATHS` includes `tests/unit/analytics`; domain 1110 passed in 8.5 s of 10; unit 1620 passed in 12.2 s of 60; integration 264 s of 600 but `50 failed, 50 errors`, all IT-03 `red_until` rows (the budget command does not exclude `red_until`, so (d) stays "no" until those stories land: intended). Note: the two `coverage report` lines must run before the mutation steps, which delete `backend/.coverage` (order as written) |
| G03-12 open defects | engineering-manager | `661f6c9` | 1 | 2026-10-07 | Dry-run 1 (late, after VR1; VR1-S3-03), whole method: `open_defects.py --json <scratch>/dry/open-defects.json docs/sprints/03/review-rounds.md` → rc=1, open 4 (PD-R1S3-01, PD-R1-06 group, PE-R1S3-01, QA-R1S3-06), JSON written; negative: the same script on `progress.md` → rc=2 (fails closed); `search_issues` `is:open label:bug` → 0; `smoke.md`, `blockers.md` → no Severity table (rc=2 each), `grep -i 'product.defect'` → none. Method unchanged |

## 7. Verification round 1 (2026-10-07; senior-qa-engineer with sre-devops-engineer, independent verifiers)

**Totals: 0 of 12 met.** The Sprint 3 goal is **not met** and was **not demonstrated** on the live stack. The cause is the same for most rows: the Sprint 3 stories ST-046, ST-047, ST-050, ST-051 and ST-052 are not built at the head. There is no stats, evidence, DELETE match, DELETE account or purge route, and no `racket.platform.purge` or `racket.dataset.admin` module. The platform underneath works: every Sprint 0-2 IT and E2E passed, with no regression.

### 7.1 Stack under test

- **Head:** `fdeeb53` (`git rev-parse HEAD`), branch `sprint-03`, clean tree.
- **Preflight:** `bash scripts/disk-precheck.sh` gave rc=0 with 13 GB free. `scripts/dev-chrome.sh` reports Chrome for Testing 141.0.7390.54.
- **Stack:** Compose project `racket-goal03`, built from this tree, fresh volumes (`ps -a` and `volume ls` were empty before the start). Ports were remapped as in §4.0, with `RA_DEV_STATE=.local/goal03`.
- **Start:** `flock .local/evidence-e2e.lock $DC up -d --build --wait` returned rc=0 in 1 m 53 s, and all 9 long-running services were healthy.
  - **Deviation from §4.0 (method defect, routed to sre-devops-engineer):** the first `up --build` failed with rc=1, `invalid peer certificate: UnknownIssuer` in `uv sync`. `infra/compose.yaml` has no way to pass the `extra_ca` build secret that `docs/process/ci-cd.md` requires behind the sandbox proxy.
  - **Workaround:** the verifier added a local, uncommitted override `.local/goal03/build-ca.override.yaml` (top-level `secrets.extra_ca.file: /root/.ccr/ca-bundle.crt` plus `build.secrets: [extra_ca]` on migrate, api, worker, mailer and web). `DC` therefore carries `-f .local/goal03/build-ca.override.yaml`.
- **Front door:** `http://localhost:43000/` returned 400. `https://localhost:43000/` with `--cacert root.crt` returned 200, and `/api/healthz` returned `{"status":"ok"}`. Alembic is at `0013`.
- **Routes:** the openapi at the head has 14 match paths. None is `/stats` or `/evidence`. `/matches/{match_id}` and `/me` serve `get` only.
- **G03-04, 08 and 11:** these ran on `scripts/dev-postgres.sh` and `scripts/dev-objectstore.sh`, with the goal03 Mailpit (`127.0.0.1:48025`, SMTP `41025`).
- **Teardown:** `flock … $DC down -v --rmi local --remove-orphans` returned rc=0, leaving 0 `racket-goal03` containers and 0 volumes. Dev Postgres and the object store were stopped.
- **Disk:** `df -h /` showed 14G free at the start, 9.4G before a prune, 14G after `docker builder prune -af` (4.933 GB reclaimed, ops/disk-and-prune.md step 2), 11G before teardown and 14G after.
- **Reports:** under `reports/goal03/` (git-ignored).

### 7.2 Preconditions (§3), checked before trusting the methods

| Rule | Status |
|---|---|
| 5 Dry-run first | **Not complete.** G03-05 (`stats_latency.py`, SRE) and G03-12 (`open_defects.py`, EM) have no dry-run row in §6. The ML author's own G03-09 row is still due. The verifier ran every method anyway and reports what it gave |
| 6 Reconciliation first | **Not complete.** The reconciliation-log table in `review-rounds.md` has only the Planning row. The EM's round-2 dispositions exist (`review-rounds.md` line 252), but there is no reconciliation row for round 1 or round 2 |

### 7.3 Summary

| ID | Target (short) | Actual | Met | Owner to fix |
|---|---|---|---|---|
| G03-01 | 5/5 live journeys | 0/5 (`stats` 404, `evidence` no items, DELETE match and `/me` 405) | no | senior-backend-engineer (ST-046, ST-047, ST-050, ST-051) |
| G03-02 | tag/correction → stats p95 ≤ 5 s; delete hidden p95 ≤ 60 s | n = 0 / 0 / 0 | no | senior-backend-engineer |
| G03-03 | purge leaves 0 rows, links 404, schedule ≤ 24 h | 14 columns with rows left, 0 links checked, no purge module, no schedule | no | senior-backend-engineer (ST-050) with sre-devops-engineer (Compose schedule) |
| G03-04 | IT-03 100%; earlier 100% | IT-03 64/177 (36.2%); earlier 317/317; sandbox 10/10 | no | senior-backend-engineer |
| G03-05 | p95 ≤ 300 ms at 50 RPS | not measured (stats never reachable, rc=1 before load) | no | senior-backend-engineer (route), then sre-devops-engineer (dry-run row) |
| G03-06 | 100% non-skipped, every E2E-03 id, 0 flaky | 97/113 non-skipped (16 failed, all Sprint 3), 6 named skips, 0 flaky | no | senior-frontend-engineer (D/E/X/L screens, ST-048), after the backend routes |
| G03-07 | dashboard ≤ 2 s, first frame ≤ 1.5 s, CLS 0 | n = 0 for all three | no | senior-frontend-engineer |
| G03-08 | golden 100%, scenarios 100%, conservation, review record | golden 31/31, manifest rc 0, conservation 1,000/0; **scenarios 0/15** | no | senior-backend-engineer |
| G03-09 | Full Tag IT and E2E; lint 1 + 5; CI job green at the head | lint 1 + 5 correct; IT-03-11 0/15; E2E-03-05 fails (no `racket.dataset.admin`); no CI run at the head | no | senior-ml-cv-engineer (ST-052) |
| G03-10 | axe 0 and targets 0 with D/E/X/L coverage; keyboard; 320/360 | axe 0 of 40 but no D/E/X/L page; 2 target failures (D-01 not-found 320/360, QA-R1S3-01) | no | senior-frontend-engineer |
| G03-11 | coverage, mutation, oracle, budgets | coverage met (96%, 99.15%, 99.57/98.41%, 91.84%), oracle 100,000/0; **mutation not scored** (both rc=1); integration budget 229 s but 63 failed, 50 errors | no | senior-qa-engineer (mutation harness, see 7.4); senior-backend-engineer (IT reds) |
| G03-12 | 0 open blocker/major | 4 open blockers; GitHub 0 | no | engineering-manager |

**Met: 0 / 12.**

### 7.4 New findings from this round (Open rows go to `review-rounds.md` through the EM's reconciliation)

| Id | Severity | Finding | Owner |
|---|---|---|---|
| VR1-S3-01 | major | **The mutation gate cannot score at the head** (NFR-072). `mutation_score.py` gives rc=1 with `status: not_checked` for both targets, because mutmut's clean test run inside `backend/mutants/` fails. `tests/unit/analytics/test_stats_contract_doc.py` (`38b5da4`) reads `docs/architecture/api-sprint-03.md`, and `tests/unit/sports/pickleball/test_metric_dictionary_status_sync.py` reads `docs/domain/metric-dictionary.md`, both through a path relative to the backend root that `mutants/` does not contain (`FileNotFoundError: …/backend/docs/…`). The CI nightly mutation job is affected the same way. Fix: `--ignore` these doc-sync tests in the mutation runs, or resolve the docs path from the repo root. Needs a TCR row if a test changes | senior-qa-engineer |
| VR1-S3-02 | minor | **`compose up --build` cannot build behind a TLS-intercepting proxy without a local override.** `infra/compose.yaml` passes no `extra_ca` build secret, so goal-scorecard §4.0 cannot run as written in this sandbox | sre-devops-engineer |
| VR1-S3-03 | minor | The §3 rule 5 and rule 6 preconditions were not met before verification: no G03-05 or G03-12 dry-run row, and no round-1 or round-2 reconciliation row (7.2) | engineering-manager |

### 7.5 Sprint demo script (sprint-03 §12), run in real time on `racket-goal03`

The walk ran on 2026-10-07 from 18:52:43 UTC. The API steps used the verifier's scratch script (`demo_walk.py`, built on `scripts/measure` helpers; log in `reports/goal03/demo-walk.txt`). The browser steps were the E2E run above.

| Step | What happened | Result |
|---|---|---|
| 1 Sign in, tagged worked-example match | Sign-in 0.65 s, match created, video `video_received` at 0.88 s, game started 201, the 14 worked-example rallies tagged at 201 each by 1.16 s, score sheet 200 | works |
| 2 Stats: 7 cards per side, n, ranges, low sample, notice | `GET /matches/{id}/stats` returned 404 `not_found`. E2E-03-03 failed and no stats page exists | **fails** |
| 3 "Show me" plays the rallies | `GET …/stats/AN-01/evidence?side=A` returned 404. E2E-03-02 failed | **fails** |
| 4 Correct rally 3; "Rallies won when receiving" 33% → 40% | The rally can be corrected (Sprint 2), but there are no stats to show the change. `live_stats` `correction` returned 404 | **fails** |
| 5 360 px stacked cards, AN-07 bar | No stats page. E2E-03-06 at 320/360 failed | **fails** |
| 6 Delete the match; purge log; empty inventory | `DELETE /matches/{id}` returned 405, and the match is still listed. Purge: `No module named racket.platform.purge` | **fails** |
| 7 Delete the account from a second session; first signed out | `DELETE /me` returned 405, and the first session's `GET /me` still returned 200 | **fails** |
| 8 Labeller Full Tag, export validates; player gets not found | `python -m racket.dataset.admin` gave `No module named racket.dataset.admin`. E2E-03-05 failed | **fails** |
| 9 Drill lint | Valid library `ok, 0 problem(s)` with rc 0. Each of the 5 negative files gave rc 1 and named its drill and reason | works |
| 10 Scorecard and test report | This section: 0/12 met; golden 31/31; conservation 1,000/0; mutation not scored; evidence crawl failed; open defects 4 | shown, goal not met |
| 11 PO questions | Not a verifier step | n/a |

**Verdict:** the demo cannot be given. Only steps 1 and 9 work end to end.

**Not runnable in this sandbox:** WebKit (CI only). Its result belongs to the CI E2E job, and the last run at `09f1f67` failed, which counts in G03-12. That is not in this round's totals.

## 8. Verification round 2 (2026-10-07; senior-qa-engineer with sre-devops-engineer, independent verifiers)

**Totals: 2 of 12 met** (G03-02, G03-05). The Sprint 3 goal is **not met**. Much more of it now works live than in round 1. Stats, evidence, the correction recompute, delete match, delete account and the purge all work on the live HTTPS stack. The demo walk shows the coach's worked-example numbers. What still blocks the goal:

- harness and test-side defects whose fixes wait on undecided TCR rows;
- two front-end defects (CLS 52; the not-found page answers 200), one flaky E2E and one timing sample that timed out;
- stale `red_until` markers that drop the IT-03 tests out of the coverage gate;
- no Compose purge schedule;
- no CI run at the head;
- 4 open blockers.

### 8.1 Stack under test

- **Head:** `593f7ff` (`git rev-parse HEAD`), branch `sprint-03`, clean tree.
- **Preflight:** `bash scripts/disk-precheck.sh` gave `ok, 13 GB free` (rc=0). `scripts/dev-chrome.sh` reports Chrome for Testing 141.0.7390.54.
- **Clean state:**
  - The VR1 reports were moved to `reports/goal03-vr1/`.
  - `.local/goal03` was deleted and rebuilt from `infra/env.example` as in §4.0.
  - Before the start there were 0 `racket-goal03` containers and 0 volumes, so the database volume and the object-store bucket are new.
- **Start:** `flock .local/evidence-e2e.lock $DC up -d --build --wait` returned rc=0 in 40 s from the build cache, and all 9 long-running services were healthy.
  - `DC` still carries `-f .local/goal03/build-ca.override.yaml`. VR1-S3-02 is still open: `infra/compose.yaml` has no `extra_ca` build secret.
  - The image was built from the head: `python -c "import racket.platform.purge, racket.dataset.admin"` in `api` printed `mods ok`.
- **Front door:** `http://localhost:43000/` returned 400. `https://localhost:43000/` with `--cacert root.crt` returned 200, and `/api/healthz` returned `{"status":"ok"}`. Alembic is at `0017`.
- **Openapi:** `/matches/{match_id}` serves `delete` and `get`, and `/me` serves `delete` and `get`. These paths now exist: `/matches/{match_id}/stats`, `/matches/{match_id}/stats/{metric_id}/evidence`, `/label/matches/{match_id}` (with `/events` and `/export`).
- **G03-04, 08 and 11:** these ran on `scripts/dev-postgres.sh` and `scripts/dev-objectstore.sh`, with the goal03 Mailpit.
- **Teardown:**
  - `flock … $DC down -v --rmi local --remove-orphans` returned rc=0, leaving 0 containers and 0 volumes.
  - Dev Postgres and the object store were stopped (rc 0 each).
  - The verifier's mutant copies under `reports/` were deleted.
- **Disk:** `df -h /` showed 14G free at the start, 7.8G before teardown, 9.7G after teardown and 11G after removing the mutant copies.
- **Reports:** under `reports/goal03/` (git-ignored).

### 8.2 Preconditions (§3)

| Rule | Status |
|---|---|
| 5 Dry-run first | **Still incomplete.** G03-05 (`stats_latency.py`, SRE) has no row in §6. The verifier ran it and reports the measurement. It met its target, and the row is counted as met because the method ran end to end as written. The missing row is a process finding (VR2-S3-05) |
| 6 Reconciliation first | Met. The EM's goal-round-1 reconciliation rows exist in `review-rounds.md` (VR1-S3-03 Fixed) |

### 8.3 Summary

| ID | Target (short) | Actual (VR2) | Met | Owner to fix |
|---|---|---|---|---|
| G03-01 | 5/5 live journeys | 0/5. Steps 1-7 pass 5/5. Step 8 fails in every run because the harness reuses the spent Mailpit link (BE-GR1-01). The product passed a manual check | no | senior-qa-engineer (BE-GR1-01, `live_stats.py`) |
| G03-02 | p95 ≤ 5 s / 5 s / 60 s | 18.2 ms (n 70) / 21.5 ms (n 5) / 41.8 ms (n 5) | **yes** | — |
| G03-03 | 0 rows, links 404, schedule ≤ 24 h | 0 rows in all 20 columns, 5/5 links 404, **no `purge` service or schedule** | no | sre-devops-engineer (Compose `purge` service with `PURGE_INTERVAL_S`, SRE-PURGE slice b) |
| G03-04 | IT-03 100%; earlier 100% | IT-03 162/177; earlier 316/317 (IT-02-05 inventory); sandbox 10/10 | no | senior-qa-engineer (decide the TCR rows for `bola.py` and IT-03-11 `_received`) |
| G03-05 | p95 ≤ 300, p99 ≤ 800, ≥ 99.5%, ≥ 47.5 RPS | 17.9 ms / 53.2 ms / 100% / 50.0 RPS, 0 unexpected | **yes** | — (sre-devops-engineer still owes the §6 dry-run row) |
| G03-06 | 100% non-skipped, 0 flaky | 108/113, 5 failed (E2E-03-02, -04, -05, -06 ×2), 1 flaky (E2E-03-08 loading) | no | senior-qa-engineer (G03-FE-R1-01/02, the E2E-03-05 and FE-404 TCR rows); senior-frontend-engineer (the E2E-03-08 flake) |
| G03-07 | 2 s / 1.5 s / CLS 0, n ≥ 20 each | 434 ms (n 20) / 604 ms (**n 19**) / **CLS 52** | no | senior-frontend-engineer (`d590a1c` route groups to `sprint-03`; the show-me first-frame timeout) |
| G03-08 | golden, scenarios, conservation, review record 100% | golden 31/31, manifest 0, conservation 1,000/0, (e) 7/7; **scenarios 13/15** | no | senior-qa-engineer (TCR rows `test_starter_stats.py`, `test_metric_evidence.py`) |
| G03-09 | Full Tag IT and E2E; lint; CI at head | lint 1 + 5 correct; IT-03-11 4/15; E2E-03-05 fails; no CI run at the head | no | senior-ml-cv-engineer (IT-03-11/E2E-03-05 with QA's TCR decision); sre-devops-engineer (push and dispatch CI) |
| G03-10 | axe 0 and targets 0 with D/E/X/L and states; keyboard; 320/360 | axe 0/53 and targets 0 with D/E/X/L; **no `E-01-empty` target check**; E2E-03-05 fails | no | senior-qa-engineer (E-01 empty-state check in `states.spec.ts`) |
| G03-11 | coverage, mutation, oracle, budgets | **changed lines 78%**; analytics 90.4%; rules 99.57/98.41%; web 91.67%; mutation 0.8635 / 0.9251; oracle 100,000/0; integration 283 s, **14 failed** | no | senior-qa-engineer (stale IT-03 `red_until` markers, BOLA TCR) |
| G03-12 | 0 | 4 open blockers; GitHub 0 | no | engineering-manager |

**Met: 2 / 12.**

### 8.4 New findings from this round (Open rows go to `review-rounds.md` through the EM's reconciliation)

| Id | Severity | Finding | Owner |
|---|---|---|---|
| VR2-S3-01 | major | **The IT-03 files still carry `pytestmark = red_until(story=…)` although their stories are built and the rows pass in G03-04.** The coverage and gate selection `not red_until` therefore drops them. Diff coverage falls to 78% (e.g. `analytics/api.py` 54.7%, `platform/purge.py` 59.6%), and the per-PR gate does not run the Sprint 3 ITs. Fix: remove the markers for built stories, with a TCR row | senior-qa-engineer |
| VR2-S3-02 | major | **No Compose `purge` service or schedule** (NFR-066 c). The contract (decision-log 2026-10-07, principal-engineer) names a `purge` service, and `statscontract.PURGE_SERVICE = "purge"`, but `docker compose config --services` has none. `infra/docker/purge_schedule.py` exists but is not wired in | sre-devops-engineer |
| VR2-S3-03 | minor | **Flaky E2E-03-08 loading** (1 of 3 repeats): "D-01 never asked the API for its numbers in the browser" (NFR-074) | senior-frontend-engineer |
| VR2-S3-04 | minor | **One `show-me-first-frame` sample in 20 timed out at 60 s** under the reference profile (`window.__s3.firstFrame` never set). The run has only 19 samples | senior-frontend-engineer |
| VR2-S3-05 | minor | The G03-05 dry-run row is still missing from §6 (rule 5), and the scorecard §4 G03-03 command still names `api`, not the contract's `purge` service | sre-devops-engineer |

### 8.5 Sprint demo script (sprint-03 §12), run in real time on `racket-goal03`

The walk ran on 2026-10-07 from 21:52:00 UTC. The API steps used the verifier's scratch script (`demo_walk.py`, built on `scripts/measure` helpers; log in `reports/goal03/demo-walk.txt`). The browser steps are the E2E run of 8.3.

| Step | What happened (elapsed time) | Result |
|---|---|---|
| 1 Sign in, tagged worked-example match | Sign-in 200 (1.68 s), match created, `video_received` (1.91 s), game 201, 14 rallies tagged (2.37 s) | works |
| 2 Stats: 7 cards, n, range, low sample, notice | 7 metrics, label `unofficial scoring (rules not yet verified)`, rules `PROVISIONAL-UNVERIFIED`, definitions `0.1`. AN-01 A: k 4, n 7, 0.5714, `low_sample true` (57%, n = 7, as scripted). In the browser, E2E-03-03 (definition, draft hidden, low sample) passed | works |
| 3 "Show me" on "Rallies won on serve" | AN-01 A evidence: 7 items, total 7. The first rally's video answered Range with 206. In the browser, E2E-03-01 passed, but the crawl E2E-03-02 failed (test-side, G03-FE-R1-01) | works (API); crawl red |
| 4 Correct rally 3 | 200. AN-02 A changed from 0.3333 (n 6) to 0.4 (n 5), as scripted (33% → 40%), with stats current in < 0.6 s | works |
| 5 360 px stacked cards | E2E-03-06 "stats and evidence at 320/360 px" passed. The not-found page at 320/360 answers 200, not 404 | works; not-found red |
| 6 Delete match; purge log; empty inventory | DELETE 202. Match 404 and not listed (3.00 s). `racket.platform.purge --once` rc 0, log `purge pass … matches 10, accounts 5, failed 0`. Inventory for the match: matches 0, rallies 0, snapshots 0, media 0. **No scheduled purge in Compose** (G03-03 c) | works by hand; not scheduled |
| 7 Delete the account from a second session | The second session signed in (200), DELETE /me returned 202, and the first session's `GET /me` returned 401. In the browser, E2E-03-04 failed (test-side, G03-FE-R1-02) | works (API) |
| 8 Labeller Full Tag, export, player not found | E2E-03-05 failed: the export holds no hit (`hits` `[]`). IT-03-11 failed 11 of 15 (`409 match_not_ready`, test-side TCR) | **fails** |
| 9 Drill lint | The valid library gave `ok, 0 problem(s)` with rc 0. Each of the 5 negative files gave rc 1 and named its drill and reason | works |
| 10 Scorecard and test report | This section: 2/12; golden 31/31; conservation 1,000/0; mutation 0.8635 / 0.9251; evidence crawl red; open defects 4 | shown, goal not met |
| 11 PO questions | Not a verifier step | n/a |

**Verdict:** the demo runs through the API end to end for steps 1-4, 6, 7 and 9, in real time. It cannot yet be given as scripted: step 8 (Full Tag) fails, the browser crawl and account-deletion specs are red, and the purge has no schedule.

**Not runnable in this sandbox:** WebKit runs only on CI, and there is no CI run at `593f7ff` (G03-09 c). The manual screen-reader pass (NFR-027 b) is human-gated (S3-DoD-P6). Neither is in this round's totals.

## 9. Verification round 3 (2026-10-08; senior-qa-engineer with sre-devops-engineer, independent verifiers)

**Totals: 10 of 12 met** (G03-01 to G03-08, G03-10, G03-11). The Sprint 3 goal is **not met**, because two rows are still "no":

- **G03-09 (c):** there is no CI run at the head. Origin `sprint-03` is 7 commits behind, and the last `ci.yml` run, at `09f1f67`, failed. This cannot be run from the sandbox: it needs the push and a CI dispatch on GitHub. WebKit also runs only there.
- **G03-12:** 3 blockers are still open. Closing each one needs a role other than the verifier, or the PO.

Everything the goal promises the player worked live over HTTPS on a fresh stack, in real time:

- the 7 stats per side equal the reference after every tag and after a correction;
- "Show me" works;
- delete match, delete account and the purge leave 0 rows and 0 objects, and the purge is scheduled daily;
- a labeller can Full Tag a match and export it, and the export validates;
- a player gets "not found".

The full browser suite was green (0 flaky over 3 repeats), and the timings, coverage, mutation and budget checks all met their targets.

### 9.1 Stack under test

- **Head:** `fb920bc` (`git rev-parse HEAD`), branch `sprint-03`, clean tree. The head was unchanged at teardown (`git status --short` empty).
- **Preflight:**
  - `bash scripts/disk-precheck.sh` → `ok, 10 GB free` (rc=0). That is at the floor, so the verifier pruned only its own data before the build (ops/disk-and-prune.md):
    - removed the `pw-out*` trace folders of its own VR1/VR2 reports and of `reports/goal02-qadry`;
    - moved the VR2 reports to `reports/goal03-vr2/`;
    - ran `docker builder prune -af` (2.125 GB).
  - Free space went from 11G to 17G.
  - `scripts/dev-chrome.sh` reports Chrome for Testing 141.0.7390.54.
  - The `racket-fegr2` stack (another lane) was left running.
- **Clean state:**
  - `.local/goal03` was deleted and rebuilt from `infra/env.example` as in §4.0.
  - Before the start there were 0 `racket-goal03` containers and 0 volumes, so the database volume and the object-store bucket are new.
  - The dev Postgres and the dev object store were started fresh under the new `RA_DEV_STATE`.
- **Start:** `flock .local/evidence-e2e.lock $DC up -d --build --wait` → rc=0 in 134 s. All 10 long-running services were healthy, including `purge`.
  - `DC` still carries the verifier-local `-f .local/goal03/build-ca.override.yaml`, because VR1-S3-02 is still open (`grep extra_ca infra/compose.yaml` → nothing).
  - The override now also needs a `purge` entry, because `purge` is a new build service.
  - The image was built from the head: `python -c "import racket.platform.purge, racket.dataset.admin"` in `api` printed `mods ok`.
- **Front door:**
  - `http://localhost:43000/` → 400.
  - `https://localhost:43000/` with `--cacert root.crt` → 200.
  - `/api/healthz` → `{"status":"ok"}`.
  - Alembic is at `0017`.
  - `$DC config --services` includes `purge`.
- **G03-04, 08 and 11:** these ran on `scripts/dev-postgres.sh` and `scripts/dev-objectstore.sh` (fresh), with the goal03 Mailpit.
- **Teardown:**
  - `flock … $DC down -v --rmi local --remove-orphans` → rc=0, leaving 0 `racket-goal03` containers and 0 volumes.
  - Dev Postgres and the object store were stopped (rc 0 each).
  - The mutant copies and the Playwright trace folders under `reports/goal03/` were deleted.
- **Disk:** `df -h /` showed:
  - 17G free after the prune and 13G after `up --build`;
  - 9.2G before teardown (the reports and mutant copies of this round), under the 10 GB floor;
  - 12G after teardown.
  - All live stack runs (G03-01..03, 05, 06, 07, demo) finished before the coverage and mutation steps, which took the space.
- **Reports:** under `reports/goal03/` (git-ignored). The driver logs are `e2e-driver.log` and `g11-driver.log`.

### 9.2 Preconditions (§3)

| Rule | Status |
|---|---|
| 5 Dry-run first | **Still incomplete.** G03-05 (`stats_latency.py`, sre-devops-engineer) still has no row in §6 and no decision-log row (`grep -n 'stats_latency' docs/sprints/03/decision-log.md` → no dry-run row). As in VR2, the method ran end to end as written and met its target, so the row counts. The missing row is VR3-S3-02 |
| 6 Reconciliation first | Met. The EM's reconciliation rows for VR2 (VR2-S3-01..05) are in `review-rounds.md` ("Reconciliation first … verification-round-2 findings", line 399) |

### 9.3 Summary

| ID | Target (short) | Actual (VR3) | Met | Owner to fix |
|---|---|---|---|---|
| G03-01 | 5/5 live journeys | 5/5, rc=0, no failing key | **yes** | — |
| G03-02 | p95 ≤ 5 s / 5 s / 60 s | 34.3 ms (n 70) / 24.0 ms (n 5) / 22.2 ms (n 5) | **yes** | — |
| G03-03 | 0 rows, links 404, schedule ≤ 24 h | 0 rows in 20 columns; 5/5 links 404; `purge` service with `PURGE_INTERVAL_S 86400`, first run ok | **yes** | — |
| G03-04 | IT-03 100%; earlier 100% | IT-03 + BOLA 183/183; earlier 317/317; sandbox 10/10 | **yes** | — |
| G03-05 | p95 ≤ 300, p99 ≤ 800, ≥ 99.5%, ≥ 47.5 RPS | 32.5 ms / 114.9 ms / 100% / 50.0 RPS, 0 unexpected | **yes** | — (sre-devops-engineer still owes the §6 dry-run row) |
| G03-06 | 100% non-skipped, 0 flaky | 114/114 non-skipped, 6 named Sprint 1 skips, 0 flaky over ×3 | **yes** | — |
| G03-07 | 2 s / 1.5 s / CLS 0, n ≥ 20 each | 231 ms / 837 ms / 0, n 20 each | **yes** | — |
| G03-08 | golden, scenarios, conservation, review record | 31/31, 15/15, 1,000/0 and 1/1, manifest 0, (e) 7/7 | **yes** | — |
| G03-09 | Full Tag IT and E2E; lint; CI at the head | IT-03-11 15/15, E2E-03-05 passed, lint 1 + 5; **no CI run at `fb920bc`** | no | sre-devops-engineer (push `sprint-03` and dispatch `ci.yml`; the orchestrator owns the push) |
| G03-10 | axe 0 and targets 0 with D/E/X/L and states; keyboard; 320/360 | axe 0/55; targets 0, every family and state present incl. `E-01-empty`; keyboard and 320/360 passed | **yes** | — |
| G03-11 | coverage, mutation, oracle, budgets | 94%; analytics 98.1%; rules 99.57/98.41%; web 91.64%; mutation 0.8635 / 0.9251; oracle 100,000/0; 8.0 s / 12.2 s / 350 s, 0 failed | **yes** | — |
| G03-12 | 0 | 3 open blockers; GitHub 0 | no | engineering-manager (escalation; the fixes need the orchestrator, reviewers and PO for the PRs, the business-analyst and product-manager for the DR-03/D-1/D-2/R2-3 cells, and senior-frontend-engineer with the chair for the R-1/R2-1 walk) |

**Met: 10 / 12.**

**Not runnable in this sandbox (not counted as met):**

- the CI run at the head, which includes WebKit and the `drill-lint` job. It runs only on GitHub Actions after the push (G03-09 c).
- the manual screen-reader pass (NFR-027 b), which is human-gated (S3-DoD-P6).

### 9.4 New findings from this round (Open rows go to `review-rounds.md` through the EM's reconciliation)

| Id | Severity | Finding | Owner |
|---|---|---|---|
| VR3-S3-01 | minor | **VR1-S3-02 is still open, and it grew.** `infra/compose.yaml` passes no `extra_ca` build secret, so §4.0 `up --build` still needs a verifier-local override behind the sandbox proxy. Since SRE-PURGE (`cad2451`), the override must also cover the new `purge` build service | sre-devops-engineer |
| VR3-S3-02 | minor | The G03-05 dry-run row is still missing from §6 and from the decision log. This is the rule-5 half of VR2-S3-05, still not done after three rounds | sre-devops-engineer |
| VR3-S3-03 | minor | **The verifier's own reports fill the disk.** Free space fell to 9.2G before teardown, under the 10 GB floor. The cause is the Playwright `pw-out*` folders (about 1.3 GB per ×3 run) plus the mutant copies of §4 G03-11. §4 has no step to delete them during the run, and `live_stats.py`/`stats_latency.py` do not record free disk in their JSON. Proposal: §4 deletes `pw-out-repeat` after `flaky_report.py` and the mutant copies after scoring (this round did both, by hand) | senior-qa-engineer (method author) |

### 9.5 Sprint demo script (sprint-03 §12), run in real time on `racket-goal03`

The walk ran on 2026-10-08 from 01:04:20 UTC, after the E2E runs.

- **API steps:** the verifier's scratch script (`demo_walk_vr3.py`, built on `scripts/measure` helpers). Log in `reports/goal03/demo-walk.txt` and `demo-walk-step8.txt`.
- **Browser steps:** the E2E run of 9.3.

| Step | What happened (elapsed time) | Result |
|---|---|---|
| 1 Sign in, tagged worked-example match | Sign-in 200 (2.36 s), match created, `video_received` (2.63 s), game 201, 14 rallies tagged (3.13 s) | works |
| 2 Stats: 7 cards, n, range, low sample, notice | 7 metrics, label `unofficial scoring (rules not yet verified)`, rules `PROVISIONAL-UNVERIFIED`, definitions `0.1`. AN-01 A: k 4, n 7, 0.5714, `low_sample true` (57%, n = 7, as scripted). In the browser, E2E-03-03 (definition shown, draft hidden, low sample) passed | works |
| 3 "Show me" on "Rallies won on serve" | AN-01 A evidence: 7 items, total 7. The first rally's video answered Range with 206 (3.20 s). In the browser, E2E-03-01 and the crawl E2E-03-02 passed | works |
| 4 Correct rally 3 | 200. AN-02 A changed from 0.3333 (k 2, n 6) to 0.4 (k 2, n 5), as scripted (33% → 40%), with stats current in < 0.6 s | works |
| 5 360 px stacked cards | E2E-03-06 "stats and evidence at 320/360 px" passed, and so did the not-found page at 320/360 (HTTP 404). G03-07 CLS 0 | works |
| 6 Delete match; purge log; empty inventory | DELETE 202. Match 404 and not listed (3.83 s). `exec -T purge python -m racket.platform.purge --once` rc 0, log `purge pass … matches 9, accounts 4, failed 0`. Inventory for the match: matches 0, rallies 0, snapshots 0, media 0. The `purge` service also ran its scheduled pass at start (`next_run_in_s 86400`) | works |
| 7 Delete the account from a second session | The second session signed in (200), DELETE /me returned 202, and the first session's `GET /me` returned 401 (7.38 s). In the browser, E2E-03-04 passed | works |
| 8 Labeller Full Tag, export, player not found | A new account got 404 on `/label/matches/{id}` before the role. `racket.dataset.admin grant-labeller` rc 0, then 409 (no consent). `consent` rc 0, then Full Tag 200 (fps 60, 3,600 frames, players A1-B2). Rally label 201, hit label (frame 40, B1) 201, export 200 `attachment; filename="labels-<id>.json"`. `validate_labels(export)` → `()`, schema `full-tag-labels/v1`. A player account got 404 on the label route and the export. The verifier's first attempt sent `outcome: "A"` instead of the schema's outcome object and got 422 `invalid_label`: a verifier input error, and the refusal was correct. In the browser, E2E-03-05 (keys, hit, export, player refused) passed | works |
| 9 Drill lint | The valid library gave `ok, 0 problem(s)` with rc 0. Each of the 5 negative files gave rc 1 and named its drill and reason | works |
| 10 Scorecard and test report | This section: 10/12. Golden 31/31; conservation 1,000/0; mutation 0.8635 / 0.9251; evidence crawl green; **open defects 3, not the scripted 0** | shown, goal not met |
| 11 PO questions | Not a verifier step | n/a |

**Verdict:** steps 1-9 of the demo run end to end in real time on the live HTTPS stack. Step 10 cannot be given as scripted: the scorecard is 10/12, with no CI run at the head and 3 open blockers.
