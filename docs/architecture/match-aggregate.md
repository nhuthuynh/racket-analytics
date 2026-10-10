# Design: the `Match` aggregate (games, rallies, outcome inputs, corrections, score as a projection)

- **Status:** Accepted, 2026-10-06, after design review D1 (outcome in §0). Proposed 2026-10-05 for review before Sprint 2 (sprint-01 §4 principal-engineer task, DoR P4; [DPA/DESIGN-15]). The review was held in the repository (review-rounds.md "Design review D1", reviewer senior-backend-engineer) because `sprint-01` was not on GitHub (PE-R3-05). The HTTP contract is `api-sprint-02.md`.
- **Date:** 2026-10-05
- **Author:** principal-engineer
- **Stories it unblocks:** Sprint 2 ST-026, ST-027, ST-030, ST-031, ST-032, ST-034, ST-035 (stretch ST-033, ST-036).
- **Requirements:** FR-045..FR-055, NFR-012, NFR-013, NFR-060, NFR-075, NFR-079.
- **Builds on (code at `17c850d`):** `racket.matches.domain.Match` (lifecycle, setup, participants), `racket.matches.match_state.MatchState` (ST-021: best of 1/3, explicit first server and ends per game, `MatchOver`), `racket.sports.pickleball.rules` (ST-020: `apply`, `fold`, `new_game`, `declare_state`, `RallyOutcome`, `PRESETS`).
- **Rules (ddd-guidelines §4):** one command, one aggregate, one transaction (4.1); the root guards invariants (4.2); keep aggregates small (4.4); pure domain logic (4.5); version what changes interpretation (4.7); user corrections win (4.8); ownership in the aggregate (4.9).

## 0. Design review D1: outcome (principal-engineer, chair, 2026-10-06)

Held late: the BE built ST-026..ST-032 on this doc while it was Proposed (blockers.md 2026-10-05; the EM decision on that start is still open there), so the review compared the doc with the code at `40de20a` as well as with the requirements. Outcome: **accepted with the answers below**; §4 is corrected (no `keep_in_game`). Nothing in §2-§6 changes the built code. Open coach questions (§8 Q1, Q2) stay `@needs-verification` and do not block acceptance (ADR 0009).

| Finding | Answer | Where |
|---|---|---|
| BE-D1-01 error body | Keep the api-sprint-00 §3 envelope; the harness reads `error.code`. Fixed in `scripts/measure/live_tagging.py` `_code()` with a regression test | api-sprint-02 §1.1 |
| BE-D1-02 `If-Match` | Accept `3`, `"3"`, `W/"3"`; missing or malformed is 409 `stale_match` (no 428); `ETag: "<version>"` on every command and the sheet | api-sprint-02 §1.2 |
| BE-D1-03 row `number` | 1-based position among kept rallies of the match, ordered by `start_ms`, then `seq` | api-sprint-02 §2.1 |
| BE-D1-04 version outside the sheet | Commands answer `{version, sheet}`; the sheet has no version, timestamp or correction id (C-04 byte-identical) | api-sprint-02 §1.3 |
| BE-D1-05 §8 Q3 | Agreed: a preset per (`rules_version`, `format`); no silent default: an unknown pair is not scored and its commands get 409 `rules_unavailable` (PE-S2-R1-05, BE) | api-sprint-02 §2.1; ST-035 |
| BE-D1-06 append-only and cascade | Agreed: the trigger allows only a `DELETE` with `pg_trigger_depth() > 1` (the cascade from `matches`), plus the REVOKE; IT-02-03 covers both | api-sprint-02 §5; migration 0010 |
| As built, not in the Proposed doc | `GET /matches/{id}/video` (T-01 whole video), `GET …/corrections`, `POST …/rallies/{id}/resolution`, the codes `game_not_started`, `game_not_over`, `decision_needed`, `nothing_to_undo` and the field code `time_after_video` (QA-S2-API-02) are accepted into the contract | api-sprint-02 §3, §4 |

## 1. The decision in one paragraph

The `Match` aggregate stores **inputs only**: the per-game set-up the player states (first server, ends switched, or a declared mid-game start) and, per rally, the **outcome input** the player tagged (times, ending, winning side, optional responsible player and fault subtype). The score is **never stored as an editable value**: the score sheet is a pure projection, `project(match) -> ScoreSheet`, computed by folding the rules engine over the stored inputs under the match's pinned `rules_version` (FR-049, NFR-075). A correction changes an input and appends an audit row; the projection is simply recomputed, so "replay from rally *k*" equals a fresh fold by construction (C-01) and undo restores a byte-identical sheet (C-04). Rallies that a correction pushes past the end of a game are never deleted; the projection marks them "needs your decision" (FR-053).

## 2. Model

```
Match (root)                         owner_id, rules_version (pinned), best_of, format, scoring_system,
 │                                   status, media_asset_id, participants, version (optimistic lock)
 ├── Game (entity, 1..best_of)       number, start: NewGame(first_server, ends_switched)
 │                                                 | DeclaredStart(serving_side, serving_score,
 │                                                                receiving_score, server_number,
 │                                                                ends_switched)
 ├── Rally (entity, ordered)         id (UUID), game_number, seq (1..n within the match),
 │                                   start_ms, end_ms, input: OutcomeInput, withdrawn (bool)
 └── Correction (entity, append-only) id, rally_id | game_number, actor_id, at, kind, field,
                                     old_value, new_value, undoes (Correction id | null)

OutcomeInput (value)                 ending ∈ {winner, unforced_error, forced_error, fault, replay}
                                     winning_side (null only for replay)
                                     responsible_player (slot A1/A2/B1/B2, optional)
                                     fault_kind (only for fault, optional subtype per FR-050)

ScoreSheet (read value, projected)   rows: seq, game, start_ms, server, score_before, score_after,
                                     winning_side, ending, corrected_by_user, marker ∈ {none,
                                     needs_decision}; games: winner per game; match winner;
                                     rules_version; unofficial (bool, FR-055)
```

Not in the aggregate (ddd-guidelines §4.4): Vision's `EventTrack` and `Shot` rows (R2; they reach `Rally` through the ACL later), media bytes and upload sessions (`video_ingest`), analytics (Sprint 3, reacts to events).

### 2.1 Outcome input → engine outcome

The engine needs only who won the rally (`RallyOutcome.rally_winner`); the ending detail is analytics data (QD-RE-09, P7). The mapping is one pure function in `racket.matches`:

| `ending` | Engine outcome | Responsible player must be on (TDD plan, judgment, coach to confirm) |
|---|---|---|
| `winner` | `RallyOutcome.won_by(winning_side)` | the winning side |
| `unforced_error`, `forced_error` | `RallyOutcome.won_by(winning_side)` | the losing side |
| `fault` | `RallyOutcome.fault(by=winning_side.other, kind=fault_kind or OTHER)` | the losing side |
| `replay` | `RallyOutcome.replay()`; `winning_side` must be null | none |

Forced and unforced errors stay apart in storage; whether analytics merges them depends on the κ gate (FR-050). The input keeps what the player said; nothing is inferred.

## 3. Invariants the root guards

| # | Invariant | Refusal | Source |
|---|---|---|---|
| I1 | Tagging needs a received video (`status = video_received`) | `MatchNotReady` (409) | NFR-060; sprint-02 TDD `Match.tag_rally` 2 |
| I2 | `rules_version`, `format`, `scoring_system` and `best_of` are fixed once the first rally exists | `Conflict` | QD-RE-02; ddd §4.7 |
| I3 | Games are numbered 1..`best_of`; game *n*+1 starts only after game *n* is over in the projection; no game starts after the match is decided | `IllegalState` / `MatchOver` | FR-045; ST-021 `start_game` |
| I4 | A declared start passes `declare_state` (server number 1-2 in doubles; score not already game over) | `IllegalStart` (422, field-level) | FR-046; SOD-13..15 |
| I5 | `0 ≤ start_ms < end_ms`, integer ms from video start; rallies ordered by `start_ms`; no overlap with any non-withdrawn rally; games follow each other on the video: a rally of game *g* starts after every kept rally of an earlier game ends and ends before every kept rally of a later game starts (checked on tags and times corrections, `out_of_game_order`; PE-S2-R1-04). Inside one game the order is free (the sheet sorts by `start_ms`) | `InvalidRally` (422) | QD-TR-02; ddd §4.2 |
| I6 | `OutcomeInput` is well formed (§2.1 table: side present except replay, fault kind only for faults, responsible player on the right side) | `InvalidOutcome` (422) | FR-050; sprint-02 TDD `RallyOutcome` |
| I7 | A new tag goes to the first game the projection says is not over (after a correction reopens game *n*, an empty game *n*+1 waits; PE-S2-R1-02); it is refused when every started game or the match is over | `GameOver` / `MatchOver` | FR-045 |
| I8 | Every change after a tag (correct, withdraw, undo, resolve) appends exactly one `Correction` in the same transaction; corrections are never updated or deleted | DB refuses UPDATE/DELETE | FR-052; IT-02-03 |
| I10 | A match holds at most `max_rallies` stored rallies (withdrawn included) and `max_changes` audit rows (`Limits`, from settings; defaults 500 and 2000); a match whose (`rules_version`, `format`) has no preset takes no game start and no tag (PE-S2-R1-05) | `ScorebookFull` (422) / `RulesUnavailable` (409) | SEC-S2-R1-01; BE-D1-05 |
| I9 | Only the owner can load or change the match (repository filters by `owner_id`; other owners get 404) | `NotFound` | ddd §4.9; IT-02-05 |

I7 is checked against the projection *before* the change, so it is the same code path as the score sheet: there is one source of truth for "is the game over".

## 4. Commands (one aggregate, one transaction each)

| Command | Effect on inputs | Audit row | Story |
|---|---|---|---|
| `start_game(first_server, ends_switched)` / `declare_start(...)` | adds a `Game` | `kind=game_started` | ST-021 (domain exists), ST-034 |
| `tag_rally(start_ms, end_ms, input)` | appends a `Rally` to the current game | none (the tag is the original fact); undo of it is audited | ST-026, ST-027 |
| `correct_rally(rally_id, field, new_value)` | changes one field of one rally's input or times; `field = outcome` sets the whole outcome input at once (the only way between `replay` and a scored ending, PE-S2-R1-03) | `kind=correction`, old and new value | ST-031, ST-032 |
| `withdraw_rally(rally_id)` | `withdrawn = true` (the row stays) | `kind=withdrawal` | ST-031 (undo of a tag) |
| `undo()` | reverses the newest not-yet-undone change by this match (a correction, a withdrawal, a game start, or the newest tag, which becomes a withdrawal) | `kind=undo`, `undoes=<id>` | ST-031, C-04 |
| `resolve(rally_id, decision)` | for a `needs_decision` rally only: `move_to_next_game` (sets `game_number`; the next game must be started; C-02, PE-S2-R2-01, provisional: only the **latest kept rally of game *n*** by `start_ms`, then `seq`, so marked rallies move forward latest kept rally first and no game-*n* rally is left behind a game-*n*+1 rally on the video (I5); any other rally → 422 `decision`/`not_last_in_game`), `move_to_previous_game` (C-03, PE-S2-R1-02, provisional: the earliest kept rally of game *n*+1 back into game *n* while game *n* is not over) or `withdraw`. There is no `keep_in_game`: a rally after the end of its game can never be scored in it, and one in a game after an unfinished game cannot be scored before that game ends | `kind=resolution` | ST-032 (provisional) |

Each command: load the whole aggregate (a 3-game match is about 70 rallies; judgment), check the `version` from the client's `If-Match` (IT-02-04: one wins, the other gets 409 `stale_match` and retries), apply, compute the projection, save, bump `version`, commit. Nothing is written if any step fails (IT-02-02). The response carries the new projection, so the client never computes a score itself beyond the optimistic display (NFR-012a).

## 5. The projection

```
project(match) -> ScoreSheet:
    config = PRESETS[match.rules_version, match.format]        # §8 Q3
    for each game g in order:
        state = new_game(config, g.first_server)  or  declare_state(config, **g.declared)
        for each non-withdrawn rally r in g, ordered by seq:
            if state.is_over:  row(r, marker=needs_decision); continue      # C-02
            after = apply(state, to_engine(r.input), config)
            row(r, before=state, after=after, server=state.server_player)
            state = after
    if game g is not over and game g+1 has rallies: mark g+1's rallies needs_decision    # C-03
    corrected_by_user(r) = r has a correction or withdrawal that is not undone
    unofficial = any rule in config is unverified (today: always; FR-055)
```

- **Pure:** no clock, no I/O, no randomness; it lives in `racket.matches` and imports only the Published Language of the rules plug-in (context map R5; the existing `test_architecture.py` rule).
- **Equal to a fresh fold:** there is no incremental path to drift from. "Replay *k..n*" (FR-053) is the same function; `replay_from(k)` in the TDD plan is a test name, not a second algorithm.
- **Byte-identical:** the sheet is serialised with a canonical encoder (sorted keys, no floats, times in integer ms); the golden replay (QD-TR-04, NFR-075) compares bytes. `corrected_by_user` is derived, so an undo removes the marker and the sheet is identical (C-04).
- **Cost:** O(rallies) `apply` calls per request; about 70 per 3-game match. No stored snapshot is needed for NFR-013 (1.5 s p95). If IT-02-08 shows otherwise, add a per-game cache keyed by (match `version`, game) and never read it as a source of truth (judgment; sprint-02 risk row).
- **Errors:** the engine returns `DomainError` values; the projection never raises on stored data. A stored input that the engine refuses (impossible after I6/I7, but defensive) marks the row `needs_decision` and logs `match.projection_refused` with `match_id` only.

## 6. Persistence (ST-026)

New migration (next free number), owned by `racket.matches` only (context map rule 1):

| Table | Columns | Notes |
|---|---|---|
| `matches` (existing) | add `best_of SMALLINT NOT NULL DEFAULT 3 CHECK (best_of IN (1,3))`, `version INTEGER NOT NULL DEFAULT 0` | `rules_version` already stored and server-set (T-MS-1) |
| `match_games` | `match_id`, `number`, `first_server`, `ends_switched`, `declared_serving_side`, `declared_serving_score`, `declared_receiving_score`, `declared_server_number` (all four null or none), PK (`match_id`, `number`) | `ON DELETE CASCADE` from `matches` |
| `match_rallies` | `id UUID PK`, `match_id`, `game_number`, `seq`, `start_ms BIGINT`, `end_ms BIGINT`, `ending`, `winning_side`, `responsible_player`, `fault_kind`, `withdrawn BOOL`, unique (`match_id`, `seq`), CHECKs mirroring I5/I6 | no score columns at all (FR-049) |
| `match_corrections` | `id UUID PK`, `match_id`, `rally_id` null, `game_number` null, `actor_id`, `at`, `kind`, `field`, `old_value JSONB`, `new_value JSONB`, `undoes` null | `REVOKE UPDATE, DELETE` from the app role **and** a `BEFORE UPDATE OR DELETE` trigger that raises, except for the cascade from deleting the match (account/match deletion, Sprint 3) (IT-02-03) |

The repository loads and saves the whole aggregate; no other module reads these tables. Old-value and new-value JSON hold only tag fields (sides, slots, enums, integers), never names or free text, so the audit trail adds no personal data beyond `actor_id` (IT-02-09).

## 7. Events

`RallyScored`, `ScoreCorrected` and `MatchScored` are named in the canvas for Analytics (context map R6). Sprint 2 has no consumer, so Sprint 2 publishes nothing (judgment, [AQS/ENG-04]). The audit table plus the stored inputs are a complete history, so the Sprint 3 Analytics design note can add an outbox written in the command's transaction without a data migration.

## 8. Open questions (owner, due)

| # | Question | Owner | Due |
|---|---|---|---|
| Q1 | C-02/C-03 resolution choices (move to next game, withdraw; D1 removed "keep"; move to the previous game for C-03, earliest rally first, built provisionally for PE-S2-R1-02; move to the next game for C-02, latest kept rally first (`not_last_in_game`), built provisionally for PE-S2-R2-01) and which rallies of the next game are marked in C-03 (all of them, or only up to the first point) | pickleball-domain-coach | before ST-032 (rows `@needs-verification`, ADR 0009) |
| Q2 | Responsible-player side rules for forced errors (table §2.1) | pickleball-domain-coach | before ST-027 tests are final |
| Q3 | `PRESETS` is keyed by `rules_version` only and holds a doubles config; singles (ST-035) needs one config per format. Proposal: key by (`rules_version`, `format`) inside `racket.sports.pickleball.rules`, no other change | senior-backend-engineer with QA | ST-035 |
| Q4 | Undo depth and scope: newest change only, repeated (stack) — proposed; no redo in R1 | principal-designer | ST-031 |
| Q5 | Gaps (FR-047, stretch ST-036): a gap is a `Game`-level item with a resync `DeclaredStart`; the projection restarts from it. Confirm before building | principal-engineer | if ST-036 is pulled in |

## 9. How this is verified

| Claim | Test (Sprint 2 plan) |
|---|---|
| Projection = fold over inputs (P6); replay rows change nothing (P8) | unit `ScoreSheet` 1-3; property test against `fold` |
| Golden replay is byte-identical under the pinned `rules_version` | QD-TR-04, NFR-075; IT-02-01 (30 rallies) |
| Correction of rally *k* equals a fresh build (C-01); undo is byte-identical (C-04) | `corrections_replay.feature`; unit `Undo` 2 |
| Rallies past a game's end are kept and marked (C-02, C-03) | `@needs-verification` scenarios; unit `replay_from` 3-4 |
| All-or-nothing commands; concurrent tags conflict | IT-02-02, IT-02-04 |
| Audit is append-only and owner-scoped | IT-02-03, IT-02-05, IT-02-09 |
| No score column exists | a schema test: `match_rallies` has no column named like `score%` (judgment) |
| Server-confirmed correction ≤ 1.5 s p95 on 3 games | IT-02-08 |
