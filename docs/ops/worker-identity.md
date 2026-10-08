# Media sandbox worker identity (ST-042, NFR-054)

Owner: sre-devops-engineer. Grants: migration `0012` (senior-backend-engineer). Decision-log 2026-10-06 (ST-042 Compose half).

| What | Where | Scope |
|---|---|---|
| Postgres group role `racket_media_worker` | migration `0012` | NOLOGIN; probe-stage grants only (jobs SELECT/UPDATE, media and upload tables, matches SELECT/UPDATE). Nothing on `accounts`, `sessions`, `sign_in_*` or the scorebook tables |
| Worker login `WORKER_DB_USER` / `WORKER_DB_PASSWORD` | `db-roles` one-shot in `infra/compose.yaml` | Member of the group role, no admin attributes. Created if missing, password set to the env value on every start |
| Worker S3 key `WORKER_S3_ACCESS_KEY_ID` / `WORKER_S3_SECRET_ACCESS_KEY` | `objectstore` identity `racket-worker` | `Read:` and `Write:` on `S3_BUCKET_MEDIA` only |

## Rotate

1. Put the new values in the env or secret store (`WORKER_DB_PASSWORD`, `WORKER_S3_SECRET_ACCESS_KEY`).
2. `docker compose … up -d db-roles objectstore worker`. `db-roles` sets the new password, `objectstore` rewrites its identities, and the worker reconnects with the new values.
3. Check: `docker compose … exec -T postgres psql -U "$POSTGRES_USER" -c "select usename from pg_stat_activity where usename = '$WORKER_DB_USER'"` returns one row.

Rollback: put the old values back and repeat step 2.

## Check least privilege

`cd infra && uv run pytest -q tests/test_compose_worker_identity.py tests/test_compose_worker_identity_live.py` (needs Docker; it runs its own project and removes it).

## Not here

Staging and production take these values from the deployment secret store, never `env.example`. Managed Postgres and object stores must apply the same scopes (ADR 0034, deployment edge).
