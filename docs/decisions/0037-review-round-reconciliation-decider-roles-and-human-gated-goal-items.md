# 0037. A review round closes only when every finding has a row; decider roles get scheduled briefs; goal items that need a human input are agreed with the PO at planning

- **Status:** Accepted (the engineering-manager is R/A for sprint process, working-agreement §4). Applies from Sprint 3 planning. The human product owner may veto it at the Sprint 2 review on 2026-11-13.
- **Date:** 2026-10-06 (Sprint 2 close, retro 2)
- **Deciders:** engineering-manager
- **Consulted:** Sprint 2 review rounds 1-3 (principal-engineer, security-privacy-engineer, senior-qa-engineer, principal-designer) and goal verification rounds 1-3 (senior-qa-engineer, sre-devops-engineer)
- **Related:** ADR 0033 (rule 1 extended, not replaced), ADR 0030, ADR 0022, ADR 0014; working-agreement §7; retro `docs/retros/2026-11-13-sprint-02.md` (M1-M3); `docs/sprints/02/sprint-report.md` §1.2

## Context and problem statement

Sprint 2 met 11 of 12 goal metrics live. It failed only on G02-11 (open findings). Three process gaps caused the failure:

1. **Findings again left the loop without a row (repeat of Sprint 1 M10).** ADR 0033 rule 1 says that each reviewer writes its own Open row. In review round 3 (at `db0f0be`), no reviewer did so. Two of them said they cannot write files (security-privacy-engineer, principal-designer). The round ran in parallel with goal verification round 1, and no EM status step followed it. Goal rounds 1-3 counted 2 open. At the close the EM wrote the missing rows, and the count became 14 (`open_defects.py` rc=1, open 14). Among them were a test-immutability blocker (QA-RV3-02) and a wrong-behaviour major (PE-S2-R3-01). The counter also skipped a routed table that had no disposition column (PD-R3S2-04, fixed in `b0e7cbb`).
2. **Decider roles never ran.** DR-01 and DR-02 need decisions from the senior-frontend-engineer, pickleball-domain-coach, business-analyst, product-manager and security-privacy-engineer. The orchestrator's lanes (sprint-02 §15) contain only the five build roles. The docs roles were never invoked with a brief, so their cells stayed empty through 6 rounds (6 of the 14 open rows). The UI stories were built before the flows existed, which is the Sprint 1 M8 pattern again.
3. **A goal item that only a human can close was committed to the goal.** C-06 (VoiceOver/TalkBack pass) waits on PO item P6, which is due on the planned review date, 2026-11-13. The sprint ran in a compressed session on 2026-10-05/06, so that goal bullet could not close in the session, however good the product was.

## Decision drivers

- Absent means open (fail closed, ADR 0014; ADR 0033 rule 1). The rule must work when a reviewer cannot write files.
- A decision that has no scheduled owner run does not happen (judgment, from 6 rounds of empty cells).
- The PO standing rule stays unchanged. Goal items are not relabelled; what changes is what is agreed at planning.

## Considered options

1. **Three rules** (below). Chosen.
2. Keep ADR 0033 and remind the reviewers. Rejected: it failed twice, and two reviewers cannot write files.
3. Let the EM fill other roles' decision cells. Rejected: it breaks the flows §10.3 rule and RACI. The EM schedules decisions; it does not make them.
4. Drop human-gated items from the goal on the EM's own authority. Rejected: that is a scope change, which goes through the PO (EP/ENG-22).

## Decision

1. **Reconcile before the next step.** A review or verification round ends with an EM reconciliation step. The orchestrator saves each reviewer's returned finding list. The EM checks that every returned finding id has a row in `review-rounds.md` with a severity and a disposition column, and writes an Open row, attributed to the reviewer, for any id that is missing. Goal verification and the next review round start only after this step. The step's evidence is the `open_defects.py` output together with the number of returned ids and the number of rows written.
2. **Decider roles are scheduled like lanes.** The sprint plan lists every design-review and decision cell as a task with a role, a brief written by the EM, and a date. The orchestrator invokes each such role at that date, in the same way as a build lane. A UI story whose flows are not approved does not start, unless the PO records a waiver before the work begins (DoR R6/R7).
3. **Human-gated goal items are agreed at planning.** If a goal bullet or metric depends on a PO item (a human, devices, files) whose need-by date falls after the planned session ends, the EM asks the PO at planning to choose one of two options: supply the input before the close, or move the item out of the goal into a named sprint-DoD row that is reported as "not met: waiting on P-n". The EM records the PO's answer in the plan. Without an answer, the item stays in the goal.

## Consequences

- One extra EM step per round (minutes). It removes the "2 → 14" surprise at the close.
- The orchestrator needs one more lane type (decider roles). This costs tokens, which is cheaper than six rounds of carried blockers (judgment).
- The goal stays honest: nothing is waived, but the PO decides ahead of time what a compressed session can close.

## Evidence

- `python3 scripts/measure/open_defects.py docs/sprints/02/review-rounds.md` at the close → rc=1, open 14, and the verifier's count was 2 (`goal-scorecard.md` §9.1).
- `review-rounds.md` "Sprint close: engineering-manager" table: the round-3 ids and their re-checks.
- `flows-sprint-02.md` §13.1: Decision cells R2-2..R2-7 are empty; `flows-sprint-01.md` §10.1 says "pending" for each named role.
- `blockers.md` row 1: P6 is due 2026-11-13, and the session ended 2026-10-06.

## Applied in

- `docs/process/working-agreement.md` §7 step 3d (new) and step 2 (note).
- `.claude/agents/engineering-manager.md` responsibilities.
