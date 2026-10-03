# Big Picture EventStorming: racket-analytics

- **Status:** First pass, accepted as the Sprint 0 input to the context map (principal-engineer, 2026-10-03). Revisit at Sprint 2 planning with a Process Modelling session on the analysis pipeline.
- **Method:** Big Picture first, then Process Modelling for the Sprint 0 slice only. The notation follows the DDD Crew cheat sheet [EP/ENG-14]:
  - domain events (orange), past tense;
  - commands (blue);
  - policies (lilac);
  - read models (green);
  - actors (yellow);
  - external systems (pink-ish, labelled `ext`);
  - hotspots (pink, labelled **H#**).

  This is step 2 ("Discover") of the starter process [EP/ENG-11].
- **How it was run (honest scope):** a desk session by the principal-engineer. It worked over the spec, the four brainstorms (`docs/requirements/brainstorm-*.md`), the FR/NFR set, ADRs 0003, 0006 and 0009, and the seed events in ddd-guidelines §5 plus ENG §2. The domain coach, PM and designer took part through their written brainstorms, not live. No human domain expert attended. Every pickleball rule touched here is still **needs-verification** [DOM G1]. A live session with the domain coach and the PO is recommended before R2 (open question ES-1).
- **Output:** the context boundaries in `context-map.md`, the canvases in `contexts/`, and the hotspot list in §5, which feeds Sprint 1+ stories and ADRs.

## 1. Actors and external systems

| Kind | Name | Notes |
|---|---|---|
| Actor | **Player** (account owner, e.g. Ivy) | Films, uploads, reviews, corrects, trains. Possibly a minor (FR-003; unverified law [AQS G3.5]) |
| Actor | **Opponent / partner** (third party) | Appears in footage. Exists in the system only as a nickname on the owner's records (FR-005) |
| Actor | **Domain coach** (team role) | Curates drills and verifies rules |
| Actor | **Worker** (system) | Runs pipeline stages from the job queue |
| ext | **Object store** (S3-compatible) | Media bytes |
| ext | **GPU provider** | Vision stages (R2; SPIKE-04) |
| ext | **LLM provider** | Drill selection (R2; ACL) |
| ext | **Mail** (Mailpit in dev) | Magic links (Sprint 1) |

## 2. Timeline (Big Picture)

Read left to right. Pivotal events are in **bold**; they are the boundaries where the language changes.

| Phase | Domain events, in order | Emerging context |
|---|---|---|
| 1. Onboarding | `AccountRegistered` → `SignedIn` → `AgeConfirmed` → `FootageNoticeAcknowledged` → (`TrainingConsentGranted` \| `TrainingConsentRevoked`) | Identity & Players; Dataset & Labelling (consent) |
| 2. Match setup | `MatchCreated` → `ParticipantsNamed` → `OpponentProfileCreated` | Match & Scoring; Identity & Players |
| 3. Capture and upload | `UploadStarted` → `UploadChunkStored`* → (`UploadPaused`† → `UploadResumed`†) → **`MatchUploaded`** → `MediaProbed` \| `ProbeFailed` → `UploadQualityChecked` \| `QualityGateFailed` → `MediaNormalised`. Side branches: `UploadRejected` (validation), `UploadExpired` (24 h, ADR 0006) | Capture & Media |
| 4. Analysis | `AnalysisJobQueued` → `JobClaimed` → (`JobRequeued` \| `StageFailed`) → `CourtCalibrated` → `CourtCalibrationConfirmed` → `PlayersIdentified` → `IdentityConfirmed` → `BallTracked` → `HitDetected` / `BounceDetected` → `RallySegmented` → `ShotClassified` → (`AnalysisLevelDegraded`) → **`AnalysisCompleted`** | Vision Analysis |
| 5. Scoring and review | `RallyScored` → `RallyOutcomeConfirmed` → `ScoreCorrected` / `ShotCorrected` → **`MatchScored`** | Match & Scoring (incl. Review & Correction, C4) |
| 6. Analytics | `MetricSnapshotComputed` → `WeaknessesRanked` | Analytics |
| 7. Coaching | `TrainingPlanGenerated` (or `PlanProposalRejected` by the validator) → `TrainingSessionCompleted` → `TrainingPlanEvaluated` | Coaching (incl. drills module, C1) |
| 8. Retention and deletion | `MatchDeletionRequested` → `MatchHidden` → `MatchDeleted`; `OriginalVideoPurged`; `MediaRetentionExpired` | Capture & Media; Match & Scoring |
| 9. Learning loop | `LabelSetExtended` (only with consent) → `GoldSetFrozen` → `PipelineEvaluated` | Dataset & Labelling; Vision Analysis |

\* `UploadChunkStored` is internal and never published. It exists so the offset rule has a name.
† `UploadPaused` and `UploadResumed` happen on the client. The server only sees the HEAD and PATCH that follow (FR-022). They are **not** server events.

**New relative to the seed list** (ddd-guidelines §5 plus ENG §2):
- `UploadChunkStored`, `UploadRejected`, `UploadExpired`, `MediaProbed`, `ProbeFailed`;
- `AnalysisJobQueued`, `JobClaimed`, `JobRequeued`, `StageFailed`, `AnalysisCompleted`;
- `CourtCalibrationConfirmed`, `PlanProposalRejected`, `TrainingSessionCompleted`;
- `MatchHidden`, `OriginalVideoPurged`, `LabelSetExtended`, `GoldSetFrozen`, `PipelineEvaluated`;
- the onboarding events.

## 3. Pivotal events and why the boundaries fall there

| Pivotal event | Language before | Language after | Boundary |
|---|---|---|---|
| `MatchUploaded` | bytes, offsets, chunks, object keys | media facts, frames, fps | Capture & Media → Vision Analysis (R3), and the `Match` lifecycle (R2) |
| `AnalysisCompleted` | detections, heatmaps, confidences, tracks | rallies, shots, score | Vision Analysis → Match & Scoring through an ACL (R4) |
| `MatchScored` | the authoritative, user-corrected match record | metrics, trends, sample sizes | Match & Scoring → Analytics (R6) |
| `WeaknessesRanked` | rallies lost per game (ADR 0003) | drills, sessions, "why" | Analytics → Coaching (R8) |

## 4. Process Modelling: the Sprint 0 slice (walking skeleton)

Grammar: Actor → Command → Aggregate → Event → Policy → Command …; read models feed the actor.

```
Ivy ──(SignIn [dev])──────────────▶ Session ─────────▶ SignedIn
Ivy ──(CreateMatch title,format)──▶ Match ───────────▶ MatchCreated            (status read model: awaiting_upload)
Ivy ──(StartUpload length)────────▶ UploadSession ───▶ UploadStarted           (read model: uploading)
Ivy ──(SendChunk offset,bytes)────▶ UploadSession ─┬─▶ UploadChunkStored
                                                   └─▶ ✗ OffsetMismatch (409; state unchanged)
                     policy P1: "when the final byte is stored"
                         ├─▶ (MarkUploaded media_asset_id) ─▶ Match ─▶ MatchUploaded   (read model: video_received)
                         └─▶ (EnqueueStage probe) ─────────▶ Job ───▶ AnalysisJobQueued(probe)
Worker ──(ClaimJob)───────────────▶ Job ─────────────▶ JobClaimed
                     policy P2: "when SIGTERM arrives during a stage" ─▶ (Requeue) ─▶ Job ─▶ JobRequeued (≤ 10 s)
Worker ──(RunProbe)───────────────▶ MediaAsset ──┬───▶ MediaProbed (facts)     (read model: media facts)
                                                 └───▶ ProbeFailed            (read model: probe_failed; no partial facts)
                     policy P3: "when a stage raises" ─▶ (FailJob, roll back stage writes) ─▶ StageFailed
Ivy ◀── read model "Match detail": title, status label, Duration · fps · resolution
```

| Element | Kind | Owner context | Sprint 0 artefact |
|---|---|---|---|
| `Match` | aggregate | Match & Scoring | `racket.matches.domain` (sprint-00 §5 tests 1-5) |
| `UploadSession` | aggregate | Capture & Media | `racket.video_ingest` (§5: OffsetMismatch, length, advance, is_complete) |
| `MediaAsset` (+ `MediaFacts` value object) | aggregate | Capture & Media | `MediaFacts.from_ffprobe` |
| `Job` (+ `JobKey`) | aggregate | Vision Analysis (job runtime, OHS) | `racket.analysis_jobs` |
| `ObjectKeyPolicy` | domain service | Capture & Media | never derives keys from user input |
| P1 final byte → mark uploaded and enqueue probe | policy | Capture & Media, invoking Match and the job runtime | same transaction, **H3** |
| P2 SIGTERM → requeue | policy | job runtime | NFR-046 |
| P3 stage raises → fail closed | policy | job runtime | NFR-047 [AQS/SEC-12] |
| Match detail | read model | Match & Scoring API, composed with `video_ingest.media_summary` | API §5.1 |

## 5. Hotspots

| # | Hotspot | Status and owner | Where it goes |
|---|---|---|---|
| H1 | "Point leak" vs rallies lost: under side-out scoring, a lost serve concedes no point | ADR 0003 (Proposed) chose rallies lost per game, split serve/receive. The glossary is updated (ddd-guidelines §6). Needs the coach to verify the rule [DOM G1 R2] | Coaching, Analytics |
| H2 | Side-out vs rally scoring, server number, two-bounce, NVZ: all unverified | needs-verification (domain coach; OQ-01 rulebook PDFs). ADR 0009 splits engine readiness | Sport Plug-in |
| H3 | Upload completion changes three things in one transaction (`UploadSession` complete, `Match.mark_uploaded`, probe job row), against "one aggregate per transaction" | **Accepted as a scoped exception** in ADR 0011. Revisit with an outbox when a second consumer of `MatchUploaded` exists (context map CM-2) | Capture & Media / Match & Scoring |
| H4 | Legal basis for training on user video and for footage of third parties and minors | **Unverified** [AQS G3.5]. NFR-070 gate; OQ-05, OQ-06 (PO) | Dataset & Labelling; Identity & Players |
| H5 | Who owns the probe stage: Vision or Capture & Media? | **Resolved**: Capture & Media owns the stage code; the job runtime is an OHS (C3 clarification) | context map R7 |
| H6 | Abandoned-upload expiry (24 h vs 7 days) and match deletion windows | ADR 0006 (Proposed), PO decision OQ-07 | Capture & Media |
| H7 | Re-processing vs user corrections: which wins? | "User corrections win" (ddd-guidelines §4.8, judgment); needs a test when R2 reprocessing exists | Match & Scoring |
| H8 | Identifying "which player is me" without face recognition | NFR-065 hard constraint; within-match re-id only; `IdentityConfirmed` is a user command | Vision Analysis |
| H9 | Sprint 0 allows one upload per match; a client that lost its upload URL cannot restart | Accepted for Sprint 0 (API §6.2). Sprint 1 adds expiry/delete and restart | Capture & Media |
| H10 | Analysis level degradation must be an explicit state, not a partial write | FR-026; NFR-047; design in the R2 Process Modelling session | Vision Analysis |

## 6. Open questions

| # | Question | Owner |
|---|---|---|
| ES-1 | Run a live Big Picture session with the domain coach and PO, to validate phases 4-7 before R2 Ready | engineering-manager to schedule; principal-engineer facilitates |
| ES-2 | Is `OpponentProfileCreated` an Identity & Players event (a third-party record) or an Analytics concern (scouting)? Currently Identity & Players, because it holds personal data with creator-only scope [AQS/SEC-03] | principal-engineer, security-privacy-engineer, at M6 |
