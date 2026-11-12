# ST-076a-part2 decisions

Per-ticket decision file (working-agreement §3). Ticket: ST-076a, part 2 of 2 (story ST-076 "Nothing a player corrected is lost", P1; NFR-045.1; ADR 0058 rules 1-3; threat rows T5-BK-1..3). Owner: sre-devops-engineer. Review tier 2 (ADR 0056): principal-engineer, security-privacy-engineer, senior-qa-engineer test. Stacked on part 1 (PR #210, branch `s05/st-076a-backup-service-nightly-encrypted-pg-dump`); merges after it.

## Why this part exists

The PR-policy step split PR #210 (602 production lines, planned S) into two parts instead of a `size-waiver`: see the "Size decisions" table in `docs/sprints/05/decisions/ST-076a.md`. This part holds the container and object-store wiring: `infra/docker/backup/Dockerfile`, the Compose `backup` service (profile `ops`), the `db-roles` backup login, the objectstore `racket-backup` identity, the `BACKUP_*` variables in `infra/env.example`, and the SigV4 media mirror in `scripts/ops/backup.py`. Measured against the part-1 head: 274 production lines.

## Decisions

The image, store-key, root-user, healthcheck and deferral rows dated 2026-11-05 in `docs/sprints/05/decisions/ST-076a.md` apply to this part unchanged; they are not copied here.

| Date | Who | Decision | Evidence | Why |
|---|---|---|---|---|
| 2026-11-05 | engineering-manager and senior-qa-engineer (PR-policy step) | **Code moved unchanged from PR #210 at `fe9f5ca0`; tests moved into new files** (`infra/tests/test_backup_service_store.py`, `tests/features/backup_service_compose.feature`) | `git diff fe9f5ca0 HEAD -- scripts/ops/backup.py infra/compose.yaml infra/env.example infra/docker/backup/Dockerfile` is empty; red `bfbb28d0`, green `353b6a3a` | New files keep part 1's tests and scenario file unchanged once it is on `main`, so this part changes no accepted test except `test_compose_registry.py` (TCR row approved in `ST-076a.md`) |

| 2026-11-12 | sre-devops-engineer | **After #210 merged, `origin/main` was merged into this branch (`aa184d36`, no conflicts); part 1's process and live tests now give every run a media store** (a local SigV4-checking stand-in, `infra/tests/fake_s3.py`) instead of making the mirror optional | At `aa184d36` the part-1 tests `test_backup_service_take.py` (2) and `test_backup_service_dump_live.py` (1) fail: `backup.run` `status: failed`, `error: KeyError` (no `S3_ENDPOINT_URL`) | ADR 0058 rule 1 makes `objects.tar.age` part of every set, so a run with no store must fail closed (new test), not write a set without the objects. The part-1 tests were written while the mirror was deferred to this part; they now assert three artefacts. TCR row below |

## Test change request (TCR), decided by the senior-qa-engineer

| Date | Test | Change | Why | Decision |
|---|---|---|---|---|
| 2026-11-12 | `infra/tests/test_backup_service_take.py` (all tests via `run()`; `test_once_writes_only_age_ciphertext_for_the_recipient_and_backup_json_last`) and `infra/tests/test_backup_service_dump_live.py` (`world` fixture, steps "every artefact ... age header" and "backup.json is complete ...") | `run()`/`run_backup()` pass the env of a local fake media bucket (`fake_s3.py`); the expected set gains `objects.tar.age`; new checks: no object plaintext in any file, the decrypted tar holds every object and `objects.manifest.json`, `backup.json` `objects` = count + manifest SHA-256, the mirror sent only `GET`, the store secret is never logged. New test `test_a_run_without_a_media_store_fails_closed_and_writes_no_backup_json` | Part 2 adds the ADR 0058 third artefact, so "exactly two artefacts" no longer holds. Every earlier assertion is kept; the exact artefact list stays an equality check | **Proposed; pending the senior-qa-engineer.** `infra/tests/` is not a protected path, so `check_test_immutability.py` passes without a label; the PR stays draft until this row is decided |

## Evidence

- Red (`bfbb28d0`): `cd infra && uv run pytest -q tests/test_backup_service.py tests/test_backup_service_scenarios.py tests/test_backup_service_store.py tests/test_compose_registry.py` → `13 failed, 39 passed` (`no attribute 'sign_v4'`; `DID NOT RAISE NotEncrypted` for `objects.tar.age`; `no \`backup\` service` x6; `KeyError: 'backup'`). `DOCKERHUB_REGISTRY=mirror.gcr.io uv run pytest -q -x tests/test_backup_service_live.py` → `1 error: no such service: backup`.
- Green (`353b6a3a`): the same unit run → `52 passed`; IT-05-03 `-m integration tests/test_backup_service_live.py tests/test_compose_registry.py` → `11 passed in 65.43s`; the nine Compose IT files → `28 passed in 38.22s`; whole infra unit suite → `1 failed, 1857 passed, 2 skipped` (`test_dev_chrome.py::test_real_install_passes_check_mode`, environment, also fails on `main`).
- After the merge of `origin/main` (2026-11-12, red `aa184d36`): `cd infra && uv run pytest -q -n 8 --dist loadfile -m unit` → `5 failed, 1945 passed` (`test_backup_service_take.py::test_once_writes_only_age_ciphertext_for_the_recipient_and_backup_json_last` and `::test_the_set_cannot_be_read_without_the_identity`: `"error": "KeyError"`; plus 3 environment failures unrelated to this change: `test_dev_chrome.py::test_real_install_passes_check_mode` (installed Chrome 153 vs pinned 141), 2x `test_warm_hypothesis_constants.py` (`No module named pytest`: this worktree has no synced backend virtualenv)); `uv run pytest -q tests/test_backup_service_dump_live.py` → `1 failed, 1 passed`.
- Green (test fix commit): unit → `3 failed, 1948 passed` (the 3 environment failures only); `uv run pytest -q tests/test_backup_service_take.py` → `6 passed`; `DOCKERHUB_REGISTRY=mirror.gcr.io uv run pytest -q -n 4 --dist loadfile -m integration tests/test_backup_service_live.py tests/test_compose_registry.py tests/test_backup_service_dump_live.py tests/test_compose_obs_profile.py tests/test_compose_purge_service.py tests/test_compose_settings_parity.py tests/test_compose_least_privilege.py` → `13 passed in 75.42s`.
