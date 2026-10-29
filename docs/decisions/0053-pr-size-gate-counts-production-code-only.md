# 0053. The PR size gate counts production code only; tests, docs and lockfiles are excluded

- **Status:** Accepted (PO decision 2026-10-28, in chat; the sre-devops-engineer owns the CI contract, ADR 0014).
- **Date:** 2026-10-28 (Sprint 4, ticket CI-SIZE-PROD-ONLY)
- **Deciders:** PO (rule), sre-devops-engineer (implementation)
- **Related:** amends ADR 0022 (commit unit, 400-line ceiling) and ADR 0030 (slices planned at 400 lines, waiver first); ADR 0052 (draft first); EP/ENG-04, NFR-077

## Context

`scripts/ci/check_pr_size.py` counted every changed line except lockfiles, fixtures and snapshots. In Sprint 4 the TDD rule (scenario, integration and unit tests in every PR) made test-heavy PRs cross 400 lines, so tickets were split repeatedly or needed a `size-waiver`. One split mixed code and tests in a single commit and broke the red-first check (#142, #143). The limit is meant to keep production changes reviewable; tests and docs are what the process asks for.

## Decision

1. Keep `SOFT_LIMIT` 100, `HARD_LIMIT` 400 and the `size-waiver` label.
2. Count only production code. Excluded: tests (`backend/tests/*`, `web/tests/*`, `infra/tests/*`, `e2e/*`, `*/e2e/*`, `tests/*`, `*.feature`, `*.spec.ts`, `*.test.ts`, `*.test.tsx`, `conftest.py`), docs (`docs/*`, `*.md`), lockfiles (`uv.lock`, `pnpm-lock.yaml`, `package-lock.json`), fixtures and snapshots (`fixtures/*`, `*.snap`). Binary files count on neither side.
3. Paths are classified after `git diff --numstat --no-renames`: a move counts as a deletion of the old path plus an addition of the new one, so a file moved from tests or docs into production code counts in full (review PE-SIZEPROD-R1-01). A rename record, if one is ever measured, is classified by its destination path.
4. The step prints both totals: `pr-size: N changed lines of production code (target ~100, limit 400); M excluded lines (tests, docs, lockfiles, fixtures)`.
5. ADR 0022's commit unit and ADR 0030's slice plan measure the same production-code lines from now on.

## Consequences

- Good: a ticket with full TDD evidence no longer needs a waiver or a split because of its tests; red-first commits are not cut apart to fit the gate.
- Good: oversize production code still fails without a waiver, even when tests come with it (`tests/features/pr_size_production_only.feature`).
- Bad: a move of a production file counts both its sides (a 150-line move counts 300); a large move needs a waiver or its own PR.
- Bad: a very large test or docs change is not limited by CI. Reviewers still judge it; the excluded total is printed so it stays visible.
- Neutral: `scripts/ci/size_decisions.py` still budgets 40 lines for the ticket's decisions file, which no longer counts; that budget is now slack (follow-up, not changed here).

## Evidence

- Red: `cd infra && uv run --no-sync pytest -q tests/test_check_pr_size_unit.py tests/test_pr_size_production_only_scenarios.py tests/test_ci_scripts.py tests/test_pr_change_set.py tests/test_pr_policy_scenarios.py tests/test_pr_policy_live_labels_scenarios.py` → `37 failed, 42 passed` before the change; `79 passed` after.
