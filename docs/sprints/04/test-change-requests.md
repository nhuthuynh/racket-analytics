# Sprint 4 test change requests

Changes to existing (accepted) tests or test support. A row raised outside the senior-qa-engineer lane needs a QA decision before the change is committed (PR label `qa-approved-test-change`, applied only by the QA decision step; ADR 0014). QA's own changes to accepted tests are logged here too. Append only; only the "QA decision" cell of an existing row may be filled in later. Ticket PRs add their rows here **only** when they change an accepted test (this file is the one shared Sprint 4 file a ticket PR may append to, because the merge gate reads it; the DOCS/RETRO ticket does not rewrite rows).

| Date | Raised by | Ticket | File | Change | Why (evidence) | Weakens a check? | QA decision |
|---|---|---|---|---|---|---|---|
| 2026-10-17 | senior-qa-engineer | C4-RECON | `infra/tests/test_reconcile_due.py` (`test_main_stays_green_after_a_fix_ticket_named_after_an_open_finding_merges`) | Docstring only: says the case relies on the latest ledger row for an id winning over the real ledger's earlier Fixed row (QA-RETRO03-03, deferred from PR #82) | PR #82 review 5532651129 (QA-RETRO03-03 nit); `git diff origin/main -- infra/tests/test_reconcile_due.py` → one docstring line changed, the rest additions | No: no assertion, input or marker changed | **Accepted** (senior-qa-engineer, 2026-10-17; QA's own change, logged) |
