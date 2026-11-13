# PD-6 decisions

Per-ticket decision file (working-agreement §3). Ticket: PD-6, "flows-sprint-06.md: reference browser, weakness view, exercise Why, consent and provenance flows" (`docs/sprints/sprint-06.md` §3.2, wave 1 gates). Owner: principal-designer. Review tier 0 (ADR 0056). Covers FR-170.R5, FR-172.R5, NFR-027.10-.14; gates ST-170c, ST-172c, ST-173d through DR-06.

**TDD does not apply:** the ticket writes a design specification (`docs/design/flows-sprint-06.md`) and this file; there is no executable behaviour to drive with a failing test. The red tests these flows define belong to ST-170c, ST-172c, ST-173d (component per state, label absent fails, table equals chart) and ST-174b (axe, target size). Instead, the doc checks ran red before the file existed and green after (PR description, "Evidence"): `docs/design/tools/check_flows.py` with every screen and the nine states, `scripts/ci/check_docs.py` (paths, citations, the DR-06 decider table), and `docs/design/tools/contrast_check.py` on the tokens the gap chart uses.

## 1. Decisions

| Date | Role | Decision | Evidence | Reason |
|---|---|---|---|---|
| 2026-11-13 | principal-designer | **Screen ids start at 10** (V-10, W-10, E-10, C-10) | V-01 (video player) and E-01/E-02 (evidence) are taken in flows-sprint-02/03 (`grep -ohE "\b[VWEC]-[0-9]{2}\b" docs/design/flows-sprint-0*.md`) | Axe and target attachments are keyed by screen id; the Sprint 4 A-10 precedent |
| 2026-11-13 | principal-designer | **Gap chart uses shape, not hue**: outlined band in `border-control`, solid range bar in `primary`, value diamond in `text`; no new token | `contrast_check.py` → 55/55 pairs pass; the three pairs are already proven ≥ 3:1 in both themes | NFR-027.11, .14 with no new colour proof needed (judgment) |
| 2026-11-13 | principal-designer | **DR-06 cell table holds only rows with a dated cell**; the schedule (Opened, Due) sits in a separate table without a `Cell` column | `scripts/ci/check_docs.py` runs `check_flows.py --decider` for every row of the current sprint's DR table on every PR (PRC-3.4); a "pending" row would turn the doc-check job red for all PRs | Keeps main green while each decider's review carries its own row (kickoff PD-1, ADR 0037 rule 2) |
| 2026-11-13 | principal-designer | **Consent notice is information, not a checkbox**; no player UI writes rights or consent fields | T6-FT-5 (no route writes `rights_basis`, `filmed_persons`); Sprint 4 R4-5 | A checkbox would imply a consent record the system does not hold (judgment) |
| 2026-11-13 | principal-designer | **Usability tasks live in the flows file until ST-083 merges** | ST-083 kit not on `origin/main` (Sprint 5 drain) | S6-P9 needs the tasks ready; follow-up PD-FL6-05 |
| 2026-11-13 | principal-designer | **Copy register coach column is "pending"**, not "agreed" | The coach cannot co-author inside this session; agreement is cited, never inferred (BA5-PE-01) | DR-06 R6-6 carries the coach's decision |

## 2. Cost per PR (ADR 0056 decision 1)

| Round | wall_time_min | total_cost_usd |
|---|---|---|
| Author build | not measured | not measured (the session does not expose per-ticket wall time or cost to the agent) |
