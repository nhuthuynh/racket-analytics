# Sprint 5 goal scorecard

- **Written:** 2026-11-03 at Sprint 5 planning (ticket PLAN-05) by the engineering-manager, with the product-manager (goal wording, what counts as release-readiness), principal-engineer (latency, alerting and restore assumptions), business-analyst (atomic items, `requirements-breakdown.md`) and senior-qa-engineer (methods, fail-closed rules, planted-failure checks).
- **Why:** PO standing rule. A sprint is done only when its **goal is shown to work on a live local stack**, each metric measured against its target. Human-only items are not goal metrics; they are the "not met: waiting on P-n" rows of §5 (PO P12 option b).
- **Verifier fills in:** `Actual`, `Met` (yes / no) and `Evidence` (exact command, stack head SHA, result line or report path). Nothing else in this file changes without a row in a ticket's `decisions/<ID>.md`.
- **Sources:** `docs/sprints/sprint-05.md` §1, §3, §8; `requirements-breakdown.md` (atomic items); NFR-010, NFR-024, NFR-036, NFR-041, NFR-042, NFR-045, NFR-049, NFR-050, NFR-063, NFR-067, NFR-069, NFR-070, NFR-073; ADR 0014 (fail closed), ADR 0033, ADR 0050, ADR 0055, ADR 0056.
- **Order (ADR 0055 rule 1, retro 4 F1):** VERIFY-05 starts only when every build ticket in `sprint-05.md` §15 is merged. RETRO-05 starts only when `retro_ready.py` (EM-CLOSE-CHECKS) exits 0. One close PR.

## 1. Sprint goal (sprint-05 §1)

**R1 is a release candidate whose agent-measurable release gates are each proven live on the local stack, and every human gate has a ready kit and a dated PO ask.**

## 2. Scorecard

| ID | What is measured (atomic items) | Target | Method (detail in §4) | Actual | Met | Evidence |
|---|---|---|---|---|---|---|
| G05-01 | **R1 read latency at 50 RPS** (NFR-010.1-.9): match, score sheet, dashboard, plan; Compose stack, flags on | **every endpoint p95 ≤ 300 ms and p99 ≤ 800 ms; errors ≤ 0.5 %; achieved ≥ 49.5 RPS; 3 of 3 runs** | §4 G05-01 | | | |
| G05-02 | **SLOs and burn-rate alerts** (NFR-041.1-.5, NFR-042.1-.5): promtool rule tests; live 5xx injection on the `obs` profile; SLI series present | **promtool 8 of 8 alert cases pass (4 firing, 4 negative not firing); live fast-burn alert firing ≤ 10 min; 0 alerts in a clean 10 min run; both SLI series > 0** | §4 G05-02 | | | |
| G05-03 | **Restore drill** (NFR-045.1-.4) | **RPO ≤ 24 h; RTO ≤ 240 min; corrections count and SHA-256 equal; object count and hash equal; planted deleted row detected** | §4 G05-03 | | | |
| G05-04 | **Browser matrix, automated** (NFR-024.1-.3): critical journeys per Playwright project | **100 % pass on `chromium`, `webkit`, `android-chrome`, 3 repeats, 0 flaky** | §4 G05-04 | | | |
| G05-05 | **Fix a call in ≤ 2 taps** (NFR-036.4) | **max taps/keys ≤ 2 for each call type on `chromium` and `android-chrome`; planted 3-step path reported as 3** | §4 G05-05 | | | |
| G05-06 | **Data protection** (NFR-063.1-.2, NFR-067.1-.3, NFR-069.1) | **unclassified stored types 0; incomplete classes 0; authenticated GETs without `no-store` 0; auth data after logout 0; SW-cached media 0; PII in metric labels or logs 0** | §4 G05-06 | | | |
| G05-07 | **ASVS 5.0 L2 release review** (NFR-050.1-.8) | **applicable L2 rows not assessed 0 (V1-V17); `Fail` rows without owner 0; `Pass` rows without evidence 0; BOLA non-404 0; missing security headers 0; pre-hydration-submittable forms 0** | §4 G05-07 | | | |
| G05-08 | **Tiered merge gate and doc checks** (PRC-2.1-2.7, PRC-3.1-3.4, PRC-4.1-4.2) | **`merge_ready.py` planted-fixture matrix 7 of 7 as expected; `doc-check` and `pr-policy` reconcile step present in `ci-gate` and green on the close head; planted breaks red 5 of 5** | §4 G05-08 | | | |
| G05-09 | **The R1 prototype still runs, flags off and on** (DEMO-1.1, FR-055.R1, REL-1.2, REL-1.3) | **`make up` → `make demo` ×2 → `make down` rc 0 flags off and flags on; E2E full suite 100 %, 0 flaky over 3 runs; "unofficial scoring" notice on 4 page families; rollback redeploy healthy; migration down/up rc 0** | §4 G05-09 | | | |
| G05-10 | **Test strength and budgets** | **every IT id passes (incl. new IT-05-*); integration ≤ 600 s in CI's parallel form; mutation ≥ 0.80 on `coaching/plan` and `coaching/weakness` and ≥ 0.85 on rules; rally-F1 matcher unit + property suite passes** | §4 G05-10 | | | |
| G05-11 | **Flow and cost per PR are measured** (PRC-5.1-5.5; ADR 0056 decisions 1 and 3). The values are reported, **never targets** [ASB/AGL-02] | **`flow_metrics.py` rc 0 with cycle time (median, max), throughput, work item age, WIP breaches; 100 % of merged Sprint 5 ticket decisions files carry the cost table (uncaptured rounds say "not measured")** | §4 G05-11 | | | |
| G05-12 | **CI, merge discipline, open defects, one close** | **CI green at the close head (push run, every job incl. `ci-gate`); every merged Sprint 5 PR has its tier's verdicts on the merged head; open blocker/major 0; merged-PR set equals `status.json` map; 1 RETRO PR** | §4 G05-12 | | | |

**Overall:** the Sprint 5 goal is met only when all 12 rows are "yes". A row whose method could not run is "no", never "n/a" (fail closed, ADR 0014). Human-gated items (§5) never count as met or missed here.

**Status at planning (engineering-manager, 2026-11-03; not a verifier result):** met 0 / 12. The SLO, restore, android-chrome, tier and doc-check work does not exist yet. CI at planning: push run 41643389454 on `main` at `04c6a826` → success (also 41639406875 at `785b4ab4` → success); scheduled CI run 41622904539 on `888760df` **cancelled** (Flaky-test report 55 min over its 45 min limit) and not noticed (PRC-1.1), so CI-NOTICE-CANCELLED goes first.

## 3. Rules for the verifier

1. Fresh worktree of `main` at the head named in the VERIFY-05 brief, own Compose project names (`racket-goal05-off`, `racket-goal05-on`, `racket-drill05`, `racket-obs05`), `bash scripts/disk-precheck.sh` rc 0 before each build (16 GB floor for builds, 10 GB otherwise); every stack torn down with `down -v --rmi local`; `df -h /` at start and end in `decisions/VERIFY-05.md`.
2. Every method in §4 is run as written, in the configuration it names; a method changed by the verifier is a finding, not a pass.
3. Re-run every row, not only rows that failed before (retro 4 §12).
4. Findings use parseable ids `QA-VERIFY05R<n>-<nn>` and get ledger rows in `docs/sprints/05/review-rounds.md` in the same PR.
5. The VERIFY PR is always merged (ADR 0055 rule 3), met or not.

## 4. Methods

Each method's author dry-runs it live, in the configuration it measures, and logs the rc in §6 and in the ticket's decisions file **before** VERIFY-05 (ADR 0055 rule 2, retro 4 E4). Each method also shows it can fail: the planted-failure line is part of the dry-run. Every block runs from the repository root, and every `cd` sits inside a `( … )` subshell, so the next line starts at the root again (PE-PLAN05-07 / PLAN05-QA-08; the same defect was in G05-04, G05-07 and G05-09).

### G05-01 (author: senior-backend-engineer, ST-074; pinned by QA-PIN-05)
```
# one Compose project for the whole block: infra/compose.yaml:6 sets name: racket-analytics and the
# Makefile's COMPOSE has no -p, so every make target (up, demo, down) reads COMPOSE_PROJECT_NAME from the shell;
# the four flags come from the shell too (shell values override infra/.env; make has no FLAGS variable)
# ST-074: each Locust user seeds its own account, so the per-IP sign-in and match-creation limits
# are raised for 3 runs x 50 accounts from one client (as the CI perf-baseline job raises them)
export COMPOSE_PROJECT_NAME=racket-goal05-on FEATURE_AGE_GATE=true FEATURE_RETENTION_SETTING=true \
  FEATURE_TRAINING_CONSENT=true FEATURE_QUOTAS=true AUTH_LINK_LIMIT_PER_IP=1000 \
  AUTH_EXCHANGE_LIMIT_PER_IP=1000 MATCH_CREATIONS_PER_IP_PER_HOUR=1000
# make up only: `make demo` fails with FEATURE_AGE_GATE on (seed_demo.py has no age confirmation;
# ST-074 finding), and locustfile_r1.py seeds its own accounts
make up
for run in 1 2 3; do
  uvx --from locust==2.46.7 locust -f backend/tests/perf/locustfile_r1.py --headless \
    -u 50 -r 50 -t 8m --csv reports/perf/r1-$run --only-summary
  python3 scripts/ci/perf_verdict.py --stats reports/perf/r1-${run}_stats.csv --rps 50 \
    --min-rps 49.5 --warmup-s 60 --p95-ms 300 --p99-ms 800 --max-error-pct 0.5 --min-window 300 \
    --per-endpoint match,score-sheet,dashboard,plan --json reports/perf/r1-$run.json
done
```
Met when all three verdict files say `pass` for all 4 endpoints. Planted failure: `--p95-ms 1` → rc 1 naming the endpoint.

### G05-02 (author: sre-devops-engineer, ST-075c)
```
# promtool image = PROMTOOL_IMAGE in infra/tests/billing_alert_fixtures.py (ADR 0057; ST-075c: the
# v2.53.2 form without --entrypoint exits 1, "prometheus: error: unexpected promtool")
docker run --rm --network=none --entrypoint=/bin/promtool -v "$PWD/infra/observability/alerts:/a:ro" -w /a \
  mirror.gcr.io/prom/prometheus:v3.5.0@sha256:63805ebb8d2b3920190daf1cb14a60871b16fd38bed42b857a3182bc621f4996 \
  test rules slo.test.yml                      # 8 cases
# drill-only stack: APP_ENV=test from the shell overrides infra/.env for this project only; shipped
# infra/env.example (APP_ENV=dev) and infra/compose.yaml are unchanged; the override adds only the seam value
# one Compose project for the whole block (PE-PLAN05-R2-01): infra/compose.yaml:6 sets name: racket-analytics and
# the Makefile's COMPOSE has no -p, so `make demo` without this export copies web-tls from the wrong project
# the obs overlay points the API at the collector (ST-075b); without it nothing reaches Prometheus
cat infra/env.example infra/observability/obs.env > infra/.env
export COMPOSE_PROJECT_NAME=racket-obs05
APP_ENV=test docker compose -f infra/compose.yaml -f infra/compose.fault-drill.yaml --env-file infra/.env \
  -p "$COMPOSE_PROJECT_NAME" --profile obs up -d --build --wait && make demo
# clean run first (ST-075c): after a burst the slow-burn alert can fire until its 30 m window clears
python3 scripts/ops/inject_5xx.py --base-url https://localhost:3000 --rate 0 --minutes 10 \
  --expect-no-alert --prom http://localhost:9090 --json reports/slo-clean.json
# fresh stack for the drill (PE-075c-R1-01): the clean run's 6000 good requests stay in the 1 h window
# and hold a 10-minute 10 % burst at 600/12000 = 5 %, under the 7.2 % fast-burn threshold
docker compose -f infra/compose.yaml -f infra/compose.fault-drill.yaml -p "$COMPOSE_PROJECT_NAME" \
  --profile obs down -v
APP_ENV=test docker compose -f infra/compose.yaml -f infra/compose.fault-drill.yaml --env-file infra/.env \
  -p "$COMPOSE_PROJECT_NAME" --profile obs up -d --build --wait && make demo
python3 scripts/ops/inject_5xx.py --base-url https://localhost:3000 --rate 10 --minutes 10 \
  --expect-alert ApiAvailabilityFastBurn --prom http://localhost:9090 --json reports/slo-drill.json
curl -s 'http://localhost:9090/api/v1/query?query=racket_upload_sessions_total' | jq '.data.result|length'
docker compose -f infra/compose.yaml -f infra/compose.fault-drill.yaml -p "$COMPOSE_PROJECT_NAME" \
  --profile obs down -v --rmi local
```
Planted failure: a rule file with the fast-burn threshold at 100 % → the promtool case fails. Negative (NFR-041.6): `python3 scripts/ops/inject_5xx.py --base-url https://localhost:3000 --rate 100 --minutes 1 --expect-no-5xx --json reports/slo-seam-off.json` against a `make up` stack (`APP_ENV=dev`, no override) → 0 responses with status 500 (the seam is dropped outside `APP_ENV=test`).

### G05-03 (author: sre-devops-engineer, ST-076c; integrity check by senior-backend-engineer, ST-076b)
```
python3 scripts/ops/restore_drill.py --project racket-drill05 --flags on --json reports/restore-drill.json
jq '{rpo_h:.rpo_hours, rto_min:.rto_minutes, corrections_equal:.corrections.equal, objects_equal:.objects.equal}' reports/restore-drill.json
python3 scripts/ops/restore_drill.py --project racket-drill05b --flags on --plant-delete-correction \
  --json reports/restore-drill-planted.json  # expect rc 1
```

### G05-04 (author: senior-frontend-engineer, ST-079)
```
(cd web && for p in chromium webkit android-chrome; do
  PW_PROJECTS=$p npx playwright test --repeat-each 3 --grep @critical --output ../reports/pw-$p \
    --reporter json > ../reports/pw-$p.json; done)
python3 scripts/measure/browser_matrix.py reports/pw-*.json --require chromium,webkit,android-chrome
```
`webkit` evidence of record is the CI run on the head (local WebKit is not installed; never `playwright install`). Planted failure: `--require firefox` → rc 1 (missing project).

### G05-05 (author: senior-qa-engineer, ST-080)
```
(cd web && PW_PROJECTS=chromium,android-chrome npx playwright test e2e/sprint-05/fix-call-taps.spec.ts \
  --reporter json > ../reports/taps.json)
jq '[.suites[]..|.annotations?[]?|select(.type=="taps")|.description|tonumber]|max' reports/taps.json
```

### G05-06 (authors: senior-backend-engineer ST-077, ST-078d, ST-075a; senior-frontend-engineer ST-078e)
```
(cd backend && uv run pytest -q tests/integration/test_it_05_data_classification.py \
  tests/integration/test_it_05_no_store.py tests/integration/test_it_05_pii_labels.py --junitxml ../reports/g06-be.xml)
(cd web && PW_PROJECTS=chromium,webkit npx playwright test e2e/sprint-05/logout-hygiene.spec.ts && npm run test -- sw-cache)
python3 scripts/measure/junit_rate.py reports/g06-be.xml --include 'test_it_05_' \
  --require data_classification --require no_store --require pii_labels
```
Planted failure: add `--require missing_suite` → rc 1. `junit_rate.py` needs `--include`, and `--require` takes one regex per flag, so the old `--require data_classification,no_store,pii_labels` form failed even from the root (argparse rc 2). Planning dry-run of this block: §6.

### G05-07 (authors: security-privacy-engineer ST-078a-c assessment tool output; senior-backend-engineer ST-078d; senior-frontend-engineer ST-078e)
```
python3 docs/security/tools/asvs_status.py docs/security/asvs-l2-checklist.md --level 2 \
  --fail-on not-assessed,fail-without-owner,pass-without-evidence --json reports/asvs.json
(cd backend && uv run pytest -q tests/regression/test_bola_matrix.py)   # NFR-050.6: existing inventory test, PE-PLAN05-04
(cd backend && uv run pytest -q tests/integration/test_it_05_security_headers.py) && (cd web && npm run test -- hydration-lock)
```

### G05-08 (author: sre-devops-engineer, CI-TIERS-a/b, CI-DOC-CHECK, CI-RECON-ON-PR)
```
(cd infra && uv run pytest -q tests/test_merge_ready_tiers.py tests/test_doc_check.py tests/test_reconcile_on_pr.py)
gh api repos/nhuthuynh/racket-analytics/actions/runs?branch=main\&event=push\&per_page=1 --jq '.workflow_runs[0].id' \
  | xargs -I{} gh api repos/nhuthuynh/racket-analytics/actions/runs/{}/jobs --jq '.jobs[]|[.name,.conclusion]|@tsv' | grep -E 'doc-check|pr-policy|ci-gate'
```
Planted breaks (5): dangling path, unconfirmed ASB id, broken front matter, decisions-file "known gap" with no id, tier 1 fixture without QA.

### G05-09 (author: senior-qa-engineer with sre-devops-engineer; demo by senior-backend-engineer, QA-VERIFY04R5-01; rollback by sre-devops-engineer, ST-082)
```
python3 scripts/measure/live_goal.py demo --flags off --project racket-goal05-off --runs 2
python3 scripts/measure/live_goal.py demo --flags on  --project racket-goal05-on  --runs 2
(cd web && npx playwright test --repeat-each 3 --output ../reports/pw-full)
python3 scripts/measure/unofficial_notice.py --base-url https://localhost:3000 --families score-sheet,stats,plan,dashboard
python3 scripts/ops/rollback_drill.py --project racket-goal05-on --to-previous-tag
(cd backend && uv run pytest -q tests/integration/test_it_05_migration_roundtrip.py)
```

### G05-10 (author: senior-qa-engineer)
CI's NFR-073 integration form (the FIX-04-4a block, pinned) and the nightly mutation job, plus `uv run pytest -q tests/unit/dataset/test_rally_f1.py -p hypothesis --hypothesis-profile ci`.

### G05-11 (author: senior-qa-engineer, QA-FLOW-METRICS)
```
python3 scripts/measure/flow_metrics.py --repo nhuthuynh/racket-analytics --since 2026-11-03 \
  --decisions docs/sprints/05/decisions --json reports/flow05.json
```
Values go to the sprint report; only the "measured and complete" condition is a goal target.

### G05-12 (author: engineering-manager, EM-CLOSE-CHECKS)
```
python3 docs/sprints/05/close-checks/retro05_check.py --repo nhuthuynh/racket-analytics --status docs/sprints/05/status.json \
  --ledger docs/sprints/05/review-rounds.md --blockers docs/sprints/05/blockers.md
python3 scripts/measure/open_defects.py docs/sprints/05/review-rounds.md
for n in $(merged Sprint 5 PRs); do python3 scripts/measure/merged_verdict.py --pr $n --tiered; done
```

## 5. Not met: waiting on P-n (PO P12 option b; not goal metrics)

| Row | Item | Waits on | What the team prepares this sprint | How it is measured once supplied |
|---|---|---|---|---|
| S5-P9 | Moderated usability test, n ≥ 5 players on their own phones (NFR-036.1-.3) | **P9** (OQ-20 testers) | ST-083 kit (protocol, tasks, interim consent script, observation sheet), COACH-5 safety review, ST-080 (NFR-036.4) | Observation sheets tallied by `scripts/measure/usability_tally.py` (written when the session is booked) |
| S5-P16 | Legal review (NFR-070, US + AU) of the age, footage, consent and retention texts; tester footage question | **P16** | SEC-5 open-question list and ADR skeleton; flags default-off for real users | ADR accepted by the PO; interim wording removed |
| S5-P7 | Rulebook for official scoring and the side-out split | **P7** (OQ-01) | COACH-5 verification queue mapped to FR-nnn.Rk; "unofficial scoring" label (FR-055.R1) | `docs/domain/rules-verified.md` rows |
| S5-P15 | Human coach review of drills (`verified`) | **P15** | ST-081b drills at `coach-reviewed`; checklist rows | `jq` count of `verified` |
| S5-P8 | Budgets and storage quota (OQ-13); GPU for SPIKE-03 | **P8** | settings as interim values | settings hold PO values |
| S5-P11 | Footage bucket and consented footage for SPIKE-02/05/07 and gold set QD-GD-04 v1 data; NFR-006.6 | **P11** (OQ-06) | ST-084a tolerance ADR, ST-084b matcher | spike reports |
| S5-P6 | Screen-reader pass (NFR-027 b) on R1 screens | **P6** | axe, target and keyboard checks | `a11y_manual.py` tally |
| S5-P10 | Repository visibility | **P10** | nothing private in git | `repo_visibility.py` |
| S5-P17 | SLO commitment and error-budget policy acceptance (NFR-041.2, NFR-042.2, NFR-049.1) | **P17** (new) | ST-075c drafts | PO acceptance quoted in po-input |
| S5-P18 | R1 release-candidate sign-off (REL-1.4) | **P18** (new) | ST-082 release notes; the PM's readiness recommendation after VERIFY-05 | PO acceptance |
| S5-P19 | Residual-risk ADR for ASVS `Fail` rows and threat-note "Accepted residual" rows (NFR-050.9) | **P19** (new) | SEC-5 + ST-078a-c draft | ADR accepted by the PO |
| S5-P20 | Real-device iOS Safari and Android Chrome, current and previous major (NFR-024.4-.5; OQ-17) | **P20** (new) | ST-079 emulation evidence; a device checklist | device checklist tally |
| S5-S6 | Admin setting 6 (ADR 0053 part 2: draft upgrade PR) | **setting 6** | nothing | first draft upgrade PR |
| S5-CAL | NFR-045.5 quarterly drill cadence; 30-day SLO windows | calendar time | first drill and first window start | next quarter |

## 6. Dry-run rows (method authors, before VERIFY-05)

One row per metric, rc 0 on the real method plus the planted-failure rc, in the configuration it measures (ADR 0055 rule 2; retro 4 E4). Rows are added by each author's ticket PR (this file is not a shared status file; each PR adds only its own row). VERIFY-05 refuses to start while any metric has no rc 0 row.

| Metric | Author | Ticket | Date | Head | Command (as §4) | rc | Planted-failure rc |
|---|---|---|---|---|---|---|---|
| G05-01 | senior-backend-engineer | ST-074 | 2026-11-04 | `ea22fe1c` | the §4 G05-01 block: its `export`, `make up`, then the 3-run locust + verdict loop (`-t 8m`, `--min-window 300`). One deviation: `DOCKERHUB_REGISTRY=mirror.gcr.io` (Docker Hub answered 429). Default ports, all 3 runs, one stack; load average sampled each second (mean 3.2-3.8, max 6.0-7.3 on 4 CPUs: Locust, the stack and other lanes' test containers) | **0, 0, 0** (3 of 3): p95/p99 ms per run, match 63/140, 130/220, 96/190; score-sheet 67/140, 130/220, 100/190; dashboard 78/180, 150/240, 110/200; plan 65/140, 130/210, 95/170; 0 failures of 19,125 / 19,246 / 19,190; 50.08 / 49.97 / 49.93 RPS; windows 381 / 385 / 384 s (98 / 95 / 96 s excluded). Earlier failing runs are kept in `decisions/ST-074.md` ("Dry runs"): r1-1 (moved ports, second stack), QA runs 1-2 | 1 (`--p95-ms 1` on run 3's CSV: `FAIL` match, score-sheet, dashboard, plan) |
| G05-02 | sre-devops-engineer | ST-075c | | | | | |
| G05-03 | sre-devops-engineer | ST-076c | | | | | |
| G05-04 | senior-frontend-engineer | ST-079 | | | | | |
| G05-05 | senior-qa-engineer | ST-080 | | | | | |
| G05-06 | senior-backend-engineer | ST-078d | | | | | |
| G05-07 | security-privacy-engineer (tool) / senior-backend-engineer (tests) | ST-078c | | | | | |
| G05-08 | sre-devops-engineer | CI-TIERS-b | | | | | |
| G05-09 | senior-qa-engineer | QA-PIN-05 | | | | | |
| G05-10 | senior-qa-engineer | QA-PIN-05 | | | | | |
| G05-11 | senior-qa-engineer | QA-FLOW-METRICS | 2026-11-03 | `cf0088d5` | the §4 G05-11 command (`--json /tmp/claude-0/fm/flow05.json`; `SSL_CERT_FILE=/root/.ccr/ca-bundle.crt` for the agent proxy) | **1**, a real finding: "cost tables: 1 of 9 merged tickets" (QA-FLOWMETRICS-01, `decisions/QA-FLOW-METRICS.md`); the same command with `--pr-from 186 --pr-to 186` (PLAN-05 only) → 0, "measured, complete". Throughput 9, cycle time median 1.4 h / max 4.5 h, 0 WIP breaches from 1 stage-count line, CI 289.8 min | 2 (`GITHUB_API_URL=http://127.0.0.1:9`: "flow-metrics: unknown (GitHub could not be read ...)"); 1 (a merged ticket without a cost table, `test_script_exits_1_when_a_merged_ticket_has_no_cost_table`) |
| G05-12 | engineering-manager | EM-CLOSE-CHECKS | | | | | |
| G05-11 (planning dry-run) | engineering-manager | PLAN-05 | 2026-11-03 | `04c6a826` | `gh api 'repos/nhuthuynh/racket-analytics/pulls?state=closed&per_page=100'` (REST; the GraphQL form in working-agreement §10 returns 403 here) | 0 | n/a (tool not built) |
| G05-02 (planning dry-run, project name only) | engineering-manager | PLAN-05 | 2026-11-03 | `6c3ffcdd` | `docker compose -f infra/compose.yaml -p racket-obs05 up -d --no-deps web-tls`, then `COMPOSE_PROJECT_NAME=racket-obs05 make demo` (only web-tls running; the obs profile and `compose.fault-drill.yaml` do not exist yet) | 0 on the `cp web-tls` step (root.crt copied); the make rc is 2 only because the API is not running (`GET /dev/users: HTTP 502`) | 2 (`env -u COMPOSE_PROJECT_NAME make demo` → "the stack's web-tls service is not reachable; run 'make up' first"; the round 2 form of the method) |
| G05-12 (planning dry-run) | engineering-manager | PLAN-05 | 2026-11-03 | `04c6a826` | `python3 scripts/measure/open_defects.py docs/sprints/04/review-rounds.md` (Sprint 4 ledger; the Sprint 5 ledger does not exist yet) | 0 (`open 0`) | n/a |
| G05-06 (planning dry-run, paths and arguments; PE-PLAN05-07 / PLAN05-QA-08) | engineering-manager | PLAN-05 | 2026-11-03 | `244b8053` + the round 3 block text | the §4 G05-06 block, run from the repo root | step 1: 4 (pytest "file or directory not found": the three ITs are planned outputs of ST-077, ST-078d and ST-075a); `reports/g06-be.xml` was written at the root and the shell stayed at the root. Step 2: not run (`e2e/sprint-05/logout-hygiene.spec.ts` is an ST-078e output; `web/node_modules` is not installed in this worktree). Step 3 on that report: 1 (`selected 0`, all 3 `--require` patterns listed as missing, as expected before the tickets). Step 3 on a fixture report with the 3 ITs passing: **0** | 1 (`--require missing_suite`). The round 1-3 form: 2 from `web/` ("can't open file …/web/scripts/measure/junit_rate.py"), and 2 from the root too (argparse: `--include` is required) |
| G05-07 (tool dry-run, V1-V5; the G05-07 row stays ST-078c's) | security-privacy-engineer | ST-078a | 2026-11-05 | `68dd23f2` | the §4 `asvs_status.py` line with `--chapters V1-V5` (`--json` into the scratchpad) | **0**: V1-V5 53 Pass, 5 Fail (owner P19), 20 N/A, 0 not assessed, "0 problem(s)". The §4 line as written (all chapters) → **1**, "116 problem(s)", all `not-assessed` in V6-V8 and V11-V16 (ST-078b/c) | 1 (planted `Not assessed`, `Fail` without owner, `Pass` without evidence: scenarios in `tests/features/asvs_status.feature`) |
