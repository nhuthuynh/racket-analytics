# Sprint 1 goal scorecard

- **Written:** 2026-10-05 by engineering-manager, with product-manager (goal wording, targets), principal-engineer (performance and engine methods), business-analyst (FR/NFR traceability) and senior-qa-engineer (test selection, fail-closed rules).
- **Why:** PO standing rule. A sprint is done only when its **goal is shown to work on a live local stack**, with every goal metric measured against its target. Unit tests alone never prove a goal.
- **Verifier fills in:** `Actual`, `Met` (yes / no) and `Evidence` (exact command, stack head SHA, result line or report path). Nothing else in this file changes without a decision-log row.
- **Sources:**
  - `docs/sprints/sprint-01.md` §1 (goal), §6 (IT and E2E ids), §8 (gates), §12 (demo) and §14.4 (NFR measures);
  - `docs/requirements/non-functional-requirements.md`;
  - ADR 0009, ADR 0019, ADR 0023, ADR 0029 and ADR 0030;
  - retro 1 actions A2 and A5 (isolated evidence, disk check).
- **Harness:** `scripts/measure/`, which is standard-library Python. Its tests are in `infra/tests/test_measure_scripts.py` (`cd infra && uv run pytest -q tests/test_measure_scripts.py`).

## 1. Sprint goal (sprint-01 §1)

1. A player signs in with an emailed link (no password). Signing out leaves nothing behind on the device.
2. A player reads the capture guide and sets up a doubles or singles match with nicknames. There is one question per page, and errors are summarised at the top.
3. A player uploads a multi-GB phone video. The upload survives a dropped connection and a closed tab. Files that are not real videos, too large or too long are refused with a clear reason.
4. The scoring engine is a pure, configurable function, built test-first. Its mechanics pass. The provisional side-out doubles and fault tables run as `@needs-verification` under `PROVISIONAL-UNVERIFIED` (ADR 0009, ADR 0023: no rulebook yet, so the score sheet says "unofficial"). The property suite and the differential oracle are green.

## 2. Scorecard

| ID | What is measured | Target | Method (detail in §4) | Actual | Met | Evidence |
|---|---|---|---|---|---|---|
| G01-01 | **Goal works end to end, live.** Runs of the full API journey over https through the web origin, each as a fresh account. One run covers the following steps, and every step must pass:<br>1. magic link via Mailpit, then exchange;<br>2. `GET /me`;<br>3. a doubles match with 4 nicknames and one "me";<br>4. tus upload with a connection drop at ≥ 40% and a resume from the HEAD offset;<br>5. a damaged chunk refused with 460 and the offset kept;<br>6. upload to the end;<br>7. "Video received" with probed facts;<br>8. a 12 GB `Upload-Length` refused with 413, and a PDF named `.mp4` refused with 415;<br>9. sign-out, after which the old session gets 401 | **5 of 5 runs pass (100%)** | `scripts/measure/live_goal.py --runs 5` | | | |
| G01-02 | **Integration-test pass rate:** (a) every Sprint 1 IT id, IT-01-01..IT-01-13, against real Postgres, the object store and Mailpit, plus the Compose worker sandbox for IT-01-10's no-network part; (b) the upload-resume and upload-validation regression suites | **(a) 100% passed, 0 failed, 0 skipped, 13 of 13 ids present; (b) 100% passed** | `pytest --junitxml` and `scripts/measure/junit_rate.py` | | | |
| G01-03 | **E2E journey pass rate,** Playwright Chromium over https against the Compose stack. All specs, including:<br>- E2E-01-01 (the walking skeleton plus first run and guide);<br>- E2E-01-02 (network cut at about 40%);<br>- E2E-01-03 (keyboard-only setup);<br>- sign-out;<br>- validation | **100% of non-skipped tests passed, 0 failed, ≤ 6 skipped (each names its API binding); 0 flaky over 3 repeats (NFR-074)** | `playwright test` (junit) and `junit_rate.py --allow-skips`; then `--repeat-each=3` | | | |
| G01-04 | **API read latency and availability, live:** an open loop at 50 RPS for 60 s on `GET /matches/{id}`, `GET /matches` and `GET /me` (NFR-010, NFR-041) | **p95 ≤ 300 ms, p99 ≤ 800 ms, availability ≥ 99.5%, 0 unexpected 4xx, achieved rate ≥ 47.5 RPS** | `scripts/measure/api_latency.py --rps 50 --duration 60` | | | |
| G01-05 | **Upload throughput, live:** sustained ingest of a ≥ 1 GB valid 1080p60 H.264 file through the https web origin, in 8 MiB chunks (ADR 0019), with sha256 `Upload-Checksum` on every chunk (NFR-016b) | **≥ 50 Mbit/s, and the final offset equals the file length** | `make_large_fixture.sh`, then `live_goal.py --file <1 GB>` | | | |
| G01-06 | **Real-time latency of the goal steps,** p95 over the 5 G01-01 runs: (a) from the link request to a signed-in session, including email delivery by the mailer worker; (b) from the final byte to "Video received" with facts, for the 60 s fixture | **(a) ≤ 10 s; (b) ≤ 30 s** (judgment, decision-log 2026-10-05) | From the G01-01 JSON: `sign_in_p95_s`, `final_byte_to_facts_p95_s` | | | |
| G01-07 | **Scoring correctness:**<br>- Ready mechanics, §7.7;<br>- match structure M-01..M-08;<br>- property suite P1-P8 at ≥ 1,000 sequences per scoring system (Hypothesis profile `ci`);<br>- the provisional golden rows SOD-01..12, SOD-16 and F-01..06, reported separately as `@needs-verification` | **100% of scoring tests passed, 0 failed (P3 skip allowed: FR-043); 100% of `needs_verification` cases passed and listed separately (≥ 19 rows); suite time ≤ 90 s** | `pytest -m "scoring and not nightly"` and `-m "scoring and needs_verification"`, with junit and `junit_rate.py` | | | |
| G01-08 | **Independent engine checks:**<br>- differential oracle P9, production engine against the QA oracle (NFR-002b);<br>- mutation score on `sports/pickleball/rules` (NFR-072; baseline this sprint, gated from Sprint 2) | **Oracle: 100,000 sequences, 0 disagreements. Mutation: baseline recorded as a number; ≥ 85% is reported but not gated** | `python -m tests.oracle.differential --sequences 100000`; `scripts/ci/mutation_score.py` | | | |
| G01-09 | **Coverage (NFR-071):**<br>- backend changed lines against `main` (the Sprint 0 close, `2b9c6ca`);<br>- rules engine and aggregates (`sports/pickleball/rules`, `matches/match_state.py`, `matches/participants.py`);<br>- web unit | **Backend changed lines ≥ 85%. Rules and aggregates ≥ 95% line and ≥ 90% branch. Web ≥ 80% line** | `pytest --cov`, then `diff-cover`, `coverage report` and `vitest --coverage` | | | |
| G01-10 | **Accessibility on Sprint 1 screens:**<br>- axe serious and critical violations (WCAG 2.2 AA tags) on every page an E2E test checks;<br>- tap targets below 24×24 CSS px;<br>- keyboard-only setup (NFR-027, NFR-028, NFR-034) | **0 serious/critical axe violations, with ≥ 1 axe check per Sprint 1 screen family (A, F/G, Q, U, M); 0 targets below 24×24; E2E-01-03 passes** | From the G01-03 Playwright JSON report | | | |
| G01-11 | **Open defects:** blocking or major findings whose latest disposition is "Open" (ADR 0030), plus open GitHub issues labelled `bug` with `blocker` or `major` | **0** | `review-rounds.md` count and GitHub issue search (§4) | | | |
| G01-12 | **Fast tests (NFR-073):**<br>- the domain unit suite;<br>- the whole backend unit suite | **Domain < 10 s; backend unit ≤ 60 s; both 0 failed** | `scripts/ci/run_with_budget.py` | | | |

**Overall:** the sprint goal is met only when all 12 rows are "yes". A row whose method could not run is "no", never "n/a" (fail closed, ADR 0014).

**Verification status (engineering-manager, 2026-10-05, review round 1 after close; PE-R1-S1-02, QA-V1-04):**

- **The Sprint 1 goal is not demonstrated, so Sprint 1 is not done** (PO standing rule). No verifier has filled the table at any head; the empty cells above are not a pass.
- The table is filled only by the verifier (senior-qa-engineer) from one isolated run at one recorded head, after the round-1 fixes land (§3). The EM does not copy reviewer numbers into it.
- Already known "no" at `488d574` from the reviewers' isolated runs: G01-03 (1 flaky test, QA-V1-04), G01-08 (no mutation score, PE-R1-S1-01) and G01-11 (24 open blocker or major findings by `open_defects.py`; GitHub bug issues 0). Supporting only: oracle `--sequences 100000` → `disagreements 0, passed true` (PE-R1-S1-02).
- Method fixes in this round: G01-02 (strict sandbox file only in the Compose-env command, QA-V1-05), G01-09 (`and not nightly`, rc checked, QA-V1-06), G01-11 (`open_defects.py`, QA-V1-07). Decision-log rows 2026-10-05.

## 3. Rules for the verifier

1. **Live stack, isolated (ADR 0030; retro 1 A5).**
   - Run everything at one recorded head (`git rev-parse HEAD`), on a fresh-volume Compose project of your own and an `RA_DEV_STATE` of your own.
   - Check the disk first (`df -h /`, ≥ 10 GB free).
   - Never reuse another agent's stack or database.
2. **Fail closed.**
   - A skipped test counts as not passed, except where a row allows named skips.
   - If no test was selected, or a required id is missing, the row is "no". `junit_rate.py` exits 1 in both cases.
3. **No edits to make a row pass.**
   - A test change needs a `test-change-requests.md` row decided by QA.
   - A product defect goes to its owner, routed as in working-agreement 1a.
4. **Evidence** is the exact command, the head SHA and the result line. Put reports under `reports/goal/` (git-ignored scratch) and quote the numbers in the table.
5. `@needs-verification` results are never counted toward a Must FR (QD-QG-P5, ADR 0009). G01-07 reports them on their own line.

## 4. Methods (exact commands)

### 4.0 Stack under test (shared by G01-01, G01-03 to G01-06 and G01-10)

```bash
cd /home/user/racket-analytics
git rev-parse HEAD; df -h /                        # record both; need >= 10 GB free
export RA_DEV_STATE=$PWD/.local/goal01 GOAL=$PWD/reports/goal; mkdir -p "$RA_DEV_STATE" "$GOAL"
cp infra/env.example "$RA_DEV_STATE/goal.env"
sed -i 's#^DOCKERHUB_REGISTRY=.*#DOCKERHUB_REGISTRY=mirror.gcr.io#' "$RA_DEV_STATE/goal.env"
printf 'AUTH_LINK_LIMIT_PER_IP=1000\nAUTH_EXCHANGE_LIMIT_PER_IP=1000\n' >> "$RA_DEV_STATE/goal.env"   # as the CI E2E job
docker ps --format '{{.Names}} {{.Ports}}'          # host ports 3000/8000/8025/1025/5432/8333 must be free
DC="docker compose -p racket-goal01 -f infra/compose.yaml --env-file $RA_DEV_STATE/goal.env"
$DC down -v --remove-orphans; $DC up -d --build --wait            # expect rc=0, all services healthy
$DC cp web-tls:/data/caddy/pki/authorities/local/root.crt "$RA_DEV_STATE/root.crt"
curl -sS -o /dev/null -w '%{http_code}\n' http://localhost:3000/                       # 400 (plain http closed)
curl --cacert "$RA_DEV_STATE/root.crt" -sS -o /dev/null -w '%{http_code}\n' https://localhost:3000/   # 200
```

Start `dockerd` first if `docker info` fails. Images come through `mirror.gcr.io`.

### G01-01: live goal journey (and G01-06)

```bash
python3 scripts/measure/live_goal.py --api https://localhost:3000/api --origin https://localhost:3000 \
  --mailpit http://127.0.0.1:8025 --cacert "$RA_DEV_STATE/root.crt" \
  --file fixtures/clips/synthetic-60s/clip.mp4 --runs 5 --json "$GOAL/live-goal.json"; echo rc=$?
```

- **Actual:** `runs_passed`/`runs` from the summary. The row is met only when the result is `rc=0` and 5/5.
- **G01-06:** `sign_in_p95_s` and `final_byte_to_facts_p95_s` from the same summary.
- **Failures:** a failing step is shown by `runs[i].steps.<step>.ok == false` together with its status code.

**Browser companion (counts in G01-03):** the demo steps in sprint-01 §12 are covered by:
- `walking-skeleton.spec.ts` (E2E-01-01, sign in → record your first match → upload → facts);
- `first-run-and-guide.spec.ts`;
- `resumable-upload.spec.ts` (E2E-01-02);
- `sign-out.spec.ts`.

### G01-02: integration-test pass rate

The backend runs on an isolated local Postgres and object store. Mailpit and the worker sandbox come from the §4.0 stack.

```bash
eval "$(bash scripts/dev-postgres.sh start)"; eval "$(bash scripts/dev-postgres.sh url)"
eval "$(bash scripts/dev-objectstore.sh start)"; eval "$(bash scripts/dev-objectstore.sh env)"
export MAILPIT_API_URL=http://127.0.0.1:8025 SMTP_HOST=127.0.0.1 SMTP_PORT=1025 MAIL_SMTP_URL=smtp://127.0.0.1:1025
(cd backend && env -u APP_ENV uv run pytest -q -p no:cacheprovider -rfEs \
   tests/integration tests/regression tests/unit/sports/pickleball/test_rules_static.py \
   --ignore=tests/integration/test_it_00_10_worker_sandbox_strict.py \
   --junitxml="$GOAL/backend-it.xml"); echo rc=$?
# the strict sandbox file runs only in the next command, with the Compose env (smoke F-01, QA-V1-05)
(cd backend && COMPOSE_PROJECT_NAME=racket-goal01 COMPOSE_ENV_FILES="$RA_DEV_STATE/goal.env" env -u APP_ENV \
   uv run pytest -q -rs tests/integration/test_it_00_10_worker_sandbox_strict.py --junitxml="$GOAL/sandbox.xml"); echo rc=$?
python3 scripts/measure/junit_rate.py --include 'test_it_01_|test_bola_matrix|test_rules_static' \
  $(for i in 01 02 03 04 05 06 07 08 09 10 12 13; do printf -- '--require test_it_01_%s_ ' $i; done) \
  --require test_bola_matrix --json "$GOAL/it-rate.json" "$GOAL/backend-it.xml"; echo rc=$?
python3 scripts/measure/junit_rate.py --include 'test_upload_resume|test_it_01_09|test_it_01_06|worker_sandbox_strict' \
  --require test_upload_resume --require worker_sandbox_strict \
  --json "$GOAL/regression-rate.json" "$GOAL/backend-it.xml" "$GOAL/sandbox.xml"; echo rc=$?
```

- IT-01-11 is the BOLA matrix (`tests/regression/test_bola_matrix.py`, including the inventory diff).
- IT-01-12 and IT-01-13 are the static checks in `test_rules_static.py`.
- The strict worker-sandbox file is excluded from the first command (`--ignore`) because it needs `COMPOSE_PROJECT_NAME` and `COMPOSE_ENV_FILES`; without them its cases skip and `junit_rate.py` fails closed (smoke F-01, QA-V1-05). It still runs in full in the second command, and `--require worker_sandbox_strict` keeps it mandatory. Decision-log 2026-10-05 (QA-V1-05).
- **Actual:** `rate`, `selected`, `failed`, `skipped` and `missing` from each JSON. The row is met only when both pytest commands and both `junit_rate.py` commands give `rc=0`.

### G01-03: E2E journey pass rate (and G01-10)

```bash
cd web
PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers BASE_URL=https://localhost:3000 PW_PROJECTS=chromium \
PLAYWRIGHT_JUNIT_OUTPUT_NAME="$GOAL/e2e.xml" PLAYWRIGHT_JSON_OUTPUT_NAME="$GOAL/e2e.json" \
  pnpm exec playwright test --workers=1 --reporter=line,junit,json; echo rc=$?
cd ..
python3 scripts/measure/junit_rate.py --include '.' --allow-skips \
  --require 'E2E-01-02' --require 'E2E-01-03' --require 'walking-skeleton|walking skeleton' \
  --require 'First run and capture guide' --require 'Signing out leaves nothing behind' \
  --require 'Upload validation' --json "$GOAL/e2e-rate.json" "$GOAL/e2e.xml"; echo rc=$?
(cd web && PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers BASE_URL=https://localhost:3000 PW_PROJECTS=chromium \
  PLAYWRIGHT_JUNIT_OUTPUT_NAME="$GOAL/e2e-repeat.xml" \
  pnpm exec playwright test e2e/sprint-01 --repeat-each=3 --workers=1 --reporter=line,junit)
python3 scripts/ci/flaky_report.py --fail-on-flaky --out "$GOAL/flaky.md" "$GOAL/e2e.xml" "$GOAL/e2e-repeat.xml"; echo rc=$?
```

- **Actual:** the `passed`/`failed`/`skipped` counts and `rate` (skips excluded) from `e2e-rate.json`, then the flaky count from `flaky.md`.
- **Skips:** the skipped count is the `skipped` field, and every skip must name its API binding in its reason.
- WebKit runs only on CI. A CI WebKit result is supporting evidence, not a substitute.

**G01-10, from the same JSON report:**

```bash
jq '[.. | objects | select(has("attachments")) | .attachments[] | select(.name|startswith("axe-"))] | length' "$GOAL/e2e.json"   # axe checks run
jq '[.. | objects | select(has("errors")) | .errors[]? | .message? // "" | select(test("axe serious/critical"))] | length' "$GOAL/e2e.json"  # must be 0
jq -r '[.. | objects | select(has("attachments")) | .attachments[] | select(.name|startswith("axe-")) | .name] | unique | .[]' "$GOAL/e2e.json"  # screen families covered
```

- The target-size check (NFR-028) and E2E-01-03 are tests in `match-setup.spec.ts`. They must be among the passed cases in `e2e-rate.json`.
- Error and transient states (PD-V1-01): `error-states-a11y.spec.ts` runs axe and the 24×24 target check on Q-03 error, U-03, U-04 (banner and different file), A-03 and A-05. All its cases must be among the passed cases. Count target failures with `jq '[.. | objects | select(has("errors")) | .errors[]? | .message? // "" | select(test("targets below 24x24"))] | length' "$GOAL/e2e.json"` (must be 0). At `d560ace` + the QA round-1 specs this is 2 (Q-03 error, U-03: the error-summary link is 21 px high, PD-R1-03), so G01-10 is "no" until senior-frontend-engineer fixes PD-R1-03.
- An axe failure fails its test, so G01-10 is also "no" whenever G01-03 has an axe-labelled failure.

### G01-04: API read latency at 50 RPS

```bash
python3 scripts/measure/api_latency.py --api http://127.0.0.1:8000 --origin https://localhost:3000 \
  --mailpit http://127.0.0.1:8025 --rps 50 --duration 60 --json "$GOAL/api-latency.json"; echo rc=$?
```

- The test hits the API's published port, which is server-side latency as NFR-010 defines it.
- The session comes from a magic-link sign-in, not the dev identity provider.
- **Actual:** `p95_ms`, `p99_ms`, `availability`, `status_unexpected` and `achieved_rps`. The row is met only when the result is `rc=0`.
- **Supporting line:** the same command with `--api https://localhost:3000/api --cacert "$RA_DEV_STATE/root.crt"`, which measures through TLS and the Next rewrite. It is supporting only.

### G01-05: upload throughput

```bash
bash scripts/measure/make_large_fixture.sh "$RA_DEV_STATE/large-1080p60.mp4" 120     # ~1.05 GB, about 1 min
python3 scripts/measure/live_goal.py --cacert "$RA_DEV_STATE/root.crt" \
  --file "$RA_DEV_STATE/large-1080p60.mp4" --runs 1 --result-timeout 300 --json "$GOAL/live-goal-large.json"; echo rc=$?
jq '.runs[0].steps.upload_complete' "$GOAL/live-goal-large.json"
```

- **Actual:** `throughput_mbps`, plus `bytes` equal to the file size.
- **Context:** record `df -h /` before and after (retro 1 M4: disk exhaustion) and `nproc`.
- The run also re-checks G01-01's steps on a large file, and its `rc` must be 0.

### G01-07: scoring correctness

```bash
cd backend
HYPOTHESIS_PROFILE=ci python3 ../scripts/ci/run_with_budget.py 90 -- env -u APP_ENV uv run pytest -q \
  -m "scoring and not nightly" --junitxml="$GOAL/scoring.xml"; echo rc=$?
env -u APP_ENV uv run pytest -q -m "scoring and needs_verification" --junitxml="$GOAL/needs-verification.xml"
cd ..
python3 scripts/measure/junit_rate.py --include '.' --allow-skips --require 'SOD|sod' --require 'M-0|match_structure' \
  --json "$GOAL/scoring-rate.json" "$GOAL/scoring.xml"; echo rc=$?
python3 scripts/measure/junit_rate.py --include '.' --require 'SOD|sod' --require 'F-0|fault' \
  --json "$GOAL/needs-verification-rate.json" "$GOAL/needs-verification.xml"; echo rc=$?
```

- **Actual:** the passed/selected count of each, and the `skipped` count. Only the P3 rally-scoring property may skip, and its reason must name FR-043.
- **Golden rows:** the `needs_verification` count is `selected` from the second report, and it must be ≥ 19.

### G01-08: oracle and mutation

```bash
cd backend
env -u APP_ENV uv run python -m tests.oracle.differential --sequences 100000 --json "$GOAL/oracle.json"; echo rc=$?
env -u APP_ENV uv run --with mutmut==3.8.0 python ../scripts/ci/mutation_score.py --project . \
  --target src/racket/sports/pickleball/rules --tests tests/unit/sports \
  --ignore tests/unit/sports/pickleball/test_rules_static.py --out "$GOAL/mutation.json"; echo rc=$?
```

- `--ignore` keeps the IT-01-13 static import scan out of the mutant runs only (mutmut 3 adds a `mutmut` import to every mutated file, so the scan would stop the run; QA-V1-03). The scan still runs in G01-02 and the normal suite.

- **Actual:** the sequences and disagreements from `oracle.json`, and `score` from `mutation.json`.
- **Optional:** the GitHub nightly run (`nightly-quality.yml`) is extra evidence when one exists (retro 1 A1).

### G01-09: coverage

```bash
(cd backend && env -u APP_ENV uv run pytest -q -m "(unit or integration or scenario or regression) and not nightly" \
   --ignore=tests/integration/test_it_00_10_worker_sandbox.py --ignore=tests/integration/test_it_00_10_worker_sandbox_strict.py \
   --cov --cov-branch --cov-report=xml:"$GOAL/coverage-backend.xml" --cov-report=json:"$GOAL/coverage-backend.json"); echo rc=$?
uvx --from diff-cover==10.6.0 diff-cover "$GOAL/coverage-backend.xml" --compare-branch=main --fail-under=85 \
  --markdown-report "$GOAL/diff-cover.md"; echo rc=$?
(cd backend && uv run coverage report --data-file=.coverage \
  --include='src/racket/sports/pickleball/rules/*,src/racket/matches/match_state.py,src/racket/matches/participants.py')
(cd web && pnpm exec vitest run --coverage --coverage.reporter=text-summary)
```

- This uses the same environment as G01-02.
- `and not nightly` drops the 100,000-sequence differential scenario (measured in G01-08), which exceeds the 120 s pytest timeout under `--cov` (QA-V1-06). The pytest command must give `rc=0`: coverage from a red run is not evidence, and the row is "no".
- **Actual:**
  - the diff-cover "Coverage:" percentage;
  - the rules and aggregates `TOTAL` line and branch percentages, with the branch figure from `coverage-backend.json` `totals.percent_branches_covered`, restricted by the same `--include`;
  - the web "Lines" percentage.

### G01-11: open defects

```bash
python3 scripts/measure/open_defects.py --json "$GOAL/open-defects.json" docs/sprints/01/review-rounds.md; echo rc=$?
```

- `open_defects.py` (tests in `infra/tests/test_measure_scripts.py`) replaces the earlier awk filter, which matched `blocking|major` (the tables say `blocker` or `**blocker**`) and read column 4 even where the disposition is in another column (QA-V1-07).
- It reads every table with a finding id, a `Severity` column and a disposition column (`Disposition` first, else `Fix…`, `State…`, `Status`). The last row naming an id wins. A blocker or major row is open when its disposition starts with "Open", "Not re-verified", "Not fixed" or "Partly" (fail closed). Ids named in one row are aliases of one finding (`PE-R3-05 / QA-R3-05`); the finding is open while the latest row of any alias is open, and is counted once (PE-R2-S1-02). Any id shape counts (`S-07`, `BLK-ASVS-6.3.3`, `QA-R2V-01`); a severity row with no parsable id makes the script refuse the file (exit 2) instead of skipping it. It exits 1 while any is open and 2 when it finds no review table.
- **GitHub:** run `mcp__github__search_issues` with `repo:nhuthuynh/racket-analytics is:issue is:open label:bug` and count the issues labelled `blocker` or `major`.
- **Integration smoke:** add any open product-defect rows from `docs/sprints/01/smoke.md` §4 (S-xx) and from `blockers.md` that are not yet in `review-rounds.md`.
- **Actual:** the sum of these counts, with the IDs listed in Evidence.

### G01-12: fast tests

```bash
cd backend
python3 ../scripts/ci/run_with_budget.py 10 -- env -u APP_ENV uv run pytest -q -m unit tests/unit; echo rc=$?
python3 ../scripts/ci/run_with_budget.py 60 -- env -u APP_ENV uv run pytest -q -m unit; echo rc=$?
```

- These are the same budgets and paths as `ci.yml` (`DOMAIN_UNIT_BUDGET_S`, `BACKEND_UNIT_BUDGET_S`).
- **Actual:** the wall time and pass/fail line of each.

## 5. Traceability of targets

| Row | FR / NFR / gate |
|---|---|
| G01-01 | FR-001, FR-005, FR-011, FR-021, FR-022, FR-023; NFR-053, NFR-055, NFR-060, NFR-067 |
| G01-02 | sprint-01 §6 IT-01-01..13; NFR-026, NFR-053 (regression suites 100%); NFR-051 (BOLA diff empty); NFR-079 |
| G01-03 | sprint-01 §6 E2E-01-01..03; NFR-032, NFR-034, NFR-037, NFR-067; NFR-074 |
| G01-04 | NFR-010 (p95 ≤ 300 ms, p99 ≤ 800 ms at 50 RPS); NFR-041 (99.5%) |
| G01-05 | NFR-016 (b) ≥ 50 Mbps sustained ingest; ADR 0019 (8 MiB dev chunk) |
| G01-06 | FR-001 and FR-022/FR-023 in real time. Thresholds are judgment until an NFR exists: decision-log 2026-10-05 |
| G01-07 | FR-040 (a), FR-041 (a), FR-044 (a), FR-045 (a); NFR-001 (provisional rows), NFR-002a; ADR 0009 |
| G01-08 | NFR-002b; NFR-072 |
| G01-09 | NFR-071; sprint-01 §8 |
| G01-10 | NFR-027, NFR-028, NFR-034; sprint-01 §8 |
| G01-11 | definition-of-done (no open Blocking finding); ADR 0030 |
| G01-12 | NFR-073 |
