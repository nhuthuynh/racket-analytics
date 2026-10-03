# Domain-Driven Design Guidelines

- **Status:** Accepted as an initial model (ADR 0001). It will be refined after the first EventStorming.
- **Date:** 2026-10-03
- **Owner:** principal-engineer
- **Citation prefixes:** see `working-agreement.md` §0.

The candidate contexts, their classification and the context-map relationships below are **(judgment)** drawn from the spec and from EP's implications. The methods used to derive and document them are cited.

## 1. Process

1. **Starter process.** Follow the DDD Crew starter process: Understand -> Discover (EventStorming) -> Decompose -> Strategize -> Connect -> Organise -> Define -> Code [EP/ENG-11].
2. **EventStorming.** Run Big Picture first, then Process Modelling, then Software Design.
   - Domain events are past-tense verbs (orange). Commands are blue, policies lilac, read models green, and hotspots pink [EP/ENG-14].
3. **Bounded Context Canvas.** Every context gets a canvas in `docs/architecture/contexts/<name>.md` [EP/ENG-12]. The canvas holds:
   - name and purpose;
   - strategic classification;
   - domain roles;
   - inbound and outbound communication;
   - ubiquitous language;
   - business decisions;
   - assumptions;
   - verification metrics;
   - open questions.
4. **Context map.** Every relationship between contexts is named with a context-mapping pattern [EP/ENG-13].
5. **Code layout.** Backend code is organised by context or domain module, not by file type [AQS/STACK-01].

## 2. Bounded contexts

| Context | Purpose (business language) | Classification | Key aggregates | Code module |
|---|---|---|---|---|
| **Identity & Players** | Who the user is, the player profiles they own, and opponent profiles they create | Generic | `Account`, `PlayerProfile`, `OpponentProfile` | `players` |
| **Capture & Media** | Getting match video in safely and keeping it private: resumable upload, quality check, storage, retention, clips | Supporting | `MediaAsset`, `UploadSession`, `Clip` | `video_ingest` |
| **Vision Analysis** | Turning video into time-stamped, confidence-scored observations: court, players, ball, hits, bounces, rallies, shot types | Core | `AnalysisJob` (per match, pipeline version and stage), `CourtCalibration`, `EventTrack` | `analysis_jobs` (API side), `workers/*` |
| **Match & Scoring** | The authoritative match record and score under a specific rules edition, including the player's corrections | Core | `Match` (root; owns `Rally` and `Shot`) | `matches`, `scoring` |
| **Analytics** | Metrics, patterns and trends per player and match, with sample sizes | Core | `MetricSnapshot` (read-model-like, recomputable) | `analytics` |
| **Coaching** | Ranking weaknesses, assembling training plans from the drill library, and scoring plans afterwards | Core | `TrainingPlan` (owns `Session`, `DrillAssignment`) | `coaching` |
| **Drill Library** | A curated, versioned catalogue of vetted drills | Supporting | `Drill` | `coaching/drills` or a separate module |
| **Sport Plug-in (pickleball)** | Court model, rules state machine, shot taxonomy, metric definitions, drill tags for one sport | Core (Published Language) | `RulesEngine` (pure functions), `CourtModel`, `ShotTaxonomy` | `sports/pickleball` |

Analytics also hosts opponent scouting from M6, as a sub-module or a separate context. That will be decided by ADR at M6.

## 3. Context map

The map follows the patterns in [EP/ENG-13]. Applying them here is judgment.

```
                       +--------------------+
                       | Identity & Players |  (Open Host Service: owner/ID checks)
                       +---------+----------+
                                 | U
            D           D        v          D
+-----------------+   +------------------+   +------------------+
| Capture & Media |-->| Vision Analysis  |-->| Match & Scoring  |
|   (U)           |   | (D of Media,     |   | (D of Vision via |
+-----------------+   |  U of Scoring)   |   |  ACL; conforms to|
                      +------------------+   |  Sport Plug-in)  |
                                             +--------+---------+
                 +------------------------+           | U (events)
                 | Sport Plug-in          |           v
                 | (Published Language)   |   +------------------+     +---------------+
                 +------------------------+   |    Analytics     |---->|   Coaching    |
                                              +------------------+  U  | (ACL to LLM)  |
                                                                       +-------+-------+
                                                                               | Customer/Supplier
                                                                       +-------v-------+
                                                                       | Drill Library |
                                                                       +---------------+
```

| Upstream -> Downstream | Pattern | Why (judgment) |
|---|---|---|
| Capture & Media -> Vision Analysis | Customer/Supplier | Vision needs a stable media contract and a signed URL. It does not need the upload details. |
| Vision Analysis -> Match & Scoring | **Anticorruption Layer** in Match & Scoring | Raw detections (boxes, heatmaps, confidences) are translated into `Rally`/`Shot` language. Model vocabulary must not leak into the match record. |
| Sport Plug-in -> Match & Scoring, Vision, Analytics, Coaching | **Published Language / Open Host Service** | One sport-plug-in interface (spec §3) that every context consumes. New sports add plug-ins without changing the contexts. |
| Match & Scoring -> Analytics | Customer/Supplier via domain events | Analytics recomputes snapshots when `RallyScored` or `ScoreCorrected` fires. |
| Analytics -> Coaching | Customer/Supplier | Coaching consumes metric trends and evidence links. |
| Drill Library -> Coaching | Customer/Supplier | Coaching can only reference drills that exist. |
| LLM provider -> Coaching | **Anticorruption Layer** | LLM output is untrusted and must be validated [AQS/SEC-08]. Model vocabulary stays out of the domain [EP implications]. |
| Identity & Players -> all | Open Host Service | Ownership and sharing checks (BOLA) are a shared dependency [AQS/SEC-09]. |

## 4. Aggregate rules

1. **One aggregate, one transaction.** A command changes one aggregate per transaction. Other aggregates react to domain events.
   - Multi-step changes inside an aggregate are all-or-nothing [AQS/SEC-07 ASVS 2.3.3].
2. **The root guards its invariants.** Outside code holds references to the root only and never mutates children directly. Examples:
   - `Match` guards: the score sequence is consistent with its `rules_version`; rallies are ordered without overlap; a correction creates a new score state that is audited.
   - `TrainingPlan` guards: each `DrillAssignment` references an existing `Drill` and a metric; total duration ≤ available time.
3. **Reference other aggregates by ID only.** Public IDs are random and unpredictable (UUID) [AQS/SEC-09].
4. **Keep aggregates small.** `Event` rows from Vision live in `EventTrack`, not in `Match`.
5. **Domain logic is pure where possible.** The rules engine is a pure function: (state, rally outcome, rules_version) -> new state. That makes it trivially unit-testable [EP/ENG-17].
6. **Raise domain events in the past tense.** Events are published after commit and must be idempotent for consumers [AQS/OPS-02].
7. **Version everything that changes interpretation:**
   - `rules_version` on `Match`;
   - `pipeline_version` on `AnalysisJob`;
   - `library_version` on `TrainingPlan` (judgment).
8. **User corrections win.** Corrected values are flagged `corrected_by_user` (spec §4) and are never overwritten by re-processing (judgment).
9. **Ownership is part of the aggregate.** Every root carries `owner_id`, and every load goes through an ownership check [AQS/SEC-03].

## 5. Initial domain events (Big Picture seed)

These events are seeded from [EP implications, ENG-14]:

`MatchCreated`, `UploadStarted`, `MatchUploaded`, `UploadQualityChecked`, `CourtCalibrated`, `PlayersIdentified`, `BallTracked`, `HitDetected`, `BounceDetected`, `RallySegmented`, `ShotClassified`, `RallyScored`, `ScoreCorrected`, `MatchScored`, `MetricSnapshotComputed`, `WeaknessesRanked`, `TrainingPlanGenerated`, `TrainingPlanEvaluated`, `MediaRetentionExpired`.

## 6. Ubiquitous language glossary

Terms marked **(needs-verification)** depend on pickleball rules that are unverified in our research [DOM G1]. The domain coach must confirm each one, with its rule number, before code relies on it.

| Term | Definition | Context |
|---|---|---|
| Match | One recorded contest between two sides, with sport, format, scoring system, `rules_version`, video and calibration | Match & Scoring |
| Game | A unit of a match won by reaching the target score (needs-verification: 11, win by 2) | Match & Scoring |
| Rally | The play from serve until the ball is dead. It has start and end times, a server, the score before and after, a winner and how it ended | Match & Scoring |
| Shot | One hit by one player within a rally, with type, time, position, outcome, confidence and `corrected_by_user` | Match & Scoring |
| Side | One of the two teams (doubles) or players (singles) | Match & Scoring |
| Server number | In doubles, which partner of the serving side is serving: 1 or 2 (needs-verification) | Sport Plug-in |
| Side-out | Serve passing to the other side (needs-verification) | Sport Plug-in |
| Side-out scoring | Only the serving side can score (needs-verification, DOM G1 R2) | Sport Plug-in |
| Rally scoring | Either side can score on any rally. Reported as a provisional rule in 2026 (needs-verification, DOM G1 R3) | Sport Plug-in |
| Rules version | The rulebook edition the engine applies, e.g. `USAP-2026` | Sport Plug-in |
| Non-volley zone (NVZ) / kitchen | The zone next to the net where volleying is not allowed (needs-verification, DOM G1 R5) | Sport Plug-in |
| Two-bounce rule | The serve and the return must each bounce before being struck (needs-verification, DOM G1 R4) | Sport Plug-in |
| Fault | A rule violation that ends the rally (needs-verification) | Sport Plug-in |
| Third shot drop / drive | The serving side's first shot after the return, played soft into the NVZ (drop) or hard (drive) (needs-verification, DOM G2 C1) | Sport Plug-in |
| Dink, drive, drop, lob, volley, speed-up, reset, erne, ATP | Shot taxonomy classes from spec §3. Definitions are owned by the domain coach (needs-verification) | Sport Plug-in |
| Transition zone | The area between the baseline and the NVZ line that players move through (needs-verification) | Sport Plug-in |
| Court calibration | The homography from image pixels to court coordinates. Valid only for points on the court plane [DOM/CV-12] | Vision Analysis |
| Event | A raw detected hit or bounce, with time, position and confidence, kept for re-processing | Vision Analysis |
| Confidence | The system's probability-like score for an automatic call, shown to the user [DPA/DESIGN-11] | Vision / Match |
| Correction | A user change to an automatic call. It is audited and becomes training data | Match & Scoring |
| Visibility | Whether the ball is visible in a frame. Not visible means unknown, not guessed [DOM/CV-01] | Vision Analysis |
| Metric snapshot | Metrics per player per match, with sample size | Analytics |
| Low-sample metric | A metric whose sample is too small to rely on. It is shown and flagged, never hidden (spec §5) | Analytics |
| Point leak | A weakness measured as points lost per match that can be attributed to it (spec §6) | Coaching |
| Drill | A vetted exercise with skill, level, duration, players, equipment and target metric | Drill Library |
| Training plan | Sessions of drill assignments, each with a "why" linked to evidence | Coaching |
| Opponent profile | A user-created record of a third-party opponent, private to its creator [AQS/SEC-03] | Identity & Players |
| Scouting report | Opponent tendencies merged across ≥ 2 matches (spec M6) | Analytics |
| Pipeline version | The identifier of the model and config set that produced events | Vision Analysis |
