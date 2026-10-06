# Sprint 3 progress

- **Owner:** engineering-manager (with the product-manager for scope and PO items). Machine-readable status: [`status.json`](status.json) (ADR 0010 units; `implemented_units` and `dod_done_units` tracked separately; decider tasks with dates).
- **Plan:** [`../sprint-03.md`](../sprint-03.md). **Goal scorecard:** [`goal-scorecard.md`](goal-scorecard.md). **Created:** 2026-10-06, at planning.
- **Branch:** `sprint-03`, based on `sprint-02` at `ce91984`. **Remote:** `nhuthuynh/racket-analytics`.
- **Process in force:** ADR 0022 (one story = one commit, owner-routed findings, smoke before review), ADR 0030 (a disposition per finding, EM status step, isolated evidence, slices and waivers before the commit), ADR 0033 (reviewer-written Open rows, dry-run every goal method, self-cleaning evidence), **ADR 0037** (EM reconciliation after every round; decider tasks scheduled with briefs and dates; human-gated goal items put to the PO at planning).

## Planning, 2026-10-06 (engineering-manager with product-manager, principal-engineer, business-analyst, senior-qa-engineer)

| Item | Result | Evidence |
|---|---|---|
| Branch | `sprint-03` created from `sprint-02` | `git checkout sprint-02 && git checkout -b sprint-03` at `ce91984` |
| Retro 2 actions reviewed first | A1-A5 mapped into the plan (sprint-03 §0.3) | `docs/retros/2026-11-13-sprint-02.md` §7 |
| PO decisions applied | ADR 0023 and `po-input-2026-10-05.md`: accept all; US + AU; https dev stack, no insecure cookie; rules stay PROVISIONAL-UNVERIFIED, sheet and stats say "unofficial"; repository public until P10 (sprint-03 §0.2) | ADR 0023; po-input retraction 2026-10-06 |
| Preconditions | Dictionary all draft (COACH-1); no api-sprint-03 (PE-1); no snapshot design (PE-2); no purge design (PE-3); no Sprint 3 flows (PD-1, DR-03); DR-01/DR-02 not held; ADR 0005 Proposed | sprint-03 §0.1; blockers.md row 2 |
| Human-gated goal items | C-06 (P6), SEC-RV3-01 (P10), BLK-GOLD-01 (P11), dictionary second reviewer (P9, if required) put to the PO as P12; stay in G03-12 without an answer | sprint-03 §0.4; blockers.md row 1 |
| Capacity | Load factor 0.8, 12.8 units/lane. Committed BE 12.5, FE 11.0, QA 9.5, SRE 7.0, ML 3.0 = 43.0 units | sprint-03 §2; `status.json` totals |
| Carried findings | 14 open Sprint 2 blocker/major rows carried as Open rows | `python3 scripts/measure/open_defects.py docs/sprints/03/review-rounds.md` → rc=1, `open 14` |
| Decider tasks | 17 dated tasks (DR-01, DR-02 + 5 decider briefs, COACH-1, PM-1, PE-1..PE-4, PD-1, DR-03, SEC-1, BA-1) | sprint-03 §3.3; `status.json` `decider_tasks` |
| PO list | P6-P12 with dates | blockers.md row 1 |
| Goal scorecard | 12 metrics G03-01..G03-12 with targets and live methods | `docs/sprints/03/goal-scorecard.md` |
| Harness | `statslib.py`, `statscontract.py`, `live_stats.py`, `stats_latency.py` with tests, red first (1 red on the first run: a float edge in the Wilson lower bound at k = 0, fixed in the implementation) | `cd infra && uv run pytest -q tests/test_measure_sprint03.py` → 51 passed; commit `75338b9` (late size waiver, decision-log) |
| Disk | 14 GB free on `/` (floor 10 GB) | `df -h /` → `252G 26G 14G 66%`; blockers.md row 3 |

## Order of the session (ADR 0037 rule 2)

1. **Step 1 (D1):** decider tasks DR-01, DR-02 (+ FE, coach, BA, PM, security briefs), COACH-1 part 1, PM-1, PE-1/PE-2/PE-3 drafts, PE-4, SEC-1, PD-1 draft. In parallel, lanes start the work that needs none of them: C3-01, C3-04, C3-05, ST-044, ST-053, ST-042, QA-FUZZ-3.
2. **Step 2 (D2):** PE-2 review, PE-1 contract and `statscontract.py`, COACH-1 statuses, PD-1 final. Then ST-043, ST-045, ST-046, ST-049, C3-03, QA-ACC-3, ST-050/051 backend.
3. **Step 3 (D3):** DR-03. Then the UI stories ST-048, ST-047 (UI), ST-050/051 (UI), ST-052 (UI).
4. **After the build:** SRE-SMOKE-3 → review round 1 → **EM reconciliation** → fix round → EM status step → … → method dry-runs → goal verification → **EM reconciliation** → close.

## Lane status

| Lane | Committed units | Implemented | DoD-done | Next |
|---|---|---|---|---|
| BE | 12.5 | 0 | 0 | ST-044 (pure), then ST-043 after COACH-1 |
| FE | 11.0 | 0 | 0 | C3-03 after C3-02; UI after DR-03 |
| QA | 9.5 | 0 | 0 | C3-01 first; QA-FUZZ-3; ST-049 with COACH-1 |
| SRE | 7.0 | 0 | 0 | C3-04, C3-05 |
| ML | 3.0 | 0 | 0 | ST-053 |
