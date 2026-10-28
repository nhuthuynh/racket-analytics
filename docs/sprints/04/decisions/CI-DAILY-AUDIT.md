# CI-DAILY-AUDIT decisions

Per-ticket decision file (PO rule 2026-10-07). Ticket: CI-DAILY-AUDIT, a daily dependency audit opens an upgrade PR before main goes red (PO 2026-10-28). Significant decision: ADR 0053 (draft PR, a reviewer marking it ready starts CI).

| Date | Who | Decision | Evidence | Why |
|---|---|---|---|---|
| 2026-10-28 | sre-devops-engineer | **The job also has `issues: write`** (scope named `contents` and `pull-requests` only) | `test_the_workflow_token_can_only_push_a_branch_edit_a_pull_request_and_an_issue` | The same scope asks for an issue when an advisory has no fix version; creating an issue needs it. Workflow-level `permissions: {}` |
| 2026-10-28 | sre-devops-engineer | **No `ci.yml` dispatch, no PAT**: the PR is a draft and the reviewer marking it ready starts CI | ADR 0053 | A dispatch run accepts a skipped `pr-policy` in `ci-gate`, and needs `actions: write`; no PAT exists in the repo |
| 2026-10-28 | sre-devops-engineer | **Merge `origin/main` into `deps/security-audit`, never force-push**; on a lock conflict take main's locks and re-upgrade | `test_workflow_never_force_pushes_the_upgrade_branch` | Never-force-push rule; the lock is regenerated anyway |
| 2026-10-28 | sre-devops-engineer | **Web critical advisories go into the issue, not an automatic upgrade** | `test_issue_body_lists_unfixed_python_and_critical_web_advisories` | Scope: upgrades are for Python packages; a Next.js upgrade needs the web suites and a human |
| 2026-10-28 | sre-devops-engineer | **Check that the lock really moved**; a package uv could not move goes into the issue as "still locked" | `test_main_reports_a_package_uv_could_not_move_in_the_issue` | A constraint can hold a package back; the PR must not claim a fix it does not contain |
| 2026-10-28 | sre-devops-engineer | **infra is audited with its dev group** (`uv export` without `--no-dev`) | `test_the_workflow_audits_with_the_same_pipaudit_command_as_ci` | infra has only a dev group (test tools); `--no-dev` would audit nothing |
| 2026-10-28 | sre-devops-engineer | **Same pip-audit export and `--strict` as ci.yml, JSON output**; the script fails closed (exit 2) on a missing or unreadable report | `test_a_broken_pip_audit_report_is_refused`, `test_main_fails_closed_on_a_missing_report`, scenario "A missing audit report fails the job" | ADR 0014: fail closed |
