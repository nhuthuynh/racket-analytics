# Sprint 3 CI status

Per-run, per-job record of CI failures and their root causes. One section per failure; each claim carries the command or log line it rests on. Append only.

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
