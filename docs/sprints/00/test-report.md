# Sprint 0 test report

Drafted by senior-backend-engineer in review auto-fix round 1 (2026-10-03) from runs in the dev container; **owner: senior-qa-engineer** (sign-off pending). Every row lists the command and the result as printed. Backing services: real Postgres 16 (`scripts/dev-postgres.sh`) and SeaweedFS 3.97 (`scripts/dev-objectstore.sh`), or the Compose stack where noted. Never SQLite or mocks for integration tests.

| Suite | Command (from the directory shown) | Result |
|---|---|---|
| Backend, everything (unit, integration, regression, scenario) | `backend/`: `uv run pytest -q` with `DATABASE_URL` and `S3_*` exported, **no** `APP_ENV` | `339 passed, 2 skipped in 47.67s` (the 2 skips are IT-00-10, which needs the Compose `worker`) |
| Domain unit suite, NFR-073 budget | `backend/`: `python3 ../scripts/ci/run_with_budget.py 10 -- uv run --no-sync pytest -q -m unit tests/unit` | `175 passed in 2.11s`; `budget: finished in 3.2s, within budget of 10s` |
| Backend unit suite, NFR-073 budget | `backend/`: `python3 ../scripts/ci/run_with_budget.py 60 -- uv run --no-sync pytest -q -m unit` | `195 passed, 146 deselected in 2.39s`; `finished in 3.4s` |
| Property tests, Hypothesis `ci` profile (>= 1,000 examples) | `backend/`: `HYPOTHESIS_PROFILE=ci python3 ../scripts/ci/run_with_budget.py 90 -- uv run --no-sync pytest -q -m unit tests/unit` | `175 passed in 15.69s`; `finished in 16.8s, within budget of 90s` |
| IT-00-10 worker sandbox (Compose) | `backend/`: `COMPOSE_PROJECT_NAME=r1review COMPOSE_ENV_FILES=<env file> CI=true uv run pytest -q tests/integration/test_it_00_10_worker_sandbox.py` against a fresh-volume stack (`up -d --wait postgres objectstore objectstore-init mailpit tracing migrate api worker` → rc=0) | `2 passed in 0.91s` |
| Backend static checks | `backend/`: `uv run ruff check .`; `uv run ruff format --check .`; `uv run mypy` | `All checks passed!`; `140 files already formatted`; `Success: no issues found in 55 source files` |
| Infra, hooks, CI scripts | `infra/`: `uv run pytest -q` | `189 passed in 52.63s` |
| Workflow lint | repo root: `actionlint -color=false` | rc=0 |
| Web unit (Vitest) | `web/`: `pnpm exec vitest run` | `Tests 132 passed (132)` |
| Web types and lint (e2e) | `web/`: `pnpm exec tsc --noEmit`; `pnpm exec eslint --max-warnings=0 e2e` | rc=0 |
| E2E (Playwright, Chromium) | `web/`: `CI=true BASE_URL=http://localhost:13000 PW_PROJECTS=chromium pnpm exec playwright test` against the Compose `api`/`worker` (images built from this tree) and `pnpm build && pnpm start` on :13000 | `7 passed (13.3s)`; again on the same DB `7 passed (13.8s)` |
| E2E walking skeleton, repeat | same, `e2e/walking-skeleton.spec.ts --repeat-each=5` | `10 passed (49.6s)` |

Not covered here: WebKit (no WebKit browser in this container; blockers.md), the web Docker image (not built in this round), and a GitHub Actions run (no remote; blockers.md).
