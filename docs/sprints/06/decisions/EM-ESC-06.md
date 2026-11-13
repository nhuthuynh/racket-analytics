# EM-ESC-06 decisions

This is the per-ticket decision file (working-agreement §3, "Daily sync").

- **Ticket:** EM-ESC-06, "PO escalation: P21 (S6/S7 order), P22 (secondary statistics), the '...' question, P11/P15/P16/P7/P19 re-asks with dated defaults, D1, Full Tag for players (A3)" (`docs/sprints/sprint-06.md` §3.2).
- **Owner:** engineering-manager. **Review tier:** 0 (ADR 0056): one fresh-context reviewer plus the automated doc checks.
- **Output:** `docs/sprints/06/po-escalations.md`. Assumptions covered: A-Q1 (Q1), A-Q2 (P21), A3 (Q4), A5 (P22).

**TDD does not apply.** The ticket writes an escalation note and no executable behaviour, so there is no failing test to write first. Doc checks run instead.

## 1. Decisions

| Date | Role | Decision | Evidence | Reason |
|---|---|---|---|---|
| 2026-11-13 | engineering-manager | **Each question asked once.** P8, P9, P6, P10, P17, P18 and P20 are not repeated; the note points to EM-ESC-05 for them | sprint brief ("each question is asked once"); `docs/sprints/05/po-escalations.md` | Two copies of one question drift |
| 2026-11-13 | engineering-manager | **P21 uses the PE's three options (port first, slice first, strangler)** from kickoff PE-2 and §5 item 1. The PE named the options but wrote no numbers, so the EM measured the cost figures at `origin/main` `91a58c78` and lists the commands; the principal-engineer is asked to confirm them in review | `docs/sprints/06/kickoff.md` PE-2, §5 item 1; commands in po-escalations P21 "Evidence" | Costs must be measured, not estimated (retro-02 L5) |
| 2026-11-13 | engineering-manager | **P21 default does not record the 2026-10-06 decision as changed.** The team proceeds with B, and roadmap S7 keeps "if P21 confirms the re-plan" | po-input "Orchestrator note (2026-11-12) … not a PO decision"; ADR 0047 | Only the PO changes a PO decision |
| 2026-11-13 | engineering-manager | **Q1 options are labelled as examples, not the team's reading of "..."**; the default adds nothing | requirements-breakdown §6 A-Q1 ("the team adds nothing") | The PO's words are never expanded |
| 2026-11-13 | engineering-manager | **Need-by dates:** P21, P22, D1 2026-11-17 (Wave 1 merge-by); P15, P7 2026-11-24 (sprint-06 §0.4 for P15; P7 aligned so COACH-6c can cite it); Q1, Q4, P19 2026-11-26 (last in-session date, so S7 planning has them); P11 S8 planning; P16 before any real user or real-person footage | sprint-06 §0.4, §3.6 | Earliest date a dependent ticket needs the answer |
| 2026-11-13 | engineering-manager | **P15 and P7 keep the coach's options and recommendations from `docs/domain/po-fallback-p7-p15.md`** with Sprint 6 scope added (reference entries, rule-dependent patterns) | that file; `find content/drills -name '*.json' -exec grep -h '"review_status"' {} +` → 32 coach-reviewed, 5 draft, 0 verified | The coach owns the domain fallback |
| 2026-11-13 | engineering-manager | **D1 carried unchanged from EM-ESC-05**, with the 2026-11-12 state | `docs/design/flows-sprint-04.md` §14.7 | Default applied; question still open |

## 2. Cost per PR (ADR 0056 decision 1)

| Round | wall_time_min | total_cost_usd / tokens |
|---|---|---|
| Author build | not measured | not measured |

## 3. Doc-check record

See the PR description ("Test evidence") for the commands and results.
