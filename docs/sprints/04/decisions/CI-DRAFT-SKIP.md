# CI-DRAFT-SKIP decisions

Per-ticket decision file (PO rule 2026-10-07). Ticket: CI-DRAFT-SKIP, CI skips draft PRs (PO 2026-10-18 "CI/CD still failed, please fix it first"). Significant decision: ADR 0052.

| Date | Who | Decision | Evidence | Why |
|---|---|---|---|---|
| 2026-10-18 | sre-devops-engineer | **Guard every `ci.yml` job, not only `pr-policy`** | `test_every_ci_job_is_skipped_on_a_draft_pull_request` (one case per job) | Guarding only the policy job would still leave a red-first draft head red in the suites (run 39088063130) |
| 2026-10-18 | sre-devops-engineer | **Test the conditions by evaluating them (`infra/tests/workflow_if.py`), not by string match only**; the evaluator raises on any construct it does not know | `test_evaluator_refuses_an_expression_it_does_not_understand`; `test_guard_does_not_change_which_jobs_run_outside_drafts` | Proves the job set per event is unchanged outside drafts; a string check cannot |
| 2026-10-18 | sre-devops-engineer | **`claude-review.yml` unchanged** | It already has `github.event.pull_request.draft == false` and `ready_for_review` (`test_claude_review_skips_drafts_too`) | Nothing to fix |
| 2026-10-18 | sre-devops-engineer | **One accepted-test change, TCR row raised** (`test_workflows.py`, ci-gate `if`) | `docs/sprints/04/test-change-requests.md` row 2026-10-18 | The old exact `== "always()"` cannot hold once the guard is added; always() stays required |
