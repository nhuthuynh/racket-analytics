# 0038. The purge/expiry job runs as its own scheduled Compose service with the app identity

- **Status:** Accepted (principal-engineer, PE-3, 2026-10-07, Sprint 3 review round 1, PE-R1S3-04): adopted by `docs/architecture/deletion-and-purge.md` §4.1 and ADR 0042. Proposed by the sre-devops-engineer on 2026-10-07. The identity is the API's existing app role and app S3 key, so it grants nothing new; the security-privacy-engineer's SEC-1 notes may still narrow it (a dedicated purge role, deletion-and-purge.md §7), by a new ADR
- **Date:** 2026-10-07
- **Deciders:** principal-engineer (PE-3), security-privacy-engineer (SEC-1)
- **Consulted:** sre-devops-engineer (author), senior-backend-engineer (ST-050 job, ST-038 expiry)
- **Related:** SRE-PURGE, ST-050, ST-038, ST-042, NFR-066 (b, c), NFR-047, NFR-054, goal-scorecard G03-03, blockers.md SRE-PURGE row (2026-10-06), ADR 0017 (job queue), ADR 0027 (mailer outside the media sandbox)

## Context and problem statement

NFR-066 (c) asks for the purge to run at least daily; G03-03 runs it once on the live stack and checks `$DC config | grep -nE 'PURGE_(INTERVAL|SCHEDULE)'`. The scorecard assumed `$DC exec -T worker python -m racket.platform.purge --once`. Since ST-042 (`a1bf473`) the `worker` service runs as `racket_media_worker` with an S3 key limited to Read/Write on the media bucket and no DELETE on most tables (IT-03-10), on the `sandbox` network. A purge deletes rows in every context and objects in the bucket, so it cannot run there without undoing ST-042. Something has to run the job on a schedule, with an identity that may delete.

## Decision drivers

- Least privilege stays as ST-042 made it: the media sandbox worker gets no new grant or key (NFR-054).
- Dev/prod parity and 12-factor: the schedule is part of the Compose stack, configured by environment, logs on stdout (AQS/OPS-01, AQS/OPS-03, AQS/OPS-05).
- At least daily, enforced by the scheduler, not only by a default (NFR-066 c).
- Job health visible: one log line per run, failures at ERROR, spans in the tracing UI (NFR-047).
- One on-demand run for evidence, with the same image and identity as the scheduled run.

## Considered options

1. **A separate `purge` Compose service (proposed):** API image (no ffprobe), app Postgres role and app S3 key, `edge` network, hardened like the mailer (read-only root, `cap_drop: ALL`, `no-new-privileges`). Its command is `infra/docker/purge_schedule.py`, a standard-library scheduler that runs `python -m racket.platform.purge --once` at start and every `PURGE_INTERVAL_S` (default 86400; refuses anything that is not a whole number from 1 to 86400), logs one JSON line per run, keeps a heartbeat for the healthcheck and passes SIGTERM to an in-flight run. On demand: `$DC exec -T purge python -m racket.platform.purge --once`.
   - Good: no change to the worker's privileges; the job code (ST-050) stays a plain `--once` CLI that is easy to test; failures do not touch the API or the media pipeline; the schedule shows in `docker compose config`.
   - Bad: one more long-running container and image build; the app identity can delete everywhere, so the job's own code is the control on what it deletes (PE-3 order, IT-03-06/07). A dedicated purge DB role is possible later (judgment: not needed for R1, since the API already holds the same role).
2. **Run the purge in the `worker` service.** Bad: needs DELETE grants and an S3 key with Delete on every prefix for the sandboxed process that parses untrusted media, reversing ST-042 (NFR-054).
3. **A background task inside the API process.** Good: no new container. Bad: every API replica would run it (needs a lock); a slow purge competes with requests; restarts of the web tier reset the timer; harder to run once on demand.
4. **Enqueue a `purge` job on the existing queue (ADR 0017) from a timer, run by a job runner with the app identity.** Good: reuses leases and retries. Bad: still needs a timer process and a runner outside the sandbox, i.e. option 1 plus queue plumbing; can be adopted later inside the job without changing the Compose shape.
5. **Host cron / a platform scheduler.** Bad: not part of the Compose stack, so the dev stack and the goal method cannot show it; no dev/prod parity.
6. **`pg_cron` in Postgres.** Bad: cannot delete objects in the object store.

## Decision outcome

Option 1, proposed to PE-3. Delivery is sliced (sprint-03 decision-log 2026-10-07):

- **Slice (a), done:** `infra/docker/purge_schedule.py`, its tests (`infra/tests/test_purge_schedule.py`) and the `COPY` into the API image. Live in the image: failed runs logged at ERROR and the schedule continued; SIGTERM stop in 1 s, exit 0; `PURGE_INTERVAL_S=90000` refused with rc 2 (`docs/ops/purge-schedule.md`).
- **Slice (b), after QA decides the test-change row for `test_compose_registry.py::test_the_five_app_services_are_the_built_ones` (it lists the built services exactly) and PE-3 accepts this ADR:** the `purge` service below in `infra/compose.yaml`, with its config tests (identity not the media worker's, not on `sandbox`, hardening, `PURGE_INTERVAL_S` default 86400 and rendered ≤ 86400 for G03-03 c).
- **Live run:** after ST-050 ships `racket.platform.purge`. Until then the scheduler logs a failed run per interval (`No module named racket.platform.purge`), which is the truth.

Proposed service (slice b):

```yaml
  purge:
    build:
      context: ..
      dockerfile: infra/docker/backend.Dockerfile
      args: *backend-build-args
      target: api
    command: ["python", "/opt/racket/purge_schedule.py", "python", "-m", "racket.platform.purge", "--once"]
    environment:
      <<: [*app-env, *media-store-access]
      OTEL_SERVICE_NAME: racket-purge
      PURGE_INTERVAL_S: ${PURGE_INTERVAL_S:-86400}
    restart: unless-stopped
    networks: [edge]
    read_only: true
    tmpfs:
      - /tmp:size=64m
    cap_drop: [ALL]
    security_opt: ["no-new-privileges:true"]
    depends_on:
      postgres: {condition: service_healthy}
      migrate: {condition: service_completed_successfully}
      objectstore-init: {condition: service_completed_successfully}
    healthcheck:
      test: ["CMD-SHELL", "test -f /tmp/purge-heartbeat && test $$(( $$(date +%s) - $$(stat -c %Y /tmp/purge-heartbeat) )) -lt 60"]
      interval: 5s
      timeout: 3s
      retries: 12
    stop_signal: SIGTERM
    stop_grace_period: 30s
```

### Consequences

- The G03-03 method changes `exec -T worker` to `exec -T purge` (method author, with `statscontract.PURGE_ONCE` unchanged); routed in blockers.md.
- The job (ST-050) must be safe when a scheduled pass and an on-demand pass overlap (IT-03-07 "parallel passes" already asks for it).
- Spans: the job sets up tracing as the other entry points do; `OTEL_SERVICE_NAME=racket-purge` names them in Jaeger. The scheduler itself only logs.
- Rollback: remove the `purge` service; nothing else depends on it.

## Notes

- **2026-10-07 (principal-engineer, PE-3):** Accepted. The job is `python -m racket.platform.purge --once` with exit codes 0 (every due item done), 1 (an item failed, retried next pass), 2 (usage/config); one pass also expires abandoned uploads (ST-038). The G03-03 on-demand command is `$DC exec -T purge python -m racket.platform.purge --once` (api-sprint-03 §4.4). Slice (b) may start once QA decides the `test_compose_registry.py` TCR row.
