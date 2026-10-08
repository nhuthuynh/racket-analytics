# Purge schedule (runbook)

Owner: sre-devops-engineer. Story: SRE-PURGE (NFR-066 c, NFR-047). Design: ADR 0038 (Proposed, waits on PE-3). Job: ST-050 (`python -m racket.platform.purge --once`, also runs ST-038 expiry).

## What runs

`infra/docker/purge_schedule.py` (standard library, copied into the API image at `/opt/racket/purge_schedule.py`) runs the job command once at start and then every `PURGE_INTERVAL_S` seconds.

| Variable | Default | Rule |
|---|---|---|
| `PURGE_INTERVAL_S` | `86400` | whole seconds, 1..86400; anything else exits 2 before any run (NFR-066 c: at least daily) |
| `PURGE_TICK_S` | `10` | heartbeat period, 1..300; does not delay a stop (a signal ends the wait between runs at once) |
| `PURGE_HEARTBEAT_FILE` | `/tmp/purge-heartbeat` | the healthcheck reads its age (< 60 s) |

## Logs (stdout, one JSON line each)

- `purge.schedule.started` (`interval_s`, `program`: the program name only, never the arguments).
- `purge.run` per run: `status` `ok`/`failed`, `exit_code`, `duration_ms`, `run`, `consecutive_failures`, `next_run_in_s`. Failed runs are `level: ERROR`; the schedule continues.
- `purge.job.not_started` when the command cannot be executed (counts as a failed run, exit code 127).
- `purge.schedule.stopped` after SIGTERM/SIGINT; an in-flight job receives SIGTERM first and is waited for. Between runs the stop is immediate whatever `PURGE_TICK_S` is, so it fits the 30 s `stop_grace_period` (ADR 0038).

The job's own output passes through unchanged; the scheduler never copies it into its records.

Find failures: `docker compose -f infra/compose.yaml logs purge | grep '"event": "purge.run"' | grep '"status": "failed"'`. Alert rule (once a log pipeline exists): `consecutive_failures >= 2` means a deletion is at least a day late against NFR-066 (judgment).

## Run once on demand (evidence)

After slice (b) adds the `purge` Compose service (ADR 0038):

```bash
docker compose -f infra/compose.yaml exec -T purge python -m racket.platform.purge --once
docker compose -f infra/compose.yaml config | grep -nE 'PURGE_(INTERVAL|SCHEDULE)'   # G03-03 (c)
```

## Evidence, slice (a), 2026-10-07

| Check | Command | Result |
|---|---|---|
| Unit tests (red first) | `cd infra && uv run pytest -q tests/test_purge_schedule.py` | red: `21 failed` (before the scheduler and service existed); green after slicing: `16 passed` |
| Image build | `docker build -f infra/docker/backend.Dockerfile --target api --build-arg PYTHON_IMAGE=mirror.gcr.io/library/python:3.11-slim …` | built |
| In the image, real job command, read-only root, `cap_drop ALL`, `PURGE_INTERVAL_S=3` | `docker run --read-only --tmpfs /tmp … python /opt/racket/purge_schedule.py python -m racket.platform.purge --once` | `purge.schedule.started` then runs 1..5 `status: failed, exit_code: 1, consecutive_failures: 1..5` (`No module named racket.platform.purge`: ST-050 not shipped); heartbeat fresh |
| Graceful stop | `docker stop -t 30` | stopped in 1 s, exit 0, last line `purge.schedule.stopped` |
| Over a day refused | `docker run --rm -e PURGE_INTERVAL_S=90000 … purge_schedule.py …` | `refused: PURGE_INTERVAL_S must be a whole number of seconds from 1 to 86400, got '90000'`, rc 2 |

## Evidence, port to main (PO P13), 2026-10-08

| Check | Command | Result |
|---|---|---|
| Scenarios red first (scheduler absent) | `origin/main f4db4e6` + the two new test files: `cd infra && DOCKERHUB_REGISTRY=mirror.gcr.io uv run pytest -q tests/test_purge_schedule_scenarios.py` | `3 failed` (`can't find '__main__' module in '/opt/racket/purge_schedule.py'`) |
| Scenarios + unit green | `cd infra && DOCKERHUB_REGISTRY=mirror.gcr.io uv run pytest -q tests/test_purge_schedule_scenarios.py tests/test_purge_schedule.py` | `19 passed` (3 scenarios in a container, 16 unit) |
| Infra job as CI runs it | `cd infra && DOCKERHUB_REGISTRY=mirror.gcr.io uv run pytest -q -m "unit or integration"` | `676 passed, 3 skipped` (gitleaks binary not set) |
| In the API image, real job command, `PURGE_INTERVAL_S=3`, read-only root, `cap_drop ALL` | `docker build -f infra/docker/backend.Dockerfile --target api …` then `docker run … python /opt/racket/purge_schedule.py python -m racket.platform.purge --once` | runs 1..3 `status: failed, exit_code: 1, level: ERROR, consecutive_failures: 1..3` (`No module named racket.platform.purge`: ST-050 not on main); heartbeat age 0.4 s |
| Graceful stop | `docker stop -t 30` | 0.77 s, exit 0, last line `purge.schedule.stopped` (`runs: 3`) |
| Over a day refused | `docker run --rm -e PURGE_INTERVAL_S=90000 … purge_schedule.py …` | `refused: … got '90000'`, rc 2 |

## Evidence, review round 1 (PE-R1-1, PE-R1-2), 2026-10-08

| Check | Command | Result |
|---|---|---|
| New tests red first (on `42473f6`) | `cd infra && DOCKERHUB_REGISTRY=mirror.gcr.io uv run pytest -q tests/test_purge_schedule_scenarios.py tests/test_purge_schedule.py` | `2 failed, 21 passed`: both between-runs stop tests (unit: no exit within 5 s of SIGTERM at `PURGE_TICK_S=300`) |
| Cadence mutant killed | same command with `sleep_until(started + 0)` | `5 failed, 18 passed`, incl. the new unit `test_runs_are_spaced_by_the_interval_not_back_to_back` and scenario `test_the_job_runs_at_start_and_again_after_each_interval` |
| Green after the self-pipe fix | same command | `23 passed` (5 scenarios in a container, 18 unit); infra job as CI runs it (`-m "unit or integration"`): `680 passed, 3 skipped` (gitleaks binary not set) |
| Reviewer's host repro | `PURGE_INTERVAL_S=600 PURGE_TICK_S=10` or `300`, `python3 infra/docker/purge_schedule.py true`, SIGTERM 2 s after start | tick 10: rc 0 in 0.015 s; tick 300: rc 0 in 0.010 s; last line `purge.schedule.stopped` |

## Rollback

Remove the `purge` service from `infra/compose.yaml` (slice b) and the `COPY` line in the API stage; nothing else depends on them.
