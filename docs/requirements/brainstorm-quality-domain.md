# Requirements Brainstorm: Quality and Domain (Senior QA + Pickleball Domain Coach)

- **Date:** 2026-10-03
- **Authors (roles):** senior-qa-engineer, pickleball-domain-coach
- **Inputs:** `docs/specs/2026-10-02-racket-analytics-design.md` (the "spec"), `docs/research/*.md`, `docs/process/*.md`, `docs/requirements/brainstorm-product.md` (the "product brainstorm"), `docs/requirements/brainstorm-engineering.md` (the "engineering brainstorm").
- **Citations:** `<file>/<ID>` per `working-agreement.md` §0 (EP, AQS, DPA, DOM). `(judgment)` marks our own opinion. `UNVERIFIED` marks a domain statement that has no verified source.
- **Requirement ID prefixes in this file:** `QD-RE` rules engine, `QD-AN` analytics, `QD-TX` shot taxonomy, `QD-DR` drill library, `QD-PL` plan logic, `QD-TR` testability, `QD-GD` golden datasets, `QD-QG` quality gates. The BA will renumber them into `FR-*`/`NFR-*`.

---

## 0. Evidence status (read this first)

1. **No pickleball rule is verified, and that has not changed today.** On 2026-10-03 we re-tried `usapickleball.org` (the Official Rulebook PDF and the Rules Summary PDF) and `en.wikipedia.org` from this sandbox. All three returned `CONNECT tunnel failed, response 403`. This matches DOM Gaps 1. Every rule below is UNVERIFIED and comes from DOM G1 R1-R6 (search snippets and background knowledge).
2. **Consequence:** every rules-engine row in §2 is tagged `@needs-verification`, as required by `testing-strategy.md` §3 and `definition-of-ready.md` "Domain truth". **Action for the human product owner:** supply the 2026 USAP Official Rulebook and the change document [DOM/DOMAIN-01, DOM/DOMAIN-02, both unverified]. The coach will then record the rule number and exact wording for each row in `docs/domain/rules-verified.md`.
3. **No coaching source is verified** [DOM G2, DOM Gaps 2]. Metric definitions (§3), shot definitions (§4) and drill content (§5) are therefore (judgment) by the coach until sourced.
4. **Verified process sources we rely on:** Gherkin format [DPA/PROD-01, DPA/PROD-02]; unit-test rules [EP/ENG-17]; TDD [EP/ENG-18]; test levels [EP/ENG-20]; regression vs capability evals, pass@k and pass^k [EP/ENG-27, DPA/AI-05]; LLM output treated as untrusted [AQS/SEC-08]; HAX confidence and explanation guidelines [DPA/DESIGN-11]; TrackEval/HOTA [DOM/CV-08]; ball metrics [DOM/CV-01]; stroke-level annotation prior art [DOM/CV-18].

**Design principle that follows (judgment):** the rules engine must be **fully parameterised**. Anything we cannot verify (target score, win-by margin, the first-server exception, the rally-scoring game-point restriction, server rotation) becomes a field in a versioned `RulesConfig`, not a hard-coded constant. After verification only the config values and test tables change, not the engine structure. This contains the cost of the verification gap.

---

## 1. Challenges to the spec and to the sibling brainstorms

| # | Position challenged | Evidence / reasoning | Proposal |
|---|---|---|---|
| X1 | Spec §6: weaknesses are ranked by **"points lost per match"**. | Under side-out scoring only the serving side scores [DOM G1 R2, UNVERIFIED]. A rally lost while serving gives the opponent **no point**. It costs a serve (server 1 → 2, or a side-out). A rally lost while receiving gives the opponent a point. So "points lost" undercounts serving-side errors, which are exactly the errors coaches care about on the third shot (judgment). | Rank by **rallies lost per game** attributable to each weakness, split into `lost_on_serve` and `lost_on_receive`. Show "points conceded" separately. Under rally scoring the two measures coincide. Add an invariant test: the attributions sum exactly to the total rallies lost (QD-AN-00). |
| X2 | Spec §4 data model: `Match → Rally`. There is no `Game`, and `Rally` has only "server" and "score before/after". | The engine needs per-game state: game number, target, the first serving side, the starting score when the video begins mid-game, and an end-switch flag. A rally needs serving side, server number (doubles), server player, a counted/replayed status, and `rules_version` [DOM G1 R1]. | Add a `Game` entity inside the `Match` aggregate. Add `serving_side`, `server_number`, `server_player_id`, `score_call` (the text called, e.g. "4-6-2"), `status ∈ {counted, replayed, gap}` and `rules_version` (via Match) to `Rally`. Principal-engineer to confirm in the DDD model. |
| X3 | Spec §4 `Rally` ending types are "winner / error / fault". | A fault is a kind of error, so the three values overlap. Coaches also distinguish **forced vs unforced** errors (judgment, a standard coaching distinction but not verified [DOM G2]). That distinction is subjective, so it needs a written definition and an agreement test. | Use the ending taxonomy `winner`, `unforced_error`, `forced_error`, `fault{serve, nvz, two_bounce, foot, other}`, `replay`. Accept the forced/unforced label only if two labellers reach Cohen's κ ≥ 0.6 on a 200-rally sample (judgment). Otherwise merge both into `error` for v1 analytics. |
| X4 | Spec §3 step 7 treats the shot taxonomy as a single label: serve, return, drive, drop, dink, lob, volley, speed-up, reset, erne, ATP. | These labels sit on different axes (judgment, domain): *sequence position* (serve, return, third), *trajectory* (drive, drop, dink, lob), *contact* (volley vs groundstroke), *intent* (speed-up, reset) and *special technique* (erne, ATP). A volley can also be a dink or a speed-up. A single-label classifier forces wrong labels and cannot be scored fairly. ShuttleSet annotates strokes at the level of individual attributes [DOM/CV-18]. | Make the taxonomy **faceted (multi-axis)**, see §4 QD-TX-01. Each facet is measured with its own F1. This replaces the engineering brainstorm's single coarse/fine hierarchy (§5.5), while keeping its "coarse first" sequencing. |
| X5 | Spec §5: metrics carry "a sample size" with no threshold. Product brainstorm US-501: flag when n < 10 rallies. | A flat n threshold ignores the size of the effect. A 7/8 success rate and a 4/8 rate have very different uncertainty (judgment, basic statistics). | For proportion metrics, show a 95% **Wilson interval** and flag "low sample" when n < 20 **or** the interval is wider than 30 percentage points. Count metrics (per game) are flagged when fewer than 2 games are in scope. All thresholds are (judgment), live in config, and are reviewed at the M4 retro. |
| X6 | Spec §6 step 4: "after the next match is uploaded, the plan is scored: did the targeted metrics move?" | One match of data cannot separate change from noise (see X5). Telling a player their plan "worked" or "failed" from noise erodes trust. HAX asks the system to make clear how well it can do what it does [DPA/DESIGN-11]. | Report "improved" or "declined" only when the before and after windows each have n ≥ 20 for the metric **and** their Wilson intervals do not overlap. Otherwise show "not enough data yet (n = x of 20)". Needs a Gherkin scenario (§7, F-07). |
| X7 | Spec M5: drill library of "~80 drills". | Count is a vanity target. What matters is coverage of each metric the plan can target, at each level, with solo and partner options (judgment). | Gate the library on the **coverage matrix** in QD-DR-05, not on a count. 80 drills is a likely outcome, not a criterion. |
| X8 | Spec M0 "Done when: … a **correct** score sheet". | "Correct" cannot be shown while the rules are unverified [DOM G1]. We agree with product brainstorm C3. | Split the criterion. **M0a:** the score sheet matches the golden tables for the configured `RulesConfig` (`@needs-verification`). **M0b:** after rule verification, it matches ≥ 10 hand-scored real games exactly (QD-GD-02). A release cannot claim "official scoring" until M0b passes (QD-QG-R3). |
| X9 | Engineering brainstorm §5.4 redefinition of M3 ("≤ 2 corrections per game at MVP, ≤ 5 confirmations, ≥ 95% of unflagged rallies correct"). | We agree, and the QA measurement needs to be pinned down. | A *score-affecting field* is: rally winner side, rally status (counted/replayed), or the fault-by side. Measure on the frozen gold set (QD-GD-04) with the correction counted by a scripted "oracle user" who fixes every mismatch with the gold labels. "Unflagged rally correct" is measured across **all** gold games pooled, with a 95% CI lower bound ≥ 93% (judgment). |
| X10 | Product brainstorm US-401 Quick Tag: "my unforced error". | Doubles analytics need to know **which player** erred, not just the side (spec §5 "unforced errors by shot type"; positioning analytics are per player). | Quick Tag captures `winner_side` + `ending` + an optional `responsible_player` (one extra tap, skippable). Metrics that need the player show "player not tagged in x rallies" instead of guessing. |
| X11 | Spec §5 positioning ("player heatmaps") and serve/return depth assume a fixed camera frame of reference. | Players change ends between games (UNVERIFIED, background knowledge). The homography maps points on the court plane only [DOM/CV-12, DOM G6 H1]. | All court coordinates are stored in a **team-relative frame** (own baseline = y 0), normalised per game using an `ends_switched` flag. Test: the same rally filmed from each end produces identical team-relative heatmap cells (QD-TR-09). |

---

## 2. Rules engine requirements (sport plug-in: pickleball)

### 2.1 Shape

- **QD-RE-01 Pure function.** `apply(state, rally_outcome, config) → state' | DomainError`. It does no I/O and uses no clock or randomness, so tests run in milliseconds without mocks [EP/ENG-17]. Replay is `fold(apply, initial_state, outcomes)`.
- **QD-RE-02 Versioned config.** `RulesConfig { rules_version, format ∈ {singles, doubles}, scoring ∈ {side_out, rally}, points_to_win, win_by, first_service_turn_single_server: bool, rally_game_point_serving_only: bool, … }`. `rules_version` is pinned per match, e.g. `"USAP-2026"` [DOM G1 R1, UNVERIFIED]. Each verified edition ships as a named preset. A match keeps the preset it was scored under, even after a newer preset ships.
- **QD-RE-03 State.** `{game_no, score[A], score[B], serving_side, server_number ∈ {1,2} (doubles only), server_player, right_court_player[side], game_over, winner}`.
- **QD-RE-04 Score call output.** For doubles, the call is three numbers: serving score, receiving score, server number. For singles it is two numbers [DOM G1 R6, UNVERIFIED]. The call is a pure projection of state and is snapshot-tested.
- **QD-RE-05 Domain errors, never exceptions.** Applying a rally after game over, an illegal start state, or an unknown outcome type returns a typed `DomainError`. Unhandled exceptions in the engine fail the build (SEC-12 "fail closed" spirit [AQS/SEC-12]).
- **QD-RE-06 Mid-game start.** A user can declare a start state (e.g. video begins at "4-6-2", A serving). The state is validated: the server number must be 1 or 2 (doubles only), and the state must not already be game over (score ≥ target with a lead ≥ win_by).
- **QD-RE-07 Gaps and resync.** A `gap` rally (an untagged or missing part of the video) is allowed only if followed by a user-declared **resync state**. Analytics exclude rallies in a gap. The score sheet shows the gap explicitly.
- **QD-RE-08 Replay.** A `replay` outcome (rally replayed, e.g. interference) changes nothing: same score, same server (UNVERIFIED that it exists in this form; the coach confirms the rule number).
- **QD-RE-09 Fault semantics.** Every fault is scored as "the faulting side loses the rally". The fault subtype affects **only** analytics. Invariant: for a fixed faulting side, the next state is independent of fault subtype.
- **QD-RE-10 Corrections replay deterministically.** Changing rally *k* re-folds rallies *k..n*. If the new fold ends a game earlier than before, the rallies after the new game end are **not dropped**. They are marked `conflict` and the user must resolve them (move them to the next game, or undo). The same applies when a game that had ended now does not end.
- **QD-RE-11 No hidden assumptions about who serves next game.** The first serving side of each game is an explicit input, and the UI defaults it to a value the coach has verified. The engine does not infer it (judgment; the rule is unverified).

### 2.2 Edge-case catalogue (table-driven `Scenario Outline` data)

All rows are `@needs-verification` and derive from DOM G1 R2, R3, R6 (UNVERIFIED). The coach adds the rule number to each row before the story is Ready. Notation: `A-B-n` = serving score, receiving score, server number.

**Side-out doubles (SOD)** with preset `points_to_win = 11`, `win_by = 2`, single server on the first turn:

| ID | Before (serving side) | Rally won by | After | Note |
|---|---|---|---|---|
| SOD-01 | 0-0-2 (A) | serving | 1-0-2 (A) | First-turn exception: the game starts on server 2 |
| SOD-02 | 0-0-2 (A) | receiving | 0-0-1 (B) | Immediate side-out; B starts on server 1 |
| SOD-03 | 3-5-1 (A) | receiving | 3-5-2 (A) | Partner serves; no point |
| SOD-04 | 3-5-2 (A) | receiving | 5-3-1 (B) | Side-out; call flips perspective |
| SOD-05 | 7-4-1 (A) | serving | 8-4-1 (A) | Same server; server switches court side (UNVERIFIED) |
| SOD-06 | 7-4-1 (A) | serving | receiving players keep their positions | Position invariant (UNVERIFIED) |
| SOD-07 | 10-8-1 (A) | serving | game over, A wins 11-8 | |
| SOD-08 | 10-10-1 (A) | serving | 11-10-1, not over | Win by 2 |
| SOD-09 | 11-10-2 (A) | serving | game over, A wins 12-10 | |
| SOD-10 | 10-9-2 (A) | receiving | 9-10-1 (B) | B at 9 is **not** at game point. A receiving side can never win the game on a rally it wins as receiver |
| SOD-11 | 21-20-1 (A) | serving | game over, A wins 22-20 | No cap; property test runs to 50+ |
| SOD-12 | game over | any | `DomainError.GameOver` | QD-RE-05 |
| SOD-13 | start declared "0-0-1" mid-game | — | accepted | Legal after a first side-out |
| SOD-14 | start declared "12-9-1" | — | `DomainError.IllegalStart` | Already game over |
| SOD-15 | start declared "4-6-3" | — | `DomainError.IllegalStart` | Server number out of range |
| SOD-16 | 5-5-1 (A) | replay | 5-5-1 (A) | QD-RE-08 |

**Faults (F)**, doubles side-out, applied on top of SOD:

| ID | Before | Fault by | Fault type | After |
|---|---|---|---|---|
| F-01 | 4-2-1 (A) | serving (server) | serve (e.g. into the NVZ incl. its line [DOM G1 R6, UNVERIFIED]) | 4-2-2 (A) |
| F-02 | 4-2-2 (A) | serving | foot fault on serve | 2-4-1 (B) |
| F-03 | 4-2-1 (A) | receiving | two-bounce violation (volleyed the serve) [DOM G1 R4, UNVERIFIED] | 5-2-1 (A) |
| F-04 | 4-2-1 (A) | serving | two-bounce violation (volleyed the return) | 4-2-2 (A) |
| F-05 | 4-2-1 (A) | receiving | NVZ volley fault incl. momentum [DOM G1 R5/R6, UNVERIFIED] | 5-2-1 (A) |
| F-06 | 4-2-1 (A) | either side, same row with each fault type | each type | identical to the generic "side X lost the rally" (QD-RE-09) |

**Side-out singles (SOS):** two-number call. A rally lost by the server is a side-out (there is no server 2). The server serves from the right when their own score is even and from the left when it is odd [DOM G1 R6, UNVERIFIED]. Rows: 0-0 start, a side-out at 0-0, 10-10 → 11-10 not over, 12-10 over, `DomainError` after game over, and court side by parity for scores 0..12.

**Rally scoring (RS)**, **blocked** until verified. Rally scoring is reported as a provisional option, and in 2026 the game-winning point is reportedly no longer limited to the serving side [DOM G1 R3, UNVERIFIED]. The engine supports both behaviours through `rally_game_point_serving_only`. Rows to fill after verification: target score values offered, win-by, server rotation in doubles (single server per turn or not), the score call format, and the game-point rule under each flag value. **No rally-scoring preset ships with a guessed rotation rule** (judgment).

**Match level (M):** best-of-1 and best-of-3 games; who serves first in each game is an explicit input (QD-RE-11); an end-switch flag per game (QD-RE-11, X11); a match is over when one side has won ⌈n/2⌉ games; rallies after match over return `DomainError`.

The 8 M rows (enumerated in the principal-engineer review, 2026-10-03, review-log RL-04, so that NFR-001's "8 M" is testable). They assert behaviour for explicit inputs (match format, first server, end switch) and make no rulebook claim, so they are engine mechanics under ADR 0009 (judgment):

| ID | Given | When | Then |
|---|---|---|---|
| M-01 | best of 1; side B wins game 1 | — | match won by B, 1-0 |
| M-02 | best of 3; side A wins games 1 and 2 | — | match won by A, 2-0; no game 3 |
| M-03 | best of 3; games split 1-1 | — | match not over; game 3 is open |
| M-04 | best of 3; A wins game 1, B wins games 2 and 3 | — | match won by B, 2-1 |
| M-05 | match decided | any rally applied | `DomainError.MatchOver` |
| M-06 | game 1 ended; input says B serves first in game 2 | game 2 starts | B serving; never inferred |
| M-07 | game 2 started with input "ends switched" | — | game 2 records `ends_switched = true` |
| M-08 | best of 1 decided | a rally is applied to game 2 | `DomainError.MatchOver` (no game beyond the format) |

**Corrections (C):** C-01 flip rally 5 of 30 and assert that states 5..30 equal a fresh fold. C-02 a flip that ends the game at rally 18 marks rallies 19..22 `conflict` (QD-RE-10). C-03 a flip that un-ends game 1 marks the first rallies of game 2 `conflict`. C-04 undo the correction and get a byte-identical score sheet.

**Minimum table size (judgment):** ≥ 16 SOD + 6 F + 12 SOS + 8 M + 4 C = **46 rows** before rule verification, and ≥ 12 RS rows after it.

### 2.3 Properties (property-based tests, ≥ 1,000 random rally sequences per scoring system per CI run; judgment)

- P1 The scores never decrease, and each counted rally adds at most 1 to exactly one side.
- P2 Under side-out scoring, a side's score rises only on a rally it won **as the serving side**.
- P3 Under rally scoring, every counted rally adds exactly 1 to the rally winner (subject to the `rally_game_point_serving_only` exception).
- P4 `server_number ∈ {1, 2}` in doubles. In side-out doubles, two consecutive serving-side losses at server 2 cannot happen without a side-out in between.
- P5 `game_over` ⇔ max(score) ≥ points_to_win ∧ |A − B| ≥ win_by, and it becomes true at the **first** rally where this holds.
- P6 Replay determinism: `fold(outcomes)` equals the sequence of single `apply` calls, and folding a prefix and then the suffix gives the same result.
- P7 Fault-subtype independence (QD-RE-09).
- P8 `replay` and `gap` rallies are identity on the score.
- P9 **Differential oracle:** a second, independent engine written by the QA agent (writer/reviewer split [DPA/AI-08]) agrees with the production engine on 100,000 random sequences per nightly run (judgment). Any disagreement is a blocking defect in one or the other.

---

## 3. Analytics definitions coaches accept

### 3.1 Rules for every metric

- **QD-AN-00 Attribution conservation.** For each game, the rallies lost attributed to all weakness categories plus `unattributed` equal the total rallies lost, split by serve/receive (X1). This is a unit-tested invariant.
- **QD-AN-01 Metric dictionary.** Each metric is a versioned entry: `id`, `version`, `name`, `formula` (numerator and denominator in domain terms), `unit`, `data_level` (QT = Quick Tag, FT = Full Tag or automatic shots), `min_sample`, `owner = pickleball-domain-coach`, `status ∈ {draft, coach-reviewed, verified}`, and a `source` or "(judgment)". The UI shows only `coach-reviewed` or `verified` metrics (judgment).
- **QD-AN-02 Definition correctness is tested separately from vision accuracy.** On gold *tags*, a metric must equal the coach's hand count **exactly** (it is deterministic arithmetic). On *automatic* events it is held to the per-metric tolerance in QD-QG-S6. This separation keeps a definition bug from hiding inside model noise (judgment).
- **QD-AN-03 Coach acceptance protocol.** Before a metric's status becomes `coach-reviewed`, the coach hand-computes it on 3 golden matches (QD-GD-03). The system must match exactly. A second coach or experienced player recomputes 1 match, and any disagreement in the *definition* (not arithmetic) means the definition text is revised (judgment).
- **QD-AN-04 Uncertainty display.** This applies X5: a Wilson 95% interval, the "low sample" flag, and metrics that are flagged but never hidden (spec §5). Every insight links to its clips (spec §6) and shows n [DPA/DESIGN-11].
- **QD-AN-05 Spatial metrics use the team-relative frame** (X11) and only ground-plane points: player feet and ball bounces [DOM G6 H1, DOM/CV-12]. No metric may use the court-plane position of an airborne ball.

### 3.2 Starter dictionary (all definitions are (judgment) by the coach until sourced [DOM G2])

| ID | Metric | Definition (numerator / denominator) | Level | Min sample | Release |
|---|---|---|---|---|---|
| AN-01 | Serve rally win % | rallies won while serving / rallies served | QT | n ≥ 20 rallies | R1 |
| AN-02 | Side-out % | rallies won while receiving / rallies received | QT | n ≥ 20 | R1 |
| AN-03 | Points per service turn | points scored / service turns (a turn = server 1 + server 2 in doubles) | QT | ≥ 10 turns | R1 |
| AN-04 | Unforced errors per game | UE count / games, per player when `responsible_player` is tagged (X10) | QT | ≥ 2 games | R1 |
| AN-05 | Serve fault % | serve faults / serves | QT | n ≥ 20 | R1 |
| AN-06 | Longest run; run histogram | consecutive points by one side without the other scoring | QT | — (descriptive) | R1 |
| AN-07 | Rally-ending mix | share of winner / UE / forced error / fault per side | QT | n ≥ 20 | R1 |
| AN-08 | Return depth | returns bouncing in the deepest third between the NVZ line and the baseline / returns in play | FT | n ≥ 20 | R2 |
| AN-09 | Third-shot mix | drop / drive / lob / other share of third shots | FT | n ≥ 20 | R2 |
| AN-10 | Third-shot drop success | drop bounces in the opponent NVZ **or** the opponent's next shot is not an attack (not a speed-up or drive), **and** the serving side does not lose the rally within the next 2 shots | FT | n ≥ 15 drops | R2 |
| AN-11 | Arrival at the NVZ | rallies where both serving-side players reach ≤ 1.0 m from their NVZ line by their side's 5th shot / serving rallies that reach a 5th shot | FT + tracking | n ≥ 15 | R2 |
| AN-12 | Lost in transition | rallies lost where the losing side's last shot was hit from the transition zone / rallies lost | FT + tracking | n ≥ 20 | R2 |
| AN-13 | Dink battle stats | length (consecutive dinks), cross vs straight share, first speed-up by, speed-up success (the speed-up side wins the rally within 2 shots) | FT | ≥ 10 dink battles | R2 |
| AN-14 | Errors by shot facet × zone | UE + forced error counted per (trajectory facet, 3×3 team-relative zone) | FT | per cell n ≥ 5, else merged | R2 |
| AN-15 | Pattern n-grams | shot facet sequences n = 3..5 with support ≥ 10 occurrences, ranked by rally win rate with a Wilson interval | FT | support ≥ 10 | R2 |
| AN-16 | Middle left open | rally time where the lateral gap between partners is > 50% of court width / rally time | tracking | ≥ 10 rallies | R2 |

The thresholds (1.0 m, "deepest third", 50%, 2 shots) live in metric config and are coach-tunable. Court dimensions (NVZ 7 ft [DOM G1 R5, UNVERIFIED]) come from `CourtModel`, never from literals in metric code.

---

## 4. Shot taxonomy

- **QD-TX-01 Faceted labels** (X4). `position ∈ {serve, return, third, fourth, later}` is derived by rule, never classified. `contact ∈ {groundstroke, volley}` is derived from bounce events where possible. `trajectory ∈ {drive, drop, dink, lob}`. `intent ∈ {neutral, speed_up, reset}`. `technique ∈ {none, erne, atp}`. A `hybrid` third-shot trajectory value is a candidate [DOM G2 C2].
- **QD-TX-02 Labelling guide.** `docs/domain/shot-taxonomy.md` gives, per value, a definition, 3 positive and 2 near-miss clip examples, and its status (UNVERIFIED until sourced).
- **QD-TX-03 Agreement before training.** A facet is admitted to the gold set only when two labellers reach Cohen's κ ≥ 0.7 on ≥ 300 shots (judgment). The κ is recorded in the gold-set manifest. A facet below 0.7 means the definition is rewritten, not that the labels are averaged.
- **QD-TX-04 Release order.** R2: `position` and `trajectory`. Later: `intent` and `technique`. This keeps the engineering brainstorm's coarse-first order [brainstorm-engineering §5.5].

---

## 5. Drill library structure

- **QD-DR-01 Schema** (one YAML or JSON file per drill, validated by JSON Schema in CI; judgment):
  `id` (immutable slug, e.g. `pb.drop.third-shot-ladder`), `version`, `name`, `summary`, `skills[]` (controlled vocabulary = metric IDs plus facet values), `target_metrics[]` (≥ 1 `AN-*` ID), `level_min`, `level_max` (`beginner | intermediate | advanced`, judgment), `duration_min` and `duration_max` (minutes), `players ∈ {1, 2, 3, 4}`, `needs ∈ {wall, half_court, full_court, ball_machine, partner_feeder}`, `equipment[]`, `setup` (steps), `success_criterion` (measurable, e.g. "8 of 10 drops bounce in the NVZ"), `progressions[]` and `regressions[]` (drill IDs), `safety_notes`, `source` (a verified source ID) **or** `coach_rationale` labelled (judgment), `review_status ∈ {draft, coach-reviewed, verified}`, `deprecated_by` (optional).
- **QD-DR-02 Immutability.** Drills are deprecated, never deleted, because saved plans reference `(id, version)`. Content edits bump `version`.
- **QD-DR-03 Lint rules (CI, blocking).** Every `target_metrics` ID exists in the dictionary. Every progression and regression ID exists, and there are no cycles. `duration_min ≤ duration_max ≤ 45`. `success_criterion` contains a number. Every drill has either `source` or `coach_rationale`. The LLM is shown only drills in `coach-reviewed` or `verified` status.
- **QD-DR-04 Safety escalation.** Any drill involving overhead lobs retreating backwards, diving, or high-intensity footwork carries `safety_notes`. Content that could cause injury is escalated to the EM and the human PO (domain-coach agent definition).
- **QD-DR-05 Coverage matrix (replaces the "~80" count, X7).** For each targetable metric (AN-04, -05, -08..-14, -16) × each level: ≥ 2 drills, of which ≥ 1 has `players ≤ 2` and ≥ 1 needs no ball machine. For R1 (AN-01..-07 only): ≥ 20 drills satisfying the matrix for the QT metrics [product brainstorm US-602]. The CI job prints the matrix and fails on empty cells in scope.

### 5.1 Plan-assembly rules (deterministic layer, before and after any LLM)

- **QD-PL-01** Total session time is ≤ the player's stated time per session. The plan's weekly total is ≤ the stated weekly hours (product US-601).
- **QD-PL-02** The drills chosen match the player's available `players` count and `needs` (no ball-machine drill for a player without one).
- **QD-PL-03** Each session starts with a warm-up drill (judgment; coach to source). No single drill takes more than 40% of a session (judgment).
- **QD-PL-04** Each assignment cites `(metric_id, value, n, clip_ids)`. The "why" text must name the metric and its value [DPA/DESIGN-11, spec §6].
- **QD-PL-05 LLM output validation** [AQS/SEC-08]: unknown drill ID or version, unknown metric, violated QD-PL-01..-03, or a missing citation → reject, retry once, then fall back to the rules-only plan (product brainstorm C10).
- **QD-PL-06** If the top weakness has a low sample (X5), the plan says so and shows n (product US-601 "Not enough data").

---

## 6. Testability requirements

| ID | Requirement | Basis |
|---|---|---|
| QD-TR-01 | The rules engine, metric functions and plan rules are pure and importable without the API, DB, GPU or network | [EP/ENG-17] |
| QD-TR-02 | All times are integer milliseconds from video start; there is no wall-clock in domain code; the clock is injected where it is needed | [EP/ENG-20] design-for-testability (application is judgment) |
| QD-TR-03 | Test-data builders exist: `a_doubles_game().at("4-6-2").serving("A")`, `rallies("SSRRS…")` — one builder per aggregate | (judgment) |
| QD-TR-04 | Scoring and metrics are recomputable from stored outcomes alone (event replay). A golden replay of stored rallies must reproduce the stored score sheet byte for byte | ddd-guidelines context map, `RallyScored`/`ScoreCorrected` |
| QD-TR-05 | Vision → Match & Scoring goes through an anticorruption layer with a contract test: a fixture of raw events maps to the expected rallies and shots | ddd-guidelines §3 |
| QD-TR-06 | The LLM sits behind an interface. CI uses recorded fake responses, including adversarial ones (unknown drill ID, missing citation, over-time plan) | [EP/ENG-17], [AQS/SEC-08] |
| QD-TR-07 | Every scoring scenario row carries `@rule-<number>` after verification; until then `@needs-verification` | [DOM G1], testing-strategy §3 |
| QD-TR-08 | Each metric has unit tests on hand-built rally fixtures covering: an empty match, n = min_sample − 1 (flagged), all-wins, all-losses, gap rallies excluded, and replay rallies excluded | [EP/ENG-17, EP/ENG-18] |
| QD-TR-09 | A coordinate-frame test: the same rally from either end gives identical team-relative zones (X11) | (judgment) |
| QD-TR-10 | The confidence for each automatic call is exposed in the API, so tests can assert flagging thresholds | [DPA/DESIGN-11] |
| QD-TR-11 | Each pipeline run records `pipeline_version` and `rules_version` and the metric dictionary version, so any number can be reproduced | ddd-guidelines glossary |

---

## 7. Acceptance test scenarios (Gherkin, declarative, 3-5 steps [DPA/PROD-01, DPA/PROD-02])

These are illustrative and tagged as required. Full tables come from §2.2.

```gherkin
@M0 @needs-verification
Feature: F-01 Side-out doubles scoring
  Rule: Only the serving side scores; a lost serve passes to the partner, then to the other side
    Scenario Outline: Score after one rally
      Given a doubles game under side-out scoring at "<before>" with <side> serving
      When the <winner> side wins the rally
      Then the score is called "<after>"
      Examples: (rows SOD-01..SOD-11 and F-01..F-05 from §2.2)

@M0 @needs-verification
Feature: F-02 Starting a score sheet mid-game
  Scenario: Video begins part-way through a game
    Given Ivy's video starts at "4-6-2" with her side receiving
    When she tags the first rally as won by her side
    Then the score sheet shows "6-4-1" with her side serving
  Scenario: Impossible start score is refused
    Given Ivy declares a start score of "12-9-1"
    Then she is told the game would already be over and asked to correct it

@M0
Feature: F-03 Correcting a rally that changes the end of a game
  Scenario: Correction ends the game earlier
    Given a tagged game in which side A won 12-10 after 24 rallies
    When Ivy changes rally 20 to "won by side A"
    Then the game shows as won by side A at rally 20
    And rallies 21 to 24 are listed as needing her decision, not deleted

@M4
Feature: F-04 Metrics show their uncertainty
  Rule: Small samples are flagged, never hidden
    Scenario Outline: Low-sample flag
      Given Ivy received serve in <n> rallies and won <won>
      When she opens her stats
      Then "side-out %" shows <pct> with "n = <n>" and low-sample label "<flag>"
      Examples:
        | n  | won | pct | flag |
        | 8  | 4   | 50% | yes  |
        | 40 | 22  | 55% | no   |

@M4
Feature: F-05 Metric definitions match a coach's hand count
  Scenario: Golden match agreement
    Given golden match GM-03 with the coach's hand-counted metrics
    When the analytics are computed from its gold tags
    Then every R1 metric equals the coach's value exactly

@M5
Feature: F-06 Plans respect the player's constraints
  Scenario: Solo player with 30 minutes
    Given Ivy practises alone for 30 minutes per session without a ball machine
    When she generates a plan
    Then every session lasts at most 30 minutes
    And every drill can be done by one player without a ball machine
  Scenario: Coaching model proposes a drill that is not in the library
    Given the coaching model answers with drill "pb.unknown.drill"
    When the plan is validated
    Then the plan is not saved from that answer
    And Ivy receives the rules-only plan with the same constraints

@M5
Feature: F-07 Plan follow-up does not over-claim
  Scenario: Too little data after one match
    Given Ivy's plan targeted "third-shot drop success" with 18 drops before the plan
    And her next match has 9 drops
    When the follow-up is shown
    Then it says "not enough data yet (n = 9 of 20)" instead of improved or declined

@M5
Feature: F-08 Drill library integrity
  Scenario: A drill targets an unknown metric
    Given a drill file that targets metric "AN-99"
    When the library is validated
    Then validation fails naming the drill and the unknown metric
```

**End-to-end journey (Playwright, nightly) [EP/ENG-20, AQS/STACK-03]:** upload the 60-second fixture clip → Quick Tag the 6 rallies in the fixture → the score sheet equals the golden sheet → the stats page shows the AN-01..-07 values from the golden file → the plan has ≥ 1 session, each drill is from the library, and each cites a metric.

---

## 8. Golden datasets

Every set has a `manifest.json` containing: `id`, `version`, `sha256` per file, `created`, `rules_version`, `metric_dict_version`, labeller role IDs, inter-labeller κ (where relevant), licence, consent status, and split (judgment). Sets are frozen per sprint, and **nobody edits a gold set to improve a score**; a change needs an ADR (testing-strategy §6, [EP/ENG-27, EP/ENG-28]).

| ID | Contents | Size target (judgment) | Purpose | Ready by |
|---|---|---|---|---|
| QD-GD-01 | Synthetic rules tables (§2.2) plus property seeds | ≥ 46 rows, ≥ 12 RS rows after verification | Engine TDD | Sprint 1 |
| QD-GD-02 | Hand-scored real games: rally outcomes plus the expected score call per rally, scored independently by 2 people | ≥ 10 side-out doubles games, ≥ 3 singles, ≥ 3 rally-scoring games | M0b "correct score sheet" (X8) | After rule verification |
| QD-GD-03 | Golden matches with Full Tag plus the coach's hand-computed metrics | 3 matches for R1 metrics, 10 for R2 metrics | QD-AN-02/-03 | R1: M0; R2: before M4 |
| QD-GD-04 | Vision gold (owned by senior-ml-cv-engineer; QA requirements only): split by venue with ≥ 3 venues held out, 20% of clips double-labelled, κ recorded per facet | Per engineering brainstorm §5.2-5.3 | M1-M3 gates, X9 | M1 |
| QD-GD-05 | Coaching eval cases: player profiles from real tagged matches, including adversarial cases (no partner, 20 min only, low sample, conflicting weaknesses) | 30 cases (within the 20-50 range [DPA/AI-05, AQS/AI-03]) | QD-QG-S7 | Before M5 |
| QD-GD-06 | Drill library snapshot plus coverage matrix | Per QD-DR-05 | Plan tests | R1 |
| QD-GD-07 | Fixture clips (≤ 60 s each) with known rallies, events and ID switches | ≥ 5: good light, backlight, fence occlusion, 30 fps, multi-court audio | Integration and E2E | M0 (one), M2 (all) |

**Licensing and consent:** SportsMOT is evaluation-only (CC BY-NC) [DOM/CV-09]. Gold-set videos show third parties; their consent and retention basis is an **open privacy question** (privacy law is unverified [AQS G3.5]) and is escalated to the human PO before any real-match gold set is created.

---

## 9. Quality gates (measurable)

### Per PR (blocking, automated by hook or CI [AQS/AI-05])
- **QD-QG-P1** All unit, scenario and integration tests are green, and no test was edited or deleted without QA approval [EP/ENG-28, DPA/AI-12].
- **QD-QG-P2** Coverage on changed code: rules engine and aggregates ≥ 95% line and ≥ 90% branch; analytics ≥ 90% (testing-strategy §8, judgment).
- **QD-QG-P3** The rules-engine property suite (P1-P8, ≥ 1,000 sequences per scoring system) passes. The unit suite finishes in < 10 s (judgment, consistent with "seconds" [EP/ENG-17]).
- **QD-QG-P4** The drill-library lint (QD-DR-03) and metric-dictionary schema validation pass.
- **QD-QG-P5** No new `@needs-verification` scenario is counted as satisfying a Must FR. The scenario reports list them separately.

### Per sprint
- **QD-QG-S1** Nightly differential-oracle run (P9) with 0 disagreements.
- **QD-QG-S2** Mutation score ≥ 85% on `sports/pickleball/rules` (tool choice is judgment, e.g. mutmut).
- **QD-QG-S3** Flaky rate < 1% of test runs over the sprint. Any flaky test is quarantined within 1 day with an owner (testing-strategy §9).
- **QD-QG-S4** The E2E journey (§7) is green on `main` for ≥ 5 consecutive nightly runs before sprint review.
- **QD-QG-S5** Analytics: 100% exact match on QD-GD-03 for every metric with status ≥ `coach-reviewed` (QD-AN-02).
- **QD-QG-S6** On automatic events vs gold: counting metrics are within ±10% relative, and rate metrics within ±5 percentage points, per match on ≥ 80% of gold matches (judgment, revisit at M4).
- **QD-QG-S7** Coaching evals [DPA/AI-05, EP/ENG-27]: code graders (drill exists, metric cited, QD-PL-01..-03) at **pass^3 = 100%** as a regression suite; model-grader rubric mean ≥ 4.0/5 on relevance and clarity; the coach hand-grades 10 cases each sprint, and the model grader must agree within ±1 point on ≥ 80% of them, otherwise the rubric is recalibrated.
- **QD-QG-S8** The model-quality regression suite shows no metric drop beyond the tolerances in its ADR [EP/ENG-27, DOM/CV-08, DOM/CV-01].

### Per release
- **QD-QG-R1** All Must stories meet the story-level DoD [EP/ENG-16].
- **QD-QG-R2** All spec milestone "Done when" criteria use the pinned definitions: X8 (M0), product C9 / CV-T09 (M2), X9 (M3).
- **QD-QG-R3** **Zero** `@needs-verification` rules scenarios in the scoring path of a release labelled with an official `rules_version`. Otherwise the UI must label the score sheet "unofficial scoring (rules not yet verified)" (judgment, HAX "make clear how well the system can do" [DPA/DESIGN-11]).
- **QD-QG-R4** Every user-visible metric and drill has status ≥ `coach-reviewed`.

---

## 10. Risks (quality and domain)

| Risk | Impact | Mitigation |
|---|---|---|
| The rulebook stays unobtainable from the sandbox | M0 cannot be called "correct"; rally scoring is blocked | The PO supplies the PDF; parameterised engine (§0); QD-QG-R3 label |
| Players mis-call their own score on video, and users trust the called score over ours | Users perceive the engine as "wrong" | Optional `called_score` tag; the UI shows the discrepancy and its cause (judgment) |
| Forced vs unforced error labels are unreliable | Noisy weakness ranking | κ gate (X3), merge fallback |
| A metric definition is disputed by coaches | Loss of trust | Dictionary versioning, the QD-AN-03 protocol, ADR for alternatives (coach agent definition) |
| Gold sets get edited to pass | False confidence | Manifest sha256 checked in CI; ADR-only changes |
| Shot-intent labels (speed-up, reset) are inherently subjective | Low classifier ceiling | Facet release order (QD-TX-04) |

---

## 11. Open questions for the human product owner

1. Can you provide the 2026 USAP Official Rulebook and change document (PDF)? Every scoring story is blocked on it [DOM/DOMAIN-01, -02].
2. Which rules editions must v1 support: USAP only, or also Pickleball Canada or GPF variants [DOM/DOMAIN-04, -05, unverified]?
3. Should rally scoring be in R1 at all, given it is provisional and its rotation details are unverified [DOM G1 R3]? We propose R2.
4. May we build gold sets from real matches showing third parties, and on what consent basis (privacy research is unverified [AQS G3.5])?
5. Do you accept "rallies lost per game" instead of "points lost per match" as the weakness ranking unit (X1)?
6. Can we recruit a second qualified coach (or a 4.0+ player) for the definition-agreement checks in QD-AN-03 and QD-TX-03?
