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

## Pre-review smoke, 2026-10-07 (sre-devops-engineer with senior-qa-engineer)

- **Tree:** `sprint-03` at `316a514` as a clean detached worktree (`git worktree add --detach <scratch>/smoke3b-wt 316a514`). The SRE commit `4d8af6d` (ST-053 `drill-lint` job), made during the run, was checked separately in the shared tree (last row of Suites).
- **Disk:** `df -h /` → `252G 23G 16G 59%` at the start (16.10 GB free by `df -Pk`), `16G` at the end. The stale local data from earlier rounds (`.local/<round>` dirs, about 1.3 GB; 4.6 GB of Docker build cache older than a day) was **not** removed: the cleanup command was refused by the session's permission policy, so it is left for the human or the next SRE turn with that permission (blockers.md row of today). The two Postgres and object-store pairs running at the time belonged to other lanes (`.local/postgres.state`, `.local/qa03`) and were left alone.
- **Why no Compose build:** `scripts/ci/evidence.sh up` requires `RA_UP_MIN_FREE_GB` 16 GB before a build (about 6 GB). At 15.5 GB free when the stack was due, the build would have been refused (rc 3) or pushed the host under the 10 GB run floor for the other lanes. So the run used the task's second option: **the Compose topology from local processes behind the committed TLS proxy**, with no image build (next bullet). The floor was not lowered.
- **Stack under test (project `racket-sre3pre`, `<scratch>/smoke3b-stack.sh up|down`):** its own `RA_DEV_STATE` with a fresh `scripts/dev-postgres.sh` and `scripts/dev-objectstore.sh`; `python -m racket.platform.migrate` (`migrate: database is at head`); the Compose `db-roles` SQL run as-is (worker login `racket_worker` in `racket_media_worker`, password from `\getenv`); `api` (uvicorn, 127.0.0.1:62800), `worker` (`WORKER_STAGES=probe`, `DATABASE_URL` user `racket_worker`), `mailer` (`WORKER_STAGES=send_sign_in_link`), `web` (`pnpm build` + `pnpm start`, 127.0.0.1:62301); containers from images already on disk on the host network: `mailpit:v1.27` (UI 62025, SMTP 62026), `jaeger:2.10.0` (OTLP 4318), and `caddy:2.10.2-alpine` with the **committed `infra/tls/Caddyfile`**, only its upstreams rewritten by `sed` (`https://localhost:62300`, `web:3000` → `127.0.0.1:62301`, `objectstore:8333` → the dev store, health `:62380`). App env as in `infra/compose.yaml` (`APP_ENV=dev`, `TRUSTED_PROXY_HOPS=1`, `PUBLIC_WEB_ORIGIN=ALLOWED_ORIGINS=S3_PUBLIC_ENDPOINT_URL=https://localhost:62300`, `API_PUBLIC_PATH_PREFIX=/api`, sign-in limits 1000). **What it does not cover** compared with Compose: container hardening (read-only, cap_drop, `sandbox` network) and the worker's own S3 key (the dev store has one key). Both are covered by `infra/tests/test_compose_*.py` and IT-03-10, and were green at the baseline on the Compose stack.

### Verdict

**Platform green; the Sprint 0-2 journeys work on the Sprint 3 head over HTTPS; the Sprint 3 goal journey still fails closed because its stories are not built. One new gate red, SRE-S3-02, routed to QA by a TCR row.** Every other red is a `red_until` row or a red-first Sprint 3 E2E spec that waits on COACH-1, ST-046/047/048/050/051/052 or QA-R1S3-01. **The goal is not demonstrated:** G03-01..03 cannot pass before ST-046/047/050/051 land.

### Suites

| Suite | Command | Result |
|---|---|---|
| Web types, lint | `pnpm exec tsc --noEmit`; `pnpm exec eslint --max-warnings=0 .` | rc 0; rc 0 |
| Web unit | `pnpm exec vitest run` | **59 files, 477 passed** |
| Infra | `cd infra && DOCKERHUB_REGISTRY=mirror.gcr.io uv run pytest -q -p no:cacheprovider -rfE` | **1 failed, 582 passed, 1 skipped** (gitleaks binary not set) in 118 s. The red is **SRE-S3-02**: `test_goal_scorecard_fast_tests.py::test_the_domain_run_uses_the_ci_domain_paths_in_order` compares the Sprint 2 G02-12 command with CI's `DOMAIN_TEST_PATHS`, which has `tests/unit/analytics` since `c7a6443`. New since the baseline (`ecee023`: 581 passed). TCR row 2026-10-07 for QA |
| Backend, full, own Postgres and object store | `env -u APP_ENV uv run pytest -q -p no:cacheprovider tests --ignore=tests/integration/test_it_00_10_worker_sandbox.py -rfE --junitxml=…` | **96 failed, 50 errors, 2326 passed, 22 skipped** in 402 s (baseline 112 failed, 50 errors, 2218 passed: 16 fewer reds; ST-053 slice (d) and its marker removal `f493c02` landed in between). The 146 are in 23 files: IT-03-01..09, 11..13; the Sprint 3 features (starter stats, uncertainty, evidence, dictionary, Full Tag, match and account deletion); GS-AN-1 `golden_an` 3; Sprint 2 `red_until` rows (SOS 18, phone fixtures 2, nightly 1); IT-03-12 50 errors (`red_until`, QA-FUZZ-3) |
| Backend, the gate's selection on those 23 files | `… pytest -q -p no:cacheprovider -m "not red_until" <the 23 files>` | **33 passed, 153 deselected, 0 failed**: every backend red is a `red_until` row. SRE-S3-01 re-checked: all 5 `tests/tools/test_bola_inventory.py` tests pass in the full run |
| Drill lint CLI (ST-053) | `cd backend && uv run --no-sync racket-drill-lint ../content/drills` | `ok, 0 problem(s), metric dictionary v0.1`, rc 0 |
| `drill-lint` CI job (`4d8af6d`, shared tree) | `cd infra && uv run pytest -q tests/test_workflows_sprint03.py` red first (`3 failed, 2 passed`), then whole infra suite; `actionlint .github/workflows/ci.yml` | `1 failed, 585 passed, 1 skipped` (the one red is SRE-S3-02); actionlint rc 0 |

### Live checks (stack `racket-sre3pre`, https://localhost:62300)

| Check | Command | Result |
|---|---|---|
| Stack up | `bash <scratch>/smoke3b-stack.sh up` | rc 0 in 71 s; api, worker, mailer, web processes running; caddy, mailpit, tracing containers up |
| TLS front door (ADR 0029) | `curl http://localhost:62300/`; `curl --cacert root.crt https://localhost:62300/` (root copied from the caddy data volume) | 400; 200 |
| API health, direct and through TLS | `curl http://127.0.0.1:62800/healthz`; `curl --cacert root.crt https://localhost:62300/api/healthz` | 200 `{"status":"ok"}`; 200 |
| ST-042 in the running stack | `PGPASSWORD=$WORKER_DB_PASSWORD psql -U racket_worker -c 'select count(*) from sessions'` / `accounts` / `jobs`; the worker process's `DATABASE_URL` user | permission denied; permission denied; `8` (allowed); `racket_worker` |
| C-13 | `grep -ci "failed to export"` over the api, worker and mailer logs | 0 (and 0 `Traceback` / error-level lines) |
| Sprint 2 journey on the Sprint 3 head (G02-01 method) | `python3 scripts/measure/live_tagging.py --api https://localhost:62300/api --origin https://localhost:62300 --mailpit http://127.0.0.1:62025 --cacert root.crt --file fixtures/clips/synthetic-60s/clip.mp4 --runs 1 --json …` | rc 0, `runs_passed 1/1`; tag→sheet p95 14.0 ms (n 6); tag server p50 20.9 ms / p95 23.2 ms (n 8). Sign-in by mail link, tus upload, the `racket_worker` probe stage and tagging all ran end to end over https |
| Sprint 3 journey (G03-01..03 method, informative) | `python3 scripts/measure/live_stats.py … --runs 1 --psql "psql … -U racket -d racket -At -F\|" --purge-cmd "… uv run --no-sync python -m racket.platform.purge --once" --json …` | rc 1, `runs_passed 0/1`, fails closed as designed. `setup` ok (sign-in + upload), `other_account` ok; `tag_to_stats`: `GET …/stats` 404 after each rally; `stats`: "no metrics in the response"; `evidence`: no items; `correction` 404; `delete_match` 405; `delete_account` 405; purge rc 1 (no `racket.platform.purge`), rows left. Waits on ST-046, ST-047, ST-050, ST-051 and COACH-1 |
| Playwright, every spec, Chromium (Chrome for Testing 141.0.7390.54, ADR 0036) | `PW_CHROMIUM_CHANNEL=chrome MAILPIT_API_URL=http://127.0.0.1:62025 PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers BASE_URL=https://localhost:62300 PW_PROJECTS=chromium … bash scripts/ci/evidence.sh e2e <run> --workers=1 --reporter=line,junit,json` | rc 1 in 10.2 min: **97 passed, 12 failed, 6 skipped, 0 flaky** of 115. **Sprint 0-2: every spec passed** (walking skeleton, security headers, BOLA, Sprint 1, E2E-02-*). The 6 skips are the Sprint 1 rows, each naming its API binding. **Sprint 3:** passed E2E-03-07 (move offer), focus after decision, PD-R3S2-01/02. Failed, all red-first: E2E-03-01, 02, 03, 06 (keyboard, 320/360) and both timing tests stop at "no coach-reviewed metric (COACH-1)"; E2E-03-04 times out (no account deletion UI or route, ST-051); E2E-03-05 "E2E_ADMIN_CMD is not set" (no labeller-admin CLI, ST-052 (b)); E2E-03-06 not-found at 320/360: `a "Go to your matches" 178x21` (**QA-R1S3-01**, FE, already Open) |
| Self-cleaning (C-15) | `bash <scratch>/smoke3b-stack.sh down` | rc 0; 0 `racket-sre3pre` containers, 0 volumes, 0 processes; dev Postgres and object store stopped and their temp dirs removed; `df -h /` 16 GB free |

### Not covered by this run

- WebKit (CI only). Locust on stats and evidence (no routes; ST-054 SRE half). The purge service and a live `--once` (SRE-PURGE (b)/(c); ST-050).
- Container hardening on the live stack (no Compose build this run, see Disk); green at the baseline on Compose.

## Review-round-2 smoke on the round-1 fix head, 2026-10-07 (sre-devops-engineer; QA-R2S3-04)

- **Why:** ADR 0022 smoke before review. The last smoke was at `316a514`. 33 commits followed (`git log --oneline 316a514..8e25478 | wc -l`), among them migration `0013_media_worker_column_grants`, the analytics changes `fee4fa3` (`starter_stats.py`, `sheet.py`, `metrics.json`), GS-AN-1 v2 (`7a6ffe5`), the new red-first E2E-03-08 (`47c34e8`) and the CI change `606edcd` (ADR 0046).
- **Tree:** `sprint-03` at `8e25478` as a clean, **locked** detached worktree (`git worktree add --detach <scratch>/sre-smoke-r2 8e25478; git worktree lock …`). A first attempt at `606edcd` was lost mid-run because another lane's cleanup removed every worktree of the shared repository (blockers.md row of today). The commits after `8e25478` (`9726add`, …) change `docs/` only (`git diff --name-only 8e25478 HEAD | grep -v '^docs/'` → nothing at the time of writing).
- **Disk:** `df -Pk /` → 15.87 GB free when the stack was due and 16 GB (`df -h`) at the end. That is under the 16 GB Compose build floor (`RA_UP_MIN_FREE_GB`), so the floor was kept and there was **no image build**. The run used the same topology as the pre-review smoke: the Compose services as local processes behind the **committed `infra/tls/Caddyfile`** (only its upstreams rewritten), with Postgres and the object store from `scripts/dev-*.sh` and mailpit, jaeger and caddy from images already on disk (`<scratch>/sre-smoke-r2-stack.sh up|down`, project `racket-sre3r2`, https://localhost:63300). It does not cover container hardening (read-only, cap_drop, the `sandbox` network). That is covered by `infra/tests/test_compose_*.py` (green below) and was green on Compose at the baseline.

### Verdict

**Platform green on the fix head. The gate's backend selection is green, and the Sprint 0-2 journeys work over HTTPS, migration 0013 included. Every red is a `red_until` row or a red-first Sprint 3 E2E spec. No new gate red.** The CI integration job's red (QA-R2S3-01, run 37643676432) no longer reproduces: 0 failed. **The Sprint 3 goal is still not demonstrated:** G03-01..03 fail closed (no stats, evidence, delete or purge routes) until ST-046/047/050/051 land (QA-R1S3-06).

### Suites

| Suite | Command | Result |
|---|---|---|
| Web types, lint | `pnpm exec tsc --noEmit`; `pnpm exec eslint --max-warnings=0 .` | rc 0; rc 0 |
| Web unit | `pnpm exec vitest run` | **59 files, 477 passed** |
| Infra | `cd infra && DOCKERHUB_REGISTRY=mirror.gcr.io uv run --no-sync pytest -q -p no:cacheprovider -rfE` | **610 passed, 1 skipped** in 113 s (gitleaks binary not set). Pre-review: 1 failed (SRE-S3-02, fixed since) |
| Workflow lint | `actionlint .github/workflows/ci.yml` | rc 0 |
| Backend, **CI integration-job selection**, own Postgres and object store | `env -u APP_ENV uv run --no-sync pytest -q -p no:cacheprovider -m "(unit or integration or scenario or regression) and not nightly and not red_until" --ignore=…worker_sandbox.py --ignore=…worker_sandbox_strict.py` | **2351 passed, 19 skipped, 157 deselected, 0 failed** in 274 s. At `09f1f67` (ci-status.md) it was 2 failed (GS-AN-1 AN-07 `low_sample`, QA-R2S3-01) |
| Backend `red_until` rows (listed, not gated) | `… pytest -q -p no:cacheprovider -m "red_until and not nightly" --junitxml=…`; `python3 ../scripts/ci/red_until_report.py --junit … --root .` | pytest `106 failed, 50 errors` (expected). Report rc 0, **"No stale markers."** Per story (failed / error): ST-024 1, ST-025 2, ST-035 18, ST-038 3, ST-046 25, ST-047 21, ST-050 14 / 50, ST-051 4, ST-052 18. COACH-1 has no rows left (QA-R2S3-02 gated it) |

### Live checks (stack `racket-sre3r2`, https://localhost:63300)

| Check | Command | Result |
|---|---|---|
| Stack up | `bash <scratch>/sre-smoke-r2-stack.sh up` | rc 0 in 52 s; `migrate: database is at head`; `select version_num from alembic_version` → `0013` |
| TLS front door (ADR 0029) | `curl http://localhost:63300/`; `curl --cacert root.crt https://localhost:63300/` | 400; 200 |
| API health, direct and through TLS | `curl http://127.0.0.1:63800/healthz`; `curl --cacert root.crt https://localhost:63300/api/healthz` | 200 `{"status":"ok"}`; 200 |
| ST-042 in the running stack | `psql -U racket_worker -c 'select count(*) from sessions'` / `accounts` / `jobs`; `/proc/<pid>/environ` of the workers | permission denied; permission denied; `0` (allowed). Probe worker: `DATABASE_URL` user `racket_worker`, `WORKER_STAGES=probe`. Mailer: `racket`, `send_sign_in_link` |
| **Migration 0013 (column grants), live** | as `racket_worker`: `update matches set owner_id = owner_id where false`; `update media_assets set object_key = object_key where false`; `update matches set status = status where false`; `update media_assets set probe_status = probe_status where false` | permission denied; permission denied; `UPDATE 0`; `UPDATE 0`. **The probe stage still works under the narrowed grants:** worker log `job.claimed` 2, `probe.done` 2, `job.done` 2, 0 `permission denied`; both matches `video_received` with `probe_status = probed` |
| C-13 | `grep -ciE 'permission denied\|Traceback\|"level": *"error"'` and `grep -ci 'failed to export'` over the api, worker and mailer logs | 0 and 0 in each |
| Sprint 2 journey on the fix head (G02-01 method) | `python3 scripts/measure/live_tagging.py --api https://localhost:63300/api --origin https://localhost:63300 --mailpit http://127.0.0.1:63025 --cacert root.crt --file fixtures/clips/synthetic-60s/clip.mp4 --runs 1 --json …` | rc 0, `runs_passed 1/1`; tag→sheet p50 12.0 ms / p95 13.0 ms (n 6, target ≤ 5,000 ms); tag server p50 17.6 ms / p95 24.5 ms (n 8). Mail-link sign-in, tus upload, probe as `racket_worker` and tagging all ran end to end over https |
| Sprint 3 journey (G03-01..03 method, informative) | `python3 scripts/measure/live_stats.py … --runs 1 --psql "psql -h 127.0.0.1 -p <pg> -U racket -d racket -At -F\|" --purge-cmd "uv run --no-sync --project <wt>/backend python -m racket.platform.purge --once" --json …` | rc 1, `runs_passed 0/1`. It fails closed, the same as the pre-review smoke: `setup` ok, `other_account` ok (404, 404); `tag_to_stats` 404 after each of the 14 rallies; `stats` "no metrics in the response"; `evidence` "no items list" for each metric and side; `correction` 404; `delete_match` 405; `delete_account` 405; purge rc 1 (`No module named racket.platform.purge`), so all rows are left; G03-02 n = 0 for (a), (b) and (c). It waits on ST-046, ST-047, ST-050 and ST-051 |
| Playwright, every spec, Chromium (Chrome for Testing, ADR 0036) | `PW_CHROMIUM_CHANNEL=chrome MAILPIT_API_URL=http://127.0.0.1:63025 PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers BASE_URL=https://localhost:63300 PW_PROJECTS=chromium PLAYWRIGHT_JSON_OUTPUT_NAME=… bash scripts/ci/evidence.sh e2e <run> --workers=1 --reporter=line,junit,json` | rc 1 in 14.7 min: **97 passed, 16 failed, 6 skipped, 0 flaky** of 119. **Sprint 0-2: 0 failures** (counted from the JSON report: failures outside `sprint-03/` = 0). The 6 skips are the Sprint 1 rows, each naming its API binding. **Sprint 3, all red-first:** E2E-03-01, -02 (timeout), -03, -06 keyboard/320/360 and both timing tests stop where there is no stats page or coach-reviewed metric. E2E-03-04 times out (no account deletion, ST-051). E2E-03-05: "E2E_ADMIN_CMD is not set" (ST-052). E2E-03-06 not-found at 320/360: targets below 24x24 (**QA-R1S3-01**, still Open). **New since the pre-review smoke:** E2E-03-08 `states.spec.ts` (4, red-first from `47c34e8`, ST-048). Once QA tags these 16 with `@red-until-<id>` (TCR row of today, ADR 0046), the gated selection is the 97 passed + 6 skipped |
| Self-cleaning (C-15) | `bash <scratch>/sre-smoke-r2-stack.sh down` | rc 0; 0 `racket-sre3r2` containers, 0 volumes, 0 stack processes; the dev Postgres and object store were stopped; `df -h /` 16 GB free |

### Not covered by this run

- WebKit (CI only). Container hardening on the live stack (no Compose build: disk under the floor). Locust on stats and evidence (no routes yet). The purge service and a live `--once` (ST-050).
