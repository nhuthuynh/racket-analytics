# CI-INFRA-BUDGET decisions

Incident: push CI on main 5bba847 (run 40908731812, merge of #151). Job `infra-tests`
(`timeout-minutes: 10`) logged `1717 passed, 10 skipped in 581.90s (0:09:41)` and was then
cancelled by the job timeout during post-job cleanup; `ci-gate` failed on `infra-tests: cancelled`.
Nothing was failing: the serial suite had crept up to its budget (green runs took 9:30-9:58).

## Evidence before the fix (serial, local, origin/main 5bba847)

`cd infra && time uv run pytest -q -m "unit or integration" --durations=30 -p no:cacheprovider`
-> `4 failed, 1715 passed, 8 skipped in 638.15s (0:10:38)`, `real 10m39.551s, user 3m19.212s`.
Wall time is about 3x CPU time: the suite mostly waits on services, sleeps and subprocesses, so
it parallelises well. The 4 failures are the Docker Hub `429 Too Many Requests` on
`busybox:1.36` in `test_compose_extra_ca*.py` (this sandbox's registry rate limit, an
environment fault; identical before and after the change).

Top offenders (seconds, phase, test):

| s | phase | test |
|---|---|---|
| 46.45 | call | test_dev_objectstore_ports.py::test_real_weed_survives_a_port_taken_by_another_process |
| 45.95 | setup | test_perf_window_locust.py::test_whole_run_rate_is_dragged_down_by_start_up |
| 29.24 | setup | test_compose_worker_identity_live.py::test_worker_login_cannot_read_identity_tables |
| 26.49 | call | test_ci_domain_budget_scenarios.py::test_the_domain_step_runs_in_parallel_workers_on_the_same_tests_with_the_same_results |
| 25.74 | call | test_compose_objectstore_netns_live.py::test_running_store_has_its_receive_buffer |
| 23.76 | setup | test_object_store_parity.py (module SeaweedFS stack, includes the first weed download) |
| 23.53 | setup | test_footage_bucket.py (module SeaweedFS stack) |
| 12.73 | call | test_ci_domain_budget_scenarios.py::test_a_fresh_checkouts_hypothesis_cache_is_filled_before_the_budget_starts |
| 10.77 | teardown | test_compose_worker_identity_live.py::test_the_app_key_keeps_full_access |
| 10.70 | teardown | test_compose_objectstore_netns_live.py::test_running_store_has_its_receive_buffer |
| 10.56 | call | test_ci_e2e_stall_report_scenarios.py::test_a_run_that_reaches_the_global_timeout_names_the_interrupted_test_and_keeps_a_report |
| 9.07 / 9.05 | call | test_objectstore_init_bounded(_scenarios).py: never-answering shell fails within the bound |

The SeaweedFS stacks are already module-scoped (one per file), so sharing fixtures further would
only couple unrelated files; the long tail is hundreds of short subprocess/wait tests.

## Decisions

| # | Decision | Reason | Evidence |
|---|---|---|---|
| 1 | Run the infra suite with pytest-xdist: `uv run pytest -q -n auto --dist loadfile --basetemp=/tmp/pt -m "unit or integration"`. pytest-xdist 3.8.0 added as a locked dev dependency (`uv add --dev "pytest-xdist>=3.6"`). | Root-cause fix: the job is I/O-bound (wall ~3x CPU). `loadfile` keeps every file's tests on one worker, so module-scoped service fixtures (SeaweedFS stacks, Compose projects) still start once per file and no test, assertion or marker is changed. Alternatives: raise the timeout (rejected: hides the creep, PO CI-first rule); split the job (more runner minutes, same creep); share one weed stack per session (couples files that assert on their own fresh store). | After, same machine: `5 failed, 1723 passed` then (after #3) `4 failed, 1725 passed, 8 skipped in 172.28s (0:02:52)`, `real 2m52.657s`; the 4 are the same Docker Hub 429s. 10:39 -> 2:53 (-73%). |
| 2 | `scripts/dev-objectstore.sh` takes `flock` on `.local/bin/.weed-download.lock` around the SeaweedFS download and re-checks the cache under the lock; a failed download removes its partial `.tgz`. | Parallel workers share `<repo>/.local/bin`; on a fresh CI checkout several workers start weed at once and would write the same `.tgz` concurrently (corrupt download, sha256 mismatch, flaky red). | Red: `test_two_first_starts_of_the_dev_object_store_download_seaweedfs_one_at_a_time` -> `downloads active at once: ['2', '2']`. Green after the lock. |
| 3 | Short `--basetemp=/tmp/pt` in CI. | Found by the first parallel run, not guessed: xdist adds `popen-gwN/` to every `tmp_path`, which pushed the multiprocessing socket of `test_parallel_migrations.py::test_the_helper_leaves_no_copy_of_the_migrations_behind` to 112 bytes, over Linux's 107-byte AF_UNIX limit (`OSError: AF_UNIX path too long`). Fixed in the invocation, not by editing the test. The runner is ephemeral, so wiping `/tmp/pt` at start is harmless; locally use your own short path. | Red: `test_parallel_temp_dirs_leave_room_for_unix_sockets` (no `--basetemp`). Green: deepest path 88 bytes; full parallel run no longer fails it. |
| 4 | Keep `timeout-minutes: 10` unchanged. | Expected CI time is well under the 6-minute target (local 2:53 on 4 cores; the runner has 4 vCPUs), so extra headroom is not needed; a guard test pins the timeout to 10-15 minutes. | `test_timeout_is_headroom_not_the_fix`. CI time to be confirmed on this PR's run. |
| 5 | Guard tests: `infra/tests/test_ci_infra_parallel.py` (unit) and `tests/features/ci_infra_budget.feature` bound by `infra/tests/test_ci_infra_budget_scenarios.py` (integration). | A later edit of the pytest line back to serial, or dropping the lock, turns a test red instead of creeping back to the timeout. | Red then green in the commit history (see PR). |
