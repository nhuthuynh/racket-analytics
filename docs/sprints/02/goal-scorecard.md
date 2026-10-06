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
| G02-01 | **Goal works end to end, live (API, real time).** Runs of the full journey over https through the web origin, each as fresh accounts. Every step of a run must pass:<br>1. magic-link sign-in; a doubles match; the 60 s fixture uploaded; "Video received";<br>2. tagging a match with no video → 409 `match_not_ready` (NFR-060);<br>3. game started; 6 rallies tagged; each response carries the reference score;<br>4. score sheet = reference rows; label "unofficial scoring (rules not yet verified)"; `rules_version` present;<br>5. an error credited to the winning side → 422, sheet unchanged;<br>6. a stale `If-Match` → 409 `stale_match`;<br>7. rally 2's winner corrected → rallies 2-6 re-scored (C-01), rally 2 marked corrected, history shows field, old and new value;<br>8. undo → sheet byte-identical to before (C-04), history lists correction and undo;<br>9. 14-rally game, rally 11 corrected → rallies 12-14 kept as `needs_decision` (C-02, `@needs-verification`);<br>10. rally 3 media link: TTL ≤ 900 s, no session token in the URL, Range → 206, tampered signature → 401/403, `start_ms` = the rally's start;<br>11. a second account → 404 on sheet, history and media;<br>12. sign-out | **5 of 5 runs pass (100%)** | `scripts/measure/live_tagging.py --runs 5` | **5/5 runs passed (100%)** (round 3); no failing step; step 9 `@needs-verification` passed 5/5 (needs_decision [12,13,14]) | yes | Round 3, `e4c24bc`, Compose `racket-goal02v3` https://localhost:33000 (fresh volumes). `live_tagging.py --runs 5 --corrections 50` **rc=0** (20.6 s whole method); `runs_passed` 5/5; failing-step query printed nothing. Run 1: tag before video 409, wrong side 422 `invalid_outcome`, stale 409, label "unofficial scoring (rules not yet verified)", `rules_version` PROVISIONAL-UNVERIFIED, conflict diffs [] needs_decision [12,13,14], media TTL 300 s, Range 206, tampered 403, other account 404/404/404. `reports/goal02-v3/live-tagging.json` |
| G02-02 | **Real-time latency of the goal steps, live:** (a) correction command → server-confirmed state on a decided best-of-3 match (seeded, about 100+ rallies), 50 correction + 50 undo commands, and the sheet byte-identical to the baseline afterwards; (b) last tag → score sheet current, over every tag of the 5 G02-01 runs | **(a) p95 ≤ 1,500 ms, ≥ 100 samples, 0 failed commands, restored byte-identical (NFR-013); (b) p95 ≤ 5 s (NFR-017)** | `live_tagging.py --corrections 50` (summary `corrections.timing`, `tag_to_sheet`) | (a) p95 **35.3 ms**, n=100, 0 failures, restored byte-identical (76 rallies, 3 games); (b) p95 **19.0 ms**, n=30 | yes | Round 3, same run as G02-01, rc=0: `corrections.timing` p50 21.2 / p95 35.3 / max 97.0 ms; `tag_to_sheet` p50 13 / p95 19 / max 20 ms. The seeded match is still 76 rallies, not "about 100+" (§7 O-2, unchanged) |
| G02-03 | **Integration-test pass rate** against real Postgres, the object store and Mailpit: (a) every committed Sprint 2 IT id: IT-02-01..IT-02-06 and IT-02-08..IT-02-12 (IT-02-07 too if ST-038 is pulled in), plus the BOLA matrix with its inventory diff (NFR-051); (b) every Sprint 1 IT id, IT-01-01..IT-01-13, and the upload-resume and upload-validation regression suites (no regression) | **(a) 100% passed, 0 failed, 0 skipped, every required id present; (b) 100% passed, 13 of 13 ids** | `pytest --junitxml`, `scripts/measure/junit_rate.py` | (a) **253/253**, 0 failed, 0 skipped, missing []; (b) **80/80**, 0 failed, missing [] | yes | Round 3, `e4c24bc`, own fresh dev Postgres (0 tables at start) and object store (`RA_DEV_STATE=.local/goal02-v3`) + Compose Mailpit: IT run `490 passed, 2 skipped in 250.07s` rc=0 (the 2 = strict sandbox, "needs the Compose stack"); strict sandbox with `COMPOSE_PROJECT_NAME=racket-goal02v3` `10 passed` rc=0; `junit_rate.py` IT-02 rc=0, IT-01 rc=0. IT-01-11 (BOLA) is covered by `test_bola_matrix` in the IT-02 rate. `reports/goal02-v3/it02-rate.json`, `it01-rate.json` |
| G02-04 | **API read latency and availability, live:** an open loop at 50 RPS for 60 s on GET score sheet, GET correction history and GET match, for a tagged match (NFR-010, NFR-041) | **p95 ≤ 300 ms, p99 ≤ 800 ms, availability ≥ 99.5%, 0 unexpected 4xx, achieved rate ≥ 47.5 RPS** | `scripts/measure/tag_latency.py --rps 50 --duration 60` | p95 **16.8 ms**, p99 **54.6 ms**, availability **1.0**, 0 unexpected, 0 5xx, 0 429, **50.0 RPS** (3,000 requests) | yes | Round 3, `e4c24bc`: `tag_latency.py --api http://127.0.0.1:38000 --seed-api https://localhost:33000/api … --rps 50 --duration 60` **rc=0**, p50 10.5 ms, max 101.0 ms. Supporting line through TLS (`--api https://localhost:33000/api`): rc=0, p95 24.7 ms, p99 60.6 ms, availability 1.0, 50.0 RPS. `reports/goal02-v3/tag-latency*.json` |
| G02-05 | **E2E pass rate,** Playwright Chromium over https against the Compose stack, every spec, including:<br>- E2E-02-01 journey v1 (sign in → set up → upload → Quick Tag 6 rallies → sheet = golden sheet);<br>- E2E-02-02 keyboard-only tagging gives the same sheet as tapping;<br>- E2E-02-03 the live region announces each tag, focus stays on the controls;<br>- E2E-02-04 rally row → video playing at the rally;<br>- E2E-02-05 any call fixed in ≤ 2 taps or keys (NFR-036d);<br>- E2E-02-06 undo restores the sheet; correction history;<br>- every Sprint 1 spec (no regression), root specs included (C-04) | **100% of non-skipped tests passed, 0 failed, every E2E-02 id present and not skipped; Sprint 1 skips ≤ 6, each naming its API binding; 0 flaky over 3 repeats of every spec (NFR-074)** | `playwright test` (junit, json) and `junit_rate.py`; `--repeat-each=3` and `flaky_report.py` | **93 passed, 0 failed, 6 skipped** (rate 1.0, missing []); ×3 repeat **279 passed, 18 skipped**; **0 flaky** | yes | Round 3, `e4c24bc`, Chrome for Testing (`/opt/google/chrome/chrome`, `PW_CHROMIUM_CHANNEL=chrome`): `playwright test --workers=1` rc=0 `93 passed (6.7m)`; `junit_rate.py` rc=0 (selected 99); every E2E-02-01..06 case passed, none skipped; 6 skips all Sprint 1, each naming its API binding (6 unique reasons); `--repeat-each=3` rc=0 `279 passed (20.2m)`; `flaky_report.py --fail-on-flaky` rc=0 "2 runs, 99 tests, 0 flaky". WebKit not run (CI only; supporting only) |
| G02-06 | **Browser timings, live** (Playwright `timing.spec.ts`, ST-039; 20 samples each): (a) tap/key → optimistic score visible; (b) any tap/key on the tagging screen → visual feedback; (c) rally row → first video frame playing, 9/1.5 Mbit/s and 4× CPU throttling (reference profile, OQ-17); (d) score sheet interactive, warm | **(a) p95 ≤ 200 ms (NFR-012a); (b) p95 ≤ 100 ms (NFR-012b); (c) p95 ≤ 1,500 ms (NFR-014); (d) p95 ≤ 2,000 ms (NFR-011); each ≥ 20 samples** | `scripts/measure/pw_timings.py` on the timing JSON report | (a) p95 **12.8 ms** n=160; (b) **12.7 ms** n=640; (c) **672.7 ms** n=40 (real H.264 link, 9/1.5 Mbit/s, CPU 4×); (d) **388.5 ms** n=60 | yes | Round 3, `e4c24bc`: `timing.spec.ts --repeat-each=20` rc=0 `80 passed (5.5m)`; `pw_timings.py --min-n 20 …` **rc=0**; (c) max 771.6 ms; the stand-in seek is `unchecked` (not the measure). `reports/goal02-v3/timings.json` |
| G02-07 | **Scoring and replay correctness:**<br>- Ready mechanics and match structure (Sprint 1) plus the projection: empty sheet, projection = fold (P6), replay rows change nothing (P8), corrections C-01 and C-04;<br>- golden replay of every stored fixture match byte-identical under its `rules_version` (NFR-075, QD-TR-04);<br>- provisional rows (`@needs-verification`): ≥ 46 present (16 SOD, 6 F, 12 SOS, 8 M, 4 C; NFR-001), every row of a committed story green, rows `red_until` a stretch story listed separately;<br>- no `red_until` marker names a committed story;<br>- property suite at ≥ 1,000 sequences per scoring system (profile `ci`) | **100% of selected scoring tests passed, 0 failed (P3 skip allowed: FR-043); golden replay 100% byte-identical; ≥ 46 provisional rows collected; 0 `red_until` on committed stories; suite ≤ 90 s** | `pytest -m "scoring and not nightly and not red_until"`, `-m needs_verification --collect-only`, `junit_rate.py`, a `grep` | scoring **304/305 passed, 1 skipped (P3, FR-043)**, 33.2 s wall; golden replay **4/4**; `needs_verification` collected **70** (≥ 46), `needs_verification and not red_until` **52/52**; committed-story `red_until` grep **0**; stretch: ST-035 | yes | Round 3, `e4c24bc`, with the G02-03 env: scoring `304 passed, 1 skipped, 1799 deselected in 31.92s`, "finished in 33.2s, within budget of 90s" rc=0; golden `4 passed` rc=0; `70/2104 tests collected`; nv `52 passed` rc=0; `junit_rate.py` scoring/golden/needs-verification rc=0, missing [] each |
| G02-08 | **Independent engine checks:** (a) differential oracle P9, production engine against the QA oracle (NFR-002b); (b) mutation score on `sports/pickleball/rules` (NFR-072, **a gate from this sprint**); (c) mutation score on the `matches` projection module, baseline | **(a) 100,000 sequences, 0 disagreements; (b) ≥ 0.85; (c) a number recorded (not gated)** | `python -m tests.oracle.differential`; `scripts/ci/mutation_score.py` | (a) **100,000 sequences, 0 disagreements**; (b) **0.8635** (386/447 killed, 0 timeouts); (c) **0.9196** (206/224) | yes | Round 3, `e4c24bc`: `python -m tests.oracle.differential --sequences 100000` rc=0 (61.9 s, seed 20261006); `mutation_score.py` rules rc=0 (cold: no `mutants/` before the run), 63 s; projection rc=0, 19 s. `reports/goal02-v3/oracle.json`, `mutation-*.json` |
| G02-09 | **Coverage (NFR-071):** backend changed lines against the Sprint 1 head `2b97fa0`; rules engine and aggregates (`sports/pickleball/rules`, `matches/match_state.py`, `matches/participants.py`, and the new `matches` aggregate, projection and correction modules); web unit | **Backend changed lines ≥ 85%; rules and aggregates ≥ 95% line and ≥ 90% branch; web ≥ 80% line** | `pytest --cov`, `diff-cover`, `coverage report`, `vitest --coverage` | backend changed lines **97%**; rules + aggregates **99.57% line, 98.41% branch**; web **91.7% lines** | yes | Round 3, `e4c24bc`: pytest --cov rc=0 `2069 passed, 1 skipped, 22 deselected in 414.27s`; `diff-cover --compare-branch=2b97fa0 --fail-under=85` rc=0 "Coverage: 97%" (1346 lines, 40 missing); `coverage json --include=…` 918/922 lines, 309/314 branches; `vitest run --coverage` rc=0, 55 files, 458 tests passed, Lines 91.7% |
| G02-10 | **Accessibility of the Sprint 2 screens** (Quick Tag, key map, score sheet, correction history, rally video) and the fixed Sprint 1 screens: (a) axe serious/critical (WCAG 2.2 AA tags) on every page an E2E test checks; (b) targets below 24×24 CSS px, and tagging controls below 48×48 (NFR-028); (c) keyboard-only tagging and announcements pass (E2E-02-02, E2E-02-03); (d) score sheet at 320 and 360 px with no sideways scrolling (NFR-034) | **(a) 0, with ≥ 1 axe check per Sprint 2 screen family (T, K, S, H, V) and per Sprint 1 family; (b) 0 and 0; (c) passed; (d) passed** | From the G02-05 Playwright JSON report | (a) **0** serious/critical over **37** axe checks, families T, K, S, H, V (`axe-V-01` real video) + every Sprint 1 family; (b) **0 and 0**; (c) E2E-02-02, E2E-02-03 passed; (d) 320 and 360 px passed | yes | Round 3, from `reports/goal02-v3/e2e.json` (the G02-05 run): the four §4 `jq` queries gave 37 / 0 / names (axe-T-01, -T-01-journey, -K-01, -S-01, -S-01-320, -S-01-360, -S-01-journey, -H-01, -V-01, -V-01-stand-in, A/F/G/M/Q/U families …) / 0; junit: the E2E-02-02, E2E-02-03 and sheet 320/360 px cases passed, 0 `<failure>`. Manual screen-reader pass (C-06) counted in G02-11 |
| G02-11 | **Open defects:** blocker or major findings whose latest disposition is open in `docs/sprints/02/review-rounds.md` (which starts with the 17 carried Sprint 1 families), plus open product-defect rows in `smoke.md` and `blockers.md` not yet in review-rounds, plus open GitHub issues labelled `bug` with `blocker` or `major` | **0** | `scripts/measure/open_defects.py`, GitHub issue search (§4) | **2 open** (review-rounds: PD-R1-06/DR-01/DR-02 family blocker, line 437; QA-R3-GATE-01/C-06 major, line 438); GitHub open `bug` issues 0; no smoke/blockers row outside review-rounds | **no** | Round 3, `e4c24bc`: `open_defects.py docs/sprints/02/review-rounds.md` **rc=1** `open 2` (both "Not fixed", principal-designer goal round 2 at `e4c24bc`); `mcp__github__search_issues` owner nhuthuynh repo racket-analytics `is:open label:bug` → total_count 0. CI: latest `sprint-02` run is still 37464553177 on `fd363fa` (success); no CI run at `e4c24bc` (docs-only commits since `6f2f2e7`) |
| G02-12 | **Fast tests (NFR-073):** the domain unit suite; the whole backend unit suite; the backend integration suite | **Domain < 10 s; backend unit ≤ 60 s; integration < 10 min; all 0 failed** | `scripts/ci/run_with_budget.py` | domain **7.1 / 6.8 / 6.8 s** wall (pytest 5.73-6.05 s, `1031 passed, 1 skipped`); backend unit **10.3 s**; integration **210.6 s**; all 0 failed | yes | Round 3, `e4c24bc`: `run_with_budget.py 10 -- … -m unit tests/unit/sports tests/unit/matches tests/unit/players tests/unit/video_ingest` rc=0 ×3; `… 60 -- … -m unit` rc=0 `1466 passed, 1 skipped, 637 deselected in 9.03s`; `… 600 -- … -m integration` rc=0 `431 passed, 2 skipped in 207.35s` (the 2 = strict sandbox via import, passed separately in G02-03). Drift guard `infra/tests/test_goal_scorecard_fast_tests.py` `3 passed` |

**Totals (verification round 3, 2026-10-06, head `e4c24bc`): 11 / 12 met. Sprint 2 goal NOT met** (G02-11: 2 blocker/major findings open, DR-01/DR-02 family and C-06; §9). Round 2 (head `6f2f2e7`): 11 / 12 (§8). Round 1 (head `db0f0be`): 10 / 12 (§7). **Overall:** the Sprint 2 goal is met only when all 12 rows are "yes". A row whose method could not run is "no", never "n/a" (fail closed, ADR 0014). `@needs-verification` results never count toward a Must FR (QD-QG-P5); G02-01 step 9 and G02-07's provisional rows are reported on their own line.

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
python3 scripts/measure/tag_latency.py --api http://127.0.0.1:38000 --seed-api "$API" --origin "$WEB" \
  --cacert "$RA_DEV_STATE/root.crt" --mailpit "$MAILPIT" \
  --rps 50 --duration 60 --json "$GOAL/tag-latency.json"; echo rc=$?
```

- Server-side latency as NFR-010 defines it (the API's published port). The session comes from a magic-link sign-in; the match is tagged with the 6-rally journey first.
- **Seeding goes through the https origin (`--seed-api "$API"`), the load stays on the API port (`--api`)** (SRE-S2-02, QA-RV1-03; decision-log 2026-10-06). On Compose the tus `Location` carries the web's `/api` prefix, which the bare API port does not serve, so seeding on the API port leaves the upload `uploading` and the run exits 1 before any load. The JSON names both bases (`api`, `seed_api`).
- **Actual:** `p95_ms`, `p99_ms`, `availability`, `status_unexpected`, `achieved_rps`. Met only with rc=0.
- **Supporting line (not the measure):** the same with `--api "$API" --cacert "$RA_DEV_STATE/root.crt"` (through TLS and the Next rewrite).

### G02-05: E2E pass rate (and G02-10)

```bash
cd web
test -x /opt/google/chrome/chrome && /opt/google/chrome/chrome --version   # ADR 0036: Chrome for Testing 141.0.7390.54
flock ../.local/evidence-e2e.lock env PW_CHROMIUM_CHANNEL=chrome MAILPIT_API_URL=$MAILPIT PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers \
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
(cd web && flock ../.local/evidence-e2e.lock env PW_CHROMIUM_CHANNEL=chrome MAILPIT_API_URL=$MAILPIT PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers \
  BASE_URL=$WEB PW_PROJECTS=chromium PLAYWRIGHT_JUNIT_OUTPUT_NAME="$GOAL/e2e-repeat.xml" \
  pnpm exec playwright test --repeat-each=3 --workers=1 --output "$GOAL/pw-out-repeat" --reporter=line,junit)
python3 scripts/ci/flaky_report.py --fail-on-flaky --out "$GOAL/flaky.md" "$GOAL/e2e.xml" "$GOAL/e2e-repeat.xml"; echo rc=$?
```

- **Browser (ADR 0036; decision-log 2026-10-06, EM, review round 2):** the `chromium` project runs in Chrome for Testing at `/opt/google/chrome/chrome` (`PW_CHROMIUM_CHANNEL=chrome`), which decodes the H.264 original. Without the variable Playwright's bundled Chromium runs, E2E-02-04 and the real-video seek fail with "this browser cannot decode the H.264 original", and that run is not the evidence for G02-05, G02-06 (c) or G02-10 (V). If the binary is missing, Playwright stops ("Chromium distribution 'chrome' is not found"): the row is "no" (fail closed).
- The repeat covers **every** spec, root specs included (C-04, QA-R3-E2E-01); in Sprint 1 it covered `e2e/sprint-01` only.
- **Skips:** no E2E-02 test may skip. The printed skip reasons (Sprint 1 specs only) must each name their API binding; at most 6.
- **Actual:** `passed`/`failed`/`skipped`/`rate` from `e2e-rate.json`, then the flaky count. WebKit runs only on CI; a CI WebKit result is supporting evidence and its failures count in G02-11.

### G02-06: browser timings

```bash
cd web
flock ../.local/evidence-e2e.lock env PW_CHROMIUM_CHANNEL=chrome MAILPIT_API_URL=$MAILPIT PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers \
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
env -u APP_ENV uv run pytest -q --collect-only -m unit >/dev/null   # unbudgeted bytecode warm-up, as CI
# Domain = CI's DOMAIN_TEST_PATHS (ci.yml env, W-01; NFR-073 "rules + domain"), not the whole tests/unit
python3 ../scripts/ci/run_with_budget.py 10 -- env -u APP_ENV uv run pytest -q -m unit tests/unit/sports tests/unit/matches tests/unit/players tests/unit/video_ingest; echo rc=$?
python3 ../scripts/ci/run_with_budget.py 60 -- env -u APP_ENV uv run pytest -q -m unit; echo rc=$?
python3 ../scripts/ci/run_with_budget.py 600 -- env -u APP_ENV uv run pytest -q -m integration tests/integration \
  --ignore=tests/integration/test_it_00_10_worker_sandbox_strict.py; echo rc=$?     # with the G02-03 env
```

- **Actual:** wall time and pass/fail line of each.
- **Method fix (goal round 1, senior-qa-engineer, decision-log 2026-10-06):** the domain run used `tests/unit` (the whole backend unit suite, 1,415 tests), which CI measures under its own 60 s budget. It now uses the same paths as the CI gate; `infra/tests/test_goal_scorecard_fast_tests.py` fails if the two drift.

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
| G02-04 | sre-devops-engineer (method fix by engineering-manager, SRE-S2-02) | 2026-10-06, head `8af0f77` + the `--seed-api` change, own fresh Compose stack `racket-ems2r1` over HTTPS (clean worktree, `evidence.sh up` rc 0, 9 services healthy; `down` rc 0, volumes and images removed). Old method (no `--seed-api`): **rc=1**, `"video": {"ok": false, "status": "uploading"}`, no load sent (reproduces SRE-S2-02). New method `--api http://127.0.0.1:34800 --seed-api https://localhost:34300/api --origin https://localhost:34300 --cacert root.crt --rps 50 --duration 60`: **rc=0**, 3000 requests, p50 11.1 ms, p95 24.1 ms, p99 73.4 ms, availability 1.0, 0 unexpected, 0 5xx, 0 429, achieved 50.0 RPS. A dry-run, not the verifier's measurement |
| G02-05, G02-06, G02-10 | senior-qa-engineer with sre-devops-engineer | 2026-10-06, head `0609d6a`, Compose `racket-qa02` (https://localhost:43000, SRE-MEDIA in), Chromium 1194. **G02-05** rc=1: `82 passed, 3 failed, 6 skipped` (rate 0.965, every required id present); failures: E2E-02-04 and `seek-first-frame` real link ("this browser cannot decode the H.264 original", blockers.md 2026-10-06) and the stand-in seek (QA-S2-UI-04); 6 skips each name their API binding; `--repeat-each=3` `248 passed`, flaky report rc=1, 1 flaky = the stand-in seek, caused by product defect QA-S2-UI-04 (not a test flake). **G02-06** rc=1: (a) n=160 p95 13.0 ms; (b) n=640 p95 12.6 ms; (c) n=0 (H.264 blocker); (d) n=60 p95 403.1 ms. **G02-10**: 36 axe attachments, 0 serious/critical, 0 target failures; families T, K, S, H, V (V via the stand-in only) and every Sprint 1 family incl. C-22 states |
| G02-11 | engineering-manager | `open_defects.py docs/sprints/02/review-rounds.md` → rc=1, open 17 (planning, 2026-10-05) |
| G02-01, G02-02 (update) | engineering-manager | 2026-10-06 (review round 2), head `48e1e71`, own native https stack `.local/em-rv2` (https://localhost:47943, SRE-MEDIA rule in its Caddy edge; Compose refused by the 16 GB build floor at 12-13 GB free). `live_tagging.py --runs 5 --corrections 50` **rc=0**: 5/5 runs, no failing step (step 9 `@needs-verification` passed); tag_to_sheet p95 17 ms (n=30); corrections p95 28.3 ms (n=100), 0 failures, restored byte-identical (76 rallies, 3 games). The row above ("Not yet possible") is superseded (decision-log 2026-10-06, EM) |
| G02-04 (re-run) | engineering-manager | 2026-10-06, head `48e1e71`, `.local/em-rv2`. `tag_latency.py --api http://127.0.0.1:47911 --seed-api https://localhost:47943/api …` **rc=0**: 3,000 requests, p95 14.5 ms, p99 17.7 ms, availability 1.0, 0 unexpected, 50.0 RPS |
| G02-05, G02-06, G02-10 (Chrome for Testing, ADR 0036) | engineering-manager | 2026-10-06, head `48e1e71`, `.local/em-rv2`, `PW_CHROMIUM_CHANNEL=chrome` (CfT 141.0.7390.54). **G02-05** rc=0: `93 passed, 0 failed, 6 skipped`, rate 1.0, missing [] (E2E-02-04 passed), 6 skips each name their API binding; ×3 repeat rc=0 `279 passed, 18 skipped`, `flaky_report.py --fail-on-flaky` rc=0, 0 flaky. **G02-06** `pw_timings.py` rc=0: (a) p95 11.5 ms n=160; (b) 11.8 ms n=640; (c) 740.1 ms n=40, real H.264 link, reference profile; (d) 392.8 ms n=60. **G02-10**: 37 axe checks incl. `axe-V-01` (real video), 0 serious/critical, 0 target failures; E2E-02-02, E2E-02-03, sheet at 320/360 px passed |

## 7. Verification round 1 (2026-10-06)

- **Verifiers:** senior-qa-engineer with sre-devops-engineer, independent of the builders (round 1). Every method of §4 run for real; nothing marked met from unit tests or reasoning.
- **Head:** `db0f0be84833231ea481946eb7f355e427e5510f` (branch `sprint-02`, clean tree).
- **Stack:** fresh Compose project `racket-goal02v1` (`RA_DEV_STATE=.local/goal02-v1`, ports of §4.0: web 33000, API 38000, Mailpit 38025/31025, Postgres 35432, S3 38333), built with the sandbox-only build-CA override (`extra_ca` build secret, not committed). `bash scripts/disk-precheck.sh` → "ok, 14 GB free on / (floor 10 GB)" rc=0. `flock .local/evidence-e2e.lock docker compose … up -d --build --wait` **rc=0** in 2 m 14 s, 9 services healthy, migrate and objectstore-init exited 0; new volumes `racket-goal02v1_{pgdata,s3data,caddy-data}`; `select count(*) from matches` → 0 (fresh database, fresh bucket). `curl http://localhost:33000/` → 400; `curl --cacert root.crt https://localhost:33000/` → 200. Backend suites used an own dev Postgres and object store under the same `RA_DEV_STATE` (started fresh, stopped and removed at the end).
- **Teardown:** `flock … docker compose … down -v --rmi local --remove-orphans` rc=0; 0 `racket-goal02v1` images and 0 volumes left; dev Postgres and object store stopped and removed. `df -h /` 15 GB free before the build, 13 GB after teardown.
- **Reports:** `reports/goal02-v1/` (git-ignored): `live-tagging.json`, `tag-latency.json`, `e2e.xml`, `e2e.json`, `e2e-rate.json`, `e2e-repeat.xml`, `flaky.md`, `e2e-timing.json`, `timings.json`, `backend-it.xml`, `sandbox.xml`, `it0{1,2}-rate.json`, `scoring*.xml/json`, `golden-*`, `needs-verification*`, `oracle.json`, `mutation-{rules,projection}.json`, `coverage-backend.{xml,json}`, `diff-cover.md`, `open-defects.json`, `g12-*.log`, `demo/*.png`.

### 7.1 Summary

| ID | Target | Actual (round 1) | Met | Owner if not met |
|---|---|---|---|---|
| G02-01 | 5 of 5 journey runs | 5/5, no failing step; step 9 `@needs-verification` 5/5 | yes | |
| G02-02 | (a) p95 ≤ 1,500 ms, ≥ 100, 0 failed, identical; (b) p95 ≤ 5 s | (a) 29.0 ms, n=100, 0 failed, identical; (b) 16.0 ms, n=30 | yes | |
| G02-03 | 100% IT-02 + BOLA; 100% IT-01 (13 ids) | 253/253; 80/80, missing [] | yes | |
| G02-04 | p95 ≤ 300, p99 ≤ 800 ms, ≥ 99.5%, 0 unexpected, ≥ 47.5 RPS | 19.8 / 79.5 ms, 1.0, 0, 50.0 RPS | yes | |
| G02-05 | 100% non-skipped, E2E-02 ids present, ≤ 6 named skips, 0 flaky ×3 | 93/93 (6 named skips), ×3 279 passed, 0 flaky | yes | |
| G02-06 | (a) ≤ 200 (b) ≤ 100 (c) ≤ 1,500 (d) ≤ 2,000 ms p95, n ≥ 20 | 12.8 / 12.9 / 630.6 / 387.3 ms | yes | |
| G02-07 | 100% scoring, golden 100%, ≥ 46 provisional, 0 committed `red_until`, ≤ 90 s | 304 + 1 P3 skip, 34.7 s; 4/4; 70 collected, 52/52; 0 | yes | |
| G02-08 | 100,000 / 0; rules ≥ 0.85; projection recorded | 100,000 / 0; 0.8635; 0.9196 | yes | |
| G02-09 | changed ≥ 85%; rules+aggregates ≥ 95% / 90%; web ≥ 80% | 97%; 99.57% / 98.41%; 91.7% | yes | |
| G02-10 | 0 axe, every family; 0 and 0 targets; E2E-02-02/03; 320/360 | 0 of 37 (T, K, S, H, V + Sprint 1); 0 / 0; passed; passed | yes | |
| G02-11 | 0 open blocker/major | 4 (BE-D1-01, QA-R1-06 ci-gate family, DR-01/DR-02 family, C-06) | **no** | engineering-manager (routes: BE-D1-01 principal-engineer/harness owner; ci-gate sre-devops-engineer; DR-02 principal-designer; C-06 senior-qa-engineer + PO P6) |
| G02-12 | domain < 10 s; unit ≤ 60 s; IT < 10 min | domain rc=124 (then 9.2 s, 10.0 s); 11.5 s; 226.4 s | **no** | senior-qa-engineer |

**Totals: 10 / 12 met. The Sprint 2 goal is not met** under the PO standing rule. The goal's working behaviour (§1 points 1-4) was shown live: G02-01/02/04/05/06/10 and the demo all pass on a fresh https Compose stack. Point 5 ("none [of the carried blockers and majors] is open at the close") is not met (G02-11).

### 7.2 Notes per row (what a skeptic should know)

- **G02-01:** the harness asserts the error codes (`_code(r) == "match_not_ready"` / `"stale_match"`, `live_tagging.py` lines 155, 209), not only the statuses. The whole 5-run + 50-correction method took 20.7 s.
- **G02-05:** the first `--repeat-each=3` attempt was stopped by the verifier after 33/297 tests (a tool timeout of the verifier's own shell, not a test result); its output was deleted and the repeat was re-run from the start; only the complete re-run is the evidence.
- **G02-07:** the §4 command `-m "needs_verification and not red_until"` selects two Postgres tests (`test_it_02_14_*`, added after the QA dry-run). Run in a fresh shell it errors at setup ("DATABASE_URL is not set"), rc=1. With the G02-03 env (as the §4 order implies) it passes 52/52. Method note for the method author (senior-qa-engineer): put the env line into the G02-07 block. Decision-log row added.
- **G02-11:** `open_defects.py` counts 3. BE-D1-01's disposition still reads "Open (harness owner to fix)", although this round's harness runs assert `error.code` and pass; the owner should re-check and close it with evidence, the verifier does not close other roles' rows. C-06 (QA-R3-GATE-01) is "Deferred", not fixed, and §4 G02-10 says it counts here while open. The QA-R1-06 family closes only on a green `ci-gate`, which needs CI (GitHub Actions), not this sandbox. DR-01/DR-02 need the routed role decisions (PD-RV2-DR-FE, -COACH, -BA, -PM, -SEC).
- **G02-12:** the "domain" budget runs `pytest -m unit tests/unit` (1,415 tests). On this 4-core host it took 9.3-10.3 s wall over 3 runs (one rc=124); the QA dry-run also gave rc=124. The suite or its budget needs work, not the host; the verifier does not change the method.
- **Disk:** the E2E ×3 run left 968 MB of Playwright output and free space fell to 9.1 GB after it finished (the live API scripts had run at 10-11 GB and record `disk_free_gb_end` 10). The verifier deleted its own `pw-out*` folders (11 GB free) before G02-06. `/tmp/racket-s3.m6I9Oj` (8.1 GB, not this round's) was left alone. Owner for the disk margin: sre-devops-engineer.
- **WebKit:** not run (WebKit only runs on CI). It is supporting evidence for G02-05 and its CI failures count in G02-11.

### 7.3 Sprint demo (sprint-02 §12), run end to end in real time

Driven in Chrome for Testing against the same stack at 14:45:51 UTC by a temporary, uncommitted Playwright file that uses the QA helpers (`web/e2e/helpers/sprint-02.ts`) for each §12 step; the whole demo took 9.9 s (`1 passed`, rc=0). Screenshots: `reports/goal02-v1/demo/1-taps.png` … `7-video.png`.

| Step | What happened | Time |
|---|---|---|
| setup | New account by magic link, "Saturday doubles" created, fixture uploaded, `video_received` | 1.8 s |
| 1 | Rallies 1-3 by touch; live region: "Rally 1: us. Score 1-0-2." / "Rally 2: them. Score 0-1-1." / "Rally 3: us. Score 0-1-2." | 2.0 s |
| 2 | `?` opened the key map (dialog), Escape closed it; rallies 4-6 keys only: "Score 1-0-1." / "Rally 5: replay. Score 1-0-1." / "Score 2-0-1." | 0.7 s |
| 3 | Sheet: 6 rows = golden rows (server, before → after, winner, ending); label "unofficial scoring (rules not yet verified)"; Rules: PROVISIONAL-UNVERIFIED | 0.5 s |
| 4 | 360 px: no sideways scroll; rows stacked | 0.1 s |
| 5 | Rally 2 switched to your side: after-scores 1-0-2, 2-0-2 … 5-0-2, "corrected by you", history "Rally 2: won by changed from the other side to your side"; undo → sheet JSON identical, history lists the undo | 0.4 s + 0.2 s |
| 6 | 14-rally conflict game, rally 11 → side A: game won 11-0-2 at rally 11; rallies 12-14 kept, marked "needs your decision" (3 rows, with "Move to the next game" / "Remove rally") (`@needs-verification`) | 1.5 s |
| 7 | "Watch rally 3": media 206 through the web origin, `X-Amz-Expires=300`, video playing at 18.006 s for a start of 18.0 s; the same link with one signature character changed → 403 | 1.0 s |
| 8 | This scorecard, filled by the verifier | n/a |
| 9 | Stretch (mid-game start, singles two-number call): not run; ST-033/34/36 not in scope of the committed goal | n/a |
| 10 | Questions to the PO: human step, not runnable here | n/a |

**Observation O-1 (new finding, routed):** at 1280 px the score sheet table is squeezed into the narrow page column, so headers and values break inside words and scores ("Ra / lly / 1", "Sco / re / bef / ore", "0- / 1-1"); see `demo/3-sheet.png` and `demo/6-conflict.png`. No WCAG reflow failure (no sideways scroll) and no metric fails on it, but a score split over two lines is easy to misread. Raised as VR1-01 (minor; principal-designer to confirm severity) in `review-rounds.md`, owner senior-frontend-engineer.

**Observation O-2:** G02-02's description says the correction match is "about 100+ rallies"; the harness seeds a decided 3-game match of 76 rallies. The target itself (≥ 100 samples, p95, identical) is met; the method author (engineering-manager with principal-engineer) should either seed a longer match or change the wording with a decision-log row.


## 8. Verification round 2 (2026-10-06)

- **Verifiers:** senior-qa-engineer with sre-devops-engineer, independent of the builders (round 2). Every method of §4 was run for real against a live stack. No row is marked met from unit tests or from reasoning. The §2 `Actual`/`Met`/`Evidence` cells now hold the round 2 values; the round 1 values stay in §7.
- **Head:** `6f2f2e70f1e3f32a0d39bdb0af12621fbd865e93` (branch `sprint-02`, clean tree). Since round 1 (`db0f0be`), the commits change only the docs, the `open_defects.py` id pattern and the G02-12 method (with its drift-guard test). No product code changed.
- **Disk:** `df -h /` showed 11 GB free. Runbook steps 2-3 (`docker builder prune -af`, `docker image prune -f`; 2.345 GB of build cache) took it to 14 GB. After `up --build` it was 9.9 GB, under the floor. Pruning that build's cache (the images stay) gave `disk-precheck.sh` "ok, 11 GB free" rc=0. `live-tagging.json` `disk_free_gb_end` is 11. Free space was 9.7 GB before teardown and 12 GB after. Another agent's dev Postgres (`/tmp/racket-pg.4CNhZ6`) and SeaweedFS (`/tmp/racket-s3.m6I9Oj`, 9.4 GB) were running and were left alone.
- **Stack:** a fresh Compose project `racket-goal02v2` (`RA_DEV_STATE=.local/goal02-v2`, the §4.0 ports: web 33000, API 38000, Mailpit 38025/31025, Postgres 35432, S3 38333). It was built with the sandbox-only build-CA override (`extra_ca` build secret, not committed). `flock .local/evidence-e2e.lock docker compose … up -d --build --wait` gave **rc=0** in 117 s, with 9 services healthy and migrate and objectstore-init exited 0. The volumes were new (`racket-goal02v2_{pgdata,s3data,caddy-data}`), and `select count(*) from matches` returned 0, so the database and the bucket were fresh. `curl http://localhost:33000/` returned 400, and `curl --cacert root.crt https://localhost:33000/` returned 200. The backend suites used a fresh dev Postgres and object store under the same `RA_DEV_STATE`.
- **Teardown:** `flock … docker compose … down -v --rmi local --remove-orphans` rc=0. It left 0 `racket-goal02v2` images and 0 volumes. `dev-postgres.sh stop` and `dev-objectstore.sh stop` both returned rc=0 ("stopped and removed"). The verifier deleted its own Playwright output (`pw-out*`) and `mutants-*` after each run.
- **Reports:** `reports/goal02-v2/` (git-ignored) holds `live-tagging.json`, `tag-latency.json`, `tag-latency-tls.json`, `e2e.{xml,json,log}`, `e2e-rate.json`, `e2e-repeat.{xml,log}`, `flaky.md`, `e2e-timing.json`, `timings.json`, `backend-it.xml`, `sandbox.xml`, `it0{1,2}-rate.json`, `scoring*`, `golden-*`, `needs-verification*`, `oracle.json`, `mutation-{rules,projection}.json`, `coverage-backend.{xml,json}`, `cov-agg.json`, `diff-cover.md`, `vitest.log`, `open-defects.json`, `g12-*.log`, `demo.log` and `demo/*.png`.

### 8.1 Summary

| ID | Target | Actual (round 2) | Met | Owner if not met |
|---|---|---|---|---|
| G02-01 | 5 of 5 journey runs | 5/5, no failing step; step 9 `@needs-verification` 5/5 | yes | |
| G02-02 | (a) p95 ≤ 1,500 ms, ≥ 100, 0 failed, identical; (b) p95 ≤ 5 s | (a) 28.7 ms, n=100, 0 failed, identical; (b) 19.0 ms, n=30 | yes | |
| G02-03 | 100% IT-02 + BOLA; 100% IT-01 (13 ids) | 253/253; 80/80, missing [] | yes | |
| G02-04 | p95 ≤ 300, p99 ≤ 800 ms, ≥ 99.5%, 0 unexpected, ≥ 47.5 RPS | 17.2 / 64.0 ms, 1.0, 0, 50.0 RPS | yes | |
| G02-05 | 100% non-skipped, E2E-02 ids present, ≤ 6 named skips, 0 flaky ×3 | 93/93 (6 named skips); ×3 279 passed, 0 flaky | yes | |
| G02-06 | (a) ≤ 200 (b) ≤ 100 (c) ≤ 1,500 (d) ≤ 2,000 ms p95, n ≥ 20 | 12.5 / 12.7 / 654.9 / 404.3 ms (n 160/640/40/60) | yes | |
| G02-07 | 100% scoring, golden 100%, ≥ 46 provisional, 0 committed `red_until`, ≤ 90 s | 304 + 1 P3 skip, 34.3 s; 4/4; 70 collected, 52/52; 0 | yes | |
| G02-08 | 100,000 / 0; rules ≥ 0.85; projection recorded | 100,000 / 0; 0.8635; 0.9196 | yes | |
| G02-09 | changed ≥ 85%; rules+aggregates ≥ 95% / 90%; web ≥ 80% | 97%; 99.57% / 98.41%; 91.7% | yes | |
| G02-10 | 0 axe, every family; 0 and 0 targets; E2E-02-02/03; 320/360 | 0 of 37 (T, K, S, H, V + Sprint 1); 0 / 0; passed; passed | yes | |
| G02-11 | 0 open blocker/major | **2**: PD-R1-06/DR-01/DR-02 family (blocker), QA-R3-GATE-01/C-06 (major) | **no** | principal-designer (DR-02 design review and the routed cells PD-RV2-DR-FE/-COACH/-BA/-PM/-SEC; EM escalates to the PO if not held by end of 2026-10-07); senior-qa-engineer with the PO (C-06: VoiceOver/TalkBack pass needs a human with devices, PO item P6) |
| G02-12 | domain < 10 s; unit ≤ 60 s; IT < 10 min; 0 failed | 7.0 s ×3; 11.0 s; 217.5 s; 0 failed | yes | |

**Totals (round 2): 11 / 12 met. The Sprint 2 goal is not met** under the PO standing rule. Goal points 1-4 work live: G02-01/02/04/05/06/10 and the demo (§8.3) all pass on a fresh https Compose stack. Point 5 ("none [of the carried blockers and majors] is open at the close") is not met, because G02-11 has 2 open. Neither of the 2 open findings can be closed in this sandbox. One needs design-review decisions by named roles. The other needs a human screen-reader pass on real devices.

### 8.2 Notes per row (what a skeptic should know)

- **G02-12, the method changed between rounds.** Round 1 failed on the domain run (`-m unit tests/unit`, the whole backend unit suite). In goal round 1, QA (the routed owner) changed the method to CI's `DOMAIN_TEST_PATHS` (`tests/unit/{sports,matches,players,video_ingest}`), with a decision-log row and a drift-guard test.
  - QA's own earlier row (decision-log 2026-10-06, "G02-12 domain budget") had said the scope of "domain" was the EM's and the principal-engineer's call. QA then made the change itself.
  - The verifiers accept the change for three reasons. NFR-073 says "Rules + domain unit suite". The paths equal the CI gate's paths (set at W-01, before round 1). The target (10 s) is unchanged.
  - Two facts for the reader. First, the paths leave out `tests/unit/analysis_jobs` and `tests/unit/dataset`. Second, under the round 1 method the row would still fail: the whole unit suite took 11.0 s wall this round.
  - The EM or the principal-engineer should confirm the scope in a decision-log row. This is not a blocker for the row.
- **G02-11:** `open_defects.py` now counts C-06 itself (row 421 "Not fixed"), so no manual addition is needed. GitHub `is:open label:bug` returned 0.
  - CI evidence: run 37464553177 at `fd363fa` is `success`. That supports the "Fixed on CI" row for the QA-R1-06 family.
  - No CI run exists at the verified head `6f2f2e7`. The commits after `fd363fa` are docs, measure-harness and infra-test commits, so this is supporting evidence only.
- **G02-03:** the 2 skips in the main IT run are the strict-sandbox file (needs the Compose stack). It passed separately against `racket-goal02v2` with `10 passed`, as in round 1.
- **G02-05:** the 6 skips are Sprint 1 tests. Each skip annotation appears twice in the JSON report (two reporters), which makes 12 lines for 6 tests.
- **WebKit:** not run, because WebKit runs only on CI. It is supporting evidence for G02-05, and its failures would count in G02-11.
- **No metric was "could not run" in round 2.** Every method ran in this sandbox.

### 8.3 Sprint demo (sprint-02 §12), run end to end in real time

The demo was driven in Chrome for Testing against the same stack, starting 16:02:15 UTC. It used a temporary, uncommitted Playwright file (deleted after the run) built on the QA helpers (`web/e2e/helpers/sprint-02.ts`), one step per §12 item. Result: `1 passed (10.0s)`, rc=0; the steps took 8.5 s from first to last. Screenshots are `reports/goal02-v2/demo/1-taps.png` … `7-video.png`.

| Step | What happened | Time |
|---|---|---|
| setup | New account by magic link; "Saturday doubles" created; fixture uploaded; status `video_received` | 1.8 s |
| 1 | Rallies 1-3 tagged by touch. Live region: "Rally 1: us. Score 1-0-2." / "Rally 2: them. Score 0-1-1." / "Rally 3: us. Score 0-1-2." | 2.0 s |
| 2 | `?` opened the key map (dialog) and Escape closed it. Rallies 4-6 tagged by keys only: "Rally 4: us. Score 1-0-1." / "Rally 5: replay. Score 1-0-1." / "Rally 6: us. Score 2-0-1." | 0.8 s |
| 3 | Sheet: 6 rows matched the golden rows (`JOURNEY_ROWS`). Label "unofficial scoring (rules not yet verified)" visible; Rules: PROVISIONAL-UNVERIFIED | 0.7 s |
| 4 | At 360 px: no sideways scroll; rows stacked | 0.2 s |
| 5 | Rally 2 switched to your side. After-scores became 1-0-2, 2-0-2, 3-0-2, 4-0-2, 4-0-2, 5-0-2, with "corrected by you" and history "Rally 2: won by changed from the other side to your side". Undo gave an identical sheet JSON, and the history lists the undo | 0.6 s |
| 6 | 14-rally conflict game: rally 11 switched to side A. The game was won 11-0-2 at rally 11. All 14 rows were kept, and rallies 12-14 were marked "needs your decision" (3 visible) (`@needs-verification`) | 1.6 s |
| 7 | "Watch rally 3": media returned 206 through the web origin `https://localhost:33000`, with `X-Amz-Expires=300`. The video played at 18.025 s for a start of 18.0 s. The same link with one signature character changed returned 403 | 0.9 s |
| 8 | This scorecard, filled by the verifier. Open defects are 2, not 0 (G02-11) | n/a |
| 9 | Stretch (mid-game start, singles two-number call): not run. ST-033/34/36 are not in the committed goal | n/a |
| 10 | Questions to the PO: a human step, not runnable here | n/a |

**Observation (VR1-01, still open, minor, already routed to senior-frontend-engineer):** at 1280 px the score sheet table is still squeezed into the narrow page column (`demo/3-sheet.png`). Headers and cells still break inside words and scores ("Ra / lly", "Sco / re / bef / ore", "0- / 1-1"). The Start column also breaks a time across three lines ("0: / 1 / 8"). No metric fails on it, and it is not counted in G02-11 (minor). No new finding was raised in round 2.

**Observation O-2 (unchanged):** the G02-02 correction match is still 76 rallies, not "about 100+". The target is met; the wording still needs the method author's decision-log row.

## 9. Verification round 3 (2026-10-06)

- **Verifiers:** senior-qa-engineer with sre-devops-engineer, independent goal verifiers (round 3). We did not build this. Every method of §4 was run for real against a live stack started from a clean state. No row is marked met from unit tests or reasoning. The §2 `Actual`/`Met`/`Evidence` cells now hold the round 3 values; round 2 stays in §8, round 1 in §7.
- **Head:** `e4c24bc29aad7748826ca78f3e024c8a3d0a1215` (branch `sprint-02`, clean tree). Since round 2 (`6f2f2e7`) only `decision-log.md`, `goal-scorecard.md` and `review-rounds.md` changed (`git diff --stat 6f2f2e7 HEAD`: 3 files, docs only). No product, test or harness code changed, so round 3 is a fresh re-measurement of the same product, not of a fix.
- **Disk:** `disk-precheck.sh` "ok, 13 GB free" rc=0 before the build; 11 GB after `up --build`; `docker builder prune -af` (2.345 GB, this build's cache) then "ok, 12 GB free" rc=0. `live-tagging.json` `disk_free_gb_end` 12. Free space fell to 9.4 GB by the end (after coverage, mutation and Playwright output; all live API, E2E and timing runs had finished above the floor), 14 GB after teardown. Owner for the disk margin stays sre-devops-engineer (round 1 note).
- **Stack (fresh):** Compose project `racket-goal02v3`, `RA_DEV_STATE=.local/goal02-v3`, the §4.0 env (identical to round 2's `goal.env`, checked with `diff`), plus the sandbox-only build-CA override (`extra_ca` build secret from `/root/.ccr/ca-bundle.crt`, not committed). No `racket` containers, images or volumes existed before. `flock .local/evidence-e2e.lock docker compose … up -d --build --wait` **rc=0** in 120 s; 9 services healthy, `migrate` and `objectstore-init` exited 0 ("created bucket racket-media"); new volumes `racket-goal02v3_{pgdata,s3data,caddy-data}`; `psql … "select count(*) from matches"` → 0. `curl http://localhost:33000/` → 400; `curl --cacert root.crt https://localhost:33000/` → 200 (HTTPS, no insecure-cookie flag). Backend suites used a fresh dev Postgres (`/tmp/racket-pg.qeO5a0`, 0 public tables at start) and object store under the same `RA_DEV_STATE`.
- **Teardown:** `flock … docker compose … down -v --rmi local --remove-orphans` rc=0; 0 `goal02v3` images, 0 volumes, 0 running containers. `dev-postgres.sh stop` and `dev-objectstore.sh stop` rc=0 ("stopped and removed"). The verifier deleted its own `pw-out*` and `mutants-*` folders and the temporary demo spec.
- **Reports:** `reports/goal02-v3/` (git-ignored): `live-tagging.{json,log}`, `tag-latency{,-tls}.{json,log}`, `e2e.{xml,json,log}`, `e2e-rate.json`, `e2e-repeat.{xml,log}`, `flaky.md`, `e2e-timing.json`, `timing.log`, `timings.json`, `backend-it.{xml,log}`, `sandbox.{xml,log}`, `it0{1,2}-rate.json`, `scoring*`, `golden-*`, `needs-verification*`, `oracle.{json,log}`, `mutation-{rules,projection}.{json,log}`, `coverage-backend.{xml,json}`, `coverage.log`, `cov-agg.json`, `diff-cover.md`, `vitest.log`, `open-defects.json`, `g12-*.log`, `demo.log`, `demo/*.png`.

### 9.1 Summary

| ID | Target | Actual (round 3) | Met | Owner if not met |
|---|---|---|---|---|
| G02-01 | 5 of 5 journey runs | 5/5, no failing step; step 9 `@needs-verification` 5/5 | yes | |
| G02-02 | (a) p95 ≤ 1,500 ms, ≥ 100, 0 failed, identical; (b) p95 ≤ 5 s | (a) 35.3 ms, n=100, 0 failed, identical; (b) 19.0 ms, n=30 | yes | |
| G02-03 | 100% IT-02 + BOLA; 100% IT-01 (13 ids) | 253/253; 80/80, missing [] | yes | |
| G02-04 | p95 ≤ 300, p99 ≤ 800 ms, ≥ 99.5%, 0 unexpected, ≥ 47.5 RPS | 16.8 / 54.6 ms, 1.0, 0, 50.0 RPS | yes | |
| G02-05 | 100% non-skipped, E2E-02 ids present, ≤ 6 named skips, 0 flaky ×3 | 93/93 (6 named skips); ×3 279 passed, 0 flaky | yes | |
| G02-06 | (a) ≤ 200 (b) ≤ 100 (c) ≤ 1,500 (d) ≤ 2,000 ms p95, n ≥ 20 | 12.8 / 12.7 / 672.7 / 388.5 ms (n 160/640/40/60) | yes | |
| G02-07 | 100% scoring, golden 100%, ≥ 46 provisional, 0 committed `red_until`, ≤ 90 s | 304 + 1 P3 skip, 33.2 s; 4/4; 70 collected, 52/52; 0 | yes | |
| G02-08 | 100,000 / 0; rules ≥ 0.85; projection recorded | 100,000 / 0; 0.8635; 0.9196 | yes | |
| G02-09 | changed ≥ 85%; rules+aggregates ≥ 95% / 90%; web ≥ 80% | 97%; 99.57% / 98.41%; 91.7% | yes | |
| G02-10 | 0 axe, every family; 0 and 0 targets; E2E-02-02/03; 320/360 | 0 of 37 (T, K, S, H, V + Sprint 1); 0 / 0; passed; passed | yes | |
| G02-11 | 0 open blocker/major | **2**: PD-R1-06/DR-01/DR-02 family (blocker), QA-R3-GATE-01/C-06 (major) | **no** | principal-designer (DR-02 review held with the routed decider cells PD-RV2-DR-FE/-COACH/-BA/-PM/-SEC filled by their roles; EM escalates to the PO if not held by end of 2026-10-07); senior-qa-engineer with a human tester and the PO (C-06: VoiceOver/TalkBack pass on real devices, PO item P6) |
| G02-12 | domain < 10 s; unit ≤ 60 s; IT < 10 min; 0 failed | 7.1 / 6.8 / 6.8 s; 10.3 s; 210.6 s; 0 failed | yes | |

**Totals (round 3): 11 / 12 met. The Sprint 2 goal is NOT met** under the PO standing rule. Goal points 1-4 work live on a fresh HTTPS Compose stack (G02-01/02/04/05/06/10 and the demo, §9.3). Point 5 ("none [of the carried blockers and majors] is open at the close") is not met: G02-11 = 2. Neither can be closed in this sandbox: one needs design-review decisions by named roles, the other a human screen-reader pass on real devices. Every other method ran here; no row is "no" because its method could not run.

### 9.2 Notes per row (what a skeptic should know)

- **Nothing changed in the product since round 2**, so rounds 2 and 3 measure the same code. The value of this round is reproducibility on a new clean stack: every number is within normal run-to-run noise of round 2 (largest move: G02-02 (a) p95 28.7 → 35.3 ms, still 42× under target).
- **G02-11:** `open_defects.py` rc=1, `open 2`; both rows read "Not fixed" after the principal-designer's goal round 2 at `e4c24bc`. The verifier does not close or downgrade other roles' rows. GitHub `is:open label:bug` total_count 0. No CI run exists at `e4c24bc`; the last `sprint-02` CI run (37464553177, `fd363fa`) is `success` and stays supporting evidence only.
- **G02-03:** the method requires 12 `test_it_01_*` ids; the 13th Sprint 1 id, IT-01-11, is the BOLA matrix, required as `test_bola_matrix` in the IT-02 rate (253/253). No file `test_it_01_11_*` exists; this matches the method, but the method author may want to say so in §4.
- **G02-12:** the integration run's 2 skips are the strict-sandbox tests (collected through an import despite `--ignore`; reason "needs the Compose stack"). They passed separately against `racket-goal02v3` (`10 passed`, G02-03). The domain scope note of §8.2 still applies (EM/principal-engineer decision-log row not yet written).
- **Ordering, to avoid load bias:** all timed browser runs (G02-05, its ×3 repeat, G02-06) and G02-07/G02-12 budgets ran with no other heavy job on the host. Only the IT run of G02-03 (no time target) and the oracle overlapped the ×3 E2E repeat; the repeat still gave 0 flaky.
- **WebKit:** not run; WebKit runs only on CI (GitHub Actions). Supporting evidence for G02-05 only; it is not a goal metric here.

### 9.3 Sprint demo (sprint-02 §12), run end to end in real time

Driven in Chrome for Testing against the same live stack, starting 16:40:19 UTC, by a temporary, uncommitted Playwright file (`web/e2e/zz-demo-vr3.spec.ts`, deleted right after the run and before the ×3 repeat so it was never collected by an evidence run) built on the QA helpers (`web/e2e/helpers/sprint-02.ts`). Result: `1 passed (9.6s)`, rc=0. Screenshots: `reports/goal02-v3/demo/1-taps.png` … `7-video.png`.

| Step | What happened | Time |
|---|---|---|
| setup | New account by magic link; "Saturday doubles" created; fixture uploaded through the web origin; status `video_received` | 1.5 s |
| 1 | Rallies 1-3 tagged by touch. Live region: "Rally 1: us. Score 1-0-2." / "Rally 2: them. Score 0-1-1." / "Rally 3: us. Score 0-1-2." | 1.9 s |
| 2 | `?` opened the key map dialog; Escape closed it. Rallies 4-6 by keys only: "Rally 4: us. Score 1-0-1." / "Rally 5: replay. Score 1-0-1." / "Rally 6: us. Score 2-0-1." | 0.8 s |
| 3 | Sheet: 6 rows equal the golden rows (`JOURNEY_ROWS`: server, before → after, winner, ending); "unofficial scoring (rules not yet verified)" visible; "Rules: PROVISIONAL-UNVERIFIED" on the page | 0.7 s |
| 4 | 360 px: no sideways scroll; rows stacked | 0.2 s |
| 5 | Rally 2 switched to your side: after-scores 1-0-2, 2-0-2, 3-0-2, 4-0-2, 4-0-2, 5-0-2, "corrected by you", history "Rally 2: won by changed from the other side to your side". Undo: sheet JSON byte-identical to before; history lists "Undone: …" | 0.6 s |
| 6 | 14-rally conflict game (side A wins 1-10, B wins 11, A wins 12-14; game won at rally 14, 11-0-1). Rally 11 switched to your side: game won 11-0-2 at rally 11; all 14 rows kept; `needs_decision` [12, 13, 14]; "needs your decision" shown 3 times (`@needs-verification`) | 1.5 s |
| 7 | "Watch rally 3": media 206 through `https://localhost:33000`, `X-Amz-Expires=300`; video at 18.008 s for a start of 18.0 s; the same link with one signature character changed → 403 | 0.9 s |
| 8 | This scorecard, filled by the verifier: 11 / 12; open defects 2, not 0 | n/a |
| 9 | Stretch (mid-game start, singles two-number call): not run; ST-033/34/36 are not in the committed goal | n/a |
| 10 | Questions to the PO: a human step, not runnable here | n/a |

**Observation (VR1-01, still open, minor, routed to senior-frontend-engineer):** reproduced again at 1280 px (`demo/3-sheet.png`): the score sheet table sits in the narrow page column; headers and cells break inside words and scores ("Ra / lly", "Sco / re / bef / ore", "0- / 1-1", "0: / 1 / 8"). No metric fails on it and it is not counted in G02-11 (minor). No new finding raised in round 3.

**Observation O-2 (unchanged):** the G02-02 correction match is still 76 rallies, not "about 100+"; target met; wording still needs the method author's (engineering-manager with principal-engineer) decision-log row.
