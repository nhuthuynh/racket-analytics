# Sprint 4 goal scorecard

- **Written:** 2026-10-17 at Sprint 4 planning (ticket PLAN-04) by the engineering-manager, with the product-manager (goal wording, targets), principal-engineer (latency, determinism and contract assumptions), business-analyst (FR/NFR traceability) and senior-qa-engineer (test selection, fail-closed rules).
- **Why:** PO standing rule. A sprint is done only when its **goal is shown to work on a live local stack**, with every goal metric measured against its target. Unit tests alone never prove a goal. Human-only items are not goal metrics; they are the "not met: waiting on P-n" rows of §5 (PO P12 option b).
- **Verifier fills in:** `Actual`, `Met` (yes / no) and `Evidence` (exact command, stack head SHA, result line or report path). Nothing else in this file changes without a row in a ticket's `decisions/<ID>.md` (and, at the close, in `decision-log.md`).
- **Sources:** `docs/sprints/sprint-04.md` §1 (goal), §3 (tickets), §6 (IT ids), §8 (gates), §12 (demo); FR-003, FR-008, FR-009, FR-120..FR-124, FR-141, FR-160; NFR-005 (a), NFR-010, NFR-019, NFR-022, NFR-023, NFR-027, NFR-034, NFR-041, NFR-066, NFR-071, NFR-073, NFR-074; QD-PL-01..06, QD-DR-04/05, QD-QG-S7, QD §7; ADR 0003, 0005, 0006, 0014, 0029, 0033, 0037, 0044, 0047, 0050, 0051.
- **Harness:** `scripts/measure/` (standard-library Python). Sprint 4 adds `planlib.py` (an independent reference for weakness ranking and a QD-PL-01..04 grader) and `live_plan.py` (ticket QA-HARNESS-4a), and `live_privacy.py` (QA-HARNESS-4b), each written red first against the PE-4 contract and dry-run before the verifier (ADR 0033 rule 2). Until PE-4 merges, the route and field names below are the plan's assumptions; PE-4 updates this file's method column if a name changes (row in `decisions/PE-4.md`).
- **The reference is not the product.** `planlib` follows `docs/domain/weakness-catalogue.md` (COACH-4) and the QD-PL rules, and is pinned by tests to the coach's worked examples. If the coach changes the catalogue, `planlib` and its tests change with a TCR row before the verifier runs.

## 1. Sprint goal (sprint-04 §1)

1. A player can run the whole R1 journey on a local stack as a prototype: `make up` + `make demo` give a demo user with a match, score sheet, stats and a 2-week plan; a fresh user can do it by hand.
2. The plan is rules-only, deterministic and honest: weaknesses by rallies lost per game split serve/receive (ADR 0003; side-out part `@needs-verification`, P7); constraints QD-PL-01..03; every drill cites metric, value, n and evidence rallies; limited data says so; code-grader eval pass^3 = 100%.
3. A starter library of ≥ 20 drills passes lint and coverage in CI (content `needs-verification` until P15).
4. A player can mark a session done offline (synced, idempotent) and swap a drill with "Not for me".
5. R1 privacy and quotas behind default-off flags with interim wording: age confirmation and footage notice, retention, training-data consent, rate limit and storage quota; billing alert rules at 50/80/100%.
6. The Sprint 3 carry-over is closed first; CI green on `main` at the close; no blocker or major open.

## 2. Scorecard

| ID | What is measured | Target | Method (detail in §4) | Actual | Met | Evidence |
|---|---|---|---|---|---|---|
| G04-01 | **Prototype journey, live (API over https through the web origin).** Runs, each as a fresh account; every step must pass:<br>1. magic-link sign-in; a doubles match; the 60 s fixture uploaded by tus; "Video received";<br>2. the coach's worked example (14 rallies) tagged; score sheet returned with the "unofficial" label; stats equal the Sprint 3 reference;<br>3. `POST /me/plan` with preferences {1 player, 30 min/session, 3 sessions/week, equipment: wall, level intermediate} → 201;<br>4. weaknesses equal `planlib` (order, rallies lost on serve and on receive per game), unit `rallies_lost_per_game` and the side-out-unverified mark present;<br>5. plan: 2 weeks × 3 sessions; `planlib` grader passes QD-PL-01..03 (session ≤ 30 min, warm-up first, no drill > 40%, players ≤ 1, no ball machine, only reviewed drills);<br>6. QD-PL-04: every assignment's (metric, value, n) equals GET stats for Ivy's side and every cited rally id is in GET evidence of that metric;<br>7. QD-PL-06: limited-data note present with rallies = 14;<br>8. a session marked done twice with one `Idempotency-Key` → done once, version unchanged on replay;<br>9. "Not for me" on one assignment → a different drill, same metric, session still ≤ 30 min;<br>10. a second account → 404 on the plan, the session and the assignment | **5 of 5 runs pass (100%)** | `scripts/measure/live_plan.py --runs 5` | | | |
| G04-02 | **Plan timings, live:** (a) `POST /me/plan` request → 201 (NFR-019 rules-only), 4 generations per run × 5 runs; (b) mark done → `GET /me/plan` shows it done, 1 per run; (c) `GET /me/plan` open loop at 50 RPS for 60 s | **(a) p95 ≤ 5,000 ms, n ≥ 20; (b) p95 ≤ 1,000 ms, n ≥ 5; (c) p95 ≤ 300 ms, p99 ≤ 800 ms, availability ≥ 99.5%, achieved ≥ 47.5 RPS** | `live_plan.py` summary `generate`, `done_visible`; `live_plan.py --load --rps 50 --duration 60` | | | |
| G04-03 | **Weakness and plan correctness:** (a) weakness ranking equals the coach's hand count (catalogue worked examples) on the 3 golden matches GS-AN-1 × 2 sides and the FR-120 example; (b) Sprint 4 scenario suites (weakness_ranking, training_plan, drill_rationale, limited_data_plan, plan_follow_through, rules_only_plan_api) pass; (c) property: generated (preferences, library, stats) inputs → plans satisfy QD-PL-01..04; (d) determinism: the same input gives byte-identical plan JSON | **(a) 100% exact, 0 mismatches over 7 comparisons; (b) 100% passed, every feature present, 0 skipped; (c) 0 violations over ≥ 1,000 examples; (d) 3 of 3 identical, live and in unit** | `pytest -m "coaching and scenario"`, `-m weakness_golden`, `-m plan_property`; `live_plan.py --determinism 3`; `junit_rate.py` | | | |
| G04-04 | **Code-grader eval on rules-only plans (NFR-005 a; QD-QG-S7):** every eval case run 3 times; graders: drill exists and reviewed, metric cited with value and n, QD-PL-01..03 | **≥ 30 cases; pass^3 = 100% (every case passes all 3 runs, runs identical); CI step green at the head** | `cd backend && uv run racket-plan-eval --runs 3 --json …`; `actions_list` | | | |
| G04-05 | **Drill library (FR-141; QD-DR-04/05):** (a) drills with `review_status` `coach-reviewed` or `verified`, not deprecated; (b) lint; (c) coverage matrix over the COACH-4 targetable metrics × 3 levels, each cell ≥ 2 drills with ≥ 1 `players ≤ 2` and ≥ 1 without `ball_machine`; (d) the gap fixture fails naming its cell; (e) drills involving lobs retreating, diving or high-intensity footwork have `safety_notes`; (f) the CI jobs | **(a) ≥ 20; (b) 0 problems; (c) 0 empty cells; (d) rc 1 naming the cell; (e) 0 missing; (f) `drill-lint` (lint + coverage) green on the last run at the head** | `racket-drill-lint ../content/drills`; `racket-drill-coverage ../content/drills` and on `backend/tests/fixtures/drills-coverage-gap/`; `jq` count; `grep` for safety terms (§4); `actions_list` | | | |
| G04-06 | **The prototype runs locally from a fresh checkout:** in a new worktree of `main` with no `.local` state: `make up` → healthy; `make demo` → rc 0, prints the stats URL and the plan URL; GET the demo user's plan over https → 200 with ≥ 1 session and every assignment citing; `make demo` again → rc 0, same match count and same plan id; README checker; `make down` | **every step rc 0 on 1 fresh run; re-run idempotent (match count and plan id unchanged); `check_readme_quickstart.py` rc 0 incl. the prototype walkthrough items** | §4 G04-06 commands; `scripts/ci/check_readme_quickstart.py` | | | |
| G04-07 | **E2E pass rate,** Playwright in Chrome for Testing over https on the Compose stack: every spec incl. E2E-04-01 full journey (upload → Quick Tag → score sheet → stats → plan → why → Show me → done offline → swap), E2E-04-02 plan states, E2E-04-03 offline done survives reload, E2E-04-04 no-alternative swap, E2E-04-05 keyboard and 320/360 px, and every earlier spec; flag-on project E2E-04-06..08 on a stack started with `FEATURE_*=1` | **100% of non-skipped tests passed; every E2E-04-01..05 id present, not skipped; earlier skips ≤ 6, each naming its binding; 0 flaky over 3 repeats; flag-on project 100% (3 of 3 ids)** | `playwright test` (junit, json), `junit_rate.py`, `--repeat-each=3`, `flaky_report.py`; WebKit from CI | | | |
| G04-08 | **Accessibility of the Sprint 4 screens** (P plan, A age, R privacy settings, Q over-limit) and every earlier family: (a) axe serious/critical (WCAG 2.2 AA tags); (b) targets below 24×24 CSS px; (c) keyboard-only plan journey (E2E-04-05); (d) plan and settings at 320 and 360 px with no sideways scrolling | **(a) 0, with ≥ 1 axe check per family P, A, R, Q and per earlier family; (b) 0, with ≥ 1 target check per family P, A, R, Q; (c) passed; (d) passed** | From the G04-07 Playwright JSON report | | | |
| G04-09 | **Privacy behind flags, live (FR-003, FR-008, FR-009; interim):** (a) flags off: one G04-01 run passes and no age question, retention or consent field is served; flags on, 3 fresh accounts each: (b) under-18 answer → 0 new account rows and the interim reason; adult → account usable; (c) retention 30 days, purge run with `--now` = analysis + 31 days → review video object 404, stats, tags and plan 200, `review_video_delete_at` shown; (d) consent off → 0 of the account's matches in a built label set; opt in → included; revoke → 0 in the next build | **(a) pass; (b)-(d) 3 of 3 accounts pass every step** | `live_privacy.py --flags off --runs 1`; `live_privacy.py --flags on --runs 3 --psql … --purge-cmd …` | | | |
| G04-10 | **Quotas and billing alerts, live (FR-160, NFR-023, NFR-022):** flags on: (a) burst of 50 `POST /matches` in one hour → exactly 10 accepted, the rest 429 with `retry_at`; (b) an upload whose length passes the quota → refused before any byte is stored, body names usage and limit; object store bytes for the account unchanged; (c) flags off → today's behaviour; (d) billing rules: LLM provider and object store × 50/80/100% | **(a) 10 accepted, 40 refused, 0 accepted beyond the limit; (b) refused, 0 bytes stored; (c) pass; (d) 6 rules present, rule test passes: each fires at its threshold and not at 1% below** | `live_privacy.py --quotas`; `promtool test rules` (or the ST-073 evaluator) per §4 | | | |
| G04-11 | **Test strength, coverage and speed:** (a) every IT-04 id (IT-04-01..17) plus the BOLA matrix with plan routes; every earlier IT id (no regression), strict sandbox; (b) changed backend lines against `c170ef0`; `racket.coaching` line coverage; web unit; (c) mutation on `coaching/plan` + `coaching/weakness`; rules; (d) budgets: domain suite (incl. `tests/unit/coaching`), backend unit, integration | **(a) 100% passed, 0 failed, 0 skipped, every id present; (b) changed lines ≥ 85%, coaching ≥ 90% line, web ≥ 80% line; (c) coaching ≥ 0.80, rules ≥ 0.85; (d) domain < 10 s, unit ≤ 60 s, integration < 10 min, all 0 failed** | `pytest --junitxml`, `junit_rate.py`, `pytest --cov`, `diff-cover`, `vitest --coverage`, `mutation_score.py`, `run_with_budget.py` | | | |
| G04-12 | **CI, merge discipline and open defects:** (a) jobs of the last `ci.yml` run on the close head of `main` (push), incl. `ci-gate`, `drill-lint` with coverage, plan eval, `Red:` check, Locust stats/evidence gate; (b) every merged Sprint 4 ticket PR: latest verdicts of the principal-engineer and of a `senior-*` role APPROVE on the merged head; (c) open blocker/major rows in `docs/sprints/03/review-rounds.md` and `docs/sprints/04/review-rounds.md`, plus open product-defect rows in `blockers.md`, plus open GitHub issues labelled `bug` with `blocker` or `major` | **(a) 100% of jobs success or allowed PR-only skip; (b) 100% of PRs (`merged_verdict.py` rc 0 for each); (c) 0** | `actions_list` / `list_workflow_jobs`; `merged_verdict.py --pr N --role principal-engineer --role <senior role>` per PR; `open_defects.py` on both ledgers; `search_issues` | | | |

**Overall:** the Sprint 4 goal is met only when all 12 rows are "yes". A row whose method could not run is "no", never "n/a" (fail closed, ADR 0014). `@needs-verification` results (weakness side-out part, drill content) never count toward a Must FR as verified (QD-QG-P5); they count here as built and measured, and their verification is the P15 row of §5 and, for the side-out part, the coach's check after OQ-01 (P7).

**Status at planning (engineering-manager, 2026-10-17; not a verifier result):** met 0 / 12. Nothing of the spine exists yet; `main` CI is green (run 39015002522 at `c170ef0`); the Sprint 3 ledger has 2 open rows (`open_defects.py docs/sprints/03/review-rounds.md` → rc 1, `open 2`).

## 3. Rules for the verifier

1. **Live stack, isolated (ADR 0030, ADR 0033).** One recorded head (`git rev-parse HEAD`) of `main`; a fresh-volume Compose project of your own with remapped host ports; your own `RA_DEV_STATE`; `bash scripts/disk-precheck.sh` first (≥ 10 GB free; below the floor the live scripts exit 2 and the row is "no"). Hold `flock .local/evidence-e2e.lock` for Compose up/down and every Playwright evidence run. Tear down with `down -v --rmi local`. Never reuse or remove another agent's stack, database or images.
2. **Flags.** G04-01..G04-08 and G04-11 run with every `FEATURE_*` off (the default). G04-09/G04-10 (flags on) and the E2E flag-on project run on a separate stack start with `FEATURE_AGE_GATE=1 FEATURE_RETENTION_SETTING=1 FEATURE_TRAINING_CONSENT=1 FEATURE_QUOTAS=1`.
3. **Fail closed.** A skipped test counts as not passed except named allowed skips; no selected test or a missing id → "no" (`junit_rate.py` exits 1).
4. **No edits to make a row pass.** A test change needs a TCR row decided by QA; a product defect goes to its owner as an Open row in `docs/sprints/04/review-rounds.md` (ledger id format, ADR 0050 rule 5).
5. **Evidence** is the exact command, the head SHA and the result line. Reports under `reports/goal04/` (git-ignored).
6. **Dry-run first (ADR 0033 rule 2).** Each method author runs their method end to end on an isolated stack and records the rc in their ticket's decisions file before VERIFY-04 starts.
7. **One round at a time; its PR merges before the next round** (ADR 0047 rule 1, ADR 0050 rule 4).

## 4. Methods

Common setup (each verifier, own names and ports):

```bash
H=$(git rev-parse HEAD); GOAL=$PWD/reports/goal04; mkdir -p "$GOAL"
bash scripts/disk-precheck.sh
export COMPOSE_PROJECT_NAME=racket-goal04 RA_DEV_STATE="$PWD/.local/goal04"
DC="docker compose -f infra/compose.yaml --env-file infra/.env"
$DC up -d --build --wait
$DC cp web-tls:/data/caddy/pki/authorities/local/root.crt "$GOAL/ca.crt"
```

- **G04-01, G04-02, G04-03 (d):** `python3 scripts/measure/live_plan.py --base-url https://localhost:43000 --cacert "$GOAL/ca.crt" --mailpit http://127.0.0.1:48025 --runs 5 --determinism 3 --json "$GOAL/live-plan.json"` → rc 0; `jq '.runs_passed, .summary' "$GOAL/live-plan.json"`. Load: `live_plan.py … --load --rps 50 --duration 60 --json "$GOAL/plan-load.json"`.
- **G04-03 (a)-(c):** `cd backend && uv run pytest -q -m "coaching and scenario" --junitxml "$GOAL/coaching-scenarios.xml"`; `-m weakness_golden`; `-m plan_property`; `cd .. && python3 scripts/measure/junit_rate.py --include '.' $(for f in weakness_ranking training_plan drill_rationale limited_data_plan plan_follow_through rules_only_plan_api; do printf -- '--require %s ' "$f"; done) --json "$GOAL/coaching-scenarios-rate.json" "$GOAL/coaching-scenarios.xml"` → rc 0 (no `--allow-skips`: a skipped scenario is not passed; one `--require` per feature, because `--require` is one regex per flag and a comma-joined list never matches). The golden and property runs write `--junitxml` too and are checked by marker: `--include '.' --require-marker weakness_golden` (9 tests: the 7 comparisons plus the metric dictionary example × 2 sides) and `--include '.' --require-marker plan_property` (1 test, 1,000 examples) → rc 0. `--require` is a regex over test ids and a marker is not in a test id, so `--require weakness_golden` fails closed on a passing run (FIX-04-2c, `decisions/FIX-04-2c.md`); the coaching unit tests record their markers as the JUnit property `markers` (`backend/tests/unit/coaching/conftest.py`).
- **G04-04:** `cd backend && uv run racket-plan-eval --runs 3 --json "$GOAL/plan-eval.json"` → rc 0; `jq '.cases, .pass_k'`; CI step from `list_workflow_jobs` of the head run.
- **G04-05:** `cd backend && uv run racket-drill-lint ../content/drills` → `ok, 0 problem(s)`; `uv run racket-drill-coverage ../content/drills` → rc 0 and the matrix; `uv run racket-drill-coverage tests/fixtures/drills-coverage-gap` → rc 1 naming the cell; `jq -s '[.[] | select((.review_status=="coach-reviewed" or .review_status=="verified") and (has("deprecated_by")|not))] | length' $(ls -d ../content/drills/*/ | while read d; do ls "$d"v*.json | sort -V | tail -1; done)` → ≥ 20; safety: `grep -liE 'lob|div(e|ing)|sprint|footwork' ../content/drills/*/v*.json | xargs jq -r 'select(.safety_notes=="") | .id'` → empty.
- **G04-06:** `git -C <repo> worktree add /home/user/wt/goal04-fresh "$H"`; in it: `make up` → rc 0; `make demo` → rc 0 (stdout has `/matches/` stats URL and `/plan`); `curl --cacert … -b <Ivy cookie> https://localhost:3000/api/me/plan` → 200, `jq '.sessions|length'` ≥ 1, every assignment has `citation.metric_id`, `value`, `n`, `rally_ids`; `make demo` again → rc 0, same plan id and match count; `python3 scripts/ci/check_readme_quickstart.py --repo . --readme README.md` → rc 0, `readme-quickstart: ok` (the script takes `--repo`/`--readme`, no positional argument); `make down` → rc 0; remove the worktree.
- **G04-07, G04-08:** the forms of Sprint 3 §4 G03-06 (flags as the scripts define them: `junit_rate.py` takes `--include` (required), `--require` once per regex and `--allow-skips` with no value; `flaky_report.py` takes `--out` and the run files):

  ```bash
  cd web
  flock ../.local/evidence-e2e.lock env PW_CHROMIUM_CHANNEL=chrome MAILPIT_API_URL=$MAILPIT PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers \
    BASE_URL=$WEB PW_PROJECTS=chromium \
    PLAYWRIGHT_JUNIT_OUTPUT_NAME="$GOAL/e2e.xml" PLAYWRIGHT_JSON_OUTPUT_NAME="$GOAL/e2e.json" \
    pnpm exec playwright test --workers=1 --output "$GOAL/pw-out" --reporter=line,junit,json; echo rc=$?
  cd ..
  # Sprint 4 ids: present and not skipped (separate run without --allow-skips)
  python3 scripts/measure/junit_rate.py --include 'E2E-04-0[1-5]' \
    $(for i in 01 02 03 04 05; do printf -- '--require E2E-04-%s ' $i; done) \
    --json "$GOAL/e2e-04-rate.json" "$GOAL/e2e.xml"; echo rc=$?
  # every spec, earlier skips allowed only as named below
  python3 scripts/measure/junit_rate.py --include '.' --allow-skips \
    $(for i in 01 02 03 04 05; do printf -- '--require E2E-04-%s ' $i; done) \
    $(for i in 01 02 03 04 05 06 07 08 09; do printf -- '--require E2E-03-%s ' $i; done) \
    $(for i in 01 02 03 04 05 06; do printf -- '--require E2E-02-%s ' $i; done) \
    --require 'E2E-01-02' --require 'E2E-01-03' --require 'walking-skeleton|walking skeleton' \
    --json "$GOAL/e2e-rate.json" "$GOAL/e2e.xml"; echo rc=$?
  jq '.skipped' "$GOAL/e2e-rate.json"    # must be <= 6 (the cap is checked here; --allow-skips takes no number)
  jq -r '[.. | objects | select(has("annotations")) | .annotations[]? | select(.type=="skip") | .description] | unique | .[]' "$GOAL/e2e.json"   # each reason names its API binding
  (cd web && flock ../.local/evidence-e2e.lock env PW_CHROMIUM_CHANNEL=chrome MAILPIT_API_URL=$MAILPIT PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers \
    BASE_URL=$WEB PW_PROJECTS=chromium PLAYWRIGHT_JUNIT_OUTPUT_NAME="$GOAL/e2e-repeat.xml" \
    pnpm exec playwright test --repeat-each=3 --workers=1 --output "$GOAL/pw-out-repeat" --reporter=line,junit)
  python3 scripts/ci/flaky_report.py --fail-on-flaky --out "$GOAL/flaky.md" "$GOAL/e2e.xml" "$GOAL/e2e-repeat.xml"; echo rc=$?
  rm -rf "$GOAL/pw-out-repeat"   # disk floor (Sprint 3 VR3-S3-03)
  # flag-on stack (rule 2): same env, PW_PROJECTS=flags-on, junit to "$GOAL/e2e-flags.xml", then
  python3 scripts/measure/junit_rate.py --include 'E2E-04-0[6-8]' \
    --require E2E-04-06 --require E2E-04-07 --require E2E-04-08 \
    --json "$GOAL/e2e-flags-rate.json" "$GOAL/e2e-flags.xml"; echo rc=$?
  ```

  Pass for G04-07: each `junit_rate.py` rc 0, `skipped` ≤ 6 in `e2e-rate.json` with every printed reason naming its binding, `flaky_report.py` rc 0. G04-08: axe and target attachments counted from `e2e.json` as in Sprint 3 G03-10 (families P, A, R, Q plus every earlier family). The project name `flags-on` and the env switch follow PE-4; a rename is a row in `decisions/PE-4.md`.
- **G04-09, G04-10:** `python3 scripts/measure/live_privacy.py --flags off --runs 1 …`; restart with the four flags on; `live_privacy.py --flags on --runs 3 --psql "$DC exec -T postgres psql -U racket racket" --purge-cmd "$DC exec -T purge python -m racket.platform.purge --once --now-offset-days 31" --quotas --json "$GOAL/live-privacy.json"` → rc 0. Rules: `docker run --rm -v "$PWD/infra/observability:/w" mirror.gcr.io/prom/prometheus:<pinned> promtool test rules /w/alerts/billing.test.yml` (or the ST-073 evaluator named in its decisions file) → `SUCCESS`.
- **G04-11:** as Sprint 3 §4 G03-11 (same pytest, `diff-cover`, `vitest` and `run_with_budget.py` lines; `$DOMAIN` must include `tests/unit/coaching`), with `--compare-branch=c170ef0` and these changes:

  ```bash
  (cd backend && uv run coverage report --data-file=.coverage --include='src/racket/coaching/*' --fail-under=90); echo rc=$?
  cd backend
  mv mutants "$GOAL/mutants-stale" 2>/dev/null || true
  env -u APP_ENV uv run --with mutmut==3.8.0 python ../scripts/ci/mutation_score.py --project . \
    --target src/racket/coaching/plan --tests tests/unit/coaching --min-score 0.80 --out "$GOAL/mutation-plan.json"; echo rc=$?
  mv mutants "$GOAL/mutants-plan" 2>/dev/null || true
  env -u APP_ENV uv run --with mutmut==3.8.0 python ../scripts/ci/mutation_score.py --project . \
    --target src/racket/coaching/weakness --tests tests/unit/coaching --min-score 0.80 --out "$GOAL/mutation-weakness.json"; echo rc=$?
  mv mutants "$GOAL/mutants-weakness" 2>/dev/null || true
  env -u APP_ENV uv run --with mutmut==3.8.0 python ../scripts/ci/mutation_score.py --project . \
    --target src/racket/sports/pickleball/rules --tests tests/unit/sports \
    --ignore tests/unit/sports/pickleball/test_rules_static.py --min-score 0.85 --out "$GOAL/mutation-rules.json"; echo rc=$?
  rm -rf "$GOAL"/mutants-*   # disk floor (VR3-S3-03)
  cd ..
  ```

  `mutation_score.py` takes `--target` (a path under `--project`) and `--out`, both required, and fails closed on a missing target. `--target src/racket/coaching/weakness` follows ST-055's dirs (`weakness*`); if ST-055 ships `weakness.py`, the method author sets `--target src/racket/coaching/weakness.py` with a row in `decisions/ST-055.md` before the dry-run. Any doc-sync test that reads files outside `backend/` gets an `--ignore` (Sprint 3 VR1-S3-01). (a) uses `junit_rate.py --include 'test_it_04_|test_bola_matrix' $(for i in 01 02 03 04 05 06 07 08 09 10 11 12 13 14 15 16 17; do printf -- '--require test_it_04_%s ' $i; done)` plus the Sprint 3 earlier-id call extended with `test_it_03_`.
- **G04-12:** `actions_list list_workflow_runs ci.yml branch=main` → the run at `$H`; `list_workflow_jobs` → every job; for each Sprint 4 ticket PR `python3 scripts/measure/merged_verdict.py --repo nhuthuynh/racket-analytics --pr N --role principal-engineer --role <its senior reviewer>` → rc 0; `python3 scripts/measure/open_defects.py docs/sprints/03/review-rounds.md docs/sprints/04/review-rounds.md` → rc 0, `open 0`; `search_issues is:open label:bug` → 0 blocker/major.

## 5. Not met: waiting on P-n (PO P12 option b; not goal metrics)

| Row | Item | Waits on | Status | How it is measured once supplied |
|---|---|---|---|---|
| S4-DoD-P15 | A human coach reviews the ≥ 20 starter drills; reviewed drills move to `verified` | P15 | not met: waiting on P15 | `jq` count of `review_status == "verified"` = drill count; `@needs-verification` removed from `drill_coverage.feature` by a TCR row |
| S4-DoD-P16 | Legal review (NFR-070, US + AU) of the age wording and footage notice (OQ-05), the consent text (OQ-06) and the retention windows (OQ-07). The values are PO-accepted (ADR 0023) and are not re-asked | P16 | not met: waiting on P16 | The review is an ADR (NFR-070); each text or window it changes is a config or wording change plus a TCR row; "interim" removed from `interim-wording-sprint-04.md` |
| S4-DoD-P7 | The coach verifies the side-out rule behind the serve/receive split of the weakness ranking (OQ-08's open part, ADR 0003; needs the OQ-01 rulebook) | P7 | not met: waiting on P7 | Row in `docs/domain/rules-verified.md`; `@needs-verification` removed from `weakness_ranking.feature` by a TCR row; the API's side-out-unverified mark cleared |
| S4-DoD-P8 | Storage quota size and monthly budgets for the billing alerts (OQ-13); GPU budget (SPIKE-03) | P8 | not met: waiting on P8 | The settings hold PO values; ADR 0051 rule 4 note updated |
| S4-DoD-P6 | Screen-reader pass (VoiceOver, TalkBack) of Sprint 1-4 screens (NFR-027 b) | P6 | not met: waiting on P6 | `scripts/measure/a11y_manual.py` tally |
| S4-DoD-P10 | Repository visibility (GitHub reports public) | P10 | not met: waiting on P10 | `scripts/measure/repo_visibility.py` |
| S4-DoD-P11 | Footage bucket provider (gates SPIKE-02/05 and Full Tag on real footage) | P11 | not met: waiting on P11 | `scripts/measure/footage_bucket.py` |

## 6. Dry-run rows (method authors, before VERIFY-04)

| Metric | Author | Date | Head | Command | rc |
|---|---|---|---|---|---|
| G04-01, G04-02, G04-03 (a, d) | senior-qa-engineer | 2026-10-17 | `64b8f08` (no stack: plan routes not on `main`) | `python3 scripts/measure/live_plan.py --base-url https://localhost:3000 --runs 5 --determinism 3 --json …` (red against PE-4; re-run on an isolated stack before VERIFY-04, `decisions/QA-HARNESS-4a.md`) | 2 |
