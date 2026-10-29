# RETRO-04 decisions

Per-ticket decision file (PO rule 2026-10-07). Ticket: Sprint 4 report and retrospective (engineering-manager). Only this ticket edits the shared files `decision-log.md`, `blockers.md`, `status.json` and `progress.md` (sprint-04 header).

## Why TDD does not apply, and the checks used instead

This is a docs-only ticket. It changes no production code, no test, no scenario and no gold file, so there is no Gherkin scenario, integration test or unit test to write (testing-strategy.md; definition-of-done.md, docs-only row). Its "behaviour" is the content the close must contain. That content was written as a fail-closed check **before** any file was written, run and seen failing, then run again after the files were written:

- **RETRO-04 check:** a standard-library script kept outside the repository (scratch), because a sprint-close checklist is not a product test. It fails unless all of these hold:
  1. the report, retro, decision log, `status.json`, progress file, this file, `smoke.md` and `decisions/VERIFY-04-r3.md` exist;
  2. the report names every merged Sprint 4 PR (57, from GitHub REST), every G04 row and every S4-DoD-P row, and starts with the goal and scorecard;
  3. `status.json` parses and maps every merged PR;
  4. the retro has 1-5 actions, each with an owner and a date, and reviews B1-B5 first;
  5. the SMOKE-04 and VERIFY-04-r3 branches are ancestors of `HEAD`;
  6. the ledger has the reconciliation ids;
  7. the traceability matrix names the Sprint 4 feature files;
  8. the roadmap has the S4 close row.
- **Repository tools:** `open_defects.py` on both ledgers, `reconcile_due.py`, `merged_verdict.py` for every merged PR, `check_pr_size.py`, `check_test_immutability.py`, `check_red_first.py`, and a JSON parse of `status.json`.

## Decisions

| Date | Who | Decision | Evidence | Why |
|---|---|---|---|---|
| 2026-10-29 | engineering-manager | **Red, before writing (worktree at `origin/main` `b9d0dc3` plus the two merged evidence branches): the close is not done** | RETRO-04 check → `retro-04-check: not met (73 failures)`, rc 1, e.g. `FAIL missing docs/sprints/04/sprint-report.md`, `FAIL status.json: FileNotFoundError`, `FAIL review-rounds lacks reconciliation id QA-VERIFY04R3-01`, `FAIL traceability matrix lacks weakness_ranking.feature`, `FAIL roadmap §12 lacks the S4 close row`. `open_defects.py docs/sprints/03/review-rounds.md docs/sprints/04/review-rounds.md` → rc 1, `open 2` (the verifier findings had no rows) | Each failure is one deliverable of the brief that is missing |
| 2026-10-29 | engineering-manager | **SMOKE-04 (#159) and VERIFY-04-r3 (#160) merged into this branch unchanged**, with `git merge --no-edit origin/s04/smoke-04-sprint-close-smoke-of-main-b9d0dc3` and `origin/s04/verify-04-r3`; both PRs are closed with a pointer after this PR opens | `git log --oneline origin/main..HEAD` shows `6f7a711`, `823d70f` and two merge commits; no conflicts (different files) | ADR 0050 rule 4; keeps the verifiers' authorship |
| 2026-10-29 | engineering-manager | **Post-merge audit (ADR 0050 rule 2): 57 of 57 merged Sprint 4 PRs meet the review rule on the merged head**, and the latest `ci-gate` run on every merged head is success | `merged_verdict.py --repo nhuthuynh/racket-analytics --pr N --role principal-engineer --role <senior>` → rc 0 ×57; GitHub `commits/<head>/check-runs` latest `ci-gate` → success ×57 | B1 audit |
| 2026-10-29 | engineering-manager | **Reconciliation:** 12 Sprint 4 majors and 2 minors written from SMOKE-04 and VERIFY-04-r3; PD-R1S3-01 group Fixed in the Sprint 3 ledger; EM-PR27-01 stays Open. Alias ids `SMOKE-04-0n` were rewritten as `QA-SMOKE04-0n` / `SRE-SMOKE04-04`, because `SMOKE-04` alone parses as a finding id and joined four rows into one group (first count 10, corrected 13) | `open_defects.py` both ledgers → `open 13`; Sprint 3 ledger alone → `open 1`; Sprint 4 alone → `open 12`; `reconcile_due.py docs/sprints/04/review-rounds.md --decisions docs/sprints/04/decisions --base origin/main --report-only` → `0 open blocker/major rows, 0 due` before this section | ADR 0037 rule 1; ADR 0050 rule 5 |
| 2026-10-29 | engineering-manager | **Retro file name is `docs/retros/2026-12-11-sprint-04.md`**, not `docs/retros/sprint-04.md` as the brief says | sprint-04 header "Retro file" and §13; `ls docs/retros` → `<date>-sprint-<nn>.md` for retros 0-3 | The plan names this file, and the existing index pattern is kept (judgment) |
| 2026-10-29 | engineering-manager | **ADR 0055 accepted** (process change; the EM is R/A for sprint process, as for ADR 0050) | retro 4 M1, M2 | Retro 3 M9 repeated; a rule on evidence PRs alone did not stop it |
| 2026-10-29 | engineering-manager | **Not done here, by design:** no PR merged, closed or labelled other than closing #159/#160 with a pointer; PR #144 is left to the orchestrator (EM-RETRO04-01); no other role's cell written | — | Separation of duties (orchestrator, 2026-10-09) |
