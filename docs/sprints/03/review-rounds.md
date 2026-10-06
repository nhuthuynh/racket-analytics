# Sprint 3 review rounds

Every reviewer appends one row per finding under its own heading, with the disposition **Open**, as soon as it states the finding (ADR 0033 rule 1; working-agreement §7 step 2). Owners add a later row with the new disposition (fixed with evidence, deferred to a named backlog row, or rejected with a reason the reviewer accepts). The last row naming an id wins. After every review or verification round the engineering-manager reconciles the reviewers' returned ids against this file and writes an Open row for any id that has none, before the next step starts (ADR 0037 rule 1; working-agreement §7 step 3d). Count: `python3 scripts/measure/open_defects.py docs/sprints/03/review-rounds.md` (goal scorecard G03-12).

## Carried from Sprint 2 (engineering-manager, planning, 2026-10-06)

The 14 blocker/major rows still open at the Sprint 2 close (`python3 scripts/measure/open_defects.py docs/sprints/02/review-rounds.md` → rc=1, `open 14`, at `ce91984`). They are copied here, one row per id as the counter lists them, so the Sprint 3 count starts from the true number (retro 2 M1; decision-log 2026-10-06). The Sprint 2 rows stay the history; this table is where their next disposition is written.

| Finding | Severity | Disposition | Owner (Sprint 3) | Waits on |
|---|---|---|---|---|
| QA-RV3-02 | blocker | Open (carried). TCR rows 24-28 of `docs/sprints/02/test-change-requests.md` have no QA decision (ADR 0014). Row C3-01, first in the QA lane | senior-qa-engineer | — |
| PE-S2-R3-02 | major | Open (carried). `api-sprint-02.md` §3/§4.2 and `match-aggregate.md` §4/§8 do not state `not_last_in_game` or "latest kept rally first". Row C3-02 (task PE-4, D1) | principal-engineer | — |
| PE-S2-R3-01 | major | Open (carried). S-01 offers "Move rally n to the next game" on rows the server refuses with `decision/not_last_in_game`. Row C3-03, red first, after C3-02 | senior-frontend-engineer | C3-02 |
| PE-S2-R3-03 | major | Open (carried). No CI run covers the Sprint 2 close head. Row C3-05 (CI at the head, smoke, merge chain; retro 2 A4) | sre-devops-engineer with the orchestrator | PO labels and merge (C3-01 first) |
| QA-RV3-04 | major | Open (carried). `scripts/dev-chrome.sh` (ADR 0036 residual) does not exist. Row C3-04 | sre-devops-engineer | — |
| QA-R3-GATE-01 / C-06 | major | Open (carried). Manual VoiceOver/TalkBack pass (NFR-027 b), 0 of 24 rows run. Row C3-06; human-gated (sprint-03 §0.4) | senior-qa-engineer with a human tester | PO item P6 |
| SEC-RV3-01 | major | Open (carried). Repository visibility: GitHub says public, the PO record's correction said private (since retracted). Row C3-07; human-gated | human PO; engineering-manager (record) | PO item P10 |
| BLK-GOLD-01 | major | Open (carried). No private bucket or access policy for footage that shows people. Row C3-08; human-gated | sre-devops-engineer, security-privacy-engineer | PO item P11 |
| PD-R1-06 / PD-R2R-02 / QA-R2V-12 / DR-02 / DR-01 / PE-S2-R3-06 | blocker | Open (carried). The Sprint 1 and Sprint 2 flows design reviews are not held. Row C3-09: decider tasks DR-01 and DR-02 on D1 (sprint-03 §3.3) | principal-designer (chair) | the deciders' briefs on D1 |
| PD-RV2-DR-FE | blocker | Open (carried). Decider cells R2-2 and R2-5 of `flows-sprint-02.md` §13.1. Task DR-02-FE, D1 | senior-frontend-engineer | — |
| PD-RV2-DR-COACH | blocker | Open (carried). Decider cells R2-4 and R2-7. Task DR-02-COACH, D1 | pickleball-domain-coach | — |
| PD-RV2-DR-BA | blocker | Open (carried). Decider cell R2-3. Task DR-02-BA, D1 | business-analyst | — |
| PD-RV2-DR-PM | blocker | Open (carried). Decider cells R2-5 and R2-7. Task DR-02-PM, D1 | product-manager | — |
| PD-RV2-DR-SEC | major | Open (carried). Decider cell R2-6. Task DR-02-SEC, D1 (if the reviewer cannot write files, the chair commits its text, attributed) | security-privacy-engineer | — |

Minors and nits deferred at the Sprint 2 close (PE-S2-R3-07/-08/-09, SEC-RV3-02/-03/-04, SEC-S2-TM-03-DOC/-04/-05/-07, QA-RV3-06, PD-R3S2-01/-02, PD-FL2-03/-05, VR1-01) keep their Sprint 2 "Deferred" rows; they are sprint-03 row C3-10 and are not counted by G03-12.

## Reconciliation log (engineering-manager, ADR 0037 rule 1)

One row per review or verification round: the ids each reviewer returned, the rows found, the rows written, and the `open_defects.py` count. Goal verification and the next round start only after the row exists.

| Round | Head | Reviewers | Returned ids | Rows already present | Open rows written by the EM | `open_defects.py` |
|---|---|---|---|---|---|---|
| Planning | `ce91984` | — (carry-over) | 14 (Sprint 2 close) | 0 | 14 (table above) | rc=1, open 14 (`python3 scripts/measure/open_defects.py docs/sprints/03/review-rounds.md`) |
