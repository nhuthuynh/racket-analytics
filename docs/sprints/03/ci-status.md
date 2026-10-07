# Sprint 3 CI status (sre-devops-engineer)

One row per CI run that matters to the sprint: what ran, at which SHA, the result, and who owns each red. Append only.

| Date | Run | Branch / SHA | Result | Reds and owners |
|---|---|---|---|---|
| 2026-10-06 | 37521787513 (dispatch) | `sprint-03` / `78644f3` | failure | Secret scan only: `generic-api-key` on the SEC-RV3-02 synthetic test key (`backend/tests/unit/platform/test_settings_sprint03.py:41`, `9ca52fe`). Fixed on `sprint-03` by `e7e86ef` (exact fingerprint in `.gitleaksignore`, guarded by `infra/tests/test_gitleaks_ignore.py`) |
| 2026-10-07 | 37606256586 (schedule, nightly) | `main` / `259a0a8` | failure (`ci-gate`) | **QA-R1S3-02 (root cause confirmed from the job log).** Every job green except "Secret scan, dependency audit": gitleaks scans every fetched ref (356 commits), so it finds the same `9ca52fe` key on `sprint-03`; the ignore file `e7e86ef` exists only on `sprint-03`. E2E (Chromium + WebKit), Locust baseline, integration, unit, infra, web, mypy, SBOM: success. Remedy: bring `.gitleaksignore` and its guard test to `main` (cherry-pick of `e7e86ef` in a small PR to `main`; PO merge), or wait for the Sprint 3 merge. Until then every nightly on `main` is red on this one finding. Owner: sre-devops-engineer (PR) with the orchestrator/PO (merge) |
