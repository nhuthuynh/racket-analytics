# 0052. CI skips draft pull requests; policy decisions are made while draft; a PR is marked ready only when its local checks pass

- **Status:** Accepted (the sre-devops-engineer owns the CI contract, ADR 0014; the PO asked for the fix on 2026-10-18).
- **Date:** 2026-10-18 (Sprint 4, ticket CI-DRAFT-SKIP)
- **Deciders:** sre-devops-engineer
- **Related:** ADR 0014 (gates fail closed), ADR 0050 (`merge_ready.py`), ADR 0030 (waiver before the commit); PO 2026-10-08 (CI first) and 2026-10-18 ("CI/CD still failed, please fix it first")

## Context

`main` is green. Every red CI run of the last day was on a pull request, and was one of two kinds:

1. **The size check ran before the EM's size-waiver decision.** `PR size (EP/ENG-04)` failed on the first push, so `ci-gate` failed although every other job was green (run 39096605529, PR #120). The same applies to `qa-approved-test-change`.
2. **A red-first TDD commit was pushed on its own** (run 39088063130, PD-4b).

Neither is a product defect. Both show a red CI to the PO for a state that the process says is not finished yet.

## Decision

1. Every job in `.github/workflows/ci.yml`, `pr-policy` and `ci-gate` included, is skipped on a `pull_request` event of a **draft** PR (`github.event_name != 'pull_request' || !github.event.pull_request.draft`). `ci-gate` keeps `always()` combined with that guard, so it still judges failed and skipped gates on every other event.
2. The `ready_for_review`, `labeled` and `unlabeled` triggers stay, so marking a PR ready (or a label change on a ready PR) starts the full run. `claude-review.yml` already skips drafts.
3. Process: a ticket PR opens as a **draft**; the size-waiver and qa-approved-test-change decisions are made while it is a draft; red-first commits are pushed together with their green commit; the PR is marked ready only when the local checks pass (`check_pr_size.py`, `check_test_immutability.py`, the touched suites).

## Consequences

- Good: a PR shows CI only once it can pass; a red run on a ready PR or on `main` is a real finding again.
- Good: gates are unchanged on ready PRs, pushes to `main`, the nightly run and manual dispatch (`infra/tests/test_ci_draft_skip.py` asserts the same job set per event as before).
- Neutral: a draft cannot be merged. GitHub refuses to merge a draft, and `merge_ready.py` needs a `ci-gate` **success** on the exact head; a skipped `ci-gate` is refused (`tests/features/ci_draft_skip.feature`).
- Bad: no CI signal while a PR is a draft. Mitigated by rule 3: the author runs the same checks locally before marking it ready.

## Evidence

- CI history (GitHub API, 2026-10-18): run 39096605529 on #120, only `PR policy` and `ci-gate` red; run 39088063130 on PD-4b, red-first head.
- Tests: `cd infra && uv run pytest -q tests/test_ci_draft_skip.py tests/test_ci_draft_skip_scenarios.py tests/test_workflows.py` → red before the change (`19 failed, 19 passed`), green after (`38 passed`).
