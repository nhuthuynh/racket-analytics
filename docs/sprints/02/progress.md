# Sprint 2 progress

- **Owner:** engineering-manager (with the product-manager for scope and PO items). Machine-readable status: [`status.json`](status.json) (ADR 0010 units; `implemented_units` and `dod_done_units` tracked separately).
- **Plan:** [`../sprint-02.md`](../sprint-02.md). **Goal scorecard:** [`goal-scorecard.md`](goal-scorecard.md). **Created:** 2026-10-05, at planning.
- **Branch:** `sprint-02`, based on `sprint-01` at `2b97fa0`. **Remote:** `nhuthuynh/racket-analytics`.
- **Process in force:** ADR 0022 (one story = one commit, owner-routed findings, smoke before review), ADR 0030 (a disposition per finding, EM status step, isolated evidence, slices planned and waivers before the commit), ADR 0033 (reviewer-written Open rows, dry-run every goal method, self-cleaning evidence, sprint-report §1 rewritten when the scorecard or the open count changes).

## Planning, 2026-10-05 (engineering-manager with product-manager, principal-engineer, business-analyst, senior-qa-engineer)

| Item | Result | Evidence |
|---|---|---|
| Branch | `sprint-02` created from `sprint-01` | `git checkout -b sprint-02` at `2b97fa0` |
| Retro 1 actions reviewed first | A1-A5 mapped into the plan (sprint-02 §0.3) | `docs/retros/2026-10-30-sprint-01.md` §9 |
| PO decisions applied | ADR 0023 and `po-input-2026-10-05.md`: accept all; US + AU; https dev stack, no insecure cookie; rules stay PROVISIONAL-UNVERIFIED, the sheet says "unofficial" (sprint-02 §0.2) | ADR 0023 note 2026-10-05 |
| Preconditions | ADR 0009 met; match-aggregate design not approved (D1); no api-sprint-02 (D2); no Sprint 2 flows (D2); DR-01 not held (D1) | sprint-02 §0.1; blockers.md row 2 |
| Capacity | Load factor 0.8, 12.8 units/lane. Committed BE 12.5, FE 12.0, QA 11.5, SRE 8.0, ML 2.0 = 46.0 units; stretch ST-035, ST-034, ST-038, ST-028b, ST-025, ST-033, ST-036; ST-042 to Sprint 3 | sprint-02 §2; decision-log rows 1-4 |
| Carried findings | 17 open Sprint 1 blocker/major families carried as Open rows | `python3 scripts/measure/open_defects.py docs/sprints/02/review-rounds.md` → rc=1, `open 17` |
| PO list | P1-P9 with dates sent on day 1 | blockers.md row 1 |
| Goal scorecard | 12 metrics G02-01..G02-12 with targets and live methods | `docs/sprints/02/goal-scorecard.md` |
| Harness | `taglib.py`, `tagcontract.py`, `live_tagging.py`, `tag_latency.py`, `pw_timings.py` with tests, red first | `cd infra && uv run pytest -q tests/test_measure_sprint02.py tests/test_measure_scripts.py` → 81 passed; commit `15c8836` (late size waiver, decision-log) |
| C-24 (EM) | Scorecard §4.0 documents the host-port remap for isolated stacks | goal-scorecard §4.0 |
| Disk | 11 GB free on `/` (floor 10 GB) | `df -h /` → `252G 28G 11G 73%`; blockers.md row 3 |

## Lane status

| Lane | Committed units | Implemented | DoD-done | Next |
|---|---|---|---|---|
| BE | 12.5 | 0 | 0 | C-01, C-02 red first |
| FE | 12.0 | 0 | 0 | C-03 |
| QA | 11.5 | 0 | 0 | QA-FUZZ (red before C-01), C-04, ST-041 |
| SRE | 8.0 | 0 | 0 | C-05, C-15, C-23, then W-01 |
| ML | 2.0 | 0 | 0 | ST-040 |
| **Total** | **46.0** | **0** | **0** | |

## Daily log

| Date | Agent | Did | Next | Blockers |
|---|---|---|---|---|
| 2026-10-05 | engineering-manager | Planning: sprint plan refined, scorecard and harness, carried findings, PO list | D1 briefs per lane (§3.2 order, slices) | P1-P9; design preconditions (D1-D2) |
