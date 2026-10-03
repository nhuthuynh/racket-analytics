# Sprint 1: Sign in, set up a match, upload safely; the scoring engine, test-first

- **Dates:** Mon 2026-10-19 → Fri 2026-10-30
- **Planning:** 2026-10-19 · **Sprint review:** 2026-10-30 · **Retrospective:** 2026-10-30
- **Retro file:** `docs/retros/2026-10-30-sprint-01.md` from [`docs/retros/TEMPLATE.md`](../retros/TEMPLATE.md). Format: **5 Whys** on the sprint's biggest miss. Focus area: **estimation accuracy and the writer/reviewer split** [EP/ENG-15].
- **Status:** Planned. **Preconditions** (checked at planning on 2026-10-19):
  - the PO has ratified ADR 0002 and ADR 0007 (OQ-02). If not, the EM re-plans and only the platform stories (ST-013, ST-014, ST-017, ST-018, ST-024) proceed;
  - the PO has ratified ADR 0009. If not, ST-020, ST-021 and ST-023 are replaced by stretch platform work and the rules engine waits for OQ-01;
  - Sprint 0 DoD is met, or its carry-over is re-sized here first.
- **Progress and status:** `docs/sprints/01/progress.md`, `docs/sprints/01/status.json` [EP/ENG-28].
- **Related ADRs:** 0002, 0007, 0008, 0009, 0010; ADR 0011 (tus server, from Sprint 0). Citation prefixes: working-agreement §0.

## 1. Sprint goal

- A player signs in with an emailed link (no password) and signs out leaving nothing behind on the device [DPA/DESIGN-06].
- A player reads the capture guide and sets up a doubles or singles match with nicknames, one question per page, with errors summarised at the top [DPA/DESIGN-12, DPA/DESIGN-13].
- A player uploads a multi-GB phone video that survives a dropped connection and a closed tab. Files that are not real videos, too large or too long are refused with a clear reason [AQS/STACK-06, AQS/SEC-02].
- The scoring engine is a pure, configurable function, built test-first. Its mechanics pass, and the provisional side-out doubles and fault tables run as `@needs-verification` (ADR 0009). The property suite and a nightly differential oracle are green.

**What we will demo:** §12.

**Not in this sprint:** tagging rallies and the score sheet (Sprint 2), singles and mid-game start (Sprint 2), abandoned-upload expiry (Sprint 2), age gate (Sprint 4), passkeys (backlog, judgment: FR-001 is satisfied by the magic link).

## 2. Capacity (ADR 0010)

Load factor 80%: 16 × 0.8 = **12.8 units per lane**.

| Lane | Committed | Stretch | Notes |
|---|---|---|---|
| BE | 12 | — | Stream 1: `players`, `video_ingest`. Stream 2: `sports/pickleball/rules`, `matches` |
| FE | 12 | 1 (ST-019) | Two streams: auth and onboarding; setup and upload |
| QA | 4 | — | Plus acceptance scenarios for every story, written first |
| SRE | 2 | — | Nightly jobs, SLIs, Mailpit |
| ML | 2 | — | Phone-file fixtures (R-05) |
| **Total** | **32** | 1 | |

## 3. Committed backlog

| Story | Title | FR / NFR | Owner (R) | Required reviewers | Size | Depends on |
|---|---|---|---|---|---|---|
| ST-013 | Passwordless sign-in with an email magic link | FR-001; NFR-032, NFR-055 (no token left in the URL), NFR-057 | BE (M) + FE (S) | QA, security-privacy-engineer, principal-designer | M+S | ST-005, ST-006 |
| ST-014 | Sign-out clears local data | FR-011; NFR-067 | FE | QA, security-privacy-engineer | S | ST-013 |
| ST-015 | First-run promise and capture guide | FR-004, FR-020; NFR-033, NFR-035 | FE | QA, principal-designer, pickleball-domain-coach (wording) | M | coach wording (Sprint 0 task) |
| ST-016 | Match setup flow with participants by nickname | FR-021, FR-005; NFR-028, NFR-031, NFR-034, NFR-037 | FE (L) + BE (S) | QA, principal-designer, principal-engineer (participant model) | L+S | ST-006 |
| ST-017 | Resumable upload: checksum and expiration extensions, resume on return | FR-022; NFR-016, NFR-026, NFR-042 (SLI emitted) | BE (M) + FE (M) | QA, security-privacy-engineer, principal-designer | M+M | ST-008, SPIKE-06 |
| ST-018 | Upload validation by content, size and duration | FR-023; NFR-053, NFR-054, NFR-060 | BE (M) + FE (S) | QA, security-privacy-engineer | M+S | ST-009, ST-025 (caps data) |
| ST-020 | Scoring engine core (a): `RulesConfig`, `GameState`, `apply`, `fold`, domain errors; side-out doubles mechanics; faults as "side lost the rally" | FR-040 (a), FR-041 (a), FR-044 (a); NFR-079 | BE | QA, principal-engineer, pickleball-domain-coach | L | ST-023 (tests first) |
| ST-021 | Match structure (a): best of 1 or 3, first server and end switch per game as explicit inputs, match over | FR-045 (a) | BE | QA, principal-engineer, pickleball-domain-coach | S | ST-020 |
| ST-022 | Property suite P1-P8, nightly differential oracle P9, mutation baseline | NFR-002, NFR-072 | QA | principal-engineer, BE peer | M | ST-020 |
| ST-023 | Golden scoring tables as executable scenarios (SOD-01..12 and SOD-16, F-01..06, M-01..M-08), written before ST-020 | NFR-001 (provisional rows) | QA | pickleball-domain-coach, principal-engineer | M | — |
| ST-024 | Nightly quality jobs and upload SLIs | NFR-002 (nightly job), NFR-042 (SLI dashboard), NFR-072 (mutation job) | SRE | QA, principal-engineer | M | ST-022 |
| ST-025 | Phone-file fixture set and upload-cap measurement (R-05) | NFR-025; FR-023 (caps confirmed by R-05) | ML | QA, security-privacy-engineer | M | OQ-06 for any footage with people; otherwise empty-court recordings |
| SPIKE-06 | Upload behaviour on phone browsers: tus client, background tab, 8 GB file | FR-022; OQ-18 | FE | principal-engineer, principal-designer | S (3 days) | ST-008 |

**Stretch:** ST-019 Footage quality report, R1 facts (FR-025) — FE, S.

### 3.1 Acceptance notes per story

- **ST-013:** the link is single-use and expires after 15 min (judgment, FR-001). After the exchange, the token is removed from the address bar [AQS/SEC-05 14.2.1]. The session cookie is `HttpOnly`, `Secure` and `SameSite` (judgment; security-privacy-engineer to confirm against ASVS V3/V7 in the threat model). Sign-in requests are rate-limited (NFR-023 partial). Authentication attempts are logged with when, where, who and what, in UTC, without the email address in plain text (NFR-057, NFR-069) [AQS/SEC-04]. Mailpit receives links in dev (ADR 0008). The dev identity provider from ST-006 stays dev/test-only.
- **ST-014:** sign-out clears client storage and service-worker caches for authenticated data; the service worker never caches media (FR-011) [AQS/SEC-05 14.3.1-14.3.3].
- **ST-015:** first-run screen per FR-004; capture guide with ≤ 6 illustrated items, alt text, and a captioned video with captions on by default; the checklist is the video's text alternative [DPA/DESIGN-08, DPA/DESIGN-09]. The coach signs off the wording. The 60 fps help text is reviewed by the coach (judgment).
- **ST-016:** pages in the order of FR-021. Scoring system page: "Side-out scoring" selectable; "Rally scoring (provisional)" shown but not selectable, with the reason "available once the rules are verified" (FR-043). Participants per FR-005: slots A1, A2, B1, B2 (doubles) or A1, B1 (singles), exactly one "me", helper text saying not to enter contact details. "Check your answers" page with "Change" links. Error summary with links to the fields [DPA/DESIGN-13]. Tap targets ≥ 24×24 CSS px, primary controls ≥ 48 dp [DPA/DESIGN-02, DPA/DESIGN-10].
- **ST-017:** tus checksum and expiration extensions [AQS/STACK-06]. Client shows % done, MB of total, a plain-language state and a time estimate after 10 s of throughput (FR-022). Copy never promises an upload continues after the tab closes (OQ-18 recommendation). Chunk size adapts between 5 and 50 MB (NFR-016).
- **ST-018:** container and codec are checked from content (magic bytes plus probe), never from the extension. Caps are provisional 10 GB and 150 min (conflict K12) until ST-025's measurement confirms them. The size cap is enforced from `Upload-Length` at creation, before any bytes are stored. Rejections use the error-summary pattern with human units. No job starts for a rejected file (NFR-060).
- **ST-020:** the engine is a pure function `(GameState, RallyOutcome, RulesConfig) → GameState | DomainError`. It has no I/O, clock or randomness (FR-040) [EP/ENG-17]. Every value QD §2.2 marks unverified is a `RulesConfig` field (NFR-079). The only shipped preset is `PROVISIONAL-UNVERIFIED` (ADR 0009). Ready acceptance criteria are stated against explicit config values (§7.7). The provisional tables (§7.8, §7.9) run tagged `@needs-verification` and do not count toward FR-041/FR-044 DoD (QD-QG-P5).
- **ST-021:** `Match` holds `Game` entities; who serves first and whether ends switched are explicit inputs per game (FR-045). A rally after the match is decided returns `DomainError.MatchOver`.
- **ST-022:** P1-P8 from QD §2.3 with ≥ 1,000 random sequences per scoring system per CI run (NFR-002a). P9: the QA agent writes an independent engine in `backend/tests/oracle/` without reading the production engine's code (writer/reviewer split [DPA/AI-08]); the nightly job compares 100,000 sequences (NFR-002b). Mutation baseline on `sports/pickleball/rules` (target ≥ 85% from Sprint 2, NFR-072).
- **ST-023:** the rows SOD-01..SOD-12, SOD-16, F-01..F-06 and M-01..M-08 from QD §2.2 (SOD-13..15 come in Sprint 2 with ST-041), as `Scenario Outline` tables with the row ID in each example. Each row is tagged `@needs-verification` until the coach adds `@rule-<number>` (QD-TR-07).
- **ST-024:** nightly workflow runs the oracle and mutation jobs and posts results to `docs/sprints/01/status.json`. Upload SLI (NFR-042) and API availability SLI (NFR-041) are emitted as OpenTelemetry metrics [AQS/OPS-07]; dashboards exist, alerts come in Sprint 5.
- **ST-025:** recordings from ≥ 5 phone models (empty court or consenting team members only, OQ-06), including at least one VFR file. Measures file size per minute at 1080p60 to confirm or change the 10 GB / 150 min caps (R-05), recorded as a dated note on the FR-023 conflict K12 and as a fixture manifest.
- **SPIKE-06:** completion rate of an 8 GB tus upload on current iOS Safari and Android Chrome with the screen locked, the tab backgrounded and the tab closed and reopened. Output: ADR with the data, informing OQ-18 (native wrapper or not).

## 4. Task breakdown per role agent

| Agent | Tasks | Due | Done-check |
|---|---|---|---|
| engineering-manager | Check preconditions at planning; brief agents; run the loop; DORA and PR metrics; retro | D1, daily, D10 | `status.json` complete with units |
| product-manager | Chase OQ-01, OQ-06, OQ-12, OQ-17; confirm R1 exit criteria wording for Sprint 5 | D3 | Answers logged as ADR notes |
| business-analyst | Write Sprint 2 stories (ST-026..ST-041) with Gherkin; update traceability with test files | D8 | Sprint 2 stories meet DoR |
| principal-engineer | `Match` aggregate design doc (games, rallies, outcome inputs, corrections, score as projection) reviewed as a PR before Sprint 2 [DPA/DESIGN-15]; review ST-016 participant model and ST-020 | D6 | Design doc approved |
| principal-designer | Quick Tag flow, keyboard map and score-sheet table with all states (Sprint 2 DoR) [DPA/DESIGN-05, DPA/DESIGN-07]; review ST-013..ST-018 UI | D7 | WCAG 2.2 AA and HAX checklists done |
| security-privacy-engineer | Threat-model notes for magic-link auth and upload validation attached before ST-013/ST-018 start; review security stories; confirm psycopg/FFmpeg licence interpretation (ADR 0008) | D2, ongoing | Notes attached; reviews done |
| pickleball-domain-coach | Capture-guide wording sign-off; review ST-023 tables; fill `docs/domain/rules-verified.md` the day OQ-01 is answered; draft the score-call format note for FR-048 | D3, on OQ-01 | Each verified row has edition and rule number |
| senior-backend-engineer | ST-013, ST-016 (API), ST-017 (server), ST-018 (server), ST-020, ST-021 | D3-D9 | Scenarios green with evidence |
| senior-frontend-engineer | SPIKE-06 (D1-D3), ST-013 (UI), ST-014, ST-015, ST-016, ST-017 (UI), ST-018 (UI); ST-019 stretch | D3-D9 | Playwright and axe green |
| senior-qa-engineer | ST-023 (D1-D2, before ST-020), ST-022, acceptance scenarios for every story before implementation, test report | D2, D8, D10 | Report lists `@needs-verification` separately |
| sre-devops-engineer | ST-024; Mailpit service in Compose | D6 | Nightly run visible |
| senior-ml-cv-engineer | ST-025; finish SPIKE-01 ADR if it slipped | D7 | Fixture manifest; R-05 note |

## 5. TDD plan (negative case first) [EP/ENG-18; testing-strategy §3]

| Domain object / unit | Context | First tests, in order |
|---|---|---|
| `RulesConfig` | sports/pickleball | 1. `points_to_win < 1` rejected; 2. `win_by < 1` rejected; 3. unknown `scoring_system` rejected; 4. a valid config is immutable (frozen) |
| `GameState` | sports/pickleball | 1. server number outside {1, 2} in doubles rejected; 2. a state already meeting the game-over condition cannot be constructed as "in play"; 3. call formatting is a separate pure function (FR-048 comes in Sprint 2) |
| `apply(state, outcome, config)` | sports/pickleball | 1. any rally on a finished game → `DomainError.GameOver` (SOD-12); 2. receiving side wins at server 1 → same side, server 2, no point; 3. receiving side wins at server 2 → side-out, other side at server 1; 4. serving side wins → +1 to serving side; 5. first-service exception from config (start at server 2); 6. game ends at the first rally meeting target and margin (P5); 7. `replay` outcome is identity (SOD-16, P8) |
| `Fault` handling | sports/pickleball | 1. every fault subtype produces the same state as "faulting side lost the rally" (F-06, P7); 2. a fault by the serving side at server 1 → server 2 |
| `fold(outcomes)` | sports/pickleball | 1. empty list → initial state; 2. fold equals sequential `apply`; 3. prefix-then-suffix equals whole (P6) |
| `MatchState` | matches | 1. rally after the match is decided → `DomainError.MatchOver`; 2. best of 3 is decided after 2 games won by one side; 3. first server of game 2 is taken from input, never inferred |
| `Participants` | matches | 1. doubles with 3 nicknames → error naming the side; 2. two "me" markers → error; 3. a nickname that looks like an email address → warning flag (judgment) |
| `MagicLinkToken` | players | 1. used token rejected; 2. token older than 15 min rejected (injected clock, QD-TR-02); 3. token bound to one email |
| `UploadPolicy` | video_ingest | 1. `Upload-Length` > cap → rejected before storage; 2. non-video magic bytes → `NotAVideo`; 3. MP4/MOV with H.264/HEVC accepted; 4. duration > cap (from probe) → rejected |
| `UploadSession` (extensions) | video_ingest | 1. checksum mismatch → chunk rejected, offset unchanged; 2. expired session → refuses PATCH; 3. `Upload-Expires` is set at creation |

Front-end (Vitest): setup-flow state machine (1. Continue without an answer → error state; 2. Back keeps answers; 3. "Change" returns to the check page), upload estimate (1. no estimate before 10 s; 2. estimate updates).

## 6. Integration tests

| ID | Boundary | Test | Story |
|---|---|---|---|
| IT-01-01 | API ↔ Mailpit ↔ DB | Request link → email arrives → open link → session created; reusing the link fails | ST-013 |
| IT-01-02 | API | Sign-in rate limit returns 429 with a retry time | ST-013 |
| IT-01-03 | API ↔ logs | Auth success and failure log lines have UTC time, request ID and pseudonymous user ID, and no email address | ST-013 |
| IT-01-04 | API | Every authenticated JSON response has `Cache-Control: no-store` | ST-014 |
| IT-01-05 | API ↔ DB | Participants: invalid slot counts rejected with field errors; valid doubles and singles stored | ST-016 |
| IT-01-06 | API ↔ store | Checksum extension: a corrupted chunk is rejected and the offset is unchanged | ST-017 |
| IT-01-07 | API ↔ store | Expiration: `Upload-Expires` header present; PATCH after expiry refused | ST-017 |
| IT-01-08 | API ↔ store | Client restart: HEAD then PATCH resumes; final sha256 equals the source | ST-017 |
| IT-01-09 | API ↔ store ↔ worker | Upload-validation suite: PDF renamed `.mp4`, executable with a video extension, `Upload-Length` 12 GB, a 4-hour fixture header → all refused; no object kept; no job created | ST-018 |
| IT-01-10 | Worker sandbox | Probe of a crafted malformed container ends with `failed` within its time limit and no network access | ST-018 |
| IT-01-11 | BOLA matrix | New routes (upload sessions, participants) added to the matrix; inventory diff empty | ST-016, ST-017 |
| IT-01-12 | Static check | No rule constants or court dimensions as literals outside `RulesConfig`/`CourtModel` (NFR-079) | ST-020 |
| IT-01-13 | Static check | `sports/pickleball/rules` imports nothing from `platform`, DB, HTTP or time modules (QD-TR-01) | ST-020 |

**E2E (Playwright):** E2E-01-01 sign in by link → first run → capture guide → set up doubles match → upload fixture → see facts. E2E-01-02 upload with the network cut for 2 minutes at about 40% → resumes. E2E-01-03 keyboard-only setup flow (NFR-034, NFR-030). Each page runs axe. The viewport matrix 320/360/768/1280 runs on setup pages (NFR-034).

## 7. Gherkin scenarios

### 7.1 Sign-in and sign-out

```gherkin
# tests/features/sign_in.feature
@M0 @story-ST-013 @nfr-032
Feature: Sign in without a memorised password
  Rule: Authentication never requires a cognitive function test

    Scenario: Sign up with an email sign-in link
      Given Ivy has no account
      When she requests a sign-in link and opens it within 15 minutes
      Then she is signed in and sees "Record your first match"
      And the address bar no longer contains the sign-in code

    Scenario Outline: A link that can no longer be used
      Given Ivy's sign-in link <condition>
      When she opens it
      Then she sees "This link has expired"
      And she is offered a new link
      Examples:
        | condition               |
        | is 16 minutes old       |
        | was already used        |

    Scenario: Too many link requests
      Given Ivy has requested 5 sign-in links in the last 10 minutes
      When she requests another one
      Then she is told when she can request a new link
```

```gherkin
# tests/features/sign_out.feature
@M0 @story-ST-014 @nfr-067
Feature: Signing out leaves nothing behind
  Scenario: Shared device
    Given Ivy viewed her match on a shared tablet
    When she signs out and the next person opens the app offline
    Then none of Ivy's matches, facts or videos can be seen
```

### 7.2 First run and capture guide

```gherkin
# tests/features/first_run_and_capture_guide.feature
@M0 @story-ST-015 @nfr-033
Feature: First run and capture guide
  Rule: The app says plainly what it can and cannot do

    Scenario: New user sees capabilities and limits
      Given Ivy has just created her account
      When the app opens for the first time
      Then she sees what the app does and what it cannot do, in plain words
      And she can continue to the capture guide

  Rule: Every filming instruction is available as text

    Scenario: Read the guide without playing the video
      Given Ivy opens the capture guide
      When she reads it without playing the video
      Then every setup instruction is available as text with an illustration
      And there are no more than 6 instructions

    Scenario: Watch the guide video
      Given Ivy opens the capture guide
      When she plays the guide video
      Then captions are shown by default
```

### 7.3 Match setup

```gherkin
# tests/features/match_setup.feature
@M0 @story-ST-016 @nfr-037
Feature: Match setup
  Rule: One question per page, with errors summarised at the top

    Scenario: Missing answer
      Given Ivy is on the "format" question
      When she continues without choosing a format
      Then she sees "There is a problem" at the top with a link to the format question
      And the page title starts with "Error:"

    Scenario: Review before upload
      Given Ivy has answered every setup question
      When she reaches "Check your answers"
      Then each answer is listed with a "Change" link

  Rule: Participants are nicknames assigned by the user

    Scenario: Doubles match setup
      Given Ivy is setting up a doubles match
      When she enters four nicknames, two per side, and marks herself as "me"
      Then the match shows two sides of two players with her marked as "me"

    Scenario Outline: Wrong participants for the format
      Given Ivy is setting up a <format> match
      When she enters <entered>
      Then she sees an error summary saying "<message>"
      Examples:
        | format  | entered                             | message                            |
        | doubles | three nicknames                     | Each side needs two players        |
        | singles | three nicknames                     | Each side needs one player         |
        | doubles | four nicknames with two marked "me" | Choose one player as "me"          |

  Rule: Only verified scoring systems can be chosen

    Scenario: Rally scoring is not yet available
      Given Ivy is on the "scoring system" question
      Then she can choose side-out scoring
      And rally scoring is shown as provisional and cannot be chosen
      And she is told it becomes available once the rules are verified
```

### 7.4 Resumable upload

```gherkin
# tests/features/resumable_upload.feature
@M0 @story-ST-017 @nfr-026
Feature: Resumable upload
  Rule: An interrupted upload continues from where the server stopped

    Scenario: Connection drops mid-upload
      Given Ivy is uploading a 3 GB video and 40% has been sent
      When her connection drops for 2 minutes and returns
      Then the upload continues from at least 40%
      And she sees the state change from "Paused: waiting for connection" to "Uploading"

    Scenario: Return after closing the tab
      Given Ivy closed the tab when her upload was 64% done
      When she opens the app again within 24 hours
      Then she is offered to resume from 64%

    Scenario: A damaged chunk is not kept
      Given Ivy's upload is at 40%
      When a chunk arrives that does not match its checksum
      Then the chunk is refused
      And the upload is still at 40%

  Rule: Progress is honest

    Scenario: Time estimate appears only after measuring
      Given Ivy has just started an upload
      When less than 10 seconds of transfer have been measured
      Then she sees the percentage and megabytes sent but no time estimate
```

### 7.5 Upload validation

```gherkin
# tests/features/upload_validation.feature
@M0 @story-ST-018 @nfr-053
Feature: Upload validation
  Rule: Only real video files within the caps are accepted

    Scenario Outline: Reject invalid files
      Given Ivy selects <file>
      When she starts the upload
      Then she sees "There is a problem" with "<message>"
      And no match video is stored from that file
      Examples:
        | file                                  | message                                      |
        | a PDF renamed to match.mp4            | This file is not a video we can read         |
        | a program renamed to match.mov        | This file is not a video we can read         |
        | a 12 GB video                         | Videos must be 10 GB or smaller              |
        | a 4-hour video                        | Videos must be 2 hours 30 minutes or shorter |

    Scenario: A valid phone video is accepted
      Given Ivy selects a 1080p 60 fps MP4 recorded on a phone
      When the upload completes
      Then the match shows the status "Video received"
```

### 7.6 Footage quality report (stretch, ST-019)

```gherkin
# tests/features/footage_quality_report.feature
@M0 @story-ST-019
Feature: Footage quality report
  Rule: The report explains consequences and never blocks

    Scenario: 30 fps video
      Given Ivy uploaded a 1080p video recorded at 30 fps
      When the quality report is shown
      Then it says which results may be less accurate and which are unaffected
      And she can continue to tag the match
```

### 7.7 Scoring engine mechanics (Ready; stated against explicit configuration, ADR 0009)

```gherkin
# tests/features/scoring_engine_mechanics.feature
@M0 @story-ST-020 @nfr-079
Feature: Configurable scoring engine
  The engine applies only the values in its configuration; no rule value is hard-coded.

  Rule: A game ends at the first rally that reaches the configured target with the configured margin

    Scenario Outline: Game end follows the configuration
      Given a game configured with target <target> and margin <margin> where only the serving side scores
      And side A is serving with the score <a> to <b>
      When side A wins the rally
      Then the game is <state>
      Examples:
        | target | margin | a  | b  | state             |
        | 11     | 2      | 10 | 8  | won by side A     |
        | 11     | 2      | 10 | 10 | not over          |
        | 15     | 2      | 14 | 12 | won by side A     |
        | 11     | 1      | 10 | 10 | won by side A     |

  Rule: A finished game accepts no more rallies

    Scenario: Rally after the game is over
      Given a game has ended
      When another rally is applied to that game
      Then the rally is refused with a "game already over" message

  Rule: Invalid configurations are refused

    Scenario Outline: Configuration out of range
      Given a game configuration with <field> set to <value>
      When the configuration is loaded
      Then it is refused with a message naming <field>
      Examples:
        | field  | value |
        | target | 0     |
        | margin | 0     |

  Rule: Scores are reproducible from the recorded rallies

    Scenario: Replaying the same rallies gives the same score sheet
      Given a game with 30 recorded rally outcomes
      When the score sheet is rebuilt from those outcomes
      Then it is identical to the score sheet computed rally by rally

    Scenario: A replayed rally changes nothing
      Given a game at 5-5 with side A serving at server 1
      When a rally is recorded as a replay
      Then the score is still 5-5 with side A serving at server 1

  Rule: A match keeps the rules version it was scored under

    Scenario: A newer rules preset ships
      Given Ivy's match was scored under preset "PROVISIONAL-UNVERIFIED"
      When a newer rules preset becomes available
      Then her match still uses "PROVISIONAL-UNVERIFIED" and shows the same scores
```

### 7.8 Provisional side-out doubles table (`@needs-verification`, QD §2.2)

```gherkin
# tests/features/side_out_doubles_provisional.feature
@M0 @story-ST-023 @needs-verification
Feature: Side-out doubles scoring under the provisional preset
  Rows come from QD §2.2 and rest on unverified rules [DOM G1 R2, R6].
  They do not count toward FR-041's Definition of Done until each row carries @rule-<number>.

  Background:
    Given the rules preset "PROVISIONAL-UNVERIFIED" with target 11, margin 2 and the first-service exception

  Rule: Only the serving side scores; a lost serve passes to the partner, then to the other side

    Scenario Outline: Score after one rally
      Given a doubles game called "<before>" with side <srv> serving
      When the <winner> side wins the rally
      Then the score is called "<after>" with side <next> serving
      Examples:
        | id     | before | srv | winner    | after  | next |
        | SOD-01 | 0-0-2  | A   | serving   | 1-0-2  | A    |
        | SOD-02 | 0-0-2  | A   | receiving | 0-0-1  | B    |
        | SOD-03 | 3-5-1  | A   | receiving | 3-5-2  | A    |
        | SOD-04 | 3-5-2  | A   | receiving | 5-3-1  | B    |
        | SOD-05 | 7-4-1  | A   | serving   | 8-4-1  | A    |
        | SOD-08 | 10-10-1| A   | serving   | 11-10-1| A    |
        | SOD-10 | 10-9-2 | A   | receiving | 9-10-1 | B    |
        | SOD-16 | 5-5-1  | A   | replay    | 5-5-1  | A    |

  Rule: A game is won at the target score by the margin

    Scenario Outline: Game end
      Given a doubles game called "<before>" with side A serving
      When the <winner> side wins the rally
      Then the game is <state>
      Examples:
        | id     | before  | winner    | state          |
        | SOD-07 | 10-8-1  | serving   | won by A 11-8  |
        | SOD-09 | 11-10-2 | serving   | won by A 12-10 |
        | SOD-11 | 21-20-1 | serving   | won by A 22-20 |

  Rule: Serving positions follow the score

    Scenario: Server changes court after scoring
      Given a doubles game called "7-4-1" with side A serving
      When the serving side wins the rally
      Then the same server serves again from the other court
      And the receiving players keep their positions

  Rule: A finished game refuses rallies

    Scenario: SOD-12 rally after game over
      Given a doubles game that side A has won 11-8
      When any rally is applied
      Then the rally is refused with a "game already over" message
```

Rows SOD-13..SOD-15 (declared starts) belong to FR-046 and run in Sprint 2 (ST-034).

### 7.9 Provisional fault table (`@needs-verification`)

```gherkin
# tests/features/faults_provisional.feature
@M0 @story-ST-023 @needs-verification
Feature: Faults end the rally against the faulting side (provisional preset)
  Rows come from QD §2.2 F-01..F-06 [DOM G1 R4-R6, unverified].

  Background:
    Given the rules preset "PROVISIONAL-UNVERIFIED"

  Rule: A fault is scored as the faulting side losing the rally

    Scenario Outline: Fault outcome
      Given a doubles game called "<before>" with side A serving
      When the <side> side commits a <fault> fault
      Then the score is called "<after>" with side <next> serving
      Examples:
        | id   | before | side      | fault                    | after | next |
        | F-01 | 4-2-1  | serving   | serve                    | 4-2-2 | A    |
        | F-02 | 4-2-2  | serving   | foot fault on serve      | 2-4-1 | B    |
        | F-03 | 4-2-1  | receiving | two-bounce               | 5-2-1 | A    |
        | F-04 | 4-2-1  | serving   | two-bounce               | 4-2-2 | A    |
        | F-05 | 4-2-1  | receiving | NVZ                      | 5-2-1 | A    |

  Rule: The fault subtype never changes the score

    Scenario Outline: F-06 same outcome for every fault subtype
      Given a doubles game called "4-2-1" with side A serving
      When the receiving side commits a <fault> fault
      Then the score is called "5-2-1" with side A serving
      Examples:
        | fault      |
        | two-bounce |
        | NVZ        |
        | other      |
```

### 7.10 Match structure

```gherkin
# tests/features/match_structure.feature
@M0 @story-ST-021
Feature: Match structure
  Rows M-01..M-08 from QD §2.2 (enumerated in review-log RL-04). They state the match format,
  first server and end switch as explicit inputs and make no rulebook claim (ADR 0009 part a).

  Rule: A match ends when one side has won the majority of its games

    Scenario Outline: Match result
      Given a best-of-<n> match in which the games were won by <games>
      Then the match is <result>
      Examples:
        | id   | n | games   | result              |
        | M-01 | 1 | B       | won by side B, 1-0  |
        | M-02 | 3 | A, A    | won by side A, 2-0  |
        | M-03 | 3 | A, B    | not over; game 3 open |
        | M-04 | 3 | A, B, B | won by side B, 2-1  |

    Scenario Outline: Rallies after the match is decided are refused
      Given a best-of-<n> match in which the games were won by <games>
      When a rally is recorded for game <game>
      Then the rally is refused with a "match is over" message
      Examples:
        | id   | n | games | game |
        | M-05 | 3 | A, A  | 3    |
        | M-08 | 1 | B     | 2    |

  Rule: Who serves first and whether ends switched are recorded, never guessed

    Scenario: M-06 and M-07 second game set-up
      Given game 1 of Ivy's match has ended
      When she starts game 2 and states that side B serves first and ends were switched
      Then game 2 starts with side B serving
      And game 2 is recorded as played from switched ends
```

## 8. Quality gates

All Sprint 0 per-PR gates (sprint-00.md §8), plus:

| Gate | Threshold | Source |
|---|---|---|
| Rules engine and aggregate coverage on changed lines | ≥ 95% line, ≥ 90% branch | testing-strategy §8 (judgment); NFR-071 |
| Property suite P1-P8 | ≥ 1,000 sequences per scoring system per run, 0 failures | NFR-002a; QD-QG-P3 |
| Domain unit suite time | < 10 s | NFR-073 |
| Upload-validation and upload-resume regression suites | 100% pass | testing-strategy §5; NFR-026, NFR-053 |
| BOLA inventory diff | empty | NFR-051 |
| `@needs-verification` scenarios | listed separately; never counted toward a Must FR | QD-QG-P5; ADR 0009 |
| Keyboard-only journeys and target-size check on new screens | 100%; 0 targets below 24×24 CSS px | NFR-028, NFR-034 |

Per sprint: nightly differential oracle 0 disagreements (QD-QG-S1); mutation baseline recorded (target ≥ 85% gated from Sprint 2, NFR-072); manual screen-reader pass on the new screens (NFR-027b) [DPA/DESIGN-14]; flaky rate < 1% (NFR-074).

## 9. Definition of Done

Story and sprint levels as in `docs/process/definition-of-done.md`. Sprint 1 adds:

- [ ] Security stories ST-013, ST-017 and ST-018 carry the threat-model notes and a security-privacy-engineer review with no open Blocking findings.
- [ ] The rules engine has no rule literal outside `RulesConfig` (IT-01-12) and no I/O import (IT-01-13).
- [ ] Sprint test report shows the provisional table counts as `@needs-verification`, separately from Ready scenarios.
- [ ] SPIKE-06 ADR and the R-05 measurement note are written.
- [ ] Sprint 2 stories meet the DoR, including the approved `Match` aggregate design doc.
- [ ] Retro 0 action items reviewed first in retro 1.

## 10. Risks for this sprint

| Risk | Signal | Response |
|---|---|---|
| OQ-02 or ADR 0009 not ratified on 2026-10-16 | Planning precondition fails | Platform stories only; rules engine waits; escalate with options |
| Magic-link email deliverability in production unknown | — | Not needed until beta; provider choice is a Sprint 4 ADR (judgment) |
| iOS Safari kills background uploads | SPIKE-06 data | "Resume on return" copy stays; native-wrapper question to PO (OQ-18) |
| Provisional rows later differ from the rulebook | Coach verification | Only config and table rows change (ADR 0009); QA edits rows with an ADR note |
| FE lane overloaded (12 of 12.8) | Burn-down at D6 | Drop ST-019 stretch first, then move ST-015's video part to Sprint 2 |

## 11. Dependencies

- Sprint 0: ST-005..ST-010 merged (API skeleton, ownership seam, queue, tus core, probe, PWA shell).
- Human: ADR 0002/0007/0009 ratification; OQ-06 for any footage with people (ST-025); OQ-17 for the browser matrix.
- Coach: capture-guide wording before ST-015 is merged.

## 12. Demo script (sprint review, 2026-10-30)

1. On a phone browser, request a sign-in link; open it from Mailpit; show the clean address bar and "Record your first match".
2. Walk the first-run screen and the capture guide with the video muted; show that every instruction is readable as text.
3. Set up a doubles match: skip the format question to show the error summary; enter nicknames; show the rally-scoring option disabled with its reason; show "Check your answers".
4. Upload a ~3 GB phone fixture; turn on airplane mode at ~40% for 2 minutes; show "Paused: waiting for connection", then the resume. Close the tab, reopen, show "Resume from 64%" (or the current %).
5. Try a PDF renamed `match.mp4` → error summary; try a 4-hour file → duration message.
6. Run `pytest -m "scoring"` live: show the mechanics scenarios green, and the provisional SOD/F rows green but reported under `@needs-verification`.
7. Show the nightly differential-oracle result (100,000 sequences, 0 disagreements) and the mutation baseline.
8. Sign out, go offline, reopen: nothing of Ivy's is visible.
9. Show SPIKE-06 and SPIKE-01 results; ask the PO for OQ-12 and OQ-18.

## 13. Retrospective

- **Date:** 2026-10-30. **File:** `docs/retros/2026-10-30-sprint-01.md` from [`docs/retros/TEMPLATE.md`](../retros/TEMPLATE.md).
- **Format:** 5 Whys on the largest miss. **Focus:** estimation accuracy (planned vs completed units, ADR 0010) and how well the QA-writes-tests-first split worked.
- Review retro 0 action items first [EP/ENG-15].

## 14. Story specifications and Definition of Ready (business-analyst, 2026-10-03)

This section adds what `docs/process/definition-of-ready.md` asks for beyond §3, §3.1 and §7:

- a value statement, priority and milestone;
- the bounded context and aggregates;
- files and interfaces;
- out of scope;
- the end-to-end verification step [DPA/AI-08];
- the measurable NFRs;
- the Gherkin missing from §7 (§14.3);
- the ADR 0009 (a)/(b) split for the rules stories (§14.2);
- the DoR check (§14.5).

§3 to §13 are unchanged. Where a story here and §3.1 disagree, §3.1 wins, and the BA raises the difference with the EM.

- **Feature files:** the `.feature` files live at `tests/features/` (repository root; `backend/pyproject.toml` sets `bdd_features_base_dir = "../tests/features"`). Their step modules are in `backend/tests/features/`, and browser journeys are in `web/e2e/`. The traceability matrix §6 is updated to these paths.
- **Priority:** from the FR's MoSCoW priority in `functional-requirements.md`. The product-manager confirms it at Sprint 1 planning (DoR "PM-assigned priority").
- **Milestone:** M0 for every story unless noted (spec §7).
- **Design:** `docs/design/flows-sprint-01.md` (screen IDs A-, F-, G-, M-, Q-, U-), `docs/design/tokens.md` and `docs/design/component-accessibility-checklist.md`.

### 14.1 Story cards

#### ST-013 Passwordless sign-in with an email magic link
- **Value:** As a player, I want to sign in with a link sent to my email, so that I never have to remember a password courtside.
- **Priority / milestone:** Must (FR-001) / M0.
- **FR / NFR:**
  - FR-001;
  - NFR-032: 0 cognitive-function tests (E2E + review);
  - NFR-055: no token left in the URL after exchange (I);
  - NFR-057: auth success and failure logged with UTC time, request ID and pseudonymous user ID, and 0 plain-text email addresses (I, IT-01-03);
  - NFR-023 partial: link requests rate-limited, 429 with a retry time (IT-01-02).
- **Context / aggregates:** Identity & Players (`players`), aggregate `Account`; value object `MagicLinkToken` (§5).
- **Files / interfaces:**
  - `backend/src/racket/players/` (domain: `MagicLinkToken`, `Account`; application: request-link and exchange-link commands; adapter: mailer to Mailpit in dev);
  - `POST /auth/links` → 202 always (D-4);
  - `POST /auth/exchange` → sets the session cookie;
  - `POST /auth/sign-out`;
  - `web/app/(auth)/` screens A-01..A-04;
  - `tests/features/sign_in.feature`.
- **Out of scope:** passkeys (backlog); the production email provider (Sprint 4 ADR); the age gate (Sprint 4); account deletion (Sprint 3).
- **E2E verification:** E2E-01-01, first step. Request a link, open it from Mailpit, and check that the address bar has no token and the page shows "Record your first match".
- **Gherkin:** §7.1 and §14.3.1.

#### ST-014 Sign-out clears local data
- **Value:** As a player who uses a shared tablet, I want signing out to leave nothing of mine on the device, so that the next person cannot see my matches.
- **Priority / milestone:** Must (FR-011) / M0.
- **FR / NFR:**
  - FR-011;
  - NFR-067: 0 authenticated responses or media in client storage or service-worker caches after sign-out; `Cache-Control: no-store` on 100% of authenticated JSON (IT-01-04, E2E).
- **Context:** Identity & Players (session) and the web client.
- **Files / interfaces:** `web/` service worker and sign-out handler; `POST /auth/sign-out`; screen A-05 and the "upload will stop" confirmation; `tests/features/sign_out.feature`.
- **Out of scope:** remote sign-out of other devices (backlog, judgment).
- **E2E verification:** demo step 8. Sign out, go offline, reopen, and check that nothing of Ivy's is visible.
- **Gherkin:** §7.1 and §14.3.2.

#### ST-015 First-run promise and capture guide
- **Value:** As a new player, I want to know what the app can and cannot do and how to film, so that my first video is usable and my expectations are right.
- **Priority / milestone:** FR-004 Should, FR-020 Must / M0.
- **FR / NFR:**
  - FR-004, FR-020;
  - NFR-033: 100% of guide media captioned, with a text alternative (content checklist);
  - NFR-035: 100% of informative illustrations have purpose alt text (A11y + review).
- **Context:** none on the server; this is static client content.
- **Files / interfaces:**
  - `web/app/(onboarding)/` screens F-01 and G-01;
  - wording from `docs/domain/capture-guide-wording.md`;
  - captions file `.vtt` alongside the guide video;
  - `tests/features/first_run_and_capture_guide.feature`.
- **Out of scope:**
  - the framing check from a still frame (R2, FR-UX-13);
  - device-specific 60 fps steps until checked on the ST-025 phones;
  - the consent courtesy line (OQ-06, D-8).
- **Dependencies:**
  - coach sign-off of the wording (Sprint 1 D3);
  - the PM decision on the F-01 copy, which corrects FR-004's example for R1 (flows D-1);
  - a guide video recorded with an empty court or consenting team members only.
- **E2E verification:** E2E-01-01, steps "first run → capture guide", with axe on both pages.
- **Gherkin:** §7.2 and §14.3.3.

#### ST-016 Match setup flow with participants by nickname
- **Value:** As a player, I want to set up a match one simple question at a time, so that I can do it quickly on my phone and fix mistakes easily.
- **Priority / milestone:** Must (FR-021, FR-005) / M0.
- **FR / NFR:**
  - FR-021, FR-005; FR-043 (rally scoring shown but disabled);
  - NFR-028: 0 targets below 24×24 CSS px; primary ≥ 48 px;
  - NFR-031: 0 focused elements fully obscured at 360×640;
  - NFR-034: keyboard-only completion; reflow at 320/360/768/1280;
  - NFR-037: 100% of validation errors use the error-summary pattern.
- **Context / aggregates:** Match & Scoring (`matches`), aggregate `Match` with `MatchParticipant` children; value object `Participants` (§5).
- **Files / interfaces:**
  - `backend/src/racket/matches/` (domain `Participants`; `POST /matches` extended with format, scoring system, participants, me and date);
  - BOLA matrix entries for any new ID routes (IT-01-11);
  - `web/app/matches/new/` pages Q-01..Q-07;
  - `tests/features/match_setup.feature`.
- **Out of scope:**
  - selectable rally scoring (R2, FR-043);
  - opponent profiles (M6);
  - match title editing (judgment, flows D-2: the match is auto-named "{Format} · {date}");
  - mid-game start (Sprint 2, ST-034).
- **E2E verification:** E2E-01-03 keyboard-only setup, and the viewport matrix.
- **Gherkin:** §7.3 and §14.3.4.

#### ST-017 Resumable upload: checksum and expiration extensions, resume on return
- **Value:** As a player uploading a multi-gigabyte video on a phone, I want the upload to survive a dropped connection or a closed tab, so that I never start over.
- **Priority / milestone:** Must (FR-022) / M0.
- **FR / NFR:**
  - FR-022;
  - NFR-016: client throughput ≥ 90% of the measured uplink; chunks adapt between 5 and 50 MB (P with throttling);
  - NFR-026: 100% pass on the upload-resume regression suite;
  - NFR-042: the upload-completion SLI is emitted (OPS).
- **Context / aggregates:** Capture & Media (`video_ingest`), aggregate `UploadSession`.
- **Files / interfaces:**
  - `backend/src/racket/video_ingest/` (tus checksum and expiration extensions, ADR 0011);
  - the match read model exposes `upload.offset` and `upload.expires_at` (flows D-3, principal-engineer to confirm);
  - `web/` upload panel U-01..U-04 (tus-js-client);
  - `tests/features/resumable_upload.feature`.
- **Out of scope:**
  - abandoned-upload expiry clean-up (Sprint 2, ST-038);
  - background upload after tab close (not promised; OQ-18, SPIKE-06);
  - the push notification (FR-UX-34, later).
- **E2E verification:** E2E-01-02. Cut the network for 2 minutes at about 40%; the upload resumes, and the final sha256 equals the source (IT-01-08).
- **Gherkin:** §7.4 and §14.3.5.

#### ST-018 Upload validation by content, size and duration
- **Value:** As a player, I want a clear reason when my file cannot be used, and as the operator I want only real videos within the caps stored, so that storage and the worker stay safe.
- **Priority / milestone:** Must (FR-023) / M0.
- **FR / NFR:**
  - FR-023;
  - NFR-053: 0 non-video files stored; size cap enforced from `Upload-Length` before any byte is stored;
  - NFR-054: a crafted malformed container ends `failed` within its time limit, with no network (IT-01-10);
  - NFR-060: 0 jobs created for a rejected file.
- **Context / aggregates:** Capture & Media, `UploadSession` and `MediaAsset`; value object `UploadPolicy` (§5).
- **Files / interfaces:** `backend/src/racket/video_ingest/` (`UploadPolicy`, magic-byte sniff, probe-based duration check); U-03; `tests/features/upload_validation.feature`.
- **Out of scope:** transcoding and normalisation (R2); the footage quality report (ST-019, stretch).
- **Dependencies:**
  - ST-025 measures the caps (R-05; until then they are provisional 10 GB / 150 min and come from config);
  - security threat-model notes (Sprint 1 D2).
- **E2E verification:** demo step 5. A PDF renamed `match.mp4` and a 4-hour file each produce the right message and no stored object.
- **Gherkin:** §7.5 and §14.3.6.

#### ST-019 (stretch) Footage quality report, R1 facts
- **Value:** As a player, I want to know whether my video's settings will limit later results, so that I can film better next time without being blocked now.
- **Priority / milestone:** Should (FR-025) / M0.
- **FR / NFR:** FR-025. NFR: none beyond the UI DoD.
- **Context:** Capture & Media (`MediaAsset` facts from ST-009).
- **Files / interfaces:** `web/` M-02 report panel; `tests/features/footage_quality_report.feature`.
- **Out of scope:** the court-visibility estimate (S6, R2).
- **E2E verification:** upload the 30 fps fixture. The report names the consequence, and "Tag this match" is enabled.
- **Gherkin:** §7.6.

#### ST-020 Scoring engine core (a)

This is part (a) of FR-040/FR-041/FR-044. Part (b) is §14.2.

- **Value:** As a player, I want my score computed by one rules engine that can be checked and replayed, so that my score sheet is consistent and can be corrected once the official rules are confirmed.
- **Priority / milestone:** Must / M0.
- **FR / NFR:**
  - FR-040 (a), FR-041 (a), FR-044 (a);
  - NFR-079: 0 rule literals outside `RulesConfig` (IT-01-12);
  - QD-TR-01: 0 I/O imports in `sports/pickleball/rules` (IT-01-13);
  - domain suite < 10 s (NFR-073).
- **Context / aggregates:** Sport Plug-in (`sports/pickleball`), pure functions `apply` and `fold`; value objects `RulesConfig`, `GameState`, `RallyOutcome`, `DomainError`.
- **Files / interfaces:** `backend/src/racket/sports/pickleball/rules/`, with `apply(state, outcome, config) -> GameState | DomainError` and `fold(outcomes, config)`; `tests/features/scoring_engine_mechanics.feature`.
- **Out of scope:**
  - the `USAP-2026` preset and any rulebook claim (ST-020b);
  - singles (ST-035);
  - the call format (FR-048, ST-029);
  - rally scoring (FR-043).
- **E2E verification:** demo step 6 (`pytest -m scoring`). Mechanics scenarios pass and are reported separately from `@needs-verification` rows.
- **Gherkin:** §7.7, stated only against explicit configuration values (ADR 0009 rule 1).

#### ST-021 Match structure (a)
- **Value:** As a player, I want a best-of-1 or best-of-3 match to know when it is over, so that I cannot accidentally add rallies after the result.
- **Priority / milestone:** Must (FR-045 (a)) / M0.
- **FR / NFR:** FR-045 (a). NFR: none beyond the domain suite budget.
- **Context / aggregates:** Match & Scoring, `Match` (root) owning `Game` entities; value object `MatchState`.
- **Files / interfaces:** `backend/src/racket/matches/` (`MatchState`); `tests/features/match_structure.feature`.
- **Out of scope:** any rulebook claim about who serves first or about end switches. Both are explicit inputs (ST-021b).
- **E2E verification:** `pytest -m "story(id='ST-021')"`; M-01..M-08 pass.
- **Gherkin:** §7.10.

#### ST-022 Property suite P1-P8, nightly differential oracle P9, mutation baseline
- **Value:** As the team, we want invariants and an independent engine to check the scoring engine, so that a scoring bug is caught before a player sees a wrong score.
- **Priority / milestone:** Must (NFR-002 is an R1 gate) / M0.
- **FR / NFR:**
  - NFR-002a: ≥ 1,000 random sequences per scoring system per CI run, 0 failures;
  - NFR-002b: 100,000 sequences nightly, 0 disagreements;
  - NFR-072: mutation baseline recorded; ≥ 85% is gated from Sprint 2.
- **Context:** Sport Plug-in (tests only).
- **Files / interfaces:** `backend/tests/unit/` property tests (Hypothesis profile `ci`); `backend/tests/oracle/` (written without reading the production engine [DPA/AI-08]); `tests/features/property_and_oracle.feature` (§14.3.7).
- **Out of scope:** the mutation gate itself (Sprint 2).
- **E2E verification:** demo step 7. The nightly oracle result reads 100,000 sequences and 0 disagreements.
- **Gherkin:** §14.3.7, new.

#### ST-023 Golden scoring tables as executable scenarios
- **Value:** As the domain coach and QA, we want the provisional scoring tables to be executable, so that when the rulebook arrives only rows and tags change.
- **Priority / milestone:** Must (NFR-001, R1 gate) / M0.
- **FR / NFR:** FR-041 and FR-044 provisional rows (`@needs-verification`); FR-045 M rows (part a); NFR-001 (19 provisional rows this sprint, reported separately; QD-QG-P5).
- **Context:** Sport Plug-in (tests only).
- **Files / interfaces:** `tests/features/side_out_doubles_provisional.feature`, `tests/features/faults_provisional.feature`, and the M rows in `tests/features/match_structure.feature`.
- **Out of scope:** SOD-13..15 (Sprint 2); SOS and C rows (Sprint 2); the RS rows (blocked, FR-043).
- **E2E verification:** the test report lists the 19 rows under `@needs-verification` (ADR 0009 Confirmation).
- **Gherkin:** §7.8, §7.9, §7.10.

#### ST-024 Nightly quality jobs and upload SLIs
- **Value:** As the team, we want nightly oracle and mutation runs and live upload and availability SLIs, so that regressions and reliability problems are visible before the release.
- **Priority / milestone:** Must (NFR-002 nightly job, NFR-042) / M0.
- **FR / NFR:**
  - NFR-002 (nightly job);
  - NFR-041: availability SLI = non-5xx / all responses, excluding 429;
  - NFR-042: upload-completion SLI = uploads reaching full length / uploads started and resumed by a live client;
  - NFR-072 (nightly mutation job).
- **Context:** platform and operations.
- **Files / interfaces:** `.github/workflows/nightly*.yml`; `docs/sprints/01/status.json` (results); OpenTelemetry metric names agreed with the BE [AQS/OPS-07].
- **Out of scope:** SLO alerts and burn-rate paging (Sprint 5).
- **E2E verification:** one nightly run is visible with its results written to `status.json`.
- **Gherkin:** §14.3.8, new.

#### ST-025 Phone-file fixture set and upload-cap measurement (R-05)
- **Value:** As the team, we want real phone recordings with known properties, so that the upload caps and the probe are tested against what players actually upload.
- **Priority / milestone:** Must (NFR-025, FR-023 caps) / M0.
- **FR / NFR:**
  - NFR-025: 100% of MP4/MOV H.264/HEVC files from ≥ 5 phone models probe and play, including ≥ 1 VFR file;
  - FR-023 caps confirmed or changed by a dated note (conflict K12).
- **Context:** dataset and fixtures (QA/ML).
- **Files / interfaces:**
  - `fixtures/clips/phones-v1/` (or Git LFS / object store if larger than the repo limit; SRE to decide);
  - `manifest.json` per QD §8 (sha256, licence, consent);
  - a note on FR-023 K12;
  - `tests/features/phone_fixtures.feature` (§14.3.9).
- **Out of scope:** footage with non-consenting people (OQ-06); normalisation (R2).
- **E2E verification:** `racket-manifest-check` passes on the new set; IT-01-09 uses the fixtures.
- **Gherkin:** §14.3.9, new.

#### SPIKE-06 Upload behaviour on phone browsers
This is a spike. The DoR does not apply in full. Its output is an ADR with data informing OQ-18 and possibly U-01's copy (flows D-7).

### 14.2 Rules stories split per ADR 0009

ADR 0009 is Proposed and must be ratified at the Sprint 0 review (2026-10-16). If it is not ratified, every row below is blocked, and the §2 precondition applies.

| Story | Part (a): Ready, criteria against explicit `RulesConfig` values, no rulebook claim | Part (b): `needs-verification`, blocked on OQ-01 | Status of (b) |
|---|---|---|---|
| ST-020 (FR-040, FR-041, FR-044) | **ST-020a = ST-020 in §3.** `RulesConfig` validation, `apply`, `fold`, game end at target and margin, replay identity, typed errors, purity. §7.7 only | **ST-020b, "USAP-2026 preset values"**: target score, win-by, first-service exception, side-out rotation and fault outcomes, each with `@rule-<n>`. The preset may be named after the federation only when every row is verified (NFR-003; ADR 0009 rule 4) | Backlog. Pulled into the sprint in which the coach fills `docs/domain/rules-verified.md` §3. Size: S (config plus row tags) if no row changes (judgment) |
| ST-021 (FR-045) | **ST-021a = ST-021 in §3.** Best of N, match over, first server and end switch as explicit inputs. §7.10 | **ST-021b, "Match-format defaults from the rulebook"**: whether formats, end switches or game-2 first server have rulebook defaults the UI may pre-fill | Backlog, `needs-verification` (rules-verified §5 priority 8) |
| ST-023 (NFR-001) | Not split. It is a test story. Its rows run now tagged `@needs-verification` and are reported separately (QD-QG-P5) | Removing `@needs-verification` is done row by row, by the QA with the coach, once `@rule-<n>` is recorded (QD-TR-07) | — |
| ST-022 (NFR-002) | Not split. P1-P8 and P9 are stated for **any valid config** and make no rule claim | — | — |

Glossary rule for (a) stories: the criteria say "configured target", "configured margin" and "configured first server". They never say "the rule says". Terms marked "(needs-verification)" in `ddd-guidelines.md` §6 appear only in (b) stories or in `@needs-verification` scenarios.

### 14.3 Additional Gherkin (gaps in §7: negative cases, states and the stories without scenarios)

Declarative, about 3-5 steps, observable `Then` [DPA/PROD-01, DPA/PROD-02]. Copy strings match `docs/design/flows-sprint-01.md`.

#### 14.3.1 Sign-in (append to `tests/features/sign_in.feature`)

```gherkin
  Rule: Requesting a link never reveals whether an account exists

    Scenario: Link requested for an unknown address
      Given no account exists for "new@example.com"
      When a sign-in link is requested for "new@example.com"
      Then the page says "Check your email"
      And the response is the same as for an address that has an account

  Rule: Sign-in never asks for a password or a puzzle

    Scenario: The sign-in page asks only for an email address
      Given Ivy opens the sign-in page
      Then the only field is "Email address"
      And pasting into it is allowed
```

The first rule is pending the security-privacy-engineer's threat-model confirmation (flows D-4). If it is rejected, the scenario is removed through the BA, not by the implementer.

#### 14.3.2 Sign-out (append to `tests/features/sign_out.feature`)

```gherkin
  Rule: Signing out during an upload is a deliberate choice

    Scenario: Upload in progress
      Given Ivy's upload of "Sat doubles" is 64% done
      When she chooses to sign out
      Then she is told "Your upload will stop"
      And she can choose to keep uploading

  Rule: Match video is never stored by the app on the device

    Scenario: Video watched, then signed out
      Given Ivy has watched her match video in the app
      When she signs out
      Then no part of the video remains in the app's storage on the device
```

#### 14.3.3 First run and capture guide (append to `tests/features/first_run_and_capture_guide.feature`)

```gherkin
  Rule: The first-run screen is honest about Release 1

    Scenario: The app does not claim to score automatically
      Given Ivy has just created her account
      When the app opens for the first time
      Then she is told that she marks who won each rally and the app keeps the score
      And she is told that scores are unofficial until the rules are verified

  Rule: The guide still works when the video does not

    Scenario: Guide video cannot load
      Given the guide video cannot be loaded
      When Ivy opens the capture guide
      Then she sees "Everything in it is in the checklist above"
      And all setup instructions are still shown
```

#### 14.3.4 Match setup (append to `tests/features/match_setup.feature`)

```gherkin
  Rule: Answers can be changed from the check page

    Scenario: Change one answer
      Given Ivy is on "Check your answers"
      When she changes the format from doubles to singles
      Then she returns to "Check your answers"
      And she is asked to enter one player per side

  Rule: Contact details are discouraged, not stored silently

    Scenario: A nickname that looks like an email address
      Given Ivy is entering players
      When she enters "carlos@example.com" as a nickname
      Then she sees "This looks like contact details. Use a nickname instead."
      And she can still continue

  Rule: Dates cannot be in the future

    Scenario: Future match date
      Given Ivy is on the "date" question
      When she enters tomorrow's date
      Then she sees an error summary saying "The date must be today or in the past"
```

#### 14.3.5 Resumable upload (append to `tests/features/resumable_upload.feature`)

```gherkin
  Rule: Resuming needs the same video

    Scenario: A different file is chosen to resume
      Given Ivy's upload of "Sat doubles.mp4" stopped at 64%
      When she chooses a different video to resume it
      Then she sees "This is not the same video"
      And the upload is still at 64%

    Scenario: The unfinished upload has expired
      Given Ivy's unfinished upload has passed its expiry time
      When she tries to resume it
      Then she is told the upload expired and must be started again

  Rule: Nobody else can continue my upload

    Scenario: Carlos tries to send data to Ivy's upload
      Given Ivy has an unfinished upload
      When Carlos sends a chunk to it
      Then Carlos gets the same "not found" result as for an upload that does not exist
      And Ivy's upload is unchanged

  Rule: The app never promises a background upload

    Scenario: Upload page wording
      Given Ivy is uploading a video
      Then the page does not say the upload continues after the tab is closed
```

#### 14.3.6 Upload validation (append to `tests/features/upload_validation.feature`)

```gherkin
  Rule: Oversized files are refused before any data is stored

    Scenario: Declared size above the cap
      Given Ivy starts an upload that declares 12 GB
      When the server receives the upload request
      Then the upload is refused with "Videos must be 10 GB or smaller"
      And no bytes of that file are stored

  Rule: A refused file starts no work

    Scenario: No video check for a refused file
      Given Ivy's file was refused as "This file is not a video we can read"
      When she opens the match
      Then the match shows "No video yet"
      And no video check was started for that file
```

#### 14.3.7 Property suite and oracle (new: `tests/features/property_and_oracle.feature`, ST-022)

```gherkin
@M0 @story-ST-022 @nfr-002
Feature: The scoring engine keeps its invariants under any valid configuration
  Invariants P1-P8 come from QD §2.3. They make no rulebook claim (ADR 0009 part a).

  Rule: Invariants hold for random rally sequences

    Scenario Outline: Random sequences under a configuration
      Given 1,000 random rally sequences
      And a game configured with target <target> and margin <margin>
      When every sequence is scored
      Then no invariant from P1 to P8 is broken
      Examples:
        | target | margin |
        | 11     | 2      |
        | 15     | 2      |
        | 21     | 2      |
        | 11     | 1      |

  Rule: An independent engine agrees with the production engine

    Scenario: Nightly differential check
      Given 100,000 random rally sequences
      When both engines score every sequence
      Then they agree on every sequence

    Scenario: A disagreement is reported usefully
      Given the two engines disagree on a sequence
      When the nightly check finishes
      Then the run is marked failed
      And the report shows the shortest sequence that disagrees
```

#### 14.3.8 Nightly jobs and SLIs (new: `tests/features/nightly_quality.feature`, ST-024)

```gherkin
@M0 @story-ST-024 @nfr-041 @nfr-042
Feature: Nightly quality jobs and service-level indicators

  Rule: Nightly results are published where the team reads them

    Scenario: Nightly run completes
      Given the nightly quality run has finished
      When the team opens the sprint status file
      Then it shows the oracle result and the mutation score with the run date

  Rule: Upload completion and availability are measured

    Scenario Outline: Upload outcome counted
      Given an upload that <outcome>
      When the upload completion indicator is read
      Then that upload is counted as <counted>
      Examples:
        | outcome                                   | counted         |
        | reached full length                       | completed       |
        | was resumed by a live client and finished | completed       |
        | was abandoned by the user                 | not in the base |

    Scenario: Rate-limited requests do not count against availability
      Given 100 requests of which 2 were rate limited and none failed
      When the availability indicator is read
      Then availability is 100%
```

#### 14.3.9 Phone fixtures (new: `tests/features/phone_fixtures.feature`, ST-025)

```gherkin
@M0 @story-ST-025 @nfr-025
Feature: Phone-file fixtures cover what players upload

  Rule: The fixture set is broad enough and documented

    Scenario: Coverage of the set
      Given the phone fixture set version 1
      Then it has files from at least 5 phone models
      And at least one file has a variable frame rate
      And every file is listed in its manifest with model, frame rate and consent status

  Rule: Footage with people needs recorded consent

    Scenario: File with people and no consent record
      Given a fixture file shows people
      And its manifest has no consent record
      When the integrity check runs
      Then the check fails and names the file

  Rule: Every phone file is readable by the probe

    Scenario: Probe every fixture
      Given the phone fixture set version 1
      When each file is probed
      Then every file reports container, codec, frame rate and duration
```

### 14.4 NFR measures for Sprint 1 (testable form)

| NFR | Measure in Sprint 1 | Target | Test level | Story |
|---|---|---|---|---|
| NFR-002 | (a) random sequences per CI run; (b) nightly disagreements | (a) ≥ 1,000 per system, 0 failures; (b) 100,000, 0 disagreements | U (Hypothesis), nightly | ST-022, ST-024 |
| NFR-016 | client throughput vs measured uplink; chunk size | ≥ 90%; 5-50 MB adaptive | P (throttled) | ST-017 |
| NFR-026 | upload-resume regression suite | 100% pass | I | ST-017 |
| NFR-028 | targets below 24×24 CSS px on new screens | 0 | E2E custom check | ST-013..ST-018 UI |
| NFR-029 | token pairs below 4.5:1 text or 3:1 non-text | 0 (55/55 pass on 2026-10-03) | design-token check + axe | all UI |
| NFR-031 | focused elements fully obscured at 360×640 | 0 | E2E | ST-016, ST-017 |
| NFR-032 | cognitive-function tests at sign-in | 0 | E2E + R | ST-013 |
| NFR-033 | guide media without captions or text alternative | 0 | R (content checklist) | ST-015 |
| NFR-034 | keyboard-only setup journey; reflow at 320 | pass; no 2-direction scroll | E2E-01-03, viewport matrix | ST-016 |
| NFR-037 | validation errors not using the error-summary pattern | 0 | R + E2E | ST-016, ST-018 |
| NFR-042 | upload-completion SLI emitted | present on the dashboard | OPS | ST-017, ST-024 |
| NFR-053 | non-video or oversize files stored | 0 | I (IT-01-09) | ST-018 |
| NFR-055 | tokens left in the URL after exchange | 0 | I/E2E | ST-013 |
| NFR-057 | auth log lines missing UTC time, request ID or pseudonymous ID; lines containing an email address | 0; 0 | I (IT-01-03) | ST-013 |
| NFR-060 | jobs for rejected files | 0 | I (IT-01-09) | ST-018 |
| NFR-067 | authenticated data left after sign-out | 0 | I (IT-01-04) + E2E | ST-014 |
| NFR-072 | mutation score recorded | baseline recorded | nightly | ST-022, ST-024 |
| NFR-079 | rule literals outside `RulesConfig` | 0 | CI static (IT-01-12) | ST-020 |

### 14.5 Definition of Ready check (2026-10-03)

Key:

- ✓ means met, with its evidence in this file or in a linked one;
- **P** means pending, with an owner and a due date;
- — means not applicable.

The EM re-checks this table at Sprint 1 planning (2026-10-19).

| DoR item | 013 | 014 | 015 | 016 | 017 | 018 | 019s | 020a | 021a | 022 | 023 | 024 | 025 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ID, value statement | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| PM-assigned priority | P1 | P1 | P1 | P1 | P1 | P1 | P1 | P1 | P1 | P1 | P1 | P1 | P1 |
| FR/NFR and milestone linked | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Out of scope listed | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Declarative Gherkin, including negative cases | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ (new) | ✓ | ✓ (new) | ✓ (new) |
| NFRs measurable | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | ✓ | — | ✓ | ✓ | ✓ | ✓ |
| QA agrees criteria are testable, with levels named | P2 | P2 | P2 | P2 | P2 | P2 | P2 | P2 | P2 | P2 | P2 | P2 | P2 |
| Domain truth verified, or (a) with no rule claim | — | — | ✓ (filming advice, no rule) | ✓ (Q-02 shows no rule definition) | — | — | — | ✓ (a), ADR 0009 **P3** | ✓ (a), ADR 0009 **P3** | ✓ (any config) | ✓ (`@needs-verification`), ADR 0009 **P3** | — | — |
| Glossary terms used; new terms added | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Context and aggregates named | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Design doc or ADR for a new component, contract or cross-context change | ✓ (auth contract in §14.1; security review via P8) | — | — | P4 (participant model) | ✓ ADR 0011; P5 (D-3 read model) | ✓ ADR 0011 | — | P4 (`Match` design doc covers ST-021) | P4 | — | — | — | P6 (fixture storage) |
| UI flow and all states; WCAG and HAX checklists | ✓ flows A-01..A-05 | ✓ A-05 | ✓ F-01, G-01 | ✓ M-01, Q-01..Q-07 | ✓ U-01, U-02, U-04 | ✓ U-03 | ✓ U-02 / M-02 | — | — | — | — | — | — |
| Design review held | P7 | P7 | P7 | P7 | P7 | P7 | P7 | — | — | — | — | — | — |
| Threat-model notes attached | P8 | P8 | — | — | P8 | P8 | — | — | — | — | — | — | — |
| Sized; PRs of about 100 lines | ✓ §3 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Dependencies available | ✓ (S0) | ✓ | P9 (coach sign-off D3; F-01 copy D-1) | ✓ | P10 (SPIKE-06 D3) | P11 (ST-025 caps) | ✓ | ✓ (ST-023 first) | ✓ | ✓ | ✓ | ✓ | P12 (OQ-06 for people) |
| Files, interfaces and E2E step named | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |

Pending items, each with an owner and a due date:

| # | Item | Owner | Due |
|---|---|---|---|
| P1 | Confirm the priorities in §14.1, which come from FR MoSCoW | product-manager | Sprint 1 planning, 2026-10-19 |
| P2 | Agree that every criterion in §7 and §14.3 is testable and name the level | senior-qa-engineer | Sprint 0 D9 |
| P3 | Ratify ADR 0009. Without it, ST-020a, ST-021a and ST-023 are not Ready (§2 precondition) | human product owner | Sprint 0 review, 2026-10-16 |
| P4 | `Match` aggregate design doc and participant model, reviewed as a PR | principal-engineer | sprint-00 §4 D10 |
| P5 | Flows D-3: the match read model exposes the upload offset and expiry | principal-engineer, senior-backend-engineer | Sprint 1 planning |
| P6 | Where the phone fixtures live (repo, LFS or object store) | sre-devops-engineer | Sprint 1 planning |
| P7 | Design review of `docs/design/flows-sprint-01.md` | principal-designer (with the coach, FE, BA and security) | Sprint 0 D8 |
| P8 | Threat-model notes for auth and upload | security-privacy-engineer | Sprint 0 D5 (v0), Sprint 1 D2 (notes) |
| P9 | Coach sign-off on the capture-guide wording; PM decision on the F-01 copy | pickleball-domain-coach; product-manager | Sprint 1 D3; ST-015 start |
| P10 | SPIKE-06 result (may change U-01's copy) | senior-frontend-engineer | Sprint 1 D3 |
| P11 | ST-025 cap measurement (until then the provisional caps come from config) | senior-ml-cv-engineer | Sprint 1 D7 |
| P12 | OQ-06 answer, for any fixture footage with people | human product owner | Sprint 1 planning |

**Verdict (BA, 2026-10-03):**

- Every BA-owned DoR item is met for ST-013..ST-025.
- No story is fully Ready yet: each has at least the QA testability check (P2) and the PM priority (P1) open, and these are not the BA's to tick.
- The rules stories also wait for ADR 0009 ratification (P3).
- The EM decides at planning.

### 14.6 Glossary additions (also added to `docs/process/ddd-guidelines.md` §6)

| Term | Definition | Context |
|---|---|---|
| Service turn | The run of rallies during which one side keeps the serve, from gaining it to the side-out or game end. In doubles it spans server 1 and server 2 (needs-verification) | Sport Plug-in / Analytics |
| Rally ending | How a rally ended: `winner`, `unforced_error`, `forced_error`, `fault` (with an optional subtype) or `replay` (FR-050; QD X3) | Match & Scoring |
| Unforced error / forced error | An error the player had time and position to avoid / an error caused by the opponent's shot. Coaching judgment; the label is kept only if labeller agreement reaches κ ≥ 0.6 (QD X3) | Match & Scoring / Analytics |
| Rules preset | A named, immutable `RulesConfig`. Only `PROVISIONAL-UNVERIFIED` exists until every row of a federation preset is verified (ADR 0009) | Sport Plug-in |
| Upload session | A resumable upload of one video to one match, with its offset, length and expiry (tus) | Capture & Media |
