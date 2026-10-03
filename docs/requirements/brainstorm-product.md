# Requirements Brainstorm: Product and Business Analysis View

- **Status:** Draft for discussion (input to `functional.md`, `non-functional.md`, `backlog.md`)
- **Date:** 2026-10-03
- **Authors:** product-manager and business-analyst agents
- **Inputs read:** `docs/specs/2026-10-02-racket-analytics-design.md` (the "spec"), `.claude/agents/product-manager.md`, `.claude/agents/business-analyst.md`, `docs/research/*.md`, `docs/process/*.md`
- **Citation convention:** `<file>/<ID>` as in `docs/process/working-agreement.md` §0 (EP, AQS, DPA, DOM). Anything not backed by a verified source is labelled **(judgment)**.

## 0. Evidence caveats that shape this whole document

1. **No pickleball rule is verified.** Every rule (side-out scoring, 0-0-2 start, win by 2, two-bounce, NVZ) is UNVERIFIED [DOM G1, R1-R6]. Any story whose acceptance criteria depend on a rule is marked `needs-verification` and is **not Ready** [process/definition-of-ready.md, "Domain truth"].
2. **No coaching source is verified** [DOM G2, Gaps 2]. Drill content and shot definitions are (judgment) until the domain coach records sources.
3. **Competitor facts are unverified.** PB Vision and SwingVision reportedly already produce pickleball stats from one phone [DOM/DOMAIN-06..08, unverified snippets]. Open-source pickleball CV is immature: the top GitHub repo has 38 stars [DOM/DOMAIN-09, verified].
4. **Product frameworks are unverified in our research.** INVEST, MoSCoW, Jobs-to-be-Done and Google HEART could not be fetched [DPA Gaps]. They are used here as working tools only, so every use of them is **(judgment)**. The acceptance-criteria format is verified: declarative Gherkin, ~3-5 steps, `Then` asserts observable output, `Rule:` per business rule, `Scenario Outline` for data variations [DPA/PROD-01, DPA/PROD-02].
5. **Privacy law is unverified.** GDPR and children's-data obligations are a high-priority gap [AQS G3.5, AQS Gaps]. Anything touching minors, consent or third-party footage is escalated to the human product owner.

## 1. Challenges to the design spec

Each challenge states the spec position, the evidence, and the proposal. Items that change a milestone's "Done when" are escalated to the human product owner (PM boundary).

| # | Spec says | Evidence / reasoning | Proposal |
|---|---|---|---|
| C1 | First milestone is "upload → stats → training plan", yet training plans arrive only at M5, after four vision milestones (spec §7). | The value chain cannot be shown to a single real user until M5. (judgment) Anthropic guidance is to start with the simplest working path and add complexity only when it is shown to help [DPA/AI-01]. | Build a **thin end-to-end "walking skeleton" by the end of Release 1**: upload → quick manual tag → score sheet → 5 basic stats → rules-only general plan from a ~20-drill starter library. Vision then *replaces manual effort* milestone by milestone rather than *unlocking value* at M5. **Escalate:** changes M0/M5 scope. |
| C2 | M0 "manual tagging UI" is both the labelling tool and the first user feature. | Tagging every shot of a match is too slow for a self-serve amateur. (judgment: a doubles game at roughly 20-30 rallies of ~6-10 shots means ~150-300 shot tags per game.) | Split into two modes. **Quick Tag** (user-facing): per rally, tap the winning side and the ending (winner / unforced error / fault), target ≤ 5 s per rally (judgment). **Full Tag** (internal labelling): every shot and bounce, for the gold set. Quick Tag alone is enough for a score sheet and rally-level stats. |
| C3 | M0 "Done when: a user can tag a match by hand and get a **correct** score sheet." | "Correct" depends on rules that are unverified [DOM G1]. | Keep the target, but mark M0 **blocked on rule verification**. The human PO should supply the 2026 USAP rulebook PDF, since egress blocks it [DOM/DOMAIN-01, domain-coach definition]. Pin `rules_version = "USAP-2026"` [DOM G1 R1]. |
| C4 | Spec calls pickleball a sport "with few tools" (spec §2). | At least two commercial tools reportedly analyse pickleball from a phone [DOM/DOMAIN-06..08, unverified]. | Treat "few tools" as an untested assumption. Before Release 2, the PM runs a first-hand competitor teardown (sign up, upload one match, record features, accuracy, price, time-to-result). Positioning on **correctable score sheets + traceable drills + opponent scouting** stays (judgment) [DOM implications table] until that teardown is done. |
| C5 | Opponent scouting is merged across "≥ 2 matches" (spec M6). | Amateurs may meet the same opponent rarely. Two matches may give single-digit samples for tendencies such as "speed-up from backhand on high dinks" (judgment). The spec itself requires sample sizes and low-sample flags (spec §5), and HAX says to make clear how well the system can do what it does (G2) and scope services when in doubt (G10) [DPA/DESIGN-11]. | Keep ≥ 2 matches as the minimum for *showing* a report, but require a **per-tendency minimum sample (proposed n ≥ 15 events)** before a tendency is stated as fact or drives an opponent plan. Below that it is shown as "low sample". Threshold is (judgment) and must be tuned with the domain coach. |
| C6 | Opponent profiles are user-created records about third parties (spec §4). | They are personal data about non-users. Privacy law is unverified [AQS G3.5]. Profiles must be scoped to their creator [AQS/SEC-03 via AQS implications]. | Opponent profiles are **Should** for Release 3, not Must. They store a user-chosen nickname only, never contact details or face data, and are never shared. Release is gated on a verified privacy research pass. **Escalate** (legal/privacy). |
| C7 | Capture at 1080p, 60 fps or better (spec §2). | Many amateurs will film at their phone's default settings (judgment). Ball-tracking prior art was trained on 30 fps broadcast tennis [DOM/CV-02], so 30 fps footage is not necessarily unusable, but our own accuracy on it is unknown. | The upload quality check **reports** frame rate and resolution and states the expected degradation instead of rejecting the file. Measure ball F1 on 30 fps vs 60 fps gold clips in M2 and set the hard minimum from data. |
| C8 | M3 "≤ 1 correction per game on average". | The denominator is ambiguous: score corrections only, or any correction to rallies, shots and identities? | Define it as **score-affecting corrections per game** (rally winner, server, fault). Track shot-type and identity corrections as separate metrics (see §8). |
| C9 | M2 "≥ 90% of rallies segmented correctly". | "Correctly" is undefined. | A rally counts as correct when its detected start and end are each within **± 1.0 s** of the gold label and it is neither merged with nor split from a neighbour (judgment threshold, tune on gold set). Report precision and recall, not just accuracy. |
| C10 | The LLM picks drills and orders them (spec §6). | Coaching should be a workflow, not an autonomous agent [DPA/AI-01]. LLM output is untrusted input to be validated [AQS implications: SEC-08 API10]. | Release 1 uses a **deterministic, rules-only plan** (top 3 point leaks → tagged drills). The LLM is added in Release 2 for ordering and the "why" text only, behind validation that every drill ID and metric exists. Rules-only stays as the fallback when the LLM fails or hits its budget. |
| C11 | Monetisation open (spec §9). | GPU cost target 1-2 GPU-min per match-minute (spec §8). We have no verified GPU price source. | Do not pick a model yet. Run the experiments in §9 and track cost per analysed match from the first GPU job [AQS/SEC-10]. **Escalate** (monetisation is a PO decision). |
| C12 | Videos "possibly minors" (spec §8). | Children's-data rules are unverified [AQS G3.5]. | Release 1: account holders must confirm they are 18+, and the capture guide asks users not to upload matches involving minors (judgment, interim). **Escalate** for a legal decision before any public beta. |

## 2. Personas

These personas are hypotheses (judgment). None is validated by user research yet; R-01 in §10 is the task to validate them with at least 8 interviews.

| ID | Persona | Profile | Main need | Release focus |
|---|---|---|---|---|
| PER-1 | **"Improving Ivy"**, recreational doubles player | Plays 2-4 times a week at a club or park, self-rated intermediate, films occasionally on a phone, will not spend more than ~10 min of effort per match on the app (judgment) | "Tell me the 2-3 things costing me the most points and what to practise." | R1-R2 (primary) |
| PER-2 | **"Competitive Carlos"**, club or tournament player | Plays leagues and local tournaments, faces repeat opponents, already watches his own video | "Help me beat *that* team next Saturday." Trend tracking across matches. | R2-R3 |
| PER-3 | **"Coach Kim"**, club coach | Teaches groups of 4-12 players, wants homework drills tied to evidence | Multi-player view, shareable plans | v1.x (spec §9 open question); out of MVP |
| PER-4 | **"Filmed Fran"**, a non-user in the footage | Partner or opponent who appears in someone else's video | Not to be identified, profiled or shared without knowing | All releases (privacy stakeholder) |
| PER-5 | **Internal labeller / ML engineer** | Uses Full Tag to build the gold set | Fast, keyboard-driven frame-accurate tagging | R1-R2 (internal) |

## 3. Jobs to be done (judgment framework)

| ID | Persona | When... | I want to... | So I can... | Evidence of value we will measure |
|---|---|---|---|---|---|
| JTBD-1 | PER-1 | I finish a match I filmed | see the score sheet and where I lost points without watching the whole video | stop guessing what to work on | Time-to-first-insight; % of users opening the stats page within 24 h of upload |
| JTBD-2 | PER-1 | I have 2-3 hours of practice a week | get a short plan of drills aimed at my biggest point leaks | practise with purpose | Plan start rate; sessions marked done |
| JTBD-3 | PER-1, PER-2 | I play my next filmed match | see whether the targeted metrics moved | know whether the practice worked | Plan efficacy score (§8) |
| JTBD-4 | PER-2 | I have a match against a known opponent | see their tendencies with clips | go in with a game plan | Scouting report views before a scheduled match (R3) |
| JTBD-5 | PER-1, PER-2 | the app makes a wrong call | fix it in a tap or two | trust the stats | Correction time; post-correction satisfaction |
| JTBD-6 | PER-4 (through PER-1) | I upload footage that shows other people | keep it private and delete it when I want | not expose friends | Deletion requests completed within SLA |

## 4. Key user journeys

### J1. First match: upload → score sheet → stats → plan (north star)
1. Sign up without a memorised password (passkey or magic link) [DPA/DESIGN-06].
2. Read a 1-screen capture guide with a captioned 30-60 s video [DPA/DESIGN-08].
3. Match setup, one question per page: format, scoring system, players (nicknames), then upload [DPA/DESIGN-12].
4. Resumable upload from the phone browser; it survives a network drop [AQS/STACK-06].
5. Quality check result: fps, resolution, court visibility; any problems use the error-summary pattern [DPA/DESIGN-13].
6. Court calibration: auto proposal plus "confirm 4 corners", with a non-drag alternative [DPA/DESIGN-05].
7. Release 1: Quick Tag each rally. Later releases: automatic analysis, then review of low-confidence calls.
8. Score sheet → stats dashboard (each metric with sample size) → general plan with a "why" per drill [DPA/DESIGN-11 G11].

**Targets (judgment):** Release 1 median total user effort ≤ 15 min for a 3-game match. Release 3 (automatic) ≤ 5 min of review effort, results ready within 2× video duration (see §7).

### J2. Review and correct
Timeline of rallies, each with confidence; low-confidence calls are surfaced first; one-tap correction with keyboard support [DPA/DESIGN-11 G2, G9]. Corrections recompute the score and all dependent stats, and the user is told what changed [DPA/DESIGN-11 G16, G18].

### J3. Follow the plan, then re-measure
Plan of 2-4 weeks (spec §6), sessions checked off. After the next uploaded match, the plan shows "targeted metric: before → after, sample sizes".

### J4. Scout an opponent (Release 3)
Link opponent nickname across matches → report with tendencies, each with n and clips → 1-3 session opponent plan.

### J5. Control my data
See all my videos, change retention, delete a match (video, clips, derived data) and delete my account. Spec §8 privacy defaults: private by default, explicit sharing, retention controls, no face recognition.

## 5. Epics

Epic order is the proposed backlog order. MoSCoW is scoped to the **MVP = Releases 1 + 2** (judgment framework).

| Epic | Name | Why (value) | Spec milestone | Release | MoSCoW (MVP) | Context [process/ddd-guidelines.md §2] |
|---|---|---|---|---|---|---|
| E1 | Account and privacy foundation | Nothing ships to real users without auth, ownership checks and deletion [AQS/SEC-09] | M0 | R1 | Must | Identity & Players |
| E2 | Capture and upload | Getting video in reliably is the first step of every journey | M0 | R1 | Must | Capture & Media |
| E3 | Rules engine and score sheet | The score sheet is deliverable #1 of the spec, and every stat depends on it | M0 | R1 | Must (blocked: rules verification) | Sport Plug-in, Match & Scoring |
| E4 | Quick Tag and Full Tag | Value before vision; Full Tag builds the gold set (spec §7 note, §8 risk) | M0 | R1 | Must | Match & Scoring |
| E5 | Starter stats dashboard | Proves JTBD-1 early | M4 subset | R1 | Must | Analytics |
| E6 | Rules-only general plan + starter drill library | Closes the value chain in R1 (challenge C1) | M5 subset | R1 | Must | Coaching, Drill Library |
| E7 | Court calibration and player tracking | First automation; heatmaps and positioning | M1 | R2 | Should | Vision Analysis |
| E8 | Ball, hit, bounce and rally detection | Removes most Quick Tag effort | M2 | R2 | Should | Vision Analysis |
| E9 | Automatic scoring, shot classification and review flow | The core differentiator: correctable automatic score sheet (judgment) | M3 | R3 | Could (MVP) / Must (R3) | Vision, Match & Scoring |
| E10 | Full analytics with clip links | Patterns, n-grams, transition, dink battles (spec §5) | M4 | R3 | Could | Analytics |
| E11 | LLM-written plan explanations and plan efficacy | Better "why", closes the loop (spec §6 step 4) | M5 | R2 | Should | Coaching |
| E12 | Opponent profiles and scouting | PER-2 differentiator; privacy-gated (C6) | M6 | R3+ | Won't (this MVP) | Analytics, Identity |
| E13 | Live mode | Spec M7 | M7 | Later | Won't (this MVP) | all |
| E14 | Coach multi-player view | PER-3; spec §9 open question | – | v1.x | Won't (this MVP) | Identity, Coaching |
| E15 | Cost guardrails and usage quotas | GPU and LLM spend are product constraints [AQS/SEC-10] | M2 onward | R1 (quotas), R2 (GPU) | Must | cross-cutting |

## 6. User stories

Format: INVEST is used as a self-check only (judgment; unverified in research [DPA Gaps]). Acceptance criteria follow [DPA/PROD-01, DPA/PROD-02]. FR IDs are proposed and will be finalised in `functional.md`. "Status" uses `ready-candidate` or `needs-verification`.

### E1 Account and privacy foundation

**US-101 Passwordless sign-up** (Must, ready-candidate, FR-ID-01)
As Improving Ivy, I want to sign up with a passkey or an email magic link, so that I don't need to remember another password.
```gherkin
Feature: Sign up without a memorised password
  Rule: Authentication never requires a cognitive function test (WCAG 2.2 SC 3.3.8)
    Scenario: Sign up with an email magic link
      Given Ivy has no account
      When she requests a sign-in link for her email and opens it within 15 minutes
      Then she is signed in and sees the "Record your first match" screen
    Scenario: Expired link
      Given Ivy requested a sign-in link 16 minutes ago
      When she opens it
      Then she sees "This link has expired" and a button to send a new one
```
Source: [DPA/DESIGN-06]. 15-minute expiry is (judgment). Out of scope: social login, password login.

**US-102 Only I can see my matches** (Must, ready-candidate, FR-ID-02, NFR-SEC-01)
As a player, I want my matches, clips and plans to be visible only to me, so that footage of my friends stays private.
```gherkin
Feature: Object-level authorisation
  Rule: Every resource ID is checked for ownership or explicit sharing
    Scenario Outline: Another user cannot open my resource
      Given Ivy owns a <resource>
      When Carlos requests that <resource> by its ID
      Then Carlos receives "not found"
      And the attempt is recorded in the security log
      Examples:
        | resource        |
        | match           |
        | rally           |
        | clip            |
        | training plan   |
        | opponent profile|
```
Source: [AQS/SEC-09, AQS/SEC-03, AQS/SEC-04]. Returning "not found" rather than "forbidden" is (judgment) to avoid confirming existence.

**US-103 Delete a match and everything derived from it** (Must, ready-candidate, FR-ID-03)
As a player, I want to delete a match, so that the video and every stat and clip from it are gone.
```gherkin
Feature: Match deletion
  Scenario: Delete a match
    Given Ivy has an analysed match with clips and a plan that cites it
    When she deletes the match and confirms
    Then the match, its video and clips no longer appear anywhere in her account within 1 minute
    And the plan shows "evidence removed" against drills that cited that match
    And the stored video object is unrecoverable within 30 days
```
The 1-minute and 30-day windows are (judgment); the spec requires retention controls (spec §8) and ASVS lists scheduled deletion of unneeded sensitive data [AQS/SEC-05, 14.2.7]. Whether the 30-day window satisfies law is unverified [AQS G3.5] → escalate.

**US-104 Retention setting** (Should, ready-candidate, FR-ID-04): choose "keep video 30 / 90 / 365 days / until I delete"; derived stats are kept, raw video is deleted on schedule. Default 90 days (judgment, escalate).

**US-105 Age confirmation** (Must for public beta, needs PO decision, FR-ID-05): account holder confirms 18+; interim control per C12.

### E2 Capture and upload

**US-201 Capture guide** (Must, ready-candidate, FR-CAP-01): one screen plus a captioned video showing tripod position behind a baseline, elevation, landscape, 1080p/60 fps (spec §2). Captions per [DPA/DESIGN-08].

**US-202 Resumable upload** (Must, ready-candidate, FR-CAP-02, NFR-REL-01)
As Ivy on court Wi-Fi, I want an interrupted upload to continue where it stopped, so that I don't re-send gigabytes.
```gherkin
Feature: Resumable upload
  Scenario: Connection drops mid-upload
    Given Ivy is uploading a 3 GB match video and 40% has been sent
    When her connection drops for 2 minutes and then returns
    Then the upload continues from at least 40%
    And she sees the remaining percentage and an estimate of time left
  Scenario: Upload abandoned
    Given Ivy started an upload 8 days ago and never finished it
    When she opens her matches list
    Then the partial upload is no longer listed and its storage is freed
```
Source: tus 1.0.0 offset resume and expiration extension [AQS/STACK-06, AQS G5.4]. 7-day expiry is (judgment).

**US-203 Upload validation** (Must, ready-candidate, FR-CAP-03, NFR-SEC-02)
```gherkin
Feature: Upload validation
  Rule: Only real video files within size and duration limits are accepted
    Scenario Outline: Reject invalid files
      Given Ivy selects <file>
      When she starts the upload
      Then she sees an error summary titled "There is a problem" with "<message>"
      Examples:
        | file                                 | message                                      |
        | a PDF renamed to match.mp4           | This file is not a video we can read         |
        | a 15 GB video                        | Videos must be 10 GB or smaller              |
        | a 4-hour video                       | Videos must be 3 hours or shorter            |
```
Sources: magic-byte check, size limits, generated storage names [AQS/SEC-02, AQS G2.7]; error summary pattern [DPA/DESIGN-13]. Limits (10 GB, 3 h) are (judgment) and need sizing against real phone files.

**US-204 Footage quality report** (Should, ready-candidate, FR-CAP-04): after upload, report fps, resolution, estimated court visibility, and what will be degraded (e.g. "30 fps: ball-based stats may be less accurate"). Never blocks the upload (challenge C7). Graceful degradation is a spec risk mitigation (spec §8).

### E3 Rules engine and score sheet (all `needs-verification`)

**US-301 Side-out doubles scoring** (Must, needs-verification, FR-SCO-01)
As a player, I want the score sheet to follow official side-out scoring, so that I can trust it.
```gherkin
Feature: Doubles side-out scoring (rules_version USAP-2026)
  # needs-verification: every row below must cite a DOMAIN-01 rule number before Ready [DOM G1 R2, R6]
  Rule: Only the serving side scores
    Scenario Outline: Score after a rally
      Given the score is <before>
      When the <rally_winner> side wins the rally
      Then the score is <after>
      Examples:
        | before | rally_winner | after |
        | 0-0-2  | serving      | 1-0-2 |
        | 0-0-2  | receiving    | 0-0-1 |
        | 3-5-1  | receiving    | 3-5-2 |
        | 3-5-2  | receiving    | 5-3-1 |
  Rule: A game is won at 11 by a margin of 2
    Scenario Outline: Game end
      Given the score is <before>
      When the serving side wins the rally
      Then the game over state is <game_over>
      Examples:
        | before  | game_over |
        | 10-8-1  | yes       |
        | 10-10-1 | no        |
        | 12-11-2 | yes       |
```
Example rows are (judgment) built from UNVERIFIED R2/R6 [DOM G1]; the domain coach owns them. Note "after" in row 4 reflects the score being called from the new serving side's perspective (needs-verification).

**US-302 Rally scoring option** (Should, needs-verification, FR-SCO-02): the match setup offers rally scoring; reported as provisional in 2026, game-winning point no longer limited to the serving team [DOM G1 R3, UNVERIFIED].

**US-303 Singles side-out scoring** (Should, needs-verification, FR-SCO-03).

**US-304 Score sheet view** (Must, ready-candidate apart from rule data, FR-SCO-04): rally-by-rally list with score before/after, server, winner, ending type; text alternative to the video (DPA implications §3: timeline as text alternative, judgment).

### E4 Quick Tag and Full Tag

**US-401 Quick Tag a rally** (Must, ready-candidate, FR-TAG-01)
As Ivy, I want to tag each rally with who won and how it ended in a couple of taps, so that I get a score sheet without tagging every shot.
```gherkin
Feature: Quick Tag
  Scenario: Tag a rally
    Given Ivy is watching rally 7 of her match
    When she marks "their side won" and "my unforced error"
    Then rally 7 shows the new score
    And the player moves to the start of rally 8
  Scenario: Keyboard only
    Given Ivy uses a keyboard and no pointer
    When she tags rally 7 with keys only
    Then the result is the same as tagging with taps
```
Targets: median ≤ 5 s per rally on a test panel of ≥ 5 users (judgment). Targets ≥ 24×24 CSS px, 48 dp on touch [DPA/DESIGN-02, DPA/DESIGN-10]. Rally boundaries are set by the user ("rally start" / "rally end" keys) until E8 supplies them.

**US-402 Full Tag** (Must, internal, FR-TAG-02): frame-stepping, hit / bounce / shot type / hitter tags, export in the gold-set format. Feeds model evaluation [DOM G8 E4] and coaching evals [DPA/AI-05].

**US-403 Undo and audit** (Must, FR-TAG-03): every tag and correction is undoable and stored with `corrected_by_user` (spec §4) as training data [DPA/DESIGN-11 G13, G15].

### E5 Starter stats dashboard

**US-501 Five starter stats** (Must, ready-candidate for definitions once coach confirms, FR-AN-01)
For each player/side, from Quick Tag data: points won on serve vs return, unforced errors per game, longest run, side-outs, rallies won by ending type. Each shows its sample size; metrics with n < 10 rallies are flagged "low sample" and still shown (spec §5; threshold is judgment).
```gherkin
Feature: Starter stats
  Rule: Every metric shows its sample size and is flagged when the sample is small
    Scenario: Low-sample metric
      Given Ivy's match has 6 rallies she served
      When she opens her stats
      Then "points won on serve" shows "n = 6" and a "low sample" label
```
Sources: [DPA/DESIGN-11 G2, G10]. Charts and heatmaps meet 3:1 non-text contrast and carry a non-colour encoding [DPA/DESIGN-04; non-colour encoding is judgment].

**US-502 Trend across matches** (Should, FR-AN-02): each starter stat over the last 5 matches, from `MetricSnapshot` (spec §4).

### E6 Rules-only general plan

**US-601 Generate a plan from my point leaks** (Must, ready-candidate after coach curates drills, FR-CO-01)
As Ivy, I want a 2-week plan targeting my top point leaks, so that my practice time goes where I lose points.
```gherkin
Feature: General training plan (rules-only)
  Rule: Every drill is from the curated library and cites the stat behind it
    Scenario: Plan from point leaks
      Given Ivy has 2 tagged matches and 3 practice hours a week
      When she asks for a plan
      Then she gets a 2-week plan whose sessions fit in 3 hours a week
      And every drill shows a "why" naming the stat and its value
      And every drill comes from the drill library
    Scenario: Not enough data
      Given Ivy has 1 tagged match with 12 rallies
      When she asks for a plan
      Then she sees that the plan is based on limited data and how many rallies it used
```
Spec §2, §6; HAX G11 "make clear why" [DPA/DESIGN-11]; workflow not agent [DPA/AI-01]. The ranking ("points lost per match attributable", spec §6 step 1) uses Quick Tag ending types in R1.

**US-602 Starter drill library** (Must, needs-verification for content, FR-DR-01): ≥ 20 drills (spec targets ~80 at M5) each tagged skill, level, duration, players, equipment, target metric, source or coach rationale; unsourced drills labelled (judgment) until reviewed [domain-coach definition].

**US-603 Mark a session done** (Should, FR-CO-02).

### E7-E9 Vision automation (summary; detailed stories owned with principal-engineer and ML)

| Story | Priority | Measurable acceptance (judgment thresholds unless cited) |
|---|---|---|
| US-701 Auto court calibration with 4-corner confirm | Should (R2) | Auto proposal accepted without edits on ≥ 80% of gold videos; reprojection error of known court lines < a documented pixel threshold [DOM G6 H1-H3]; non-drag corner placement [DPA/DESIGN-05] |
| US-702 Assign identities once per match | Should (R2) | User taps each of 4 players once; constraint "2 per side" (DOM G4 P4, judgment); ID switches per game reported with HOTA/IDF1 on the gold set [DOM/CV-08] |
| US-703 Player heatmaps | Should (R2) | Spec M1 "Done when"; ground-plane points only [DOM G6 H1] |
| US-801 Automatic rally segmentation | Should (R2) | ≥ 90% per C9 definition (spec M2) |
| US-802 Hit timing from audio + video | Should (R2) | Median hit-timing error ≤ 50 ms vs gold (judgment) [DOM G7, G8] |
| US-901 Automatic score with confidence | Could (R3 Must) | ≤ 1 score-affecting correction per game on average (spec M3, C8 definition); every call shows confidence [DPA/DESIGN-11 G2] |
| US-902 Review low-confidence calls first | Could (R3 Must) | Calls below a confidence threshold listed first; one-tap fix [DPA/DESIGN-11 G9] |
| US-903 Reprocessing notice | Should | When a new pipeline version changes past stats, user sees what changed [DPA/DESIGN-11 G14, G18] |

### E11 LLM plan explanation and efficacy (R2)

**US-1101 LLM-written "why" with validation** (Should, FR-CO-03): the LLM orders drills and writes the why; the service rejects any output naming a drill or metric that does not exist and falls back to the rules-only plan [AQS implications SEC-08 API10; DPA/AI-01]. Evals: 20-50 realistic player profiles built before release, code grader for drill/metric existence, model grader calibrated by the coach, pass^k for consistency [DPA/AI-05, DPA G-EVAL-1..3].

**US-1102 Plan efficacy** (Should, FR-CO-04): after the next match, each targeted metric shows before → after with sample sizes (spec §6 step 4); no claim of improvement when either sample is low.

### E15 Cost guardrails

**US-1501 Monthly analysis quota** (Must, FR-COST-01, NFR-COST-01)
```gherkin
Feature: Analysis quota
  Rule: Each plan tier has a monthly analysed-minutes quota
    Scenario: Quota reached
      Given Ivy has used all 180 analysed minutes this month
      When she uploads another match
      Then the video is stored but not analysed
      And she sees when her quota resets
```
Source: quotas, rate limits and spending alerts [AQS/SEC-10, AQS G2.6]. 180 min is a placeholder (judgment) pending §9.

**US-1502 Spend alerts** (Must, internal): billing alerts on GPU provider and Anthropic API at 50/80/100% of a monthly budget [AQS/SEC-10; percentages are judgment].

## 7. Non-functional requirement candidates (for the BA's `non-functional.md`)

Percentile targets are (judgment): DPA/DESIGN-16 defines response time, throughput and latency but prescribes no percentiles [DPA G-REQ-7].

| ID | Category | Requirement | Verification | Source |
|---|---|---|---|---|
| NFR-SEC-01 | Security | Every endpoint that takes a resource ID enforces ownership or explicit sharing; parametrised test proves user B gets not-found on all of them | Integration test suite | [AQS/SEC-09, AQS/SEC-03] |
| NFR-SEC-02 | Security | Upload: size and duration caps, magic-byte type check, generated storage keys, signed short-lived download URLs | Integration test | [AQS/SEC-02] |
| NFR-SEC-03 | Security | API and client meet OWASP ASVS 5.0 Level 2 | Security review checklist per release | [AQS/SEC-01] |
| NFR-SEC-04 | Security | LLM output validated before persistence (drill IDs and metric IDs exist) | Unit + eval | [AQS implications SEC-08 API10] |
| NFR-PRIV-01 | Privacy | Videos private by default; no face recognition; identity assigned by the user | Design review + test | spec §8 |
| NFR-PRIV-02 | Privacy | Data classified (video high, names medium, metrics low/medium) with retention per class; scheduled deletion | Test + review | [AQS/SEC-05] |
| NFR-A11Y-01 | Accessibility | WCAG 2.2 AA; targets ≥ 24×24 CSS px (48 dp on touch); text contrast 4.5:1; chart/heatmap contrast 3:1; non-drag alternatives; no obscured focus | axe-core in CI + manual screen-reader pass per sprint | [DPA/DESIGN-01..07, DPA/DESIGN-10, DPA/DESIGN-14] |
| NFR-PERF-01 | Performance | Dashboard and score sheet p95 load ≤ 2.0 s on a mid-range phone over 4G (judgment) | Performance test | [DPA/DESIGN-16] for the categories |
| NFR-PERF-02 | Performance | Quick Tag action to updated score ≤ 200 ms p95 (judgment) | E2E timing | [DPA/DESIGN-16] |
| NFR-PERF-03 | Latency | Automatic analysis completes within 2× video duration at p90 (judgment), e.g. a 60-min match ready in ≤ 2 h | Job metrics | [DPA/DESIGN-16] |
| NFR-REL-01 | Reliability | SLOs (judgment start values): upload success ≥ 99%, analysis job success ≥ 97%, API availability ≥ 99.5% monthly; each with an error budget | SLI dashboards | [AQS/REL-01, AQS/REL-02] |
| NFR-REL-02 | Reliability | A failed pipeline stage fails closed; "score only, no shot detail" is an explicit state, not a partial write | Integration test | [AQS/SEC-12], spec §8 |
| NFR-COST-01 | Cost | ≤ 2 GPU-min per match-minute (spec §8), measured per job from M2; LLM tokens per plan budgeted and alerted | Job metrics + alerts | spec §8, [AQS/SEC-10] |
| NFR-QUAL-01 | Model quality | Frozen gold set; ball F1, HOTA/IDF1, hit-timing error, rally segmentation accuracy reported every sprint; no regression gate | Model-quality test layer | [DOM G8 E1-E4] |
| NFR-TRACE-01 | Trust | Every insight and drill links to the stat and video moments behind it | E2E test | spec §6, [DPA/DESIGN-11 G11] |

## 8. Success metrics

Google HEART could not be verified [DPA Gaps]; the metric set below is (judgment). All targets are hypotheses to be reset after the first 50 real users.

### North star
**Weekly Active Improvers (WAI):** users who, in a 7-day window, uploaded a match **or** completed a plan session **and** have an active plan. Rationale: it captures the whole "upload → stats → plan" chain rather than uploads alone (judgment).

### Funnel and outcome metrics

| Metric | Definition | R1 target | R3 target |
|---|---|---|---|
| Activation | % of sign-ups with a score sheet within 7 days | ≥ 40% | ≥ 60% |
| Time to first insight | Median minutes from upload complete to stats visible (incl. user effort) | ≤ 20 min (Quick Tag) | ≤ 2× video duration, ≤ 5 min user effort |
| Quick Tag effort | Median seconds per rally | ≤ 5 s | n/a |
| Correction rate | Score-affecting corrections per game (C8) | n/a | ≤ 1.0 (spec M3) |
| Trust | % of users rating "I trust these stats" ≥ 4/5 in an in-app 1-question survey | ≥ 60% | ≥ 75% |
| Plan start | % of users with a plan who complete ≥ 1 session within 14 days | ≥ 35% | ≥ 50% |
| Plan efficacy | % of completed plans where ≥ 1 targeted metric improved with both samples ≥ threshold | measure only | ≥ 40% |
| Retention | % of activated users who upload a 2nd match within 30 days | ≥ 30% | ≥ 45% |
| Unit cost | GPU + LLM cost per analysed match-hour | measure only | ≤ the price-point margin set in §9 |
| Reliability | SLO attainment for NFR-REL-01 | per NFR | per NFR |
| Privacy | Deletion requests completed within the stated window | 100% | 100% |

Guardrails: no increase in support tickets about wrong scores after a model release; no user-facing metric shown without sample size.

## 9. Monetisation assumptions to validate

All assumptions are (judgment). The model choice is a PO decision (spec §9; PM escalation rule).

| ID | Assumption | Why it matters | How to validate | Pass threshold (judgment) |
|---|---|---|---|---|
| MA-1 | Amateurs will pay a monthly subscription for automatic analysis + plans | Decides freemium vs subscription | Fake-door pricing page in R1 beta with 3 price points; count "start trial" clicks | ≥ 8% of activated users click a paid tier |
| MA-2 | Free value is the rules-only plan from Quick Tag; paid value is automatic analysis | Free tier costs little GPU; paid tier carries GPU cost | Compare R1 (manual) vs R2 (auto) retention and survey willingness to pay | Auto users retain ≥ 1.5× manual users at 30 days |
| MA-3 | A typical user analyses ~4 matches (~4-6 hours) per month | Sizes quotas and unit cost | Upload logs in R1-R2 | Median measured; quota set at P75 |
| MA-4 | GPU cost at ≤ 2 GPU-min per match-minute fits the price | Gross margin | Measure GPU-seconds per job from M2 [AQS implications: OpenTelemetry GPU-seconds metric]; no verified GPU price source yet, so get quotes | Cost per analysed hour ≤ 30% of the monthly price ÷ expected hours (judgment) |
| MA-5 | Opponent scouting is a paid upsell valued by competitive players | Justifies E12 | Interview ≥ 8 PER-2 players; fake-door "Scout an opponent" button | ≥ 25% of PER-2 users click in a month |
| MA-6 | Clubs or coaches would pay for multi-player views | Decides E14 (spec §9) | 5 coach interviews before R3 | ≥ 3 of 5 say they would pay |
| MA-7 | Competitors' pricing sets the anchor | Positioning | First-hand teardown (C4) | Documented before pricing decision |

## 10. Research and validation tasks (instead of guessing)

| ID | Task | Owner | Blocks |
|---|---|---|---|
| R-01 | ≥ 8 interviews with recreational and competitive players to validate personas and JTBD | product-manager | Release 2 priorities |
| R-02 | Obtain 2026 USAP rulebook (human PO supplies PDF) and record rule numbers for R1-R6 | pickleball-domain-coach | All E3 stories, M0 Done |
| R-03 | Competitor teardown (PB Vision, SwingVision) first-hand | product-manager | C4, MA-7 |
| R-04 | Verified privacy research: consent for third parties, minors, retention, lawful basis | security-privacy-engineer + human PO | Public beta, E12 |
| R-05 | Measure real phone file sizes and fps defaults on ≥ 5 phone models | senior-ml-cv-engineer | US-203 limits, C7 |
| R-06 | Coach-verified drill sources for the starter library | pickleball-domain-coach | US-602 |
| R-07 | GPU provider pricing quotes | principal-engineer | MA-4 |

## 11. Proposed release slicing (input to sprint planning)

Sprint length and capacity are for the engineering-manager to set. The order below is (judgment).

| Release | Contains | Exit criterion |
|---|---|---|
| **R1 Walking skeleton** (spec M0 + subsets of M4, M5) | E1, E2, E3 (after R-02), E4, E5, E6, E15 quotas | A real user uploads a match, Quick Tags it, gets a correct score sheet, 5 starter stats and a rules-only plan, with median effort ≤ 15 min |
| **R2 First automation** (M1, M2, M5) | E7, E8, E11, E15 GPU alerts | Rally segmentation ≥ 90% (C9) on gold set; Quick Tag effort drops ≥ 50%; LLM plan passes evals |
| **R3 Automatic scoring** (M3, M4) | E9, E10 | ≤ 1 score-affecting correction per game; all §5 metrics except scouting |
| Later | E12 (after R-04), E13, E14 | per spec M6, M7 |

## 12. Out of scope for the MVP (R1 + R2)

Live mode (M7); opponent scouting and opponent plans (M6); coach multi-player view; social sharing and public links; sports other than pickleball; native mobile app; face recognition (never); payments implementation (fake-door only).

## 13. Open questions for the human product owner

1. Approve challenge C1: a thin end-to-end R1 that moves a rules-only plan and starter stats ahead of vision work (changes M0/M5 scope)?
2. Can you supply the 2026 USA Pickleball Official Rulebook PDF? Rules sources are egress-blocked and M0 cannot be "correct" without it [DOM/DOMAIN-01].
3. Which rulebook governs: USAP only, or also other federations (Pickleball Canada, GPF) [DOM/DOMAIN-04, DOMAIN-05]?
4. Minimum account age and policy on footage that includes minors (C12)? Needs legal input.
5. Default video retention period (proposed 90 days) and deletion window (proposed 30 days)?
6. Monetisation direction to test first: freemium with analysis quota, or subscription with trial (MA-1, MA-2)?
7. Is opponent scouting a v1 promise or a later upsell, given the privacy gate (C6)?
8. Budget ceiling per month for GPU and LLM during beta (sets alert thresholds in US-1502)?
9. Product name (spec §9).
