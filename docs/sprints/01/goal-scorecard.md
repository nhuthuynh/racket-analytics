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
| G01-01 | **Goal works end to end, live.** Runs of the full API journey over https through the web origin, each as a fresh account. One run covers the following steps, and every step must pass:<br>1. magic link via Mailpit, then exchange;<br>2. `GET /me`;<br>3. a doubles match with 4 nicknames and one "me";<br>4. tus upload with a connection drop at ≥ 40% and a resume from the HEAD offset;<br>5. a damaged chunk refused with 460 and the offset kept;<br>6. upload to the end;<br>7. "Video received" with probed facts;<br>8. a 12 GB `Upload-Length` refused with 413, and a PDF named `.mp4` refused with 415;<br>9. sign-out, after which the old session gets 401 | **5 of 5 runs pass (100%)** | `scripts/measure/live_goal.py --runs 5` | 5 of 5 runs passed (100%) | yes | Head `7c6a0ae`, run `racket-qav3`: `live_goal.py --api https://localhost:33000/api --origin https://localhost:33000 --mailpit http://127.0.0.1:38025 --cacert $RA_DEV_STATE/root.crt --file fixtures/clips/synthetic-60s/clip.mp4 --runs 5` → rc=0, `runs_passed 5`, every run `ok true` (`reports/goal-qav3/live-goal.json`) |
| G01-02 | **Integration-test pass rate:** (a) every Sprint 1 IT id, IT-01-01..IT-01-13, against real Postgres, the object store and Mailpit, plus the Compose worker sandbox for IT-01-10's no-network part; (b) the upload-resume and upload-validation regression suites | **(a) 100% passed, 0 failed, 0 skipped, 13 of 13 ids present; (b) 100% passed** | `pytest --junitxml` and `scripts/measure/junit_rate.py` | (a) 69/69 passed, 0 failed, 0 skipped, `missing []`; (b) 41/41 passed (upload resume, IT-01-06/09 and 10 strict-sandbox cases) | yes | Head `7c6a0ae`, run `racket-qav3`: §4 G01-02 commands with Mailpit `127.0.0.1:38025` and SMTP `31025`. Pytest → rc=0, `223 passed, 2 skipped`; the 2 skips are Sprint 0 `test_it_00_10_worker_sandbox.py` cases, outside both includes. Strict sandbox pytest with `COMPOSE_PROJECT_NAME=racket-qav3` → rc=0, `10 passed`. `it-rate.json` rc=0 `ok true`; `regression-rate.json` rc=0 `ok true` |
| G01-03 | **E2E journey pass rate,** Playwright Chromium over https against the Compose stack. All specs, including:<br>- E2E-01-01 (the walking skeleton plus first run and guide);<br>- E2E-01-02 (network cut at about 40%);<br>- E2E-01-03 (keyboard-only setup);<br>- sign-out;<br>- validation | **100% of non-skipped tests passed, 0 failed, ≤ 6 skipped (each names its API binding); 0 flaky over 3 repeats (NFR-074)** | `playwright test` (junit) and `junit_rate.py --allow-skips`; then `--repeat-each=3` | 58 selected, 52 passed, 0 failed, 6 skipped (rate 1.0). Repeat ×3: 135 passed, 0 failed, 18 skipped. 0 flaky | yes | Head `7c6a0ae`, run `racket-qav3`: `MAILPIT_API_URL=http://127.0.0.1:38025 PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers BASE_URL=https://localhost:33000 PW_PROJECTS=chromium pnpm exec playwright test --workers=1 --reporter=line,junit,json` → rc=0, `52 passed, 6 skipped`. `junit_rate.py … --allow-skips` (6 `--require`) → rc=0, `ok true`, `missing []`. `e2e/sprint-01 --repeat-each=3` → rc=0, `135 passed, 18 skipped`. `flaky_report.py --fail-on-flaky` → rc=0, "2 runs, 58 tests, 0 flaky". The T-UV-10 race found at `afb0e23` (QA-V2-01) is fixed in `7c6a0ae` and passed here. WebKit: CI only, none at this head |
| G01-04 | **API read latency and availability, live:** an open loop at 50 RPS for 60 s on `GET /matches/{id}`, `GET /matches` and `GET /me` (NFR-010, NFR-041) | **p95 ≤ 300 ms, p99 ≤ 800 ms, availability ≥ 99.5%, 0 unexpected 4xx, achieved rate ≥ 47.5 RPS** | `scripts/measure/api_latency.py --rps 50 --duration 60` | p95 16.7 ms, p99 57.6 ms, availability 100%, 0 unexpected 4xx, 0 5xx, 49.99 RPS (3,000 requests) | yes | Head `7c6a0ae`, run `racket-qav3`: `api_latency.py --api http://127.0.0.1:38000 --origin https://localhost:33000 --mailpit http://127.0.0.1:38025 --rps 50 --duration 60` → rc=0, `ok true` (`api-latency.json`) |
| G01-05 | **Upload throughput, live:** sustained ingest of a ≥ 1 GB valid 1080p60 H.264 file through the https web origin, in 8 MiB chunks (ADR 0019), with sha256 `Upload-Checksum` on every chunk (NFR-016b) | **≥ 50 Mbit/s, and the final offset equals the file length** | `make_large_fixture.sh`, then `live_goal.py --file <1 GB>` | 457.9 Mbit/s; final offset 1,052,838,365 = file size | yes | Head `7c6a0ae`, run `racket-qav3`: `make_large_fixture.sh … 120` → 1,052,838,365 bytes. `live_goal.py --file large-1080p60.mp4 --runs 1 --result-timeout 300` → rc=0, run 1/1 PASS; `upload_complete`: ok true, bytes 1052838365, transfer_s 18.396, throughput_mbps 457.9. `df -h /`: 16 G free before the fixture, 14 G after the run (`disk_free_gb_start 14`, `_end 13`); `nproc` 4 |
| G01-06 | **Real-time latency of the goal steps,** p95 over the 5 G01-01 runs: (a) from the link request to a signed-in session, including email delivery by the mailer worker; (b) from the final byte to "Video received" with facts, for the 60 s fixture | **(a) ≤ 10 s; (b) ≤ 30 s** (judgment, decision-log 2026-10-05) | From the G01-01 JSON: `sign_in_p95_s`, `final_byte_to_facts_p95_s` | (a) 1.064 s; (b) 0.906 s | yes | Head `7c6a0ae`, run `racket-qav3`: from the G01-01 summary, `sign_in_p95_s 1.064` and `final_byte_to_facts_p95_s 0.906` |
| G01-07 | **Scoring correctness:**<br>- Ready mechanics, §7.7;<br>- match structure M-01..M-08;<br>- property suite P1-P8 at ≥ 1,000 sequences per scoring system (Hypothesis profile `ci`);<br>- the provisional golden rows SOD-01..12, SOD-16 and F-01..06, reported separately as `@needs-verification` | **100% of scoring tests passed, 0 failed (P3 skip allowed: FR-043); 100% of `needs_verification` cases passed and listed separately (≥ 19 rows); suite time ≤ 90 s** | `pytest -m "scoring and not nightly"` and `-m "scoring and needs_verification"`, with junit and `junit_rate.py` | 204/205 passed, 0 failed, 1 skipped (P3, FR-043), 33.7 s. `needs_verification`: 26/26 passed, 0 skipped | yes | Head `7c6a0ae`, run `racket-qav3`: `HYPOTHESIS_PROFILE=ci run_with_budget.py 90 -- … pytest -q -m "scoring and not nightly"` → rc=0, `204 passed, 1 skipped in 32.62s`, budget 33.7 s. `-m "scoring and needs_verification"` → `26 passed`. Both `junit_rate.py` runs → rc=0, `ok true`, `missing []`. Skip reason: "P3 is rally scoring: blocked on FR-043 / OQ-01". The 26 provisional rows are `@needs-verification` only and are not counted toward a Must FR |
| G01-08 | **Independent engine checks:**<br>- differential oracle P9, production engine against the QA oracle (NFR-002b);<br>- mutation score on `sports/pickleball/rules` (NFR-072; baseline this sprint, gated from Sprint 2) | **Oracle: 100,000 sequences, 0 disagreements. Mutation: baseline recorded as a number; ≥ 85% is reported but not gated** | `python -m tests.oracle.differential --sequences 100000`; `scripts/ci/mutation_score.py` | Oracle: 100,000 sequences, 0 disagreements. Mutation baseline: 0.8654 (373 of 431 killed, 58 survived) | yes | Head `7c6a0ae`, run `racket-qav3`: `python -m tests.oracle.differential --sequences 100000` → rc=0, `disagreements 0` in 57.4 s. `mutation_score.py --target src/racket/sports/pickleball/rules …` (mutmut 3.8.0) → rc=0, `status measured`, `score 0.8654`. That run reused a warm `mutants/` cache, so it was repeated with the cache moved aside: rc=0, 76 s, same 373/431 (`mutation-cold.json`). The score is ≥ 85%; it is reported, not gated, this sprint |
| G01-09 | **Coverage (NFR-071):**<br>- backend changed lines against `main` (the Sprint 0 close, `2b9c6ca`);<br>- rules engine and aggregates (`sports/pickleball/rules`, `matches/match_state.py`, `matches/participants.py`);<br>- web unit | **Backend changed lines ≥ 85%. Rules and aggregates ≥ 95% line and ≥ 90% branch. Web ≥ 80% line** | `pytest --cov`, then `diff-cover`, `coverage report` and `vitest --coverage` | Backend changed lines 95% (1,579 lines, 64 missing). Rules and aggregates 99.4% line (470/473), 98.7% branch. Web 90.22% lines | yes | Head `7c6a0ae`, run `racket-qav3`: coverage pytest (§4 G01-09, with the 3 `--deselect` lines from `df03731`) → rc=0, `1067 passed, 1 skipped, 4 deselected`. `diff-cover --compare-branch=main --fail-under=85` → rc=0, "Coverage: 95%". `coverage report --include=<rules+aggregates>` → `TOTAL 473 3 156 2 99%`; `coverage json` → `percent_branches_covered 98.72`. `vitest run --coverage` → rc=0, `269 passed`, `Lines 90.22% (2862/3172)`. The 3 deselected tests are still red and counted in G01-11 (S-07, PE-R3-05 family) |
| G01-10 | **Accessibility on Sprint 1 screens:**<br>- axe serious and critical violations (WCAG 2.2 AA tags) on every page an E2E test checks;<br>- tap targets below 24×24 CSS px;<br>- keyboard-only setup (NFR-027, NFR-028, NFR-034) | **0 serious/critical axe violations, with ≥ 1 axe check per Sprint 1 screen family (A, F/G, Q, U, M); 0 targets below 24×24; E2E-01-03 passes** | From the G01-03 Playwright JSON report | 19 axe checks, 0 serious/critical, families A, F/G, Q, U and M covered; 0 targets below 24×24; E2E-01-03 passed | yes | Head `7c6a0ae`, run `racket-qav3`: from `reports/goal-qav3/e2e.json` (§4 jq). Axe attachments: 19 (A-01, A-03, A-04, A-05, F-01, G-01, Q-01-error, Q-03-error, Q-07, U-03, U-04-banner, U-04-different-file, match-detail, matches-empty, new-match, uploading, sign-in, after-sign-in, not-found). "axe serious/critical" errors: 0. "targets below 24x24" errors: 0. Passed: `error-states-a11y.spec.ts` 5/5, the 4 reflow/target tests and E2E-01-03 |
| G01-11 | **Open defects:** blocking or major findings whose latest disposition is "Open" (ADR 0030), plus open GitHub issues labelled `bug` with `blocker` or `major` | **0** | `review-rounds.md` count and GitHub issue search (§4) | 11 at the measured head (review-rounds.md 11; GitHub bug issues 0; no extra smoke or blocker rows) | no | Head `7c6a0ae`, run `racket-qav3`: `open_defects.py docs/sprints/01/review-rounds.md` → rc=1, `open 11` (aliases counted once): PE-R3-05 family (QA-R1-06, PE-R2-02, QA-R2-02, QA-R3-05, QA-R2V-01); PE-R1-S1-02/QA-V1-04 (closed by this fill; see review-rounds round 2); QA-R2V-03; PD-R1-02/PD-R1-04/PE-R1-04/QA-R1-04/S-09/QA-R2V-06/PD-R2R-01; S-08/QA-R2V-08; SEC-R3-S1-01/SEC-R4-S1-01; SEC-R4-S1-04/BLK-ASVS-6.3.3; QA-R2V-11; PD-R2R-03; S-07/QA-R2V-07; PD-R1-06/PD-R2R-02/QA-R2V-12. `mcp__github__search_issues` `is:open label:bug` on nhuthuynh/racket-analytics → `total_count 0`. Every open `blockers.md` row is either PO input or environment, or is already one of these findings. Recount with this fill's review-rounds rows (PE-R1-S1-02/QA-V1-04 fixed) → rc=1, `open 10` |
| G01-12 | **Fast tests (NFR-073):**<br>- the domain unit suite;<br>- the whole backend unit suite | **Domain < 10 s; backend unit ≤ 60 s; both 0 failed** | `scripts/ci/run_with_budget.py` | Domain 7.3 s (721 passed, 1 skipped); backend unit 8.2 s (763 passed, 1 skipped); 0 failed | yes | Head `7c6a0ae`, run `racket-qav3`: `run_with_budget.py 10 -- … pytest -q -m unit tests/unit` → rc=0, `721 passed, 1 skipped in 6.23s`, budget 7.3 s. `run_with_budget.py 60 -- … pytest -q -m unit` → rc=0, `763 passed, 1 skipped, 320 deselected in 7.04s`, budget 8.2 s |

**Overall:** the sprint goal is met only when all 12 rows are "yes". A row whose method could not run is "no", never "n/a" (fail closed, ADR 0014).

**Verifier result (senior-qa-engineer, 2026-10-05, review round 2; PE-R2-S1-01, QA-R2V-02):** **11 of 12 rows are "yes". G01-11 (open defects) is "no", so the Sprint 1 goal is NOT met and Sprint 1 is not done.**

- **What works:** the goal itself works live. Rows G01-01..G01-10 and G01-12 meet their targets on one isolated stack at one head: 5/5 live journeys, E2E 52/52 non-skipped with 0 flaky, 50 RPS p95 16.7 ms, and 1 GB ingest at 458 Mbit/s.
- **What blocks closing:** the 11 open blocker or major findings. Most of them wait on human-PO input: the push and CI/nightly dispatch, the WebKit trace, real phone clips, the ASVS 6.3.3 decision and the P7 design review.
- **Run:** one isolated run at head `7c6a0ae60bf15e3455a329c6c614369eddfbff7d` (`reports/goal-qav3/head.txt`; `git status` clean before and after).
  - Fresh-volume Compose project `racket-qav3`: `up -d --build --wait` → rc=0. Its images were built from this tree with the proxy CA build secret (`.local/qav3/ca-override.yaml`).
  - Ports 33000/38000/38025/31025 and `RA_DEV_STATE=.local/qav3`. Plain http on 33000 → 400; https → 200.
  - Its own `dev-postgres` and `dev-objectstore`.
  - Disk at the start: 20 G free.
  - Every command is in `reports/goal-qav3/run.log`, and the reports are in `reports/goal-qav3/` (git-ignored).
- **Same tree:** the G01-11 count is the `review-rounds.md` at that head. A first run at `afb0e23` (`racket-qav2`) found the T-UV-10 race (QA-V2-01, fixed in `7c6a0ae`). It is superseded because 12 round-2 commits landed during it, including `infra/compose.yaml`.
- **Reviewer runs:** the runs at `afb0e23` (PE-R2-S1-01 `racket-fer1`; QA-R2V-02 `racket-qar2`) are supporting evidence only.

**Verification status (engineering-manager, 2026-10-05, review round 1 after close; PE-R1-S1-02, QA-V1-04):**

- **Superseded by the verifier result under §2 "Overall"** (review round 2): the table is filled at `7c6a0ae`. The bullets below record the round-1 state.

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
   --deselect tests/features/test_nightly_quality.py::test_nightly_run_completes \
   --deselect tests/features/test_phone_fixtures.py::test_coverage_of_the_set \
   --deselect tests/features/test_phone_fixtures.py::test_probe_every_fixture \
   --cov --cov-branch --cov-report=xml:"$GOAL/coverage-backend.xml" --cov-report=json:"$GOAL/coverage-backend.json"); echo rc=$?
uvx --from diff-cover==10.6.0 diff-cover "$GOAL/coverage-backend.xml" --compare-branch=main --fail-under=85 \
  --markdown-report "$GOAL/diff-cover.md"; echo rc=$?
(cd backend && uv run coverage report --data-file=.coverage \
  --include='src/racket/sports/pickleball/rules/*,src/racket/matches/match_state.py,src/racket/matches/participants.py')
(cd web && pnpm exec vitest run --coverage --coverage.reporter=text-summary)
```

- This uses the same environment as G01-02.
- The three `--deselect` lines (QA-R2V-04, decision-log 2026-10-05 EM row) leave out exactly the three tests that are red only because the human PO has not yet supplied their input (a GitHub nightly run, S-08; real phone recordings, S-07). They stay in G01-02's full run and in G01-11 as open findings, so they are still counted against the sprint. Remove a `--deselect` line as soon as its test can pass. No other test may be deselected here; any other failure keeps `rc=1` and the row "no".
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
