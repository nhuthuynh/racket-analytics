# Drill review checklist, warm-up rule and coverage scope (R1)

- **Owner:** pickleball-domain-coach (COACH-4, 2026-10-17). **Used by:** ST-058a..c (each drill's checklist row goes in that ticket's decisions file), ST-056 (warm-up rule), ST-059 (coverage CLI), G04-05.
- **Basis:** FR-140, FR-141; QD-DR-01..05, QD-PL-03; schema `backend/src/racket/coaching/drills/schema.json`; weakness-catalogue §6. Every rule here is **(judgment)**; no coaching source is verified [DOM G2]. Until a human coach reviews the library (P15), drills carry the interim notice "drills not yet checked by a human coach" (PD-4).

## 1. What `coach-reviewed` means for a drill

A drill version moves `draft` → `coach-reviewed` only when every row passes. One failed row keeps it `draft`.

| # | Check | Pass when |
|---|---|---|
| C1 | Schema and lint | `cd backend && uv run racket-drill-lint ../content/drills` → `ok, 0 problem(s)` with the drill in the library |
| C2 | Source | `source` names a verified source ID, **or** `coach_rationale` explains why the drill trains its target metric and contains "(judgment)" |
| C3 | Target fit | every `target_metrics` ID is an R1 targetable metric (AN-01, AN-02, AN-04, AN-05, AN-07), or the drill is a warm-up (§2); a drill with `AN-07` has `share:fault` and/or `share:forced-error` in `skills`, and a drill without `AN-07` has neither (weakness-catalogue §5); the setup actually produces the shots that move that metric (that share for AN-07: fewer own faults, or fewer errors under pressure) |
| C4 | Numeric success criterion | `success_criterion` is countable in one session ("7 of 10 serves land past the cone line"); no "improve", "feel" or "until comfortable" without a number |
| C5 | Safety (QD-DR-04) | a drill with overhead lobs retreating backwards, diving, sprints or high-intensity footwork has non-empty `safety_notes` (e.g. "turn and run back, never backpedal"; "stop if dizzy or in pain"); content that could cause injury is escalated to the EM and the PO instead of reviewed |
| C6 | Level fit | `level_min`..`level_max` matches the demand: beginner = cooperative feeds, no speed-ups; intermediate = some live balls; advanced = live, competitive or speed-up content |
| C7 | Logistics | `players` is the number of people needed; `needs` lists every facility (`wall`, `half_court`, `full_court`, `ball_machine`, `partner_feeder`); a drill playable alone with a wall says `players: 1` and `needs: ["wall"]` |
| C8 | Duration | `duration_min`..`duration_max` fits the content (lint caps 45); a warm-up is 5-10 (§2) |

The coach records one row per drill: `id@version`, C1..C8 pass/fail, the date. A content change bumps `version` and needs a new review (QD-DR-02).

## 2. Warm-up rule (QD-PL-03, FR-121)

1. A **warm-up drill** has `warm-up` in `skills`, `duration_min ≥ 5`, `duration_max ≤ 10`, `level_min: beginner`, and no C5 safety trigger (no lobs retreating, diving or sprints).
2. **Every session starts with exactly one warm-up drill**, assigned 5-10 minutes. It needs a reviewed warm-up whose `players` and `needs` fit the player (QD-PL-02); a solo, wall-free warm-up (e.g. footwork and shadow swings) must exist in ST-058a.
3. The warm-up counts toward the session time and the 40% cap. Hence a session needs at least 13 minutes (5 / 0.40 = 12.5); below that no plan is feasible, and the preferences are refused (validation per PE-4; 15 minutes is the recommended minimum, judgment).
4. A warm-up drill still lists ≥ 1 `target_metrics` (schema). It does not count toward coverage (§3) and is never chosen for a weakness slot.

## 3. Coverage scope (QD-DR-05, FR-141; checked by ST-059)

- **Targets:** `AN-01`, `AN-02`, `AN-04`, `AN-05`, `AN-07:fault`, `AN-07:forced-error` (the plan targets of weakness-catalogue §5: AN-07 is split by share, so a library with no drill for one share fails).
- **Cells:** each target × each level (beginner, intermediate, advanced) = **18 cells**.
- **Counted drills:** latest version, `review_status` `coach-reviewed` or `verified`, no `deprecated_by`, not a warm-up. A drill counts in every cell of each target it hits × each level in `level_min`..`level_max`; for AN-07 it hits a share only through the `share:fault` / `share:forced-error` skill. An AN-07 drill with no share skill counts in no AN-07 cell and the check names it (`<id>@<version>: AN-07 without share skill`).
- **Each cell needs:** ≥ 2 drills; of them ≥ 1 with `players ≤ 2` and ≥ 1 whose `needs` excludes `ball_machine` (one drill may satisfy both).
- **Library:** ≥ 20 counted-or-warm-up reviewed drills in total, with ≥ 3 warm-ups (ST-058a). AN-03 and AN-06 are out of scope (weakness-catalogue §6).
- The CI check prints the matrix (count, `players ≤ 2` count, no-ball-machine count per cell) and fails naming each empty cell, e.g. `AN-05 × beginner: players ≤ 2: 0` or `AN-07:forced-error × advanced: drills: 0`.

### 3.1 Profile axis: players x equipment (QA-VERIFY04R3-01, FR-124 "Not for me")

- **Why:** the target x level cells can pass while a whole setup has one drill per target. Then every "Not for me" swap for that setup answers `409 no_alternative`. VERIFY-04-r3 measured this for G04-01 step 9 (1 player, wall, intermediate: AN-04 had only `pb.drive.wall-margin`).
- **Profiles:** `solo+wall` = the G04-01 step 3 preferences: 1 player, equipment `wall`, 30 min per session, 3 sessions per week. It is checked at the levels the goal scorecard measures (intermediate). A new profile or level is a new row in the ticket's decisions file and a change to `PROFILES` in `racket-drill-coverage`.
- **Counted drills:** the counted drills of §3 that are not warm-ups, that fit the profile exactly as the plan picks them (`Drill.fits`, QD-PL-02: `players` ≤ the profile's players and `needs` ⊆ its equipment, so a solo drill with no needs counts), and whose `duration_min` fits the session's 40% drill cap (QD-PL-03: 12 minutes for 30). AN-07 counts by share, as in §3.
- **Each target x level x profile cell needs ≥ 2 drills.** The check prints one row per cell and fails naming each short cell, e.g. `AN-04 × intermediate × solo+wall: drills: 1`.
- **Known limit (judgment):** 2 drills are enough when the plan trains more than one weakness, because each session then holds at most one drill per target. When the plan trains a single weakness, a 30-minute session can hold both drills of that target, and that session's swap still answers `409 no_alternative`. Closing that needs a third drill per target or a planner rule. Recorded in `docs/sprints/04/decisions/QA-VERIFY04R3-01.md`.
