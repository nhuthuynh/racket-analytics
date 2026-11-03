# PD-DR04 decisions

Per-ticket decision file (PO rule 2026-10-07). Ticket: collect the five DR-04 decider cells on the shipped Sprint 4 screens, or a PO waiver request; re-read pending DR-01..03 cells. Owner: principal-designer (chair). Output: `docs/design/flows-sprint-04.md` §14.2-§14.6. Append only.

| Date | Who | Decision | Evidence | Reasoning |
|---|---|---|---|---|
| 2026-11-03 | principal-designer | **TDD does not apply** (text and decisions, no executable behaviour). The gate check runs before and after: `check_flows.py … --review DR-04 --decider <five roles>` rc 1 both times (cells still pending), `--opened <five roles>` rc 0 | `docs/design/tools/check_flows.py` | The tool turns green only when the deciders write their cells; the chair does not write them (ADR 0037 rule 2) |
| 2026-11-03 | principal-designer | **Cells not collected; the deciders could not be reached; a PO waiver request is written (§14.5) for EM-ESC-05 to carry, recommending a hold by 2026-11-05** | `ListAgents` → "No reachable agents"; no branch changes the file | Retro-04 M5: cells left to other roles were never invoked; escalating the same day stops a fourth sprint of drift |
| 2026-11-03 | principal-designer | **Three shipped-vs-spec gaps become ledger rows now (PD-DR04-01 major, -02 and -03 minor), not after the deciders' cells** | `flows-sprint-04.md` §14.4; ST-071 and ST-068b decision files | Retro-04 M3: a known gap with no ledger row became a goal miss. The rows are the chair's findings, not reject cells |
| 2026-11-03 | principal-designer | **DR-01..DR-03 have no pending cell** | §14.6 grep | All three held (2026-10-10, 2026-10-17) |
