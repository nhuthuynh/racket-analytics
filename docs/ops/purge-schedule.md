# Purge schedule (runbook)

Owner: sre-devops-engineer. Story: SRE-PURGE (NFR-066 c, NFR-047). Design: ADR 0038 (Accepted, PE-3). Compose service: `purge` in `infra/compose.yaml` (slice b). Job: ST-050 (`python -m racket.platform.purge --once`, also runs ST-038 expiry).

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

The `purge` Compose service (ADR 0038, slice b) has the app identity; the on-demand pass uses the same image and identity as the scheduled one:

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

## Evidence, slice (b), 2026-10-07 (goal round 2, G03-03)

Isolated Compose project `racket-sre-gr2` over HTTPS (`https://localhost:43000`), method env of goal-scorecard §4.0, head `b889dc3` plus this change.

| Check | Command | Result |
|---|---|---|
| Config tests (red first) | `cd infra && DOCKERHUB_REGISTRY=mirror.gcr.io uv run pytest -q tests/test_compose_purge_service.py tests/test_compose_registry.py` | red `6 failed, 3 passed`; green `9 passed` |
| Schedule rendered | `$DC config \| grep -nE 'PURGE_(INTERVAL\|SCHEDULE)'` | `343:      PURGE_INTERVAL_S: "86400"`, rc 0 |
| Service up | `$DC up -d --build --wait` | rc 0, `purge` Healthy; runs as `uid=999(app)`; first scheduled run `purge.run` `status ok`, `exit_code 0` |
| G03-03 method | `live_stats.py --runs 5 … --purge-cmd "$DC exec -T purge python -m racket.platform.purge --once"` | rc 0, `runs_passed 5`; `purge.ok true`, all 20 columns 0 rows, `media [404 x5]`, `problems []` |
| Cadence | `PURGE_INTERVAL_S=15 $DC up -d --wait purge` | runs 1, 2, 3 at 22:22:10, :25, :40 (15 s apart), all `ok` |
| Graceful stop | `$DC stop purge` | 3.4 s, exit 0, last line `purge.schedule.stopped` |
| Teardown | `$DC down -v --rmi local --remove-orphans` | 0 containers left |

Note: the variable is rendered as given, so an operator value above 86400 still renders; the scheduler then refuses it at start (exit 2, the container never turns healthy), which keeps NFR-066 c fail-closed.

## Rollback

Remove the `purge` service from `infra/compose.yaml` (slice b) and the `COPY` line in the API stage; nothing else depends on them.
