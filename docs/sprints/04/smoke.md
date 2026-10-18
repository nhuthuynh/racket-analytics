# Sprint 4 integration smoke of `main` (SMOKE-04)

Run 2026-10-18 by the sre-devops-engineer with the senior-qa-engineer, after the Sprint 4 merges up to PR #131.

- **Tree:** `origin/main` at `09d279d` (Merge PR #131, ST-069), clean detached worktree `git -C /home/user/racket-analytics worktree add --detach /home/user/wt/smoke-04 origin/main`.
- **CI on that SHA:** CI run 39127874056 (push, `main`, `09d279d`) `conclusion: success`. The previous push runs on `main` (#130 `34752f2`, #127 `3908d72`, #124 `a10982c`, #123 `c4572b7`, #126 `58f79a9`) and the nightly schedule run 39109902498 are also `success`; the push run for #125 (`e708b81`) was `cancelled` (superseded by the next merge, not a failure).
- **Isolation:** own Compose project `smoke04` (`docker compose -p smoke04 -f infra/compose.yaml`), default ports, images through `DOCKERHUB_REGISTRY=mirror.gcr.io`, `EXTRA_CA_FILE=/root/.ccr/ca-bundle.crt` for the build (sandbox proxy CA, BuildKit secret only). `infra/.env` from `infra/env.example` plus `AUTH_LINK_LIMIT_PER_IP=1000` and `AUTH_EXCHANGE_LIMIT_PER_IP=1000`, the same values CI's E2E job sets.
- **Docker daemon proxy:** `docker info | grep -i "https proxy"` equals `$HTTPS_PROXY` (no dockerd restart needed).

## Verdict

**`main` is green on the local stack.** Every suite passed once three environment faults of this sandbox were removed (each re-run below). No product defect found. Two gaps: the Sprint 4 Playwright journeys (E2E-04-01..05, ST-065) are not on `main` yet, so the Sprint 4 goal journey is not covered by this smoke; and the disk was under the 10 GB floor for part of the run (see Disk).

## Stack

| Check | Command | Result |
|---|---|---|
| Build and start from clean state | `EXTRA_CA_FILE=/root/.ccr/ca-bundle.crt docker compose -p smoke04 -f infra/compose.yaml up -d --build --wait` | rc 0 in 2 m 47 s; postgres, objectstore, mailpit, tracing, api, worker, mailer, purge, web, web-tls healthy; db-roles, migrate, objectstore-init exited 0 |
| Clean state again before the journeys | `docker compose -p smoke04 … down -v` then `up -d --wait` | rc 0; fresh volumes |
| HTTPS front door (ADR 0029) | `curl --cacert <stack root.crt> https://localhost:3000/` | 200 |
| API health | `curl http://localhost:8000/healthz` | 200 |
| Tear-down | `docker compose -p smoke04 … down -v --rmi local` | rc 0; 0 `smoke04` images left |

## Suites

| Suite | Command | Result |
|---|---|---|
| Backend: unit, integration, scenario, regression (CI selection) | `cd backend && pytest -q -n 4 -p no:cacheprovider -m "(unit or integration or scenario or regression) and not nightly and not red_until" --ignore=…worker_sandbox*.py --ignore-glob='tests/integration/harness/test_ci_objstore_*.py'`, env = only the variables CI's "Export service endpoints" step sets | **3677 passed, 1 skipped, 5 errors** in 359 s. The 5 errors are the wheel-build fixture (`uv build`: `invalid peer certificate: UnknownIssuer` for pypi), because this run's `env -i` dropped the sandbox proxy CA variables. Re-run with them: `pytest -q tests/integration/test_st_043_metric_dictionary_packaged.py tests/integration/test_gs_an_1_v2_shipped_statuses_packaged.py` → **7 passed** |
| Worker sandbox IT-00-10 against the running worker | `COMPOSE_PROJECT_NAME=smoke04 COMPOSE_ENV_FILES=infra/.env pytest -q tests/integration/test_it_00_10_worker_sandbox.py tests/integration/test_it_00_10_worker_sandbox_strict.py` | **12 passed** |
| Web lint, types | `pnpm exec eslint --max-warnings=0 .`; `pnpm exec tsc --noEmit` | rc 0; rc 0 |
| Web unit | `pnpm exec vitest run` | **88 files, 773 passed** |
| Infra, hooks, CI scripts | `cd infra && pytest -q -p no:cacheprovider -m "unit or integration"` | **1601 passed, 8 skipped, 4 failed** in 612 s. The 4 (`test_compose_extra_ca.py` ×2, `test_compose_extra_ca_scenarios.py` ×2) pulled `docker.io/library/busybox:1.36` and got `429 Too Many Requests` (Docker Hub rate limit). Re-run through the mirror: `DOCKERHUB_REGISTRY=mirror.gcr.io pytest -q tests/test_compose_extra_ca.py tests/test_compose_extra_ca_scenarios.py` → **13 passed** |
| Playwright journeys, gated set (Chromium) | `CI=1 PW_PROJECTS=chromium BASE_URL=https://localhost:3000 E2E_ADMIN_CMD="docker compose -p smoke04 … exec -T api python -m racket.dataset.admin" pnpm exec playwright test --project=chromium --grep-invert "@red-until-" --global-timeout=1800000` | **133 passed, 6 skipped**, 0 failed, 0 flaky, in 11.8 min (1 worker). The 6 skips are the specs' own conditional skips (expired upload, other user's upload, 16-minute link, 12 GB file, declared size above the cap, wrong participants) |
| `make demo` on the running stack (MVP-03, ST-064) | `RA_DEMO_BASE_URL=https://localhost:3000 RA_DEMO_CACERT=<root.crt> RA_DEMO_COMPOSE="docker compose -p smoke04 …" pytest -q -rA tests/test_demo_seed_scenarios.py tests/test_demo_seed_live.py` | **6 passed** (fresh stack shows stats, re-run reuses the match, refuses a stack without dev sign-in) |

WebKit is not installed in this sandbox (`/opt/pw-browsers` has Chromium only), so the WebKit matrix leg is covered only by CI's E2E job (green on `09d279d`).

## Environment faults (not product findings)

1. **Harness env leak (this run's own mistake).** The first backend run exported all of `infra/env.example` with `set -a` (CI exports only the service endpoints). Result: 352 failed, 240 errors, nearly all `HEAD failed: 404` on `/api/uploads/<id>`. The same files with CI's variables only: 15 passed. The run was discarded and repeated (row above). Observation for the senior-qa-engineer: the backend suite is not hermetic against the dev-stack variables in `infra/env.example`, so a developer who sources that file gets a wall of red.
2. **Proxy CA variables dropped** by `env -i` (wheel-build errors above).
3. **Docker Hub 429** for `docker.io/library/busybox:1.36` in the infra extra-CA tests (re-run via `mirror.gcr.io`).

## Disk

| Moment | `df -h /` (Avail) |
|---|---|
| Start, `bash scripts/disk-precheck.sh` | 11G (`ok, 10 GB free`) |
| After `up --build` | 7.4G |
| After the backend and infra suites | 5.9G |
| Before the journeys, after `down -v` and `up -d` | 7.2G (`disk-precheck` rc 3) |
| After the prune of docs/ops/disk-and-prune.md steps 2-4 (`docker builder prune -af` reclaimed 2.556 GB; image and volume prune 0 B) | 9.1G (`disk-precheck` rc 3) |
| End of the journeys | 8.6G |
| After `down -v --rmi local` | 11G |

The journeys ran 0.9 GB under the floor; they passed, so the floor did not produce a false red, but by working-agreement 1a that leg should be repeated above the floor if it is used as goal evidence. What holds the space: a stale `racket-analytics` Compose project (containers worker, purge, mailer from `/home/user/wt/mvp-final`, a directory that is no longer a registered worktree) with its images and 810 MB of volumes, and other lanes' images (`racket-mvp02-*`, `mvp03-*`, `st051-*`, `qa048r1-*`, about 4 GB each set). Not removed here (not this run's).

## Not covered

- Sprint 4 goal journey E2E-04-01..05 (`web/e2e/sprint-04/journey-v3.spec.ts`, ST-065) and the flags-on project E2E-04-06..08: not on `main` (`grep -rlE "ST-06[0-9]|E2E-04" web/e2e` → no file).
- Live goal measurements of `docs/sprints/04/goal-scorecard.md`: not part of this smoke.
- Locust baseline and nightly-only suites.
