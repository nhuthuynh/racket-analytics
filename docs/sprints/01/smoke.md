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
| S-09 | senior-frontend-engineer, sre-devops-engineer | WebKit-only E2E failures (guide video text track, PATCH body never seen in `resumable-upload.spec.ts:43`, sign-out during upload) cannot be reproduced here | CI job 111725272519 | blockers.md row "E2E job still red…", Open |

No wiring defect was found in the SRE lane, so no infra change was made.
