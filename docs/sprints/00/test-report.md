# Sprint 0 test report

- **Owner:** senior-qa-engineer. **Signed:** 2026-10-05, senior-qa-engineer (closes QA-R3-04 and retro 0 action A2).
- **History:** first drafted by the senior-backend-engineer in review auto-fix round 1 (2026-10-03); rewritten here from fresh runs after review round 3 and the QA carry-over (commit `3e9cb04`).
- **Tree:** branch `sprint-01` at `cd2612f` (Sprint 0 code plus Sprint 1 red-first tests). Sprint 0 scope is selected with `-m "not red_until"`: every Sprint 1 test written before its code carries `red_until(story=…)`.
- **Backing services:** real Postgres 16 (`scripts/dev-postgres.sh`) and SeaweedFS 3.97 (`scripts/dev-objectstore.sh`) for the suites; a fresh Compose stack (`COMPOSE_PROJECT_NAME=qa01`, images built from this tree with `DOCKERHUB_REGISTRY=mirror.gcr.io` and the proxy CA as a build secret) for IT-00-10, Mailpit and the browser journeys. Never SQLite or mocks for integration tests.

## 1. Results

| Suite | Command (directory) | Result |
|---|---|---|
| Backend: unit, integration, regression, scenario (Sprint 0 scope) | `backend/`: `COMPOSE_PROJECT_NAME=qa01 COMPOSE_ENV_FILES=<qa env> MAILPIT_API_URL=http://127.0.0.1:28025 env -u APP_ENV uv run pytest -q -m "not red_until" tests` | `503 passed, 131 deselected in 56.19s`, **0 skipped** (IT-00-10 ran against Compose) |
| IT-00-10 worker sandbox, old and strict files (Compose) | `backend/`: `CI=true … uv run pytest -q tests/integration/test_it_00_10_worker_sandbox.py tests/integration/test_it_00_10_worker_sandbox_strict.py` | `12 passed in 2.87s`. Discrimination check: probe from `api` to `https://example.com/` → `OPEN tls`; from `worker` → `BLOCKED dns`; worker → object store `OPEN http` |
| Backend static checks | `backend/`: `uv run ruff check .`; `uv run ruff format --check .`; `uv run mypy` | `All checks passed!`; `180 files already formatted`; `Success: no issues found in 56 source files` |
| Infra, hooks, CI scripts | `infra/`: `env -u S3_ENDPOINT_URL uv run pytest -q` | `217 passed in 54.52s` |
| Web unit (Vitest) | `web/`: `pnpm exec vitest run` | `Tests 132 passed (132)` |
| E2E (Playwright, Chromium) against Compose `api`/`worker` and the `web` image built from this tree | `web/`: `CI=true BASE_URL=http://localhost:23000 PW_PROJECTS=chromium pnpm exec playwright test e2e/walking-skeleton.spec.ts e2e/object-level-authorisation.spec.ts e2e/security-headers.spec.ts` | `7 passed (15.8s)` |
| E2E repeat (flake check, QA-R1-04/05 rows) | same, `--repeat-each=3` on `walking-skeleton` and `object-level-authorisation` | `9 passed (40.5s)` |

## 2. Test changes and approvals

All six Sprint 0 test-change rows are decided (`grep -c '| Pending |' docs/sprints/00/test-change-requests.md` → `0`): five approved, one approved with follow-up (QA-R3-06, the reload test still does not resume from a non-zero offset; replaced by E2E-01-02 in Sprint 1). The weak IT-00-10 probe is retired (QA-R3-07) and the 21 stale `red_until` markers are gone (QA-R3-08); both are logged in `docs/sprints/01/test-change-requests.md`.

## 3. Skipped, quarantined and flaky

- **Skipped in the Sprint 0 scope:** none in this run. Without Compose, the 5 IT-00-10 tests skip locally by design and fail in CI (`CI=true`).
- **Flaky:** none observed (`--repeat-each=3` above). The reload test flake (QA-R1-05) is fixed.
- **Quarantined:** none.

## 4. Not covered here (open, with owners)

| Item | Why | Owner |
|---|---|---|
| WebKit project of the browser matrix | No WebKit browser in this container (only Chromium under `/opt/pw-browsers`). On GitHub, CI run 37277549983 failed 3 WebKit journeys at sign-in (`Secure` session cookie over plain http; `docs/sprints/01/blockers.md`, SRE row 2026-10-05) | senior-backend-engineer + security-privacy-engineer (cookie policy), sre-devops-engineer (re-run) |
| A green `ci-gate` run on GitHub for the Sprint 0 tree | The first `main` run (37277549983) is red only on the WebKit row above; branch protection and labels are retro 0 A1 | sre-devops-engineer, human product owner |
| Manual keyboard and screen-reader pass on the ST-010 shell | Manual, per sprint (NFR-027b) | principal-designer with senior-qa-engineer |

## 5. Sign-off

Sprint 0 test DoD items owned by QA are met for the local evidence above: every Sprint 0 scenario and regression suite is green, no test change is pending, no unowned skip or flake. The Sprint 0 story DoD still waits for the GitHub CI evidence in §4. Signed: senior-qa-engineer, 2026-10-05.
