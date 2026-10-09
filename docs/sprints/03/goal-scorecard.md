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
| G03-01 | **Goal works end to end, live (API, real time).** Runs of the full journey over https through the web origin, each as a fresh account. Every step of a run must pass:<br>1. magic-link sign-in; a doubles match; the 60 s fixture uploaded; "Video received";<br>2. the coach's worked example (14 rallies) tagged; after **each** tag the stats equal the reference for the rallies so far;<br>3. stats = reference for AN-01..AN-07 × 2 sides (k, n, value, Wilson bounds ±0.001, low-sample flag, by-player counts, run histogram, ending mix); `rules_version`, `metric_def_version` and the label "unofficial scoring (rules not yet verified)" present;<br>4. "Show me" for every metric and side with n > 0: ≤ 10 items, total = n, every item behind the metric; the first item's rally video answers Range with 206;<br>5. rally 3 corrected → stats equal the corrected reference;<br>6. a second account → 404 on stats and evidence;<br>7. DELETE the match → 404 on the match and its stats, gone from the list;<br>8. DELETE the account → the old session 401; signing in again with the same address gives an empty account | **5 of 5 runs pass (100%)** | `scripts/measure/live_stats.py --runs 5` | | | |
| G03-02 | **Real-time behaviour of the goal steps, live:** (a) tag → stats current, every tag of the 5 G03-01 runs (70 samples); (b) correction → stats current (5 samples, one per run); (c) DELETE match → hidden from the owner (match 404 and not listed), 5 samples | **(a) p95 ≤ 5,000 ms, n ≥ 70 (NFR-017 analogue); (b) p95 ≤ 5,000 ms, n ≥ 5; (c) p95 ≤ 60,000 ms, n ≥ 5 (NFR-066 a, ADR 0006)** | `live_stats.py` summary `tag_to_stats`, `correction_to_stats`, `delete_hidden` | | | |
| G03-03 | **Purge leaves nothing, live (NFR-066 b):** after the 5 runs, the purge job is run once on the stack; (a) rows in any public table whose `match_id`, `owner_id` or `account_id` column, or `matches.id` / `accounts.id`, holds a deleted match or account id; (b) rally video links taken before deletion and still within their TTL, fetched after the purge; (c) the purge job is scheduled at least daily in Compose (NFR-066 c) | **(a) 0 rows; (b) every checked link 404 (object gone), ≥ 1 link checked; (c) schedule present, interval ≤ 24 h** | `live_stats.py --psql … --purge-cmd …` summary `purge`; `grep` of the scheduler config (§4) | | | |
| G03-04 | **Integration-test pass rate** against real Postgres, the object store and Mailpit: (a) every Sprint 3 IT id IT-03-01..IT-03-14 plus the BOLA matrix with its inventory diff (NFR-051); (b) every Sprint 1 and Sprint 2 IT id (IT-01-01..13 except 11, IT-02-01..12 except 07), the upload-resume regression and the strict sandbox (no regression) | **(a) 100% passed, 0 failed, 0 skipped, every required id present; (b) 100% passed, every id present** | `pytest --junitxml`, `scripts/measure/junit_rate.py` | | | |
| G03-05 | **API read latency and availability, live:** open loop at 50 RPS for 60 s on GET stats, GET evidence (AN-01, side A) and GET match, for a match tagged with the worked example (NFR-010 "dashboard", NFR-041) | **p95 ≤ 300 ms, p99 ≤ 800 ms, availability ≥ 99.5%, 0 unexpected 4xx, achieved rate ≥ 47.5 RPS** | `scripts/measure/stats_latency.py --rps 50 --duration 60` | | | |
| G03-06 | **E2E pass rate,** Playwright in Chrome for Testing (ADR 0036) over https against the Compose stack, every spec, including:<br>- E2E-03-01 journey v2 (tag → stats = reference → Show me plays → delete match → gone);<br>- E2E-03-02 evidence crawl;<br>- E2E-03-03 definition shown, draft hidden, low-sample text;<br>- E2E-03-04 delete account;<br>- E2E-03-05 Full Tag (labeller tags and exports; player refused);<br>- E2E-03-06 keyboard-only and 320/360 px on stats and evidence;<br>- E2E-03-07 S-01 move offered only on the latest kept rally (C3-03);<br>- every Sprint 1 and Sprint 2 spec, root specs included (no regression) | **100% of non-skipped tests passed, 0 failed, every E2E-03 id present and not skipped; earlier skips ≤ 6, each naming its API binding; 0 flaky over 3 repeats of every spec (NFR-074)** | `playwright test` (junit, json), `junit_rate.py`, `--repeat-each=3`, `flaky_report.py` | | | |
| G03-07 | **Browser timings, live** (`web/e2e/sprint-03/timing.spec.ts`, ST-054; 20 samples each): (a) stats dashboard interactive, warm; (b) "Show me" rally → first video frame playing, 9/1.5 Mbit/s and 4× CPU (reference profile); (c) cumulative layout shift while the stats load (CLS × 1000) | **(a) p95 ≤ 2,000 ms (NFR-011); (b) p95 ≤ 1,500 ms (NFR-014); (c) p95 = 0 (NFR-039); each ≥ 20 samples** | `scripts/measure/pw_timings.py` on the timing JSON report | | | |
| G03-08 | **Metric correctness:**<br>(a) golden matches GS-AN-1 v1 (3 matches × every coach-reviewed metric × 2 sides) equal the coach's hand counts exactly (NFR-004), and the manifest check passes (FR-151, NFR-078);<br>(b) FR-101 examples and ADR 0005 thresholds (8/4, 20/10, 40/22, one game) as executable scenarios;<br>(c) FR-109 attribution conservation, property suite at ≥ 1,000 generated matches;<br>(d) metric dictionary: draft entries absent, a definition change bumps the version (FR-102);<br>(e) the coach's review record lists every shown entry as `coach-reviewed` with its QD-AN-03 evidence | **(a) 100% exact, 0 mismatches, manifest rc=0; (b) 100% passed; (c) 0 violations, ≥ 1,000 examples; (d) 100% passed; (e) every entry the API shows is `coach-reviewed` or `verified` in metric-dictionary §3** | `pytest -m golden_an`, `-m "analytics and scenario"`, `-m conservation`, `racket-manifest-check`, a `grep` | | | |
| G03-09 | **Full Tag and drill lint:** (a) IT-03-11 and E2E-03-05 (labeller only; consent required; export validates against `gold-label-schema` v1 with the tagged frame and player); (b) drill lint: the valid fixture library passes and each of the 5 FR-140 negative fixtures fails naming the drill and its reason; (c) the lint runs as a CI job on the PR | **(a) passed; (b) 1 pass + 5 named failures, 0 wrong verdicts; (c) the CI job exists and was green on the last run at the head** | `junit_rate.py` on the G03-04/G03-06 reports; `racket-drill-lint` (name per ST-053) on the fixtures; `actions_list` | | | |
| G03-10 | **Accessibility of the Sprint 3 screens** (stats dashboard D, evidence E, deletion X, Full Tag L) and every earlier family: (a) axe serious/critical (WCAG 2.2 AA tags) on every page an E2E test checks; (b) targets below 24×24 CSS px; (c) keyboard-only stats, evidence and Full Tag (E2E-03-05, E2E-03-06); (d) stats at 320 and 360 px with no sideways scrolling (NFR-034) | **(a) 0, with ≥ 1 axe check per family D, E, X, L and per earlier family; (b) 0; (c) passed; (d) passed** | From the G03-06 Playwright JSON report | | | |
| G03-11 | **Test strength, coverage and speed:** (a) backend changed lines against the Sprint 2 head `ce91984`; analytics line coverage; rules and aggregates; web unit; (b) mutation score on `sports/pickleball/rules` (gate) and on the starter-stats module (first gate); (c) differential oracle; (d) fast tests: domain suite (CI's `DOMAIN_TEST_PATHS`, which must include `tests/unit/analytics`), backend unit, integration | **(a) changed lines ≥ 85%; analytics ≥ 90% line (NFR-071); rules and aggregates ≥ 95% line / ≥ 90% branch; web ≥ 80% line; (b) rules ≥ 0.85; starter stats ≥ 0.80; (c) 100,000 sequences, 0 disagreements; (d) domain < 10 s, unit ≤ 60 s, integration < 10 min, all 0 failed (NFR-073)** | `pytest --cov`, `diff-cover`, `coverage report`, `vitest --coverage`, `mutation_score.py`, `tests.oracle.differential`, `run_with_budget.py` | | | |
| G03-12 | **Open defects:** blocker or major findings whose latest disposition is open in `docs/sprints/03/review-rounds.md` (which starts with the 14 carried Sprint 2 rows), plus open product-defect rows in `smoke.md` and `blockers.md` not yet in review-rounds, plus open GitHub issues labelled `bug` with `blocker` or `major` | **0** | `scripts/measure/open_defects.py`, GitHub issue search (§4) | | | |

**Overall:** the Sprint 3 goal is met only when all 12 rows are "yes". A row whose method could not run is "no", never "n/a" (fail closed, ADR 0014). `@needs-verification` results never count toward a Must FR (QD-QG-P5): metrics that read the provisional score sequence (AN-01, AN-02, AN-03, AN-05, AN-06) are reported on their own line in G03-08. Human-gated rows (sprint-03 §0.4) stay in G03-12 unless the PO chose option (b) in writing before the verifier runs.

**Status note (engineering-manager, review round 1, 2026-10-07; not a verifier result):** the goal is **not met**. The stats, evidence, delete-match and delete-account routes are not served at `15a7551` (openapi: no `/stats` or `/evidence` path; `/matches/{match_id}` and `/me` have only `get`), and `api-sprint-03.md` and `flows-sprint-03.md` do not exist. The pre-review smoke at `316a514` gives `live_stats.py` rc 1, runs passed 0/1 (QA-R1S3-06). G03-12 at this step: `open_defects.py` rc=1, open 9. Under PO P12 (b), C-06, SEC-RV3-01 and BLK-GOLD-01 are sprint-DoD rows (sprint-03 §9.1), not G03-12 rows.

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
  --purge-cmd "$DC exec -T api python -m racket.platform.purge --once" \
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
  $(for i in 01 02 03 04 05 06 07; do printf -- '--require E2E-03-%s ' $i; done) \
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
```

- Screen families D (dashboard), E (evidence), X (deletion), L (Full Tag) with the screen ids of `flows-sprint-03.md` (PD-1). E2E-03-05, E2E-03-06 and the 320/360 px cases must be among the passed cases of `e2e-rate.json`.
- The manual screen-reader pass (NFR-027 b, C3-06) is a human item; while open it counts in G03-12.

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
| G03-12 open defects | engineering-manager | | | | |
