# Sprint 2 integration smoke (ADR 0022, ADR 0033 rule 3; SRE-SMOKE)

- **Date:** 2026-10-06
- **Run by:** sre-devops-engineer
- **Tree:** `sprint-02` at `bddd3c7`, as a clean detached worktree (`git worktree add --detach … HEAD`), so no lane's uncommitted file is in the run. `git diff --stat ffce41d bddd3c7 -- . ':(exclude)docs'` is empty: the CI head `ffce41d` has the same code.
- **Isolation:** own `RA_DEV_STATE=.local/sre02-smoke` Postgres and object store, own Mailpit container `sre02-smoke-mailpit` (ports 59025/51125); the Compose part ran on a fresh GitHub runner (fresh volumes by construction).
- **Disk:** `df -h /` 15G free at the start, 13G at the end (other agents' stacks running). See "Not run locally".

## Verdict

**Ready for review round 1 for the platform; not ready overall.** Every platform gate is green, and the live checks of the SRE stories hold. The remaining reds all have an owner outside the platform and an Open row in `review-rounds.md`: the 21 `red_until` rows (stretch ST-035 and PO-blocked ST-024/ST-025), five stale `red_until` markers (SRE-S2-04), H.264 in CI Chromium (SRE-S2-05), five Sprint 2 specs that fail in WebKit only (SRE-S2-07), and two Chromium-only timing tests that run in WebKit (SRE-S2-08).

## Suites

| Suite | Where | Command | Result |
|---|---|---|---|
| Infra (incl. hooks, CI scripts, evidence wrapper, perf verdict, red-until report) | worktree | `cd infra && uv run pytest -q -p no:cacheprovider` | **454 passed** in 69.3 s |
| Web types, lint | worktree | `pnpm exec tsc --noEmit`; `pnpm exec eslint --max-warnings=0 .` (with `pipefail`) | rc 0, rc 0 |
| Web unit | worktree | `pnpm exec vitest run --coverage` | **51 files, 406 passed**; lines 91.02% |
| Backend, full | worktree, own Postgres/object store/Mailpit, no ambient service variables | `env -u APP_ENV uv run pytest -q tests --ignore=…worker_sandbox*.py` | **21 failed, 1876 passed, 1 skipped** in 395 s; the 21 are exactly the `red_until` rows: ST-035 SOS-01..18 (18), ST-025 phone fixtures (2), ST-024 nightly (1) |
| Fresh Compose stack, `up --wait` | CI run 37438997898 (`ffce41d`) | E2E job "Start the full stack" | success (1m43s); worker sandbox IT-00-10 against the running worker: success |
| Playwright, Chromium + WebKit, https | same | `pnpm exec playwright test` | **161 passed, 9 failed, 12 skipped** (14.0 min); failures in `ci-status.md` (SRE-S2-05, -07, -08) |
| Backend gate selection on Compose services | same | integration job | success (`not red_until`); the red-until step fails on SRE-S2-04 as designed |
| Locust baseline, 50 RPS | same | `perf-baseline` job | success: 0 failures, correction p95 410 ms, restored byte-identical |

## Live checks of the platform stories (own stack `racket-sre02`, https://localhost:53000)

Stack built from the tree at `7bb971f` plus the then-uncommitted SRE-MEDIA change (`03ab524`), with `scripts/ci/evidence.sh up` (rc 0, 17 → 12 GB free).

| Story | Check | Result |
|---|---|---|
| TLS front door | `curl http://localhost:53000/`; `curl --cacert root.crt https://localhost:53000/` | 400; 200 |
| C-18 | POST with `Origin: https://evil.example` through the web; same on the API port; POST with the web origin | 403; 403; passes the check (404 route) |
| SRE-MEDIA | `live_tagging.py --runs 1` step `media_link`; unsigned, listing, PUT, DELETE on the bucket path; cross-origin GET | ok (206, tampered 403, TTL 300 s); 403 each; 206 with no `Access-Control-*`, no `Server` (docs/ops/media-serving.md) |
| C-13 | api, worker, mailer logs > 60 s after the change | 0 export errors; traces still in Jaeger |
| ST-039 | Locust run + `perf_verdict.py` | verdict ok (numbers in decision-log; host contended, so reads not a baseline) |
| G02-01 (one run, informative) | `live_tagging.py --runs 1` | 10 of 13 steps; the 3 failing steps are BE-D1-01 (harness `_code()`, owner EM), not platform |
| C-15 | `scripts/ci/evidence.sh down racket-sre02 …` | rc 0, "removed with its volumes and images", 0 `racket-sre02` images and 0 volumes left |

## Not run locally (disk)

A local fresh-volume Compose run of the smoke tree needs 16 GB free before `up --build` (`docs/ops/evidence-runs.md`); this host had 13-15 GB, held by other agents' running stacks and object stores, which the SRE does not remove (`disk-and-prune.md`). The SRE pruned its own state and the build cache (3.2 GB). The Compose part of this smoke therefore comes from CI run 37438997898 at the same code, a fresh runner with fresh volumes. To re-run locally once 16 GB are free: `bash scripts/ci/evidence.sh up racket-smoke02 <env>` from the worktree, Playwright with `evidence.sh e2e`, then `evidence.sh down`.

## Smoke 2 at `aeed281`: local fresh-volume Compose over HTTPS (SRE-SMOKE, 2026-10-06)

- **Run by:** sre-devops-engineer with senior-qa-engineer. **Tree:** `sprint-02` at `aeed281`, a clean detached worktree (`git worktree add --detach .local/smoke-s2b/tree HEAD`); removed after the run.
- **Disk first (disk-and-prune.md):** `bash scripts/disk-precheck.sh` → `18 GB free (floor 10 GB)`. Stale local test data deleted (git-ignored only, no running agent uses it): `reports/goal-qar3/pw-out*` (1.2 GB, Sprint 1 round 3 traces), `web/test-results` (809 MB); `docker builder prune -af`, `docker image prune -f`. Then `20 GB free`. The default dev Postgres/object store (`/tmp/racket-pg.4CNhZ6`, `/tmp/racket-s3.m6I9Oj`, 2 GB) was left alone: it is running and may belong to another agent.
- **Isolation:** Compose project `racket-smoke2b` (fresh volumes), host ports 43000/48000/48025/41025/45432/48333/46686; backend suite on its own `RA_DEV_STATE=.local/smoke-s2b/svc` Postgres + object store and its own Mailpit container (`smoke2b-mailpit`, 49025/49125). The local Compose run that smoke 1 could not do (disk) ran this time.

### Verdict

**The live stack works over HTTPS and the Sprint 2 journey works on it; the run is not fully green.** Platform: TLS, origin check, media through the origin, all services healthy, teardown clean. Every red has an owner and is already routed, except one new flaky test (SRE-S2-09 below).

### Stack

| Check | Command | Result |
|---|---|---|
| Up | `RA_EVIDENCE_COMPOSE_EXTRA=.local/smoke-s2b/ca-override.yaml bash scripts/ci/evidence.sh up racket-smoke2b .local/smoke-s2b/smoke.env` (env = `infra/env.example`, `mirror.gcr.io`, origin `https://localhost:43000`, ports above) | rc 0; 9 services healthy (api, worker, mailer, web, web-tls, postgres, objectstore, mailpit, tracing); `df` 21G → 16G free |
| TLS | `curl http://localhost:43000/`; `curl --cacert root.crt https://localhost:43000/` | 400; 200 |
| Origin check (C-18) | `curl --cacert root.crt -X POST -H 'Origin: https://evil.example' https://localhost:43000/api/auth/magic-link` | 403 |
| Media through the origin (SRE-MEDIA) | scratch probe (`.local/smoke-s2b/ct_probe.py`): sign in, upload the 60 s fixture, `GET /matches/{id}/video`, ranged GET of the presigned URL | URL on `https://localhost:43000/racket-media/originals/…`; 206, **`Content-Type: application/octet-stream`** (QA-S2-UI-03 still open, BE) |
| C-13 | `docker compose … logs --since 30m api worker mailer \| grep -ciE 'Failed to export\|export.*(error\|fail)'` | 0 |
| Down (C-15) | `bash scripts/ci/evidence.sh down racket-smoke2b …` | rc 0, "removed with its volumes and images"; 0 `smoke2b` volumes, 0 images; own Postgres/object store stopped, Mailpit removed; `df` 18G free at the end |

### Suites

| Suite | Command | Result |
|---|---|---|
| Infra | `cd infra && uv run pytest -q -p no:cacheprovider` | **454 passed** (72.0 s) |
| Web types, lint | `pnpm exec tsc --noEmit`; `pnpm exec eslint --max-warnings=0 .` (`pipefail`) | rc 0; rc 0 |
| Web unit | `pnpm exec vitest run --coverage` | **51 files, 406 passed**; lines 91.02% |
| Backend, full (own services) | `env -u APP_ENV uv run pytest -q -p no:cacheprovider -rfE tests --ignore=tests/integration/test_it_00_10_worker_sandbox_strict.py` | **21 failed, 1996 passed, 3 skipped** (353 s); the 21 are exactly the `red_until` rows: ST-035 SOS-01..18 (18), ST-025 phone fixtures (2), ST-024 nightly (1) |
| Worker sandbox, strict, against the running Compose worker | `COMPOSE_PROJECT_NAME=racket-smoke2b COMPOSE_ENV_FILES=…/smoke.env env -u APP_ENV uv run pytest -q tests/integration/test_it_00_10_worker_sandbox_strict.py` | **10 passed** |
| Playwright, all specs, Chromium, https | `MAILPIT_API_URL=http://127.0.0.1:48025 PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers BASE_URL=https://localhost:43000 PW_PROJECTS=chromium … bash scripts/ci/evidence.sh e2e .local/smoke-s2b/reports --workers=1 --reporter=line,junit,json` | rc 1: **82 passed, 3 failed, 6 skipped** (6.6 min). `junit_rate.py --require E2E-02-01..06` → 0 missing. E2E-02-01, -02, -03, -05, -06 and the other Sprint 2 specs pass. Failures: E2E-02-04 and `seek-first-frame (real video link)` = no H.264 in Playwright Chromium (blockers 2026-10-06, SRE-S2-05); `seek-first-frame with the decodable stand-in` = SRE-S2-09. The 6 skips are the Sprint 1 API-bound skips (each names its binding) |
| Re-run of the stand-in seek | `… evidence.sh e2e …/rerun e2e/sprint-02/timing.spec.ts -g "decodable stand-in" --repeat-each=3` | **1 failed, 2 passed**: flaky, `no change seen for seek in 10 s` |
| WebKit | not run locally (CI only, testing-strategy) | see smoke 1 / `ci-status.md` (SRE-S2-07, -08) |

### Goal journeys on the live stack (informative, not the verifier's run)

| Row | Command | Result |
|---|---|---|
| G02-01/02 as written | `python3 scripts/measure/live_tagging.py --api https://localhost:43000/api --origin https://localhost:43000 --mailpit http://127.0.0.1:48025 --cacert root.crt --file fixtures/clips/synthetic-60s/clip.mp4 --runs 5 --corrections 50` | rc 1, **0 of 5 runs**; failing steps only `tag_before_video_refused` (409), `wrong_side_refused` (422), `stale_version_refused` (409), 5 each: the harness `_code()` reads a top-level `code` (BE-D1-01, still open). Corrections n 100, p95 24.6 ms, 0 failures, restored byte-identical; tag_to_sheet p95 17 ms |
| G02-01/02 with the 2-line `_code()` fix in a scratch copy (not committed) | same, `scratch/live_tagging.py` | **rc 0, 5 of 5 runs**; corrections p95 24.1 ms, n 100, byte-identical; tag_to_sheet p95 18 ms |
| G02-04 as written | `python3 scripts/measure/tag_latency.py --api http://127.0.0.1:48000 --origin https://localhost:43000 --mailpit http://127.0.0.1:48025 --rps 50 --duration 60` | rc 1 before any load, `video: {"status": "uploading"}` (SRE-S2-02, still open) |
| G02-04 supporting line through the origin | same with `--api https://localhost:43000/api --cacert root.crt` | rc 0: p50 14.6 ms, **p95 29.3 ms**, p99 70.7 ms, availability 1.0, 0 unexpected, 49.98 RPS (load average 0.9) |

### Reds and owners

| Id | Owner | State |
|---|---|---|
| BE-D1-01 (harness `_code()`) | principal-engineer | Open; blocks G02-01 as written; scratch fix proves 5/5 |
| SRE-S2-02 (`tag_latency.py` seeds on the bare API port) | engineering-manager (harness author) | Open; blocks G02-04 as written |
| SRE-S2-05 / blockers 2026-10-06 (no H.264 in local Chromium; no Chrome in `/opt/pw-browsers`) | senior-qa-engineer (`channel: 'chrome'` on CI), engineering-manager with the PO (accept CI evidence for E2E-02-04 and G02-06 (c)) | Open |
| QA-S2-UI-03 (media `application/octet-stream`) | senior-backend-engineer (content type on the original or `ResponseContentType`), senior-frontend-engineer | Open, re-confirmed above |
| **SRE-S2-09 (new)** `timing.spec.ts` "seek-first-frame with the decodable stand-in" is flaky: 1 of 1 in the full run and 1 of 3 in the re-run fail with `no change seen for seek in 10 s` | senior-qa-engineer (spec), senior-frontend-engineer if V-01 misses a seek | Open |
| 21 `red_until` rows (ST-035 stretch, ST-024/ST-025 PO-blocked) | as in smoke 1 | expected |

## Sprint-close head

To be filled by the SRE at the sprint-close head (C-12 rule; Sprint 1 §7): tree, stack, suites, verdict.
