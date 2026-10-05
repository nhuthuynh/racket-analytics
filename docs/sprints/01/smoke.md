# Sprint 1 integration smoke (ADR 0022)

- **Date:** 2026-10-05
- **Run by:** sre-devops-engineer with senior-qa-engineer
- **Tree:** `sprint-01` at `6ba9b28` (clean working tree)
- **Scope:** a fresh-volume Compose stack with web-tls (ADR 0029), plus the full backend, web unit, infra and Playwright suites, run before review round 1. This run also re-checks the WebKit cookie fix, as the user asked: "fix the WebKit cookie issue in sprint 1 too".

## Verdict

**Not ready for review.** The stack comes up healthy over https and the cookie fix holds. The infra and web unit suites are green. The backend suite and Playwright are red. Every red test is covered by a test-change row that is still **Pending** in `test-change-requests.md`, or by an existing open blocker. No new product defect was found. One flaky E2E test is new (S-06).

## 1. WebKit cookie issue (ADR 0029): fixed and verified

The fix was already committed: `93993af`, `3fbfc32`, `6358c6d` and `2390e9a` (blockers rows closed in `6ba9b28`). No further code change was needed. Re-verified on the fresh stack:

| Check | Command | Result |
|---|---|---|
| Plain-http entry point is closed | `curl -sS -o /dev/null -w '%{http_code}' http://localhost:3000/` | `400` |
| The TLS chain verifies against the dev root (no `-k`) | `docker compose -p racket-smoke01 … cp web-tls:/data/caddy/pki/authorities/local/root.crt root.crt; curl --cacert root.crt https://localhost:3000/` | `200 ssl_verify=0` |
| The cookie matches production | `curl --cacert root.crt -D - -X POST -H 'content-type: application/json' -d '{"username":"ivy"}' https://localhost:3000/api/dev/sign-in` | `HTTP/2 204`, `set-cookie: __Host-racket_session=…; HttpOnly; Max-Age=43200; Path=/; SameSite=lax; Secure` |
| WebKit sign-in on CI | CI run 37298471332, job E2E 111725272519 (head `2390e9a`) | No WebKit test fails at sign-in. The remaining WebKit-only failures are not about cookies (blockers.md row "E2E job still red after the WebKit cookie fix") |

WebKit cannot run in the sandbox: `/opt/pw-browsers` has only `chromium-1194`, `chromium_headless_shell-1194` and `ffmpeg-1011`, and `playwright install` is not allowed.

## 2. Stack

```
docker compose -p racket-smoke01 -f infra/compose.yaml --env-file <copy of infra/env.example with DOCKERHUB_REGISTRY=mirror.gcr.io, AUTH_LINK_LIMIT_PER_IP=1000, AUTH_EXCHANGE_LIMIT_PER_IP=1000> up -d --build --wait
```

Result: `rc=0` in 1m42s. Healthy: postgres, objectstore, mailpit, tracing, api, worker, mailer, web, web-tls. Exited 0: migrate, objectstore-init. The per-IP limits were raised as in the CI E2E job. The stale pre-ADR-0029 `racket-smoke01` stack (no web-tls) was removed first with `down -v --remove-orphans`, so the volumes are fresh.

## 3. Suites

| Suite | Command | Result |
|---|---|---|
| Web unit | `cd web && pnpm exec vitest run` | **30 files, 244 passed** (14.6 s) |
| Web types and lint | `pnpm exec tsc --noEmit`; `pnpm exec eslint .` | rc=0; no findings |
| Infra | `cd infra && uv run pytest -q` | **239 passed** in 54.9 s |
| Worker sandbox IT-00-10 against the running worker | `cd backend && COMPOSE_PROJECT_NAME=racket-smoke01 COMPOSE_ENV_FILES=<env copy> uv run pytest -q tests/integration/test_it_00_10_worker_sandbox.py tests/integration/test_it_00_10_worker_sandbox_strict.py` | **12 passed** |
| Backend (full) | `eval "$(bash scripts/dev-postgres.sh url)"; eval "$(bash scripts/dev-objectstore.sh env)"; cd backend && env -u APP_ENV uv run pytest -q` | **18 failed, 1008 passed, 16 skipped, 9 errors** in 124.6 s |
| Backend, failing files in isolation | same env, `pytest tests/regression/test_upload_resume.py tests/integration/video_ingest/test_tus_edges.py tests/integration/video_ingest/test_tus_round1.py tests/regression/test_error_bodies.py tests/integration/test_it_00_01_matches_api.py` | 11 failed, 28 passed, 9 errors: the same failures, so they do not depend on test order |
| Playwright (Chromium, https) | `cd web && PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers BASE_URL=https://localhost:3000 PW_PROJECTS=chromium pnpm exec playwright test --workers=1` | **38 passed, 6 failed, 6 skipped** (9.2 min) |
| Flake check | `… playwright test e2e/sprint-01/sign-in.spec.ts:46 --repeat-each=3 --workers=1` | 2 passed, 1 failed |

### Playwright journeys (Chromium)

| Journey | Result |
|---|---|
| Sign-in via Mailpit magic link (`sign-in.spec.ts`) | 3 passed. `:17` and `:46` failed (S-02, S-06) |
| First run and capture guide (ST-015) | 5 passed |
| Match setup (ST-016) | 13 passed, 1 skipped |
| Upload with resume (ST-017) | 6 passed, 2 skipped |
| Validation refusal (ST-018) | 4 passed, 1 failed (S-03), 2 skipped |
| Sign-out (ST-014) | 3 passed |
| HTML security headers | 4 passed |
| Sprint 0 walking skeleton and BOLA | 3 failed (S-01) |

## 4. Findings, routed by owner (working agreement 1a)

| ID | Owner | Finding | Evidence | Existing row |
|---|---|---|---|---|
| S-01 | senior-qa-engineer | `walking-skeleton.spec.ts:10` and `:42`, and `object-level-authorisation.spec.ts:7`, time out waiting for the "New match" link, which ST-015/ST-016 replaced | `waiting for getByRole('link', { name: /new match/i })` at `helpers/journey.ts:21` | TCR row 22 (`journey.ts::createMatch`), Pending |
| S-02 | senior-qa-engineer | `sign-in.spec.ts:17` fails with `Please use browser.newContext()` (axe on a closed or shared context) | `sign-in.spec.ts:29` | TCR row 20, Pending |
| S-03 | senior-qa-engineer | `upload-validation.spec.ts:38`: `getByRole('alert')` matches two elements, the error summary and the Next route announcer | strict mode violation, `upload-validation.spec.ts:43` | TCR row 26, Pending |
| S-04 | senior-qa-engineer (decide), senior-backend-engineer (apply) | Backend: 9 errors and 9 failures in Sprint 0 tus tests that send arbitrary bytes at offset 0. ST-018 now refuses them with `415 not_a_video` | `assert 415 == 204`; `KeyError: 'Upload-Offset'`; log `"status": 415, "code": "not_a_video"` | TCR row 16, Pending |
| S-05 | senior-qa-engineer (decide), senior-backend-engineer (apply) | Backend: `test_error_bodies` (fields list), `test_it_00_01` (match allowlist), `test_tus_edges::test_discovery…` (`creation,checksum,expiration`), the `test_tus_round1` concurrency test and `test_it_01_06` (`429 upload_quota_exceeded`), and the `test_resumable_upload` features (`percent()` returns e.g. `19026486308`) | pytest output above | TCR rows 10-15, Pending |
| S-06 | senior-qa-engineer | **New flake:** `sign-in.spec.ts:46` "Link requested for an unknown address" fails 1 in 3 over https. `page.goto('/')` is interrupted by the client redirect to `/welcome` | `Navigation to "https://localhost:3000/" is interrupted by another navigation to "https://localhost:3000/welcome"` | blockers.md row "E2E job still red…" (recorded as 1 in 3 there) |
| S-07 | senior-ml-cv-engineer, human product owner | `test_phone_fixtures` (2 tests) stay red until real phone clips exist | `RED until ST-025: fixtures/clips/phones-v1/manifest.json does not exist` | blockers.md ST-025 row, Open |
| S-08 | sre-devops-engineer, human product owner | `test_nightly_quality::test_nightly_run_completes` needs a nightly CI result | `no nightly result in docs/sprints/01/status.json` | retro 0 A1 (nightly streak) |
| S-09 | senior-frontend-engineer, sre-devops-engineer | WebKit-only E2E failures (guide video text track, PATCH body never seen in `resumable-upload.spec.ts:43`, sign-out during upload) cannot be reproduced here | CI job 111725272519 | blockers.md row "E2E job still red…", Open. 2026-10-05 (EM, PE-R2-02): no CI run exists after `2390e9a`, so the QA-R1-05 rewrite has never run on WebKit. Close only with a green WebKit E2E job at `961648e` or later, or reopen with its logs |

No wiring defect was found in the SRE lane, so no infra change was made.

## 5. Rerun after the QA round 1 fixes (2026-10-05, senior-qa-engineer)

Same stack (`racket-smoke01`, web-tls, raised per-IP limits). E2E only: no backend change in the QA lane.

| Suite | Command | Result |
|---|---|---|
| Playwright (Chromium, https) | `cd web && PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers BASE_URL=https://localhost:3000 PW_PROJECTS=chromium pnpm exec playwright test --workers=1` | **44 passed, 6 skipped, 0 failed** (2.6 min). S-01, S-02, S-03 and S-06 are fixed |
| Flake check (S-06) | `… playwright test e2e/sprint-01/sign-in.spec.ts --repeat-each=10 --workers=1` | 50 passed, 10 skipped, 0 failed |

S-04 and S-05 (backend) are decided (TCR rows 4-10 approved) and routed to senior-backend-engineer to apply. S-09: the damaged-chunk test no longer depends on reading a request body (QA-R1-05); WebKit still needs CI.


## 6. Re-run at the sprint-close head (2026-10-05, sre-devops-engineer with senior-qa-engineer; retro 1 A5)

- **Tree:** `sprint-01` at `f97f0e7` (clean) for the stack start; `8e58d4d` (one infra wiring fix, below) for every suite. No product code changed between them.
- **Host:** `nproc` 4, 15 GB RAM. `df -h /` before cleanup `17G` free; after cleanup `21G`; after the 1 GB upload run `14G`.
- **Cleanup first (retro 1 M4):** removed the stale `qar2` Compose project (`docker compose -p qar2 down -v --remove-orphans`, idle 2 h), the default-`RA_DEV_STATE` Postgres and object store (`dev-postgres.sh stop`, `dev-objectstore.sh stop`: removed `/tmp/racket-pg.*` 64 MB and `/tmp/racket-s3.*` 771 MB), one dangling volume, `/tmp/pytest-of-root`, and `docker builder prune -f` (2.9 GB). No repo files touched.
- **Isolation:** own `RA_DEV_STATE=.local/smoke-r4`, own Compose project `racket-smoke-r4` with fresh volumes, own local Postgres and object store started under that state dir.

### 6.1 Wiring fix in the SRE lane (`8e58d4d`)

`up --build` with `DOCKERHUB_REGISTRY=mirror.gcr.io` failed: `target web: failed to solve: node:22-slim: unexpected status from HEAD request to https://registry-1.docker.io/... 429 Too Many Requests`. The five built services (migrate, api, worker, mailer, web) ignored the registry variable for their base image and their `# syntax=` frontend. They now pass `PYTHON_IMAGE`/`NODE_IMAGE` and `BUILDKIT_SYNTAX` through `${DOCKERHUB_REGISTRY:-docker.io}`; with the default the references equal the Dockerfile defaults, so CI is unchanged.

- Red first: `cd infra && uv run pytest -q tests/test_compose_registry.py` → `3 failed, 1 passed`.
- Green: same → `4 passed`; whole infra suite `274 passed in 56.54s`.

Sandbox-only (not committed): the build needs the agent proxy CA as the existing optional build secret, through a scratch override `secrets: {extra_ca: {file: /root/.ccr/ca-bundle.crt}}` plus `build.secrets: [extra_ca]` on the five built services. Without it `pnpm install` fails `SELF_SIGNED_CERT_IN_CHAIN`.

### 6.2 Stack

```
export RA_DEV_STATE=$PWD/.local/smoke-r4
cp infra/env.example $RA_DEV_STATE/smoke.env   # DOCKERHUB_REGISTRY=mirror.gcr.io; AUTH_LINK_LIMIT_PER_IP=1000; AUTH_EXCHANGE_LIMIT_PER_IP=1000
DC="docker compose -p racket-smoke-r4 -f infra/compose.yaml -f <scratch CA override> --env-file $RA_DEV_STATE/smoke.env"
$DC up -d --build --wait
```

| Check | Result |
|---|---|
| `up -d --build --wait` | `rc=0` in 114 s. Healthy: postgres, objectstore, mailpit, tracing, api, worker, mailer, web, web-tls. Exited 0: migrate, objectstore-init |
| `curl -sS -o /dev/null -w '%{http_code}' http://localhost:3000/` | `400` (plain http closed) |
| `$DC cp web-tls:/data/caddy/pki/authorities/local/root.crt …; curl --cacert root.crt https://localhost:3000/` | `200 verify=0` |
| `docker logs racket-smoke-r4-objectstore-1 \| grep -ci 'no more free space'` | `0` |
| `docker logs racket-smoke-r4-api-1 \| grep -c 'Traceback\|"level": "error"'` | `0` |

### 6.3 Suites

Backend env: `eval "$(bash scripts/dev-postgres.sh start)"`, `eval "$(bash scripts/dev-objectstore.sh start)"`, then `url`/`env`, plus `MAILPIT_API_URL=http://127.0.0.1:8025 SMTP_HOST=127.0.0.1 SMTP_PORT=1025 MAIL_SMTP_URL=smtp://127.0.0.1:1025`.

| Suite | Command | Result |
|---|---|---|
| Backend (full) | `cd backend && env -u APP_ENV uv run pytest -q -p no:cacheprovider -rfEs --junitxml=…/backend.xml` | **3 failed, 1060 passed, 6 skipped** in 137.3 s. The 3 failures are the known external blockers only: `test_nightly_quality::test_nightly_run_completes` (S-08) and `test_phone_fixtures::{test_coverage_of_the_set,test_probe_every_fixture}` (S-07, `RED until ST-025`). Skips: 5 × IT-00-10 strict (no Compose env in this run, run below), 1 × P3 (FR-043) |
| Worker sandbox IT-00-10 | `COMPOSE_PROJECT_NAME=racket-smoke-r4 COMPOSE_ENV_FILES=…/smoke.env env -u APP_ENV uv run pytest -q tests/integration/test_it_00_10_worker_sandbox.py tests/integration/test_it_00_10_worker_sandbox_strict.py` | **12 passed** |
| Sprint 1 IT ids (G01-02 a) | `junit_rate.py --include 'test_it_01_\|test_bola_matrix\|test_rules_static' --require test_it_01_{01..10,12,13}_ --require test_bola_matrix … backend.xml` | `selected 65, passed 65, failed 0, skipped 0, missing [], ok true` |
| Regression (G01-02 b) | same Compose env, `pytest tests/regression tests/integration/test_it_00_10_worker_sandbox_strict.py tests/integration/test_it_01_09* tests/integration/test_it_01_06*`, then `junit_rate.py --include 'test_upload_resume\|test_it_01_09\|test_it_01_06\|worker_sandbox_strict' …` | `71 passed in 31.5 s`; rate `selected 41, passed 41, skipped 0, ok true`. See F-01 |
| Infra | `cd infra && uv run pytest -q` | **274 passed** in 56.5 s |
| Web unit | `cd web && pnpm exec vitest run` | **31 files, 251 passed** (13.2 s) |
| Web types and lint | `pnpm exec tsc --noEmit`; `pnpm exec eslint .` | rc=0; rc=0 |
| Playwright, all specs (Chromium, https) | `cd web && PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers BASE_URL=https://localhost:3000 PW_PROJECTS=chromium pnpm exec playwright test --workers=1 --reporter=line,junit,json` | `rc=0`: **45 passed, 6 skipped, 0 failed** (2.7 min) |
| E2E rate | `junit_rate.py --include '.' --allow-skips --require E2E-01-02 --require E2E-01-03 --require 'walking-skeleton\|walking skeleton' --require 'First run and capture guide' --require 'Signing out leaves nothing behind' --require 'Upload validation' … e2e.xml` | `selected 51, passed 45, failed 0, skipped 6, rate 1.0, missing [], ok true`. Every skip names its API binding (16-min link TTL, 24 h expiry, other user's upload, 12 GB file, declared size, singles Q-04 rows) |
| Flake check (sprint-01 specs) | `… playwright test e2e/sprint-01 --repeat-each=3 --workers=1`, then `scripts/ci/flaky_report.py --fail-on-flaky e2e.xml e2e-repeat.xml` | `114 passed, 18 skipped, 0 failed` (7.2 min); `2 runs, 51 tests, 0 flaky` |
| Accessibility (axe) | `jq` on `e2e.json` (goal-scorecard §4 G01-10) | 13 axe checks, 0 failures; screens `A-01 A-04 F-01 G-01 Q-01-error Q-07 after-sign-in match-detail matches-empty new-match not-found sign-in uploading` |

### 6.4 Real-time runs on the live stack

| Run | Command | Result |
|---|---|---|
| Goal journey ×5 (fresh account each: magic link via Mailpit, `/me`, doubles match, tus drop at 40% and resume, damaged chunk 460, complete, facts, 12 GB → 413, PDF → 415, sign-out → 401) | `python3 scripts/measure/live_goal.py --api https://localhost:3000/api --origin https://localhost:3000 --mailpit http://127.0.0.1:8025 --cacert $RA_DEV_STATE/root.crt --file fixtures/clips/synthetic-60s/clip.mp4 --runs 5` | `rc=0`, **5/5 PASS**; `sign_in_p95_s 1.067`, `final_byte_to_facts_p95_s 0.888`, `throughput_min_mbps 72.1` |
| API reads at 50 RPS for 60 s | `python3 scripts/measure/api_latency.py --api http://127.0.0.1:8000 --origin https://localhost:3000 --mailpit http://127.0.0.1:8025 --rps 50 --duration 60` | `rc=0`: `p95 16.6 ms`, `p99 71.0 ms`, availability `1.0`, unexpected `0`, achieved `50.01 RPS` |
| 1 GB 1080p60 upload over https, 8 MiB chunks with sha256 | `bash scripts/measure/make_large_fixture.sh $RA_DEV_STATE/large-1080p60.mp4 120`; `live_goal.py --cacert … --file $RA_DEV_STATE/large-1080p60.mp4 --runs 1 --result-timeout 300` | `rc=0`; `bytes 1052829819` (= file size), `transfer_s 16.873`, **`throughput_mbps 499.2`**; result `video_received` |

These are smoke evidence, not the scorecard: the verifier still fills `goal-scorecard.md` from its own isolated run (§3 rule 1).

### 6.5 Findings, routed by owner

| ID | Owner | Finding | Evidence |
|---|---|---|---|
| F-01 | engineering-manager (scorecard author) with senior-qa-engineer | goal-scorecard §4 G01-02(b) cannot pass as written: the first backend command runs `tests/integration` **without** the Compose env, so the 3 `worker_sandbox_strict` cases selected by `--include … worker_sandbox_strict` are **skipped** in `backend-it.xml`, and `junit_rate.py` fails closed even though `sandbox.xml` has them passing | `junit_rate.py … backend.xml sandbox.xml` → `selected 54, passed 51, skipped 3, ok false`; the same cases with `COMPOSE_PROJECT_NAME`/`COMPOSE_ENV_FILES` set → `41/41, ok true`. Fix: set the Compose env on the first command or exclude the strict file from it |
| F-02 | sre-devops-engineer (done, `8e58d4d`) | Built images ignored `DOCKERHUB_REGISTRY` (429 on a fresh build) | §6.1 |
| S-07, S-08, S-09 | unchanged | Phone clips (ST-025), nightly run, WebKit-only results still need the human PO / CI | backend failures above; WebKit cannot run here |

**Verdict:** ready for review. Every suite is green except the 3 tests held by external blockers (S-07, S-08). All Sprint 1 Playwright journeys pass on Chromium over https with 0 flaky over 3 repeats, and the live goal journey passes 5 of 5. WebKit still has CI evidence only (S-09).
