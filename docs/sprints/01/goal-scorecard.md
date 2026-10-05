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
| G01-01 | **Goal works end to end, live.** Runs of the full API journey over https through the web origin, each as a fresh account. One run covers the following steps, and every step must pass:<br>1. magic link via Mailpit, then exchange;<br>2. `GET /me`;<br>3. a doubles match with 4 nicknames and one "me";<br>4. tus upload with a connection drop at ≥ 40% and a resume from the HEAD offset;<br>5. a damaged chunk refused with 460 and the offset kept;<br>6. upload to the end;<br>7. "Video received" with probed facts;<br>8. a 12 GB `Upload-Length` refused with 413, and a PDF named `.mp4` refused with 415;<br>9. sign-out, after which the old session gets 401 | **5 of 5 runs pass (100%)** | `scripts/measure/live_goal.py --runs 5` | 5 of 5 runs passed (100%) | yes | Head `e76fb96` (code tree; `HEAD` moved to `7a9e41e` mid-run, a docs-only blockers.md row), verification round 3 (independent), run `racket-gv3` (fresh volumes, ports 23000/28000/28025/21025, `RA_DEV_STATE=.local/gv3`): `live_goal.py --api https://localhost:23000/api --origin https://localhost:23000 --mailpit http://127.0.0.1:28025 --cacert $RA_DEV_STATE/root.crt --file fixtures/clips/synthetic-60s/clip.mp4 --runs 5` → rc=0, `runs_passed 5`; `jq '[.runs[].steps[]\|.ok]\|all'` → true. Every run: link 202, exchange 200, `/me` 200, upload create 201, drop at 40.0% and resume from HEAD offset 689,684, damaged chunk 460, `video_received` with facts 60,000 ms 60 fps 1920×1080 h264, 12 GB 413, PDF PATCH 415 (match stays `awaiting_upload`), sign-out 204 then `/me` 401. `disk_free_gb_start 10`, `_end 10` |
| G01-02 | **Integration-test pass rate:** (a) every Sprint 1 IT id, IT-01-01..IT-01-13, against real Postgres, the object store and Mailpit, plus the Compose worker sandbox for IT-01-10's no-network part; (b) the upload-resume and upload-validation regression suites | **(a) 100% passed, 0 failed, 0 skipped, 13 of 13 ids present; (b) 100% passed** | `pytest --junitxml` and `scripts/measure/junit_rate.py` | (a) 69/69 passed, 0 failed, 0 skipped, `missing []`; (b) 41/41 passed | yes | Head `e76fb96` (code tree; `HEAD` moved to `7a9e41e` mid-run, a docs-only blockers.md row), verification round 3 (independent), run `racket-gv3` (fresh volumes, ports 23000/28000/28025/21025, `RA_DEV_STATE=.local/gv3`): fresh `dev-postgres` and `dev-objectstore` (new `racket-media` bucket) under `.local/gv3`, Mailpit `127.0.0.1:28025`, SMTP `21025`. First pytest (§4 G01-02) → rc=0, `223 passed, 2 skipped in 58.33s`; the 2 skips (junit) are `tests.integration.test_it_00_10_worker_sandbox` (Sprint 0), outside both includes. Strict sandbox with `COMPOSE_PROJECT_NAME=racket-gv3` → rc=0, `10 passed in 1.57s`. `it-rate.json` rc=0 `selected 69 passed 69 skipped 0 missing [] ok true`; `regression-rate.json` rc=0 `selected 41 passed 41 ok true` |
| G01-03 | **E2E journey pass rate,** Playwright Chromium over https against the Compose stack. All specs, including:<br>- E2E-01-01 (the walking skeleton plus first run and guide);<br>- E2E-01-02 (network cut at about 40%);<br>- E2E-01-03 (keyboard-only setup);<br>- sign-out;<br>- validation | **100% of non-skipped tests passed, 0 failed, ≤ 6 skipped (each names its API binding); 0 flaky over 3 repeats (NFR-074)** | `playwright test` (junit) and `junit_rate.py --allow-skips`; then `--repeat-each=3` | 58 selected, 52 passed, 0 failed, 6 skipped (rate 1.0). Repeat ×3: 135 passed, 0 failed, 18 skipped. 0 flaky (Chromium) | yes | Head `e76fb96` (code tree; `HEAD` moved to `7a9e41e` mid-run, a docs-only blockers.md row), verification round 3 (independent), run `racket-gv3` (fresh volumes, ports 23000/28000/28025/21025, `RA_DEV_STATE=.local/gv3`): `MAILPIT_API_URL=http://127.0.0.1:28025 PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers BASE_URL=https://localhost:23000 PW_PROJECTS=chromium pnpm exec playwright test --workers=1 --reporter=line,junit,json` → rc=0, `52 passed, 6 skipped (3.2m)`. `junit_rate.py … --allow-skips` (6 `--require`) → rc=0, `selected 58 passed 52 failed 0 skipped 6 rate 1.0 missing []`. Each of the 6 skip reasons (from `e2e.json` annotations) names its API binding. `e2e/sprint-01 --repeat-each=3` → rc=0, `135 passed, 18 skipped (8.2m)`. `flaky_report.py --fail-on-flaky` → rc=0, "2 runs, 58 tests, 0 flaky". Chromium only: WebKit is not installed in this sandbox (`/opt/pw-browsers` has Chromium only) and runs only on CI; CI run 37372059078 (`sprint-01`@`e76fb96`) was still `queued` at the end of this round, and its WebKit defects count in G01-11 |
| G01-04 | **API read latency and availability, live:** an open loop at 50 RPS for 60 s on `GET /matches/{id}`, `GET /matches` and `GET /me` (NFR-010, NFR-041) | **p95 ≤ 300 ms, p99 ≤ 800 ms, availability ≥ 99.5%, 0 unexpected 4xx, achieved rate ≥ 47.5 RPS** | `scripts/measure/api_latency.py --rps 50 --duration 60` | p95 12.79 ms, p99 49.52 ms, availability 100%, 0 unexpected 4xx, 0 5xx, 0 429, 50.01 RPS (3,000 requests) | yes | Head `e76fb96` (code tree; `HEAD` moved to `7a9e41e` mid-run, a docs-only blockers.md row), verification round 3 (independent), run `racket-gv3` (fresh volumes, ports 23000/28000/28025/21025, `RA_DEV_STATE=.local/gv3`): `api_latency.py --api http://127.0.0.1:28000 --origin https://localhost:23000 --mailpit http://127.0.0.1:28025 --rps 50 --duration 60` → rc=0, `ok true`, `p50_ms 8.70`, `max_ms 118.2`. Supporting line through TLS and the Next rewrite (`--api https://localhost:23000/api --cacert …`) → rc=0, p95 20.19 ms, p99 54.53 ms, 100%, 50.01 RPS |
| G01-05 | **Upload throughput, live:** sustained ingest of a ≥ 1 GB valid 1080p60 H.264 file through the https web origin, in 8 MiB chunks (ADR 0019), with sha256 `Upload-Checksum` on every chunk (NFR-016b) | **≥ 50 Mbit/s, and the final offset equals the file length** | `make_large_fixture.sh`, then `live_goal.py --file <1 GB>` | Measured 541.8 Mbit/s, final offset 1,052,798,536 = file size, rc=0. **Not valid evidence:** the run ended under the 10 GB disk floor (`disk_free_gb_end 9`) | no | Head `e76fb96` (code tree; `HEAD` moved to `7a9e41e` mid-run, a docs-only blockers.md row), verification round 3 (independent), run `racket-gv3` (fresh volumes, ports 23000/28000/28025/21025, `RA_DEV_STATE=.local/gv3`): `make_large_fixture.sh /dev/shm/gv3/large-1080p60.mp4 120` → rc=0, 1,052,798,536 bytes, ffprobe h264 1920×1080 60/1 120.0 s (fixture on tmpfs to spare disk). `live_goal.py --api https://localhost:23000/api … --file /dev/shm/gv3/large-1080p60.mp4 --runs 1 --result-timeout 300` → rc=0, `runs_passed 1`. `upload_complete`: ok true, bytes 1052798536, transfer_s 15.546, throughput_mbps 541.8. Drop at 40.6% (server offset 427,819,008), damaged chunk 460, facts 120,000 ms 60 fps 1920×1080, 413/415, sign-out 401. But `disk_free_gb_start 10`, **`disk_free_gb_end 9`**. A first run had the same result (562.1 Mbit/s, `_end 9`, kept as `live-goal-large-run1-invalid-disk.json`). docs/ops/disk-and-prune.md: "A run whose `disk_free_gb_end` is under the floor is not valid evidence; prune and run it again." Pruning was exhausted: build cache step 2 reclaimed 5.119 GB (6.1 G → 11 G free), own volumes were recreated, and removing the stale images of finished rounds (5.5 GB reclaimable) was **denied by the session permission policy**. So the method cannot give valid evidence in this sandbox in its current disk state; fail closed (ADR 0014). `df -h /` 11 G before the run, 9.6 G after; `nproc` 4 |
| G01-06 | **Real-time latency of the goal steps,** p95 over the 5 G01-01 runs: (a) from the link request to a signed-in session, including email delivery by the mailer worker; (b) from the final byte to "Video received" with facts, for the 60 s fixture | **(a) ≤ 10 s; (b) ≤ 30 s** (judgment, decision-log 2026-10-05) | From the G01-01 JSON: `sign_in_p95_s`, `final_byte_to_facts_p95_s` | (a) 1.058 s; (b) 0.879 s | yes | Head `e76fb96` (code tree; `HEAD` moved to `7a9e41e` mid-run, a docs-only blockers.md row), verification round 3 (independent), run `racket-gv3` (fresh volumes, ports 23000/28000/28025/21025, `RA_DEV_STATE=.local/gv3`): from the G01-01 summary: `sign_in_p95_s 1.058` (runs 0.44/0.245/1.058/1.055/0.85 s), `final_byte_to_facts_p95_s 0.879`. Large-file run: 0.483 s and 0.604 s. Demo (real browser): sign-in 1.55 s |
| G01-07 | **Scoring correctness:**<br>- Ready mechanics, §7.7;<br>- match structure M-01..M-08;<br>- property suite P1-P8 at ≥ 1,000 sequences per scoring system (Hypothesis profile `ci`);<br>- the provisional golden rows SOD-01..12, SOD-16 and F-01..06, reported separately as `@needs-verification` | **100% of scoring tests passed, 0 failed (P3 skip allowed: FR-043); 100% of `needs_verification` cases passed and listed separately (≥ 19 rows); suite time ≤ 90 s** | `pytest -m "scoring and not nightly"` and `-m "scoring and needs_verification"`, with junit and `junit_rate.py` | 204/205 passed, 0 failed, 1 skipped (P3, FR-043), 32.5 s. `needs_verification`: 26/26 passed, 0 skipped | yes | Head `e76fb96` (code tree; `HEAD` moved to `7a9e41e` mid-run, a docs-only blockers.md row), verification round 3 (independent), run `racket-gv3` (fresh volumes, ports 23000/28000/28025/21025, `RA_DEV_STATE=.local/gv3`): `HYPOTHESIS_PROFILE=ci run_with_budget.py 90 -- … pytest -q -rs -m "scoring and not nightly"` → rc=0, `204 passed, 1 skipped, 879 deselected in 31.50s`, budget 32.5 s. `-m "scoring and needs_verification"` → rc=0, `26 passed, 1058 deselected`. `scoring-rate.json` rc=0 `selected 205 passed 204 skipped 1 missing [] ok true`; `needs-verification-rate.json` rc=0 `selected 26 passed 26 ok true`. Skip reason: "P3 is rally scoring: blocked on FR-043 / OQ-01". The 26 provisional rows are reported only as `@needs-verification`; the first-run screen says "unofficial" (demo step 2) |
| G01-08 | **Independent engine checks:**<br>- differential oracle P9, production engine against the QA oracle (NFR-002b);<br>- mutation score on `sports/pickleball/rules` (NFR-072; baseline this sprint, gated from Sprint 2) | **Oracle: 100,000 sequences, 0 disagreements. Mutation: baseline recorded as a number; ≥ 85% is reported but not gated** | `python -m tests.oracle.differential --sequences 100000`; `scripts/ci/mutation_score.py` | Oracle: 100,000 sequences, 0 disagreements. Mutation baseline 0.8654 (373 of 431 killed, 58 survived), cold cache | yes | Head `e76fb96` (code tree; `HEAD` moved to `7a9e41e` mid-run, a docs-only blockers.md row), verification round 3 (independent), run `racket-gv3` (fresh volumes, ports 23000/28000/28025/21025, `RA_DEV_STATE=.local/gv3`): `python -m tests.oracle.differential --sequences 100000` → rc=0 in 57 s, `sequences 100000`, `disagreements 0`, `passed true` (seed 20261005); `tests/oracle/engine.py` imports nothing from `racket`. `backend/mutants` existed at the start (warm run: rc=0 in 6 s, same 0.8654, kept as `mutation-warm.json`), so it was moved aside to the scratchpad and the run repeated cold: `mutation_score.py --target src/racket/sports/pickleball/rules …` (mutmut 3.8.0) → rc=0 in 61 s, `status measured`, `score 0.8654`, killed 373, survived 58, total 431. Reported, not gated, this sprint |
| G01-09 | **Coverage (NFR-071):**<br>- backend changed lines against `main` (the Sprint 0 close, `2b9c6ca`);<br>- rules engine and aggregates (`sports/pickleball/rules`, `matches/match_state.py`, `matches/participants.py`);<br>- web unit | **Backend changed lines ≥ 85%. Rules and aggregates ≥ 95% line and ≥ 90% branch. Web ≥ 80% line** | `pytest --cov`, then `diff-cover`, `coverage report` and `vitest --coverage` | Backend changed lines 95% (1,579 lines, 64 missing). Rules and aggregates 99.4% line (470/473), 98.7% branch. Web 90.22% lines | yes | Head `e76fb96` (code tree; `HEAD` moved to `7a9e41e` mid-run, a docs-only blockers.md row), verification round 3 (independent), run `racket-gv3` (fresh volumes, ports 23000/28000/28025/21025, `RA_DEV_STATE=.local/gv3`): coverage pytest (§4 G01-09, with the 3 `--deselect` lines, fresh `.coverage`) → rc=0, `1067 passed, 1 skipped, 4 deselected in 112.87s`. `diff-cover --compare-branch=main --fail-under=85` → rc=0, "Total: 1579 lines, Missing: 64 lines, Coverage: 95%". `coverage report --include=<rules+aggregates>` → `TOTAL 473 3 156 2 99%`; `coverage json` same include → `covered_lines 470`, `percent_branches_covered 98.72`. `vitest run --coverage` → rc=0, `269 passed`, `Lines 90.22% (2862/3172)`. The 3 deselected tests are red on PO input and counted in G01-11 |
| G01-10 | **Accessibility on Sprint 1 screens:**<br>- axe serious and critical violations (WCAG 2.2 AA tags) on every page an E2E test checks;<br>- tap targets below 24×24 CSS px;<br>- keyboard-only setup (NFR-027, NFR-028, NFR-034) | **0 serious/critical axe violations, with ≥ 1 axe check per Sprint 1 screen family (A, F/G, Q, U, M); 0 targets below 24×24; E2E-01-03 passes** | From the G01-03 Playwright JSON report | 19 axe checks, 0 serious/critical, families A, F/G, Q, U and M covered; 0 targets below 24×24; E2E-01-03 passed | yes | Head `e76fb96` (code tree; `HEAD` moved to `7a9e41e` mid-run, a docs-only blockers.md row), verification round 3 (independent), run `racket-gv3` (fresh volumes, ports 23000/28000/28025/21025, `RA_DEV_STATE=.local/gv3`): from `reports/goal-gv3/e2e.json` (§4 jq): 19 axe attachments (A-01, A-03, A-04, A-05, F-01, G-01, Q-01-error, Q-03-error, Q-07, U-03, U-04-banner, U-04-different-file, after-sign-in, match-detail, matches-empty, new-match, not-found, sign-in, uploading), every body decodes to `[]`. "axe serious/critical" errors: 0. "targets below 24x24" errors: 0. Passed: E2E-01-03, the 4 reflow tests (320/360/768/1280 px) and all 5 `error-states-a11y.spec.ts` cases. Chromium only (WebKit: CI) |
| G01-11 | **Open defects:** blocking or major findings whose latest disposition is "Open" (ADR 0030), plus open GitHub issues labelled `bug` with `blocker` or `major` | **0** | `review-rounds.md` count and GitHub issue search (§4) | 11 open blocker/major findings (method rc=1, now measurable); GitHub open bug issues 0 | no | Head `e76fb96` (code tree; `HEAD` moved to `7a9e41e` mid-run, a docs-only blockers.md row), verification round 3 (independent), run `racket-gv3` (fresh volumes, ports 23000/28000/28025/21025, `RA_DEV_STATE=.local/gv3`): `open_defects.py --json … docs/sprints/01/review-rounds.md` → **rc=1, `open 11`** (EM-G1-01 fixed: the rc=2 of round 2 is gone). Open: DEMO-07 (blocker); QA-R2V-03 (blocker); PE-R3-05 family QA-R1-06/PE-R2-02/QA-R2-02/QA-R3-05/QA-R2V-01 (blocker); WebKit family PD-R1-02/PD-R1-04/PE-R1-04/QA-R1-04/S-09/QA-R2V-06/PD-R2R-01 (blocker); S-07/QA-R2V-07 (blocker); QA-R2V-11 (major, partly fixed); SEC-R3-S1-01/SEC-R4-S1-01 (major); S-08/QA-R2V-08 (major); SEC-R4-S1-04/BLK-ASVS-6.3.3 (major); PD-R2R-03 (major); PD-R1-06/PD-R2R-02/QA-R2V-12 (major). `mcp__github__list_issues state OPEN` → `totalCount 0`. Smoke §4 S-07, S-08, S-09 are already in the count; no new blockers.md product-defect row. P1 is now partly actioned (blockers.md row at `7a9e41e`: `sprint-01` pushed, `ci.yml` dispatched, run 37372059078 `queued`; `nightly-quality.yml` dispatch → 404 until it exists on `main`), but no finding's disposition has changed yet |
| G01-12 | **Fast tests (NFR-073):**<br>- the domain unit suite;<br>- the whole backend unit suite | **Domain < 10 s; backend unit ≤ 60 s; both 0 failed** | `scripts/ci/run_with_budget.py` | Domain 7.4 s (721 passed, 1 skipped); backend unit 8.3 s (763 passed, 1 skipped); 0 failed | yes | Head `e76fb96` (code tree; `HEAD` moved to `7a9e41e` mid-run, a docs-only blockers.md row), verification round 3 (independent), run `racket-gv3` (fresh volumes, ports 23000/28000/28025/21025, `RA_DEV_STATE=.local/gv3`): `run_with_budget.py 10 -- … pytest -q -m unit tests/unit` → rc=0, `721 passed, 1 skipped in 6.33s`, budget 7.4 s. `run_with_budget.py 60 -- … pytest -q -m unit` → rc=0, `763 passed, 1 skipped, 320 deselected in 7.17s`, budget 8.3 s |

**Overall:** the sprint goal is met only when all 12 rows are "yes". A row whose method could not run is "no", never "n/a" (fail closed, ADR 0014).

**Current totals (goal verification round 3, 2026-10-05, code head `e76fb96`, run `racket-gv3`; detail in §8): 10 of 12 met. G01-05 is "no": the 1 GB ingest measured 541.8 Mbit/s, but both runs ended under the 10 GB disk floor (`disk_free_gb_end 9`), which docs/ops/disk-and-prune.md makes invalid evidence, and the remaining prune (stale images of finished rounds) was denied in this session. G01-11 is "no": the method is measurable again and gives 11 open blocker/major findings. The Sprint 1 goal is NOT met and Sprint 1 is not done.** The table above holds the round-3 values; round 1 is in §6 and round 2 in §7 (round 2 totals were 11 of 12).

**Verifier result (senior-qa-engineer, 2026-10-05, review round 2; PE-R2-S1-01, QA-R2V-02; superseded by §6):** **11 of 12 rows are "yes". G01-11 (open defects) is "no", so the Sprint 1 goal is NOT met and Sprint 1 is not done.**

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

## 6. Verification round 1 (2026-10-05, independent goal verifiers)

- **Verifiers:** senior-qa-engineer with sre-devops-engineer, acting as independent goal verifiers. Neither built the stories; the earlier fill (`racket-qav3` at `7c6a0ae`) was not reused, and every method in §4 was run again.
- **Head:** `fb9e7d66b724b516ff170256982ad95a5824d71b` (`reports/goal-gv1/head.txt`). `git status --porcelain` empty before and after the run.
- **Stack, from a clean state:** no containers running at the start (`docker ps -a` empty). Compose project `racket-gv1`: `down -v --remove-orphans`, then `up -d --build --wait` with the proxy-CA build secret → rc=0 in 1m55s, all 9 services healthy, new volumes `racket-gv1_pgdata`, `_s3data`, `_caddy-data`; Mailpit `total 0`. Plain http on 43000 → 400; https with the Caddy root → 200 (CSP with nonce, no insecure-cookie flag). Separate fresh `dev-postgres` (new `PGDATA`) and `dev-objectstore` (new `racket-media` bucket) under `RA_DEV_STATE=.local/gv1` for G01-02 and G01-09.
- **Disk (retro 1 A5, disk-and-prune.md):** 13 G free at the start; 9 G after the image build, so `live_goal.py` refused (rc=2, no requests sent). Prune steps 2-3 (`docker builder prune -af` reclaimed 5.58 GB; no other agent's stack was running) → 15 G free. The large-file run ended at 11 G free (`disk_free_gb_end 11`), above the floor.
- **Reports and log:** `reports/goal-gv1/` (git-ignored), with every step and rc in `run.log`.

| ID | Target | Actual (round 1) | Met | Owner if not met |
|---|---|---|---|---|
| G01-01 | 5 of 5 live runs pass | 5/5, rc=0 | yes | |
| G01-02 | IT 100%, 13/13 ids; regression 100% | 69/69, `missing []`; 41/41 | yes | |
| G01-03 | 100% non-skipped, ≤ 6 named skips, 0 flaky ×3 | 52/52, 6 skips, ×3: 135/135, 0 flaky (Chromium) | yes | |
| G01-04 | p95 ≤ 300 ms, p99 ≤ 800 ms, ≥ 99.5%, ≥ 47.5 RPS | 14.95 ms, 57.7 ms, 100%, 50.01 RPS | yes | |
| G01-05 | ≥ 50 Mbit/s, offset = length | 531.8 Mbit/s, 1,052,796,534 = size | yes | |
| G01-06 | (a) ≤ 10 s; (b) ≤ 30 s | 1.061 s; 0.912 s | yes | |
| G01-07 | 100% scoring, ≥ 19 provisional rows, ≤ 90 s | 204/205 (P3 skip), 26/26, 33.7 s | yes | |
| G01-08 | 100,000 sequences 0 disagreements; mutation number | 0 disagreements; 0.8654 (cold) | yes | |
| G01-09 | ≥ 85% / ≥ 95% line, ≥ 90% branch / ≥ 80% | 95% / 99.4%, 98.7% / 90.22% | yes | |
| G01-10 | 0 serious/critical, all families, 0 small targets, E2E-01-03 | 19 checks, 0, A F/G Q U M, 0, passed | yes | |
| G01-11 | 0 open blocker/major | 10 | **no** | engineering-manager (PO escalations P1-P4); see below |
| G01-12 | domain < 10 s, unit ≤ 60 s, 0 failed | 7.7 s, 9.0 s, 0 failed | yes | |

**Totals: 11 of 12 met. The Sprint 1 goal is NOT met (G01-11), so Sprint 1 is not done** (PO standing rule; §2 "Overall").

**G01-11, owners of the 10 open findings** (from `open_defects.py`, latest disposition):
- PE-R3-05 family (CI and nightly dispatch) and S-08/QA-R2V-08 (nightly result): human PO pushes `sprint-01` and dispatches `ci.yml` and `nightly-quality.yml`; sre-devops-engineer records the run IDs.
- WebKit family PD-R1-02/PD-R1-04/S-09/QA-R2V-06/PD-R2R-01: senior-frontend-engineer, once a CI WebKit run exists. **WebKit cannot run in this sandbox** (`/opt/pw-browsers` has Chromium only); it runs on CI.
- S-07/QA-R2V-07 (real phone clips): senior-ml-cv-engineer, after the human PO supplies the recordings.
- SEC-R3-S1-01/SEC-R4-S1-01 (account identity key, ST-013b): senior-backend-engineer with security-privacy-engineer.
- SEC-R4-S1-04/BLK-ASVS-6.3.3 and QA-R2V-11 (ADR 0031/0032): human PO decision; security-privacy-engineer.
- PD-R2R-03 (capture-guide consent line, partly fixed) and PD-R1-06/PD-R2R-02/QA-R2V-12 (DoR P7 flows design review): principal-designer.
- QA-R2V-03: the G01-11 escalation itself; closes when the rows above close (engineering-manager).

**Sprint demo (sprint-01 §12), run end to end in real time.** A Playwright script written by the verifiers (scratch, not a project test) drove a phone viewport (Chromium, Pixel 7 profile) against `https://localhost:43000`. Second attempt → rc=0, `1 passed (2.8m)`; step timings are in `reports/goal-gv1/demo-steps.json` and screenshots in `reports/goal-gv1/demo-out/`.
1. Sign-in link requested, read from Mailpit, opened → `/welcome` in 1.49 s, no token in the address bar, "Record your first match" shown.
2. First-run screen ("What Racket Analytics does", "unofficial") and capture guide: 6 checklist items, each readable text, guide video not autoplaying.
3. Continue with no format → error summary "There is a problem · Select doubles or singles", page title `Error: …`. Rally scoring `aria-disabled` with "It becomes available once the rules are verified." Doubles with Ivy, Dana, Carlos, Sam → "Check your answers".
4. **Upload of the 1.05 GB 1080p60 fixture** (not ~3 GB: disk floor, see above). Offline at 40% for a **real 120 s**: "Paused: waiting for connection" shown and the percentage held at 40%. Back online → "Uploading" again in 0.42 s. Tab closed at 60%, new tab → "Your upload of 'Doubles · 5 Oct 2026' is 60% done." → "Resume upload", same file chosen → resumed from the server offset (API log: HEAD, then PATCHes only) → "Video received" with "Duration 2:00 · 60 fps · 1920×1080", 13.1 s later. No existing E2E test resumes a closed tab with the same file through to "Video received"; this run covers that.
5. PDF renamed `match.mp4` → error summary "This file is not a video we can read". The 4-hour clip → "Videos must be 2 hours 30 minutes or shorter. Nothing from this file was saved."
6. `pytest -m scoring` (G01-07): mechanics green; 26 SOD/F rows green and reported only as `@needs-verification`.
7. Oracle 100,000 sequences, 0 disagreements, and the mutation baseline 0.8654 (G01-08), run locally. **No nightly GitHub result exists** (PE-R3-05, S-08), so the "nightly" part of the step could not be shown.
8. Sign out → "You have signed out". Offline reopen renders the browser's blank offline page: nothing of Ivy's is visible. Storage and Cache API could not be read on that page; the online checks (0 storage items, no cached media or API) pass in `sign-out.spec.ts` (G01-03).
9. SPIKE-06 and SPIKE-01 results and the OQ-12/OQ-18 questions are for the human PO at the review; not runnable.
- **First demo attempt (run 1):** stopped by the verifiers after the resume step. The cause was the verifiers' script: an extra click with no timeout, after the upload had already auto-resumed. The server had the match `video_received` at 19:23:14 (Postgres `matches.status`, worker `probe.done`). It is not a product defect, and run 2 is the evidence.

**Observations (not goal metrics; routed for the owners to triage, none blocks a row):**
- On the paused upload screen, "Status" still reads "Awaiting upload" and a "Pause" button stays offered while offline (`demo-out/…/4-paused.png`). Owner: principal-designer with senior-frontend-engineer.
- `live_goal.py` drops the connection between chunks (client `close()` after the chunk at 40%), not mid-chunk. A mid-chunk cut is covered only by E2E-01-02 in the browser. Owner: senior-qa-engineer (harness).

## 7. Verification round 2 (2026-10-05, independent goal verifiers)

- **Verifiers:** senior-qa-engineer with sre-devops-engineer, acting as independent goal verifiers (round 2). Neither built the stories. No round-1 stack, database, image or report was reused: every §4 method was run again from a clean state and the table in §2 now holds the round-2 values.
- **Head:** `3194096fad48e319525b585c1bb84eed881c1943` (`reports/goal-gv2/head.txt`). Since round 1 (`fb9e7d6`) only docs changed (`git diff fb9e7d6..HEAD --stat`: 7 files under `docs/`, among them `review-rounds.md`, which adds the goal-round-1 rows). `git status --porcelain` empty before and after the run.
- **Stack, from a clean state:** no containers running at the start. The leftover `racket-gv1-*` images were removed and the build cache pruned before the build. Compose project `racket-gv2` (`-f infra/compose.yaml -f .local/gv2/ca-override.yaml`, proxy-CA build secret): `down -v --remove-orphans`, then `up -d --build --wait` → rc=0 in 2m23s, all services healthy (migrate and objectstore-init exited 0), new volumes `racket-gv2_pgdata`, `_s3data`, `_caddy-data`; Mailpit `total 0`. Plain http on 53000 → 400; https with the Caddy root → 200, CSP with nonce, no insecure-cookie flag. A separate fresh `dev-postgres` (new `PGDATA` `/tmp/racket-pg.5h61pV`, created 20:18) and `dev-objectstore` (new `racket-media` bucket) under `RA_DEV_STATE=.local/gv2` for G01-02 and G01-09. Torn down at the end (`down -v` rc=0, dev services stopped).
- **Disk (retro 1 A5):** 16 G free before the build, 8.4 G after it (below the floor). `docker builder prune -af` reclaimed 5.12 GB → 13 G. The large-file run ended at `disk_free_gb_end 10`; the demo upload took it to 9.7 G (the demo is not a floor-gated evidence run); 13 G after teardown. Removing other rounds' stale images (`racket-pe-r3-*`, `racket-qav3-*`, `racket-qar2-*`) was not attempted (blockers.md, permission policy).
- **Reports and log:** `reports/goal-gv2/` (git-ignored), every step and rc in `run.log`.

| ID | Target | Actual (round 2) | Met | Owner if not met |
|---|---|---|---|---|
| G01-01 | 5 of 5 live runs pass | 5/5, rc=0, every step `ok true` | yes | |
| G01-02 | IT 100%, 13/13 ids; regression 100% | 69/69, `missing []`; 41/41 | yes | |
| G01-03 | 100% non-skipped, ≤ 6 named skips, 0 flaky ×3 | 52/52, 6 named skips; ×3: 135/135, 0 flaky (Chromium) | yes | |
| G01-04 | p95 ≤ 300 ms, p99 ≤ 800 ms, ≥ 99.5%, ≥ 47.5 RPS | 16.47 ms, 106.6 ms, 100%, 50.01 RPS | yes | |
| G01-05 | ≥ 50 Mbit/s, offset = length | 486.5 Mbit/s, 1,052,825,715 = size | yes | |
| G01-06 | (a) ≤ 10 s; (b) ≤ 30 s | 1.055 s; 0.890 s | yes | |
| G01-07 | 100% scoring, ≥ 19 provisional rows, ≤ 90 s | 204/205 (P3 skip, FR-043), 26/26, 33.4 s | yes | |
| G01-08 | 100,000 sequences 0 disagreements; mutation number | 0 disagreements; 0.8654 (cold) | yes | |
| G01-09 | ≥ 85% / ≥ 95% line, ≥ 90% branch / ≥ 80% | 95% / 99.4%, 98.7% / 90.22% | yes | |
| G01-10 | 0 serious/critical, all families, 0 small targets, E2E-01-03 | 19 checks, 0, A F/G Q U M, 0, passed | yes | |
| G01-11 | 0 open blocker/major | method rc=2 (cannot be measured, fails closed); supporting count 12; GitHub 0 | **no** | engineering-manager (PO escalations); sre-devops-engineer for EM-G1-01 |
| G01-12 | domain < 10 s, unit ≤ 60 s, 0 failed | 7.0 s, 8.1 s, 0 failed | yes | |

**Totals: 11 of 12 met. The Sprint 1 goal is NOT met (G01-11), so Sprint 1 is not done** (PO standing rule; §2 "Overall").

**G01-11 in round 2, and why it is worse than round 1:**
- `open_defects.py docs/sprints/01/review-rounds.md` now exits **2** at `line 286: severity row with no finding id: 'DEMO (step 7)'`. The goal-round-1 sre-devops-engineer rows (`DEMO (step 7)` blocker, `DEMO (step 4, ~3 GB file)` minor, `DEMO (step 9)` —) have no parsable id, so the method refuses the file and the row fails closed (ADR 0014). This is EM-G1-01 (major, open, routed to sre-devops-engineer): give the three rows parsable ids, without changing the script or its tests.
- Supporting count only (not the metric): the same script on a scratch copy with the ids renamed `DEMO-7/-4/-9` → rc=1, **12 open** (round 1: 10). The 2 new ones are DEMO-7 (blocker: the nightly result for demo step 7 needs the PO's push and dispatch, same root as the PE-R3-05 family) and EM-G1-01 itself. The other 10 are the round-1 families with unchanged dispositions; QA-R2V-11 is now "Partly fixed" (ADR 0032 accepted, still open).
- Owners are as in §6: human PO items P1 (push and dispatch `ci.yml` and `nightly-quality.yml`; closes the PE-R3-05 family, S-08/QA-R2V-08 and DEMO-7, and gives the WebKit run), P2 (ADR 0031: SEC-R4-S1-04/BLK-ASVS-6.3.3), P3 (phone clips or ST-025 carry-over: S-07/QA-R2V-07); senior-frontend-engineer for the WebKit family once a CI WebKit run exists; senior-backend-engineer with security-privacy-engineer for SEC-R3-S1-01/SEC-R4-S1-01 (ST-013b); principal-designer for PD-R2R-03 and the P7 review (PD-R1-06/PD-R2R-02/QA-R2V-12, due 2026-10-06); engineering-manager for QA-R2V-03.
- **What cannot run in this sandbox:** WebKit (`/opt/pw-browsers` has Chromium only; runs on CI, which needs P1) and the GitHub nightly (`nightly-quality.yml`, needs P1). Real phone recordings do not exist (`fixtures/clips/` has no `phones-v1`).
- GitHub: `mcp__github__search_issues` `is:open label:bug` → `total_count 0`; `mcp__github__list_issues` state OPEN → `totalCount 0`.

**Sprint demo (sprint-01 §12), run end to end in real time** on the `racket-gv2` stack: a verifier-written Playwright script (scratch, not a project test; the round-1 script, with the offline check also looking for "Ivy") drove a phone viewport (Chromium, Pixel 7 profile) against `https://localhost:53000` → rc=0, `1 passed (2.9m)`, first attempt. Timings: `reports/goal-gv2/demo-steps.json`; screenshots: `reports/goal-gv2/demo-out/`.
1. Sign-in link requested, read from Mailpit, opened → `/welcome` in 1.12 s, no token in the URL, "Record your first match" shown.
2. First-run screen ("What Racket Analytics does", "unofficial") and the capture guide: 6 checklist items, each readable text, guide video not autoplaying.
3. Continue with no format → "There is a problem · Select doubles or singles", page title `Error: …`. Rally scoring `aria-disabled` with "It becomes available once the rules are verified." Doubles with Ivy, Dana, Carlos, Sam → "Check your answers" (Side A: Ivy, Dana; Side B: Carlos, Sam; You: Ivy).
4. Upload of the **1.05 GB** 1080p60 fixture (not ~3 GB: disk, see blockers.md DEMO step 4). Offline at 40% (12.3 s into the upload) for a **real 120 s**: "Paused: waiting for connection" shown and the percentage held at 40%. Back online → upload moving again in 0.19 s. Tab closed at 60%, new tab → "Your upload of 'Doubles · 5 Oct 2026' is 60% done." → "Resume upload", same file → "Video received" with "Duration 2:00 · 60 fps · 1920×1080 … Footage quality Good", 14.3 s later (157 s total incl. the 120 s offline). API log for that account: 1 POST create, 51 PATCH, HEAD after reconnect, 25 PATCH, HEAD after reopen, 51 PATCH (127 PATCHes of 8 MiB, no second create), so both resumes started from the server offset.
5. PDF renamed `match.mp4` → "This file is not a video we can read". 4-hour clip → "Videos must be 2 hours 30 minutes or shorter. Nothing from this file was saved."
6. `pytest -m "scoring and not nightly"` (G01-07): 204 passed, P3 skipped (FR-043); the 26 SOD/F rows passed and reported only under `@needs-verification`.
7. Oracle 100,000 sequences, 0 disagreements, and mutation baseline 0.8654, both run locally (G01-08). **No nightly GitHub result exists** (PE-R3-05, S-08, DEMO-7), so the "nightly" part of the step could not be shown.
8. Sign out → "You have signed out". Offline reopen renders the browser's blank offline page: none of Ivy, Dana, Carlos, Sam, "Video received", "Doubles ·" visible. Storage and Cache API cannot be read on that error page (-1); the online checks pass in `sign-out.spec.ts` (G01-03).
9. SPIKE-06/SPIKE-01 results and OQ-12/OQ-18 are for the human PO at the review; not runnable.

**Observations (not goal metrics; for owners to triage):**
- Still present from round 1: while offline, the upload screen shows "Status: Awaiting upload" and still offers "Pause" under "Paused: waiting for connection" (`demo-out/…/4-paused.png`). Owner: principal-designer with senior-frontend-engineer.
- G01-04 p99 rose from 57.7 ms (round 1) to 106.6 ms (max 397 ms), still far under 800 ms; single runs on a shared 4-core host, so not a trend.
- The stale images of finished rounds keep the host near the 10 GB floor after each build; every verifier has to prune the build cache first. Owner: sre-devops-engineer (disk-and-prune.md).

## 8. Verification round 3 (2026-10-05, independent goal verifiers)

- **Verifiers:** senior-qa-engineer with sre-devops-engineer, acting as independent goal verifiers (round 3). Neither built the stories. No stack, database, report or certificate from rounds 1-2 or the SRE demo rerun was reused. Every §4 method was run again, and the §2 table now holds the round-3 values.
- **Head:** `e76fb96172a0475d9c1ec1a08601fe3cf1086158` (`reports/goal-gv3/head.txt`), with `git status --porcelain` empty at the start. During the run the orchestrator committed `7a9e41e` (one blockers.md row: P1 actioned). `git diff --stat e76fb96..7a9e41e` shows 1 docs file, so the tree under test is unchanged. Since round 2 (`3194096`) only docs changed (4 files under `docs/sprints/01/`).
- **Stack, from a clean state:** no containers were running at the start. Compose project `racket-gv3` (`-f infra/compose.yaml -f .local/gv3/ca-override.yaml`, proxy-CA build secret, `DOCKERHUB_REGISTRY=mirror.gcr.io`). `down -v --remove-orphans` then `up -d --build --wait` → rc=0 in 2m17s. All 9 services were healthy, `migrate` and `objectstore-init` exited 0, and the volumes were new (`racket-gv3_pgdata`, `_s3data`, `_caddy-data`). Mailpit `total 0`. Plain http on 23000 → 400. https with the Caddy root → 200, CSP with nonce, and no insecure-cookie flag in the env. A separate fresh `dev-postgres` and `dev-objectstore` (new `racket-media` bucket) under `RA_DEV_STATE=.local/gv3` served G01-02 and G01-09. Before the G01-05 rerun and again before the demo, the stack's own volumes were recreated (`down -v`, `up --no-build --wait`, rc=0, new Caddy root copied). Teardown at the end: `down -v` rc=0 and the dev services stopped.
- **Disk (retro 1 A5, disk-and-prune.md):** 13 G free at the start. The build took it to **6.1 G**, under the floor. Step 2 (`docker builder prune -af`) reclaimed 5.119 GB, back to 11 G. Removing the stale images of finished rounds (`racket-gv2-*`, `racket-pe-r3-*`, `racket-qav3-*`, `racket-qar2-*`; `docker system df` → 5.5 GB reclaimable) was **denied by the session permission policy**, and the denial was respected. The large fixtures went to tmpfs (`/dev/shm`). Even so, every 1 GB ingest ended at 9.6 G (`disk_free_gb_end 9`); see G01-05. The `racket-gv3-*` images are left in place (4.6 GB) for the same reason. 11 G free after teardown.
- **Reports and log:** `reports/goal-gv3/` (git-ignored), with every step and rc in `run.log`.

| ID | Target | Actual (round 3) | Met | Owner if not met |
|---|---|---|---|---|
| G01-01 | 5 of 5 live runs pass | 5/5, rc=0, every step `ok true` | yes | |
| G01-02 | IT 100%, 13/13 ids; regression 100% | 69/69, `missing []`; 41/41 | yes | |
| G01-03 | 100% non-skipped, ≤ 6 named skips, 0 flaky ×3 | 52/52, 6 named skips; ×3: 135/135, 0 flaky (Chromium only) | yes | |
| G01-04 | p95 ≤ 300 ms, p99 ≤ 800 ms, ≥ 99.5%, ≥ 47.5 RPS | 12.79 ms, 49.52 ms, 100%, 50.01 RPS | yes | |
| G01-05 | ≥ 50 Mbit/s, offset = length | 541.8 Mbit/s, offset = size, rc=0, but `disk_free_gb_end 9` (< 10 GB floor): invalid evidence | **no** | sre-devops-engineer (host disk: the stale-image removal needs human approval, then rerun) |
| G01-06 | (a) ≤ 10 s; (b) ≤ 30 s | 1.058 s; 0.879 s | yes | |
| G01-07 | 100% scoring, ≥ 19 provisional rows, ≤ 90 s | 204/205 (P3 skip, FR-043), 26/26, 32.5 s | yes | |
| G01-08 | 100,000 sequences 0 disagreements; mutation number | 0 disagreements; 0.8654 (cold) | yes | |
| G01-09 | ≥ 85% / ≥ 95% line, ≥ 90% branch / ≥ 80% | 95% / 99.4%, 98.7% / 90.22% | yes | |
| G01-10 | 0 serious/critical, all families, 0 small targets, E2E-01-03 | 19 checks, 0, A F/G Q U M, 0, passed | yes | |
| G01-11 | 0 open blocker/major | 11 open (rc=1); GitHub 0 | **no** | engineering-manager (PO items P1-P4; owners per finding below) |
| G01-12 | domain < 10 s, unit ≤ 60 s, 0 failed | 7.4 s, 8.3 s, 0 failed | yes | |

**Totals: 10 of 12 met. The Sprint 1 goal is NOT met (G01-05, G01-11), so Sprint 1 is not done** (PO standing rule; §2 "Overall").

**G01-05, why "no" although the number meets the target.**
- Two runs on the live stack both passed every step. The first gave 562.1 Mbit/s and the second 541.8 Mbit/s, each with final offset 1,052,798,536 = file size.
- Both ended at `disk_free_gb_end 9`. disk-and-prune.md says such a run "is not valid evidence; prune and run it again". The prune steps open to this session were used (build cache; own volumes recreated). The step that would free enough space (removing other rounds' images) was denied.
- So the method cannot produce valid evidence in this sandbox as it stands. Under fail closed (ADR 0014; task rule: never "met" from reasoning) the row is "no". This is a host-capacity problem, not a product defect.
- To fix: the human approves or runs the removal of the stale `racket-*` images (or the host gets more disk), then any verifier reruns §4 G01-05 with ≥ 12 GB free (`RA_MIN_FREE_GB=12 bash scripts/disk-precheck.sh`).
- Owner: sre-devops-engineer, with the human for the approval. A second option is for sre-devops-engineer to change the procedure so that each round removes its own images at teardown (`down -v --rmi local`). That stops the pile-up recurring.

**G01-11 in round 3.**
- EM-G1-01 is fixed, so the method is measurable again: `open_defects.py` → rc=1, **11 open** (round 2: not measurable, 12 on a scratch copy). GitHub: `list_issues state OPEN` → `totalCount 0`.
- Owners are unchanged from §7:
  - Human PO, P1 (now partly actioned at `7a9e41e`): PE-R3-05 family, S-08/QA-R2V-08, DEMO-07 and the WebKit run. CI run 37372059078 on `sprint-01`@`e76fb96` was still `queued` at the end of this round. `nightly-quality.yml` cannot be dispatched until it exists on `main`. sre-devops-engineer records the run.
  - P2 (ADR 0031): SEC-R4-S1-04/BLK-ASVS-6.3.3 and half of QA-R2V-11.
  - P3: S-07/QA-R2V-07.
  - P4: carry-over approval.
  - senior-frontend-engineer: the WebKit family PD-R1-02/…/PD-R2R-01, once a CI WebKit run exists.
  - senior-backend-engineer with security-privacy-engineer: SEC-R3-S1-01/SEC-R4-S1-01 (ST-013b).
  - principal-designer: PD-R2R-03 and the P7 review PD-R1-06/PD-R2R-02/QA-R2V-12 (due 2026-10-06).
  - engineering-manager: QA-R2V-03.

**What cannot run in this sandbox (fail closed, counted above):**
- WebKit E2E: `/opt/pw-browsers` has Chromium only. It runs only on CI (run 37372059078, queued).
- The GitHub nightly (`nightly-quality.yml`): it needs the workflow on `main`.
- A valid G01-05 large-file run: it needs ≥ 12 GB free, which in turn needs the image removal that was denied.
- Real phone recordings: there is no `fixtures/clips/phones-v1`.

**Sprint demo (sprint-01 §12), run end to end in real time** on the `racket-gv3` stack (fresh volumes recreated just before). The SRE round-2 demo script was copied to the scratchpad (`gv3-demo/`); only its output paths changed. It drove a Pixel 7 Chromium viewport against `https://localhost:23000` → rc=0, `1 passed (2.8m)`, first attempt, 21:00-21:03 UTC. Timings are in `reports/goal-gv3/demo-steps.json`, screenshots in `reports/goal-gv3/demo-out/` and the API log in `api-demo.log`.
1. A sign-in link was requested, read from Mailpit and opened → `/welcome` in 1.55 s. No token in the URL, and "Record your first match" is shown.
2. First-run screen ("What Racket Analytics does", "unofficial") and the capture guide: 6 checklist items, each readable text. The guide video does not autoplay.
3. Continue with no format → "There is a problem · Select doubles or singles", page title `Error: …`. Rally scoring is `aria-disabled` with "It becomes available once the rules are verified." Doubles with Ivy, Dana, Carlos and Sam → "Check your answers" (Side A: Ivy, Dana; Side B: Carlos, Sam; You: Ivy; video `large-1080p60.mp4 (1.1 GB)`).
4. Upload of the **1.05 GB** 1080p60 fixture, not ~3 GB: the disk could not take a 3 GB stored object above the SeaweedFS floor after the build (see Disk). The SRE ran it with 3 GB in goal round 2, DEMO-04.
   - Offline at 40% (12.8 s into the upload) for a **real 120 s**: "Paused: waiting for connection" was shown and the percentage held at 40%. Back online, the upload moved again in 0.41 s.
   - Tab closed at 60%. New tab → "Your upload of 'Doubles · 5 Oct 2026' is 60% done." → "Resume upload", same file → resume screen "60% · 0.6 GB of 1.1 GB" → "Video received" 13.1 s later (155.9 s in total, including the 120 s offline). Facts shown: "Duration 2:00 · 60 fps · 1920×1080 … h264 … Footage quality Good".
   - API log: `POST /matches/{id}/uploads` 3 (the large file, the PDF and the 4-hour file, with no second create for the large file), `HEAD` 2 (after reconnect and after reopen), `PATCH` 128 × 204 + 1 × 415 (the PDF). No 5xx in this run, so SRE-G2-02 (ClientDisconnect logged as 500) did not reproduce here. Postgres `matches`: `video_received 1`, `awaiting_upload 2`.
5. A PDF renamed `match.mp4` → "This file is not a video we can read". The 4-hour clip → "Videos must be 2 hours 30 minutes or shorter. Nothing from this file was saved."
6. `pytest -m "scoring and not nightly"` (G01-07): 204 passed, P3 skipped (FR-043). The 26 SOD/F rows passed and are reported only under `@needs-verification`.
7. Oracle: 100,000 sequences, 0 disagreements. Mutation baseline (cold): 0.8654. Both were run locally (G01-08). **No nightly GitHub result exists** (DEMO-07), so the "nightly" part of the step could not be shown.
8. Sign out → "You have signed out". The offline reopen renders the browser's blank offline page, and none of Ivy, Dana, Carlos, Sam, "Video received" or "Doubles ·" is visible. Storage and the Cache API cannot be read on that error page (-1). The online checks pass in `sign-out.spec.ts` (G01-03).
9. The SPIKE-06/SPIKE-01 results and OQ-12/OQ-18 are for the human PO at the review, so this step could not be run.

**Observations (not goal metrics; for owners to triage):**
- SRE-G2-01 is still present: the API's OTLP metrics export gets 404 from Jaeger every minute (3 `ERROR` lines in `api-demo.log`, 21:00:59-21:02:59). Owner: sre-devops-engineer.
- Every verification round leaves about 4.6 GB of `racket-<round>-*` images, and this session may not remove other rounds' images. Each fresh `up --build` now lands under the floor (6.1 G) before pruning. This is the cause of G01-05's "no". Owner: sre-devops-engineer (disk-and-prune.md).
