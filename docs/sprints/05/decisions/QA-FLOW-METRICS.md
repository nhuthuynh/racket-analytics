# QA-FLOW-METRICS decisions

Per-ticket decisions file (PO rule 2026-10-07). Ticket: `flow_metrics.py` over REST: cycle time, throughput, age, breaches, cost-row completeness; fix the working-agreement §10 command. Story PRC-05 (the process rules are enforced by checks), atomic items PRC-5.1, PRC-5.2, PRC-5.3, PRC-5.4, PRC-5.5; goal metric G05-11; ADR 0056 decisions 1 and 3. Owner: senior-qa-engineer. Review tier 1 (ADR 0056): principal-engineer, plus a senior-* test review by a role other than the author (the senior-qa-engineer cannot review its own PR, working-agreement §6).

| Date | Who | Decision | Evidence | Why |
|---|---|---|---|---|
| 2026-11-03 | senior-qa-engineer | **REST only, paged with `?page=N` until an empty page.** The script never follows GitHub's `Link` header | `gh api --paginate 'repos/nhuthuynh/racket-analytics/pulls?state=closed&per_page=100'` → HTTP 403 "Numeric-ID repository paths (repositories/{id}/...) are not supported through this proxy" after page 1; `test_script_measures_over_rest_pages_and_writes_the_json` asserts every request is a GET under `/repos/{repo}/` and that page 3 was read | The GraphQL form (`gh pr list`) returns 403 here (PLAN-05 §6 dry-run row), and so do Link URLs |
| 2026-11-03 | senior-qa-engineer | **Two durations per merged PR:** cycle time = earliest commit author date → `merged_at` (§10 definition), and time to merge = `created_at` → `merged_at` (§10 "PR time-to-merge", the sprint-report §2 "Open → merge" column) | QA dry-run below: time to merge equals sprint-report 04 §2 exactly | The card asks for the sprint-report §2 numbers, which are open → merge; §10 defines cycle time from the first commit. Both are reported, so neither is redefined |
| 2026-11-03 | senior-qa-engineer | **Throughput** = PRs with a `merged_at` into base `main` inside `--since` (inclusive) / `--until` (exclusive) and `--pr-from`/`--pr-to`. A closed PR without `merged_at` is never counted | `test_a_pr_with_no_merge_time_is_excluded_from_throughput` (the card's red-first case), `test_throughput_counts_only_merges_into_main_inside_the_window` | PRC-5.2 |
| 2026-11-03 | senior-qa-engineer | **Work item age** = now → earliest commit (PR `created_at` if it has none) for every open PR into `main`; flagged when above the window's median cycle time (§10) | `test_work_item_age_of_each_open_ticket_pr_is_named_when_over_the_median` | PRC-5.3 |
| 2026-11-03 | senior-qa-engineer | **WIP breaches** come from every line of `decisions/*.md` that reads `In progress N · in review N · awaiting QA N · awaiting merge N` (`·`, `,` or `;` between counts; any case). A count above `--wip-limits` (default 4,3,2,1, sprint-05 §2.1) is one breach; the rest of the line is its reason, or "no reason given" | `test_a_stage_count_above_its_limit_is_a_breach_with_its_reason`; scenario "A stage count above its WIP limit is a breach" | PRC-5.4; that is the form PLAN-05 uses ("Stage counts at planning") |
| 2026-11-03 | senior-qa-engineer | **CI minutes per PR** = sum of workflow-run wall time (`run_started_at` → `updated_at`) of `actions/runs?event=pull_request` on the PR's head branch, started between open and merge. Not billable minutes: the per-run `/timing` call would cost one request per run | `test_ci_minutes_per_pr_sum_its_branch_runs_between_open_and_merge` | Card: "CI minutes per PR"; cost of the read (judgment) |
| 2026-11-03 | senior-qa-engineer | **Cost-table completeness:** a merged PR's ticket id is its title's `[ID]` prefix; it is complete when `decisions/<ID>.md` has a table with at least one data row under a heading containing "Cost per PR". Rows containing "not measured" are listed. **Exit 0 complete, 1 a merged ticket has no table, 2 GitHub unreadable or bad arguments** (fail closed, ADR 0014). Values are reported, never targets [ASB/AGL-02] | `test_cost_table_completeness_names_missing_tables_and_not_measured_rounds`, `test_the_report_is_complete_only_when_every_merged_ticket_has_a_cost_table`, `test_script_exits_1_when_a_merged_ticket_has_no_cost_table`, `test_script_exits_2_when_github_cannot_be_read` | PRC-5.5; G05-11's only target is "measured and complete" |
| 2026-11-03 | senior-qa-engineer | **Commits are read only for PRs in the window** (added after the first live run took over 120 s paging the commits of every merged PR) | Red: `test_script_reads_commits_only_for_prs_in_the_window` → 1 failed (`/pulls/8/commits` read for a PR merged before `--since`); green after refactor `cf0088d5`; live run then 13.8 s | Run time |
| 2026-11-03 | senior-qa-engineer | **Working-agreement §10:** the `gh pr list ... createdAt,mergedAt` command is replaced by the `flow_metrics.py` call (one line) | `test_working_agreement_section_10_calls_the_script_not_graphql` | SRE-2 kickoff item |
| 2026-11-03 | senior-qa-engineer | **QA-FLOWMETRICS-01 (minor):** the live G05-11 method finds 8 of the 9 Sprint 5 PRs merged so far without a cost table (#183 DOCS-RES-01, #184 DOCS-PROC-01, #185 DOCS-ROLES-01, #187 CI-NOTICE-CANCELLED, #188 CI-TIERS-a, #189 CI-DOC-CHECK, #190 QA-TCR-04, #191 CI-RECON-ON-PR); only PLAN-05 has one. Owner: engineering-manager (backfill each table, uncaptured rounds as "not measured", before VERIFY-05). If not backfilled, G05-11 is "no" at VERIFY-05 | Live method below → rc 1, "cost tables: 1 of 9 merged tickets" | Reported, not fixed: those files belong to other tickets. Rated minor because a backfill closes it and no product behaviour is affected (judgment); the EM re-rates it at the status step if it is still open at VERIFY-05 |

## TDD (red first)

| Step | Commit | Command | Result |
|---|---|---|---|
| Red | `2ef3caf2` | `cd infra && uv run --no-sync pytest -q -p no:cacheprovider tests/test_flow_metrics.py tests/test_flow_metrics_scenarios.py` | 17 failed: `FileNotFoundError: ... scripts/measure/flow_metrics.py`; `assert 'gh pr list' not in ...` (§10) |
| Green | `759f7773` | same | 17 passed |
| Red (window reads) | `c3c30d19` | `... tests/test_flow_metrics.py -k only_for_prs` | 1 failed (`/pulls/8/commits` read) |
| Refactor, green | `cf0088d5` | same as Red | 18 passed |

## QA dry-run against Sprint 4's PR range (card QA step)

`SSL_CERT_FILE=/root/.ccr/ca-bundle.crt python3 scripts/measure/flow_metrics.py --repo nhuthuynh/racket-analytics --pr-from 87 --pr-to 158 --decisions docs/sprints/04/decisions --json reports/flow04.json` → rc 1 (no Sprint 4 ticket had a cost table; the rule is new in Sprint 5).

| Value | flow_metrics.py | sprint-report 04 §2 | Equal |
|---|---|---|---|
| Merged PRs (throughput) | 57 | 57 | yes |
| Open → merge median | 2.2 h | 2.2 h | yes |
| Open → merge mean | 7.7 h | 7.7 h | yes |
| Open → merge max | 252.2 h | 252 h (ST-066 #147) | yes |
| Cycle time (first commit → merge) | median 2.6 h, max 255.8 h (ST-065 #152) | not reported | n/a |
| CI minutes (workflow-run wall time) | 1696.5 over 57 PRs | not reported | n/a |

## Traceability (PRC-5.1-5.5 → scenario → test)

The matrix in `docs/requirements/traceability-matrix.md` is written per sprint at the close (RETRO-05); these rows are its input.

| Item | Scenario (`tests/features/flow_metrics.feature`) | Tests (`infra/tests/`) |
|---|---|---|
| PRC-5.1 cycle time, REST only | — | `test_flow_metrics.py::test_cycle_time_runs_from_the_earliest_commit_to_the_merge`, `::test_a_merged_pr_without_commits_has_no_cycle_time_and_is_named`, `::test_script_measures_over_rest_pages_and_writes_the_json` |
| PRC-5.2 throughput | "A pull request closed without a merge is not throughput" | `::test_a_pr_with_no_merge_time_is_excluded_from_throughput`, `::test_throughput_counts_only_merges_into_main_inside_the_window` |
| PRC-5.3 work item age | — | `::test_work_item_age_of_each_open_ticket_pr_is_named_when_over_the_median` |
| PRC-5.4 WIP breaches | "A stage count above its WIP limit is a breach" | `::test_a_stage_count_above_its_limit_is_a_breach_with_its_reason` |
| PRC-5.5 cost-table completeness | "A merged ticket without a cost table makes the measurement incomplete"; "GitHub cannot be read" | `::test_cost_table_completeness_names_missing_tables_and_not_measured_rounds`, `::test_the_report_is_complete_only_when_every_merged_ticket_has_a_cost_table`, `::test_script_exits_1_when_a_merged_ticket_has_no_cost_table`, `::test_script_exits_2_when_github_cannot_be_read` |
| CI minutes per PR (card) | — | `::test_ci_minutes_per_pr_sum_its_branch_runs_between_open_and_merge` |

## Stage counts

In progress 1 · in review 0 · awaiting QA 0 · awaiting merge 0. QA-FLOW-METRICS goes into review once ready.

## Cost per PR (ADR 0056 decision 1)

| Round | Wall time (min) | total_cost_usd / tokens |
|---|---|---|
| Author build | about 50 | not measured (this invocation does not expose `total_cost_usd`) |
