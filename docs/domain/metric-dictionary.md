# Metric dictionary: R1 starter metrics AN-01..AN-07

- **Owner:** pickleball-domain-coach (QD-AN-01)
- **Status of every entry:** `coach-reviewed` (2026-10-07, COACH-1; ADR 0044). Created `draft` 2026-10-03. Moved after the QD-AN-03 hand count on GS-AN-1 v1 (§2b, §3). The next step is `verified` (ADR 0044 rule 3: second recompute, κ check for AN-04/AN-07, verified rules).
  - The coach hand-computes each metric on 3 golden matches (QD-GD-03), and the system must match exactly.
  - A second coach or a 4.0+ player recomputes 1 match (OQ-20). Per ADR 0044 this gates `verified`, not `coach-reviewed`.
  - Users see only `coach-reviewed` or `verified` entries (FR-102).
- **Requirements:** FR-100 (starter stats), FR-101 (sample size and uncertainty), FR-102 (versioned dictionary), FR-103 ("Show me" evidence); NFR-004 (exact on gold tags); NFR-038; ADR 0005 (Wilson interval and minimum n).
- **Sources:** formulas start from QD §3.2. **Every definition is (judgment) by the coach. No coaching source is verified** [DOM G2]. Definitions that depend on a scoring rule inherit that rule's **UNVERIFIED** status (`docs/domain/rules-verified.md` §5).
- **Data level:** all seven are `QT` and use only Quick Tag fields (FR-050):
  - `winning_side`;
  - `ending` ∈ {`winner`, `unforced_error`, `forced_error`, `fault`, `replay`};
  - an optional `fault_subtype` ∈ {`serve`, `nvz`, `two_bounce`, `foot`, `other`};
  - an optional `responsible_player`;
  - plus the engine's per-rally `serving_side`, `server_number` and score.

## 0. Rules that apply to every entry

1. **Excluded rallies:** `replay` and `gap` rallies are excluded from every numerator and denominator. They do not change the score (P8, SOD-16).
2. **Who made the ending (attribution):** derived, never guessed.
   - `winner` → the winning side hit it.
   - `unforced_error`, `forced_error` and `fault` → the **losing** side committed it.
   - The player is known only when `responsible_player` is tagged (QD X10). Otherwise the UI shows "player not tagged in x rallies".
3. **Uncertainty** (FR-101; ADR 0005):
   - every metric shows n;
   - proportions show a 95% Wilson interval, flagged "low sample" when n < `min_sample` or the interval is wider than 30 percentage points;
   - count-per-game metrics are flagged when fewer than 2 games are in scope;
   - flagged metrics are de-emphasised and never hidden.

   All thresholds are config.
4. **Scope:** per side (A, B) per match by default; per player where noted. The "me" side and player come from setup (FR-005).
5. **Rules dependence:** a metric whose meaning depends on a scoring rule is computed under the match's `rules_version`. While that is `PROVISIONAL-UNVERIFIED`, the stats page carries the same "unofficial scoring (rules not yet verified)" notice as the score sheet (FR-055), once, before the first card (flows-sprint-03 §0; DR-03 R3-3, coach accept 2026-10-07).
6. **Versioning:** a definition change bumps `version`. Old snapshots keep their version (ENG §3.2 `metric_def_version`).

## 1. Entries

### AN-01 Serve rally win %

| Field | Value |
|---|---|
| id / version | AN-01 / 0.1 |
| name (UI) | Rallies won on serve |
| plain-language definition (the "How is this measured?" text) | "Of the rallies your side served, the share your side won." |
| formula | rallies where `winning_side = S` and `serving_side = S` / rallies where `serving_side = S` |
| unit | % (proportion), Wilson 95% interval |
| data_level | QT |
| min_sample | n ≥ 20 rallies served (ADR 0005) |
| scope | per side; per player only as "rallies served by this player" (server identity needs the engine's server number plus the setup slot, judgment) |
| rules dependence | Under side-out scoring, winning a rally on serve is the same as scoring a point (DOM G1 R2, **UNVERIFIED**). The *formula* is rule-independent, because it counts rallies, not points |
| status / source | `coach-reviewed` 2026-10-07 (QD-AN-03, GS-AN-1 v1, §2b; ADR 0044) / (judgment), QD §3.2 |
| open issues | none |

### AN-02 Side-out % (receiving rally win %)

| Field | Value |
|---|---|
| id / version | AN-02 / 0.1 |
| name (UI) | Rallies won when receiving (D-1 decided, option a, 2026-10-07, ADR 0044 rule 5). FR-100 and FR-101 still say "side-out %"; their wording is the business-analyst's to change |
| plain-language definition | "Of the rallies the other side served, the share your side won." |
| formula | rallies where `winning_side = S` and `serving_side ≠ S` / rallies where `serving_side ≠ S` |
| unit | %, Wilson 95% interval |
| data_level | QT |
| min_sample | n ≥ 20 rallies received |
| rules dependence | none for the formula |
| status / source | `coach-reviewed` 2026-10-07 (QD-AN-03, GS-AN-1 v1, §2b; ADR 0044) / (judgment), QD §3.2 |
| **D-1 (terminology), decided 2026-10-07: option (a)** | Under side-out doubles scoring (provisional), winning a receiving rally against server 1 passes the serve to server 2. It is **not** a side-out (SOD-03). Calling this metric "side-out %" therefore misnames it for doubles players. **Options:** (a) rename the UI label to "Rallies won when receiving" and keep the formula; (b) keep "side-out %" but define it as *service turns ended / opponent service turns*, which is a different metric. **Recommendation:** (a). Changing the FR-100/FR-101 label is a requirement change: it goes to the BA and PM, and FR-101's Gherkin label would change with QA approval. Logged in the Sprint 0 decision log; not changed unilaterally |

### AN-03 Points per service turn

| Field | Value |
|---|---|
| id / version | AN-03 / 0.1 |
| name (UI) | Points per service turn |
| plain-language definition | "On average, how many points your side scored each time it got the serve." |
| formula | points scored by S while serving / service turns of S. A **service turn** begins when S gains the serve (or at the game start) and ends at the side-out or the game end. In doubles it covers server 1 and server 2, and the first turn of a game may have only one server (provisional first-service exception) |
| unit | points per turn (mean, 1 decimal). No Wilson interval, because it is not a proportion |
| data_level | QT (turns come from the engine's server-number sequence) |
| min_sample | ≥ 10 service turns (QD §3.2). Flagged below that |
| rules dependence | **Depends on unverified rules:** side-out scoring, the doubles server rotation and the first-service exception (rules-verified §5, priorities 1 and 3). Under rally scoring the metric is **undefined** and is not shown ("Not used with rally scoring") |
| edge cases | The turn in progress at game end counts as a turn (judgment). A mid-game start (FR-046, Sprint 2) counts the first partial turn |
| status / source | `coach-reviewed` 2026-10-07 (QD-AN-03, GS-AN-1 v1, §2b; ADR 0044) / (judgment), QD §3.2 |

### AN-04 Unforced errors per game

| Field | Value |
|---|---|
| id / version | AN-04 / 0.1 |
| name (UI) | Unforced errors per game |
| plain-language definition | "How many rallies per game ended with a mistake by your side that the other side did not force." |
| formula | rallies with `ending = unforced_error` attributed to S (rule 0.2) / games in scope (completed games, plus the current game if the match is unfinished, judgment). Per player: the same, with `responsible_player = P`; untagged rallies are listed as "player not tagged in x rallies", never spread across players |
| unit | count per game (1 decimal) |
| data_level | QT |
| min_sample | ≥ 2 games (count metric; FR-101) |
| rules dependence | none |
| **D-2 (label reliability), decided 2026-10-07: keep both** | "Unforced" vs "forced" is a subjective coaching call (QD X3). **Working definition (judgment, UNVERIFIED):** "an error on a ball the player had time and position to play safely; if the opponent's shot made the ball hard to play, it is forced". Kept only if two labellers reach Cohen's κ ≥ 0.6 on 200 rallies (QD X3). Otherwise v1 merges both into "errors" and AN-04 becomes "errors per game" with a version bump. **Decided 2026-10-07 (ADR 0044 rule 4):** kept separate in v0.1, in the Quick Tag buttons and in AN-07; the κ check gates `verified`, not `coach-reviewed`. A later merge loses nothing because both labels are captured |
| status / source | `coach-reviewed` 2026-10-07 (QD-AN-03, GS-AN-1 v1, §2b; ADR 0044) / (judgment), QD §3.2, X3, X10 |

### AN-05 Serve fault %

| Field | Value |
|---|---|
| id / version | AN-05 / 0.1 |
| name (UI) | Serve faults |
| plain-language definition | "Of your side's serves, the share that were faults." |
| formula | rallies with `ending = fault` and `fault_subtype = serve` attributed to S while `serving_side = S` / rallies where `serving_side = S` |
| unit | %, Wilson 95% interval |
| data_level | QT; needs the optional `fault_subtype` |
| min_sample | n ≥ 20 serves |
| rules dependence | What counts as a serve fault is a rule (DOM G1, **UNVERIFIED**). The metric counts what the user tagged, so the definition is "tagged serve faults" |
| edge cases | Serving-side faults with no subtype make the value a **lower bound**. The card says "fault type not tagged in x rallies" and is flagged when x > 0 (judgment). One serve per rally is assumed; lets and replays are excluded by rule 0.1 |
| status / source | `coach-reviewed` 2026-10-07 (QD-AN-03, GS-AN-1 v1, §2b; ADR 0044) / (judgment), QD §3.2 |

### AN-06 Longest run and run histogram

| Field | Value |
|---|---|
| id / version | AN-06 / 0.1 |
| name (UI) | Longest scoring run |
| plain-language definition | "The most points your side scored in a row before the other side scored." |
| formula | A **run** is a maximal sequence of points scored by S with no point scored by the other side in between. Rallies that change only the serve, with no point, do not break a run. Runs reset at game end. Output: the longest run per side per game, and a histogram of run lengths (1, 2, 3, 4, 5+) per side per match |
| unit | points (integer); histogram counts |
| data_level | QT |
| min_sample | none: descriptive (QD §3.2). It shows "n = x points" and is never flagged |
| rules dependence | "Point" depends on the scoring system. Under side-out scoring (provisional) only the server scores. The formula reads points from the engine's score sequence, so it holds under any configured system |
| status / source | `coach-reviewed` 2026-10-07 (QD-AN-03, GS-AN-1 v1, §2b; ADR 0044) / (judgment), QD §3.2 |

### AN-07 Rally-ending mix

| Field | Value |
|---|---|
| id / version | AN-07 / 0.1 |
| name (UI) | How rallies ended |
| plain-language definition | "Of the rallies your side ended, how many were winners you hit, unforced errors, forced errors or faults." |
| formula | For S, among rallies whose ending is attributed to S (rule 0.2), the share of each of `winner`, `unforced_error`, `forced_error` and `fault`. n = the number of such rallies. The four shares sum to 100% |
| unit | % per category, each with a Wilson 95% interval |
| data_level | QT |
| min_sample | n ≥ 20 rallies ended by S. Rule 0.3 applies to each of the four shares: the side's AN-07 is flagged when n < 20 or any share's 95% interval is wider than 30 points (a restatement of rule 0.3, not a change; PE-R1S3-05, confirmed by the coach 2026-10-07) |
| rules dependence | Fault categories depend on fault rules (**UNVERIFIED**); counted as tagged |
| display | A stacked bar needs a non-colour encoding: printed values per segment (NFR-034; DES FR-UX-72) |
| open issue | If the κ check of D-2 fails (ADR 0044 rule 3b), this becomes 3 categories with a version bump |
| status / source | `coach-reviewed` 2026-10-07 (QD-AN-03, GS-AN-1 v1, §2b; ADR 0044) / (judgment), QD §3.2 |

## 2. Worked example (hand count, for QD-AN-02 unit tests)

**This is an example under the `PROVISIONAL-UNVERIFIED` side-out doubles preset.** The game starts at "0-0-2" with side A serving. Calls are given as serving score - receiving score - server number. The sequence is invented test data, not a real match.

The figures were computed with `python3 docs/domain/tools/metric_example.py` (run 2026-10-03; it printed the states and counts below) and checked by hand.

| # | Before | Winner | Ending (subtype, player) | After |
|---|---|---|---|---|
| 1 | 0-0-2 A | A | winner (A1) | 1-0-2 A |
| 2 | 1-0-2 A | B | fault (serve, A2) | 0-1-1 B |
| 3 | 0-1-1 B | B | winner | 1-1-1 B |
| 4 | 1-1-1 B | B | unforced error (A1) | 2-1-1 B |
| 5 | 2-1-1 B | A | forced error (B2) | 2-1-2 B |
| 6 | 2-1-2 B | A | fault (nvz, B1) | 1-2-1 A |
| 7 | 1-2-1 A | A | winner (A2) | 2-2-1 A |
| 8 | 2-2-1 A | — | replay | excluded |
| 9 | 2-2-1 A | A | unforced error (player untagged) | 3-2-1 A |
| 10 | 3-2-1 A | B | unforced error (A2) | 3-2-2 A |
| 11 | 3-2-2 A | A | fault (no subtype) | 4-2-2 A |
| 12 | 4-2-2 A | B | fault (serve, A1) | 2-4-1 B |
| 13 | 2-4-1 B | B | winner (B1) | 3-4-1 B |
| 14 | 3-4-1 B | B | winner (B2) | 4-4-1 B |

13 rallies are counted, and the replay is excluded. A served 7 and B served 6.

| Metric | Side A | Side B | Low-sample flag |
|---|---|---|---|
| AN-01 rallies won on serve | 4 / 7 = 57% | 4 / 6 = 67% | yes (n < 20) |
| AN-02 rallies won when receiving | 2 / 6 = 33% | 3 / 7 = 43% | yes |
| AN-03 points per service turn | 4 points / 2 turns = 2.0 | 4 / 2 = 2.0 (2nd turn open at end) | yes (< 10 turns) |
| AN-04 unforced errors per game | 2 (A1: 1, A2: 1) | 1 ("player not tagged in 1 rally") | yes (< 2 games) |
| AN-05 serve faults | 2 / 7 = 29% | 0 / 6 = 0% | yes |
| AN-06 longest run | 3 (rallies 7, 9, 11; the serve loss in rally 10 does not break it) | 2 (rallies 3-4 and 13-14) | never flagged |
| AN-07 how rallies ended (n) | n = 6: winner 2 (33%), UE 2 (33%), FE 0 (0%), fault 2 (33%) | n = 7: winner 3 (43%), UE 1 (14%), FE 1 (14%), fault 2 (29%) | yes |

Final score: 4-4, B serving at server 1. The provisional preset target is not reached, so the game is not over.

## 2b. QD-AN-03 hand count on the golden matches GS-AN-1 v1 (COACH-1, 2026-10-07)

The coach counted the three ST-049 tag scripts (`backend/tests/regression/golden_matches/*.script.json`; synthetic, PROVISIONAL-UNVERIFIED preset) from this dictionary's text, rally by rally. The trace is printed by `python3 docs/domain/tools/hand_count_gs_an1.py`, which imports neither the product nor `scripts/measure/statslib.py`. The full record, in the shape `test_golden_an.py` reads, is `docs/domain/hand-counts/GS-AN-1-v1.json` (`--write`).

**Results (2026-10-07):**

- **Product vs hand count:** 0 differences on every compared field of AN-01..AN-07, both sides, all 3 matches, including the evidence rallies and AN-06 per-game longest runs (product path of `test_golden_an.py`, `product_stats`).
- **Frozen GS-AN-1 v1 (the QA reference's values) vs hand count:** 2 differences, both AN-07 side A `low_sample` (gm1, gm2): hand count `true`, frozen `false`. The hand count applies rule 0.3 to each AN-07 share (gm1 A: n = 21, unforced-error share 5/21 has a 34.5-point interval). This is the reference defect PE-R1S3-05; the fix is QA's TCR row, not a change here (ADR 0044 rule 2).
- `cd backend && env -u APP_ENV uv run pytest -q tests/regression/test_golden_an.py` → `4 failed, 27 passed`; the four failures are those two cells, seen once against the product and once against the hand count. The hand-count case for gm3 passes.

**gm1-two-games**

| Metric | Side A | Side B |
|---|---|---|
| AN-01 | 18/32 = 56.2% [39.3%, 71.8%]; low sample | 13/26 = 50.0% [32.1%, 67.9%]; low sample |
| AN-02 | 13/26 = 50.0% [32.1%, 67.9%]; low sample | 14/32 = 43.8% [28.2%, 60.7%]; low sample |
| AN-03 | 18 points / 8 turns = 2.2; low sample | 13 points / 8 turns = 1.6; low sample |
| AN-04 | 5 in 2 games = 2.5; A2: 2; not tagged 3; not flagged | 11 in 2 games = 5.5; B1: 4, B2: 5; not tagged 2; not flagged |
| AN-05 | 1/32 = 3.1% [0.5%, 15.7%]; type not tagged 1; low sample | 1/26 = 3.9% [0.7%, 18.9%]; type not tagged 0; not flagged |
| AN-06 | longest 6 (per game 5, 6); runs 1/2/3/4/5+ = 2/0/0/0/3; n = 18; not flagged | longest 5 (per game 1, 5); runs 1/2/3/4/5+ = 2/1/0/1/1; n = 13; not flagged |
| AN-07 | n = 21: winner 6, UE 5, FE 6, fault 4; low sample | n = 37: winner 12, UE 11, FE 9, fault 5; not flagged |

**gm2-three-games**

| Metric | Side A | Side B |
|---|---|---|
| AN-01 | 24/35 = 68.6% [52.0%, 81.5%]; not flagged | 11/22 = 50.0% [30.7%, 69.3%]; low sample |
| AN-02 | 11/22 = 50.0% [30.7%, 69.3%]; low sample | 11/35 = 31.4% [18.6%, 48.0%]; not flagged |
| AN-03 | 24 points / 8 turns = 3.0; low sample | 11 points / 7 turns = 1.6; low sample |
| AN-04 | 9 in 3 games = 3.0; A1: 2, A2: 4; not tagged 3; not flagged | 6 in 3 games = 2.0; B1: 3, B2: 2; not tagged 1; not flagged |
| AN-05 | 0/35 = 0.0% [0.0%, 9.9%]; type not tagged 0; not flagged | 0/22 = 0.0% [0.0%, 14.9%]; type not tagged 0; not flagged |
| AN-06 | longest 11 (per game 11, 1, 11); runs 1/2/3/4/5+ = 2/0/0/0/2; n = 24; not flagged | longest 8 (per game 0, 8, 0); runs 1/2/3/4/5+ = 1/1/0/0/1; n = 11; not flagged |
| AN-07 | n = 38: winner 21, UE 9, FE 2, fault 6; low sample | n = 19: winner 5, UE 6, FE 3, fault 5; low sample |

**gm3-corrections-needs-decision**

| Metric | Side A | Side B |
|---|---|---|
| AN-01 | 11/13 = 84.6% [57.8%, 95.7%]; low sample | 4/6 = 66.7% [30.0%, 90.3%]; low sample |
| AN-02 | 2/6 = 33.3% [9.7%, 70.0%]; low sample | 2/13 = 15.4% [4.3%, 42.2%]; low sample |
| AN-03 | 11 points / 2 turns = 5.5; low sample | 4 points / 1 turns = 4.0; low sample |
| AN-04 | 1 in 1 games = 1.0; A1: 1; not tagged 0; low sample | 1 in 1 games = 1.0; no player tagged; not tagged 1; low sample |
| AN-05 | 0/13 = 0.0% [0.0%, 22.8%]; type not tagged 0; low sample | 0/6 = 0.0% [0.0%, 39.0%]; type not tagged 0; low sample |
| AN-06 | longest 11 (per game 11); runs 1/2/3/4/5+ = 0/0/0/0/1; n = 11; not flagged | longest 4 (per game 4); runs 1/2/3/4/5+ = 0/0/0/1/0; n = 4; not flagged |
| AN-07 | n = 12: winner 9, UE 1, FE 1, fault 1; low sample | n = 7: winner 3, UE 1, FE 1, fault 2; low sample |

## 3. Review record

| Date | Who | Entries | Status change | Evidence |
|---|---|---|---|---|
| 2026-10-03 | pickleball-domain-coach | AN-01..AN-07 | created as `draft` | this file; `python3 docs/domain/tools/metric_example.py` |
| 2026-10-07 | pickleball-domain-coach | AN-01 Rallies won on serve | `draft` → `coach-reviewed` | QD-AN-03 hand count on GS-AN-1 v1 (3 matches × 2 sides), §2b and `docs/domain/hand-counts/GS-AN-1-v1.json`; product equals the hand count on every compared field (0 differences); second recompute (OQ-20) gates `verified` (ADR 0044). |
| 2026-10-07 | pickleball-domain-coach | AN-02 Rallies won when receiving | `draft` → `coach-reviewed` | QD-AN-03 hand count on GS-AN-1 v1 (3 matches × 2 sides), §2b and `docs/domain/hand-counts/GS-AN-1-v1.json`; product equals the hand count on every compared field (0 differences); second recompute (OQ-20) gates `verified` (ADR 0044). D-1 decided: UI name "Rallies won when receiving". |
| 2026-10-07 | pickleball-domain-coach | AN-03 Points per service turn | `draft` → `coach-reviewed` | QD-AN-03 hand count on GS-AN-1 v1 (3 matches × 2 sides), §2b and `docs/domain/hand-counts/GS-AN-1-v1.json`; product equals the hand count on every compared field (0 differences); second recompute (OQ-20) gates `verified` (ADR 0044). |
| 2026-10-07 | pickleball-domain-coach | AN-04 Unforced errors per game | `draft` → `coach-reviewed` | QD-AN-03 hand count on GS-AN-1 v1 (3 matches × 2 sides), §2b and `docs/domain/hand-counts/GS-AN-1-v1.json`; product equals the hand count on every compared field (0 differences); second recompute (OQ-20) gates `verified` (ADR 0044). D-2 decided: forced and unforced kept separate (ADR 0044 rule 4). |
| 2026-10-07 | pickleball-domain-coach | AN-05 Serve faults | `draft` → `coach-reviewed` | QD-AN-03 hand count on GS-AN-1 v1 (3 matches × 2 sides), §2b and `docs/domain/hand-counts/GS-AN-1-v1.json`; product equals the hand count on every compared field (0 differences); second recompute (OQ-20) gates `verified` (ADR 0044). |
| 2026-10-07 | pickleball-domain-coach | AN-06 Longest scoring run | `draft` → `coach-reviewed` | QD-AN-03 hand count on GS-AN-1 v1 (3 matches × 2 sides), §2b and `docs/domain/hand-counts/GS-AN-1-v1.json`; product equals the hand count on every compared field (0 differences); second recompute (OQ-20) gates `verified` (ADR 0044). |
| 2026-10-07 | pickleball-domain-coach | AN-07 How rallies ended | `draft` → `coach-reviewed` | QD-AN-03 hand count on GS-AN-1 v1 (3 matches × 2 sides), §2b and `docs/domain/hand-counts/GS-AN-1-v1.json`; product equals the hand count on every compared field (0 differences); second recompute (OQ-20) gates `verified` (ADR 0044). The frozen GS-AN-1 v1 `low_sample` for gm1 A and gm2 A disagrees (reference defect PE-R1S3-05, TCR pending with QA); if QA's decision reads rule 0.3 differently, AN-07 returns to `draft` (ADR 0044 rule 2). |
| after OQ-20 (P9, 2026-11-16 at the earliest) | second coach or 4.0+ player | AN-01..AN-07 | → `verified` (planned) | recompute 1 golden match; κ ≥ 0.6 for AN-04/AN-07; rules verified (ADR 0044 rule 3) |
