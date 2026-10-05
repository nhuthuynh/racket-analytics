# Sprint 1 CI status

Owner: sre-devops-engineer. One section per CI run that the sprint acts on. Job results are read
with the GitHub MCP tools (`actions_get get_workflow_run`, `actions_list list_workflow_jobs`,
`get_job_logs`); there is no `gh` CLI in the sandbox.

## Run 37277549983: first CI run on `main` (commit 2b9c6ca, push, 2026-10-05 07:24-07:27 UTC)

Conclusion: **failure**. <https://github.com/nhuthuynh/racket-analytics/actions/runs/37277549983>

| Job | Result | Failing step | Cause | Lane / owner | Action |
|---|---|---|---|---|---|
| Workflow lint (actionlint) | success | — | — | — | — |
| Python lint and format (Ruff) | success | — | — | — | — |
| Python types (mypy) | success | — | — | — | — |
| Python unit suites (time-budgeted) | success | — | — | — | — |
| Fixture and gold-set integrity | success | — | — | — | — |
| Web lint, types, unit, coverage, bundle budget | success | — | — | — | — |
| Infra, hooks and CI-script tests | **failure** | `uv run pytest -q -m "unit or integration"`: 10 failed, 186 passed | `infra/tests/conftest.py::run_hook` passed the runner's `GITHUB_ACTIONS=true` to `.claude/hooks/stop.py`, which then does nothing by design (CI bot mode), so every Stop-hook test saw exit 0 and no run | SRE (infra tests) | Fixed: harness drops `GITHUB_ACTIONS`/`CI`; tests that need them pass them explicitly |
| Integration, scenario and regression suites on Compose | **failure** | Start backing services | `docker compose up -d --wait ... objectstore-init ...` exits 1 on `container racket-analytics-objectstore-init-1 exited (0)`: `--wait` treats a finished one-shot as a failure. Backend suites never ran | SRE (CI) | Fixed: `up --wait` the long-running services, then `compose run --rm objectstore-init`. Same fix in `flaky-report` |
| Secret scan, dependency audit | **failure** | pip-audit | `FORCE_COLOR=1` made `uv export` write ANSI colour codes into `/tmp/req.txt`; pip-audit: `invalid specifier at line 1`. gitleaks passed; pnpm audit was skipped | SRE (CI) | Fixed: `uv export --color never ... -o /tmp/req.txt`. Vulnerability result itself not yet known |
| SBOM (CycloneDX) and licence gate | **failure** | SBOM for the backend environment | `ENOENT: no such file or directory, open 'reports/sbom-backend.cdx.json'`: sbom-action does not create the output directory. Licence gate never ran | SRE (CI) | Fixed: `mkdir -p reports` before the SBOM steps. Licence result not yet known |
| E2E (Playwright, Chromium + WebKit) | **failure** | Playwright journeys | 11 passed, 3 failed, all `[webkit]`: after "sign in as", `getByRole('heading', { name: /matches/i })` not visible (helpers/journey.ts:17). Chromium passed the same journeys. Matches the Sprint 0 open blocker: WebKit rejects the `Secure` `__Host-racket_session` cookie over `http://localhost` with `APP_ENV=dev`. IT-00-10 worker sandbox step passed | BE + security (cookie policy), FE (E2E) | Blocker raised in `blockers.md`; not changed in CI (changing APP_ENV or TLS for E2E is a security-relevant choice) |
| Flaky-test report | skipped | — | push event; runs on schedule/dispatch only | — | — |
| PR policy | skipped | — | push event, allowed by `ci-gate` | — | — |
| ci-gate | **failure** | — | aggregates the five failures above | — | Re-check after the fixes land on `main` |

### Evidence for the CI fixes (local, sprint-01 branch)

- Red first: `cd infra && GITHUB_ACTIONS=true uv run pytest -q tests/test_hook_stop.py` → `10 failed, 3 passed` (same 10 tests as CI).
- New regression guards red first: `uv run pytest -q tests/test_workflows_ci_run1.py` → `5 failed`; after the `ci.yml` fix → `5 passed`.
- Green: `cd infra && GITHUB_ACTIONS=true CI=true uv run pytest -q -m "unit or integration"` → `197 passed`.
- Compose: old command `up -d --wait postgres objectstore objectstore-init mailpit tracing` → exit 1; new `up -d --wait postgres objectstore mailpit tracing` → exit 0, then `run --rm objectstore-init` → exit 0 ("created bucket racket-media"). Run under project `sre01` with shifted host ports and `DOCKERHUB_REGISTRY=mirror.gcr.io`.
- `FORCE_COLOR=1 uv export --locked --no-dev --no-emit-project --format requirements-txt | grep -c $'\x1b'` → `92`; with `--color never -o file` → `0`.
- `actionlint .github/workflows/ci.yml` (actionlint-py 1.7.12.25) → no findings.

Not verifiable in the sandbox: the SBOM action and the outcome of pip-audit/licence gate once they
can actually run. They are confirmed by the next CI run on `main` (the EM pushes; agents never push).
