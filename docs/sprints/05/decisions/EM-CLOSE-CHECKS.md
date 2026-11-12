# EM-CLOSE-CHECKS decisions

Per-ticket decisions file (PO rule 2026-10-07). Ticket: `retro_ready.py` (RETRO trigger) and `retro05_check.py` (PR set = status map; open causes) under `docs/sprints/05/close-checks/`. Story PRC-05 (the process rules are enforced by checks), atomic items PRC-6.1, PRC-6.2, PRC-6.3; goal metric G05-12; retro 4 F1 and F3 (lessons L22, L23, L24); kickoff EM-1 and EM-10. Owner: engineering-manager. Review tier 1 (ADR 0056; the scripts are executable, so the executable floor makes them tier 1, CI-TIERS-a): principal-engineer, plus the senior-qa-engineer test review.

| Date | Who | Decision | Evidence | Why |
|---|---|---|---|---|
| 2026-11-12 | engineering-manager | **`retro_ready.py` is the RETRO-05 trigger (PRC-6.1).** Ready only when (a) a VERIFY-05 PR is merged into `main`, (b) no VERIFY-05 PR is open, and (c) the latest ledger row of every VERIFY-05 finding (`<ROLE>-VERIFY05R<n>-<nn>`, scorecard §3 rule 4) starts with "Fixed". A VERIFY-05 PR is one whose title starts with `[VERIFY-05` or whose head branch starts with `s05/verify-05`. A VERIFY PR closed without a merge does not count as merged. Exit 0 ready, 1 not ready (each reason printed), 2 unknown | `test_a_planted_open_verify_pr_makes_the_retro_not_ready`, `test_no_merged_verify_pr_makes_the_retro_not_ready`, `test_a_verify_finding_whose_latest_row_is_not_fixed_makes_the_retro_not_ready` (4 dispositions incl. Deferred and empty), scenarios 1-3 of `tests/features/close_checks.feature` | Retro 4 M16 root: the close was triggered by "all tickets merged". (a) follows ADR 0055 rule 3 (the VERIFY PR is always merged); "Deferred" is not Fixed because PRC-6.1 says "not Fixed" (fail closed, ADR 0014) |
| 2026-11-12 | engineering-manager | **Orchestrator step:** before briefing RETRO-05 the orchestrator runs `python3 docs/sprints/05/close-checks/retro_ready.py --repo nhuthuynh/racket-analytics --ledger docs/sprints/05/review-rounds.md` on a fresh fetch of `main` and briefs RETRO-05 only on rc 0. rc 1 routes the printed reasons to their owners; rc 2 is re-run, never read as ready | Live dry-run below → rc 1 today | Kickoff EM-1; goal-scorecard "Order" |
| 2026-11-12 | engineering-manager | **PR set (PRC-6.2):** the Sprint 5 set is every PR merged into `main` whose head branch starts with `s05/` (`--prefix`, repeatable, e.g. `--prefix s05/ --prefix docs/` when a `docs/<slug>` bootstrap PR merged inside the sprint). It must equal the `status.json` `ticket_prs.map` rows with `merged: true` (Sprint 4 shape). Both differences are printed: `on GitHub, not in status.json: #n` and `in status.json, not merged on GitHub: #n`. A map that is missing or has a row without an integer `pr` → rc 2 | `test_a_planted_extra_pr_on_github_is_printed_as_a_set_difference`, `test_sprint_set_is_merged_into_main_from_sprint_branches_only`, `test_a_status_file_without_a_readable_map_is_refused` | Retro 4 M17 / L23: a count difference is explained by the set difference, never by reasoning. Branch prefix, not a date window: every Sprint 5 ticket branch is `s05/<id>` (working-agreement §5) |
| 2026-11-12 | engineering-manager | **Open causes (PRC-6.3), cause format for RETRO-05:** every `blockers.md` row whose Status cell contains the word "open" (any case) names its causes in one cell after `Cause:` or `Causes:`. Allowed causes: `#n` (open while the GitHub issue or PR state is `open`), a ledger finding id (open while its latest row starts with Open, Not fixed, Not re-verified or Partly; an id the ledger does not hold fails), `P<n>` (a PO item) or `setting <n>` (an admin setting). An Open row that names no cause fails. `P<n>` and `setting <n>` are human items whose answer no API shows, so the check treats them as open; the RETRO's PO-list row is the place that records an answer | `test_a_planted_closed_cause_on_an_open_blocker_row_fails`, `test_an_open_row_that_names_no_cause_fails_closed`, `test_a_ledger_finding_cause_is_open_only_while_its_latest_row_is_open`, `test_a_ledger_cause_that_the_ledger_does_not_hold_fails_closed`, `test_a_po_item_cause_counts_as_open` | Retro 4 M18 / L24: a row stayed Open after #162 fixed its cause. Sprint 4 rows named causes only in prose, so an explicit marker is the smallest rule a script can check (judgment) |
| 2026-11-12 | engineering-manager | **One close (G05-12 "1 RETRO PR"):** at most one PR whose head starts with `s05/retro-05` is merged or open; a RETRO PR closed without a merge does not count | `test_a_second_retro_pr_fails_the_one_close_rule` | Retro 4 M16 (four close PRs in one sprint) |
| 2026-11-12 | engineering-manager | **REST only**, paged with `?page=N` until an empty page; no GraphQL and no `Link` header (both refused by the agent proxy, `decisions/QA-FLOW-METRICS.md`). Shared helpers in `docs/sprints/05/close-checks/closelib.py`; scripts stay in the close-checks folder as the plan's Dirs say | `test_retro_ready_exits_1_on_a_planted_open_verify_pr` asserts every request is a GET under `/repos/{repo}/` and that page 2 was read | Same proxy limits as G05-11 |
| 2026-11-12 | engineering-manager | **EM-CLOSECHECKS-01 (minor, Open):** the third line of the scorecard §4 G05-12 block, `merged_verdict.py --pr $n --tiered`, cannot run: `merged_verdict.py` has no `--tiered` flag and requires `--repo` and `--role` (`python3 scripts/measure/merged_verdict.py --pr 225 --tiered` → argparse usage error). Not changed here: a tiered post-merge verdict check reuses `merge_ready.py`'s tier rules (tier 2 code). Owner: engineering-manager, who opens an `s05/owners-` row and a fix ticket before VERIFY-05; until then the verifier runs `merged_verdict.py --repo … --pr $n --role principal-engineer --role senior-qa-engineer` per tier 1 PR and records it as a method deviation | Command and output above | A method that does not run is a finding, not a pass (scorecard §3 rule 2) |

## TDD (red first)

| Step | Commit | Command | Result |
|---|---|---|---|
| Red | `d2e98acc` | `cd infra && uv run --no-sync pytest -q -p no:cacheprovider tests/test_close_checks.py tests/test_close_checks_scenarios.py` | `40 failed`: 27 × `FileNotFoundError: … docs/sprints/05/close-checks/retro05_check.py` / `retro_ready.py`; 13 subprocess runs `can't open file … [Errno 2] No such file or directory` (rc 2) |
| Green | `a7d5637e` | same | `40 passed` |
| Lint, format, types | `a7d5637e` | `infra/.venv/bin/ruff check` and `ruff format --check` on the 6 files (root `ruff.toml`); `uv run --no-sync --with mypy==1.13.0 mypy --strict ../docs/sprints/05/close-checks/` | `All checks passed!`, `6 files already formatted`; `Success: no issues found in 3 source files` |

## Dry runs (live GitHub, 2026-11-12, head `a7d5637e`)

| Command | rc | Result |
|---|---|---|
| `retro_ready.py --repo nhuthuynh/racket-analytics --ledger docs/sprints/05/review-rounds.md` | 1 | `FAIL no merged VERIFY-05 PR`; correct today (VERIFY-05 has not run); 2.9 s |
| The §4 G05-12 `retro05_check.py` line as written | 2 | `No such file or directory: 'docs/sprints/05/status.json'`; RETRO-05 writes `status.json` and `blockers.md` |
| `retro05_check.py` with a scratch `status.json` built from the 35 merged `s05/` PRs (#186-#233) and a scratch `blockers.md` (`Cause: #234`, open; `Causes: P9, P16, setting 6`) | 0 | `retro05-check: met (35 merged PRs equal the status map; Open causes open)` |
| Planted: the same map without #233, and an Open row with `Cause: #233` (merged) | 1 | `FAIL on GitHub, not in status.json: #233`; `FAIL blockers line 3: Open row names #233, which is closed on GitHub` |
| `python3 scripts/measure/open_defects.py docs/sprints/05/review-rounds.md` | 1 | `open 5`: SEC-S5-TM-01, SEC-S5-TM-02, COACH-S5-01, COACH-S5-05, PD-DR04-01 (owned by their tickets) |

## Traceability (PRC-6.1-6.3 → scenario → test)

| Item | Scenario (`tests/features/close_checks.feature`) | Unit / integration test (`infra/tests/test_close_checks.py`) |
|---|---|---|
| PRC-6.1 | An open VERIFY PR keeps the retro from starting; A VERIFY finding that is not Fixed …; The retro starts once … | `test_a_planted_open_verify_pr_makes_the_retro_not_ready`, `test_retro_ready_exits_1_on_a_planted_open_verify_pr`, `test_retro_ready_exits_0_when_verify_is_merged_and_its_findings_fixed` |
| PRC-6.2 | A merged Sprint 5 PR missing from the status map fails the close | `test_a_planted_extra_pr_on_github_is_printed_as_a_set_difference`, `test_retro05_check_exits_1_on_a_planted_extra_pr_and_a_planted_closed_cause` |
| PRC-6.3 | An Open blocker row whose cause is closed fails the close; The close is met when … | `test_a_planted_closed_cause_on_an_open_blocker_row_fails`, `test_retro05_check_exits_0_when_the_close_is_consistent` |
| fail closed | GitHub cannot be read | `test_retro_ready_exits_2_when_github_or_the_ledger_cannot_be_read`, `test_retro05_check_exits_2_when_github_cannot_be_read_or_status_is_bad` |

## Cost per PR (ADR 0056 decision 1)

| Round | Wall time (min) | total_cost_usd / tokens |
|---|---|---|
| Author build (read, tests, scripts, dry runs) | 70 | not measured |
