# Sprint 3 integration smoke (ADR 0022, ADR 0033 rule 3; SRE-SMOKE-3)

Three runs are planned: a **build-phase baseline** (this section, before the Sprint 3 stories land, so a later red can be told apart from one that was already there), the **pre-review smoke** on the integrated tree before review round 1, and the **sprint-close head** smoke. SRE-SMOKE-3 is done only after the last two.

## Build-phase baseline, 2026-10-07 (sre-devops-engineer)

- **Tree:** `sprint-03` at `ecee023`, as a clean detached worktree (`git worktree add --detach <scratch>/smoke3-wt ecee023`), so no lane's uncommitted file is in the run (the shared tree had uncommitted QA and EM files at the time).
- **Isolation:** own Compose project `racket-sre3smoke` (ports 61300 https, 61800 API, 61025 Mailpit UI, 61432, 61333), images through `mirror.gcr.io` (Docker Hub returned 429 earlier the same day), sandbox-only build-CA override outside the repository; own `RA_DEV_STATE` Postgres and object store for the backend suite.
- **Disk:** `df -h /` 19 GB free at the start (`disk-precheck: ok, 18 GB free on / (floor 16 GB)` before the build), 15 GB at the end (other lanes' stacks running).

### Verdict

**Platform green; the Sprint 2 journey still works on the Sprint 3 head; the Sprint 3 goal journey is not built yet (fails closed as designed).** One gate-selected red that is not a `red_until` row: SRE-S3-01, routed to the senior-qa-engineer. CI on `main` is red on the secret scan for a reason outside `main` (QA-R1S3-02, root cause in `ci-status.md`).

### Suites

| Suite | Command | Result |
|---|---|---|
| Infra (hooks, CI scripts, Compose, evidence wrapper, measure harness, purge scheduler) | `cd infra && DOCKERHUB_REGISTRY=mirror.gcr.io uv run pytest -q -p no:cacheprovider` | **581 passed, 1 skipped** (gitleaks binary not set) in 126 s |
| Web types, lint | `pnpm exec tsc --noEmit`; `pnpm exec eslint --max-warnings=0 .` | rc 0, rc 0 |
| Web unit | `pnpm exec vitest run` | **59 files, 477 passed** |
| Backend, full, own Postgres and object store | `env -u APP_ENV uv run pytest -q -p no:cacheprovider tests --ignore=tests/integration/test_it_00_10_worker_sandbox.py` | **112 failed, 50 errors, 2218 passed, 22 skipped** in 458 s. The 162 are the Sprint 3 red-first rows (IT-03-01..IT-03-14, QA-ACC-3 features, GS-AN-1 golden AN rows) and the known Sprint 2 `red_until` rows (ST-035 SOS 18, ST-025 phone fixtures 2, ST-024 nightly 1), **except one** (next row) |
| Backend, the same files with the gate's selection | `… pytest -q -m "not red_until" <the 26 files with a red>` | **1 failed, 37 passed, 168 deselected**: `tests/tools/test_bola_inventory.py::test_each_method_on_an_id_route_needs_its_own_entry` (SRE-S3-01) |

### Live checks (stack `racket-sre3smoke`, https://localhost:61300)

| Check | Command | Result |
|---|---|---|
| Stack up | `scripts/ci/evidence.sh up racket-sre3smoke <env>` | rc 0; 9 services healthy (postgres, objectstore, mailpit, tracing, api, worker, mailer, web, web-tls) |
| TLS front door (ADR 0029) | `curl http://localhost:61300/`; `curl --cacert root.crt https://localhost:61300/` | 400; 200 (verified against the stack's own root) |
| API health | `curl http://127.0.0.1:61800/healthz` | 200 `{"status":"ok"}` |
| ST-042 in the running stack (IT-03-10) | `psql -U $WORKER_DB_USER -c 'select count(*) from sessions'` / `accounts` / `jobs` | permission denied; permission denied; `0` (allowed). The worker's `S3_ACCESS_KEY_ID` equals `WORKER_S3_ACCESS_KEY_ID` (1 match) |
| C-13 still holds | `docker compose logs api worker mailer \| grep -ci "failed to export"` | 0 |
| Sprint 2 journey on the Sprint 3 head (G02-01 method, regression) | `scripts/measure/live_tagging.py --runs 1 …` | rc 0, `runs_passed 1/1`, tag→sheet ok, tag server p50 29.1 ms / p95 48.2 ms (n 8) |
| Sprint 3 journey (G03-01..03 method, informative) | `scripts/measure/live_stats.py --runs 1 …` | rc 1, `runs_passed 0/1`: upload ok; every `GET …/stats` 404 after each of 14 rallies; "no metrics in the response"; evidence has no items. Expected until ST-046/ST-047 land (fails closed) |
| Self-cleaning (C-15) | `scripts/ci/evidence.sh down racket-sre3smoke <env>` | rc 0, "removed with its volumes and images"; 0 `racket-sre3smoke` images, 0 volumes; dev Postgres and object store stopped |

### Not covered by this run

- The purge service (SRE-PURGE slice b) is not in Compose yet (`no such service: purge`); the purge job does not exist (ST-050).
- Playwright on this stack: the Sprint 3 specs target screens that do not exist yet (ST-047/048 UI); the Sprint 2 specs ran green on CI `main` (run 37606256586, E2E job success).
- Locust on stats/evidence (ST-054 SRE half): no routes.
