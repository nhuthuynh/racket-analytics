# Purge schedule (runbook)

Owner: sre-devops-engineer. Story: SRE-PURGE (NFR-066 c, NFR-047). Design: ADR 0038 (Proposed, waits on PE-3). Job: ST-050 (`python -m racket.platform.purge --once`, also runs ST-038 expiry).

## What runs

`infra/docker/purge_schedule.py` (standard library, copied into the API image at `/opt/racket/purge_schedule.py`) runs the job command once at start and then every `PURGE_INTERVAL_S` seconds.

| Variable | Default | Rule |
|---|---|---|
| `PURGE_INTERVAL_S` | `86400` | whole seconds, 1..86400; anything else exits 2 before any run (NFR-066 c: at least daily) |
| `PURGE_TICK_S` | `10` | heartbeat period, 1..300 |
| `PURGE_HEARTBEAT_FILE` | `/tmp/purge-heartbeat` | the healthcheck reads its age (< 60 s) |

## Logs (stdout, one JSON line each)

- `purge.schedule.started` (`interval_s`, `program`: the program name only, never the arguments).
- `purge.run` per run: `status` `ok`/`failed`, `exit_code`, `duration_ms`, `run`, `consecutive_failures`, `next_run_in_s`. Failed runs are `level: ERROR`; the schedule continues.
- `purge.job.not_started` when the command cannot be executed (counts as a failed run, exit code 127).
- `purge.schedule.stopped` after SIGTERM/SIGINT; an in-flight job receives SIGTERM first and is waited for.

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

## Rollback

Remove the `purge` service from `infra/compose.yaml` (slice b) and the `COPY` line in the API stage; nothing else depends on them.
