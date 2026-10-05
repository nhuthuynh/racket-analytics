# Sprint 2: Quick Tag to score sheet (spec M0 "Done when", labelled unofficial)

- **Dates:** Mon 2026-11-02 → Fri 2026-11-13
- **Planning:** 2026-11-02 · **Sprint review:** 2026-11-13 · **Retrospective:** 2026-11-13
- **Retro file:** `docs/retros/2026-11-13-sprint-02.md` from [`docs/retros/TEMPLATE.md`](../retros/TEMPLATE.md). Format: **Mad/Sad/Glad**. Focus area: **domain correctness and the coach's verification flow** [EP/ENG-15].
- **Status:** Planned (just-in-time refinement at Sprint 2 planning). **Preconditions:**
  - the `Match` aggregate design doc (principal-engineer, Sprint 1) is approved [DPA/DESIGN-15];
  - the Quick Tag flow, keyboard map and score-sheet states (principal-designer, Sprint 1) are done;
  - ADR 0009 is ratified (otherwise ST-029, ST-032, ST-034 and ST-035 drop to their mechanics only, see §3.1).
- **Progress and status:** `docs/sprints/02/progress.md`, `docs/sprints/02/status.json`.
- **Related ADRs:** 0002, 0003 (rallies-lost unit, for the data captured here), 0007, 0009, 0010. Citation prefixes: working-agreement §0.

## 1. Sprint goal

- A player tags every rally of an uploaded match by tapping or by keyboard (start, end, winning side, ending, optional responsible player). Each tag shows the new score at once and announces it to screen readers.
- The player opens a score sheet that lists every rally with server, score before and after, winner and ending. The score is computed by replaying the rules, never stored as an editable value, and the sheet is labelled "unofficial scoring (rules not yet verified)" (FR-055).
- The player can undo any tag and correct any rally. Later rallies are re-scored in one step. Rallies that a correction pushes past the end of a game are kept and marked "needs your decision", never deleted. Every change is in an audit trail.
- A match that starts mid-game, and singles matches, are scored too, under the provisional preset.
- Every rally row opens the video at that rally.

This demonstrates spec M0's "Done when": *a user can tag a match by hand and get a score sheet*. It is "correct" only in the unofficial sense until OQ-01 is answered and NFR-003 passes (ADR 0009).

**Not in this sprint:** stats (Sprint 3), training plans (Sprint 4), correction consequences and gaps (stretch here), age gate and retention settings (Sprint 4).

## 2. Capacity (ADR 0010)

Load factor: the lower of 85% and the median completed ratio of Sprints 0-1. Planned at **80% (12.8 units per lane)**; the EM adjusts at planning from `status.json`.

| Lane | Committed | Stretch | Notes |
|---|---|---|---|
| BE | 12.5 | 1.5 | Stream 1: `matches` aggregate, tagging, corrections. Stream 2: `sports/pickleball` singles and starts, `video_ingest` expiry and media URLs |
| FE | 12.5 | 1.5 | Stream 1: Quick Tag and keyboard. Stream 2: score sheet, video seek, undo |
| QA | 4 | — | Golden tables first; E2E journey v1; performance baseline |
| SRE | 1 | — | Media serving (range requests, signed URLs); Locust in CI |
| ML | 2 | — | Gold-set label schema and capture protocol |
| **Total** | **32** | 3 | |

## 3. Committed backlog

| Story | Title | FR / NFR | Owner (R) | Required reviewers | Size | Depends on |
|---|---|---|---|---|---|---|
| ST-026 | `Match` aggregate persistence: games, rallies, outcome inputs; score as a projection by replay | FR-049 (backend); NFR-075 | BE | QA, principal-engineer | M | design doc; ST-020, ST-021 |
| ST-027 | Quick Tag a rally | FR-050; NFR-012, NFR-028, NFR-030 | BE (M) + FE (L) | QA, principal-designer, pickleball-domain-coach, principal-engineer (API contract) | M+L | ST-026 |
| ST-028 | Keyboard tagging with a remappable key map | FR-051; NFR-034 | FE | QA, principal-designer | M | ST-027 |
| ST-029 | Score call and polite announcement after each tag | FR-048 (call format provisional) | FE | QA, principal-designer, pickleball-domain-coach | S | ST-027 |
| ST-030 | Score sheet with the "unofficial scoring" label | FR-049, FR-055; NFR-011, NFR-029, NFR-033, NFR-034 | FE (M) + BE (XS) | QA, principal-designer, pickleball-domain-coach | M+XS | ST-026 |
| ST-031 | Undo and correction audit | FR-052 | BE (M) + FE (S) | QA, principal-engineer, security-privacy-engineer (audit) | M+S | ST-026 |
| ST-032 | Corrections replay the score; conflicting rallies kept (a) | FR-053 (a); NFR-013 | BE (M) + FE (S) | QA, principal-engineer, pickleball-domain-coach | M+S | ST-031, ST-041 |
| ST-034 | Start the score sheet mid-game (a) | FR-046 (a) | BE (S) + FE (XS) | QA, pickleball-domain-coach | S+XS | ST-026, ST-041 |
| ST-035 | Side-out singles (a) | FR-042 (a) | BE | QA, pickleball-domain-coach | S | ST-020, ST-041 |
| ST-037 | Jump to the video moment with short-lived media URLs | FR-027; NFR-014, NFR-055 | BE (S) + FE (S) | QA, security-privacy-engineer | S+S | ST-027 |
| ST-038 | Abandoned uploads expire | FR-024; NFR-066 (d) | BE | QA, security-privacy-engineer | S | ST-017 |
| ST-039 | E2E journey v1 and performance baseline | NFR-010, NFR-012, NFR-013, NFR-017 (baselines) | QA (M) + SRE (S) | principal-engineer, sre-devops-engineer | M+S | ST-030 |
| ST-040 | Gold-set label schema, manifest v1 and footage capture protocol | FR-151 (prep for QD-GD-03/-04/-07) | ML | QA, security-privacy-engineer (consent), pickleball-domain-coach | M | OQ-06 |
| ST-041 | Golden tables written first: SOS rows, declared starts SOD-13..15, corrections C-01..C-04 | NFR-001 (provisional rows) | QA | pickleball-domain-coach, principal-engineer | M | — |

**Security carry-over from Sprint 1 (proposed 2026-10-05 by sre-devops-engineer, review round 2, SEC-R5-S1-01; EM confirms at planning):**

| Story | Title | FR / NFR | Owner (R) | Required reviewers | Size | Depends on |
|---|---|---|---|---|---|---|
| ST-042 | Least-privilege credentials for the media sandbox worker (threat model S1-F3, v0 F-1). The worker gets its own Postgres role with SELECT/UPDATE only on the job, media and upload tables, and no access to `sessions`, `sign_in_*` or `accounts`; the worker also gets its own S3 key. Then a test shows that a worker-uid process reading `/proc/1/environ` can no longer read `sessions` | NFR-054; ASVS 14.x (judgment) | BE (grants migration, S) + SRE (Compose roles, SeaweedFS identity, S) | security-privacy-engineer, principal-engineer | S+S | — |

ST-042 is a **gate before any non-dev deployment**, like S1-F2 and ST-038. The Sprint 1 part is already done: the mailer no longer holds the S3 key.

**Stretch:** ST-033 Correction consequences (FR-054; FE S + BE XS); ST-036 Gaps and resync (FR-047; BE XS + FE XS, sized S overall).

### 3.1 Acceptance notes per story

- **ST-026:** one command changes one aggregate in one transaction (ddd-guidelines §4.1). Score before/after is computed by `fold` over stored outcome inputs and is never an editable column (FR-049; ENG §3.2). Every stored output carries `rules_version` (NFR-075). A golden replay of stored rallies reproduces the stored score sheet byte for byte (QD-TR-04).
- **ST-027:** controls per FR-050 and DES FR-UX-60: rally start, rally end, winner side, ending (winner, unforced error, forced error, fault, replay), optional responsible player, optional fault subtype. Controls are ≥ 48 dp with no overlap of the focused control [DPA/DESIGN-10, DPA/DESIGN-07]. No dragging is needed (NFR-030) [DPA/DESIGN-05]. The optimistic score update appears within 200 ms p95 (NFR-012a). FR-050 now states the R1 behaviour: "the video continues from the end of rally 7, ready to mark rally 8"; jumping to the next rally start waits for FR-087 in R2 (review-log RL-02, 2026-10-03).
- **ST-028:** key map shown with `?` (DES FR-UX-61). Single-key shortcuts can be turned off or remapped. Keyboard tagging gives a score sheet identical to tapping (FR-051).
- **ST-029:** after each tag or correction, a polite live region announces "Rally 7: them. Score 4-6-1." (FR-048, DES FR-UX-62). The call format is provisional; its scenario is tagged `@needs-verification` until the coach verifies it.
- **ST-030:** a semantic table with caption and row headers, readable at 360 px by stacking (FR-049, DES FR-UX-70). Markers for corrected rallies ("corrected by you") and conflicts in text, not colour alone (NFR-034). The label "unofficial scoring (rules not yet verified)" appears on every score sheet while any rule in the scoring path is unverified (FR-055).
- **ST-031:** every tag and correction can be undone. Corrections are append-only rows (who, when, field, old value, new value) and set `corrected_by_user` (FR-052). The table is protected against UPDATE and DELETE at the database level (judgment).
- **ST-032:** changing rally *k* replays *k..n* atomically. If a correction ends or un-ends a game, the affected rallies are marked "needs your decision" (FR-053). The mechanics (replay equals a fresh fold; undo restores a byte-identical sheet: C-01, C-04) are Ready. The game-end cases (C-02, C-03) are tagged `@needs-verification` (ADR 0009). Server-confirmed state arrives within 1.5 s p95 for a 3-game match (NFR-013).
- **ST-034:** the user declares a starting score and serving side; impossible states are refused (FR-046). Rows SOD-13..SOD-15 are `@needs-verification`.
- **ST-035:** two-number call; a rally lost by the server is a side-out; serving court by parity of the server's score (FR-042). All rows `@needs-verification`.
- **ST-037:** rally rows link to the video at the rally's start time (FR-027). Media is served by presigned URLs with TTL ≤ 15 min, never with session tokens in the URL (NFR-055) [AQS/SEC-05 14.2.1], with HTTP range support for seeking. Click to first frame playing ≤ 1.5 s p95 on the reference profile (NFR-014; reference profile pending OQ-17).
- **ST-038:** an upload not completed within 24 h (configurable) expires; its bytes are freed and it is no longer listed or resumable (FR-024; ADR 0006, Proposed).
- **ST-039:** Playwright journey v1: sign in → set up → upload fixture → Quick Tag 6 rallies → score sheet equals the golden sheet (QD §7, first half). Locust baseline at 50 RPS for match, score-sheet and correction endpoints (NFR-010, NFR-013), and tag-to-current timing (NFR-017). Baselines are recorded; they become gates at the R1 review (Sprint 5).
- **ST-040:** label schema for Full Tag (hit, bounce, hitter, rally boundaries, outcome, facets) and the gold-set manifest v1 per QD §8. A written capture protocol for team-recorded footage with written consent from everyone filmed (OQ-06 recommendation), split by venue (FR-151). No real-match footage is collected before the PO answers OQ-06.
- **ST-041:** QA writes the SOS rows, SOD-13..SOD-15 and C-01..C-04 from QD §2.2 before ST-032, ST-034 and ST-035 start. With Sprint 1's SOD/F/M rows this reaches the ≥ 46 rows of NFR-001.

## 4. Task breakdown per role agent

| Agent | Tasks | Due | Done-check |
|---|---|---|---|
| engineering-manager | Adjust load factor from retro 0/1 data; brief agents; review loop; metrics; retro | D1, daily, D10 | `status.json` complete |
| product-manager | Confirm the R1 exit criteria and usability-test plan with the PO (OQ-20); chase OQ-01 (latest useful date: Sprint 3 planning) | D3 | Answers recorded |
| business-analyst | Confirm the FR-050 R1 video behaviour with the PO (fixed in FR-050, review-log RL-02); write Sprint 3 stories (stats, evidence, deletion, labelling tool, drill schema) | D2, D8 | Sprint 3 stories meet DoR |
| principal-engineer | Review ST-026/ST-032 for aggregate invariants; Analytics design note (metric dictionary, recompute on `RallyScored`/`ScoreCorrected`) for Sprint 3 | D9 | Design note approved |
| principal-designer | Review Quick Tag, keyboard and score-sheet UI; stats dashboard, metric card and "Show me" flows with all states for Sprint 3 [DPA/DESIGN-11]; moderated usability-test protocol for NFR-036 (Sprint 5) | D5, D9 | Checklists done |
| security-privacy-engineer | Review audit trail, media URLs and expiry; deletion threat notes for Sprint 3 (FR-006/007) | D6 | Notes attached |
| pickleball-domain-coach | Review all rule-related scenarios; verify call format and rows when OQ-01 lands; metric-dictionary entries AN-01..AN-07 to `coach-reviewed` for Sprint 3 (QD-AN-03) | D8 | Each entry has a definition and min sample |
| senior-backend-engineer | ST-026, ST-027 (API), ST-030 (API), ST-031, ST-032, ST-034, ST-035, ST-037 (API), ST-038 | D2-D9 | Scenarios green |
| senior-frontend-engineer | ST-027 (UI), ST-028, ST-029, ST-030, ST-031 (UI), ST-032 (UI), ST-034 (UI), ST-037 (UI); stretch ST-033, ST-036 | D3-D9 | Playwright, axe and keyboard journeys green |
| senior-qa-engineer | ST-041 (D1-D2), ST-039, sprint test report | D2, D9, D10 | Report separates `@needs-verification` |
| sre-devops-engineer | ST-039 (Locust in CI); media range requests and URL signing config; retention job scheduler skeleton | D6 | Locust job runs |
| senior-ml-cv-engineer | ST-040; plan SPIKE-02/03 inputs for Sprints 3-5 | D8 | Schema and protocol merged |

## 5. TDD plan (negative case first) [EP/ENG-18]

| Domain object / unit | Context | First tests, in order |
|---|---|---|
| `Rally` | matches | 1. end before start → error; 2. overlapping an earlier rally → error; 3. times are integer ms from video start (QD-TR-02) |
| `RallyOutcome` | matches | 1. unknown ending → error; 2. a responsible player for an error or fault must be on the side that lost the rally (judgment; coach to confirm); 3. a responsible player for a winner must be on the winning side; 4. responsible player optional |
| `Match.tag_rally` | matches | 1. tag on a match that is over → `MatchOver`; 2. tag on a match not yet uploaded → refused (NFR-060); 3. a tag appends a rally and the projection shows the new score |
| `ScoreSheet` projection | matches | 1. empty match → empty sheet; 2. projection equals `fold` over outcomes (P6); 3. replay rally rows show no score change (P8); 4. golden replay byte-identical (NFR-075) |
| `Correction` | matches | 1. correction of a non-existent rally → error; 2. correction records old and new values; 3. corrections are never edited, only appended; 4. a correction sets `corrected_by_user` |
| `Undo` | matches | 1. undo with nothing to undo → error; 2. undo of a correction restores a byte-identical sheet (C-04); 3. undo is itself audited |
| `replay_from(k)` | matches | 1. k out of range → error; 2. replay equals a fresh fold (C-01); 3. game ending earlier marks later rallies `conflict`, keeps them (C-02, provisional); 4. un-ending a game marks the next game's first rallies `conflict` (C-03, provisional) |
| `DeclaredStart` | matches / sports | 1. server number 3 → `IllegalStart` (SOD-15); 2. score already game over → `IllegalStart` (SOD-14); 3. "0-0-1" accepted (SOD-13) |
| `SinglesRules` | sports/pickleball | 1. rally after game over → `GameOver`; 2. server loses → side-out (no server 2); 3. court by parity of the server's score |
| `ScoreCall` formatter | sports/pickleball | 1. doubles call has three numbers, serving side first; 2. singles call has two numbers |
| `UploadExpiryPolicy` | video_ingest | 1. 23 h 59 min old → not expired; 2. 24 h old → expired; 3. completed uploads never expire by this rule |
| `MediaUrlPolicy` | video_ingest | 1. TTL above 15 min refused; 2. URL never contains the session token |

Front-end (Vitest): tagging reducer (1. "end" before "start" ignored; 2. optimistic score rolls back on a server error), key-map store (1. remap to a used key refused; 2. turning shortcuts off disables single keys only).

## 6. Integration tests

| ID | Boundary | Test | Story |
|---|---|---|---|
| IT-02-01 | API ↔ DB | Tag 30 rallies; stored outcomes replay to the same sheet; `rules_version` stored | ST-026 |
| IT-02-02 | API ↔ DB | A failure injected in the middle of a correction replay rolls back everything; the sheet is unchanged | ST-032 |
| IT-02-03 | DB | UPDATE or DELETE on the corrections table is refused | ST-031 |
| IT-02-04 | API ↔ DB | Concurrent tags on the same match: one wins, the other gets a conflict and retries (optimistic locking, judgment) | ST-027 |
| IT-02-05 | BOLA matrix | Rally, correction, undo, score-sheet and media-URL routes added; Carlos gets 404 on each | ST-026..ST-037 |
| IT-02-06 | API ↔ store | Presigned URL expires after its TTL; range requests return 206 | ST-037 |
| IT-02-07 | Scheduler ↔ store ↔ DB | Expiry job removes the object and hides the session after 24 h (clock injected) | ST-038 |
| IT-02-08 | API | Server-confirmed correction on a 3-game fixture within 1.5 s p95 over 50 runs | ST-032 |
| IT-02-09 | Logs | Correction and undo log lines carry `match_id` and pseudonymous user ID only | ST-031 |

**E2E (Playwright):** E2E-02-01 journey v1 (ST-039). E2E-02-02 keyboard-only tagging of the 6-rally fixture produces the same sheet as tapping. E2E-02-03 screen-reader announcement text appears in the live region after each tag. E2E-02-04 seek from rally row to playing video ≤ 1.5 s on the throttled profile. E2E-02-05 any call can be fixed in ≤ 2 taps or keys from where it is seen (NFR-036d). axe on every page; viewport matrix on the score sheet.

**Fixture:** the 6-rally fixture is a team-recorded, consented clip (GD-07 #2) if OQ-06 is answered. Otherwise the synthetic clip from ST-011 is used with scripted rally boundaries; tagging does not depend on what the video shows (judgment).

## 7. Gherkin scenarios

### 7.1 Quick Tag and keyboard

```gherkin
# tests/features/quick_tag.feature
@M0 @story-ST-027 @nfr-012
Feature: Quick Tag
  A player records each rally's outcome by hand; the rules engine scores it.

  Background:
    Given Ivy is tagging her doubles match "Saturday doubles"

  Rule: Each tagged rally is scored immediately

    Scenario: Tag a rally
      Given rally 7 has been marked from start to end
      When she records it as won by the other side with "unforced error" by herself
      Then rally 7 shows the new score
      And the error is attributed to her
      And the video continues from the end of rally 7, ready to mark rally 8

    Scenario: Responsible player skipped
      Given Ivy has tagged rally 8 without choosing a responsible player
      When she opens the score sheet
      Then rally 8 shows its winner and ending
      And rally 8 shows "player not tagged"

    Scenario Outline: Every ending can be recorded
      Given rally 9 has been marked from start to end
      When she records it as won by her side with ending "<ending>"
      Then rally 9 shows ending "<ending>" on the score sheet
      Examples:
        | ending         |
        | winner         |
        | unforced error |
        | forced error   |
        | fault          |

    Scenario: A replay does not change the score
      Given the score before rally 10 is "5-5-1"
      When she records rally 10 as a replay
      Then the score after rally 10 is still "5-5-1"

  Rule: A player on the wrong side cannot be blamed

    Scenario: Error attributed to the winning side
      Given rally 11 has been marked from start to end
      When she records it as won by her side with "unforced error" by her own partner
      Then she is told the player who made the error must be on the side that lost the rally
```

```gherkin
# tests/features/keyboard_tagging.feature
@M0 @story-ST-028 @nfr-034
Feature: Keyboard tagging
  Rule: Keyboard and touch give the same result

    Scenario: Keyboard only
      Given Ivy uses a keyboard and no pointer
      When she tags rallies 1 to 6 of the fixture match using keys only
      Then the score sheet is identical to tagging the same rallies with taps

  Rule: Shortcuts are discoverable and can be changed

    Scenario: Show the key map
      Given Ivy is on the tagging screen
      When she presses "?"
      Then she sees every tagging shortcut and what it does

    Scenario: Turn single-key shortcuts off
      Given Ivy has turned single-key shortcuts off
      When she presses "1" while the video has focus
      Then no winner is recorded
```

### 7.2 Score call (provisional format)

```gherkin
# tests/features/score_call.feature
@M0 @story-ST-029 @needs-verification
Feature: Score call and announcement
  The three-number call format is unverified [DOM G1 R6].

  Rule: Every tag is announced without moving focus

    Scenario: Screen-reader user tags a rally
      Given Ivy uses a screen reader while tagging
      When she tags rally 7 as won by the other side
      Then she hears the rally number, the winner and the new score
      And her focus stays on the tagging controls
```

### 7.3 Score sheet and unofficial label

```gherkin
# tests/features/score_sheet.feature
@M0 @story-ST-030 @nfr-033
Feature: Score sheet
  Rule: The score sheet is a complete text record of the match

    Scenario: Read the match without the video
      Given Ivy has tagged a 3-game match
      When she opens the score sheet
      Then every rally shows its number, server, score before and after, winner and ending
      And corrected rallies are marked "corrected by you" in text

    Scenario: Narrow phone screen
      Given Ivy opens her score sheet on a screen 360 pixels wide
      Then every rally's details can be read without scrolling sideways

  Rule: Unverified rules are never presented as official

    Scenario: Rules not yet verified
      Given the active rules preset contains an unverified rule
      When Ivy opens any score sheet
      Then she sees "unofficial scoring (rules not yet verified)"
```

### 7.4 Undo and corrections

```gherkin
# tests/features/undo_and_audit.feature
@M0 @story-ST-031
Feature: Undo and correction history
  Rule: Every change can be undone and is remembered

    Scenario: Undo a correction
      Given Ivy changed rally 5's winner
      When she undoes the change
      Then the score sheet is identical to the one before her change
      And her correction history lists both the change and the undo

    Scenario: Correction history shows what changed
      Given Ivy changed rally 5's ending from "winner" to "forced error"
      When she opens the correction history
      Then it shows rally 5, the field "ending", the old value "winner" and the new value "forced error"
```

```gherkin
# tests/features/corrections_replay.feature
@M0 @story-ST-032 @nfr-013
Feature: Corrections re-score later rallies
  Rule: A correction re-scores every later rally in one step

    Scenario: C-01 correction in the middle of a game
      Given a tagged game with 30 rallies
      When Ivy changes the winner of rally 5
      Then rallies 5 to 30 show scores recomputed from the corrected outcomes
      And the score sheet matches one built from scratch with the corrected outcomes

    Scenario: C-04 undo restores the exact sheet
      Given Ivy changed the winner of rally 5 of 30
      When she undoes that change
      Then the score sheet is identical to the one before the change

  Rule: Rallies are never deleted when a correction changes where a game ends

    @needs-verification
    Scenario: C-02 correction ends the game earlier
      Given a tagged game that side A won 12-10 after 24 rallies
      When Ivy changes rally 20 to "won by side A"
      Then the game shows as won by side A at rally 20
      And rallies 21 to 24 are listed as needing her decision, not deleted

    @needs-verification
    Scenario: C-03 correction un-ends a game
      Given game 1 was won by side A at rally 22 and game 2 has 5 tagged rallies
      When Ivy changes rally 22 to "won by side B"
      Then game 1 is no longer over
      And the first rallies of game 2 are listed as needing her decision, not deleted
```

### 7.5 Mid-game start and singles (provisional)

```gherkin
# tests/features/mid_game_start.feature
@M0 @story-ST-034 @needs-verification
Feature: Start the score sheet mid-game
  Rows SOD-13..SOD-15 from QD §2.2 [DOM G1, unverified].

  Scenario: Video begins part-way through a game
    Given Ivy declares the start as "4-6-2" with her side receiving
    When she tags the first rally as won by her side
    Then the score sheet shows "6-4-1" with her side serving

  Scenario: SOD-13 a legal mid-game start
    Given Ivy declares the start as "0-0-1"
    Then the declared start is accepted

  Scenario Outline: Impossible start refused
    Given Ivy declares a start score of "<start>"
    Then she is told why it is impossible and asked to correct it
    Examples:
      | id     | start  |
      | SOD-14 | 12-9-1 |
      | SOD-15 | 4-6-3  |
```

```gherkin
# tests/features/side_out_singles_provisional.feature
@M0 @story-ST-035 @needs-verification
Feature: Side-out singles scoring under the provisional preset
  Rows come from QD §2.2 SOS [DOM G1 R6, unverified]. Two-number call, server's score first.

  Background:
    Given the rules preset "PROVISIONAL-UNVERIFIED" with target 11 and margin 2

  Rule: Only the server scores; a lost rally passes the serve

    Scenario Outline: Score after one rally
      Given a singles game called "<before>" with player <srv> serving
      When the <winner> player wins the rally
      Then the score is called "<after>" with player <next> serving
      And the game is <state>
      Examples:
        | id     | before | srv | winner    | after | next | state          |
        | SOS-01 | 0-0    | A   | serving   | 1-0   | A    | not over       |
        | SOS-02 | 0-0    | A   | receiving | 0-0   | B    | not over       |
        | SOS-03 | 10-10  | A   | serving   | 11-10 | A    | not over       |
        | SOS-04 | 11-10  | A   | serving   | 12-10 | A    | won by A 12-10 |

    Scenario: SOS-05 rally after game over
      Given a singles game that player A has won 11-8
      When any rally is applied
      Then the rally is refused with a "game already over" message

  Rule: The server's court follows the parity of the server's score

    Scenario Outline: Serving court
      Given a singles game where the server's score is <score>
      When the server serves
      Then the serve is expected from the <court> court
      Examples:
        | score | court |
        | 0     | right |
        | 1     | left  |
        | 2     | right |
        | 3     | left  |
        | 4     | right |
        | 5     | left  |
        | 6     | right |
        | 7     | left  |
        | 8     | right |
        | 9     | left  |
        | 10    | right |
        | 11    | left  |
        | 12    | right |
```

### 7.6 Evidence deep link and upload expiry

```gherkin
# tests/features/evidence_deep_link.feature
@M0 @story-ST-037 @nfr-014 @nfr-055
Feature: Jump to the video moment
  Rule: Every rally row opens the video at that rally

    Scenario: Open a rally from the score sheet
      Given Ivy's score sheet lists rally 12 starting at 14:32
      When she opens rally 12's video link
      Then the video plays from 14:32

    Scenario: An old video link stops working
      Given Ivy copied a video link from her score sheet 20 minutes ago
      When the link is opened
      Then the video does not play
      And reopening rally 12 from the score sheet still works
```

```gherkin
# tests/features/abandoned_upload_expiry.feature
@M0 @story-ST-038 @nfr-066
Feature: Abandoned upload expiry
  Scenario: Upload never finished
    Given Ivy started an upload 25 hours ago and never finished it
    When she opens her matches list
    Then the partial upload is not listed
    And it cannot be resumed

  Scenario: Upload finished in time
    Given Ivy started an upload 23 hours ago and finished it 1 hour later
    When she opens her matches list
    Then the match is listed with its video
```

### 7.7 Stretch scenarios

```gherkin
# tests/features/correction_consequences.feature
@M0 @story-ST-033
Feature: Correction consequences
  Scenario: Correction affects later rallies
    Given Ivy is changing the winner of rally 8 of 20
    When she reviews the change before saving
    Then she is told the score of the next 12 rallies will change
```

```gherkin
# tests/features/gaps_and_resync.feature
@M0 @story-ST-036
Feature: Gaps in the video
  Scenario: Camera stopped for two rallies
    Given Ivy marks a gap after rally 9 and declares the resync score "7-5-1"
    When she views the score sheet
    Then a gap row appears after rally 9 and rally 10 starts at "7-5-1"
```

## 8. Quality gates

All Sprint 0 and Sprint 1 per-PR gates, plus:

| Gate | Threshold | Source |
|---|---|---|
| Mutation score on `sports/pickleball/rules` | ≥ 85% (first sprint as a gate) | NFR-072; QD-QG-S2 (judgment) |
| Golden tables | ≥ 46 provisional rows present and green, reported as `@needs-verification` | NFR-001; ADR 0009 |
| Golden replay | byte-identical sheet for every stored fixture match | NFR-075; QD-TR-04 |
| Optimistic tag feedback (E2E timing) | p95 ≤ 200 ms; any tap feedback ≤ 100 ms | NFR-012 (judgment targets) |
| Correction confirmed by server | p95 ≤ 1.5 s on a 3-game match | NFR-013 |
| Seek to playing video | p95 ≤ 1.5 s, throttled profile | NFR-014 |
| No dragging; keyboard-only journeys | 100% of tagging and score-sheet flows | NFR-030, NFR-034 [DPA/DESIGN-05] |
| E2E journey v1 | green on `main` for ≥ 3 consecutive nightly runs before the review (judgment; 5 from the R1 review) | QD-QG-S4 |

Baselines recorded but not yet gating: NFR-010 (API latency at 50 RPS), NFR-017 (tag to current results).

## 9. Definition of Done

Story and sprint levels as in `docs/process/definition-of-done.md`. Sprint 2 adds:

- [ ] Every score sheet in the demo shows the "unofficial scoring" label.
- [ ] Rule-dependent scenarios are reported separately and counted toward no Must FR (QD-QG-P5).
- [ ] The pickleball-domain-coach has reviewed every rule-related scenario and PR (working-agreement §6).
- [ ] The traceability matrix lists the feature files for FR-024, FR-027, FR-042, FR-046, FR-048..FR-053, FR-055.
- [ ] Sprint 3 stories meet the DoR, including coach-reviewed metric entries AN-01..AN-07.
- [ ] Retro 1 action items reviewed first.

## 10. Risks for this sprint

| Risk | Signal | Response |
|---|---|---|
| OQ-01 still open | No rule numbers by D5 | Ship unofficial (FR-055); remind PO that Sprint 3 planning is the last useful date for official scoring in R1 |
| Correction replay too slow on long matches | IT-02-08 p95 > 1.5 s | Replay only from the changed game onward; snapshot per game (judgment); PE design review |
| Quick Tag effort too high (NFR-036 ≤ 5 s per rally) | Internal timing in E2E-02-02 | Principal-designer adjusts the control bar before the Sprint 5 usability test |
| Responsible-player side rule wrong for some endings | Coach review | Coach decides; BA updates FR-050 note; QA changes the test with an ADR note |

## 11. Dependencies

- Sprint 1: rules engine core (ST-020, ST-021), resumable upload (ST-017), setup (ST-016).
- Design: `Match` aggregate design doc; Quick Tag and score-sheet flows.
- Human: OQ-01 (official scoring), OQ-06 (consented fixture footage), OQ-17 (reference profile for NFR-014).

## 12. Demo script (sprint review, 2026-11-13)

1. Open "Saturday doubles" (uploaded in setup). Tag rallies 1-3 by touch, showing the score after each tag and the live-region text.
2. Tag rallies 4-6 using keys only; press `?` to show the key map.
3. Open the score sheet: every rally with server, score before/after, winner, ending; point out "unofficial scoring (rules not yet verified)".
4. Narrow the window to 360 px; show the stacked rows.
5. Change rally 3's winner; show rallies 3-6 re-scored and "corrected by you"; open the correction history; undo and show the identical sheet.
6. Open the prepared 24-rally game (seeded fixture); change rally 20 to "won by side A"; show rallies 21-24 as "needs your decision".
7. Start a new match mid-game at "4-6-2" receiving; tag one rally won; show "6-4-1".
8. Click rally 12's link; the video plays from its start time. Show an expired link failing.
9. Show the test report: Ready scenarios, `@needs-verification` count (≥ 46 rows), mutation score, golden replay result, Locust baselines.
10. Ask the PO: OQ-01 status; accept the FR-050 R1 video behaviour (review-log RL-02); OQ-13 (spend ceiling for SPIKE-04 in Sprint 3).

## 13. Retrospective

- **Date:** 2026-11-13. **File:** `docs/retros/2026-11-13-sprint-02.md` from [`docs/retros/TEMPLATE.md`](../retros/TEMPLATE.md).
- **Format:** Mad/Sad/Glad. **Focus:** domain correctness and the coach verification flow; whether the ADR 0009 split held up.
- Review retro 1 action items first [EP/ENG-15].
