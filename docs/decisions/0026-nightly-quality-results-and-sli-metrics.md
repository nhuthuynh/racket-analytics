# 0026. Nightly quality jobs publish to the sprint status file; SLI metric names and emission

- **Status:** Proposed (sre-devops-engineer R; principal-engineer and senior-qa-engineer review as ST-024 reviewers). Publishing to `main` needs a human admin decision on branch protection (see Consequences).
- **Date:** 2026-10-05
- **Deciders:** sre-devops-engineer
- **Consulted:** senior-qa-engineer (seams `STATUS_NIGHTLY_KEY`, `SLI_*` in `backend/tests/support/contract.py`), senior-backend-engineer (metric-name proposal, `docs/architecture/api-sprint-01.md` §10)
- **Related:** sprint-01 §3.1 ST-024, §14.3.8; ADR 0008 (mutmut); ADR 0014 (fail closed); NFR-002b, NFR-041, NFR-042, NFR-072

## Context and problem statement

ST-024 asks for (1) a nightly workflow that runs the 100,000-sequence differential oracle (P9) and a mutation run on `sports/pickleball/rules`, with results "posted to `docs/sprints/01/status.json`", and (2) the availability (NFR-041) and upload-completion (NFR-042) SLIs emitted as OpenTelemetry metrics, with dashboards. Alerts are Sprint 5.

Two choices are significant: how a scheduled job writes into a file on `main`, and the metric names that the dashboards and Sprint 5 alerts will depend on.

## Decision drivers

- The status file is where the team reads sprint state (§14.3.8 "When the team opens the sprint status file").
- Least privilege for CI tokens; test code must not run with write access (judgment, DPA/AI-13 minimal permissions).
- Fail closed: a missing report is never shown as passed (ADR 0014).
- OTel semantic conventions over custom names where one exists [AQS/OPS-07] (judgment on which convention).
- No personal data in metric attributes (NFR-069).

## Considered options

### A. Publishing nightly results

1. **Do nothing / artifact only.** Results only as workflow artifacts. Pro: no write token. Con: fails §14.3.8; nobody reads artifacts.
2. **Bot PR per night.** Pro: works with "require PRs". Con: a PR every night that someone must merge; the status file goes stale until merged.
3. **Direct bot commit to the default branch from a separate `publish` job** (chosen). Only `publish` has `contents: write`; it runs no test code and receives the reports as job outputs (small JSON). The commit message carries `[skip ci]`, and `GITHUB_TOKEN` pushes do not start workflows, so there is no loop. Pro: the status file is current every morning. Con: needs a branch-protection bypass for `github-actions[bot]` if "require PRs" is enabled.
4. **A separate `nightly-results` branch.** Pro: no protection conflict. Con: the status file on `main` never shows the results.

### B. Metric names

1. **Custom SLI counters** (`racket.sli.http.responses{sli.outcome}`), my first draft. Pro: the SLI is a ratio of two series. Con: duplicates the standard HTTP metric and hides status codes.
2. **BE proposal, api-sprint-01 §10** (chosen): standard `http.server.request.duration` (histogram, s) with `http.request.method` and `http.response.status_code`; `racket.upload.sessions` (counter) with `event` ∈ created, completed, expired, rejected, cancelled and `reason` on rejected only. Pro: standard names work with stock dashboards; the upload lifecycle is explicit. Con: the SLI is computed in the query.

## Decision

- A3 and B2.
- `.github/workflows/nightly-quality.yml` (02:43 UTC and manual dispatch): `oracle` runs `python -m tests.oracle.differential --sequences 100000`; `mutation` runs `scripts/ci/mutation_score.py` with mutmut 3.8.0 (ADR 0008), score = (killed + timeout) / (total − skipped); `publish` runs `scripts/ci/nightly_status.py --status auto` and commits. The `nightly` key holds `run_date`, `run_url`, `commit`, `oracle` and `mutation`. A missing report is `no_report`, a missing target is `target_missing`, and mutants that were never tested are `not_checked` with no score.
- Sprint 1 records the mutation baseline. The ≥ 85% gate (`--min-score 0.85`) starts in Sprint 2 (NFR-072).
- `racket.platform.slis`: `HttpMetricsMiddleware` (outermost, so error-mapped 5xx and crashes are counted; a crash before a response counts as 500), `SLIRecorder.upload_event` for the upload context, and the pure `availability` and `upload_completion` functions that define the SLI arithmetic. Unusual HTTP methods are bucketed to `_OTHER` to bound cardinality. No route, path or user attributes.
- Metrics export only when `OTEL_EXPORTER_OTLP_METRICS_ENDPOINT` is set (OTLP/HTTP). Compose has no metrics backend yet (Jaeger stores traces only), so emission is a no-op in dev. Dashboard definition: `infra/observability/dashboards/slis.json` (Grafana, Prometheus data source, queries in `docs/ops/sli-metrics.md`).

## Consequences

- **Human admin action:** if branch protection "require PRs" is enabled on `main` (ci-cd.md §2.1), add `github-actions[bot]` / the GitHub Actions app as a bypass actor, or the `publish` push is rejected (the job fails visibly; the results stay in the job summary and artifacts). If a bypass is not acceptable, switch to option A2 with a new ADR.
- The oracle and mutation jobs stay red until ST-020 creates `racket.sports.pickleball.rules`. That is expected (red-first); the status file then shows `oracle.status: no_report` and `mutation.status: target_missing`.
- The upload-completion SLI has data only once the upload context calls `SLIRecorder.upload_event` (ST-017/ST-018, senior-backend-engineer).
- A metrics backend (collector to Prometheus or a managed service) is needed before the dashboard shows data. That is a Sprint 5 decision together with alerts; a new paid service is escalated (SRE role rule).
- Rollback: delete `nightly-quality.yml` and remove the `nightly` key; remove one `add_middleware` line in `platform/app.py`.

## Evidence

| Claim | Evidence |
|---|---|
| Scripts and workflow behave as specified | `cd infra && uv run pytest -q tests/test_nightly_quality.py` → `15 passed` (13 red first: `13 failed` before the scripts and workflow existed) |
| SLI arithmetic and emission | `cd backend && env -u APP_ENV uv run pytest -q tests/unit/platform/` → `69 passed`; QA binding `tests/features/test_nightly_quality.py` → 4 SLI scenarios pass, "Nightly run completes" stays red until the first nightly run on `main` |
| Differential pipeline tells right from wrong | `differential.main(..., candidate=oracle_run)` → exit 0; `candidate=mutants.receiver_scores` → exit 1, 1955/2000 disagreements, shortest prefix length 1, written into a copy of status.json as `oracle.status: failed` |
| Mutation script measures a real package | positive control in a scratch copy of `backend/`: `mutation_score.py --target src/racket/matches --tests tests/unit/matches` → `measured`, 239 mutants, 33 killed, score 0.1381. First attempt exposed that mutmut 3 needs `also_copy = src/` and newline-separated lists, and that untested mutants must not score 0 (guarded by `test_mutants_that_were_never_tested_give_no_score`) |
| Production engine not there yet | `python -m tests.oracle.differential --sequences 2000` → `RED until ST-020: seam 'racket.sports.pickleball.rules:RulesConfig' is not implemented yet` |
| Workflow syntax | `actionlint` (actionlint-py 1.7.12.25 with shellcheck) → no findings |
