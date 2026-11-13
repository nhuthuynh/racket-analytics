# Sprint 6 review rounds

Every reviewer appends one row per finding under its own heading, with the disposition **Open**, as soon as it states the finding (ADR 0033 rule 1; ADR 0050 rule 5). Owners add a later row with the new disposition (Fixed with evidence, Deferred to a named backlog row, or Rejected with a reason). The engineering-manager writes the reconciliation row of each round before the next round starts (working-agreement §7 steps 3b and 3d; ADR 0037 rule 1, ADR 0047 rule 1). The last row naming a finding id wins. Ticket PRs may add ledger rows here. The Sprint 6 open-defect count: `python3 scripts/measure/open_defects.py docs/sprints/06/review-rounds.md`.

Created by the engineering-manager in PLAN-06 (PR #241), round 3 fix (PE-PLAN06-08, QA06-PLAN-04). The reviewers of rounds 1 to 3 returned their findings as PR reviews and wrote no rows, so the Open rows below are the EM's §7 step 3d rows, attributed to the reviewer that returned each id.

**Id renumbering (EM, 2026-11-13).** The principal-engineer used the ids PE-PLAN06-08, -09 and -10 twice: in round 2 (review 5885000282: a minor and two nits) and again in round 3 (review 5885060980: two majors and a nit). Ids are unique in this ledger, because the last row naming an id wins. Round 3 keeps its ids, since the round 3 brief and the PLAN-06 decisions file name them. The round 2 findings are ledgered as PE-PLAN06-11 (was round 2 "-08"), PE-PLAN06-12 (was round 2 "-09") and PE-PLAN06-13 (was round 2 "-10", the same finding as QA06-PLAN-02, so it is one row with both ids).

## PLAN-06 (PR #241), review round 1: principal-engineer (review 5884845775, head `94f46ff8`)

| Finding | Severity | Disposition | Owner (Sprint 6) | Waits on |
|---|---|---|---|---|
| PE-PLAN06-01 / QA06-PLAN-01 | blocker | Open: the PR turns the 6 QA-DOR-CHECK scenarios red (`tests/features/atomic_breakdown.feature` plants Sprint 5 ids, the current breakdown is Sprint 6) | engineering-manager | — |
| PE-PLAN06-02 | major | Open: FR-172.R1 ranks a weakness "wholly on the worse side" but no rule says which side is worse | engineering-manager, business-analyst | — |
| PE-PLAN06-03 | major | Open: FR-171.R4 (AN-13 median) has no stated interval method, while FR-171.R1 / FR-172.R1 use Wilson | engineering-manager, business-analyst | — |
| PE-PLAN06-04 | minor | Open: the measure snapshot key has no subject or pattern id (ST-171e, NFR-075.1) | engineering-manager | — |
| PE-PLAN06-05 | minor | Open: PE-6a and ST-170a/b name two owners for references | engineering-manager | — |
| PE-PLAN06-06 | minor | Open: roadmap §2 S7 row still says "R2" while §5-6 say Go port | engineering-manager | — |
| PE-PLAN06-07 | nit | Open: FR-172.R4 width is undefined for a point reference | engineering-manager, business-analyst | — |

## PLAN-06 (PR #241), review round 1: senior-qa-engineer (review 5884863089, head `94f46ff8`)

| Finding | Severity | Disposition | Owner (Sprint 6) | Waits on |
|---|---|---|---|---|
| QA06-PLAN-01 / PE-PLAN06-01 | blocker | Open: same finding as PE-PLAN06-01 (6 infra scenarios red in CI's infra job) | engineering-manager | — |

## PLAN-06 (PR #241), round 1 reconciliation (engineering-manager)

Fix commits: `06eb84df` (red picker tests), `6f82a16a` (pickers, TCR row 1), `9346a3d4` (plan text). Re-checked as fixed by the principal-engineer (review 5885000282) and the senior-qa-engineer (review 5885019428), both APPROVE on `9346a3d4`. Findings returned: 8 ids (PE-PLAN06-01..07, QA06-PLAN-01), 7 distinct findings; rows: 7 (one row carries both ids of the blocker).

| Finding | Severity | Disposition | Owner (Sprint 6) | Waits on |
|---|---|---|---|---|
| PE-PLAN06-01 / QA06-PLAN-01 | blocker | Fixed (`06eb84df` red, `6f82a16a` green): the scenarios pick their planted rows from the current breakdown (`first_nfr_row_with`, `first_fr_rule_with_negative`, `first_prc_id` in `infra/tests/atomic_breakdown_fixtures.py`); `infra/tests/test_atomic_breakdown_pickers.py` runs them on every sprint's breakdown; TCR row 1 accepted by the senior-qa-engineer (review 5885019428). Evidence: `cd infra && uv run pytest -q tests/test_atomic_breakdown_scenarios.py tests/test_atomic_breakdown_pickers.py tests/test_merge_ready_tiers.py` → 96 passed (reviews 5885019428, 5885067391) | engineering-manager | — |
| PE-PLAN06-02 | major | Fixed (`9346a3d4`): `better_direction` (`higher` / `lower` / `inside_band`) in FR-170.R1, COACH-6a and ST-170a; FR-172.R1 defines the worse side from it, with Examples on both sides and a `lower` pattern (`docs/sprints/06/requirements-breakdown.md`). Verified in review 5885000282 | engineering-manager | — |
| PE-PLAN06-03 | major | Fixed (`9346a3d4`): FR-171.R4 states `order_statistic_median` (none below n = 6), `interval_method` is a `PatternMeasure` field, won dink rallies are `n_censored`. Math checked in review 5885000282 (n = 10 gives l = 2; n = 6 gives l = 1) | engineering-manager | — |
| PE-PLAN06-04 | minor | Fixed (`9346a3d4`): snapshot key (subject, pattern id, match version, rules_version, definition version) split from the gap-result key in ST-171e and PE-6a (`docs/sprints/sprint-06.md`) | engineering-manager | — |
| PE-PLAN06-05 | minor | Fixed (`9346a3d4`): PE-6a / ADR 0061 settles one owner: sport-plugin content read by Coaching through the ACL (`docs/sprints/sprint-06.md` PE-6a row) | engineering-manager | — |
| PE-PLAN06-06 | minor | Fixed (`9346a3d4`): roadmap §2 S7 row reads "Go port or R2, pending P21" (`docs/sprints/roadmap.md`) | engineering-manager | — |
| PE-PLAN06-07 | nit | Fixed (`9346a3d4`): FR-172.R4 defines the gap and the width (interval width for a point reference) | engineering-manager | — |

## PLAN-06 (PR #241), review round 2: principal-engineer (review 5885000282, head `9346a3d4`, APPROVE)

| Finding | Severity | Disposition | Owner (Sprint 6) | Waits on |
|---|---|---|---|---|
| PE-PLAN06-11 | minor | Open (returned as round 2 "PE-PLAN06-08"): assumption A6 in `docs/sprints/06/requirements-breakdown.md` still says "interval 95 % Wilson", which contradicts FR-171.R4 for AN-13 | engineering-manager | — |
| PE-PLAN06-12 | nit | Open (returned as round 2 "PE-PLAN06-09"): ST-170a lists the context "sport plugin content + Coaching/reference" and puts the loader under `backend/src/racket/coaching/reference/`; acceptable only as the ACL read side, which ADR 0061 should state | principal-engineer | PE-6a |
| QA06-PLAN-02 / PE-PLAN06-13 | nit | Open (PE returned it as round 2 "PE-PLAN06-10"): the scenario Then step matches the planted item by substring (`ctx["item"] in ln`), so `NFR-063.3` would match a line naming `NFR-063.31`; no false pass today | senior-qa-engineer | — |

## PLAN-06 (PR #241), review round 2: senior-qa-engineer (review 5885019428, head `9346a3d4`, APPROVE)

| Finding | Severity | Disposition | Owner (Sprint 6) | Waits on |
|---|---|---|---|---|
| QA06-PLAN-02 / PE-PLAN06-13 | nit | Open: same finding as the principal-engineer's round 2 "-10" (substring match in the Then step) | senior-qa-engineer | — |

## PLAN-06 (PR #241), review round 3: principal-engineer (review 5885060980, head `e6e9e518`, CHANGES REQUESTED)

| Finding | Severity | Disposition | Owner (Sprint 6) | Waits on |
|---|---|---|---|---|
| PE-PLAN06-08 | major | Open: no Sprint 6 review-rounds ledger; round 1 ids have no rows (working-agreement §7 3b, 3d); `reconcile_due.py --pr` rc 1, 6 problems | engineering-manager | — |
| PE-PLAN06-09 | major | Open: regression from `e6e9e518`: `docs/sprints/06/decisions/PLAN-06.md` line 75 cites a ledger path that does not exist; `check_docs.py` rc 1, 1 problem (0 on `9346a3d4`) | engineering-manager | — |
| PE-PLAN06-10 | nit | Open: the PR policy table records results against `9346a3d4`; re-state the head the decision covers once the ledger commit lands | engineering-manager | — |

## PLAN-06 (PR #241), review round 3: senior-qa-engineer (review 5885067391, head `e6e9e518`, CHANGES REQUESTED)

| Finding | Severity | Disposition | Owner (Sprint 6) | Waits on |
|---|---|---|---|---|
| QA06-PLAN-03 | major | Open: same defect as PE-PLAN06-09 (doc check rc 1 on the head, rc 0 on `9346a3d4`) | engineering-manager | — |
| QA06-PLAN-04 | major | Open: same defect as PE-PLAN06-08 (ledger missing, `reconcile_due.py --pr` rc 1) | engineering-manager | — |

## PLAN-06 (PR #241), rounds 2 and 3 reconciliation (engineering-manager, 2026-11-13)

Findings returned in rounds 2 and 3: 9 ids from the reviewers (round 2: PE "-08", "-09", "-10", QA06-PLAN-02; round 3: PE-PLAN06-08, -09, -10, QA06-PLAN-03, -04), 8 distinct findings after the renumbering and the one shared id pair (QA06-PLAN-02 / PE-PLAN06-13); rows below: 8, one per distinct finding. The fixes are in the commit that adds this file (the head after `e6e9e518` on `s06/plan`; its SHA is stated in the PR thread replies). Evidence, run in the PLAN-06 worktree:

- `python3 scripts/measure/reconcile_due.py --pr --base origin/main --head HEAD` (run on the committed head): rc 0 (results in `docs/sprints/06/decisions/PLAN-06.md`, "Review rounds 2 and 3").
- `python3 scripts/ci/check_docs.py --base origin/main --head HEAD`: rc 0, 0 problems.
- `python3 scripts/measure/open_defects.py docs/sprints/06/review-rounds.md`: 0 open blocker/major rows.

| Finding | Severity | Disposition | Owner (Sprint 6) | Waits on |
|---|---|---|---|---|
| PE-PLAN06-08 | major | Fixed: this file exists, with an Open row per returned id attributed to its reviewer and a reconciliation row per finding for rounds 1 to 3; `reconcile_due.py --pr --base origin/main --head HEAD` rc 0 | engineering-manager | — |
| QA06-PLAN-04 | major | Fixed: same fix as PE-PLAN06-08; rows for PE-PLAN06-01..13 and QA06-PLAN-01..04, each with a disposition | engineering-manager | — |
| PE-PLAN06-09 | major | Fixed: the path cited at `docs/sprints/06/decisions/PLAN-06.md` line 75 now exists; `check_docs.py --base origin/main --head HEAD` rc 0, 0 problems | engineering-manager | — |
| QA06-PLAN-03 | major | Fixed: same fix as PE-PLAN06-09 | engineering-manager | — |
| PE-PLAN06-10 | nit | Fixed: `docs/sprints/06/decisions/PLAN-06.md` "Review rounds 2 and 3" re-runs the PR-policy commands on the new tree and says the decision covers the head that carries this file; the PR reply names its SHA | engineering-manager | — |
| PE-PLAN06-11 | minor | Fixed: A6 now reads "95 % interval per the pattern's `interval_method` (`wilson` for proportions, FR-171.R1; `order_statistic_median` for AN-13, min_n ≥ 6, FR-171.R4)" (`docs/sprints/06/requirements-breakdown.md`); `check_atomic_breakdown.py` rc 0 | engineering-manager | — |
| PE-PLAN06-12 | nit | Deferred to PE-6a (ADR 0061, principal-engineer, Sprint 6): the PE-6a row already settles one owner (sport-plugin content read by Coaching through the ACL, not a Coaching aggregate); ADR 0061 states that the `coaching/reference/` module is the ACL read side, and ST-170a's Context and Dirs follow ADR 0061 before ST-170a is Ready | principal-engineer | PE-6a |
| QA06-PLAN-02 / PE-PLAN06-13 | nit | Deferred to QA-PIN-06 (senior-qa-engineer, Sprint 6, `infra/tests/`): tighten the Then step to a word-boundary match, with a TCR row (it changes an accepted test). Not fixed in PLAN-06 because it is not needed for a correct result today (the check fails only the planted row) and a second test change in a plan PR needs its own QA decision | senior-qa-engineer | QA-PIN-06 |
