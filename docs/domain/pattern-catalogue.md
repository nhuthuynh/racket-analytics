# Pattern catalogue v0.1 (reference patterns)

- **Owner:** pickleball-domain-coach (COACH-6a, Sprint 6, 2026-11-13). The coach owns each definition; the business-analyst owns the `FR-171.Rk` rules these definitions make operational (BA-6), and is asked to co-review every worked example on the COACH-6a PR. Where the BA already wrote an Example in `docs/sprints/06/requirements-breakdown.md` §1, it is reused here word for word.
- **Status of every entry:** `draft` (definition v0.1). An entry becomes `coach-reviewed` after the QD-AN-03 hand count on the gold fixture GS-PAT-1 (COACH-6b; ADR 0044) and `verified` only after a human coach recomputes it (P15). Every coaching sense below is **(judgment)**: no coaching source resolves yet ([SRC-0010], [SRC-0012]; `docs/domain/sources.md` §3).
- **Requirements:** FR-171.R2-R7 (pattern measures), FR-170.R1 (`better_direction` comes from here), FR-172.R1-R3 (what is rankable), A2 (level bands), A6 (min_n and interval method) [SRC-0002]. Formulas start from QD §3.2 [SRC-0001].
- **Who uses it:** ST-171b/c/d (extractors), COACH-6b (gold fixture GS-PAT-1 and `docs/domain/tools/pattern_example.py --check`, §11), COACH-6c (reference set v1), ST-170a (lint copies `better_direction` and `interval_method` from here), ML-6 (pattern-source matrix), PD-6 (copy and states), ST-173b/c (drill `target_metrics` use the AN id).
- **Citations** are `[SRC-nnnn]` rows of `docs/domain/sources.md`. `@needs-verification` marks every line whose meaning depends on an unverified rule or coaching claim.
- **Sprint 6 build scope:** AN-09 and AN-13 (wave B), AN-08 (stretch) [SRC-0002]. AN-10 is defined here for the next wave. AN-11, AN-12, stacking and partner spacing are defined but marked **needs CV (7.1)**: no Sprint 6 story may build them (roadmap §7.1, NFR-006).

## 0. Rules for every pattern

### 0.1 Shot order

Patterns count facets of single shots, not one label per shot [SRC-0014]. Inside one rally of a Full Tag label document [SRC-0003], the `hit` events in frame order are numbered 1, 2, 3, ...

- Hit 1 is the **serve**; its hitter's side (the slot letter, `A1` → A) is the **serving side** of the rally.
- Hit 2 is the **return**; hit 3 is the **third shot**; hits 3 and later are the **rally shots**.
- Sides alternate from hit to hit. A rally whose hits 1-3 do not alternate (A, B, A or B, A, B) is excluded from AN-09, AN-10 and AN-08 with reason `side_order_invalid`: it is a labelling error, never guessed. `@needs-verification` (two-bounce rule, §0.9)

### 0.2 Universe, exclusions and conservation

- **Scope:** per side (A, B) per match, as metric dictionary rule 0.4 [SRC-0004]. The player's side is "me" from setup.
- **Match-level unassigned:** a `replay` rally (reason `replay`) and a rally with no `hit` event (reason `no_serve_hit`) belong to neither side and are reported once per match.
- **Conservation:** for each pattern and side, `counted + Σ excluded = universe`, and over the match `universe(A) + universe(B) + unassigned = all rallies` for serve-anchored patterns. ST-171 tests this as a property ("counted ∪ excluded = all", FR-171.R3).
- **Unavailable (FR-171.R5):** a pattern whose data source the match lacks is `unavailable` with a reason, never 0: `no_shot_facets` (Quick Tag only), `no_bounce_positions` (no bounce has `court_xy_m`), `needs_cv` (positions of players).

### 0.3 Uncertainty, min_n and rankability (A6)

- `interval_method: wilson` for proportions: Wilson 95 % interval [SRC-0005], computed by `wilson(k, n)` [SRC-0006]. `interval_method: order_statistic_median` for AN-13 (FR-171.R4) [SRC-0007].
- **min_n** default **20 opportunities** (A6). Below min_n the measure is `low_sample` and not `rankable` (FR-171.R6). AN-13 uses 10 (§5).
- A rankable measure can be a weakness only by FR-172.R1 (no overlap with the reference, on the worse side).

### 0.4 `better_direction`

`higher` (more is better: a weakness lies below the reference), `lower` (a weakness lies above), `inside_band` (both sides of a band are weaknesses, named "below band" or "above band"). The reference lint copies this value per definition version (FR-170.R1). A descriptive pattern (stacking) has none and is never rankable.

### 0.5 Data source tags

`QT` Quick Tag fields; `FT` Full Tag facets and events [SRC-0003]; `CV` a vision stage (player positions, ball tracking). A Sprint 6 Ready item uses only QT or FT. A CV pattern is defined here so the spike plans (ST-176b) and ML-6 know what to measure; it is built only after its roadmap §7.1 gate is met on footage (P11).

### 0.6 Level bands (A2)

| Band id | Profile `level` (plan model `LEVELS`) | Display label (judgment) | Use |
|---|---|---|---|
| `beginner` | beginner | "below 3.0" | a target band may exist |
| `intermediate` | intermediate | "3.0-3.5" | a target band may exist |
| `advanced` | advanced | "4.0 and above" | a target band may exist |
| `pro` | none (no player has it) | "pro play" | **direction only**: shown as "pros tend to ...", never as a target, never compared for ranking (A2; FR-172.R3) |

- A reference is per pattern × band × **format** (singles, doubles). A doubles reference never applies to a singles match.
- The display labels are self-rating words (judgment); the profile stores the word, not a number.
- Band **values** are reference-set content (COACH-6c), not catalogue content. No resolved statistic exists on 2026-11-13, so every v1 value is `source_type: judgment` (`docs/domain/sources.md` §3). A `pro` direction needs a resolved pro source; until then it is not shown.

### 0.7 Court frame and dimensions `@needs-verification`

- Labels v1 give `court_xy_m = [x, y]` in court metres but do not pin the axes. This catalogue uses, and asks the senior-ml-cv-engineer to confirm for labels v1 (§10 Q1): **origin at the left corner of side A's baseline (seen from side A at the rally's start), x across the court (0..6.10), y along it towards side B's baseline (0..13.41)**.
- Dimensions (judgment, UNVERIFIED until P7, [SRC-0008]): court 6.10 m × 13.41 m, net at y = 6.705, NVZ 2.13 m deep on each side. A ball on a line is in (DOM G1 R6, UNVERIFIED).
- "Distance from the net" d = |y − 6.705|. Side A's half is 0 ≤ y ≤ 6.705, side B's half 6.705 ≤ y ≤ 13.41; in court also needs 0 ≤ x ≤ 6.10.
- Only ground-plane points (bounces, feet) are placed on the court; an airborne ball never is [SRC-0013].

### 0.8 Versioning

Each entry has `definition_version` (0.1 here). Any change to a numerator, denominator, exclusion, min_n, interval method or `better_direction` bumps it; reference entries and measures keep the version they were made with (FR-170.R1).

### 0.9 Rule dependence (P7) `@needs-verification`

| Pattern | Depends on (UNVERIFIED) | Rules queue row ([SRC-0015]) |
|---|---|---|
| AN-09, AN-10, AN-08 | two-bounce rule: the return and the third shot must bounce, which is why the third shot is a distinct pattern | row 10 (FR-044.R2) |
| AN-08, AN-10, AN-11, AN-12, SPACING | court dimensions, NVZ depth, line-in rule | none yet: proposed as a new row 11 (§10 Q3) |
| AN-13 | NVZ volley rule (a dink rally can end in an NVZ fault) | row 10 |
| STACK | serving position follows the serving side's score | row 6 (FR-041.R4) |

The counting rules below are rule-free (they count labelled hits and bounces); only their coaching meaning depends on the rows above.

## 1. Summary

| Pattern | Name (UI) | Value | Data source | min_n | interval_method | better_direction | Sprint 6 |
|---|---|---|---|---|---|---|---|
| AN-09 | Third-shot drop share | drops / third shots with a trajectory | FT | 20 | wilson | inside_band | ST-171b (P0) |
| AN-10 | Third-shot drop success | successful drops / decided drops | FT | 20 | wilson | higher | defined only |
| AN-08 | Return depth (and serve depth) | deep returns / returns in play with a bounce | FT | 20 | wilson | higher | ST-171d (P2) |
| AN-13 | Dink tolerance | median dinks before the side's dink error | FT | 10 | order_statistic_median | higher | ST-171c (P0) |
| AN-11 | Arrival at the NVZ | rallies with both servers at the line by hit 5 / serving rallies reaching hit 5 | CV | 20 | wilson | higher | needs CV (7.1) |
| AN-12 | Lost in transition | rallies lost from the transition zone / rallies lost | CV | 20 | wilson | lower | needs CV (7.1) |
| STACK | Stacking | share of service turns stacked | CV | 20 | wilson | none (descriptive) | needs CV (7.1) |
| SPACING | Partner spacing (AN-16, middle left open) | rally time with a wide partner gap / rally time | CV | 20 | wilson | lower | needs CV (7.1) |
| AN-05 | Serve faults | tagged serve faults / serves by the side (metric dictionary AN-05 [SRC-0017]) | QT | 20 | wilson | lower | ST-171a (P0), wave A |
| AN-07 | Unforced-error share (`AN-07:unforced-error`) | unforced errors / rallies the side ended (metric dictionary AN-07 [SRC-0017]) | QT | 20 | wilson | lower | ST-171a (P0), wave A |
| AN-04 | Unforced errors per game | unforced errors / games (metric dictionary AN-04) | QT | 2 games | none | none (context only) | ST-171a (P0), wave A, never ranked |

**Wave A rows (COACH-6c).** AN-05, AN-07 and AN-04 keep the metric dictionary's v0.1 definitions (`coach-reviewed` 2026-10-07); these rows only add what the reference lint and the gap rule read. AN-07 is compared on its unforced-error share alone (`AN-07:unforced-error`, ADR 0061 Rule 3.1); its other three shares are descriptive. AN-04 has no interval method, so it gets no reference entry and is shown as context, never ranked (ADR 0061 Rule 3.1).

## 2. AN-09 third-shot drop share

| Field | Value |
|---|---|
| id / definition_version | AN-09 / 0.1 (FR-171.R2, R3; QD AN-09 "third-shot mix" [SRC-0001]) |
| plain-language definition | "Of your side's third shots, the share you hit as a drop rather than a drive or a lob." |
| numerator | rallies served by S whose hit 3 (by S) has `trajectory: drop` |
| denominator | rallies served by S whose hit 3 (by S) has any `trajectory` (drive, drop, dink, lob) |
| exclusions | `no_third_shot` (fewer than 3 hits), `side_order_invalid` (§0.1), `facet_missing` (hit 3 has no `trajectory`); match-level `replay`, `no_serve_hit` |
| companions (descriptive, never ranked) | the full mix: drive, lob and dink shares over the same denominator |
| min_n | 20 third shots (A6) |
| interval_method | wilson |
| better_direction | `inside_band`: too few drops (always driving) and only drops (never driving) are both gaps (judgment) |
| level bands | beginner, intermediate, advanced × singles, doubles; pro as direction only (§0.6). In singles the drop is rarer; a singles band must not reuse a doubles band (judgment) |
| data source | FT (`trajectory` facet on hit 3) [SRC-0003]; unavailable `no_shot_facets` on a Quick Tag-only match |
| rule dependence | two-bounce rule (§0.9) `@needs-verification` |
| sense (judgment) | the drop lets the serving side move forward while the receivers are already at the NVZ ([SRC-0010], unresolved) `@needs-verification` |

Rule: AN-09.1 (FR-171.R2) The third shot is the serving side's first hit after the return; its share of drops is drops / third shots with a trajectory
  Example: 10 rallies with a third shot, 6 drops, 4 drives → 0.60, n = 10 (happy; BA example). Wilson 0.313-0.832 <!-- wilson: 6 10 0.313 0.832 -->; n < 20 so `low_sample`, not rankable (FR-171.R6)
  Example: 25 third shots, 5 drops → 0.20, Wilson 0.089-0.391, rankable (happy) <!-- wilson: 5 25 0.089 0.391 -->
  Example: a rally that ends before the 3rd hit is excluded and counted in n_excluded, never as a drive (negative; BA example; rally r4 below)
Rule: AN-09.2 (FR-171.R3) A third shot with no trajectory facet is excluded with reason `facet_missing`
  Example: 10 third shots, 2 without facet → n = 8, n_excluded = 2 (happy; BA example)
  Example: a missing facet counted as a drive → the property "counted ∪ excluded = all third shots" fails (negative; BA example; rally r3 below)
Rule: AN-09.3 Hits 1-3 that do not alternate sides are excluded with reason `side_order_invalid`
  Example: hits A1, B1, A2 → counted (happy)
  Example: hits A1, B1, B2 → excluded `side_order_invalid`, not counted for side B (negative)

Worked label example W-09-a (doubles, team-made, no real people). Side A: r1 drop (counted), r2 drive (counted), r3 no facet (`facet_missing`), r4 two hits (`no_third_shot`); r5 is a replay (match-level); r6 is served by B, so it is in B's universe only.

<!-- example: W-09-a -->
```json
{"schema": "full-tag-labels/v1", "clip": "clips/w09a.mp4", "fps": 60, "frame_count": 1200,
 "players": ["A1", "A2", "B1", "B2"],
 "rallies": [
  {"id": "r1", "start_frame": 0, "end_frame": 150,
   "outcome": {"ending": "unforced_error", "winning_side": "A", "responsible_player": "B2"},
   "events": [{"type": "hit", "frame": 10, "hitter": "A1"}, {"type": "hit", "frame": 40, "hitter": "B1"},
              {"type": "hit", "frame": 70, "hitter": "A2", "facets": {"trajectory": "drop"}},
              {"type": "hit", "frame": 100, "hitter": "B2", "facets": {"trajectory": "dink"}}]},
  {"id": "r2", "start_frame": 200, "end_frame": 300, "outcome": {"ending": "winner", "winning_side": "A"},
   "events": [{"type": "hit", "frame": 210, "hitter": "A1"}, {"type": "hit", "frame": 240, "hitter": "B2"},
              {"type": "hit", "frame": 270, "hitter": "A1", "facets": {"trajectory": "drive"}}]},
  {"id": "r3", "start_frame": 400, "end_frame": 500, "outcome": {"ending": "forced_error", "winning_side": "B"},
   "events": [{"type": "hit", "frame": 410, "hitter": "A1"}, {"type": "hit", "frame": 440, "hitter": "B1"},
              {"type": "hit", "frame": 470, "hitter": "A2"}]},
  {"id": "r4", "start_frame": 600, "end_frame": 700, "outcome": {"ending": "winner", "winning_side": "B"},
   "events": [{"type": "hit", "frame": 610, "hitter": "A1"}, {"type": "hit", "frame": 640, "hitter": "B1"}]},
  {"id": "r5", "start_frame": 800, "end_frame": 850, "outcome": {"ending": "replay", "winning_side": null},
   "events": [{"type": "hit", "frame": 810, "hitter": "A1"}]},
  {"id": "r6", "start_frame": 1000, "end_frame": 1100, "outcome": {"ending": "winner", "winning_side": "A"},
   "events": [{"type": "hit", "frame": 1010, "hitter": "B1"}, {"type": "hit", "frame": 1040, "hitter": "A1"},
              {"type": "hit", "frame": 1070, "hitter": "B2", "facets": {"trajectory": "lob"}},
              {"type": "hit", "frame": 1090, "hitter": "A2", "facets": {"trajectory": "drive"}}]}
 ]}
```
<!-- expect: {"AN-09@A": {"k": 1, "n": 2, "excluded": {"facet_missing": 1, "no_third_shot": 1}, "unassigned": {"replay": 1}}, "AN-09@B": {"k": 0, "n": 1, "mix": {"lob": 1}}} -->

Expected: side A drop share 1/2 (n = 2, `low_sample`), n_excluded 2 (`facet_missing` 1, `no_third_shot` 1); side B 0/1 with mix lob 1; match-level unassigned `replay` 1. Conservation: A 2 + 2 = 4 served rallies, B 1, unassigned 1 → 6 rallies.

## 3. AN-10 third-shot drop success

| Field | Value |
|---|---|
| id / definition_version | AN-10 / 0.1 (QD AN-10 [SRC-0001]) |
| plain-language definition | "Of your third-shot drops, the share that let you move in: the drop landed in the kitchen, or the other side could not attack it, and you did not lose the rally in the next two shots." |
| numerator | AN-09-counted drops of S that are **successful**: (a) the first bounce after hit 3 lies in the opponent's NVZ, **or** the opponent's hit 4 is not an attack (absent, or `trajectory` ≠ drive and `intent` ≠ speed_up, both labelled); **and** (b) S does not lose the rally at or before hit 5 |
| denominator | AN-09-counted drops of S that are decided (successful or failed) |
| failed | (b) fails (the rally ends with ≤ 5 hits and S lost), **or** the bounce is labelled outside the NVZ **and** hit 4 is an attack (`trajectory: drive` or `intent: speed_up`) |
| exclusions | all AN-09 exclusions, plus `next_shot_unlabelled`: (b) holds but neither the bounce position nor hit 4's facets decide (a) |
| min_n | 20 decided drops (A6; QD's 15 is replaced by the A6 default) |
| interval_method | wilson |
| better_direction | `higher` |
| level bands | as AN-09 (§0.6) |
| data source | FT (hit facets `trajectory`, `intent`; bounce `court_xy_m`, §0.7) |
| rule dependence | NVZ depth (§0.9) `@needs-verification` |

Rule: AN-10.1 A drop that lands in the opponent's NVZ, or is not attacked, and is not followed by a loss within 2 shots is a success
  Example: 22 decided drops, 14 successful → 0.636, Wilson 0.430-0.803, rankable once n ≥ 20 (happy) <!-- wilson: 14 22 0.430 0.803 -->
  Example: rally r2 below: bounce outside the NVZ, B attacks with a speed-up drive and A loses on hit 5 → failed, never a success (negative)
Rule: AN-10.2 A drop whose outcome the labels cannot decide is excluded with reason `next_shot_unlabelled`
  Example: rally r1 below: bounce in the NVZ with hit 4 unlabelled → decided (success) by the bounce alone (happy)
  Example: rally r3 below: no bounce labelled and hit 4 has a trajectory but no intent → excluded, never counted as a success (negative)

Worked label example W-10-a (side A serves every rally; frame as §0.7, side B's NVZ is 6.705 ≤ y ≤ 8.835).

<!-- example: W-10-a -->
```json
{"schema": "full-tag-labels/v1", "clip": "clips/w10a.mp4", "fps": 60, "frame_count": 1200,
 "players": ["A1", "A2", "B1", "B2"],
 "rallies": [
  {"id": "r1", "start_frame": 0, "end_frame": 200,
   "outcome": {"ending": "unforced_error", "winning_side": "A", "responsible_player": "B2"},
   "events": [{"type": "hit", "frame": 10, "hitter": "A1"}, {"type": "hit", "frame": 40, "hitter": "B1"},
              {"type": "hit", "frame": 70, "hitter": "A2", "facets": {"trajectory": "drop"}},
              {"type": "bounce", "frame": 85, "visible": true, "court_xy_m": [3.0, 8.0]},
              {"type": "hit", "frame": 100, "hitter": "B1"}, {"type": "hit", "frame": 130, "hitter": "A2"},
              {"type": "hit", "frame": 160, "hitter": "B2"}]},
  {"id": "r2", "start_frame": 300, "end_frame": 450,
   "outcome": {"ending": "forced_error", "winning_side": "B", "responsible_player": "A2"},
   "events": [{"type": "hit", "frame": 310, "hitter": "A1"}, {"type": "hit", "frame": 340, "hitter": "B2"},
              {"type": "hit", "frame": 370, "hitter": "A1", "facets": {"trajectory": "drop"}},
              {"type": "bounce", "frame": 385, "visible": true, "court_xy_m": [3.0, 10.5]},
              {"type": "hit", "frame": 400, "hitter": "B2", "facets": {"trajectory": "drive", "intent": "speed_up"}},
              {"type": "hit", "frame": 430, "hitter": "A2"}]},
  {"id": "r3", "start_frame": 500, "end_frame": 700,
   "outcome": {"ending": "unforced_error", "winning_side": "A", "responsible_player": "B1"},
   "events": [{"type": "hit", "frame": 510, "hitter": "A1"}, {"type": "hit", "frame": 540, "hitter": "B1"},
              {"type": "hit", "frame": 570, "hitter": "A2", "facets": {"trajectory": "drop"}},
              {"type": "hit", "frame": 600, "hitter": "B1", "facets": {"trajectory": "dink"}},
              {"type": "hit", "frame": 620, "hitter": "A1"}, {"type": "hit", "frame": 640, "hitter": "B2"},
              {"type": "hit", "frame": 660, "hitter": "A2"}, {"type": "hit", "frame": 680, "hitter": "B1"}]},
  {"id": "r4", "start_frame": 800, "end_frame": 950, "outcome": {"ending": "winner", "winning_side": "A"},
   "events": [{"type": "hit", "frame": 810, "hitter": "A1"}, {"type": "hit", "frame": 840, "hitter": "B1"},
              {"type": "hit", "frame": 870, "hitter": "A2", "facets": {"trajectory": "drop"}},
              {"type": "bounce", "frame": 885, "visible": true, "court_xy_m": [2.0, 11.0]},
              {"type": "hit", "frame": 900, "hitter": "B1", "facets": {"trajectory": "drive", "intent": "neutral"}},
              {"type": "hit", "frame": 920, "hitter": "A1"}, {"type": "hit", "frame": 935, "hitter": "B2"},
              {"type": "hit", "frame": 945, "hitter": "A2"}]},
  {"id": "r5", "start_frame": 1000, "end_frame": 1100,
   "outcome": {"ending": "unforced_error", "winning_side": "B", "responsible_player": "A2"},
   "events": [{"type": "hit", "frame": 1010, "hitter": "A1"}, {"type": "hit", "frame": 1040, "hitter": "B1"},
              {"type": "hit", "frame": 1070, "hitter": "A2", "facets": {"trajectory": "drop"}}]}
 ]}
```
<!-- expect: {"AN-09@A": {"k": 5, "n": 5}, "AN-10@A": {"k": 1, "n": 4, "excluded": {"next_shot_unlabelled": 1}}} -->

Expected for side A: 5 drops (AN-09 5/5). AN-10: r1 success (bounce in the NVZ); r2 failed (lost on hit 5); r3 excluded `next_shot_unlabelled`; r4 failed (bounce outside the NVZ and hit 4 a drive, even though A later won the rally); r5 failed (drop into the net: lost on hit 3). Value 1/4, n_excluded 1.

## 4. AN-08 return depth (and serve depth)

| Field | Value |
|---|---|
| id / definition_version | AN-08 / 0.1 (FR-171.R7; QD AN-08 [SRC-0001]) |
| plain-language definition | "Of your side's returns that landed in, the share that landed deep: in the third of the court nearest the server's baseline." |
| numerator | rallies served by the other side whose hit 2 (by S) has its first following bounce in the server's half with d ≥ 4.47 m (two thirds of the 6.705 m half, §0.7) |
| denominator | rallies served by the other side whose hit 2 (by S) has a labelled bounce inside the server's half |
| exclusions | `no_return` (one hit only), `side_order_invalid`, `bounce_missing` (no bounce event between hit 2 and hit 3 or the rally end, or its `court_xy_m` is null), `not_in_play` (bounce outside the server's half: out, or on the returner's own side) |
| serve depth (no AN id yet, §10 Q2) | the same with hit 1 by S, the bounce before hit 2, the receiving half, and `not_in_play` also for a serve bounce inside the NVZ (d ≤ 2.13). Diagonal service court not checked in v0.1 |
| min_n | 20 returns in play with a bounce (A6) |
| interval_method | wilson |
| better_direction | `higher` (judgment: a deep return keeps the serving side back) |
| level bands | as AN-09 (§0.6) |
| data source | FT (bounce `court_xy_m`); unavailable `no_bounce_positions` when no bounce in the match has a position |
| rule dependence | court dimensions, line-in rule (§0.9) `@needs-verification` |
| open | QD AN-08 measures the deepest third **between the NVZ line and the baseline** (d ≥ 5.18 m), FR-171.R7 the deepest third **of the half** (d ≥ 4.47 m). v0.1 follows FR-171.R7, the newer binding rule; the coach prefers QD's deeper line (judgment) and asks the BA to decide before ST-171d starts (§10 Q2) |

Rule: AN-08.1 (FR-171.R7) Return depth = deep returns / returns in play with a labelled bounce
  Example: 12 returns with a labelled bounce, 5 deep → 5/12 (happy; BA example), Wilson 0.193-0.680, `low_sample` <!-- wilson: 5 12 0.193 0.680 -->
  Example: a return with no labelled bounce is excluded with reason `bounce_missing` (negative; BA example; rallies r3 and r5 below)
Rule: AN-08.2 A return that lands out is excluded with reason `not_in_play`, never counted as shallow or deep
  Example: 24 returns in play, 9 deep → 0.375, Wilson 0.212-0.573 (happy) <!-- wilson: 9 24 0.212 0.573 -->
  Example: rally r4 below lands behind the server's baseline (y = −0.5) → `not_in_play` (negative)

Worked label example W-08-a (side A serves; side B returns into side A's half, 0 ≤ y ≤ 6.705, deep when y ≤ 2.235).

<!-- example: W-08-a -->
```json
{"schema": "full-tag-labels/v1", "clip": "clips/w08a.mp4", "fps": 60, "frame_count": 1000,
 "players": ["A1", "A2", "B1", "B2"],
 "rallies": [
  {"id": "r1", "start_frame": 0, "end_frame": 150,
   "outcome": {"ending": "unforced_error", "winning_side": "A", "responsible_player": "B1"},
   "events": [{"type": "hit", "frame": 10, "hitter": "A1"},
              {"type": "bounce", "frame": 25, "visible": true, "court_xy_m": [1.5, 11.0]},
              {"type": "hit", "frame": 40, "hitter": "B1"},
              {"type": "bounce", "frame": 55, "visible": true, "court_xy_m": [2.0, 1.2]},
              {"type": "hit", "frame": 70, "hitter": "A2", "facets": {"trajectory": "drive"}}]},
  {"id": "r2", "start_frame": 200, "end_frame": 350, "outcome": {"ending": "winner", "winning_side": "A"},
   "events": [{"type": "hit", "frame": 210, "hitter": "A1"},
              {"type": "bounce", "frame": 225, "visible": true, "court_xy_m": [4.5, 12.0]},
              {"type": "hit", "frame": 240, "hitter": "B2"},
              {"type": "bounce", "frame": 255, "visible": true, "court_xy_m": [4.0, 4.0]},
              {"type": "hit", "frame": 270, "hitter": "A1"}]},
  {"id": "r3", "start_frame": 400, "end_frame": 550, "outcome": {"ending": "winner", "winning_side": "A"},
   "events": [{"type": "hit", "frame": 410, "hitter": "A1"}, {"type": "hit", "frame": 440, "hitter": "B1"},
              {"type": "bounce", "frame": 455, "visible": false, "court_xy_m": null},
              {"type": "hit", "frame": 470, "hitter": "A2"}]},
  {"id": "r4", "start_frame": 600, "end_frame": 700,
   "outcome": {"ending": "unforced_error", "winning_side": "A", "responsible_player": "B1"},
   "events": [{"type": "hit", "frame": 610, "hitter": "A1"}, {"type": "hit", "frame": 640, "hitter": "B1"},
              {"type": "bounce", "frame": 655, "visible": true, "court_xy_m": [3.0, -0.5]}]},
  {"id": "r5", "start_frame": 800, "end_frame": 950, "outcome": {"ending": "winner", "winning_side": "A"},
   "events": [{"type": "hit", "frame": 810, "hitter": "A1"}, {"type": "hit", "frame": 840, "hitter": "B2"},
              {"type": "hit", "frame": 870, "hitter": "A2"}]}
 ]}
```
<!-- expect: {"AN-08@B": {"k": 1, "n": 2, "excluded": {"bounce_missing": 2, "not_in_play": 1}}, "AN-08S@A": {"k": 1, "n": 2, "excluded": {"bounce_missing": 3}}} -->

Expected: side B return depth 1/2 (r1 deep at d = 5.505; r2 shallow at d = 2.705), excluded `bounce_missing` 2 (r3 null position, r5 no bounce), `not_in_play` 1 (r4). Side A serve depth 1/2 (r2 deep at d = 5.295; r1 in play at d = 4.295, not deep), excluded `bounce_missing` 3.

## 5. AN-13 dink tolerance

| Field | Value |
|---|---|
| id / definition_version | AN-13 / 0.1 (FR-171.R4; QD AN-13 "dink battle stats" [SRC-0001]) |
| plain-language definition | "When your side lost a dink exchange on its own dink, how many dinks your side had made in that exchange first (the middle value)." |
| terms | **dink exchange:** the last maximal run of consecutive rally shots (hit 3 and later) with `trajectory: dink`, with at least 2 hits (so both sides dinked). A rally with one is a **dink rally** |
| numerator (sample value) | for each dink rally that S lost on its own dink: the run's last hit is the rally's last hit, its hitter is on S, S lost, and the ending is `unforced_error`, `forced_error` or `fault` (metric dictionary rule 0.2 [SRC-0004]). Value x = S's dinks in the run minus the erring one (x ≥ 0) |
| statistic | median of x (for an even n the mean of the two middle values) |
| denominator (n) | S's error-ended dink rallies; reported with **n_censored** = S's dink rallies that ended any other way (S won, the other side erred, or the run was broken by a non-dink shot) |
| exclusions | `facet_missing` (any rally shot without `trajectory`: run boundaries unknown), `no_dink_exchange` (no run of ≥ 2 dinks); only rallies with ≥ 4 hits and not `replay` enter the universe |
| min_n | **10** error-ended dink rallies (≥ 6 required by FR-171.R4; at n = 6 the interval is the whole range [x(1), x(6)], too wide to rank, judgment) |
| interval_method | `order_statistic_median`: [x(l), x(n−l+1)], l the largest rank with P(Binomial(n, 0.5) ≤ l−1) ≤ 0.025; none below n = 6 [SRC-0007] |
| better_direction | `higher` |
| level bands | as AN-09 (§0.6) |
| data source | FT (`trajectory` on every rally shot) |
| rule dependence | NVZ volley rule (§0.9) `@needs-verification` |
| sense (judgment) | a dink is a soft shot from at or near the NVZ line that lands in the opponent's NVZ ([SRC-0010], unresolved) `@needs-verification` |

**Why the error-ended sample, and what it hides (PE-PLAN06-03).** A dink exchange S survives (S wins it, the other side errs, or someone speeds up) is right-censored: S's tolerance in it was at least its length. v0.1 keeps FR-171.R4's error-ended median and does not switch to a censored estimate, because:

1. It answers the coaching question the drill fixes (judgment): "when you do miss in a dink exchange, how early?" A low value with a reasonable n points straight at a dink-consistency drill.
2. It is computable and checkable by hand on GS-PAT-1 with a distribution-free interval that needs no model (COACH-6b, QA recount).
3. The reference value (COACH-6c) is defined on the same error-ended statistic, so player and reference are compared like for like.

What it hides: if a player wins many dink exchanges with a speed-up, the error-ended sample keeps only the short failures and understates tolerance. So **n_censored is always reported next to n**, and the Why and the weakness view show "and n_censored exchanges you did not lose on a dink" (PD-6). A censored (Kaplan-Meier) median is the v0.2 candidate if GS-PAT-1 or the demo data show a censored share above one half (judgment, §10 Q5).

Rule: AN-13.1 (FR-171.R4) Tolerance is the median of S's dinks before its own dink error, with an order-statistic interval
  Example: 10 error-ended dink rallies with runs 2, 3, 3, 4, 5, 5, 6, 7, 8, 10 → median 5, n = 10, l = 2, interval [3, 8], rankable (happy; BA example) <!-- median: [2, 3, 3, 4, 5, 5, 6, 7, 8, 10] 5 l=2:[3,8] -->
  Example: runs 3, 5, 8 → median 5, n = 3, interval unavailable, rankable false, never a Wilson interval (negative; BA example) <!-- median: [3, 5, 8] 5 none -->
  Example: runs 1, 2, 2, 3, 4, 6 → median 2.5, n = 6, l = 1, interval [1, 6], `low_sample` (n < 10), not rankable (negative) <!-- median: [1, 2, 2, 3, 4, 6] 2.5 l=1:[1,6] -->
Rule: AN-13.2 (FR-171.R4) A dink rally S did not lose on its own dink is counted in n_censored, never as a tolerance sample
  Example: rally r5 below (B errs) → a sample for B (x = 1), censored for A (happy)
  Example: a dink rally won by the side is counted in n_censored, never as a tolerance sample (negative; BA example; rally r1 below for B, r2 for both)
Rule: AN-13.3 A rally shot without a trajectory facet excludes the rally with reason `facet_missing`
  Example: rally r4 below (all rally shots labelled, all drives) → `no_dink_exchange`, decided (happy)
  Example: rally r3 below (hit 3 unlabelled) → `facet_missing` for both sides, never a dink rally (negative)

Worked label example W-13-a.

<!-- example: W-13-a -->
```json
{"schema": "full-tag-labels/v1", "clip": "clips/w13a.mp4", "fps": 60, "frame_count": 1400,
 "players": ["A1", "A2", "B1", "B2"],
 "rallies": [
  {"id": "r1", "start_frame": 0, "end_frame": 300,
   "outcome": {"ending": "unforced_error", "winning_side": "B", "responsible_player": "A2"},
   "events": [{"type": "hit", "frame": 10, "hitter": "A1"}, {"type": "hit", "frame": 40, "hitter": "B1"},
              {"type": "hit", "frame": 70, "hitter": "A2", "facets": {"trajectory": "drop"}},
              {"type": "hit", "frame": 100, "hitter": "B1", "facets": {"trajectory": "dink"}},
              {"type": "hit", "frame": 130, "hitter": "A2", "facets": {"trajectory": "dink"}},
              {"type": "hit", "frame": 160, "hitter": "B2", "facets": {"trajectory": "dink"}},
              {"type": "hit", "frame": 190, "hitter": "A1", "facets": {"trajectory": "dink"}},
              {"type": "hit", "frame": 220, "hitter": "B1", "facets": {"trajectory": "dink"}},
              {"type": "hit", "frame": 250, "hitter": "A2", "facets": {"trajectory": "dink"}}]},
  {"id": "r2", "start_frame": 400, "end_frame": 650,
   "outcome": {"ending": "forced_error", "winning_side": "A", "responsible_player": "B2"},
   "events": [{"type": "hit", "frame": 410, "hitter": "A1"}, {"type": "hit", "frame": 440, "hitter": "B1"},
              {"type": "hit", "frame": 470, "hitter": "A2", "facets": {"trajectory": "drop"}},
              {"type": "hit", "frame": 500, "hitter": "B1", "facets": {"trajectory": "dink"}},
              {"type": "hit", "frame": 530, "hitter": "A2", "facets": {"trajectory": "dink"}},
              {"type": "hit", "frame": 560, "hitter": "B2", "facets": {"trajectory": "dink"}},
              {"type": "hit", "frame": 590, "hitter": "A1", "facets": {"trajectory": "drive", "intent": "speed_up"}}]},
  {"id": "r3", "start_frame": 700, "end_frame": 850,
   "outcome": {"ending": "unforced_error", "winning_side": "B", "responsible_player": "A1"},
   "events": [{"type": "hit", "frame": 710, "hitter": "A1"}, {"type": "hit", "frame": 740, "hitter": "B1"},
              {"type": "hit", "frame": 770, "hitter": "A2"},
              {"type": "hit", "frame": 800, "hitter": "B2", "facets": {"trajectory": "dink"}},
              {"type": "hit", "frame": 830, "hitter": "A1", "facets": {"trajectory": "dink"}}]},
  {"id": "r4", "start_frame": 900, "end_frame": 1050, "outcome": {"ending": "winner", "winning_side": "A"},
   "events": [{"type": "hit", "frame": 910, "hitter": "A1"}, {"type": "hit", "frame": 940, "hitter": "B1"},
              {"type": "hit", "frame": 970, "hitter": "A2", "facets": {"trajectory": "drive"}},
              {"type": "hit", "frame": 1000, "hitter": "B1", "facets": {"trajectory": "drive"}},
              {"type": "hit", "frame": 1030, "hitter": "A2", "facets": {"trajectory": "drive"}}]},
  {"id": "r5", "start_frame": 1100, "end_frame": 1300,
   "outcome": {"ending": "unforced_error", "winning_side": "A", "responsible_player": "B1"},
   "events": [{"type": "hit", "frame": 1110, "hitter": "A1"}, {"type": "hit", "frame": 1140, "hitter": "B1"},
              {"type": "hit", "frame": 1170, "hitter": "A2", "facets": {"trajectory": "drop"}},
              {"type": "hit", "frame": 1200, "hitter": "B2", "facets": {"trajectory": "dink"}},
              {"type": "hit", "frame": 1230, "hitter": "A1", "facets": {"trajectory": "dink"}},
              {"type": "hit", "frame": 1260, "hitter": "B1", "facets": {"trajectory": "dink"}}]}
 ]}
```
<!-- expect: {"AN-13@A": {"runs": [2], "n": 1, "n_censored": 2, "excluded": {"facet_missing": 1, "no_dink_exchange": 1}}, "AN-13@B": {"runs": [1], "n": 1, "n_censored": 2}} -->

Expected: side A one sample x = 2 (r1: A dinked 3 times in the run, the third was the error), censored 2 (r2 broken by A's speed-up; r5 B erred). Side B one sample x = 1 (r5), censored 2 (r1 B won; r2). Both sides: `facet_missing` 1 (r3), `no_dink_exchange` 1 (r4).

## 6. AN-11 arrival at the NVZ (needs CV (7.1))

| Field | Value |
|---|---|
| id / definition_version | AN-11 / 0.1 (QD AN-11 [SRC-0001]) |
| plain-language definition | "Of your serving rallies that lasted to your side's third hit, the share where both of you were at the kitchen line by then." |
| numerator | rallies served by S that reach hit 5, where both S players' foot points are within 1.0 m behind their NVZ line (2.13 ≤ d ≤ 3.13) at the frame of hit 5 |
| denominator | rallies served by S that reach hit 5 |
| exclusions | `position_missing` (a player's foot point not placed at that frame), `side_order_invalid`; singles: one player |
| min_n | 20 (A6) |
| interval_method | wilson |
| better_direction | `higher` |
| level bands | as AN-09 (§0.6) |
| data source | **CV**: player foot points on the court plane (tracking + homography [SRC-0013]); FT gives hit 5's frame. **needs CV (7.1)**: not Ready until the tracking and calibration gates are measured on footage (P11; ST-176b spike plan). Pose is not needed (feet only), but player tracks are personal data: tier 2 with the security-privacy-engineer |
| rule dependence | NVZ depth (§0.9) `@needs-verification` |

Rule: AN-11.1 Both serving players within 1.0 m of their NVZ line at hit 5 count as an arrival
  Example: 30 serving rallies reach hit 5, 12 arrivals → 0.40, Wilson 0.246-0.577 (happy) <!-- wilson: 12 30 0.246 0.577 -->
  Example: a rally where one player's feet are not placed at hit 5 → `position_missing`, never "not arrived" (negative)

## 7. AN-12 lost in transition (needs CV (7.1))

| Field | Value |
|---|---|
| id / definition_version | AN-12 / 0.1 (QD AN-12 [SRC-0001]) |
| plain-language definition | "Of the rallies your side lost, the share where your side's last shot was hit from no-man's land between the baseline and the kitchen." |
| numerator | rallies lost by S whose last hit by S was hit with the hitter's foot point in the **transition zone**: 3.13 < d < 5.205 (more than 1.0 m behind the NVZ line and more than 1.5 m inside the baseline; judgment) |
| denominator | rallies lost by S in which S hit at least once after the serve and return (hit 3 or later) |
| exclusions | `position_missing`, `replay`; rallies S lost before hitting a rally shot are outside the universe (serve and return errors are AN-05 / AN-07) |
| min_n | 20 (A6) |
| interval_method | wilson |
| better_direction | `lower` |
| level bands | as AN-09 (§0.6) |
| data source | **CV** (hitter foot point at the hit frame). **needs CV (7.1)**; personal data, tier 2 as AN-11 |
| rule dependence | court dimensions (§0.9); "transition zone" bounds are judgment ([SRC-0010], unresolved) `@needs-verification` |

Rule: AN-12.1 A lost rally whose last S shot came from the transition zone counts as lost in transition
  Example: 26 lost rallies, 11 from the transition zone → 0.423, Wilson 0.255-0.611 (happy) <!-- wilson: 11 26 0.255 0.611 -->
  Example: a rally lost on a return error (S never hit a rally shot) → outside the universe, never in the denominator (negative)

## 8. STACK: stacking (no AN id yet; needs CV (7.1))

| Field | Value |
|---|---|
| id / definition_version | none yet (the BA assigns one; FR-107 lists AN-08..AN-14) / 0.1 |
| plain-language definition | "How often your pair kept the same left/right sides after the serve or return instead of the sides the score would put you on." |
| numerator | service turns (serving or receiving) of S where, after S's first rally shot, each S player stands in the half (left or right of the centre line) opposite to the one the score-parity serving or receiving position put them in |
| denominator | service turns of S with both players' foot points placed after S's first rally shot |
| exclusions | `position_missing`; singles (not defined) |
| min_n | 20 service turns (A6) |
| interval_method | wilson |
| better_direction | none: descriptive, **never rankable** (a tactic, not a skill gap; judgment) |
| level bands | none (descriptive); shown beside AN-11 for context only |
| data source | **CV** (foot points, centre line). **needs CV (7.1)**; personal data, tier 2 |
| rule dependence | serving position follows the score (§0.9, row 6) `@needs-verification` |

Rule: STACK.1 Stacking is described, never ranked
  Example: 28 measured turns, 18 stacked → 0.643, Wilson 0.458-0.793, shown as "you stacked in 18 of 28 turns" (happy) <!-- wilson: 18 28 0.458 0.793 -->
  Example: stacking shown as a weakness or given a target band → the reference lint refuses the entry (no `better_direction`) (negative)

## 9. SPACING: partner spacing (AN-16 middle left open; needs CV (7.1))

| Field | Value |
|---|---|
| id / definition_version | AN-16 / 0.1 (QD AN-16 [SRC-0001]) |
| plain-language definition | "The share of rally time when the gap between you and your partner was more than half the court's width, leaving the middle open." |
| numerator | rally frames (from hit 3 to the rally end) where the lateral distance between the two S players' foot points is > 3.05 m (half of 6.10 m) |
| denominator | rally frames with both S foot points placed; rallies are the counting unit for min_n |
| exclusions | `position_missing` frames (reported as a share); singles (not defined) |
| min_n | 20 rallies (A6; QD's 10 is replaced by the A6 default) |
| interval_method | wilson, over rallies (a rally counts as "open" when its open-frame share is > 0.25, judgment), because frames within a rally are not independent |
| better_direction | `lower` |
| level bands | as AN-09 (§0.6), doubles only |
| data source | **CV** (tracks + homography). **needs CV (7.1)**; personal data, tier 2 |
| rule dependence | court width (§0.9) `@needs-verification` |

Rule: SPACING.1 A rally counts as "middle open" when more than a quarter of its measured frames have a partner gap above half the court width
  Example: 40 rallies, 13 open → 0.325, Wilson 0.201-0.480 (happy) <!-- wilson: 13 40 0.201 0.480 -->
  Example: an interval computed over frames instead of rallies → refused in review: frames are not independent trials (negative)

## 10. Open questions

| # | Question | To | Default until answered |
|---|---|---|---|
| Q1 | Labels v1 `court_xy_m` axes and origin (§0.7) and which end side A starts at after an end switch | senior-ml-cv-engineer (ML-6, ST-171d) | the §0.7 convention; ST-171d does not start without the answer |
| Q2 | AN-08 deep line: FR-171.R7 (d ≥ 4.47 m) or QD (d ≥ 5.18 m); and an AN id for serve depth | business-analyst | FR-171.R7; serve depth defined, not built |
| Q3 | Add a rules-queue row 11 "court dimensions, NVZ depth, line-in" to `docs/domain/rules-verified.md` §5 | pickleball-domain-coach (next coach ticket), P7 | patterns carry `@needs-verification` |
| Q4 | Add a `hybrid` third-shot trajectory value ([SRC-0011], unresolved; QD-TX-01) | coach, senior-ml-cv-engineer | not added; AN-09 counts hybrids as the labeller's nearest value |
| Q5 | AN-13 censored estimate (Kaplan-Meier) in v0.2 if the censored share is above one half on GS-PAT-1 or the demo data. COACH-6b: the share is about one half by construction (each error-ended rally censors the other side, §11); state the trigger on the rallies the side ended itself (its own dink errors plus its own winning speed-ups)? | coach, senior-ml-cv-engineer | error-ended median with n_censored shown |

## 11. Gold fixture GS-PAT-1 (COACH-6b)

GS-PAT-1 v1 is `docs/domain/hand-counts/GS-PAT-1-v1.json`: two team-made Full Tag label documents (no video, no real people; clip names are placeholders), a plain-language rally sheet per match, and the coach's hand count of AN-09, AN-13 and AN-08 per side with the rally ids of every bucket. `gp1-doubles` (48 rallies) reaches min_n for some measures; `gp2-singles` (12 rallies) holds every exclusion reason in a few rallies and is the match QA recounts by hand. Both documents pass `validate_labels` (labels v1).

The rows below are printed by `python3 docs/domain/tools/pattern_example.py`; `--check` fails unless (1) every worked example of §2-§5 gives its `expect` fields, (2) every stated Wilson and median figure is exact, (3) the replay of §0-§5 equals the hand count in the fixture bucket by bucket, and (4) every table below is exactly these rows. The tool imports neither the product nor `scripts/measure/` (ADR 0044). These are fixture values, never reference values: they do not feed a band (§0.6; COACH-6c). Statuses stay `draft` until the product equals this hand count (ADR 0044).

AN-09 third-shot drop share (§2; side = server; min_n 20):

<!-- table: GS-PAT-1 AN-09 -->
| Match | Side | Drops k | Third shots n | Share | Wilson 95 % | State | Excluded | Mix (companions) |
|---|---|---|---|---|---|---|---|---|
| gp1-doubles | A | 16 | 20 | 0.800 | 0.584-0.919 | rankable | facet_missing 1, no_third_shot 2, side_order_invalid 1 | drive 3, drop 16, lob 1 |
| gp1-doubles | B | 6 | 18 | 0.333 | 0.163-0.563 | low_sample | facet_missing 1, no_third_shot 3 | drive 11, drop 6, lob 1 |
| gp2-singles | A | 3 | 5 | 0.600 | 0.231-0.882 | low_sample | none | drive 1, drop 3, lob 1 |
| gp2-singles | B | 2 | 3 | 0.667 | 0.208-0.939 | low_sample | facet_missing 1, no_third_shot 1, side_order_invalid 1 | drive 1, drop 2 |

AN-13 dink tolerance (§5; min_n 10; interval `order_statistic_median`, none below n = 6):

<!-- table: GS-PAT-1 AN-13 -->
| Match | Side | Samples x (sorted) | n | Median | Interval | State | n_censored | Excluded |
|---|---|---|---|---|---|---|---|---|
| gp1-doubles | A | 0, 1, 1, 1, 2, 2, 2, 2, 2, 3, 3, 4 | 12 | 2 | [1, 3] (l = 3) | rankable | 13 | facet_missing 2, no_dink_exchange 10 |
| gp1-doubles | B | 0, 1, 1, 1, 2, 2, 2, 3, 3, 4 | 10 | 2 | [1, 3] (l = 2) | rankable | 15 | facet_missing 2, no_dink_exchange 10 |
| gp2-singles | A | 1, 1 | 2 | 1 | none | low_sample | 3 | facet_missing 1, no_dink_exchange 2 |
| gp2-singles | B | 0, 2 | 2 | 1 | none | low_sample | 3 | facet_missing 1, no_dink_exchange 2 |

AN-08 return depth (§4; side = returner; deep when d ≥ 4.47 m; min_n 20). Serve depth is not tabled (§10 Q2):

<!-- table: GS-PAT-1 AN-08 -->
| Match | Side (returner) | Deep k | Returns in play n | Share | Wilson 95 % | State | Excluded |
|---|---|---|---|---|---|---|---|
| gp1-doubles | A | 13 | 19 | 0.684 | 0.460-0.846 | low_sample | bounce_missing 1, no_return 1, not_in_play 1 |
| gp1-doubles | B | 13 | 20 | 0.650 | 0.433-0.819 | rankable | bounce_missing 2, no_return 1, side_order_invalid 1 |
| gp2-singles | A | 2 | 3 | 0.667 | 0.208-0.939 | low_sample | bounce_missing 1, not_in_play 1, side_order_invalid 1 |
| gp2-singles | B | 3 | 5 | 0.600 | 0.231-0.882 | low_sample | none |

Match-level rallies of neither side (§0.2):

<!-- table: GS-PAT-1 unassigned -->
| Match | Format | Rallies | Unassigned (match level) |
|---|---|---|---|
| gp1-doubles | doubles | 48 | no_serve_hit 1, replay 1 |
| gp2-singles | singles | 12 | replay 1 |

Conservation (FR-171.R3), `gp1-doubles`: AN-09 A 20 + 4 = 24 served, B 18 + 4 = 22 served, unassigned 2 → 48 rallies; AN-13 universe 37 rallies (≥ 4 hits, not a replay) = A 12 + 13 + 12 = B 10 + 15 + 12; AN-08 B 20 + 4 = 24 returns faced, A 19 + 3 = 22. `gp2-singles`: AN-09 5 + 0 and 3 + 3 → 11 + 1 unassigned = 12; AN-13 universe 8 = 2 + 3 + 3 per side; AN-08 B 5 + 0, A 3 + 3.

Censored share (§5, §10 Q5): on `gp1-doubles` 13 of A's 25 dink rallies and 15 of B's are censored, above one half. This is by construction, not a finding about play: every error-ended dink rally is a sample for the side that erred and censored for the other. Q5's trigger is reworded as a question in §10 (COACH-6b).

## Changelog

| Date | Who | Change |
|---|---|---|
| 2026-11-13 | pickleball-domain-coach | v0.1 written with COACH-6a: rules §0, AN-09, AN-10, AN-08, AN-13 (FT), AN-11, AN-12, STACK, SPACING (CV, needs 7.1); worked label examples W-09-a, W-10-a, W-08-a, W-13-a |
| 2026-11-13 | pickleball-domain-coach | §11 gold fixture GS-PAT-1 v1 tables and `pattern_example.py --check` (COACH-6b); Q5 note; no definition changed, statuses stay `draft` |
| 2026-11-13 | pickleball-domain-coach | §1 wave A rows AN-05, AN-07 (unforced-error share) and AN-04 (context only) for the reference set v1 (COACH-6c); no definition changed |
