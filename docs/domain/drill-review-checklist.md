# Drill review checklist, warm-up rule and coverage scope (R1)

- **Owner:** pickleball-domain-coach (COACH-4, 2026-10-17; §3.1.1 added by COACH-5, 2026-11-03). **Used by:** ST-058a..c (each drill's checklist row goes in that ticket's decisions file), ST-056 (warm-up rule), ST-059 (coverage CLI), G04-05.
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
- **Pairs of targets (PE-R1-1).** A plan that trains targets t and u can hold, in one session, t's drill beside a drill for u that also cites t (two drills of one session are always different). So for every ordered pair (t, u) whose drills overlap, t needs ≥ 2 drills apart from that one, i.e. ≥ 3 in all; a pair with no shared drill needs nothing beyond the cell. The check fails naming each short pair, e.g. `AN-01 with AN-05 × intermediate × solo+wall: drills: 1` (the library before `pb.serve.wall-serve-and-ready`: both serve drills cited AN-01 and AN-05, so a plan training both serve metrics put both in one session and its swaps answered `409 no_alternative`). A target already short on its own is not repeated as a pair.
- **Superseded by the session-size rule below (COACH-5, 2026-11-03).** The pair rule covered a session with up to two weakness drills that cite two targets. It missed (a) a plan that trains a single weakness, where a session can hold both drills of that target, and (b) a longer session with three or more weakness drills whose drills overlap. In both cases the swap answered `409 no_alternative` (finding COACH-S5-01, `docs/sprints/05/review-rounds.md`; first recorded in `docs/sprints/04/decisions/QA-VERIFY04R3-01.md`).

#### 3.1.1 Session-size rule (FR-124.R1, FR-124.R2, FR-141.R1; COACH-5, judgment)

- **Session size `S(p, level)`:** the most non-warm-up drills one session of profile p can hold: `floor((minutes_per_session − 5) / m)`, where 5 is the shortest warm-up (§2) and m is the smallest `duration_min` among the profile's counted drills at that level (as defined above). For `solo+wall` at 30 minutes, m = 10, so S = floor(25 / 10) = **2**.
- **Why S + 1:** a session holds at most S weakness drills. When the player presses "Not for me" on one of them, a different drill for the same target is needed that is not already in the session. The worst case is that every other drill in the session also cites that target. This is always true for a single-weakness plan (case a), and it can happen in a session of three or more drills whose drills overlap (case b). So at most S drills of the target are taken, and one more must exist.
- **Each target × level × profile cell needs ≥ S + 1 counted drills** (3 for `solo+wall` at 30 minutes). The check fails naming the cell and both numbers, e.g. `AN-02 × intermediate × solo+wall: drills: 2 < 3 (single-weakness swap)`. This includes the pair rule above: a pair (t, u) can take at most S drills of t in one session, so S + 1 drills of t always leave a swap. The pair message stays for its own case.
- **Reading of FR-141.R1:** FR-141.R1 says a cell fails with "fewer than 2 fitting drills". The coach reads this as fewer than 2 fitting alternatives to the drill being swapped. One of those alternatives may already be in the session, so the count in all is S + 1 = 3 for `solo+wall`. Under both readings, the negative Example (a gap fixture without a second solo-wall drill) fails.
- **FR-124.R2 is a behaviour rule, not a coverage rule.** A swap never returns a drill that is already in that session. When no such drill exists, the answer is `409 no_alternative` and the plan is unchanged. The coverage rule makes this answer rare for the checked profiles. It cannot make it impossible for every possible profile (players 1, 2, 4 × equipment). So only the profiles in `PROFILES` fail the build, and any other profile is reported as an advisory row.
- **Library state on `main` at `8c37e98d` (hand count, the same filter as `check_profiles`):** `solo+wall` × intermediate: AN-01 3, AN-05 3, AN-02 2, AN-04 2, AN-07:fault 2, AN-07:forced-error 2. Under S + 1 = 3, four cells are short by one drill each. ST-081a's check reports them red, and ST-081b closes them with 4 drills, within its limit of 6. For each new drill, the coach records a §1 row and a usability safety class in `docs/domain/usability-drill-safety.md` §2.
- **Profiles for Sprint 5:** `solo+wall` (1 player, `wall`, 30 min, intermediate) fails the build, as today. Adding a fail-the-build profile, for example a pair on a half court or a 45-minute session where S = 4, needs a decisions-file row and enough drills. It is not in Sprint 5 because ST-081b may add at most 6 drills (kickoff COACH-3).
