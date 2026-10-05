# Sprint 2 review rounds

Every reviewer appends one row per finding under its own heading, with the disposition **Open**, as soon as it states the finding (ADR 0033 rule 1; working-agreement §7 step 2). Owners add a later row with the new disposition (fixed with evidence, deferred to a named backlog row, or rejected with a reason the reviewer accepts). The last row naming an id wins. Count: `python3 scripts/measure/open_defects.py docs/sprints/02/review-rounds.md` (goal scorecard G02-11).

## Carried from Sprint 1 (engineering-manager, planning, 2026-10-05)

The 17 blocker/major families still open at the Sprint 1 close (`python3 scripts/measure/open_defects.py docs/sprints/01/review-rounds.md` → rc=1, `open 17`, at `2b97fa0`). They are copied here, one row per family, so the Sprint 2 count starts from the true number (decision-log 2026-10-05; retro 1 M10). The Sprint 1 rows stay the history; this table is where their next disposition is written.

| Finding | Severity | Disposition | Owner (Sprint 2) | Waits on |
|---|---|---|---|---|
| SEC-R6-S1-01 | blocker | Open (carried). NUL/control character in the address or match title gives a 500. Sprint 2 row C-01, red first, before any new story | senior-backend-engineer | — |
| PE-R3R-01 | major | Open (carried). Parallel upload creations pass the open-upload quota. Row C-02, concurrency IT first | senior-backend-engineer | — |
| PD-R3V-01 | major | Open (carried). No recovery after an upload server error. Row C-03 (with C-35) | senior-frontend-engineer | — |
| QA-R3-E2E-01 / PD-R3V-02 | major | Open (carried). Timing flake in `walking-skeleton.spec.ts`; root specs not repeated. Row C-04, TCR row first | senior-qa-engineer | — |
| QA-R3-E2E-02 | major | Open (carried). Evidence E2E runs share output and network. Row C-05 | sre-devops-engineer | — |
| QA-R3-GATE-01 | major | Open (carried). Manual screen-reader pass (NFR-027b) on Sprint 1 screens. Row C-06, due 2026-11-13 | senior-qa-engineer with a human tester | PO item P6 (devices or tester) |
| SEC-R3-S1-01 / SEC-R4-S1-01 | major | Open (carried). Account identity on the rotatable `email_key`. Story ST-013b (committed) | senior-backend-engineer | — |
| QA-R1-06 / PE-R2-02 / QA-R2-02 / PE-R3-05 / QA-R3-05 / QA-R2V-01 | blocker | Open (carried). No green `ci-gate` run on GitHub for the Sprint 1 head; PR #1 blocked (run 37377206126). Row W-01 | sre-devops-engineer (triage), human PO (labels, protection, merge) | PO item P1 |
| S-08 / QA-R2V-08 | major | Open (carried). No published `nightly-quality.yml` run: the workflow is not on `main` | sre-devops-engineer | PO item P1 (merge to `main`) |
| PD-R1-02 / PD-R1-04 / PE-R1-04 / QA-R1-04 / S-09 / QA-R2V-06 / PD-R2R-01 | blocker | Open (carried). WebKit E2E failures (8 `[webkit]` on run 37377206126). Row W-01: SRE triages from the CI logs, FE fixes product defects | sre-devops-engineer, senior-frontend-engineer | PO item P1 (CI runs) |
| DEMO-07 | blocker | Open (carried). The demo's nightly result does not exist (same cause as S-08) | sre-devops-engineer | PO item P1 |
| SEC-R4-S1-04 / BLK-ASVS-6.3.3 | major | Open (carried). ADR 0031 (single-factor magic link) needs the PO's decision | security-privacy-engineer (input), human PO (decider) | PO item P2 |
| QA-R2V-11 | major | Open (carried). The ADR 0031 half (same decision as the row above) | human PO | PO item P2 |
| S-07 / QA-R2V-07 | blocker | Open (carried). Real phone recordings for ST-025 | senior-ml-cv-engineer | PO item P3 (recordings, or approval to defer) |
| PD-R2R-03 | major | Open (carried). Capture-guide consent line: security wording decision (flows §10.1 D-8), then FE red test | security-privacy-engineer, senior-frontend-engineer | DR-01 (P7 review), due 2026-11-02 |
| PD-R1-06 / PD-R2R-02 / QA-R2V-12 | major | Open (carried). DoR P7 flows design review of Sprint 1 not held. Row DR-01 | principal-designer (chair) and participants | DR-01, due 2026-11-02 |
| QA-R2V-03 | blocker | Open (carried). The Sprint 1 G01-11 escalation itself; closes when the rows above close | engineering-manager | PO items P1-P4 |
