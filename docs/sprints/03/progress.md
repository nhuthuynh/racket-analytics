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

## Review round 1: EM status step, 2026-10-07 (ADR 0030 rule 2; QA-R1S3-12)

| Item | Result | Evidence |
|---|---|---|
| Ticket PRs (PO rule) | The "from Sprint 4" date was the agent's, not the PO's, and is retracted. **ADR 0039:** Sprint 3 goes to `main` as ticket PRs only, each with a principal-engineer and a senior-engineer verdict before merge. There is no sprint PR. 0 ticket PRs opened so far | `git show 94cdb99` (author Claude); `list_pull_requests state=all` → #1-#3 only; blockers.md P13 and the ticket-PR row |
| Implemented | 12 of 30 items, 12.0 of 43.0 units (0.279): C3-01..C3-05, ST-042, ST-044, ST-045, ST-053, QA-ACC-3, QA-FUZZ-3, QA-MIN-3 | `status.json` stories (evidence commits per item) |
| In progress | C3-09, ST-043, ST-049, ST-052 (a), ST-054, QA-DRY-3, SRE-PURGE (a), SRE-SMOKE-3 | `status.json` |
| Blocked | ST-046, ST-047, ST-048, ST-050, ST-051, ST-038 (PE-1/2/3, SEC-1, PM-1, PD-1, DR-03, COACH-1); C3-06/07/08 (P6/P10/P11, now sprint-DoD rows §9.1) | blockers.md rows 2, 4, 7 |
| DoD-done | 0. Nothing has merged to `main`. Under ADR 0039 a unit counts only after its ticket PR merges | `status.json` totals |
| Goal | **Not met.** Stats, evidence and delete routes are not served; G03-01 smoke 0/1 (QA-R1S3-06) | openapi check at `15a7551`; smoke.md pre-review |
| Open defects (G03-12) | rc=1, open 9 (was 11). SEC-RV3-01, BLK-GOLD-01 and C-06 moved to sprint-DoD rows (P12 b); QA-R1S3-02 deferred to T-SEC-RV3-02 | `python3 scripts/measure/open_defects.py docs/sprints/03/review-rounds.md` |
| Size | Five commits over 400 lines recorded as breaches. Waivers for the ticket PRs decided before they open | decision-log 2026-10-07 |

## Review round 2: EM status step, 2026-10-07 (ADR 0030 rule 2)

| Item | Result | Evidence |
|---|---|---|
| Ticket PRs (PO rule) | Still 0 opened. Slice brief for ST-046a … ST-052c (each ≤ 400 lines, no waiver) and the orchestrator runbook are written. Waiting on principal-engineer bases, then the orchestrator | `mcp__github__list_pull_requests state=all` → #1-#3 closed; `list_branches` → no `s3/*`; decision-log and blockers.md round-2 EM rows |
| Goal | **Not met.** No stats, evidence or label path; `/matches/{match_id}` and `/me` GET only; no `racket.platform.purge` (QA-R1S3-06) | openapi check and `import racket.platform.purge` → `ModuleNotFoundError` at `7a6ffe5` |
| TDD order (QA-R1S3-09/10) | Accepted breach for six commits, deferred to retro-3 input R3-IN-1 (sprint-03 §13). Not claimed as test-first | `git log --format=%B -1 <sha> \| grep -c '^Red:'` → 0 ×6 |
| Screen-reader pass (QA-R3-GATE-01 / C-06) | Reconciled: deferred to S3-DoD-P6 only. No longer counted in G03-12. 0 of 38 rows run | a11y-manual §4, scorecard G03-10 note |
| Open defects (G03-12) | rc=1, **open 8** (was 11): PD-R1S3-01, PD-R1-06 family, SEC-S3-TM-01/02/05, PE-R1S3-07/QA-R1S3-07, QA-R1S3-06, PE-R1S3-01/QA-R1S3-04 | `python3 scripts/measure/open_defects.py docs/sprints/03/review-rounds.md` |

## Sprint close: EM status step, 2026-10-08 (head `c1fba6a`; VR3 measured `fb920bc`)

| Item | Result | Evidence |
|---|---|---|
| Goal | **Not met.** VR3 met 10 of 12 live on a fresh HTTPS stack, and every player-facing promise ran 5/5 in real time. G03-09 (c) has no CI run at the head. G03-12 is **8** after the EM reconciled review round 3 (the verifier counted 3) | scorecard §9.3; `sprint-report.md` §1 |
| Reconciliation | Review round 3 (`fdeeb53`, run in parallel with VR1) had 0 rows for its 25 new ids. Each is now written and re-checked at the head. VR3-S3-01..03 written (minor) | review-rounds "Sprint close: engineering-manager"; `open_defects.py` → rc=1, open 3 → 8 |
| Implemented | 38.5 of 43.0 units (0.895): BE 12.5, FE 11.0, QA 9.0, SRE 3.0, ML 3.0 | `status.json` totals |
| DoD-done | 0. No Sprint 3 ticket PR (ADR 0039); Sprint 1 + 2 reached `main` by PR #2 (2026-10-06) | `list_pull_requests state=all`; `list_branches` |
| Tests at the head (EM) | backend unit 1,833 passed, 1 skipped (11.17 s); web 68 files, 580 passed; infra 618 passed, 1 skipped | commands in `sprint-report.md` §5 |
| Decisions | ADR 0046 accepted with an amendment; ADR 0047 (retro 3); G03-08 wording names GS-AN-1 v2; size breaches `d83ee1b`/`cd8856f`/`96044d9` recorded | decision-log 2026-10-08 rows; ADR 0046 Notes; ADR 0047 |
| Retro | `docs/retros/2026-11-27-sprint-03.md`: 5 actions (A1 ticket PRs, A2 CI at the head, A3 chair outcomes, A4 security ITs, A5 ADR 0047 + `Red:` check) | retro §7 |
| Carry-over | C4-PR, C4-CI, C4-DR, C4-SEC, C4-SRE, C4-MIN, human-gated rows, stretch | `sprint-report.md` §8 |
