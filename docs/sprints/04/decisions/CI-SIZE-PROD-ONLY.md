# CI-SIZE-PROD-ONLY decisions

Per-ticket decision file (PO rule 2026-10-07). Ticket: CI-SIZE-PROD-ONLY, the PR size gate counts production code only (PO 2026-10-28). Significant decision: ADR 0053.

| Date | Who | Decision | Evidence | Why |
|---|---|---|---|---|
| 2026-10-28 | sre-devops-engineer | **Exclusions are path patterns in four named groups** (`LOCKFILES`, `FIXTURES`, `TESTS`, `DOCS`); `tests/*` (root feature files) and `*/e2e/*` (`web/e2e`) join the brief's list | `test_tests_docs_lockfiles_and_fixtures_are_excluded` (19 paths), `test_production_code_counts` (9 paths, negative case first) | Same test roots as `check_red_first.py`'s `TESTS`, so both gates agree on what a test is |
| 2026-10-28 | sre-devops-engineer | **Output keeps the prefix `pr-size: N changed lines`** and adds `of production code` and the excluded total | `test_pr_policy_scenarios.py`, `test_pr_policy_live_labels_scenarios.py` pass unchanged | Existing accepted scenarios stay byte-identical |
| 2026-10-28 | sre-devops-engineer | **One accepted-test change, TCR row raised** (`test_pr_change_set.py`) | `docs/sprints/04/test-change-requests.md` row 2026-10-28 | Its fixture PR is docs-only, so its count is now 0; the test still proves main's later lines are not counted |
| 2026-10-28 | sre-devops-engineer | **`size_decisions.py` not changed** | Its 40-line `DECISIONS_FILE_BUDGET` is now slack, since decisions files no longer count | Out of scope; keeps the PR small. Follow-up for the EM |
