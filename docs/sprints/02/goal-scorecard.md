# Sprint 2 goal scorecard

- **Written:** 2026-10-05 at Sprint 2 planning by the engineering-manager, with the product-manager (goal wording, targets), principal-engineer (performance and replay methods, contract assumptions), business-analyst (FR/NFR traceability) and senior-qa-engineer (test selection, fail-closed rules).
- **Why:** PO standing rule. A sprint is done only when its **goal is shown to work on a live local stack**, with every goal metric measured against its target. Unit tests alone never prove a goal.
- **Verifier fills in:** `Actual`, `Met` (yes / no) and `Evidence` (exact command, stack head SHA, result line or report path). Nothing else in this file changes without a decision-log row.
- **Sources:**
  - `docs/sprints/sprint-02.md` §1 (goal), §6 (IT and E2E ids), §8 (gates), §12 (demo);
  - `docs/requirements/non-functional-requirements.md` (NFR-001, 002, 010..014, 017, 027..036, 041, 051, 055, 060, 071..075);
  - `docs/architecture/match-aggregate.md` (§3 invariants, §5 projection);
  - ADR 0009 and ADR 0023 (rules stay PROVISIONAL-UNVERIFIED, the score sheet says "unofficial"), ADR 0029 (https dev stack, no insecure-cookie flag), ADR 0030 and ADR 0033 (isolated, self-cleaning evidence; dry-run before handover; reviewer-written Open rows);
  - retro 1 actions A1-A5.
- **Harness:** `scripts/measure/` (standard-library Python). Sprint 2 adds `taglib.py`, `tagcontract.py`, `live_tagging.py`, `tag_latency.py` and `pw_timings.py`. Tests: `cd infra && uv run pytest -q tests/test_measure_sprint02.py tests/test_measure_scripts.py` (81 passed at `15c8836`).
- **Contract assumptions:** the Sprint 2 routes and fields used by G02-01, G02-02 and G02-04 live only in `scripts/measure/tagcontract.py`. They follow `match-aggregate.md` until `api-sprint-02.md` exists; the principal-engineer updates that file with the contract (decision-log 2026-10-05).

## 1. Sprint goal (sprint-02 §1)

1. A player tags every rally of an uploaded match by tapping or by keyboard: start, end, winning side, ending, optional responsible player. Each tag shows the new score at once and announces it to screen readers.
2. The player opens a score sheet that lists every rally with server, score before and after, winner and ending. The score is computed by replaying the rules, never stored as an editable value. The sheet says "unofficial scoring (rules not yet verified)" (FR-055; ADR 0009, ADR 0023: no rulebook yet).
3. The player can undo any change and correct any rally. Later rallies are re-scored in one step. Rallies that a correction pushes past the end of a game are kept and marked "needs your decision", never deleted. Every change is in an audit trail.
4. Every rally row opens the video at that rally, through a short-lived link.
5. The Sprint 1 blockers and majors are fixed first (C-01..C-06, ST-013b), and none is open at the close.

## 2. Scorecard

| ID | What is measured | Target | Method (detail in §4) | Actual | Met | Evidence |
|---|---|---|---|---|---|---|
| G02-01 | **Goal works end to end, live (API, real time).** Runs of the full journey over https through the web origin, each as fresh accounts. Every step of a run must pass:<br>1. magic-link sign-in; a doubles match; the 60 s fixture uploaded; "Video received";<br>2. tagging a match with no video → 409 `match_not_ready` (NFR-060);<br>3. game started; 6 rallies tagged; each response carries the reference score;<br>4. score sheet = reference rows; label "unofficial scoring (rules not yet verified)"; `rules_version` present;<br>5. an error credited to the winning side → 422, sheet unchanged;<br>6. a stale `If-Match` → 409 `stale_match`;<br>7. rally 2's winner corrected → rallies 2-6 re-scored (C-01), rally 2 marked corrected, history shows field, old and new value;<br>8. undo → sheet byte-identical to before (C-04), history lists correction and undo;<br>9. 14-rally game, rally 11 corrected → rallies 12-14 kept as `needs_decision` (C-02, `@needs-verification`);<br>10. rally 3 media link: TTL ≤ 900 s, no session token in the URL, Range → 206, tampered signature → 401/403, `start_ms` = the rally's start;<br>11. a second account → 404 on sheet, history and media;<br>12. sign-out | **5 of 5 runs pass (100%)** | `scripts/measure/live_tagging.py --runs 5` | | | |
| G02-02 | **Real-time latency of the goal steps, live:** (a) correction command → server-confirmed state on a decided best-of-3 match (seeded, about 100+ rallies), 50 correction + 50 undo commands, and the sheet byte-identical to the baseline afterwards; (b) last tag → score sheet current, over every tag of the 5 G02-01 runs | **(a) p95 ≤ 1,500 ms, ≥ 100 samples, 0 failed commands, restored byte-identical (NFR-013); (b) p95 ≤ 5 s (NFR-017)** | `live_tagging.py --corrections 50` (summary `corrections.timing`, `tag_to_sheet`) | | | |
| G02-03 | **Integration-test pass rate** against real Postgres, the object store and Mailpit: (a) every committed Sprint 2 IT id: IT-02-01..IT-02-06 and IT-02-08..IT-02-12 (IT-02-07 too if ST-038 is pulled in), plus the BOLA matrix with its inventory diff (NFR-051); (b) every Sprint 1 IT id, IT-01-01..IT-01-13, and the upload-resume and upload-validation regression suites (no regression) | **(a) 100% passed, 0 failed, 0 skipped, every required id present; (b) 100% passed, 13 of 13 ids** | `pytest --junitxml`, `scripts/measure/junit_rate.py` | | | |
| G02-04 | **API read latency and availability, live:** an open loop at 50 RPS for 60 s on GET score sheet, GET correction history and GET match, for a tagged match (NFR-010, NFR-041) | **p95 ≤ 300 ms, p99 ≤ 800 ms, availability ≥ 99.5%, 0 unexpected 4xx, achieved rate ≥ 47.5 RPS** | `scripts/measure/tag_latency.py --rps 50 --duration 60` | | | |
| G02-05 | **E2E pass rate,** Playwright Chromium over https against the Compose stack, every spec, including:<br>- E2E-02-01 journey v1 (sign in → set up → upload → Quick Tag 6 rallies → sheet = golden sheet);<br>- E2E-02-02 keyboard-only tagging gives the same sheet as tapping;<br>- E2E-02-03 the live region announces each tag, focus stays on the controls;<br>- E2E-02-04 rally row → video playing at the rally;<br>- E2E-02-05 any call fixed in ≤ 2 taps or keys (NFR-036d);<br>- E2E-02-06 undo restores the sheet; correction history;<br>- every Sprint 1 spec (no regression), root specs included (C-04) | **100% of non-skipped tests passed, 0 failed, every E2E-02 id present and not skipped; Sprint 1 skips ≤ 6, each naming its API binding; 0 flaky over 3 repeats of every spec (NFR-074)** | `playwright test` (junit, json) and `junit_rate.py`; `--repeat-each=3` and `flaky_report.py` | | | |
| G02-06 | **Browser timings, live** (Playwright `timing.spec.ts`, ST-039; 20 samples each): (a) tap/key → optimistic score visible; (b) any tap/key on the tagging screen → visual feedback; (c) rally row → first video frame playing, 9/1.5 Mbit/s and 4× CPU throttling (reference profile, OQ-17); (d) score sheet interactive, warm | **(a) p95 ≤ 200 ms (NFR-012a); (b) p95 ≤ 100 ms (NFR-012b); (c) p95 ≤ 1,500 ms (NFR-014); (d) p95 ≤ 2,000 ms (NFR-011); each ≥ 20 samples** | `scripts/measure/pw_timings.py` on the timing JSON report | | | |
| G02-07 | **Scoring and replay correctness:**<br>- Ready mechanics and match structure (Sprint 1) plus the projection: empty sheet, projection = fold (P6), replay rows change nothing (P8), corrections C-01 and C-04;<br>- golden replay of every stored fixture match byte-identical under its `rules_version` (NFR-075, QD-TR-04);<br>- provisional rows (`@needs-verification`): ≥ 46 present (16 SOD, 6 F, 12 SOS, 8 M, 4 C; NFR-001), every row of a committed story green, rows `red_until` a stretch story listed separately;<br>- no `red_until` marker names a committed story;<br>- property suite at ≥ 1,000 sequences per scoring system (profile `ci`) | **100% of selected scoring tests passed, 0 failed (P3 skip allowed: FR-043); golden replay 100% byte-identical; ≥ 46 provisional rows collected; 0 `red_until` on committed stories; suite ≤ 90 s** | `pytest -m "scoring and not nightly and not red_until"`, `-m needs_verification --collect-only`, `junit_rate.py`, a `grep` | | | |
| G02-08 | **Independent engine checks:** (a) differential oracle P9, production engine against the QA oracle (NFR-002b); (b) mutation score on `sports/pickleball/rules` (NFR-072, **a gate from this sprint**); (c) mutation score on the `matches` projection module, baseline | **(a) 100,000 sequences, 0 disagreements; (b) ≥ 0.85; (c) a number recorded (not gated)** | `python -m tests.oracle.differential`; `scripts/ci/mutation_score.py` | | | |
| G02-09 | **Coverage (NFR-071):** backend changed lines against the Sprint 1 head `2b97fa0`; rules engine and aggregates (`sports/pickleball/rules`, `matches/match_state.py`, `matches/participants.py`, and the new `matches` aggregate, projection and correction modules); web unit | **Backend changed lines ≥ 85%; rules and aggregates ≥ 95% line and ≥ 90% branch; web ≥ 80% line** | `pytest --cov`, `diff-cover`, `coverage report`, `vitest --coverage` | | | |
| G02-10 | **Accessibility of the Sprint 2 screens** (Quick Tag, key map, score sheet, correction history, rally video) and the fixed Sprint 1 screens: (a) axe serious/critical (WCAG 2.2 AA tags) on every page an E2E test checks; (b) targets below 24×24 CSS px, and tagging controls below 48×48 (NFR-028); (c) keyboard-only tagging and announcements pass (E2E-02-02, E2E-02-03); (d) score sheet at 320 and 360 px with no sideways scrolling (NFR-034) | **(a) 0, with ≥ 1 axe check per Sprint 2 screen family (T, K, S, H, V) and per Sprint 1 family; (b) 0 and 0; (c) passed; (d) passed** | From the G02-05 Playwright JSON report | | | |
| G02-11 | **Open defects:** blocker or major findings whose latest disposition is open in `docs/sprints/02/review-rounds.md` (which starts with the 17 carried Sprint 1 families), plus open product-defect rows in `smoke.md` and `blockers.md` not yet in review-rounds, plus open GitHub issues labelled `bug` with `blocker` or `major` | **0** | `scripts/measure/open_defects.py`, GitHub issue search (§4) | | | |
| G02-12 | **Fast tests (NFR-073):** the domain unit suite; the whole backend unit suite; the backend integration suite | **Domain < 10 s; backend unit ≤ 60 s; integration < 10 min; all 0 failed** | `scripts/ci/run_with_budget.py` | | | |

**Overall:** the Sprint 2 goal is met only when all 12 rows are "yes". A row whose method could not run is "no", never "n/a" (fail closed, ADR 0014). `@needs-verification` results never count toward a Must FR (QD-QG-P5); G02-01 step 9 and G02-07's provisional rows are reported on their own line.

## 3. Rules for the verifier

1. **Live stack, isolated (ADR 0030, ADR 0033).**
   - Run everything at one recorded head (`git rev-parse HEAD`), on a fresh-volume Compose project of your own, with an `RA_DEV_STATE` of your own and remapped host ports (§4.0).
   - `bash scripts/disk-precheck.sh` first (≥ 10 GB free). The live scripts refuse below the floor (rc=2); that is a "no", not a skip.
   - Hold `flock .local/evidence-e2e.lock` for Compose up/down and every Playwright evidence run; pass `--output "$GOAL/pw-out"` to Playwright.
   - Tear down with `down -v --rmi local` at the end. Never reuse or remove another agent's stack, database or images.
2. **Fail closed.** A skipped test counts as not passed, except where a row allows named skips. If no test was selected, or a required id is missing, the row is "no" (`junit_rate.py` exits 1).
3. **No edits to make a row pass.** A test change needs a `test-change-requests.md` row decided by QA. A product defect goes to its owner as an Open row in `review-rounds.md` (working-agreement §7 step 2).
4. **Evidence** is the exact command, the head SHA and the result line. Reports go under `reports/goal/` (git-ignored); quote the numbers in the table.
5. **Dry-run first (ADR 0033 rule 2).** Before the verifier runs, each method author has run their method end to end on an isolated stack and written the rc in `decision-log.md`. A method with no dry-run row goes back to its author.

## 4. Methods (exact commands)

### 4.0 Stack under test (shared by G02-01, G02-02, G02-04 to G02-06 and G02-10)

Host ports are remapped so the evidence stack never collides with a developer's stack or another round (C-24, QA-R2V-14). The variables are the ones `infra/compose.yaml` reads.

```bash
cd /home/user/racket-analytics
git rev-parse HEAD; bash scripts/disk-precheck.sh; echo rc=$?    # rc must be 0 (>= 10 GB free)
export RA_DEV_STATE=$PWD/.local/goal02 GOAL=$PWD/reports/goal02; mkdir -p "$RA_DEV_STATE" "$GOAL"
cp infra/env.example "$RA_DEV_STATE/goal.env"
sed -i 's#^DOCKERHUB_REGISTRY=.*#DOCKERHUB_REGISTRY=mirror.gcr.io#' "$RA_DEV_STATE/goal.env"
cat >> "$RA_DEV_STATE/goal.env" <<'EOF'
AUTH_LINK_LIMIT_PER_IP=1000
AUTH_EXCHANGE_LIMIT_PER_IP=1000
WEB_HOST_PORT=33000
API_HOST_PORT=38000
MAILPIT_UI_HOST_PORT=38025
MAILPIT_SMTP_HOST_PORT=31025
POSTGRES_HOST_PORT=35432
S3_HOST_PORT=38333
TRACING_UI_HOST_PORT=36686
EOF
# PUBLIC_WEB_ORIGIN / ALLOWED_ORIGINS must name https://localhost:33000 (C-18)
sed -i 's#https://localhost:3000#https://localhost:33000#g' "$RA_DEV_STATE/goal.env"
DC="docker compose -p racket-goal02 -f infra/compose.yaml --env-file $RA_DEV_STATE/goal.env"
flock .local/evidence-e2e.lock $DC up -d --build --wait; echo rc=$?          # all services healthy
$DC cp web-tls:/data/caddy/pki/authorities/local/root.crt "$RA_DEV_STATE/root.crt"
curl -sS -o /dev/null -w '%{http_code}\n' http://localhost:33000/                                       # 400
curl --cacert "$RA_DEV_STATE/root.crt" -sS -o /dev/null -w '%{http_code}\n' https://localhost:33000/   # 200
export WEB=https://localhost:33000 API=https://localhost:33000/api MAILPIT=http://127.0.0.1:38025
# ... all methods ...
flock .local/evidence-e2e.lock $DC down -v --rmi local --remove-orphans     # self-cleaning (ADR 0033 rule 3)
```

Start `dockerd` first if `docker info` fails; images come through `mirror.gcr.io`. Record `df -h /` before and after.

### G02-01 and G02-02: live tagging journey and real-time latency

```bash
python3 scripts/measure/live_tagging.py --api "$API" --origin "$WEB" --mailpit "$MAILPIT" \
  --cacert "$RA_DEV_STATE/root.crt" --file fixtures/clips/synthetic-60s/clip.mp4 \
  --runs 5 --corrections 50 --json "$GOAL/live-tagging.json"; echo rc=$?
jq '.summary | {runs, runs_passed, tag_to_sheet, corrections: .corrections | {ok, rallies, games, failures, restored_byte_identical, timing}}' "$GOAL/live-tagging.json"
jq -r '.runs[] | .steps | to_entries[] | select(.value.ok != true) | .key' "$GOAL/live-tagging.json"   # must print nothing
```

- **G02-01 actual:** `runs_passed`/`runs`; met only with rc=0 and 5/5. A failing step is the key printed by the last command; its `diffs`, `status` and `code` say why.
- Step 9 (`conflict_kept_needs_verification`) is provisional (C-02, ADR 0009). It must pass, and it is reported on its own line as `@needs-verification`.
- **G02-02 actual:** (a) `corrections.timing.p95_ms`, `n`, `failures`, `restored_byte_identical`; (b) `tag_to_sheet.p95_ms`. The server tag round trip (`tag_server_ms`) is reported, not a target.
- **Browser companion (counts in G02-05):** E2E-02-01 drives the same journey through the UI.

### G02-03: integration-test pass rate

```bash
eval "$(bash scripts/dev-postgres.sh start)"; eval "$(bash scripts/dev-postgres.sh url)"
eval "$(bash scripts/dev-objectstore.sh start)"; eval "$(bash scripts/dev-objectstore.sh env)"
export MAILPIT_API_URL=$MAILPIT SMTP_HOST=127.0.0.1 SMTP_PORT=31025 MAIL_SMTP_URL=smtp://127.0.0.1:31025
(cd backend && env -u APP_ENV uv run pytest -q -p no:cacheprovider -rfEs \
   tests/integration tests/regression tests/unit/sports/pickleball/test_rules_static.py \
   --ignore=tests/integration/test_it_00_10_worker_sandbox_strict.py \
   --junitxml="$GOAL/backend-it.xml"); echo rc=$?
(cd backend && COMPOSE_PROJECT_NAME=racket-goal02 COMPOSE_ENV_FILES="$RA_DEV_STATE/goal.env" env -u APP_ENV \
   uv run pytest -q -rs tests/integration/test_it_00_10_worker_sandbox_strict.py --junitxml="$GOAL/sandbox.xml"); echo rc=$?
python3 scripts/measure/junit_rate.py --include 'test_it_02_|test_bola_matrix' \
  $(for i in 01 02 03 04 05 06 08 09 10 11 12; do printf -- '--require test_it_02_%s_ ' $i; done) \
  --require test_bola_matrix --json "$GOAL/it02-rate.json" "$GOAL/backend-it.xml"; echo rc=$?
python3 scripts/measure/junit_rate.py --include 'test_it_01_|test_rules_static|test_upload_resume|worker_sandbox_strict' \
  $(for i in 01 02 03 04 05 06 07 08 09 10 12 13; do printf -- '--require test_it_01_%s_ ' $i; done) \
  --require test_upload_resume --require worker_sandbox_strict \
  --json "$GOAL/it01-rate.json" "$GOAL/backend-it.xml" "$GOAL/sandbox.xml"; echo rc=$?
```

- IT ids are in sprint-02 §6. Test files are named `test_it_02_<nn>_*.py` so `--require` finds them. If ST-038 is pulled in, add `07` to the first loop.
- The strict sandbox file runs only with the Compose env (smoke F-01, QA-V1-05).
- **Actual:** `rate`, `selected`, `failed`, `skipped`, `missing` from both JSON files. Met only when all four commands give rc=0.

### G02-04: read latency at 50 RPS

```bash
python3 scripts/measure/tag_latency.py --api http://127.0.0.1:38000 --origin "$WEB" --mailpit "$MAILPIT" \
  --rps 50 --duration 60 --json "$GOAL/tag-latency.json"; echo rc=$?
```

- Server-side latency as NFR-010 defines it (the API's published port). The session comes from a magic-link sign-in; the match is tagged with the 6-rally journey first.
- **Actual:** `p95_ms`, `p99_ms`, `availability`, `status_unexpected`, `achieved_rps`. Met only with rc=0.
- **Supporting line (not the measure):** the same with `--api "$API" --cacert "$RA_DEV_STATE/root.crt"` (through TLS and the Next rewrite).

### G02-05: E2E pass rate (and G02-10)

```bash
cd web
flock ../.local/evidence-e2e.lock env MAILPIT_API_URL=$MAILPIT PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers \
  BASE_URL=$WEB PW_PROJECTS=chromium \
  PLAYWRIGHT_JUNIT_OUTPUT_NAME="$GOAL/e2e.xml" PLAYWRIGHT_JSON_OUTPUT_NAME="$GOAL/e2e.json" \
  pnpm exec playwright test --workers=1 --output "$GOAL/pw-out" --reporter=line,junit,json; echo rc=$?
cd ..
python3 scripts/measure/junit_rate.py --include '.' --allow-skips \
  $(for i in 01 02 03 04 05 06; do printf -- '--require E2E-02-%s ' $i; done) \
  --require 'E2E-01-02' --require 'E2E-01-03' --require 'walking-skeleton|walking skeleton' \
  --require 'Signing out leaves nothing behind' --require 'Upload validation' \
  --json "$GOAL/e2e-rate.json" "$GOAL/e2e.xml"; echo rc=$?
jq -r '[.. | objects | select(has("annotations")) | .annotations[]? | select(.type=="skip") | .description] | .[]' "$GOAL/e2e.json"
(cd web && flock ../.local/evidence-e2e.lock env MAILPIT_API_URL=$MAILPIT PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers \
  BASE_URL=$WEB PW_PROJECTS=chromium PLAYWRIGHT_JUNIT_OUTPUT_NAME="$GOAL/e2e-repeat.xml" \
  pnpm exec playwright test --repeat-each=3 --workers=1 --output "$GOAL/pw-out-repeat" --reporter=line,junit)
python3 scripts/ci/flaky_report.py --fail-on-flaky --out "$GOAL/flaky.md" "$GOAL/e2e.xml" "$GOAL/e2e-repeat.xml"; echo rc=$?
```

- The repeat covers **every** spec, root specs included (C-04, QA-R3-E2E-01); in Sprint 1 it covered `e2e/sprint-01` only.
- **Skips:** no E2E-02 test may skip. The printed skip reasons (Sprint 1 specs only) must each name their API binding; at most 6.
- **Actual:** `passed`/`failed`/`skipped`/`rate` from `e2e-rate.json`, then the flaky count. WebKit runs only on CI; a CI WebKit result is supporting evidence and its failures count in G02-11.

### G02-06: browser timings

```bash
cd web
flock ../.local/evidence-e2e.lock env MAILPIT_API_URL=$MAILPIT PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers \
  BASE_URL=$WEB PW_PROJECTS=chromium PLAYWRIGHT_JSON_OUTPUT_NAME="$GOAL/e2e-timing.json" \
  pnpm exec playwright test e2e/sprint-02/timing.spec.ts --repeat-each=20 --workers=1 \
  --output "$GOAL/pw-out-timing" --reporter=line,json; echo rc=$?
cd ..
python3 scripts/measure/pw_timings.py "$GOAL/e2e-timing.json" --min-n 20 \
  --target tag-optimistic=200 --target tap-feedback=100 \
  --target seek-first-frame=1500 --target score-sheet-interactive=2000 \
  --json "$GOAL/timings.json"; echo rc=$?
```

- `timing.spec.ts` (senior-qa-engineer, ST-039) attaches one `timing-<metric>` JSON body `{"ms": n}` per sample. `seek-first-frame` runs with Chromium network emulation at 9 Mbit/s down, 1.5 Mbit/s up and CPU throttling 4× (reference profile, OQ-17); the others on the unthrottled profile.
- **Actual:** each metric's `p95_ms` and `n`. Met only with rc=0 (every metric ≥ 20 samples and within target).

### G02-07: scoring and replay correctness

```bash
cd backend
HYPOTHESIS_PROFILE=ci python3 ../scripts/ci/run_with_budget.py 90 -- env -u APP_ENV uv run pytest -q -rs \
  -m "scoring and not nightly and not red_until" --junitxml="$GOAL/scoring.xml"; echo rc=$?
env -u APP_ENV uv run pytest -q -m "golden_replay" --junitxml="$GOAL/golden-replay.xml"; echo rc=$?
env -u APP_ENV uv run pytest -q --collect-only -m "needs_verification" | tail -1        # "N tests collected": N >= 46
env -u APP_ENV uv run pytest -q -rs -m "needs_verification and not red_until" --junitxml="$GOAL/needs-verification.xml"; echo rc=$?
cd ..
grep -rnE 'red_until\(story="ST-0(26|27|28|29|30|31|32|37|41)"' backend/tests | wc -l         # must be 0
grep -rnE 'red_until\(story="ST-0(33|34|35|36|38)"' backend/tests                            # stretch rows: list them
python3 scripts/measure/junit_rate.py --include '.' --allow-skips --require 'C-01|c_?01' --require 'C-04|c_?04' \
  --require 'P6|projection_equals_(a_)?fold' --require 'P8|replay' --json "$GOAL/scoring-rate.json" "$GOAL/scoring.xml"; echo rc=$?
python3 scripts/measure/junit_rate.py --include '.' --require 'golden_replay' --json "$GOAL/golden-rate.json" "$GOAL/golden-replay.xml"; echo rc=$?
python3 scripts/measure/junit_rate.py --include '.' --require 'SOD|sod' --require 'F-0|f0|fault' --require 'C-02|c_?02' \
  --json "$GOAL/needs-verification-rate.json" "$GOAL/needs-verification.xml"; echo rc=$?
```

- The `golden_replay` marker is added by ST-026/ST-039 (QA registers it in `backend/pyproject.toml`); the test replays every stored fixture match (IT-02-01's 30 rallies, the journey and the conflict game) and compares canonical bytes.
- Only the P3 rally-scoring property may skip; its reason must name FR-043.
- **Actual:** passed/selected of each report; the collected `needs_verification` count; the two grep results. Provisional rows are reported on their own line.

### G02-08: oracle and mutation

```bash
cd backend
env -u APP_ENV uv run python -m tests.oracle.differential --sequences 100000 --json "$GOAL/oracle.json"; echo rc=$?
mv mutants "$GOAL/mutants-stale" 2>/dev/null || true          # cold run (G01-08 note)
env -u APP_ENV uv run --with mutmut==3.8.0 python ../scripts/ci/mutation_score.py --project . \
  --target src/racket/sports/pickleball/rules --tests tests/unit/sports \
  --ignore tests/unit/sports/pickleball/test_rules_static.py --out "$GOAL/mutation-rules.json"; echo rc=$?
mv mutants "$GOAL/mutants-rules" 2>/dev/null || true
env -u APP_ENV uv run --with mutmut==3.8.0 python ../scripts/ci/mutation_score.py --project . \
  --target src/racket/matches/scorebook/domain/projection.py --tests tests/unit/matches --out "$GOAL/mutation-projection.json"; echo rc=$?
```

- The projection module path follows match-aggregate §5; if ST-026 names it differently, the method author changes the `--target` with a decision-log row before the dry-run.
- **Actual:** oracle sequences and disagreements; `score` of each mutation JSON. (b) is met only with score ≥ 0.85.

### G02-09: coverage

```bash
(cd backend && env -u APP_ENV uv run pytest -q -m "(unit or integration or scenario or regression) and not nightly and not red_until" \
   --ignore=tests/integration/test_it_00_10_worker_sandbox.py --ignore=tests/integration/test_it_00_10_worker_sandbox_strict.py \
   --deselect tests/features/test_nightly_quality.py::test_nightly_run_completes \
   --deselect tests/features/test_phone_fixtures.py::test_coverage_of_the_set \
   --deselect tests/features/test_phone_fixtures.py::test_probe_every_fixture \
   --cov --cov-branch --cov-report=xml:"$GOAL/coverage-backend.xml" --cov-report=json:"$GOAL/coverage-backend.json"); echo rc=$?
uvx --from diff-cover==10.6.0 diff-cover "$GOAL/coverage-backend.xml" --compare-branch=2b97fa0 --fail-under=85 \
  --markdown-report "$GOAL/diff-cover.md"; echo rc=$?
(cd backend && uv run coverage report --data-file=.coverage \
  --include='src/racket/sports/pickleball/rules/*,src/racket/matches/match_state.py,src/racket/matches/participants.py,src/racket/matches/scorebook/domain/*')
(cd web && pnpm exec vitest run --coverage --coverage.reporter=text-summary)
```

- The three `--deselect` lines are the Sprint 1 tests that are red only on PO input (S-07, S-08); they stay counted in G02-11. Remove a line as soon as its test can pass (PO items P1, P3). No other test may be deselected.
- If ST-026 names the aggregate modules differently, the method author fixes the `--include` before the dry-run (decision-log row).
- **Actual:** the diff-cover percentage; the include `TOTAL` line and branch percent (from `coverage-backend.json`, same include); the web "Lines" percentage. Met only when the pytest command gives rc=0.

### G02-10: accessibility, from the G02-05 JSON report

```bash
jq '[.. | objects | select(has("attachments")) | .attachments[] | select(.name|startswith("axe-"))] | length' "$GOAL/e2e.json"
jq '[.. | objects | select(has("errors")) | .errors[]? | .message? // "" | select(test("axe serious/critical"))] | length' "$GOAL/e2e.json"   # 0
jq -r '[.. | objects | select(has("attachments")) | .attachments[] | select(.name|startswith("axe-")) | .name] | unique | .[]' "$GOAL/e2e.json"
jq '[.. | objects | select(has("errors")) | .errors[]? | .message? // "" | select(test("targets below 24x24|tagging targets below 48x48"))] | length' "$GOAL/e2e.json"   # 0
```

- Axe attachments are named `axe-<screen id>`; Sprint 2 screen families are T (Quick Tag), K (key map), S (score sheet), H (correction history) and V (rally video), with the screen ids of the Sprint 2 flows file (principal-designer, sprint-02 §4). The 48×48 check covers the tagging controls (NFR-028; ST-027 acceptance).
- E2E-02-02, E2E-02-03 and the score-sheet reflow tests at 320 and 360 px must be among the passed cases of `e2e-rate.json`.
- The manual screen-reader pass (NFR-027b, C-06) is a human item; while it is open it counts in G02-11 (QA-R3-GATE-01), not here.

### G02-11: open defects

```bash
python3 scripts/measure/open_defects.py --json "$GOAL/open-defects.json" docs/sprints/02/review-rounds.md; echo rc=$?
```

- The file starts with the 17 carried Sprint 1 families (planning, 2026-10-05; `open 17`). Reviewers append Open rows for new findings (ADR 0033 rule 1).
- **GitHub:** `mcp__github__search_issues` with `repo:nhuthuynh/racket-analytics is:issue is:open label:bug`; count those labelled `blocker` or `major`.
- **Smoke and blockers:** add any open product-defect rows from `docs/sprints/02/smoke.md` and `blockers.md` not yet in `review-rounds.md`.
- **Actual:** the sum, with the ids in Evidence. A CI run on GitHub is the only evidence that closes the WebKit and CI families.

### G02-12: fast tests

```bash
cd backend
python3 ../scripts/ci/run_with_budget.py 10 -- env -u APP_ENV uv run pytest -q -m unit tests/unit; echo rc=$?
python3 ../scripts/ci/run_with_budget.py 60 -- env -u APP_ENV uv run pytest -q -m unit; echo rc=$?
python3 ../scripts/ci/run_with_budget.py 600 -- env -u APP_ENV uv run pytest -q -m integration tests/integration \
  --ignore=tests/integration/test_it_00_10_worker_sandbox_strict.py; echo rc=$?     # with the G02-03 env
```

- **Actual:** wall time and pass/fail line of each.

## 5. Traceability of targets

| Row | FR / NFR / gate |
|---|---|
| G02-01 | FR-027, FR-049, FR-050, FR-052, FR-053 (a), FR-055; NFR-051, NFR-055, NFR-060, NFR-075; match-aggregate I1, I6, I8, I9 |
| G02-02 | NFR-013 (p95 ≤ 1.5 s, 3-game match); NFR-017 (p95 ≤ 5 s) |
| G02-03 | sprint-02 §6 IT-02-01..IT-02-12; NFR-051 (BOLA diff empty); NFR-023 (quota, C-02); retro 1 L11 (JSON string fuzz, C-01); ADR 0032 (ST-013b) |
| G02-04 | NFR-010 (p95 ≤ 300 ms, p99 ≤ 800 ms at 50 RPS); NFR-041 (99.5%) |
| G02-05 | sprint-02 §6 E2E-02-01..06; NFR-030, NFR-034, NFR-036 (d); NFR-074 |
| G02-06 | NFR-011, NFR-012 (a)(b), NFR-014 |
| G02-07 | FR-049, FR-053 (C-01, C-04 Ready; C-02, C-03 provisional); NFR-001, NFR-002a, NFR-075; ADR 0009 |
| G02-08 | NFR-002b; NFR-072 (gate from Sprint 2) |
| G02-09 | NFR-071; sprint-02 §8 |
| G02-10 | NFR-027 (a), NFR-028, NFR-031, NFR-034; sprint-02 §8 |
| G02-11 | definition-of-done (no open Blocking finding); ADR 0030, ADR 0033 |
| G02-12 | NFR-073 |

## 6. Method dry-runs (ADR 0033 rule 2)

| Row | Method author | Dry-run (date, head, rc) |
|---|---|---|
| G02-01, G02-02 | engineering-manager with principal-engineer | Not yet possible: the Sprint 2 API does not exist. Harness unit tests 81 passed; fail-closed smoke rc=1 (decision-log 2026-10-05) |
| G02-03, G02-07, G02-08, G02-09, G02-12 | senior-qa-engineer | 2026-10-06, heads `0609d6a`..`77a7201` (test-only commits between), QA's own Postgres/object store/Mailpit and Compose `racket-qa02` for the strict sandbox. **G02-03** rc=0 ×4: IT run `458 passed, 2 skipped` (the 2 are the strict sandbox file, run separately: `10 passed`); IT-02 rate 231/231, missing []; IT-01 rate 80/80, missing []. **G02-07** rc=0 after two method fixes (decision-log 2026-10-06): scoring `275 passed, 1 skipped` (P3, FR-043) in 34.9 s; golden replay `4 passed`; `needs_verification` collected 62 (≥ 46); `needs_verification and not red_until` `44 passed`; committed-story `red_until` grep 0; stretch: ST-035 (SOS rows). **G02-08** oracle 100,000 sequences, 0 disagreements, rc=0; mutation rules 0.8635 (≥ 0.85), projection 0.9107 (target path fixed), rc=0. **G02-09** pytest rc=0 (`1871 passed, 1 skipped`); diff-cover 97% (rc=0); rules + aggregates 99.54% line, 98.25% branch (include fixed); web lines 91.02%. **G02-12** rc=124 / 0 / 0: domain run 10 s budget exceeded on this loaded host (pytest itself 7.8-8.5 s; wall 9.5-10.4 s), backend unit 11.2 s, integration 227.9 s |
| G02-04 | sre-devops-engineer | |
| G02-05, G02-06, G02-10 | senior-qa-engineer with sre-devops-engineer | 2026-10-06, head `0609d6a`, Compose `racket-qa02` (https://localhost:43000, SRE-MEDIA in), Chromium 1194. **G02-05** rc=1: `82 passed, 3 failed, 6 skipped` (rate 0.965, every required id present); failures: E2E-02-04 and `seek-first-frame` real link ("this browser cannot decode the H.264 original", blockers.md 2026-10-06) and the stand-in seek (QA-S2-UI-04); 6 skips each name their API binding; `--repeat-each=3` `248 passed`, flaky report rc=1, 1 flaky = the stand-in seek, caused by product defect QA-S2-UI-04 (not a test flake). **G02-06** rc=1: (a) n=160 p95 13.0 ms; (b) n=640 p95 12.6 ms; (c) n=0 (H.264 blocker); (d) n=60 p95 403.1 ms. **G02-10**: 36 axe attachments, 0 serious/critical, 0 target failures; families T, K, S, H, V (V via the stand-in only) and every Sprint 1 family incl. C-22 states |
| G02-11 | engineering-manager | `open_defects.py docs/sprints/02/review-rounds.md` → rc=1, open 17 (planning, 2026-10-05) |
