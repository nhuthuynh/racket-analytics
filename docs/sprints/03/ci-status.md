# Sprint 3 CI status (sre-devops-engineer)

One row per CI run that matters to the sprint: what ran, at which SHA, the result, and who owns each red. Append only.

| Date | Run | Branch / SHA | Result | Reds and owners |
|---|---|---|---|---|
| 2026-10-06 | 37521787513 (dispatch) | `sprint-03` / `78644f3` | failure | Secret scan only: `generic-api-key` on the SEC-RV3-02 synthetic test key (`backend/tests/unit/platform/test_settings_sprint03.py:41`, `9ca52fe`). Fixed on `sprint-03` by `e7e86ef` (exact fingerprint in `.gitleaksignore`, guarded by `infra/tests/test_gitleaks_ignore.py`) |
| 2026-10-07 | 37606256586 (schedule, nightly) | `main` / `259a0a8` | failure (`ci-gate`) | **QA-R1S3-02 (root cause confirmed from the job log).** Every job green except "Secret scan, dependency audit": gitleaks scans every fetched ref (356 commits), so it finds the same `9ca52fe` key on `sprint-03`; the ignore file `e7e86ef` exists only on `sprint-03`. E2E (Chromium + WebKit), Locust baseline, integration, unit, infra, web, mypy, SBOM: success. Remedy: bring `.gitleaksignore` and its guard test to `main` (cherry-pick of `e7e86ef` in a small PR to `main`; PO merge), or wait for the Sprint 3 merge. Until then every nightly on `main` is red on this one finding. Owner: sre-devops-engineer (PR) with the orchestrator/PO (merge) |
| 2026-10-07 | 37521787513 (dispatch), **correction of row 1** (QA-R1S3-07) | `sprint-03` / `78644f3` | failure | Row 1 was wrong: it was not "Secret scan only". `list_workflow_jobs 37521787513`: **Python unit suites** failure (step 9, backend unit suite: `test_bola_inventory`, SRE-S3-01, fixed later on the branch), **Integration** failure (step 9, backend suites; the `red_until` and diff-cover steps skipped), **E2E** failure (step 11, Playwright), **Secret scan** failure (gitleaks, `9ca52fe`), so `ci-gate` failure. Nine other jobs success |
| 2026-10-07 | 37639459765 (dispatch, PE-R1S3-07) | `sprint-03` / `48988f4` (first push since `0903a54`: `git push origin sprint-03` → `0903a54..48988f4`, fast-forward, 34 commits) | failure | Green: secret scan (the `e7e86ef` ignore works on CI), Python unit, mypy, Ruff, actionlint, drill-lint (first CI run of `4d8af6d`), web checks, SBOM, fixtures, Locust. Red: (1) **infra** 2 failed / 569 passed: `test_gitleaks_ignore.py::test_every_entry_names_a_commit_in_this_repository` (shallow checkout, `9ca52fe` absent; **SRE**, fixed `8b451d9`) and `test_goal_scorecard_fast_tests.py::test_the_domain_run_uses_the_ci_domain_paths_in_order` (**SRE-S3-02**, routed to QA by the TCR row of 2026-10-07; QA's change is in the shared tree, not committed). Also found: 14 infra tests deselected by `-m "unit or integration"` (no mark; **SRE**, fixed `8b451d9`). (2) **Integration** step 9: reproduced locally at `8b451d9` in a detached worktree with its own `RA_DEV_STATE` Postgres and object store, the job's selection: `2 failed, 2346 passed, 22 skipped, 154 deselected`, both `tests/regression/test_golden_an.py::…[GS-AN-1-gm1-two-games-AN-07]` and `[…gm2-three-games-AN-07]`: "AN-07 side A low_sample: expected False, got True" (the AN-07 rule change in `fee4fa3`, PE-R1S3-05, against the frozen GS-AN-1 v1 values; **senior-backend-engineer with senior-qa-engineer**). (3) **E2E** "24 failed" (Playwright run summary annotation): the red-first Sprint 3 specs E2E-03-01..06 in Chromium and WebKit (ST-043/047/048/051/052/054 not built; QA-R1S3-01). No Sprint 0-2 spec in the failure annotations |
| 2026-10-07 | 37640321145 (dispatch) attempt 1 / attempt 2 | `sprint-03` / `8b451d9` | attempt 1: every job `abandoned` (no runner after 24 min, `ci-gate` log); attempt 2 (`rerun_workflow_run`): failure | Attempt 2: secret scan, unit, mypy, Ruff, actionlint, drill-lint, web, SBOM, fixtures green. **infra** 2 failed / 586 passed, 0 deselected: the gitleaks check now passes; `test_dev_chrome.py::test_real_install_passes_check_mode` (newly selected) ran against the runner image's Google Chrome 154 at `/opt/google/chrome` (**SRE**, fixed `09f1f67`) and SRE-S3-02 (QA). **Integration** red again at step 9 (log not readable here; the local reproduction in the row above is at this same SHA, `8b451d9`). **E2E** red again: annotation "24 failed", every listed failure in `e2e/sprint-03/` |
| 2026-10-07 | 37643676432 (dispatch) | `sprint-03` / `09f1f67` (includes `6f3bfce`, QA's SRE-S3-02 fix) | failure | **12 of 14 jobs green**, among them **infra** (first green infra job on `sprint-03` CI: SRE fixes `8b451d9`, `09f1f67` and QA's `6f3bfce`), secret scan, Python unit, drill-lint, Locust, flaky report. Red: (1) **Integration** step 9, reproduced locally at `09f1f67` (own `RA_DEV_STATE`, the job's selection): `2 failed, 2346 passed, 22 skipped, 154 deselected`, the two GS-AN-1 AN-07 `low_sample` cases; owner senior-backend-engineer with senior-qa-engineer (blockers.md senior-backend-engineer row of 2026-10-07; TCR row for `gm1`/`gm2` expected AN-07, QA's change). (2) **E2E** "32 failed": red-first Sprint 3 specs only in the failure annotations (E2E-03-01..06, plus E2E-03-08 from `47c34e8`), both browsers; blockers.md sre-devops-engineer row of 2026-10-07 (no E2E `red_until`). `ci-gate` failure |
| 2026-10-08 | 37715576115 (pull_request, PR #4 `sprint-03` → `main`, label `qa-approved-test-change`) | `sprint-03` / `2ba4dd1` (merge of `main` into `sprint-03`; first CI run after the close) | failure | Per job: Python unit success; Ruff success; mypy success; secret scan success; drill-lint **success** (G03-09 c); fixtures success; actionlint success; Locust baseline success; infra success; web checks success; SBOM success; flaky report skipped (by design, not a PR job); **PR policy failure** (step "PR size": 27,015 changed lines, no `size-waiver`; owner engineering-manager, blockers.md); **Integration failure** (step 9 exit 124, the 600 s NFR-073 budget; local repro of the same selection with coverage 649.31 s; owner principal-engineer + senior-qa-engineer, blockers.md); **E2E failure** (4 failed: E2E-03-05 ×2 browsers "E2E_ADMIN_CMD is not set" → SRE, fixed `bbd95ff`; WebKit `fe-minors.spec.ts:24` PD-R3S2-02 → FE/QA; Chromium `resumable-upload.spec.ts:38` → QA); `ci-gate` failure |
| 2026-10-08 | 37718386760 (pull_request, PR #4) | `sprint-03` / `f554edd` (SRE fixes `8be152d` ADR 0046 amendment, `bbd95ff` E2E_ADMIN_CMD) | failure | Per job: Python unit, Ruff, mypy, secret scan, drill-lint, fixtures, actionlint, Locust, infra, web, SBOM **success**; flaky report skipped (by design). **E2E failure: 1 failed, 15 skipped, 224 passed (14.9 m)**, only `[webkit] fe-minors.spec.ts:24` PD-R3S2-02 (E2E-03-05 now passes in both browsers; the Chromium resumable-upload failure did not recur). **Integration failure** (exit 124 at the 600 s budget, again). **PR policy failure** (PR size). `ci-gate` failure |
| 2026-10-08 | 37719909230 (pull_request, PR #4) | `sprint-03` / `7ef4c50` (docs only on top of `f554edd`) | failure | Per job: Python unit, Ruff, mypy, secret scan, drill-lint, fixtures, actionlint, Locust, infra, web, SBOM **success**; **Integration success** (step 9 02:52:42 → 03:01:44, 542 s incl. `uv sync`, inside the 600 s budget this time: the budget is borderline, 2 of 3 runs on PR #4 exceeded it; blockers.md row stays open); flaky report skipped (by design). **E2E failure**: 1 failed, 15 skipped, 224 passed (16.0 m), only `[webkit] fe-minors.spec.ts:24` PD-R3S2-02 (owner senior-frontend-engineer with senior-qa-engineer; decision-log row of this date). **PR policy failure** (PR size; no EM `size-waiver`). `ci-gate` failure. **PR #4 not merged** (PO rule: merge only when CI is green) |

## CI-IT0213-HANG: IT-02-13 rate test timed out in scheduled run 37764445816 (2026-10-08)

Owner: senior-backend-engineer. Run <https://github.com/nhuthuynh/racket-analytics/actions/runs/37764445816>, job 113268514073 ("Integration, scenario and regression suites on Compose"), head `5f80f0a` on `main`. Only failure: `tests/integration/test_it_02_13_scorebook_limits.py::test_it_02_13_parallel_commands_never_pass_the_per_account_rate[1]`, `Failed: Timeout (>120.0s) from pytest-timeout`, worker `gw3`, `1 failed, 2088 passed, 1 skipped in 273.11s`. The same code passed on push run #66.

### Root cause

**The 120 s ran out in the test's arrange step, before the parallel burst was sent.** The rate limiter, its advisory lock and the connection pool played no part.

1. Where it stopped. The failure points at line 108, `api.run(sb.receive_video(ivy, match_id))`, inside the loop that uploads a video to each of the 12 matches. The `burst()` at line 117 never ran.
2. What the process was doing. The pytest-timeout dump shows two threads. One is the AnyIO worker of the API, in `video_ingest/service.py:416 write_chunk` → `platform/storage.py:149 upload_part` → botocore → `http/client.py _read_status` → `socket.recv_into`, waiting for the object store to answer an S3 `UploadPart`. The other is xdist's execnet receiver. No thread waited on Postgres, a lock, the pool or the event loop.
3. How much data went through. `receive_video` sends the 1,724,207-byte clip in two PATCHes. The first chunk is staged with `PutObject` (862,104 bytes) because it is under the 5 MiB part minimum. The second sends staged + chunk as one `UploadPart` (1,724,207 bytes). That is 2,586,311 bytes of S3 writes per match and 31,035,732 bytes for the 12 matches. Measured with the new harness test (red output below).
4. How fast the store took it. The API request log of the failed test and the store's own log, both in the job log, show:

   | Upload # | PATCH 1 (0.86 MB `PutObject`) | PATCH 2 (1.72 MB `UploadPart` + complete) |
   |---|---|---|
   | 1-2 | < 0.6 s | < 0.6 s |
   | 3 | 3.56 s | 8.79 s |
   | 4 | 3.14 s | 6.70 s |
   | 5 | 13.6 s | 26.9 s |
   | 6 (`10:39:57.18` → `10:40:10.51` → `10:40:37.18`) | 13.33 s | 26.67 s |
   | 7 (`10:40:37.23` → `10:40:50.56`) | 13.33 s | still waiting when the timeout fired at `10:40:53` |

   13.33 s for 862,104 bytes and 26.67 s for 1,724,207 bytes is about 64 KiB/s, in proportion to the bytes sent. In the store log (`--tail=200`), the gaps between requests match these times exactly (`10:39:57.19` → `10:40:10.53`, 13.3 s; `10:40:10.53` → `10:40:37.24`, 26.7 s). Small writes from the other workers in the same minute (`staging/…` PUT followed by its part 30 ms later) stayed fast.
5. Postgres was not the bottleneck. In the job's Postgres log, the checkpoint at `10:39:53` reports `write=0.002 s, sync=0.009 s`. There are no lock timeouts or deadlocks in the window, only the expected `could not obtain lock` from the NOWAIT test at `10:37:47`.

So a test that checks the per-account command rate spent its whole budget moving 31 MB through the object store. When the store's write throughput on the runner fell to about 64 KiB/s for two minutes, the arrange step alone needed about 8 minutes (12 × 39.5 s). The SeaweedFS log kept by CI is only the last 200 lines, so it does not say why the store slowed down. A disk stall is unlikely (see the Postgres checkpoint). The cause inside the store stays open (see Follow-ups).

### Reproduction (local, deterministic)

`backend/tests/support/slow_store.py` is a TCP proxy in front of the real SeaweedFS. It passes bytes to the store at `CI_WRITE_RATE` = 64 KiB/s, the rate measured above. The stack: Postgres 16 (`scripts/dev-postgres.sh`) and SeaweedFS 3.97 in Docker with the CI flags (`weed server … -volume.max=0 -master.volumeSizeLimitMB=1024 -filer -s3`, image `mirror.gcr.io/chrislusf/seaweedfs:3.97`).

- Red (commit `fceb7ff`): `uv run pytest -n 3 tests/features/test_ci_it0213_rate_on_a_slow_store.py tests/integration/harness/test_ci_it0213_rate_arrange.py tests/unit/test_slow_store_throttle.py` gave `2 failed, 5 passed in 132.93s`:
  - The scenario failed with `Failed: Timeout (>120.0s) from pytest-timeout`. Its dump shows the same CI stack: the AnyIO worker in `write_chunk` → `storage.put_bytes` → botocore → `recv_into`, plus the proxy's `_pump` threads.
  - The harness test failed with `assert 31035732 <= 16384`.
- At the reproduced hang, sampled 40 s and 80 s in: `pg_stat_activity` showed one session `idle in transaction` (ClientRead, 25 s old, the PATCH's `SELECT … FROM upload_sessions … FOR UPDATE NOWAIT`) and one idle. `pg_locks` showed 0 waiting locks and 0 advisory locks. Nothing in the database was blocked. The open transaction is the upload row lock that ADR 0011 holds while a chunk is stored.
- Without the proxy, the CI suite does not fail locally. Three full runs, each `-n 4` on 4 vCPUs: `2071 passed, 19 skipped` with dev SeaweedFS and the CI flags; the same in 143.56 s with `-volume.max=7`; and `2071 passed, 19 skipped in 182.58s` with `--cov` against the Docker store. This matches CI, where the same code passed on run #66.

### Fix

The harness, not the product. The rate tests need a match whose video is received. They never probe the video, so the 1.72 MB clip is not needed.

- `tests/support/rate_burst.py` (new): `matches_with_video(api, client, prefix, count)` creates the matches and receives a 64-byte MP4-headed video (`tus.video_bytes(64)`) through the real tus API (create, HEAD, one PATCH). That is 64 bytes per match instead of 2,586,311.
- Green (commit `a0d5466`): the same three files gave `7 passed in 4.54s`. The scenario through the 64 KiB/s store took 2.00 s (it had timed out at 120 s).
- `test_it_02_13_parallel_commands_never_pass_the_per_account_rate` must use the helper (a 3-line change). This is a change to an accepted test, so it waits for the TCR row of 2026-10-08 (CI-IT0213-HANG) and is **not committed** until QA decides (retro 2 M4). Evidence with the change applied in the working tree:
  - `VIA_PROXY=1 loop200.sh`: 70 rounds × 3 params with `-n 4`, every S3 call through the 64 KiB/s proxy → `consecutive passes: 210`.
  - `loop200.sh` without the proxy, run at the same time as a full `--cov -n 4` suite: `consecutive passes: 210`.
  - The full suite: `2078 passed, 19 skipped in 305.72s`.

The command each round ran: `uv run pytest -q -n 4 tests/integration/test_it_02_13_scorebook_limits.py::test_it_02_13_parallel_commands_never_pass_the_per_account_rate`, with the round counted only on `3 passed`.

Not done, by rule: no skip, no quarantine, no retry, and no higher timeout. No ADR: the fix does not change any concurrency design.

### CI evidence on the PR

Three consecutive green runs of the integration job on the PR head are still to be recorded here after the QA decision and push. Until then this goal is **not met**.

### Follow-ups (not in this ticket)

- The store slowdown itself (about 64 KiB/s for big writes on the runner) has no cause yet. Suggestion for sre-devops-engineer: on failure, the integration job should keep the whole object store log as an artifact, not `--tail=200` (`ci.yml` "Service logs on failure").
- A slow store keeps a PATCH's transaction and its `upload_sessions` row lock open for as long as the S3 write takes (observed: 25 s, `idle in transaction`). With pool 5 + overflow 10, about 15 slow PATCHes at once would use up the pool. This is design (ADR 0011 step order), not this defect; it is for the principal-engineer to decide whether to bound it.
- Other tests that use `sb.receive_video` once or twice per test are not at risk on the same scale (2.6 MB each). IT-02-13 was the only one that uploaded 12 videos in one test.

### Review round 1 (PE-PR17-01, QA-PR17-01): the fix to IT-02-13 is committed

The senior-qa-engineer accepted the TCR row with conditions in the [PR #17 review](https://github.com/nhuthuynh/racket-analytics/pull/17#pullrequestreview-5456430248); the decision is copied into the row. The 3-line change plus 1 import is commit `a3500d1` (`test(CI-IT0213-HANG)`), on its own. Local stack (Postgres 16 via `scripts/dev-postgres.sh`, SeaweedFS 3.97 via `scripts/dev-objectstore.sh`), `backend/`, `T=tests/integration/test_it_02_13_scorebook_limits.py::test_it_02_13_parallel_commands_never_pass_the_per_account_rate`:

- Red, test unchanged, every S3 call through `slow_object_store` at `CI_WRITE_RATE` (scratch `-p` plugin that wraps `S3_ENDPOINT_URL` for the whole run): `uv run pytest -q -n 3 -p viaslow $T` gave `3 failed in 131.06s`.
- Green, with `a3500d1`, the same command 3 times: `3 passed in 4.45s`, `3 passed in 4.59s`, `3 passed in 4.72s`.
- Direct (no proxy), 3 times: `uv run pytest -q -n 3 $T` gave `3 passed in 4.13s`, `4.18s`, `4.01s`.
- The ticket's suites and the whole IT-02-13 file: `uv run pytest -q -n 3 tests/integration/test_it_02_13_scorebook_limits.py tests/features/test_ci_it0213_rate_on_a_slow_store.py tests/integration/harness/test_ci_it0213_rate_arrange.py tests/unit/test_slow_store_throttle.py` gave `18 passed in 6.53s`. `uv run mypy`: `Success: no issues found in 94 source files`.

CI on the PR head `f2130ba` (code head; the commit after it changes only this file), [run 37777727725](https://github.com/nhuthuynh/racket-analytics/actions/runs/37777727725), job "Integration, scenario and regression suites on Compose (+ changed-lines coverage)", 3 consecutive attempts, each `success` (including the step "Backend suites with coverage (< 10 min, NFR-073)", which runs IT-02-13):

| Attempt | Job id | Started → completed (UTC) | Conclusion |
|---|---|---|---|
| 1 | 113312713391 | 12:33:37 → 12:37:25 | success |
| 2 | 113319980852 | 12:51:22 → 12:55:49 | success |
| 3 | 113327553218 | 13:09:12 → 13:14:16 | success |

The other jobs of attempt 1 were green as well, except `PR policy (test immutability, size)`, which fails as designed until the senior-qa-engineer applies `qa-approved-test-change` (log: `test-immutability: … modified: backend/tests/integration/test_it_02_13_scorebook_limits.py`) and the size waiver is recorded; `ci-gate` follows it.
