# Functional Requirements (FR register)

- **Status:** Baselined draft v1, for product-owner review. Items whose acceptance criteria rest on a pickleball rule are `needs-verification` and are **not Ready** [DOM G1; process/definition-of-ready.md "Domain truth"].
- **Date:** 2026-10-03
- **Author:** business-analyst
- **Consulted (via their brainstorm files):** product-manager and business-analyst (`brainstorm-product.md`, cited "PROD"); principal-engineer, senior-backend-engineer, senior-ml-cv-engineer, sre-devops-engineer, security-privacy-engineer (`brainstorm-engineering.md`, "ENG"); principal-designer, senior-frontend-engineer (`brainstorm-design.md`, "DES"); senior-qa-engineer, pickleball-domain-coach (`brainstorm-quality-domain.md`, "QD").
- **Inputs:** `docs/specs/2026-10-02-racket-analytics-design.md` ("spec §n"), the four brainstorms, `docs/research/*.md`, `docs/process/*.md`.
- **Companion files:** `non-functional-requirements.md` (NFR-###), `traceability-matrix.md`, `open-questions.md`, ADRs 0002-0006 in `docs/decisions/`.

## 0. How to read this register

### 0.1 Citations and evidence
- Research is cited `<file>/<ID>` with the prefixes EP, AQS, DPA and DOM [process/working-agreement.md §0]. Only sources the research files mark verified are cited. A gap reference such as `[AQS G3.5]` points at a guideline or gap in that file.
- Brainstorm items are cited by file and item ID, e.g. "PROD US-401", "ENG ENG-FR-07", "DES FR-UX-63", "QD QD-RE-10".
- Anything without a verified source is labelled **(judgment)**. Every numeric threshold in an acceptance criterion is (judgment) unless a source is given next to it.
- **Pickleball rule content is UNVERIFIED** [DOM G1 R1-R6, DOM Gaps 1]. Score examples in the Gherkin below come from QD §2.2. QD built them from those unverified rules, and the domain coach owns them.

### 0.2 Priority: MoSCoW (judgment)
MoSCoW could not be verified from its source [DPA Gaps], so we use it as a working tool only (judgment). Priority is stated **relative to the MVP**:
- **Must:** the MVP release it is in cannot ship without it.
- **Should:** important, and planned for the stated release. It can slip one release without breaking the value chain.
- **Could:** desirable. Planned only if capacity allows, or it belongs to a post-MVP release.
- **Won't (this MVP):** explicitly out of scope for R1 and R2. It is recorded so nobody builds it by accident.

### 0.3 Releases (see ADR 0002, status Proposed)
| Release | Name | Spec milestones | Meaning |
|---|---|---|---|
| **R1** | MVP-1 "Walking skeleton" | M0 + thin slices of M4 and M5 | Upload → Quick Tag → score sheet → starter stats → rules-only plan. Delivers the first milestone end to end with no computer vision. |
| **R2** | MVP-2 "First automation" | M1, M2, and M5 (LLM "why" + efficacy) | Automation takes over tagging effort: calibration, tracking, ball/hit/rally detection. Adds LLM-written explanations behind validation. |
| R3 | Post-MVP "Automatic scoring" | M3, M4 | Auto score with review queue, shot classification, full §5 analytics, clips. |
| Later | — | M6, M7, spec §9 | Opponent scouting, live mode, coach view. |

"MVP" in this repo means **R1 + R2**.

### 0.4 Status values
`ready-candidate` (can become Ready once the DoR checklist is done), `needs-verification` (depends on an unverified rule or coaching fact), `needs-PO-decision` (blocked on an item in `open-questions.md`), `deferred` (Won't for this MVP).

### 0.5 Bounded contexts
The FRs are grouped by the contexts in `docs/process/ddd-guidelines.md` §2. Engineering proposed three changes: merge Drill Library into Coaching, add a "Dataset & Labelling" context, and keep Review & Correction inside Match & Scoring [ENG §2 C1-C4]. Those changes belong to the principal-engineer and the first EventStorming [EP/ENG-11, EP/ENG-14], not to the BA. Until then this register:
- groups Coaching and Drill Library together but keeps their FR blocks separate (§F, §G);
- lists labelling FRs in their own section (§H), marked "proposed context";
- puts review and correction in Match & Scoring (§C), as all three engineering, design and QA brainstorms assumed.

---

## 1. Conflict resolution log

Where the brainstorms disagreed, the BA chose as follows. Each row names who proposed what. Rows marked ADR are significant enough to have their own decision record.

| # | Topic | Proposals | Decision and why | Where |
|---|---|---|---|---|
| K1 | MVP scope | Spec: M0-M5 before a plan exists. PROD C1: a thin R1 walking skeleton, with MVP = R1+R2. ENG §0.1/§9: "M0 + thin slice of M1-M3", with the coaching workflow in sprint 3. DES and QD follow PROD's R1/R2/R3. | **PROD's slicing**, with ENG's sequencing inside it. All four brainstorms agree that R1 must close the value chain without CV. Using PROD's release names keeps one vocabulary. Needs PO approval because it changes M0/M5 scope. | ADR 0002 |
| K2 | LLM in R1? | ENG §9 step 2 put the coaching workflow (LLM + validator + 20-case eval) in sprint 3. PROD C10 asked for a rules-only R1 plan and the LLM in R2. | **Rules-only in R1, LLM in R2.** Start with the simplest working path [DPA/AI-01]. The eval set should exist before the capability [DPA/AI-05]. The rules-only plan stays as the fallback either way. | FR-121, FR-125; ADR 0002 |
| K3 | Weakness-ranking unit | Spec §6: "points lost per match". QD X1: "rallies lost per game", split by serve and receive, because under side-out scoring a rally lost on serve concedes no point [DOM G1 R2, unverified]. | **QD's unit**, behind an attribution-conservation invariant. The spec's unit would undercount serving-side errors. Rally scoring makes the two units coincide, so nothing is lost. Depends on R2 verification → PO confirmation. | FR-109, FR-120; ADR 0003 |
| K4 | M2 "≥90% rallies segmented correctly" | PROD C9: within ±1.0 s, no merge/split, report P/R. ENG CV-T09: F1 with the same matching rule. | **F1 with the ±1.0 s / no-merge-or-split rule.** Both agree; F1 subsumes P and R. | NFR-006; ADR 0004 |
| K5 | M3 "≤1 correction per game" | PROD C8: count score-affecting corrections only. ENG §5.4: ≤2 corrections + ≤5 confirmations per game at MVP, with ≥95% of unflagged rallies correct. QD X9: defines score-affecting fields and an oracle-user measurement, with a CI lower bound ≥93%. | **ENG's split metric, with QD's definitions and measurement.** One correction per game implies ~96-97% accuracy on every score-affecting field (ENG, judgment), which conflicts with the spec's own premise that one phone cannot referee. M3 is R3 (post-MVP), so this is Proposed and goes to the PO. | NFR-007; ADR 0004 |
| K6 | Low-sample threshold | PROD US-501 and DES FR-UX-71: flag at n < 10 rallies. QD X5: 95% Wilson interval, flag at n < 20 or interval width > 30 pp; count metrics flagged below 2 games. | **QD's rule.** A flat n ignores effect size (QD, judgment). HAX asks us to make clear how well the system can do what it does [DPA/DESIGN-11 G2]. The thresholds live in config. | FR-101; ADR 0005 |
| K7 | Plan efficacy claims | Spec §6 step 4: score the plan after the next match. PROD US-1102 and DES FR-UX-83: no claim when either sample is low. QD X6: n ≥ 20 in both windows **and** non-overlapping Wilson intervals. | **QD's stricter rule.** It is the only measurable version. | FR-127; ADR 0005 |
| K8 | Rally ending taxonomy | Spec §4: winner / error / fault. PROD US-401: winner / unforced error / fault. QD X3: winner, unforced_error, forced_error, fault{subtype}, replay, with a κ ≥ 0.6 gate on forced vs unforced. | **QD's taxonomy, with the κ fallback.** "Fault" overlaps "error" in the spec's list. QD's gate makes the subjective label safe: below κ 0.6, analytics merge forced and unforced into "error". | FR-050, FR-100 |
| K9 | Who erred (doubles) | PROD US-401 records the side only. QD X10 adds an optional `responsible_player`. | **Add the optional tap.** Spec §5 needs per-player errors. It is skippable, so the Quick Tag effort target holds. | FR-050 |
| K10 | Shot taxonomy | Spec §3: a single label. ENG §5.5: hierarchical, coarse then fine. QD X4: faceted (position, contact, trajectory, intent, technique). | **QD's faceted model, released in ENG's coarse-first order** (QD-TX-04 keeps it). A single label forces wrong labels, e.g. a volley that is also a dink (QD). Shot-level stroke annotation has prior art in ShuttleSet [DOM/CV-18]. This is R3 scope; the coach and ML engineer record the taxonomy ADR before R3. | FR-088 |
| K11 | Shot-level metrics' release | QD §3.2: AN-08..AN-16 in R2. PROD E10: full analytics in R3. | **AN-16 (partner spacing) and heatmaps in R2; AN-08..AN-15 in R3.** AN-08..AN-15 need shot types, which come from automatic classification (R3) or internal Full Tag. Shipping them in R2 would show users metrics they cannot get from their own matches. | FR-106, FR-107, FR-108 |
| K12 | Upload caps | PROD US-203: 10 GB and 3 h. ENG NFR-SEC-04: 10 GB and 150 min. DES FR-UX-33: "2 h 30 min and 8 GB", pending R-05. | **10 GB and 150 min, provisional.** The security owner's numbers, which DES's 150 min matches. Final values come from the R-05 phone-file measurement. | FR-023, NFR-053 |
| K13 | Abandoned-upload expiry | PROD US-202: 7 days. ENG ENG-FR-01: 24 h. | **24 h, configurable.** A partial upload of up to 10 GB is High-class data (ENG §4.6), and keeping it for 7 days is ~7x the storage exposure. DES FR-UX-31's "resume on return" covers same-day returns. Revisit with upload telemetry. | FR-024; ADR 0006 |
| K14 | Deletion windows | PROD US-103: gone from the account in 1 min, unrecoverable in 30 days. ENG NFR-PRIV-04: all objects and rows removed in 7 days. | **Hidden in ≤ 1 min, fully purged in ≤ 7 days.** Takes the stricter value from each. The legal adequacy of either window is unverified [AQS G3.5] → PO. | FR-006, NFR-066; ADR 0006 |
| K15 | Video retention | PROD US-104: user choice of 30/90/365 days or until deleted, default 90. ENG §6.1: originals deleted 30 days after analysis, proxy kept while the match exists. | **Both, at different layers.** Originals and mezzanine are deleted 30 days after analysis completes (system rule, cost: ENG §4.3). The user's retention choice applies to the review proxy and clips, default 90 days. Trade-off: re-processing (FR-089) after 30 days runs on the proxy or not at all → PO question. | FR-008; ADR 0006 |
| K16 | Correction latency | PROD NFR-PERF-02 and DES NFR-UXP-02: ≤ 200 ms p95. ENG NFR-PERF-02: ≤ 1.5 s p95 for replay + metrics. | **Both, measured at different points.** The optimistic client update must take ≤ 200 ms. The server-confirmed replay and recomputed metrics must take ≤ 1.5 s. | NFR-012, NFR-013 |
| K17 | Time to results (automatic) | PROD NFR-PERF-03: p90 ≤ 2x video duration. ENG NFR-PERF-04: p50 ≤ 0.5x, p90 ≤ 1.0x, hard cap 2 h. | **PROD's value is the release gate and ENG's is the target.** ENG's numbers depend on SPIKE-03/04, which have no data yet. | NFR-018 |
| K18 | Calibration interaction | Spec §3: "confirm 4 corners", which in practice means dragging. DES CD1/CD2: confirm any ≥ 4 named keypoints, tap-to-place, no drag required. | **DES.** Required by WCAG 2.2 SC 2.5.7 [DPA/DESIGN-05]. More points help a robust homography fit [DOM G6 H2, partly inferred]. | FR-082 |
| K19 | "Height over the net" | Spec §4 `Shot` field. ENG §0.5: drop it. DES CD5: show "not measured". | **Won't (this MVP).** A homography is valid only on the court plane [DOM/CV-12]. | §J non-goals |
| K20 | Evidence links in R1 | Spec: clips arrive at M4. DES CD8: timestamp deep links from R1. | **DES.** Costs little and keeps spec §6's "every insight links to the video moments". | FR-027, FR-103 |
| K21 | Training-data consent | Spec §2: "every correction becomes training data". ENG C2 / NFR-PRIV-06: a separate, revocable opt-in. | **ENG.** Training is a different purpose from analysing the user's own match (judgment). The legal basis is unverified [AQS G3.5] → PO. | FR-009 |
| K22 | Rally scoring timing | PROD US-302: Should, release unspecified. QD Q3: R2. | **Should, R2, blocked on verification.** It is provisional, and its rotation rules are unknown [DOM G1 R3]. | FR-043 |

---

## A. Identity & Players

#### FR-001 Passwordless sign-in
- **Description:** A user signs up and signs in with a passkey or an email magic link. The link is single-use, expires after 15 min (judgment), and its token is removed from the URL after it is exchanged. No password, puzzle or other cognitive function test is required.
- **Priority:** Must · **Release:** R1 · **Milestone:** M0 · **Status:** ready-candidate
- **Source:** PROD US-101; DES FR-UX-01; [DPA/DESIGN-06]; [AQS/SEC-05] (no tokens in URLs, 14.2.1)
```gherkin
Feature: Sign in without a memorised password
  Rule: Authentication never requires a cognitive function test
    Scenario: Sign up with an email magic link
      Given Ivy has no account
      When she requests a sign-in link and opens it within 15 minutes
      Then she is signed in and sees "Record your first match"
    Scenario: Expired or reused link
      Given Ivy's sign-in link is 16 minutes old or was already used
      When she opens it
      Then she sees "This link has expired" and an option to send a new one
```

#### FR-002 Only the owner can access their resources
- **Description:** Every match, rally, shot, clip, media object, plan and player record can be read or changed only by its owner. MVP has no sharing (NFR-064; DES FR-UX-100). Any other user gets the same "not found" response as for a missing resource. The attempt is security-logged.
- **Priority:** Must · **Release:** R1 · **Milestone:** M0 · **Status:** ready-candidate
- **Source:** PROD US-102; ENG NFR-SEC-01; DES FR-UX-101; [AQS/SEC-09]; [AQS/SEC-03]; [AQS/SEC-04]
```gherkin
Feature: Object-level authorisation
  Rule: Every resource ID is checked against its owner
    Scenario Outline: Another user cannot open my resource
      Given Ivy owns a <resource>
      When Carlos requests that <resource> by its ID
      Then Carlos sees the same "not found" result as for a resource that does not exist
      And the attempt appears in the security log
      Examples:
        | resource       |
        | match          |
        | rally          |
        | clip           |
        | video          |
        | training plan  |
        | player profile |
```

#### FR-003 Age confirmation and footage notice
- **Description:** At sign-up the account holder confirms they are 18 or over. They also see a notice asking them not to upload matches that involve minors. The question uses a single question page. The legal wording and the age threshold are interim pending PO and legal decisions.
- **Priority:** Must (gate for any real-user beta) · **Release:** R1 · **Milestone:** M0 · **Status:** needs-PO-decision (OQ-05)
- **Source:** PROD US-105, C12; DES FR-UX-03; [DPA/DESIGN-12]; privacy law unverified [AQS G3.5]
```gherkin
Feature: Age confirmation
  Scenario: Under-age applicant
    Given Sam is creating an account
    When Sam answers that he is under 18
    Then the account is not created
    And Sam sees why and what he can do instead
  Scenario: Adult confirms
    Given Ivy is creating an account
    When she confirms she is 18 or over
    Then she continues to the first-run screen and sees the footage notice
```

#### FR-004 First-run promise
- **Description:** One screen states what the app can and cannot do in this release. Example: "We score your match and show where you lose points. One phone can't make line calls good enough to referee from."
- **Priority:** Should · **Release:** R1 · **Milestone:** M0 · **Status:** ready-candidate
- **Source:** DES FR-UX-02; spec §2 accuracy posture; [DPA/DESIGN-11] G1, G2
```gherkin
Feature: First-run promise
  Scenario: New user sees capabilities and limits
    Given Ivy has just created her account
    When the app opens for the first time
    Then she sees what the app does and what it cannot do, in plain words
    And she can continue to the capture guide
```

#### FR-005 Match participants by nickname
- **Description:** Match setup records who is on each side, as nicknames only, and which participant is "me". Doubles has slots A1, A2, B1, B2; singles has A1, B1. Nickname fields carry helper text saying not to enter contact details. No contact details, photos or face data are stored for participants.
- **Priority:** Must · **Release:** R1 · **Milestone:** M0 · **Status:** ready-candidate
- **Source:** DES FR-UX-20, FR-UX-103; PROD C6; ENG §3.2 `MatchParticipant`; spec §8
```gherkin
Feature: Match participants
  Rule: Participants are nicknames assigned by the user
    Scenario: Doubles match setup
      Given Ivy is setting up a doubles match
      When she enters four nicknames, two per side, and marks herself as "me"
      Then the match shows two sides of two players with her marked as "me"
    Scenario: Wrong number of players for the format
      Given Ivy is setting up a doubles match
      When she enters three nicknames
      Then she sees an error summary saying each side needs two players
```

#### FR-006 Delete a match and everything derived from it
- **Description:** The owner can delete a match. The confirmation page states the consequence. The match, its videos, clips, tags, stats and derived artefacts disappear from the account within 1 min and are purged from storage and the database within 7 days. Plans that cited the match keep a note "evidence removed".
- **Priority:** Must · **Release:** R1 · **Milestone:** M0 · **Status:** ready-candidate (windows needs-PO-decision, OQ-07)
- **Source:** PROD US-103; ENG NFR-PRIV-04; DES FR-UX-90; [AQS/SEC-05] 14.2.7; [DPA/DESIGN-11] G16; conflict K14; ADR 0006
```gherkin
Feature: Match deletion
  Scenario: Delete an analysed match
    Given Ivy has a match with stats and a plan that cites it
    When she deletes the match and confirms the stated consequences
    Then within 1 minute the match no longer appears anywhere in her account
    And the plan shows "evidence removed" against drills that cited it
    And within 7 days no stored object or record of that match remains
```

#### FR-007 Delete my account
- **Description:** The owner can delete their account. All their matches are deleted as in FR-006, plus profiles and plans. They are signed out everywhere.
- **Priority:** Must · **Release:** R1 · **Milestone:** M0 · **Status:** ready-candidate
- **Source:** PROD J5; ENG ENG-FR-13; spec §8
```gherkin
Feature: Account deletion
  Scenario: Delete account
    Given Ivy has 3 matches and a plan
    When she deletes her account and confirms
    Then she is signed out and cannot sign in to that account again
    And within 7 days none of her matches, plans or profiles remain stored
```

#### FR-008 Video retention setting
- **Description:** Two rules apply:
  - **System rule:** original and normalised video are deleted 30 days after analysis completes.
  - **User rule:** the user chooses how long the review video and clips are kept: 30, 90 or 365 days, or "until I delete". The default is 90 days (judgment).

  Derived stats, tags and plans stay until the match is deleted. The user sees each video's deletion date.
- **Priority:** Should · **Release:** R1 · **Milestone:** M0 · **Status:** needs-PO-decision (OQ-07)
- **Source:** PROD US-104; ENG §6.1; DES FR-UX-90; spec §8; [AQS/SEC-05] 14.2.7; conflict K15; ADR 0006
```gherkin
Feature: Video retention
  Rule: Review video is deleted on the user's schedule; stats remain
    Scenario: Retention period passes
      Given Ivy chose "keep video 30 days" for a match analysed 31 days ago
      When she opens that match
      Then the score sheet and stats are shown
      And the video area says the video was deleted on its retention date
```

#### FR-009 Training-data consent
- **Description:** A separate, optional, revocable opt-in decides whether a user's matches may be used to train or evaluate models. It is off by default. Revoking it removes the user's matches from future label sets. What happens to already-frozen gold sets is a PO decision.
- **Priority:** Should · **Release:** R1 · **Milestone:** M0 · **Status:** needs-PO-decision (OQ-06)
- **Source:** ENG §2 C2, NFR-PRIV-06; spec §2 ("every correction becomes training data"); legal basis unverified [AQS G3.5]; conflict K21
```gherkin
Feature: Training-data consent
  Scenario: User has not opted in
    Given Ivy has not opted in to training use
    When the next label set is built
    Then none of Ivy's matches or corrections are in it
  Scenario: User revokes consent
    Given Ivy opted in and later revokes
    When the next label set is built
    Then none of Ivy's matches are in it
```

#### FR-010 Export my data
- **Description:** The owner can export their match records (rallies, scores, tags, metrics, plans) as JSON and CSV.
- **Priority:** Could · **Release:** R2 · **Milestone:** — · **Status:** ready-candidate
- **Source:** ENG ENG-FR-13 (judgment)
```gherkin
Feature: Data export
  Scenario: Export a match
    Given Ivy has a tagged match
    When she requests an export
    Then she receives a CSV and a JSON file containing every rally and its score
```

#### FR-011 Sign out clears local data
- **Description:** Signing out clears authenticated data from client storage and service-worker caches. Media is never cached by the service worker.
- **Priority:** Must · **Release:** R1 · **Milestone:** M0 · **Status:** ready-candidate
- **Source:** DES FR-UX-91; [AQS/SEC-05] 14.3.1-14.3.3; [AQS/STACK-04]
```gherkin
Feature: Sign out
  Scenario: Shared device
    Given Ivy viewed her score sheet on a shared tablet
    When she signs out and the next person opens the app offline
    Then none of Ivy's matches, stats or videos can be seen
```

#### FR-012 Opponent profiles linked across matches
- **Description:** A user-created, creator-only opponent record linked across matches (spec §4, M6).
- **Priority:** Won't (this MVP) · **Release:** Later · **Milestone:** M6 · **Status:** deferred (privacy gate, OQ-15)
- **Source:** spec §4, §7 M6; PROD C6, E12; [AQS/SEC-03]
```gherkin
Feature: Opponent profiles (deferred)
  Scenario: Profile privacy
    Given Ivy created an opponent profile "Lefty"
    When Carlos requests that profile by its ID
    Then Carlos sees "not found"
```

---

## B. Capture & Media

#### FR-020 Capture guide
- **Description:** A checklist of no more than 6 illustrated items:
  - tripod behind a baseline;
  - as high as safely possible;
  - landscape orientation;
  - 1080p at 60 fps;
  - whole court in frame;
  - avoid sun behind the court.

  Each illustration has alt text. A captioned 30-60 s video supplements the checklist, which also serves as the video's text alternative. Expandable help explains how to set 60 fps on iPhone and Android. The domain coach signs off the wording.
- **Priority:** Must · **Release:** R1 · **Milestone:** M0 · **Status:** ready-candidate
- **Source:** PROD US-201; DES FR-UX-10..12, CD11; spec §2, §8; [DPA/DESIGN-08]; [DPA/DESIGN-09]; [DPA/DESIGN-10]
```gherkin
Feature: Capture guide
  Scenario: Read the guide before filming
    Given Ivy opens the capture guide
    When she reads it without playing the video
    Then every setup instruction is available as text with an illustration
  Scenario: Watch the guide video
    Given Ivy plays the guide video
    Then captions are shown by default
```

#### FR-021 Match setup flow
- **Description:** Setup asks one question per page, in this order:
  1. format;
  2. scoring system (rally scoring is labelled provisional; FR-043);
  3. participants (FR-005);
  4. which participant is "me";
  5. date (pre-filled);
  6. video.

  Each page has a Back link and a Continue button. Optional fields say "(optional)". Known answers are pre-filled from the last match. A "Check your answers" page comes before the upload starts. Validation errors use the error-summary pattern.
- **Priority:** Must · **Release:** R1 · **Milestone:** M0 · **Status:** ready-candidate
- **Source:** DES FR-UX-20..23; PROD J1 step 3; [DPA/DESIGN-12]; [DPA/DESIGN-13]; FR-UX-23's "check answers" page is (judgment)
```gherkin
Feature: Match setup
  Rule: One question per page, with errors summarised at the top
    Scenario: Missing answer
      Given Ivy is on the "format" page
      When she continues without choosing a format
      Then she sees "There is a problem" at the top with a link to the format question
      And the page title starts with "Error:"
    Scenario: Review before upload
      Given Ivy has answered every setup question
      When she reaches "Check your answers"
      Then each answer is listed with a "Change" link
```

#### FR-022 Resumable upload
- **Description:** Video uploads resume from the last acknowledged byte after a network loss or after the user leaves and returns. The UI shows % done, MB of total, a plain-language state, and a time estimate once 10 s of throughput has been measured. The copy must not promise that uploads continue after the tab is closed.
- **Priority:** Must · **Release:** R1 · **Milestone:** M0 · **Status:** ready-candidate
- **Source:** PROD US-202; ENG ENG-FR-01; DES FR-UX-30..32; spec §3; [AQS/STACK-06]
```gherkin
Feature: Resumable upload
  Scenario: Connection drops mid-upload
    Given Ivy is uploading a 3 GB video and 40% has been sent
    When her connection drops for 2 minutes and returns
    Then the upload continues from at least 40%
    And she sees the state change from "Paused: waiting for connection" to "Uploading"
  Scenario: Return after closing the tab
    Given Ivy closed the tab when her upload was 64% done
    When she opens the app again within 24 hours
    Then she is offered to resume from 64%
```

#### FR-023 Upload validation
- **Description:** The server accepts only real video files: MP4 or MOV containers with H.264 or HEVC, checked by content and not by extension. Files must be within the size and duration caps (provisional: 10 GB and 150 min). Rejections use the error summary and state the caps in human units. Server checks are authoritative.
- **Priority:** Must · **Release:** R1 · **Milestone:** M0 · **Status:** ready-candidate (caps confirmed by R-05)
- **Source:** PROD US-203; ENG NFR-SEC-04; DES FR-UX-33; [AQS/SEC-02]; [DPA/DESIGN-13]; conflict K12
```gherkin
Feature: Upload validation
  Rule: Only real video files within the caps are accepted
    Scenario Outline: Reject invalid files
      Given Ivy selects <file>
      When she starts the upload
      Then she sees "There is a problem" with "<message>"
      And no match is created from that file
      Examples:
        | file                         | message                                     |
        | a PDF renamed to match.mp4   | This file is not a video we can read        |
        | a 12 GB video                | Videos must be 10 GB or smaller             |
        | a 4-hour video               | Videos must be 2 hours 30 minutes or shorter |
```

#### FR-024 Abandoned uploads expire
- **Description:** An upload not completed within 24 h (judgment, configurable) expires. Its stored bytes are freed and it no longer appears in the matches list.
- **Priority:** Must · **Release:** R1 · **Milestone:** M0 · **Status:** ready-candidate
- **Source:** ENG ENG-FR-01; PROD US-202 (7 days, not chosen); [AQS/STACK-06] expiration extension; conflict K13; ADR 0006
```gherkin
Feature: Abandoned upload expiry
  Scenario: Upload never finished
    Given Ivy started an upload 25 hours ago and never finished it
    When she opens her matches list
    Then the partial upload is not listed
    And it cannot be resumed
```

#### FR-025 Footage quality report
- **Description:** After upload the user sees frame rate, resolution and duration. From R2 they also see a court-visibility estimate. Each problem is stated as its consequence, e.g. "30 fps: shot types may be less accurate. Score and rally stats are unaffected." The report never blocks the upload or the manual path.
- **Priority:** Should · **Release:** R1 (fps, resolution, duration); R2 (court visibility) · **Milestone:** M0/M1 · **Status:** ready-candidate
- **Source:** PROD US-204, C7; ENG ENG-FR-02; DES FR-UX-40, CD7; spec §8; [DPA/DESIGN-11] G16
```gherkin
Feature: Footage quality report
  Rule: The report explains consequences and never blocks
    Scenario: 30 fps video
      Given Ivy uploaded a 1080p video recorded at 30 fps
      When the quality report is shown
      Then it says which results may be less accurate and which are unaffected
      And she can continue to tag the match
```

#### FR-026 Analysis level is explicit
- **Description:** Every match shows its analysis level: "Manual tagging only", "Rally and score only" or "Full analysis". A degraded level is an explicit state, never a partial result.
- **Priority:** Should · **Release:** R2 · **Milestone:** M2 · **Status:** ready-candidate
- **Source:** DES FR-UX-41; ENG §1.2 `analysis_level`; spec §8; [AQS/SEC-12]
```gherkin
Feature: Analysis level
  Scenario: Ball tracking failed the quality gate
    Given Ivy's video passed rally detection but not ball tracking
    When the analysis finishes
    Then the match is labelled "Rally and score only"
    And no shot-level stats are shown for it
```

#### FR-027 Jump to the video moment
- **Description:** From any rally row or evidence link the video starts playing at that rally's start time. No clip extraction is needed.
- **Priority:** Must · **Release:** R1 · **Milestone:** M0 · **Status:** ready-candidate
- **Source:** DES CD8; spec §6 ("every insight links to the video moments"); [DPA/DESIGN-11] G11; conflict K20
```gherkin
Feature: Evidence deep links
  Scenario: Open a rally from the score sheet
    Given Ivy's score sheet lists rally 12 starting at 14:32
    When she opens rally 12's video link
    Then the video plays from 14:32
```

#### FR-029 Analysis-ready notification
- **Description:** After the first upload completes, the app offers opt-in web push for "analysis ready". It also sends an email (judgment). An in-app status is always available. The "Analysing" page shows stages and an estimate, not a spinner.
- **Priority:** Should · **Release:** R2 · **Milestone:** M2 · **Status:** ready-candidate
- **Source:** DES FR-UX-34, §4; ENG ENG-FR-14; [AQS/STACK-04] (VAPID web push); [DPA/DESIGN-11] G3
```gherkin
Feature: Analysis-ready notification
  Scenario: Push permission asked in context
    Given Ivy has never uploaded a match
    When she opens the app
    Then she is not asked for notification permission
  Scenario: Notified when ready
    Given Ivy opted in to notifications and her analysis is running
    When the analysis finishes
    Then she receives a notification that links to the match
```

#### FR-030 Extracted clips
- **Description:** Short clips around evidence moments are generated on demand from the review video and served by short-lived signed URL.
- **Priority:** Could · **Release:** R3 · **Milestone:** M4 · **Status:** ready-candidate
- **Source:** spec §5, §6, M4; ENG ENG-FR-12; [AQS/SEC-05] 14.2.1
```gherkin
Feature: Evidence clips
  Scenario: Clip for an insight
    Given an insight cites rally 7 of Ivy's match
    When she opens its clip
    Then a clip from 2 seconds before to 1 second after the cited moment plays
```

#### FR-031 Framing check before the match
- **Description:** The user uploads one still frame before filming and gets a "court visible?" result.
- **Priority:** Could · **Release:** R2 · **Milestone:** M1 · **Status:** ready-candidate
- **Source:** DES FR-UX-13 (judgment); depends on FR-082
```gherkin
Feature: Pre-match framing check
  Scenario: Far baseline out of frame
    Given Ivy uploads a still where the far baseline is cut off
    When the check runs
    Then she is told the far baseline is not visible and how to fix the framing
```

---

## C. Match & Scoring (includes the pickleball Sport Plug-in rules)

> All rules content in this section is UNVERIFIED [DOM G1]. Scenarios carry `@needs-verification` until the coach records rule numbers in `docs/domain/rules-verified.md` [testing-strategy §3; QD-TR-07].

#### FR-040 Versioned, parameterised rules engine
- **Description:** Scoring is a pure function: (state, rally outcome, `RulesConfig`) → new state or a typed domain error. It does no I/O and uses no clock or randomness. Every rule that cannot yet be verified is a `RulesConfig` field rather than a constant. These include the target score, the win-by margin, the first-service-turn exception, rally-scoring game-point behaviour and server rotation. Each match is pinned to a `rules_version` preset and keeps it when newer presets ship. Until OQ-01 is answered the only preset is `PROVISIONAL-UNVERIFIED`; a federation-named preset such as `USAP-2026` may ship only once every row it relies on is verified (ADR 0009 rule 4, NFR-003).
- **Priority:** Must · **Release:** R1 · **Milestone:** M0 · **Status:** needs-verification (preset values)
- **Source:** QD QD-RE-01, -02, -05, §0 design principle; ENG ENG-FR-06; ddd-guidelines §4.5; [EP/ENG-17]; [DOM G1 R1]
```gherkin
@needs-verification
Feature: Rules version pinning
  Scenario: A newer rules preset ships
    Given Ivy's match was scored under preset "PROVISIONAL-UNVERIFIED"
    When a newer rules preset becomes available
    Then her score sheet still shows "PROVISIONAL-UNVERIFIED" and the same scores
  Scenario: Rally after the game is over
    Given a game has ended
    When another rally is applied to that game
    Then the rally is refused with a "game already over" message
```

#### FR-041 Side-out doubles scoring
- **Description:** Implements side-out scoring for doubles as configured by the preset: only the serving side scores, server 1 → server 2 → side-out, the game starts at 0-0-2, and a game is won at the target score by the win-by margin. The score is called as three numbers.
- **Priority:** Must · **Release:** R1 · **Milestone:** M0 · **Status:** needs-verification
- **Source:** spec §2, M0; PROD US-301; QD §2.2 SOD-01..16; [DOM G1 R2, R6] (UNVERIFIED)
```gherkin
@M0 @needs-verification
Feature: Side-out doubles scoring
  Rule: Only the serving side scores
    Scenario Outline: Score after one rally
      Given a doubles game under side-out scoring called "<before>" with side <srv> serving
      When the <winner> side wins the rally
      Then the score is called "<after>" with side <next> serving
      Examples:
        | id     | before | srv | winner    | after | next |
        | SOD-01 | 0-0-2  | A   | serving   | 1-0-2 | A    |
        | SOD-02 | 0-0-2  | A   | receiving | 0-0-1 | B    |
        | SOD-03 | 3-5-1  | A   | receiving | 3-5-2 | A    |
        | SOD-04 | 3-5-2  | A   | receiving | 5-3-1 | B    |
        | SOD-05 | 7-4-1  | A   | serving   | 8-4-1 | A    |
  Rule: A game is won at the target score by the win-by margin
    Scenario Outline: Game end
      Given a doubles game called "<before>" with side A serving
      When the <winner> side wins the rally
      Then the game is <state>
      Examples:
        | id     | before  | winner    | state           |
        | SOD-07 | 10-8-1  | serving   | won by A 11-8   |
        | SOD-08 | 10-10-1 | serving   | not over        |
        | SOD-09 | 11-10-2 | serving   | won by A 12-10  |
        | SOD-10 | 10-9-2  | receiving | not over        |
        | SOD-11 | 21-20-1 | serving   | won by A 22-20  |
```
The full table (≥ 16 SOD rows) is in QD §2.2 and is the minimum test data.

#### FR-042 Side-out singles scoring
- **Description:** Singles side-out scoring: two-number call, no server 2, and service court chosen by the parity of the server's score.
- **Priority:** Should · **Release:** R1 · **Milestone:** M0 · **Status:** needs-verification
- **Source:** spec §2 ("singles supported"); PROD US-303; QD §2.2 SOS; [DOM G1 R6] (UNVERIFIED)
```gherkin
@needs-verification
Feature: Side-out singles scoring
  Scenario Outline: Server's court by score parity
    Given a singles game where the server's score is <score>
    When the server serves
    Then the serve is expected from the <court> court
    Examples:
      | score | court |
      | 0     | right |
      | 5     | left  |
```

#### FR-043 Rally scoring option
- **Description:** Match setup offers rally scoring, labelled "provisional". It is enabled only after the coach verifies the target score, win-by, doubles server rotation, call format and the game-point rule. No rally-scoring preset ships with a guessed rotation rule.
- **Priority:** Should · **Release:** R2 · **Milestone:** M0 (engine flag), R2 (UI) · **Status:** needs-verification (blocked)
- **Source:** PROD US-302; QD §2.2 RS, Q3; DES FR-UX-20; [DOM G1 R3] (UNVERIFIED); conflict K22
```gherkin
@needs-verification
Feature: Rally scoring
  Rule: Under rally scoring every counted rally scores for its winner
    Scenario: Receiving side wins a rally
      Given a rally-scoring game at 5-5 with side A serving
      When side B wins the rally
      Then side B's score is 6
```

#### FR-044 Faults end the rally against the faulting side
- **Description:** Every fault is scored as "the faulting side lost the rally". The fault subtype (serve, NVZ, two-bounce, foot, other) affects analytics only.
- **Priority:** Must · **Release:** R1 · **Milestone:** M0 · **Status:** needs-verification
- **Source:** QD QD-RE-09, §2.2 F-01..F-06; [DOM G1 R4-R6] (UNVERIFIED)
```gherkin
@needs-verification
Feature: Fault scoring
  Rule: The fault subtype never changes the score
    Scenario Outline: Same outcome for every fault subtype
      Given a doubles game called "4-2-1" with side A serving
      When side B commits a <fault> fault
      Then the score is called "5-2-1" with side A serving
      Examples:
        | fault      |
        | two-bounce |
        | NVZ        |
        | other      |
```

#### FR-045 Match structure
- **Description:**
  - Matches are best of 1 or best of 3 games.
  - Each game records which side served first and whether the sides switched ends. Both are explicit inputs, never inferred; the UI defaults them to coach-verified values.
  - A match ends when a side has won a majority of games, and any rally after that is refused.
  - A `Game` entity sits inside the `Match` aggregate.
- **Priority:** Must · **Release:** R1 · **Milestone:** M0 · **Status:** needs-verification
- **Source:** QD X2, QD-RE-11, §2.2 "Match level"; spec §4 (data model gap)
```gherkin
@needs-verification
Feature: Match structure
  Scenario: Best of three decided in two games
    Given side A has won games 1 and 2 of a best-of-3 match
    When Ivy tries to tag another rally
    Then she is told the match is over
```

#### FR-046 Start the score sheet mid-game
- **Description:** If the video starts part-way through a game, the user declares the starting score and serving side. The system refuses states that are impossible: a server number outside 1-2, or a score that already meets the game-over condition.
- **Priority:** Must · **Release:** R1 · **Milestone:** M0 · **Status:** needs-verification
- **Source:** QD QD-RE-06, §7 F-02, SOD-13..15
```gherkin
@needs-verification
Feature: Mid-game start
  Scenario: Video begins part-way through a game
    Given Ivy declares the start as "4-6-2" with her side receiving
    When she tags the first rally as won by her side
    Then the score sheet shows "6-4-1" with her side serving
  Scenario Outline: Impossible start refused
    Given Ivy declares a start score of "<start>"
    Then she is told why it is impossible and asked to correct it
    Examples:
      | start  |
      | 12-9-1 |
      | 4-6-3  |
```

#### FR-047 Gaps and resync
- **Description:** A part of the video can be marked as a gap (missing or untagged). A gap must be followed by a user-declared resync score. The score sheet shows the gap, and analytics exclude it.
- **Priority:** Should · **Release:** R1 · **Milestone:** M0 · **Status:** ready-candidate
- **Source:** QD QD-RE-07, property P8
```gherkin
Feature: Gaps in the video
  Scenario: Camera stopped for two rallies
    Given Ivy marks a gap after rally 9 and declares the resync score "7-5-1"
    When she views the score sheet
    Then a gap row appears after rally 9 and rally 10 starts at "7-5-1"
    And her stats count no rallies inside the gap
```

#### FR-048 Score call and announcement
- **Description:** After each tagged or corrected rally the current score is shown in the coach-verified call format. It is also announced through a polite live region, e.g. "Rally 7: them. Score 4-6-1."
- **Priority:** Must · **Release:** R1 · **Milestone:** M0 · **Status:** needs-verification (call format)
- **Source:** DES FR-UX-62; QD QD-RE-04; [DOM G1 R6] (UNVERIFIED)
```gherkin
@needs-verification
Feature: Score call
  Scenario: Screen-reader user tags a rally
    Given Ivy uses a screen reader while tagging
    When she tags rally 7 as won by the other side
    Then she hears the rally number, the winner and the new score
    And her focus stays on the tagging controls
```

#### FR-049 Score sheet
- **Description:** The score sheet lists every rally with:
  - number;
  - start time;
  - server;
  - score before and after;
  - winner;
  - ending;
  - gap and conflict markers;
  - a "corrected by you" marker.

  It is a semantic table, readable at 360 px wide, and serves as the text alternative to the match video. Score before/after is computed by replaying the rules; it is never stored as an editable value.
- **Priority:** Must · **Release:** R1 · **Milestone:** M0 · **Status:** ready-candidate (rule data needs-verification)
- **Source:** spec §1 (score sheet), §4; PROD US-304; DES FR-UX-70, CD12; ENG §3.2 (score is a projection); [DPA/DESIGN-09]
```gherkin
Feature: Score sheet
  Scenario: Read the match without the video
    Given Ivy has tagged a 3-game match
    When she opens the score sheet
    Then every rally shows its number, server, score before and after, winner and ending
    And corrected rallies are marked "corrected by you" in text
```

#### FR-050 Quick Tag a rally
- **Description:** For each rally the user marks:
  - rally start and end;
  - the winning side;
  - the ending: winner, unforced error, forced error, fault, or replay;
  - optionally, the responsible player;
  - optionally, the fault subtype.

  In R1 there is no automatic segmentation, so after a tag the video continues from the end of the tagged rally and the user marks the next start. Jumping straight to the next rally's start needs automatic rally boundaries (FR-087, R2).

  The ending applies the rules engine. Forced vs unforced error is kept apart in analytics only if two labellers reach Cohen's κ ≥ 0.6 on 200 rallies. Otherwise both are reported as "error".
- **Priority:** Must · **Release:** R1 · **Milestone:** M0 · **Status:** ready-candidate
- **Source:** PROD US-401, C2; QD X3, X10; ENG ENG-FR-05; DES FR-UX-60; spec M0; conflicts K8, K9
```gherkin
Feature: Quick Tag
  Scenario: Tag a rally
    Given Ivy is watching rally 7 of her match
    When she marks the rally as won by the other side with "unforced error" by herself
    Then rally 7 shows the new score and the error is attributed to her
    And the video continues from the end of rally 7, ready to mark rally 8
  Scenario: Responsible player skipped
    Given Ivy tags rally 8 without choosing a responsible player
    When she opens her stats
    Then per-player error stats say "player not tagged in 1 rally"
```

#### FR-051 Keyboard tagging
- **Description:** Quick Tag works fully from the keyboard, using an in-app key map shown with `?`. Single-key shortcuts can be turned off or remapped. Keyboard tagging gives the same results as tapping.
- **Priority:** Must · **Release:** R1 · **Milestone:** M0 · **Status:** ready-candidate
- **Source:** PROD US-401 (keyboard scenario); DES FR-UX-61; SC 2.1.1 and 2.1.4 not fetched (judgment)
```gherkin
Feature: Keyboard tagging
  Scenario: Keyboard only
    Given Ivy uses a keyboard and no pointer
    When she tags rally 7 using keys only
    Then the score sheet is identical to tagging the same rally with taps
```

#### FR-052 Undo and correction audit
- **Description:** Every tag and correction can be undone. Each correction is stored in an append-only audit record (who, when, what field, old value, new value) and flags the value `corrected_by_user`.
- **Priority:** Must · **Release:** R1 · **Milestone:** M0 · **Status:** ready-candidate
- **Source:** PROD US-403; ENG §3.2 `Correction`; spec §4; [DPA/DESIGN-11] G9, G13, G15
```gherkin
Feature: Undo
  Scenario: Undo a correction
    Given Ivy changed rally 5's winner
    When she undoes the change
    Then the score sheet is identical to the one before her change
    And her correction history lists both the change and the undo
```

#### FR-053 Corrections replay the score and keep conflicting rallies
- **Description:** Changing rally *k* re-scores rallies *k..n* atomically. If the change ends a game earlier, or un-ends a game, the affected rallies are not dropped. They are marked "needs your decision" and the user resolves each one.
- **Priority:** Must · **Release:** R1 · **Milestone:** M0 · **Status:** needs-verification (game-end rule)
- **Source:** QD QD-RE-10, §7 F-03, §2.2 C-01..C-04; ENG ENG-FR-07; ddd-guidelines §4.1
```gherkin
@needs-verification
Feature: Correction changes the end of a game
  Scenario: Correction ends the game earlier
    Given a tagged game that side A won 12-10 after 24 rallies
    When Ivy changes rally 20 to "won by side A"
    Then the game shows as won by side A at rally 20
    And rallies 21 to 24 are listed as needing her decision, not deleted
```

#### FR-054 Show the consequences of a correction
- **Description:** Before saving a correction that changes later scores, the app says how many rallies change. After saving, it lists the stats that changed.
- **Priority:** Should · **Release:** R1 · **Milestone:** M0 · **Status:** ready-candidate
- **Source:** DES FR-UX-65; [DPA/DESIGN-11] G16, G18
```gherkin
Feature: Correction consequences
  Scenario: Correction affects later rallies
    Given Ivy is changing the winner of rally 8 of 20
    When she reviews the change before saving
    Then she is told the score of the next 12 rallies will change
```

#### FR-055 "Unofficial scoring" label
- **Description:** While any rule in the scoring path is still `needs-verification`, every score sheet is labelled "unofficial scoring (rules not yet verified)".
- **Priority:** Must · **Release:** R1 · **Milestone:** M0 · **Status:** ready-candidate
- **Source:** QD QD-QG-R3, X8; [DOM G1]; [DPA/DESIGN-11] G2
```gherkin
Feature: Unofficial scoring label
  Scenario: Rules not yet verified
    Given the active rules preset contains an unverified rule
    When Ivy opens any score sheet
    Then she sees "unofficial scoring (rules not yet verified)"
```

#### FR-056 User corrections survive re-processing
- **Description:** A value the user corrected is never overwritten when a match is re-processed with a new pipeline version.
- **Priority:** Must · **Release:** R2 · **Milestone:** M2 · **Status:** ready-candidate
- **Source:** DES CD9, NFR-TRUST-05, §11 seed; ENG ENG-FR-07; ddd-guidelines §4.8; [DPA/DESIGN-11] G14, G18
```gherkin
Feature: Corrections survive re-processing
  Rule: A user's correction is never overwritten by a new model version
    Scenario: Re-process after correction
      Given Ivy corrected rally 7's winner
      When the match is re-processed with a new model version
      Then rally 7 still shows her correction
      And she sees a summary of what changed in her stats
```

#### FR-057 "Needs your eyes" review queue
- **Description:** Calls in the lowest confidence band are listed first, ordered by score impact: rally winner, server, fault-by side, then stat impact. Each item shows the video moment, the call and its band in words, plus one-tap "Correct" and "Change to…" with the 2-3 most likely alternatives.
- **Priority:** Should · **Release:** R2 (rally-level calls); Must in R3 · **Milestone:** M2/M3 · **Status:** ready-candidate
- **Source:** PROD US-902; DES FR-UX-63, CD3, §11 seed; [DPA/DESIGN-11] G2, G9
```gherkin
Feature: Review queue
  Rule: Low-confidence calls that affect the score come first
    Scenario: Review queue order
      Given the analysis has 3 "Check this" calls, one of them a rally winner
      When Ivy opens "Needs your eyes"
      Then the rally-winner call is listed first
      And each call shows its band in words
```

#### FR-058 Automatic scoring with confidence
- **Description:** The pipeline infers each rally's winner side and ending, with a calibrated confidence band, and feeds the rules engine through the anticorruption layer.
- **Priority:** Could (MVP); Must for R3 · **Release:** R3 · **Milestone:** M3 · **Status:** ready-candidate (targets per ADR 0004)
- **Source:** spec §2, M3; PROD US-901; ENG §5.4; QD X9
```gherkin
Feature: Automatic scoring
  Scenario: Confident rally outcome
    Given the system called rally 4 "won by side B" in band "Sure"
    When Ivy opens the score sheet
    Then rally 4 shows side B as winner with "Sure" in text
    And it is not in the review queue
```

#### FR-059 "Who is who" identity assignment
- **Description:** In doubles the user taps each of the 4 detected players once and assigns a participant slot, with exactly 2 per side enforced. A swap mid-match is fixed with one "swap these two from here on" action. There is no face recognition.
- **Priority:** Should · **Release:** R2 · **Milestone:** M1 · **Status:** ready-candidate
- **Source:** PROD US-702; ENG ENG-FR-04; DES FR-UX-66; spec §8; [DOM G4 P4]
```gherkin
Feature: Identity assignment
  Scenario: Three players assigned to one side
    Given Ivy is assigning players in a doubles match
    When she assigns a third player to side A
    Then she is told each side must have exactly two players
  Scenario: Fix a swap
    Given the tracker swapped Ivy and her partner from rally 9
    When she applies "swap these two from here on" at rally 9
    Then rallies 9 onward attribute shots to the correct players
```

#### FR-060 Correction reason
- **Description:** When correcting, the user may give an optional single-tap reason: "ball hidden", "wrong player", "wrong shot type" or "other". It never blocks saving.
- **Priority:** Could · **Release:** R2 · **Milestone:** M3 · **Status:** ready-candidate
- **Source:** DES FR-UX-67; [DPA/DESIGN-11] G13, G15
```gherkin
Feature: Correction reason
  Scenario: Save without a reason
    Given Ivy is correcting a rally winner
    When she saves without choosing a reason
    Then the correction is saved
```

#### FR-061 Full rally timeline with shots
- **Description:** A vertical rally list. Each rally expands to show its shots with type facets, confidence band and corrected marker.
- **Priority:** Could · **Release:** R3 · **Milestone:** M3 · **Status:** ready-candidate
- **Source:** DES FR-UX-64; spec §3 "review timeline"; [DPA/DESIGN-05]
```gherkin
Feature: Rally timeline
  Scenario: Expand a rally
    Given rally 3 has 9 detected shots
    When Ivy expands rally 3
    Then she sees 9 shots in order, each with its hitter, type and band
```

---

## D. Vision Analysis

#### FR-080 Analysis job lifecycle
- **Description:** Analysis runs as a job per match and pipeline version. Each stage either commits its full result or nothing. A failed stage marks the job failed, or degrades it to an explicit lower analysis level (FR-026). Analysis cannot start until the upload is complete and checksum-verified.
- **Priority:** Should · **Release:** R2 (the queue itself exists in R1 for media probing) · **Milestone:** M0/M2 · **Status:** ready-candidate
- **Source:** ENG §1.1-1.2; spec §3; [AQS/OPS-02]; [AQS/SEC-12]; [AQS/SEC-07] 2.3.1
```gherkin
Feature: Analysis job lifecycle
  Scenario: Stage fails
    Given the ball-tracking stage fails for Ivy's match
    When the job finishes
    Then no partial ball or shot results are shown
    And the match shows its highest completed analysis level
  Scenario: Incomplete upload
    Given Ivy's upload is at 80%
    Then no analysis starts for that match
```

#### FR-081 Media probe and normalisation
- **Description:** Every upload is probed for container, codec, fps, variable frame rate, duration and audio (R1). For automatic analysis it is then normalised: constant frame rate, a 16 kHz mono audio track and a 720p review video (R2).
- **Priority:** Must (probe, R1); Should (normalise, R2) · **Release:** R1/R2 · **Milestone:** M0/M2 · **Status:** ready-candidate
- **Source:** ENG §1.2 stages 0-1, RISK-14; [AQS/SEC-02]
```gherkin
Feature: Media normalisation
  Scenario: Variable frame rate phone video
    Given Ivy uploads a video recorded with a variable frame rate
    When it is prepared for analysis
    Then the review video plays in sync with its audio at every rally
```

#### FR-082 Court calibration without dragging
- **Description:** The system proposes court keypoints and overlays the court model on a frame. The user chooses "Looks right" or "Adjust". In Adjust, the user can place any 4 or more named keypoints, such as corners, NVZ line ends, centre-line ends and net posts. They can tap to select, tap to place, and nudge with buttons or arrow keys; dragging is optional. The fit quality is shown in words. Continue is disabled, with the reason stated, while fewer than 4 points are placed.
- **Priority:** Should · **Release:** R2 · **Milestone:** M1 · **Status:** ready-candidate
- **Source:** spec §3, M1; PROD US-701; ENG ENG-FR-03; DES FR-UX-50..54, CD1, CD2, §11 seed; [DPA/DESIGN-05]; [DOM G6 H1-H2]; [DOM/CV-12]; conflict K18
```gherkin
Feature: Court calibration without dragging
  Rule: Every calibration point can be placed with taps or keys only
    Scenario: Place a point by tapping
      Given the automatic court fit is marked "Check the far baseline"
      When Ivy selects "Far-left corner" and taps its position on the frame
      Then the court lines redraw through the new point
      And the fit quality is shown in words
    Scenario: Too few points
      Given Ivy has placed 3 points
      Then she cannot continue and is told at least 4 points are needed
```

#### FR-083 Player detection and tracking
- **Description:** On-court players are detected and tracked through the match. Their foot positions are mapped to court coordinates, using ground-plane points only. Players on adjacent courts are excluded.
- **Priority:** Should · **Release:** R2 · **Milestone:** M1 · **Status:** ready-candidate (licence decision ENG SPIKE-01, OQ-12)
- **Source:** spec §3 step 2, M1; ENG §1.2 stage 4; [DOM G4 P1-P4]; [DOM/CV-04]; [DOM/CV-05]; [DOM/CV-12]
```gherkin
Feature: Player tracking
  Scenario: Doubles match on a multi-court venue
    Given Ivy's video shows her court and part of the next court
    When tracking finishes
    Then exactly four players are tracked on her court, two per side
```

#### FR-084 Ball tracking with visibility
- **Description:** The ball is tracked frame by frame with an explicit visible / not-visible flag. A hidden ball is "not visible", never a guessed position. Trajectory overlays show gaps, labelled "ball hidden", where the ball is not visible.
- **Priority:** Should · **Release:** R2 · **Milestone:** M2 · **Status:** ready-candidate
- **Source:** spec §3 step 4, M2; ENG §1.2 stage 7; DES CD6; [DOM G3 B1-B4]; [DOM/CV-01]
```gherkin
Feature: Ball visibility
  Scenario: Ball hidden behind a player
    Given the ball is hidden for 12 frames during rally 5
    When Ivy views the trajectory overlay for rally 5
    Then that segment is drawn as a gap labelled "ball hidden"
```

#### FR-085 Hit detection from video and audio
- **Description:** Hits are detected by fusing an audio onset with a visual trajectory change and a nearby player. A hit is never created from audio alone. Each hit has a time, a participant and a confidence.
- **Priority:** Should · **Release:** R2 · **Milestone:** M2 · **Status:** ready-candidate
- **Source:** spec §3 step 5, "Why audio matters"; ENG §5.2 item 6; PROD US-802; [DOM G7 A1-A2]; [DOM/CV-14]
```gherkin
Feature: Hit detection
  Scenario: Paddle pop from the next court
    Given the audio has a paddle pop while the ball on Ivy's court is in flight away from all players
    When hits are detected
    Then no hit is recorded at that moment
```

#### FR-086 Bounce detection and landing position
- **Description:** Bounces are detected as a separate step on the ball trajectory. Landing positions are mapped to court coordinates, since a bounce is on the court plane.
- **Priority:** Should · **Release:** R2 · **Milestone:** M2 · **Status:** ready-candidate
- **Source:** spec §3 step 5; ENG §5.1; [DOM G3 B5]; [DOM/CV-19]; [DOM/CV-12]
```gherkin
Feature: Bounce detection
  Scenario: Serve bounce
    Given a serve bounces in the service court during rally 2
    When analysis finishes
    Then rally 2's serve shows a landing position inside that service court
```

#### FR-087 Automatic rally segmentation
- **Description:** Rally start and end times are detected automatically and pre-fill Quick Tag. The user then confirms winner and ending. Automatic scoring of outcomes comes later (FR-058).
- **Priority:** Should · **Release:** R2 · **Milestone:** M2 · **Status:** ready-candidate
- **Source:** spec §3 step 6, M2; PROD US-801, R2 exit ("Quick Tag effort drops ≥ 50%"); ENG §1.2 stage 10
```gherkin
Feature: Automatic rally segmentation
  Scenario: Pre-filled rally boundaries
    Given automatic analysis found 26 rallies in game 1
    When Ivy opens Quick Tag for game 1
    Then 26 rallies are listed with start and end times already set
    And she only needs to tag the winner and ending of each
```

#### FR-088 Shot classification (faceted)
- **Description:** Shots are labelled on separate facets:
  - **position:** serve, return, third, fourth or later. This is derived by rule, not classified.
  - **contact:** groundstroke or volley.
  - **trajectory:** drive, drop, dink or lob.
  - **intent:** neutral, speed-up or reset.
  - **technique:** none, erne or ATP.

  Position and trajectory come first; intent and technique come later. No facet ships before its definition is coach-verified and two labellers agree at κ ≥ 0.7.
- **Priority:** Could · **Release:** R3 · **Milestone:** M3 · **Status:** needs-verification (definitions [DOM G2])
- **Source:** spec §3 step 7; QD X4, QD-TX-01..04; ENG §5.5; [DOM/CV-18]; conflict K10
```gherkin
@needs-verification
Feature: Faceted shot labels
  Scenario: A volley that is also a dink
    Given a shot is played at the kitchen line before the ball bounces and lands softly in the opponent's NVZ
    When it is classified
    Then its contact is "volley" and its trajectory is "dink"
```

#### FR-089 Re-processing on a new pipeline version
- **Description:** A match can be re-run on a new pipeline version. Prior results stay visible until the new run succeeds. Then the user sees a "what changed" summary with before → after values for each affected metric.
- **Priority:** Should · **Release:** R2 · **Milestone:** M2 · **Status:** ready-candidate (depends on video retention, OQ-07)
- **Source:** ENG ENG-FR-08; PROD US-903; DES CD9; spec §4 (`Event` kept for re-processing); [DPA/DESIGN-11] G14, G18
```gherkin
Feature: Re-processing
  Scenario: New run fails
    Given Ivy's match has results from pipeline version 3
    When a re-run on version 4 fails
    Then she still sees her version 3 results unchanged
```

#### FR-090 Confidence on every automatic value
- **Description:** Every automatic value carries a confidence, which the API exposes. The UI shows it as a word band ("Sure", "Likely", "Check this"). A band is used only if it is backed by measured gold-set accuracy for the current pipeline version (NFR-008). The raw % appears only in a details view. High-confidence calls show a quiet indicator.
- **Priority:** Should · **Release:** R2 · **Milestone:** M2 · **Status:** needs-PO-decision (OQ-10)
- **Source:** spec §2; ENG ENG-FR-09; DES CD3, CD4; QD QD-TR-10; [DPA/DESIGN-11] G2
```gherkin
Feature: Confidence bands
  Scenario: Band explained
    Given a rally boundary is shown with band "Likely"
    When Ivy opens "how we know"
    Then she sees how often "Likely" calls were right in testing
```

---

## E. Analytics

#### FR-100 Starter stats from Quick Tag
- **Description:** For each side, and per player where `responsible_player` was tagged, the app computes:
  - AN-01 serve rally win %
  - AN-02 side-out %
  - AN-03 points per service turn
  - AN-04 unforced errors per game
  - AN-05 serve fault %
  - AN-06 longest run and run histogram
  - AN-07 rally-ending mix

  The definitions are in QD §3.2 and are (judgment) by the coach until sourced.
- **Priority:** Must · **Release:** R1 · **Milestone:** M4 subset · **Status:** needs-verification (definitions, coach review)
- **Source:** spec §5 "Score and flow", §7 M4; PROD US-501; QD §3.2; conflict K8
```gherkin
Feature: Starter stats
  Scenario: Serve rally win %
    Given Ivy's side served 40 rallies and won 22 of them
    When she opens her stats
    Then "serve rally win %" shows 55% with "n = 40"
```

#### FR-101 Sample size and uncertainty on every metric
- **Description:** Every metric shows its sample size n. Proportion metrics also show a 95% Wilson interval and are flagged "low sample" when n < 20 or the interval is wider than 30 percentage points. Count metrics are flagged when fewer than 2 games are in scope. Flagged metrics are visually de-emphasised but never hidden, and the flag is in text. The thresholds live in config.
- **Priority:** Must · **Release:** R1 · **Milestone:** M0/M4 · **Status:** ready-candidate
- **Source:** spec §5 ("marks the metric that way instead of hiding it"); QD X5, QD-AN-04, §7 F-04; PROD US-501; DES FR-UX-71; [DPA/DESIGN-11] G2, G10; conflict K6; ADR 0005
```gherkin
Feature: Metrics show their uncertainty
  Rule: Small samples are flagged, never hidden
    Scenario Outline: Low-sample flag
      Given Ivy received serve in <n> rallies and won <won>
      When she opens her stats
      Then "side-out %" shows <pct> with "n = <n>" and low-sample label "<flag>"
      Examples:
        | n  | won | pct | flag |
        | 8  | 4   | 50% | yes  |
        | 40 | 22  | 55% | no   |
```

#### FR-102 Versioned metric dictionary
- **Description:** Each metric is a versioned dictionary entry. The entry gives the formula in domain terms, the unit, the data level, the minimum sample, the owner (domain coach), a status (draft, coach-reviewed or verified) and a source or "(judgment)". Users see only metrics with status coach-reviewed or verified. Every "How is this measured?" link shows the entry's plain-language definition.
- **Priority:** Must · **Release:** R1 · **Milestone:** M0 · **Status:** ready-candidate
- **Source:** QD QD-AN-01, QD-AN-03, QD-QG-R4; DES FR-UX-71; ENG §3.2 `metric_def_version`
```gherkin
Feature: Metric dictionary
  Scenario: Draft metric hidden
    Given metric AN-05 has status "draft"
    When Ivy opens her stats
    Then AN-05 is not shown
  Scenario: Definition shown
    Given AN-02 is coach-reviewed
    When Ivy opens "How is this measured?" on side-out %
    Then she sees its definition in plain words
```

#### FR-103 "Show me" evidence for every metric
- **Description:** Every metric card links to the rallies behind it: up to 10, with "see all n". Each opens at its video moment (FR-027).
- **Priority:** Must · **Release:** R1 · **Milestone:** M0 · **Status:** ready-candidate
- **Source:** spec §6 ("players trust what they can see"); DES FR-UX-71, NFR-TRUST-03, principle 1; [DPA/DESIGN-11] G11
```gherkin
Feature: Evidence behind a metric
  Scenario: Show me the errors
    Given Ivy's stats show 6 unforced errors in game 2
    When she opens "Show me" on that metric
    Then she sees the 6 rallies, each with a link that plays it
```

#### FR-104 Trends across matches
- **Description:** Each starter stat is shown over the last 5 matches, with n per point. A change is labelled "too few rallies to tell" unless both samples pass the low-sample rule.
- **Priority:** Should · **Release:** R2 · **Milestone:** M4 subset · **Status:** ready-candidate
- **Source:** PROD US-502; DES FR-UX-74; spec §4 `MetricSnapshot`; QD X5
```gherkin
Feature: Trends
  Scenario: Small samples
    Given Ivy's last two matches have 12 and 9 served rallies
    When she views the trend for serve rally win %
    Then the change between them is labelled "too few rallies to tell"
```

#### FR-105 Team-relative court frame
- **Description:** All spatial data is stored in a team-relative frame (own baseline = 0) and normalised per game using the end-switch flag. Only ground-plane points (feet, bounces) have court positions.
- **Priority:** Should · **Release:** R2 · **Milestone:** M1 · **Status:** needs-verification (end switching)
- **Source:** QD X11, QD-AN-05, QD-TR-09; DES CD5; [DOM G6 H1]; [DOM/CV-12]
```gherkin
@needs-verification
Feature: Team-relative positions
  Scenario: Players change ends between games
    Given Ivy played game 1 from the near end and game 2 from the far end
    When she views her position heatmap for the match
    Then positions from both games are shown relative to her own baseline
```

#### FR-106 Player heatmaps and partner spacing
- **Description:** Per-player position heatmaps use at most 5 binned levels, each with a printed value. They come with AN-16, "middle left open": the share of rally time where the lateral gap between partners is more than 50% of court width.
- **Priority:** Should · **Release:** R2 · **Milestone:** M1 · **Status:** needs-verification (AN-16 definition)
- **Source:** spec §5 "Positioning", M1 Done-when; QD §3.2 AN-16; DES FR-UX-73; [DPA/DESIGN-04]; conflict K11
```gherkin
Feature: Player heatmap
  Scenario: Heatmap readable without colour
    Given Ivy has a tracked doubles match
    When she opens her position heatmap
    Then each court zone shows a printed value as well as a colour
```

#### FR-107 Shot-level analytics
- **Description:** The shot-level metrics:
  - AN-08 return depth
  - AN-09 third-shot mix
  - AN-10 third-shot drop success
  - AN-11 arrival at the NVZ
  - AN-12 lost in transition
  - AN-13 dink battle stats
  - AN-14 errors by shot facet × zone

  The definitions are in QD §3.2.
- **Priority:** Could · **Release:** R3 · **Milestone:** M4 · **Status:** needs-verification (definitions [DOM G2])
- **Source:** spec §5; QD §3.2; PROD E10; conflict K11
```gherkin
@needs-verification
Feature: Third-shot drop success
  Scenario: Successful drop
    Given a third shot classified as a drop bounces in the opponent's NVZ
    And the serving side does not lose the rally within the next 2 shots
    When analytics run
    Then that drop counts as a success
```

#### FR-108 Pattern n-grams
- **Description:** Shot-facet sequences of length 3-5 with at least 10 occurrences, ranked by rally win rate with a Wilson interval.
- **Priority:** Could · **Release:** R3 · **Milestone:** M4 · **Status:** needs-verification
- **Source:** spec §5 "Patterns"; QD §3.2 AN-15
```gherkin
Feature: Patterns
  Scenario: Rare pattern excluded
    Given a 4-shot pattern occurred 7 times in Ivy's matches
    When she views her patterns
    Then that pattern is not ranked
```

#### FR-109 Attribution conservation
- **Description:** For each game, the rallies lost that are attributed to weakness categories, plus those marked "unattributed", equal the total rallies lost. This is split into rallies lost on serve and on receive. The invariant is checked on every computation.
- **Priority:** Must · **Release:** R1 · **Milestone:** M0 · **Status:** ready-candidate
- **Source:** QD QD-AN-00, X1; ADR 0003
```gherkin
Feature: Attribution conservation
  Scenario: Every lost rally is accounted for once
    Given side A lost 14 rallies in game 1, 6 on serve and 8 on receive
    When weaknesses are attributed
    Then the attributed and unattributed rallies on serve total 6
    And on receive they total 8
```

#### FR-110 Opponent scouting report
- **Description:** Opponent tendencies merged across at least 2 matches against the same opponent. Each tendency needs n ≥ 15 events (judgment) before it is stated as fact.
- **Priority:** Won't (this MVP) · **Release:** Later · **Milestone:** M6 · **Status:** deferred
- **Source:** spec §1, §5, M6; PROD C5, E12
```gherkin
Feature: Scouting (deferred)
  Scenario: Low-sample tendency
    Given an opponent's backhand speed-up tendency has 9 events
    When Carlos views the scouting report
    Then the tendency is labelled "low sample" and drives no plan
```

---

## F. Coaching

#### FR-120 Rank weaknesses by rallies lost
- **Description:** Weaknesses are ranked by rallies lost per game attributable to each, split into lost on serve and lost on receive. Points conceded are shown separately. In R1 attribution uses Quick Tag ending types and the responsible player.
- **Priority:** Must · **Release:** R1 · **Milestone:** M5 subset · **Status:** needs-PO-decision (OQ-08); needs-verification (side-out rule)
- **Source:** spec §6 step 1 (changed); QD X1; PROD US-601; conflict K3; ADR 0003
```gherkin
@needs-verification
Feature: Weakness ranking
  Scenario: Serving errors are not undercounted
    Given Ivy lost 10 rallies on serve to her unforced errors and 4 rallies on receive to serve faults
    When her weaknesses are ranked
    Then "unforced errors" ranks above "serve faults"
    And each weakness shows rallies lost on serve and on receive
```

#### FR-121 Rules-only general training plan
- **Description:** From the top 3 weaknesses, a deterministic workflow builds a 2-week plan (the spec allows 2-4). The plan must:
  - fit the player's stated time per session and per week;
  - fit their number of players and equipment;
  - start each session with a warm-up (judgment);
  - give no drill more than 40% of a session (judgment);
  - use only coach-reviewed library drills.
- **Priority:** Must · **Release:** R1 · **Milestone:** M5 subset · **Status:** ready-candidate (needs FR-141 content)
- **Source:** spec §2, §6; PROD US-601, C1, C10; QD QD-PL-01..03, §7 F-06; [DPA/AI-01]; conflict K2
```gherkin
Feature: Rules-only training plan
  Rule: Plans respect the player's constraints
    Scenario: Solo player with 30 minutes
      Given Ivy practises alone for 30 minutes per session without a ball machine
      When she generates a plan
      Then every session lasts at most 30 minutes
      And every drill can be done by one player without a ball machine
    Scenario: Weekly time
      Given Ivy has 3 practice hours a week
      When she generates a 2-week plan
      Then each week's sessions total at most 3 hours
```

#### FR-122 Every drill explains why
- **Description:** Each drill assignment cites (metric, value, n, evidence rallies). Its "why" text names the metric and value and links to the rallies.
- **Priority:** Must · **Release:** R1 · **Milestone:** M5 subset · **Status:** ready-candidate
- **Source:** spec §2, §6 step 2; QD QD-PL-04; DES FR-UX-80, FR-UX-81; [DPA/DESIGN-11] G11
```gherkin
Feature: Drill rationale
  Scenario: Why this drill
    Given Ivy's plan includes a serve-consistency drill
    When she opens it
    Then she sees the metric it targets, her value and its n
    And a link to the rallies behind that value
```

#### FR-123 Plan built on limited data says so
- **Description:** If the top weakness is low-sample, the plan says it is based on limited data and states how many rallies it used.
- **Priority:** Must · **Release:** R1 · **Milestone:** M5 subset · **Status:** ready-candidate
- **Source:** PROD US-601; QD QD-PL-06; DES §4 plan states
```gherkin
Feature: Limited-data plan
  Scenario: One short match
    Given Ivy has 1 tagged match with 12 rallies
    When she asks for a plan
    Then she sees that the plan is based on limited data from 12 rallies
```

#### FR-124 Mark sessions done and swap drills
- **Description:** Sessions can be checked off; marking done works offline and syncs later. "Not for me", with an optional reason, swaps in an alternative library drill that meets the same constraints.
- **Priority:** Should · **Release:** R1 · **Milestone:** M5 subset · **Status:** ready-candidate
- **Source:** PROD US-603; DES FR-UX-81, §4; [DPA/DESIGN-11] G8, G15
```gherkin
Feature: Plan follow-through
  Scenario: Swap a drill
    Given Ivy's session includes a drill she cannot do
    When she chooses "Not for me"
    Then a different library drill targeting the same metric replaces it
    And the session still fits her time limit
```

#### FR-125 LLM-written ordering and explanation, validated
- **Description:** An LLM orders the drills and writes the "why" in one workflow step: rules rank the weaknesses, a tool returns candidate library drills, the LLM selects and explains, then a validator checks the result. The plan is rejected if the output:
  - names a drill or version that is not in the pinned library;
  - cites a metric that does not exist for the player;
  - breaks the plan constraints (FR-121);
  - lacks a citation.

  On rejection the step is retried once, and then falls back to the rules-only plan. The user never sees an LLM error state.
- **Priority:** Should · **Release:** R2 · **Milestone:** M5 · **Status:** ready-candidate (eval set first)
- **Source:** spec §2, §6; PROD US-1101, C10; ENG ENG-FR-11; QD QD-PL-05, §7 F-06; DES FR-UX-82; [AQS/SEC-08]; [DPA/AI-01]; [DOM/CV-20]
```gherkin
Feature: Validated LLM plan
  Scenario: Coaching model proposes a drill that is not in the library
    Given the coaching model answers with drill "pb.unknown.drill"
    When the plan is validated
    Then the plan is not saved from that answer
    And Ivy receives the rules-only plan with the same constraints
```

#### FR-126 AI-text label and global control
- **Description:** A "Written by AI from your stats" label is shown when the LLM wrote the "why". A setting turns AI-written explanations off, so only rules-only text is used.
- **Priority:** Should · **Release:** R2 · **Milestone:** M5 · **Status:** ready-candidate
- **Source:** DES FR-UX-82, FR-UX-84, NFR-TRUST-06; [DPA/DESIGN-11] G1, G17
```gherkin
Feature: AI explanation controls
  Scenario: AI explanations turned off
    Given Ivy turned off AI-written explanations
    When she generates a plan
    Then no drill shows "Written by AI"
```

#### FR-127 Plan efficacy without over-claiming
- **Description:** After the next uploaded match, each targeted metric shows before → after with n. "Improved" or "declined" is shown only when both windows have n ≥ 20 and their 95% Wilson intervals do not overlap. Otherwise the app says "not enough data yet (n = x of 20)".
- **Priority:** Should · **Release:** R2 · **Milestone:** M5 · **Status:** ready-candidate
- **Source:** spec §6 step 4; PROD US-1102; QD X6, §7 F-07; DES FR-UX-83; conflict K7; ADR 0005
```gherkin
Feature: Plan follow-up does not over-claim
  Scenario: Too little data after one match
    Given Ivy's plan targeted "serve fault %" with 18 serves before the plan
    And her next match has 9 serves
    When the follow-up is shown
    Then it says "not enough data yet (n = 9 of 20)" instead of improved or declined
```

#### FR-128 Opponent-specific plan
- **Description:** 1-3 sessions before a known match, built from a scouting report.
- **Priority:** Won't (this MVP) · **Release:** Later · **Milestone:** M6 · **Status:** deferred
- **Source:** spec §6 step 3, M6; PROD E12
```gherkin
Feature: Opponent plan (deferred)
  Scenario: Plan from scouting
    Given Carlos has a scouting report on "Lefty" with no low-sample tendencies
    When he asks for an opponent plan
    Then he gets 1 to 3 sessions that each cite a tendency
```

---

## G. Drill Library

#### FR-140 Drill schema, lint and immutability
- **Description:** One file per drill, validated in CI against a JSON Schema. The fields are defined in QD-DR-01: id, version, skills, target metrics (≥ 1), level range, duration, players, needs, equipment, setup, measurable success criterion, progressions and regressions, safety notes, source or coach rationale, and review status.

  The CI lint fails when any of these holds:
  - a target metric is unknown;
  - a progression or regression is unknown or forms a cycle;
  - the duration is out of range (more than 45 min);
  - the success criterion has no number;
  - the drill has neither a source nor a rationale.

  Drills are deprecated, never deleted. Edits bump the version.
- **Priority:** Must · **Release:** R1 · **Milestone:** M5 subset · **Status:** ready-candidate
- **Source:** spec §3 `drillLibrary`, §2 ("does not invent drills"); QD QD-DR-01..03, §7 F-08
```gherkin
Feature: Drill library integrity
  Scenario: A drill targets an unknown metric
    Given a drill file that targets metric "AN-99"
    When the library is validated
    Then validation fails naming the drill and the unknown metric
  Scenario: Plan keeps a deprecated drill
    Given Ivy's plan uses drill version 2, which was later deprecated
    When she opens the plan
    Then the drill still shows its version 2 content
```

#### FR-141 Starter drill library by coverage
- **Description:** The R1 library has at least 20 coach-reviewed drills. They must cover every metric R1 can target, at every level, with at least 2 drills per cell: at least 1 for ≤ 2 players and at least 1 that needs no ball machine. The CI job prints the coverage matrix and fails on empty cells in scope. The spec's "~80 drills" (M5) is an expected outcome, not a criterion. Drills involving retreating lobs, diving or high-intensity footwork carry safety notes.
- **Priority:** Must · **Release:** R1 · **Milestone:** M5 subset · **Status:** needs-verification (drill content [DOM G2])
- **Source:** spec M5; PROD US-602; QD X7, QD-DR-04, QD-DR-05
```gherkin
@needs-verification
Feature: Drill coverage
  Scenario: Missing coverage cell
    Given no reviewed drill targets AN-05 for beginners with 2 or fewer players
    When the coverage check runs
    Then it fails and names the empty cell
```

---

## H. Dataset & Labelling (proposed context, ENG §2 C2)

#### FR-150 Full Tag labelling tool (internal)
- **Description:** An internal mode with frame stepping and tags for hit, bounce, hitter, shot facets, rally boundaries and outcome. Export uses the gold-set format. It is only available to the labeller role and only for matches with training consent (FR-009).
- **Priority:** Must · **Release:** R1 · **Milestone:** M0 · **Status:** ready-candidate (consent: OQ-06)
- **Source:** spec §7 M0 note, §8 "Training data"; PROD US-402, PER-5; ENG §5.2 item 3; [DOM G8 E3-E4]
```gherkin
Feature: Full Tag
  Scenario: Labeller tags a hit
    Given a labeller is stepping frame by frame through a consented match
    When they tag a hit by player B1 at frame 18,402
    Then the exported label file contains that hit with its frame and player
  Scenario: Player cannot open Full Tag
    Given Ivy has a normal player account
    Then the Full Tag mode is not available to her
```

#### FR-151 Frozen, versioned gold sets
- **Description:** Each gold set has a manifest: id, version, sha256 per file, rules and metric-dictionary versions, labeller roles, inter-labeller κ, licence, consent status and split. Sets are frozen per sprint. Changing a frozen set needs an ADR. Vision sets are split by venue, with at least 3 venues held out.
- **Priority:** Must · **Release:** R1 · **Milestone:** M0 · **Status:** ready-candidate
- **Source:** QD §8; ENG §5.3; testing-strategy §6; [EP/ENG-27]; [EP/ENG-28]; [DOM/CV-09] (licence: SportsMOT evaluation only)
```gherkin
Feature: Gold set integrity
  Scenario: Gold file edited
    Given gold set GS-3 v2 is frozen
    When any file in it changes without a new version
    Then the evaluation run fails and names the changed file
```

---

## I. Usage & Cost (cross-cutting)

#### FR-160 Upload and job rate limits
- **Description:** Each user has a storage quota (the size is a PO decision) and at most 10 job creations per hour (judgment). A user over a limit gets a clear message stating when they can continue.
- **Priority:** Must · **Release:** R1 · **Milestone:** M0 · **Status:** needs-PO-decision (OQ-13)
- **Source:** PROD E15; ENG NFR-COST-05, NFR-SEC-06; [AQS/SEC-10]; [AQS/SEC-07] 2.4.1; [AQS/SEC-02] 5.2.4
```gherkin
Feature: Rate limits
  Scenario: Too many uploads
    Given Ivy has created 10 matches in the last hour
    When she starts another
    Then she is told she can start a new match after a stated time
```

#### FR-161 Monthly analysis quota
- **Description:** Each plan tier has a monthly quota of analysed match-minutes. The R2 placeholder is 180 min (judgment, PO to set). When the quota is used, new videos are stored but not analysed, the manual tagging path stays available, and the user sees when the quota resets.
- **Priority:** Must · **Release:** R2 · **Milestone:** M2 · **Status:** needs-PO-decision (OQ-13, OQ-14)
- **Source:** PROD US-1501; ENG NFR-COST-05; [AQS/SEC-10]
```gherkin
Feature: Analysis quota
  Rule: Each plan tier has a monthly analysed-minutes quota
    Scenario: Quota reached
      Given Ivy has used all her analysed minutes this month
      When she uploads another match
      Then the video is stored but not analysed automatically
      And she can still Quick Tag it
      And she sees when her quota resets
```

#### FR-162 Pricing fake door
- **Description:** A pricing page with 3 price points records "start trial" clicks. No payment is taken.
- **Priority:** Could · **Release:** R1 · **Milestone:** — · **Status:** needs-PO-decision (OQ-14)
- **Source:** PROD MA-1, §12 ("payments implementation: fake-door only")
```gherkin
Feature: Pricing fake door
  Scenario: Click a paid tier
    Given Ivy opens the pricing page
    When she chooses "start trial" on a paid tier
    Then she is told paid plans are not available yet
    And no payment details are requested
```

---

## J. Explicit non-goals for the MVP (Won't)

These are recorded so nobody builds them by accident. Each source agrees.

| Item | Why | Source |
|---|---|---|
| Live mode (stream ingest, live score) | Spec M7. Reuses the pipeline later. No streaming abstractions now [AQS/ENG-04] | spec §7; PROD §12; ENG §1.1 |
| Opponent profiles, scouting and opponent plans (FR-012, FR-110, FR-128) | Privacy gate, plus low samples for amateurs | PROD C5, C6; spec M6 |
| Coach multi-player view | Spec §9 open question | PROD E14 |
| Sharing and public links | Private by default (spec §8). No share surface in the MVP | PROD §12; DES FR-UX-100 |
| Sports other than pickleball | The plug-in interface is designed for them (NFR-082), but none ships | spec §3 |
| Native mobile app | PWA first (spec §3). Revisit after ENG SPIKE-06 | spec §3; DES OQ 6 |
| Face recognition or biometric templates | **Never**, not only in the MVP | spec §8; ENG NFR-PRIV-03 |
| "Height over the net" | Not measurable from a ground-plane homography [DOM/CV-12] | ENG §0.5; DES CD5; conflict K19 |
| Payments | Fake door only (FR-162) | PROD §12 |

## K. Counts

83 FRs in total. Counts are computed from the `Priority` lines above.

| Priority | Count | IDs |
|---|---|---|
| Must | 42 (40 in R1, 2 in R2: FR-056, FR-161) | FR-001, 002, 003, 005, 006, 007, 011, 020, 021, 022, 023, 024, 027, 040, 041, 044, 045, 046, 048, 049, 050, 051, 052, 053, 055, 056, 081, 100, 101, 102, 103, 109, 120, 121, 122, 123, 140, 141, 150, 151, 160, 161 |
| Should | 28 | FR-004, 008, 009, 025, 026, 029, 042, 043, 047, 054, 057, 059, 080, 082, 083, 084, 085, 086, 087, 089, 090, 104, 105, 106, 124, 125, 126, 127 |
| Could | 10 | FR-010, 030, 031, 058, 060, 061, 088, 107, 108, 162 |
| Won't (this MVP) | 3 | FR-012, 110, 128 |

**Readiness:** 18 FRs are `needs-verification` (FR-049 only for its rule data), i.e. not Ready until the coach records the 2026 rulebook numbers or the coaching sources. 11 of those are R1 Musts: FR-040, 041, 044, 045, 046, 048, 053, 100, 120, 141, and the rule data in FR-049. **R1 therefore cannot reach "official scoring" until OQ-01 is answered.** It can still ship labelled "unofficial scoring" (FR-055).
