# Sprint 3 integration smoke of `main` (SMOKE-03)

- **Date:** 2026-10-08
- **Run by:** sre-devops-engineer with senior-qa-engineer.
- **Tree:** `origin/main` at `5f80f0a`, a fresh worktree (`git -C /home/user/racket-analytics worktree add -b s03/smoke-03-integration-smoke-of-main /home/user/wt/smoke-03 origin/main`). `5f80f0a` is the nightly `[skip ci]` commit. `git diff --stat 68df5d7 5f80f0a` shows that only `docs/sprints/02/status.json` changed, so the code is the same as the last CI head on `main`, `68df5d7` (merge of PR #13).
- **What `main` contains:** Sprint 2 (PR #2) plus the Sprint 3 CI and security ticket PRs merged so far: #7 SEC-RV3-02, #9 CI-FLAKE-RESUMABLE (1/2), #11 CI-POLICY-BASE, #12 PE-R1S3-07 and #13 CI-PERF-GATES. **No Sprint 3 product story is on `main` yet.** The plan PR, ST-046/047/050/051/052 and the rest are still on `sprint-03` or in open PRs (#4, #5, #6, #8, #10, #14, #15). This smoke therefore covers the platform and the Sprint 1–2 product as they stand on `main`. It is not a Sprint 3 goal measurement.
- **Isolation:** Compose project `racket-smoke03` with fresh volumes. Host ports: web 33000, api 38000, postgres 35432, object store 38333, Mailpit 38025/31025, tracing 36686. Env file = `infra/env.example` with only those ports changed, plus `DOCKERHUB_REGISTRY=mirror.gcr.io` and, for the second bring-up, the two CI E2E limits (see "Stack"). The build-CA override (`/root/.ccr/ca-bundle.crt` as the `extra_ca` build secret) is local and is not committed. Every run went through `scripts/ci/evidence.sh`, which holds the lock and checks the disk floors.

## Verdict

**`main` at `5f80f0a` is green end to end on a fresh local HTTPS stack.** Infra, web, backend (gate selection), worker sandbox and every Playwright journey in Chrome passed. The only reds are the 21 known `red_until` rows: ST-035 stretch (18), and ST-024 (1) and ST-025 (2), both PO-blocked. Their report is green and finds no stale markers. WebKit and Locust were not run locally (no WebKit build in `/opt/pw-browsers`; Locust is a CI-only gate). Both are green in CI run 37756587805 at the same code.

The first Playwright run was red (68 of 99 tests failed). The cause was this smoke's own local setup, not the product: the per-IP sign-in limit stayed at its default. Details are under "Stack".

## Stack (fresh volumes, HTTPS)

| Check | Command | Result |
|---|---|---|
| Disk first | `scripts/disk-precheck.sh` (inside `evidence.sh up`) | 1st up: 17 GB free before, 12 GB after. 2nd up: 13 GB, below the 16 GB build floor (rc 3). `docker builder prune -af` (4.49 GB) and `docker image prune -f` then left 18 GB. The 2nd up finished with 14 GB free |
| Up #1 | `RA_EVIDENCE_COMPOSE_EXTRA=.local/smoke-03/ca-override.yaml bash scripts/ci/evidence.sh up racket-smoke03 .local/smoke-03/smoke.env` | rc 0 (10:21:04 → 10:23:15 UTC). api, worker, mailer, web, web-tls, postgres, objectstore, mailpit and tracing all healthy. migrate and objectstore-init exited as one-shots |
| TLS front door | `curl http://localhost:33000/`; `curl --cacert root.crt https://localhost:33000/` (`root.crt` copied from `web-tls:/data/caddy/pki/authorities/local/root.crt`, as `ci.yml` does) | 400; 200 |
| Origin check (C-18) | `curl --cacert root.crt -X POST -H 'Origin: https://evil.example' https://localhost:33000/api/auth/links` | 403 |
| Down #1 / Up #2 | `evidence.sh down racket-smoke03 …`, then the two lines `AUTH_LINK_LIMIT_PER_IP=1000` and `AUTH_EXCHANGE_LIMIT_PER_IP=1000` added to the env file (the same values as the `ci.yml` e2e job's "Start the full stack" step), then `evidence.sh up` again | down rc 0 ("removed with its volumes and images"). up rc 0 (10:39:41 → 10:41:42). The api container has `AUTH_LINK_LIMIT_PER_IP=1000`. Up #2 repeated the checks above: http 400, https 200, evil origin 403 |
| Service logs (C-13) | `docker compose -p racket-smoke03 … logs api worker mailer \| grep -ciE 'Failed to export\|export.*(error\|fail)'`; the same with `'"level": "ERROR"'`; api `'"status": 5[0-9][0-9]'` | 0; 0; 0 (after the full Playwright run) |
| Down (C-15) | `bash scripts/ci/evidence.sh down racket-smoke03 .local/smoke-03/smoke.env` | rc 0, "removed with its volumes and images". `docker images \| grep -c smoke03` → 0 and `docker volume ls \| grep -c smoke03` → 0. 16 GB free at the end |

## Suites

| Suite | Command (from the worktree) | Result |
|---|---|---|
| Infra (hooks, CI scripts, evidence wrapper, red-until reports) | `cd infra && DOCKERHUB_REGISTRY=mirror.gcr.io uv run pytest -q -p no:cacheprovider` | **537 passed, 1 skipped** (133.8 s). The skip is `test_gitleaks_ignore.py:104`, "set GITLEAKS_BIN"; CI's secret-scan job runs gitleaks |
| Object store parity IT-00-16 | `cd infra && uv run pytest -q tests/test_object_store_parity.py` (against the stack's store) | **7 passed** |
| Python lint, format, types | `cd backend && uv run ruff check .`; `uv run ruff format --check .`; `uv run mypy` | rc 0; "317 files already formatted"; "Success: no issues found in 94 source files" |
| Web lint, types | `cd web && pnpm install --frozen-lockfile && pnpm exec eslint --max-warnings=0 . && pnpm exec tsc --noEmit` | rc 0; rc 0; rc 0 |
| Web unit | `pnpm exec vitest run --coverage` | **56 files, 463 passed**; lines 91.7%, branches 87.74% |
| Backend, CI gate selection, on the Compose services | `cd backend && uv run --no-sync pytest -q -p no:cacheprovider -n auto -m "(unit or integration or scenario or regression) and not nightly and not red_until" --ignore=…worker_sandbox.py --ignore=…worker_sandbox_strict.py`, with only the variables CI's "Export service endpoints" step sets (`DATABASE_URL`, `S3_*`, `SMTP_*`, `MAIL_SMTP_URL`, `MAILPIT_API_URL`, `APP_ENV=test`) | **2089 passed, 1 skipped**, rc 0 (169 s) |
| Rows waiting on a story | `uv run --no-sync pytest -q -m "red_until and not nightly"`, then `python3 ../scripts/ci/red_until_report.py --junit … --root .` | 21 failed, as expected: ST-024 1, ST-025 2, ST-035 18. Report rc 0, "No stale markers." |
| Worker sandbox IT-00-10 (both files) against the running worker | `COMPOSE_PROJECT_NAME=racket-smoke03 COMPOSE_ENV_FILES=…/smoke.env uv run --no-sync pytest -q tests/integration/test_it_00_10_worker_sandbox.py tests/integration/test_it_00_10_worker_sandbox_strict.py` | **12 passed**, on up #1 and again on up #2 |

## Playwright journeys (every spec under `web/e2e`, https)

Environment: `PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers BASE_URL=https://localhost:33000 MAILPIT_API_URL=http://127.0.0.1:38025 PW_PROJECTS=chromium PW_CHROMIUM_CHANNEL=chrome NODE_EXTRA_CA_CERTS=root.crt`. The `chrome` channel is the local `/opt/google/chrome`, "Google Chrome for Testing 141.0.7390.54". It decodes the H.264 match video, as Google Chrome does on CI (SRE-S2-05).

| Run | Command | Result |
|---|---|---|
| Gate selection, up #2 | `bash scripts/ci/evidence.sh e2e .local/smoke-03/e2e2 --workers=1 --grep-invert "@red-until-" --reporter=line,junit,json` | rc 0: **93 passed, 0 failed, 0 flaky, 6 skipped** (6.9 min). Passes include E2E-02-01..06, E2E-02-04 on the real H.264 video, both seek-first-frame timings, object-level authorisation, security headers and the walking skeleton. The 6 skips are the Sprint 1 API-bound skips: match-setup:61, resumable-upload:141 and :145, sign-in:41, upload-validation:34 and :55 |
| Red-until selection | `… evidence.sh e2e .local/smoke-03/e2e-red2 --workers=1 --grep "@red-until-" --reporter=json`, then `python3 scripts/ci/e2e_red_until_report.py --json …/e2e-red.json --specs web/e2e` | Playwright "No tests found". The report gives rc 0: "0 `@red-until-` tags under `web/e2e` and none selected" |
| Gate selection, up #1 (setup error, kept for the record) | same as the first row, against up #1 | rc 1: 25 passed, **68 failed**, 6 skipped. All 68 fail in `requestLink` waiting for "Check your email". The api log for `/auth/links` shows 69 × 429 `rate_limited` and 20 × 202, with the first 429 at 10:30:25Z. The default `AUTH_LINK_LIMIT_PER_IP` is 20 (`infra/compose.yaml:166`), and every Playwright sign-in comes from one IP. CI raises the limit only in the e2e job's step env (`ci.yml:333-338`), and `docs/ops/evidence-runs.md` does not say so. That gap is finding SMOKE03-01 |
| WebKit | not run locally (`/opt/pw-browsers` has no WebKit) | CI run 37756587805 at `68df5d7`: E2E job (Chromium via Chrome and WebKit) `success` |

## CI at the same code

CI run [37756587805](https://github.com/nhuthuynh/racket-analytics/actions/runs/37756587805) (push to `main`, `68df5d7`): `success` for ci-gate, E2E (Chromium + WebKit) with axe, integration on Compose (incl. red-until step), Locust 50 RPS, infra, web, Python unit, Ruff, mypy, actionlint, fixtures, secret scan and audit, and SBOM/licence. PR policy and the flaky report were `skipped`, which is expected on a push. Nightly quality run 37756684702 at `68df5d7`: `success`.

## Findings

| Id | Owner | Finding | Evidence |
|---|---|---|---|
| SMOKE03-01 | sre-devops-engineer | A local full Playwright run against `evidence.sh up` with `infra/env.example` hits the per-IP sign-in limit: 68 of 99 tests fail. `docs/ops/evidence-runs.md` should tell the reader to set `AUTH_LINK_LIMIT_PER_IP`/`AUTH_EXCHANGE_LIMIT_PER_IP` as `ci.yml` does | "Gate selection, up #1" row above |
| SMOKE03-02 | sre-devops-engineer | Sourcing the whole Compose env file into the backend pytest process (instead of only CI's exported variables) gave `98 failed, 1780 passed, 1 skipped, 211 errors` (254 × `HEAD failed: 404` on tus uploads). With only CI's variables, the same test passes and the full selection is green. Not bisected; the env file sets `API_PUBLIC_PATH_PREFIX=/api`, which the upload `Location` uses (`video_ingest/api.py:129`). The runbook should list the exact variables | first backend run log (`.local/smoke-03`, not committed); `tests/integration/test_it_00_06_tus_upload.py` → 1 passed with the CI list |
| SMOKE03-03 | engineering-manager | `main` has no Sprint 3 plan docs (`docs/sprints/sprint-03.md`, `docs/sprints/03/*` exist only on `sprint-03`). This file is the first `docs/sprints/03/` file on `main`. When the plan PR lands, its `docs/sprints/03/smoke.md` will meet this one as an add/add conflict, to be merged by keeping both texts | `git ls-tree origin/main docs/sprints/03` → this PR only |
| SMOKE03-04 | engineering-manager | No Sprint 3 product story is on `main` yet (open PRs #4, #5, #6, #8, #10, #14, #15), so no Sprint 3 goal can be measured live on `main` at this point | PR list 2026-10-08 |
