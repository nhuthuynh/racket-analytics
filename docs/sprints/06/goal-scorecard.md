# Sprint 6 goal scorecard

- **Written:** 2026-11-13 at Sprint 6 planning (ticket PLAN-06) by the engineering-manager, with the product-manager (goal wording, metrics the product can fail), principal-engineer (comparison and read-cost assumptions), business-analyst (atomic items, `requirements-breakdown.md`) and senior-qa-engineer (methods, fail-closed rules, planted-failure checks).
- **Why:** PO standing rule. A sprint is done only when its **goal is shown to work on a live local stack**, each metric measured against its target. Human-only items are not goal metrics; they are the "not met: waiting on P-n" rows of §5 (PO P12 option b).
- **Verifier fills in:** `Actual`, `Met` (yes / no) and `Evidence` (exact command, stack head SHA, result line or report path, and the verification data: synthetic fixture, team-made Full Tag fixture, licensed footage or consented footage). Nothing else in this file changes without a row in a ticket's `decisions/<ID>.md`.
- **Sources:** `docs/sprints/sprint-06.md` §1, §3, §8; `requirements-breakdown.md` (atomic items); FR-170..FR-174 (BA-6), NFR-006, NFR-010, NFR-027, NFR-050, NFR-062, NFR-063, NFR-066, NFR-069, NFR-075; ADR 0005, 0014, 0055, 0056, 0060.
- **Order (ADR 0055 rule 1):** VERIFY-06 starts only when Sprint 5 is closed (entry condition E1) and every wave 2 ticket in `sprint-06.md` §15 is merged. RETRO-06 starts only when `retro_ready.py` exits 0. One close PR.
- **Honesty rule for this sprint:** a row met on team-made or synthetic fixtures says so in Evidence. No row may report that anything was "measured from pro matches"; that needs P11.

## 1. Sprint goal (sprint-06 §1)

**On the local stack (`make up` + `make demo`) a player sees a versioned, cited reference pattern set, their own measured gaps against it ranked with n and uncertainty, and drills chosen to close the top gaps, each drill citing the metric and the reference pattern; and every value says where it came from.**

## 2. Scorecard

| ID | What is measured (atomic items) | Target | Method (detail in §4) | Actual | Met | Evidence |
|---|---|---|---|---|---|---|
| G06-01 | **Reference-set integrity and provenance** (FR-170.R1-R4) | **reference set v1: 100 % of entries with source_type, resolvable source id, n, interval, level band, status and version (lint rc 0); 0 draft entries returned by the API; planted refusals red 5 of 5 (no source, unresolved citation, measured entry without "reference-library" use, duplicate version, edited published version)** | §4 G06-01 | | | |
| G06-02 | **Pattern computation correctness** (FR-171.R1-R6) | **`pattern_example.py --check` 0 differences on GS-PAT-1; QA-REF-GOLD golden test 0 differences; Quick Tag measures equal starter stats on GS-AN-1 (0 differences); mutation ≥ 0.80 on `analytics/patterns`** | §4 G06-02 | | | |
| G06-03 | **Honest gap ranking** (FR-172.R1-R4, NFR-075.1-.2) | **on the demo stack: 0 ranked weaknesses with n < min_n or with overlapping intervals; 100 % of listed patterns carry state, n, interval, reference id, version and status; planted low-n and overlap fixtures give "not enough data" and "no clear gap"; golden replay identical; mutation ≥ 0.80 on `coaching/weakness`** | §4 G06-03 | | | |
| G06-04 | **Cited exercise recommendations with coverage** (FR-173.R1-R4) | **100 % of recommended drills' Why carry pattern id, value, n, interval, reference id, version and status (validator); plan eval pass^3 = 100 % incl. the new gap cases; coverage rc 0 over pattern × level × players × equipment; planted Why without version rejected; planted gap fixture rc 1 naming the cell** | §4 G06-04 | | | |
| G06-05 | **The demo slice end to end** (DEMO-6.1-6.4) | **`make up` → `make demo` ×2 rc 0; @critical slice journey 100 % pass on `chromium`, `webkit`, `android-chrome`, 3 repeats, 0 flaky; demo-a and demo-b top gaps differ; planted reference v2 changes the Why; flags off: R1 journey passes and new routes 404** | §4 G06-05 | | | |
| G06-06 | **Weakness-view latency and read cost** (NFR-010.10-.12) | **`GET /me/weaknesses` p95 ≤ 300 ms and p99 ≤ 800 ms at ≥ 49.5 RPS, 3 of 3 runs, flags on; ≤ 4 SQL statements per read of an unchanged match** | §4 G06-06 | | | |
| G06-07 | **Accessibility of the new screens** (NFR-027.10-.14) | **axe serious/critical violations 0 on the reference browser, weakness view and plan on 3 projects; chart marks ≥ 3:1; chart vs table mismatches 0; controls < 24 px 0; states by colour only 0** | §4 G06-07 | | | |
| G06-08 | **Provenance, privacy and licence gates** (FR-174.R1-R2, NFR-062.1-.3, NFR-063.3-.4, NFR-066.10, NFR-069.2, NFR-050.10) | **jobs for assets without provenance or with incomplete consent refused 100 % of planted cases, nothing decoded; AGPL/unknown licences incl. weights manifest 0 and a planted AGPL row rc 1; unclassified new columns 0; pattern rows left after match purge 0; pattern values in logs or labels 0; BOLA non-404 on new routes 0** | §4 G06-08 | | | |
| G06-09 | **Test strength, budgets and security fixes** (NFR-050.11-.12, NFR-006.7) | **every IT id passes incl. IT-06-01..08; integration ≤ 600 s in CI's parallel form; mutation ≥ 0.80 on `coaching/plan` and `coaching/weakness`; eval harness dry-run rc 0 with a planted regression rc 1; SEC-R05 and SEC-R11 rows Pass (if merged; P2 rows missing are "no")** | §4 G06-09 | | | |
| G06-10 | **Flow and cost per PR are measured** (ADR 0056 decisions 1 and 3; PRC-12.1). Values reported, **never targets** [ASB/AGL-02] | **`flow_metrics.py` rc 0 with cycle time (median, max), throughput, work item age, WIP breaches; 100 % of merged Sprint 6 ticket decisions files carry the cost table with agent wall time per round (uncaptured rounds say "not measured"); `wip_gate.py` planted 4th start refused** | §4 G06-10 | | | |
| G06-11 | **CI, merge discipline, Sprint 5 closed, one close** | **CI green at the close head (push run, every job incl. `ci-gate`) and the last 2 scheduled CI runs on `main` green; every merged Sprint 6 PR has its tier's verdicts on the merged head; RETRO-05 merged before VERIFY-06; open blocker/major 0; merged-PR set equals `status.json`; 1 RETRO-06 PR** | §4 G06-11 | | | |

**Overall:** the Sprint 6 goal is met only when all 11 rows are "yes". A row whose method could not run is "no", never "n/a" (fail closed, ADR 0014). Human-gated items (§5) never count as met or missed here.

**Status at planning (engineering-manager, 2026-11-13; not a verifier result):** met 0 / 11. None of the slice exists. CI at planning: push run 43334586810 at `e7ed7d9d` → success; scheduled CI 43206773425 → success, 43007950254 → failure (2026-11-11, perf; CI-NIGHTLY-PERF #232 open). Sprint 5 is not closed (13 open PRs).

## 3. Rules for the verifier

1. Fresh worktree of `main` at the head named in the VERIFY-06 brief, own Compose project names (`racket-goal06-off`, `racket-goal06-on`, `racket-perf06`), `bash scripts/disk-precheck.sh` rc 0 before each build (16 GB floor for builds, 10 GB otherwise); every stack torn down with `down -v --rmi local`; `df -h /` at start and end in `decisions/VERIFY-06.md`.
2. Every method in §4 is run as written, in the configuration it names; a method changed by the verifier is a finding, not a pass.
3. Re-run every row, not only rows that failed before.
4. Findings use parseable ids `QA-VERIFY06R<n>-<nn>` and get ledger rows in `docs/sprints/06/review-rounds.md` (planned) in the same PR.
5. The VERIFY PR is always merged (ADR 0055 rule 3), met or not.
6. Every Evidence cell names the verification data (§ header honesty rule).

## 4. Methods

Each method's author dry-runs it live, in the configuration it measures, and logs the rc in §6 and in the ticket's decisions file **before** VERIFY-06 (ADR 0055 rule 2). Each method also shows it can fail: the planted-failure line is part of the dry-run. Every block runs from the repository root; every `cd` sits inside a `( … )` subshell. Scripts and files marked (planned) are created by the ticket named in the heading; the author fixes the exact command in its §6 row, and a changed command is pinned by QA-PIN-06.

### G06-01 (authors: senior-backend-engineer ST-170a, ST-170b; content pickleball-domain-coach COACH-6c) (planned)
```
(cd backend && uv run racket-reference-lint ../content/references)
(cd backend && uv run racket-reference-lint --planted ../backend/tests/fixtures/reference_refusals)   # expects rc 1, 5 named refusals
(cd backend && uv run pytest -q tests/integration/test_it_06_02_reference_api.py)
```

### G06-02 (authors: pickleball-domain-coach COACH-6b; senior-ml-cv-engineer ST-171b/c; senior-qa-engineer QA-REF-GOLD; senior-backend-engineer ST-171a) (planned)
```
python3 docs/domain/tools/pattern_example.py --check
(cd backend && uv run pytest -q tests/regression/golden_patterns tests/integration/test_it_06_03_quick_tag_equivalence.py)
```
Mutation from the nightly job's `analytics/patterns` target (QA-PIN-06 pins the step).

### G06-03 (author: senior-backend-engineer, ST-172a/b) (planned)
```
export COMPOSE_PROJECT_NAME=racket-goal06-on FEATURE_REFERENCE_PATTERNS=true
make up && make demo
python3 scripts/measure/weakness_honesty.py --base-url https://localhost:3000 --users demo-a,demo-b --min-n-from content/references
(cd backend && uv run pytest -q tests/integration/test_it_06_06_golden_replay.py tests/unit/coaching/weakness)
```
`weakness_honesty.py` (planned, ST-172b) exits 1 on any ranked pattern with n < min_n or overlapping intervals, or any listed pattern missing a field; its planted line runs it against a stubbed response with one such pattern.

### G06-04 (author: senior-backend-engineer, ST-173a/b) (planned)
```
(cd backend && uv run racket-plan-eval --repeats 3)
(cd backend && uv run racket-drill-coverage ../content/drills)
(cd backend && uv run pytest -q tests/integration/test_it_06_07_plan_why.py)
```

### G06-05 (author: senior-qa-engineer, ST-174b; demo by senior-backend-engineer, ST-174a) (planned)
```
python3 scripts/measure/live_goal.py demo --flags on  --project racket-goal06-on  --runs 2
python3 scripts/measure/live_goal.py demo --flags off --project racket-goal06-off --runs 2
(cd web && npx playwright test --grep @critical --project chromium --project webkit --project android-chrome --repeat-each 3 e2e/sprint-06)
python3 scripts/measure/browser_matrix.py --require chromium,webkit,android-chrome --report web/playwright-report
```

### G06-06 (author: senior-backend-engineer, ST-172b; pinned by QA-PIN-06) (planned)
The Sprint 5 G05-01 block (Locust 2.46.7, 50 RPS, 3 runs, flags on) with the `weakness-view` task, then `perf_verdict.py --endpoint weakness-view --p95-ms 300 --p99-ms 800`; plus `(cd backend && uv run pytest -q tests/integration/test_it_06_05_weakness_read_cost.py)`.

### G06-07 (authors: senior-frontend-engineer ST-172c; senior-qa-engineer ST-174b) (planned)
```
(cd web && npx playwright test --grep @a11y e2e/sprint-06)
python3 docs/design/tools/contrast_check.py --tokens docs/design/tokens.json --pairs gap-chart
(cd web && npm run test:unit -- weakness-chart-table)
```

### G06-08 (authors: senior-backend-engineer ST-175a, ST-171e, ST-172b; sre-devops-engineer ST-175b) (planned)
```
(cd backend && uv run pytest -q tests/integration/test_it_06_08_provenance_gate.py tests/integration/test_it_05_05_classification.py tests/integration/test_it_06_04_pattern_deletion.py tests/regression/test_bola_matrix.py)
python3 scripts/ci/licence_gate.py --sbom reports/sbom-worker.json --weights models/manifest.json
python3 scripts/ci/licence_gate.py --sbom backend/tests/fixtures/sbom_agpl.json --weights models/manifest.json   # expects rc 1
```

### G06-09 (author: senior-qa-engineer; eval harness senior-ml-cv-engineer ST-176a) (planned)
CI's NFR-073 integration form (pinned), the nightly mutation job, `python3 scripts/eval/run_eval.py --fixtures docs/data/phone-fixtures.md --out docs/evals/` and its planted-regression line, and the ASVS status tool on the SEC-R05/R11 rows.

### G06-10 (author: senior-qa-engineer, QA-FLOW-METRICS and QA-WIP-GATE)
```
python3 scripts/measure/flow_metrics.py --repo nhuthuynh/racket-analytics --since 2026-11-13 \
  --decisions docs/sprints/06/decisions --json reports/flow06.json
```
Plus `wip_gate.py` against a stub with 3 PRs in review (expects rc 1). Values go to the sprint report; only "measured and complete" is a target.

### G06-11 (author: engineering-manager, RETRO-06 close checks)
```
python3 scripts/measure/open_defects.py docs/sprints/06/review-rounds.md
gh api 'repos/nhuthuynh/racket-analytics/actions/runs?event=schedule&branch=main&per_page=4'
python3 scripts/measure/retro_ready.py --repo nhuthuynh/racket-analytics --ledger docs/sprints/06/review-rounds.md
```
and the per-PR `merged_verdict.py` audit as Sprint 5's G05-12.

## 5. Not met: waiting on P-n (PO P12 option b; not goal metrics)

| Row | Item | Waits on | What the team prepares this sprint | How it is measured once supplied |
|---|---|---|---|---|
| S6-P21 | Confirmation that Sprint 6 is video analysis and the Go port moves to Sprint 7 (conflicts with "Port the product to Go (PO decision 2026-10-06)") | **P21** (new) | EM-ESC-06 options with cost; a CV-optional, tag-based slice with pure domain functions | PO answer quoted in po-input |
| S6-P11 | Licensed pro-match footage and consented training footage; reference values "measured" from them; CV spikes (NFR-006.9) | **P11** (OQ-06) | provenance gate ST-175a, licence gate ST-175b, eval harness ST-176a, spike plans ST-176b, footage spec and rights/consent checklist (COACH-6a, SEC-6), labelling protocol | first `measured` reference entry with a rights record; spike eval reports |
| S6-P15 | Human coach verification of reference patterns and new drills (`verified`) | **P15** | COACH-6a/6c entries `coach-reviewed` with citations; ST-173c drills; copy register | count of `verified` entries |
| S6-P16 | Legal review: training-video consent, pose data, statistics derived from licensed footage (NFR-070, US + AU) | **P16** | SEC-6 question list; flags default-off | ADR accepted by the PO |
| S6-P22 | Permission to cite published secondary statistics in the reference set | **P22** (new) | sources register with resolve status | PO answer; entries re-labelled if refused |
| S6-P7 | Rulebook (OQ-01) for rule-dependent patterns | **P7** | COACH-6a maps rule-dependent patterns to rule ids | `rules-verified.md` rows |
| S6-P9 | Usability of the weakness view with players | **P9** | PD-6 tasks added to the R1 usability kit | observation tally |
| S6-P19 | Residual-risk ADR 0059 acceptance | **P19** | SEC-6 re-ask text; no deployment beyond localhost | ADR accepted |
| S6-P8 | GPU budget for CV (OQ-13) | **P8** | CPU-only spike plans | budget value in settings |
| S6-D1 | DR-04 hold or waiver | **D1** | PD-DR04 record | PO answer |

## 6. Dry-run rows (method authors, before VERIFY-06)

One row per metric, rc 0 on the real method plus the planted-failure rc, in the configuration it measures (ADR 0055 rule 2). Each author's ticket PR adds its own row. VERIFY-06 refuses to start while any metric has no rc 0 row. Methods for tools that do not exist yet cannot be dry-run at planning; their row is a merge condition of the ticket that builds them.

| Metric | Author | Ticket | Date | Head | Command (as §4) | rc | Planted-failure rc |
|---|---|---|---|---|---|---|---|
| G06-01 | senior-backend-engineer | ST-170a | | | | | |
| G06-02 | pickleball-domain-coach / senior-qa-engineer | COACH-6b, QA-REF-GOLD | | | | | |
| G06-03 | senior-backend-engineer | ST-172b | | | | | |
| G06-04 | senior-backend-engineer | ST-173a | | | | | |
| G06-05 | senior-qa-engineer | ST-174b | | | | | |
| G06-06 | senior-backend-engineer | ST-172b | | | | | |
| G06-07 | senior-frontend-engineer | ST-172c | | | | | |
| G06-08 | senior-backend-engineer / sre-devops-engineer | ST-175a, ST-175b | | | | | |
| G06-09 | senior-qa-engineer | QA-PIN-06 | | | | | |
| G06-10 | senior-qa-engineer | QA-WIP-GATE | | | | | |
| G06-11 | engineering-manager | RETRO-06 | | | | | |
| G06-11 (planning dry-run, ledger tool) | engineering-manager | PLAN-06 | 2026-11-13 | `e7ed7d9d` | `python3 scripts/measure/open_defects.py docs/sprints/05/review-rounds.md` (the Sprint 6 ledger does not exist yet) | 1, `"open": 5` (SEC-S5-TM-01, SEC-S5-TM-02 blockers; COACH-S5-01, COACH-S5-05 majors; 1 more): a real Sprint 5 state, reconciled in the drain | this run is itself the failing case; rc 0 on `docs/sprints/04/review-rounds.md` (`open 0`, PLAN-05 row) shows the passing case |
| G06-11 (planning dry-run, scheduled runs) | engineering-manager | PLAN-06 | 2026-11-13 | `e7ed7d9d` | `gh api 'repos/nhuthuynh/racket-analytics/actions/runs?event=schedule&per_page=10'` | 0 (data source reachable; 43206773425 success, 43007950254 failure) | n/a (read only) |
| G06-10 (planning dry-run, data source) | engineering-manager | PLAN-06 | 2026-11-13 | `e7ed7d9d` | the §4 G06-10 command with `--since 2026-11-03 --decisions docs/sprints/05/decisions` (no Sprint 6 PR has merged yet), `SSL_CERT_FILE=/root/.ccr/ca-bundle.crt` | 1, "flow-metrics: measured, incomplete": throughput 39, cycle time median 2.2 h / max 182.6 h, CI 1295.9 min, **cost tables 9 of 39 merged tickets (23 %)**, work item age #201 218.5 h, #218 185.1 h | the run above is the failing case (incomplete cost tables); it is why CI-DOC-CHECK-06 adds PRC-11.3 |
