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

## Run 37298471332: `workflow_dispatch` on `sprint-01` (head 2390e9a, 2026-10-05 10:44-11:05 UTC)

Conclusion: **failure**. <https://github.com/nhuthuynh/racket-analytics/actions/runs/37298471332>. Green: actionlint, Ruff, mypy, fixtures, web, infra tests, secret scan and pip-audit, SBOM and licence gate, flaky report. Red:

| Job | Failing step | Cause | Lane / owner | Action |
|---|---|---|---|---|
| Python unit suites | Domain unit suite < 10 s | killed at the 10 s budget on a cold bytecode cache (11.1 s cold vs 6.8 s warm locally) | SRE | Fixed `a4dfd43`: unbudgeted collect-only warm-up; budget unchanged |
| Integration on Compose | Backend suites: 44 failed, 980 passed, 14 errors | (1) no `ffprobe` on the runner: probe stage fails, so upload, walking-skeleton, worker-crash and probe tests fail; (2) `MAILPIT_API_URL` not set: 7 IT-01-01 and 3 sign-in feature tests; (3) `test_nightly_quality::test_nightly_run_completes`: no nightly run yet; (4) tus/upload test defects (TCR rows, now decided in `71da707`) and ST-025 phone fixtures (blocker) | SRE for (1)-(3); BE/QA for (4); PO for ST-025 | (1), (2) fixed `a4dfd43`; (3) needs the first nightly run, see blockers.md (push needed) |
| E2E | Playwright: 74 passed, 14 failed | no WebKit sign-in failure (ADR 0029 cookie fix holds); remaining are spec drift and WebKit-only UI issues, see blockers.md | QA, FE | QA-R1-01/02 E2E fixes in `71da707` |
| ci-gate | aggregate | — | — | re-check on the next run |

Evidence for `a4dfd43`: `cd infra && uv run pytest -q tests/test_workflows_ci_run2.py` → red first per guard (`2 failed` for the warm-up guards, then `4 failed` for the ffprobe and Mailpit guards, each before its `ci.yml` change), `6 passed` after; `GITHUB_ACTIONS=true CI=true uv run pytest -q -m "unit or integration"` → `245 passed`; `actionlint .github/workflows/ci.yml` → clean.

**Next run: not dispatched.** GitHub `sprint-01` is at `6ba9b28`, behind the local head; a dispatch would test stale code. Waiting for the EM push (blockers.md), then dispatch `ci.yml` and `nightly-quality.yml` and record both IDs here and in `status.json`.

## PE-R2-02 check, 2026-10-05 (engineering-manager): no CI run covers the round-1 fixes yet

- `mcp__github__actions_list list_workflow_runs` on branch `sprint-01` → `total_count=1`: run 37298471332, head `2390e9a`, conclusion failure. No run exists for any later commit, and no `nightly-quality.yml` run exists.
- `mcp__github__list_branches` → GitHub `sprint-01` is now at `961648e75a0e` (the push asked for in blockers.md has happened). That head includes `71da707` (QA-R1-01/02/05 E2E fixes, including the WebKit damaged-chunk rewrite), `4f10ba2` and `a4dfd43`.
- Consequence: the ADR 0029 WebKit cookie fix is verified only at `2390e9a`. No WebKit sign-in or E2E claim for code after `71da707` has evidence. S-09 (smoke.md) stays **Open**. ST-013, ST-014, ST-015 and ST-017 carry this in `status.json` `open` and are not DoD-done. `ci-gate` stays red.
- **Next step (human product owner):** dispatch `ci.yml` and `nightly-quality.yml` (`workflow_dispatch`, ref `sprint-01`) at `961648e` or later. Agents have not dispatched them. The finding routes the dispatch to the human. The SRE then records both run IDs here and in `status.json` `ci_runs.runs`, and closes S-09 or reopens it with the WebKit job logs.

## QA-R2-02 check, 2026-10-05 (sre-devops-engineer): still no run after `2390e9a`; dispatch left to the human

- `mcp__github__list_branches` → GitHub `sprint-01` = `961648e75a0e00f2050e261d38cf965d4c745f14` (push from the QA-R1-06 blocker has happened; that part of the blocker row is resolved).
- `mcp__github__actions_list list_workflow_runs` branch `sprint-01` → `total_count=1`: run 37298471332, head `2390e9a`, failure. No `ci.yml` run after it and no `nightly-quality.yml` run at all.
- `git log --oneline 961648e..HEAD` (local) → `4430b25`, `5873308`, `0519599`; QA-R2-01 is not committed yet. GitHub is behind the round-2 fixes.
- **Not dispatched by the SRE.** (1) The EM routed the dispatch to the human product owner (decision-log, PE-R2-02). (2) `nightly-quality.yml`'s `publish` job commits to GitHub `sprint-01` (ADR 0026); with the local branch ahead, an agent-triggered nightly would make local and GitHub diverge, and agents never push or rewrite history. (3) A run at `961648e` would not include QA-R2-01, which the finding names as a precondition.
- Unblock order and close conditions: blockers.md, QA-R1-06 row. S-09, QA-R1-05 (WebKit damaged chunk) and `test_nightly_run_completes` stay open until a green WebKit E2E job and a published `nightly` key exist for a head that includes the round-2 fixes.

## Check on 2026-10-05, sprint-close review round 1 (engineering-manager, PE-R3-05/QA-R3-05)

No new run. `mcp__github__actions_list list_workflow_runs` → `total_count: 2` (37277549983 on `main` at `2b9c6ca`, 37298471332 on `sprint-01` at `2390e9a`, both `conclusion: failure`). `mcp__github__list_branches` → `sprint-01` = `9195ea9`, `main` = `2b9c6ca`; local `sprint-01` is ahead. Open and escalated to the human PO (push without force, dispatch `ci.yml` then `nightly-quality.yml`, or decide `sprint-report.md` §6 D1); see `blockers.md`. The SRE records the run IDs here when they exist.

## Check on 2026-10-05, sprint-close review round 1 (sre-devops-engineer, PE-R3-05, S-08)

Still no new run. `mcp__github__actions_list list_workflow_runs` → `total_count: 2` (37277549983 on `main` at `2b9c6ca`, 37298471332 on `sprint-01` at `2390e9a`, both `conclusion: failure`); no `nightly-quality.yml` run exists. `mcp__github__list_branches` → `sprint-01` = `9195ea9`, `main` = `2b9c6ca`, both `protected: false`. Local `sprint-01` = `33e6146`, `git rev-list --count 9195ea9..HEAD` → 8. No run IDs to record. The SRE did not push or dispatch (agents do not push; the nightly `publish` job commits to GitHub `sprint-01`, ADR 0026, which would diverge from the local branch). Open on the human PO: push `sprint-01` without force, dispatch `ci.yml` then `nightly-quality.yml`, turn on branch protection for `main` with `ci-gate` required, or decide D1. Note for the dispatch: the nightly mutation job now passes `--ignore tests/unit/sports/pickleball/test_rules_static.py` (`33e6146`, QA-V1-03); without that commit on GitHub the nightly mutation job cannot produce a score.

## Check on 2026-10-05, sprint-close review round 2 (engineering-manager, PE-R3-05 family, QA-R2V-01)

No new run. `mcp__github__actions_list list_workflow_runs` → `total_count: 2` (37277549983 on `main` at `2b9c6ca`, 37298471332 on `sprint-01` at `2390e9a`, both `conclusion: failure`); no `nightly-quality.yml` run. `mcp__github__list_branches` → `sprint-01` = `9195ea9`, `main` = `2b9c6ca`, both `protected: false`. `git rev-list --count 9195ea9..351488e` → 30 local commits not on GitHub.

**One disposition (ADR 0030) for the whole family:** QA-R1-06, PE-R2-02, QA-R2-02, PE-R3-05 / QA-R3-05 (both rows) and QA-R2V-01 describe the same missing push and dispatch. They are closed as duplicates of **PE-R3-05**, which stays **Open, escalated to the human PO** (blockers.md EM row "PO decision request, review round 2", item P1). `review-rounds.md` review round 2 has a single row naming all of these ids, so `open_defects.py` counts the family once. Agents did not push or dispatch. Once the PO acts, the SRE records both run IDs here and in `status.json` `ci_runs.runs`; S-08 (`test_nightly_run_completes`) and S-09 (WebKit) are judged on those runs.

## Check on 2026-10-05, goal round 1 (sre-devops-engineer, DEMO step 7)

No new run. `mcp__github__actions_list list_workflow_runs` → `total_count: 2` (37277549983 on `main` at `2b9c6ca`, 37298471332 on `sprint-01` at `2390e9a`, both `conclusion: failure`); no `nightly-quality.yml` run exists, so demo step 7 has no nightly result to show. `mcp__github__list_branches` → `sprint-01` = `9195ea9`, `main` = `2b9c6ca`, both `protected: false`. Local `sprint-01` is 46 commits ahead (`git rev-list --count 9195ea9..d16f51b`). No run IDs to record; still waiting on the human PO (blockers.md EM row P1).

## Check on 2026-10-05, goal round 2 (sre-devops-engineer, DEMO-07)

No new run. `mcp__github__actions_list list_workflow_runs` → `total_count: 2` (37298471332 on `sprint-01` at `2390e9a`, 37277549983 on `main` at `2b9c6ca`, both `conclusion: failure`). There is no `nightly-quality.yml` run, so demo step 7 still has no nightly result. `mcp__github__list_branches` → `sprint-01` = `9195ea9`, `main` = `2b9c6ca`, both `protected: false`. Still waiting on the human PO (blockers.md EM row P1).
