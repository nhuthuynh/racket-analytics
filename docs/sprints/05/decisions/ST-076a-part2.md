# ST-076a-part2 decisions

Per-ticket decision file (working-agreement §3). Ticket: ST-076a, part 2 of 2 (story ST-076 "Nothing a player corrected is lost", P1; NFR-045.1; ADR 0058 rules 1-3; threat rows T5-BK-1..3). Owner: sre-devops-engineer. Review tier 2 (ADR 0056): principal-engineer, security-privacy-engineer, senior-qa-engineer test. Stacked on part 1 (PR #210, branch `s05/st-076a-backup-service-nightly-encrypted-pg-dump`); merges after it.

## Why this part exists

The PR-policy step split PR #210 (602 production lines, planned S) into two parts instead of a `size-waiver`: see the "Size decisions" table in `docs/sprints/05/decisions/ST-076a.md`. This part holds the container and object-store wiring: `infra/docker/backup/Dockerfile`, the Compose `backup` service (profile `ops`), the `db-roles` backup login, the objectstore `racket-backup` identity, the `BACKUP_*` variables in `infra/env.example`, and the SigV4 media mirror in `scripts/ops/backup.py`. Measured against the part-1 head: 274 production lines.

## Decisions

The image, store-key, root-user, healthcheck and deferral rows dated 2026-11-05 in `docs/sprints/05/decisions/ST-076a.md` apply to this part unchanged; they are not copied here.

| Date | Who | Decision | Evidence | Why |
|---|---|---|---|---|
| 2026-11-05 | engineering-manager and senior-qa-engineer (PR-policy step) | **Code moved unchanged from PR #210 at `fe9f5ca0`; tests moved into new files** (`infra/tests/test_backup_service_store.py`, `tests/features/backup_service_compose.feature`) | `git diff fe9f5ca0 HEAD -- scripts/ops/backup.py infra/compose.yaml infra/env.example infra/docker/backup/Dockerfile` is empty; red `bfbb28d0`, green `353b6a3a` | New files keep part 1's tests and scenario file unchanged once it is on `main`, so this part changes no accepted test except `test_compose_registry.py` (TCR row approved in `ST-076a.md`) |

## Evidence

- Red (`bfbb28d0`): `cd infra && uv run pytest -q tests/test_backup_service.py tests/test_backup_service_scenarios.py tests/test_backup_service_store.py tests/test_compose_registry.py` → `13 failed, 39 passed` (`no attribute 'sign_v4'`; `DID NOT RAISE NotEncrypted` for `objects.tar.age`; `no \`backup\` service` x6; `KeyError: 'backup'`). `DOCKERHUB_REGISTRY=mirror.gcr.io uv run pytest -q -x tests/test_backup_service_live.py` → `1 error: no such service: backup`.
- Green (`353b6a3a`): the same unit run → `52 passed`; IT-05-03 `-m integration tests/test_backup_service_live.py tests/test_compose_registry.py` → `11 passed in 65.43s`; the nine Compose IT files → `28 passed in 38.22s`; whole infra unit suite → `1 failed, 1857 passed, 2 skipped` (`test_dev_chrome.py::test_real_install_passes_check_mode`, environment, also fails on `main`).
