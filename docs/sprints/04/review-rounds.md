# Sprint 4 review rounds

Every reviewer appends one row per finding under its own heading, with the disposition **Open**, as soon as it states the finding (ADR 0033 rule 1; ADR 0050 rule 5: ids in the ledger format `<ROLE>-<TICKET>-<nn>`, e.g. `PE-ST055-01`). Owners add a later row with the new disposition (Fixed with evidence, Deferred to a named backlog row, or Rejected with a reason). The engineering-manager writes the reconciliation row of each round before the next round starts (ADR 0037 rule 1, ADR 0047 rule 1). G04-12 counts the open blocker/major rows of this file **and** of `docs/sprints/03/review-rounds.md` (`scripts/measure/open_defects.py docs/sprints/03/review-rounds.md docs/sprints/04/review-rounds.md`).

## Carried from Sprint 3 (engineering-manager, planning, 2026-10-17)

The two Sprint 3 rows still open stay in the Sprint 3 ledger (they close there, in ticket C4-G12); they are listed here so the Sprint 4 count starts from the true number. `python3 scripts/measure/open_defects.py docs/sprints/03/review-rounds.md` → rc 1, `open 2` at `c170ef0`.

| Finding | Severity | Disposition | Owner (Sprint 4) | Waits on |
|---|---|---|---|---|
| PLAN-04-CARRY-01 | minor | Open (pointer row, not a defect): PD-R1S3-01 / QA-R3S3-06 (blocker) and EM-PR27-01 (major) are open in `docs/sprints/03/review-rounds.md` lines 524-525 and are counted there; ticket C4-G12 closes them | engineering-manager | C4-G12 |

## PLAN-04 (PR #87), review round 1

| Finding | Severity | Disposition | Owner (Sprint 4) | Waits on |
|---|---|---|---|---|
| PE-PLAN04-01 | major | Fixed (engineering-manager, 2026-10-17): OQ-05..OQ-08 recorded as PO-accepted (ADR 0023) in `po-input-2026-10-05.md`, ADR 0051, sprint-04, scorecard, blockers and roadmap; P16 is now the NFR-070 legal review; S4-DoD-P7 added for the side-out rule check; `decisions/PLAN-04.md` row | engineering-manager | — |
| QA-PLAN04-01 | major | Fixed (engineering-manager, 2026-10-17): scorecard §4 G04-03, G04-06, G04-07/08 and G04-11 rewritten to the scripts' real flags; each new form run at `c8ca483` (`decisions/PLAN-04.md` row) | engineering-manager | — |
