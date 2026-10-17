# Weakness catalogue v0.1 (R1, Quick Tag)

- **Owner:** pickleball-domain-coach (COACH-4, 2026-10-17). **Used by:** ST-055 (`racket.coaching.weakness`), ST-056/057 (target metric), `scripts/measure/planlib.py` (QA-HARNESS-4a), G04-03 (a).
- **Basis:** FR-109, FR-120; ADR 0003 (rallies lost per game, split serve/receive); metric dictionary v0.1 rules 0.1-0.2. Every mapping is **(judgment)** by the coach; no coaching source is verified [DOM G2].
- **`@needs-verification`:** the side-out part. "Lost on serve concedes no point" depends on side-out scoring (DOM G1 R2, **UNVERIFIED**, P7). The counts below do not depend on it; only "points conceded" (§3) does.

## 1. Terms

- **Side S** is the player's side ("me", FR-005). A **rally lost by S** is a counted rally (not `replay`, `gap` or after the game end: rule 0.1) with `winning_side ≠ S`.
- **Lost on serve:** S was the serving side of that rally (the engine's `serving_side`). **Lost on receive:** the other side served.
- **Unit:** rallies lost per game = count / games in scope (the AN-04 rule: completed games, plus the current game if unfinished), shown to 1 decimal.

## 2. Cells: ending of a rally S lost → weakness and target metric

Rule 0.2 makes S responsible for its own `unforced_error`, `forced_error` and `fault`; an opponent `winner` is the other side's shot. The `responsible_player` tap only adds the per-player line; it never changes the cell.

| Ending (fault subtype) | Weakness | Target metric, lost on serve | Target metric, lost on receive |
|---|---|---|---|
| `unforced_error` by S | Unforced errors (`unforced_errors`) | AN-04 | AN-04 |
| `fault` (`serve`) by S | Serve faults (`serve_faults`) | AN-05 | AN-07 fault share (note a) |
| `fault` (`nvz`, `two_bounce`, `foot`, `other`, or not tagged) by S | Other faults (`other_faults`) | AN-07 fault share | AN-07 fault share |
| `forced_error` by S | Errors under pressure (`errors_under_pressure`) | AN-07 forced-error share | AN-07 forced-error share |
| `winner` by the other side | Opponent winners against you (`opponent_winners`) | AN-01 | AN-02 |
| anything else (no ending) | unattributed (FR-109) | none | none |

- **(a)** A `serve` fault tagged on the receiving side (FR-120's "rallies on receive to serve faults"; e.g. a wrong-receiver call, rule **UNVERIFIED**) stays "Serve faults" because the user tagged it so (the dictionary counts what is tagged). AN-05 counts only serving-side faults, so this half cites AN-07. GS-AN-1 has 5 such rallies.
- A fault with no subtype goes to "Other faults"; the card says "fault type not tagged in x rallies" (as AN-05). AN-05 stays a lower bound.
- **Conservation (FR-109, QD-AN-00):** per game and per serve/receive, the five weaknesses plus unattributed equal the rallies S lost. In R1 Quick Tag always records an ending, so unattributed is 0; the bucket stays for the invariant.

## 3. Serve/receive attribution and points conceded

1. The split comes from the engine's `serving_side` of each rally, never from the tagger.
2. A rally S lost on receive gives the other side a point. A rally S lost on serve gives no point: it costs the serve (server 1 → 2, or a side-out). **`@needs-verification` (DOM G1 R2, P7).**
3. Points conceded per weakness = its lost-on-receive count under side-out scoring; under rally scoring = its total. Shown separately; never used for ranking (ADR 0003).
4. While the side-out rule is unverified, the ranking carries the side-out-unverified mark (field name per PE-4) and the "unofficial scoring" notice.

## 4. Ranking and tie-break

1. Rank by total rallies lost (serve + receive) over the scope. All weaknesses of one player share the same games, so compare the integer counts, not rounded per-game values.
2. Equal counts → catalogue order: **1 Unforced errors, 2 Serve faults, 3 Other faults, 4 Errors under pressure, 5 Opponent winners against you.** Reason (judgment): own unforced mistakes are the most controllable and the cheapest to train; opponent winners are the least.
3. Weaknesses with 0 rallies lost are not listed. Zero games in scope → an empty ranking with a reason, not an error. The plan uses the top 3 (FR-121).

## 5. Primary metric (what the plan targets and cites)

Unforced errors → AN-04. Errors under pressure → AN-07 forced-error share. Other faults → AN-07 fault share. Serve faults → AN-05 if lost on serve ≥ lost on receive, else AN-07 fault share. Opponent winners → AN-01 if lost on serve ≥ lost on receive, else AN-02. The citation (QD-PL-04) is that metric's value and n for side S; for AN-07 the value is the named share.

## 6. R1 targetable metrics

**AN-01, AN-02, AN-04, AN-05, AN-07** (decided by the coach, judgment). AN-03 (points per service turn) and AN-06 (longest run) are summaries of serving and momentum, not a skill a drill trains directly; AN-03 also depends on unverified rotation rules. Drills may name them in `skills`, but plans never target them and coverage (drill-review-checklist §3) does not count them.

## 7. Worked examples (pins ST-055 unit tables, `planlib`, G04-03 a)

Each row: `rank. weakness total = on serve + on receive (per game; primary metric)`; last column: rallies lost = on serve + on receive. Rows are printed by `python3 docs/domain/tools/weakness_example.py`; `--check` fails unless every row below is exact. FR-120 is counted as one game (the scenario gives no game count; the order is the same for any count). "dict §2" is metric-dictionary §2 (the 14-rally example used by G04-01); gm1..gm3 are GS-AN-1 (corrections applied, PROVISIONAL-UNVERIFIED preset).

| Example | Side | Games | Ranking | Rallies lost |
|---|---|---|---|---|
| FR-120 | Ivy | 1 | 1. Unforced errors 10 = 10 + 0 (10.0/game; AN-04)<br>2. Serve faults 4 = 0 + 4 (4.0/game; AN-07 fault) | 14 = 10 + 4; unattributed 0 |
| dict §2 | A | 1 | 1. Opponent winners against you 3 = 0 + 3 (3.0/game; AN-02)<br>2. Unforced errors 2 = 1 + 1 (2.0/game; AN-04)<br>3. Serve faults 2 = 2 + 0 (2.0/game; AN-05) | 7 = 3 + 4; unattributed 0 |
| dict §2 | B | 1 | 1. Other faults 2 = 1 + 1 (2.0/game; AN-07 fault)<br>2. Opponent winners against you 2 = 0 + 2 (2.0/game; AN-02)<br>3. Unforced errors 1 = 0 + 1 (1.0/game; AN-04)<br>4. Errors under pressure 1 = 1 + 0 (1.0/game; AN-07 FE) | 6 = 2 + 4; unattributed 0 |
| gm1 | A | 2 | 1. Opponent winners against you 12 = 6 + 6 (6.0/game; AN-01)<br>2. Errors under pressure 6 = 4 + 2 (3.0/game; AN-07 FE)<br>3. Unforced errors 5 = 1 + 4 (2.5/game; AN-04)<br>4. Serve faults 2 = 1 + 1 (1.0/game; AN-05)<br>5. Other faults 2 = 2 + 0 (1.0/game; AN-07 fault) | 27 = 14 + 13; unattributed 0 |
| gm1 | B | 2 | 1. Unforced errors 11 = 3 + 8 (5.5/game; AN-04)<br>2. Errors under pressure 9 = 6 + 3 (4.5/game; AN-07 FE)<br>3. Opponent winners against you 6 = 1 + 5 (3.0/game; AN-02)<br>4. Other faults 3 = 2 + 1 (1.5/game; AN-07 fault)<br>5. Serve faults 2 = 1 + 1 (1.0/game; AN-05) | 31 = 13 + 18; unattributed 0 |
| gm2 | A | 3 | 1. Unforced errors 9 = 5 + 4 (3.0/game; AN-04)<br>2. Other faults 5 = 1 + 4 (1.7/game; AN-07 fault)<br>3. Opponent winners against you 5 = 3 + 2 (1.7/game; AN-01)<br>4. Errors under pressure 2 = 2 + 0 (0.7/game; AN-07 FE)<br>5. Serve faults 1 = 0 + 1 (0.3/game; AN-07 fault) | 22 = 11 + 11; unattributed 0 |
| gm2 | B | 3 | 1. Opponent winners against you 21 = 7 + 14 (7.0/game; AN-02)<br>2. Unforced errors 6 = 3 + 3 (2.0/game; AN-04)<br>3. Other faults 4 = 0 + 4 (1.3/game; AN-07 fault)<br>4. Errors under pressure 3 = 1 + 2 (1.0/game; AN-07 FE)<br>5. Serve faults 1 = 0 + 1 (0.3/game; AN-07 fault) | 35 = 11 + 24; unattributed 0 |
| gm3 | A | 1 | 1. Opponent winners against you 3 = 1 + 2 (3.0/game; AN-02)<br>2. Unforced errors 1 = 0 + 1 (1.0/game; AN-04)<br>3. Other faults 1 = 1 + 0 (1.0/game; AN-07 fault)<br>4. Errors under pressure 1 = 0 + 1 (1.0/game; AN-07 FE) | 6 = 2 + 4; unattributed 0 |
| gm3 | B | 1 | 1. Opponent winners against you 9 = 0 + 9 (9.0/game; AN-02)<br>2. Unforced errors 1 = 1 + 0 (1.0/game; AN-04)<br>3. Serve faults 1 = 0 + 1 (1.0/game; AN-07 fault)<br>4. Other faults 1 = 1 + 0 (1.0/game; AN-07 fault)<br>5. Errors under pressure 1 = 0 + 1 (1.0/game; AN-07 FE) | 13 = 2 + 11; unattributed 0 |

Cross-checks against metric-dictionary §2b: the unforced-error totals equal AN-04 (gm1 A 5, B 11; gm2 A 9, B 6; gm3 1, 1); rallies lost on serve equal served minus AN-01 wins (gm1 A 32 - 18 = 14); ties are broken by §4 (dict §2 A: Unforced errors before Serve faults; dict §2 B: Other faults before Opponent winners).
