# Drill review checklist, warm-up rule and coverage scope (R1)

- **Owner:** pickleball-domain-coach (COACH-4, 2026-10-17). **Used by:** ST-058a..c (each drill's checklist row goes in that ticket's decisions file), ST-056 (warm-up rule), ST-059 (coverage CLI), G04-05.
- **Basis:** FR-140, FR-141; QD-DR-01..05, QD-PL-03; schema `backend/src/racket/coaching/drills/schema.json`; weakness-catalogue §6. Every rule here is **(judgment)**; no coaching source is verified [DOM G2]. Until a human coach reviews the library (P15), drills carry the interim notice "drills not yet checked by a human coach" (PD-4).

## 1. What `coach-reviewed` means for a drill

A drill version moves `draft` → `coach-reviewed` only when every row passes. One failed row keeps it `draft`.

| # | Check | Pass when |
|---|---|---|
| C1 | Schema and lint | `cd backend && uv run racket-drill-lint ../content/drills` → `ok, 0 problem(s)` with the drill in the library |
| C2 | Source | `source` names a verified source ID, **or** `coach_rationale` explains why the drill trains its target metric and contains "(judgment)" |
| C3 | Target fit | every `target_metrics` ID is an R1 targetable metric (AN-01, AN-02, AN-04, AN-05, AN-07), or the drill is a warm-up (§2); the setup actually produces the shots that move that metric |
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

- **Cells:** each R1 targetable metric (AN-01, AN-02, AN-04, AN-05, AN-07) × each level (beginner, intermediate, advanced) = **15 cells**.
- **Counted drills:** latest version, `review_status` `coach-reviewed` or `verified`, no `deprecated_by`, not a warm-up. A drill counts in every cell of each target metric × each level in `level_min`..`level_max`.
- **Each cell needs:** ≥ 2 drills; of them ≥ 1 with `players ≤ 2` and ≥ 1 whose `needs` excludes `ball_machine` (one drill may satisfy both).
- **Library:** ≥ 20 counted-or-warm-up reviewed drills in total, with ≥ 3 warm-ups (ST-058a). AN-03 and AN-06 are out of scope (weakness-catalogue §6).
- The CI check prints the matrix (count, `players ≤ 2` count, no-ball-machine count per cell) and fails naming each empty cell, e.g. `AN-05 × beginner: players ≤ 2: 0`.
