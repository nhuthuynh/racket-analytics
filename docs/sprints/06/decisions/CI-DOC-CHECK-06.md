# CI-DOC-CHECK-06 decisions (sre-devops-engineer)

Story PRC-06, atomic items PRC-11.1-11.3 (`docs/sprints/06/requirements-breakdown.md`), ADR 0056 required ticket (b) extended. Review tier 1.

## 1. Decisions

| Date | Who | Decision | Evidence | Why |
|---|---|---|---|---|
| 2026-11-13 | sre-devops-engineer | **Reference citations are checked over the whole `content/references/` tree on every run**, not only the changed files | `reference_problems` in `scripts/ci/check_docs.py` | A change to `docs/domain/sources.md` that drops a row must fail even when no reference file changes (unit test `test_unchanged_reference_file_fails_when_its_source_row_goes`) |
| 2026-11-13 | sre-devops-engineer | **"Resolve" means the id is a row of the register**, nothing more. Whether a `published` value needs a `resolved` row of kind `statistic` stays with the reference lint (ST-170a), which owns the schema | `docs/domain/sources.md` §1 rule 3; sprint-06 ST-170 acceptance | One owner per rule; the doc check stays schema-agnostic and finds every `source.citation_id` at any depth (judgment) |
| 2026-11-13 | sre-devops-engineer | **The newest threat notes are run without `--topic`, `--route` or `--disclaimer`**: links, 8-cell threat rows and accepted residuals naming an Accepted ADR | `threat_notes_problems` in `scripts/ci/check_docs.py` | Topic and route lists differ per sprint and are named by the security-privacy-engineer's own gate; the generic rules hold for every notes file (judgment) |
| 2026-11-13 | sre-devops-engineer | **The cost-table rule is a separate script, `scripts/ci/check_cost_table.py`, in the pr-policy job**, not a mode of `check_docs.py` | `.github/workflows/ci.yml` step "Cost per PR table (PRC-11.3)" | pr-policy has no setup-python or PyYAML install; the script is stdlib only. It reads the table with `cost_rows` of `scripts/measure/flow_metrics.py`, so the gate and the sprint metric agree |
| 2026-11-13 | sre-devops-engineer | **A PR title without a `[TICKET-ID]` prefix is skipped**; a ticket PR without a decisions file fails | `check_cost_table.py` | Dependency bumps carry no ticket; every ticket PR has a decisions file (ADR 0056 decision 1). No label waives the rule; the step logs labels like every pr-policy step |
| 2026-11-13 | sre-devops-engineer | **The doc-check job name is unchanged** | `scripts/ci/merge_ready.py` `DOC_CHECK` | `merge_ready.py` matches the check-run name for tier 0 PRs; a rename would break merges (CI-TIERS) |
| 2026-11-13 | sre-devops-engineer | **`infra/tests/pr_checkout.py` gains the `github.event.pull_request.title` event field** ("planted policy change", no ticket id) | the harness substitutes every `${{ }}` of a pr-policy step env | Without it every pr-policy scenario raised `KeyError`; the value skips the new step, so the existing scenarios assert what they did before |

## 2. Cost per PR (ADR 0056 decision 1)

| Round | wall_time_min | total_cost_usd | Note |
|---|---|---|---|
| Author build (red, green, checks) | not measured | not measured | the session does not expose per-ticket wall time or cost to the agent |
