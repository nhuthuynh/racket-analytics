# Context map

- **Status:** Accepted for Sprint 0 and R1 (principal-engineer, 2026-10-03). It replaces the provisional map in `docs/process/ddd-guidelines.md` §2-§3, which now points here.
- **Inputs:** the Big Picture EventStorming (`eventstorming.md`), ENG §2 C1-C5 (`docs/requirements/brainstorm-engineering.md`), the spec, and the code as it stands (`backend/src/racket/*`).
- **Method:** context-mapping patterns [EP/ENG-13]; canvases [EP/ENG-12]; the DDD starter process Decompose → Strategize → Connect [EP/ENG-11]. Applying the patterns to this product is (judgment).

## 1. Decisions on ENG §2 C1-C5

| # | Proposal | Decision | Reasoning | Evidence |
|---|---|---|---|---|
| **C1** | Merge Drill Library into Coaching for the MVP as `coaching/drills` with its own `library_version` | **Accepted.** Drill Library is a **module of Coaching**, not a context. `Drill` stays its own aggregate, and `library_version` is kept on `TrainingPlan` (ddd-guidelines §4.7) | One team, one deployable, about 80 drills (spec M5). The EventStorming found no event that the library emits without Coaching consuming it, and no separate actor before coaches author drills (judgment). A context-map edge with no separate model is overhead [AQS/ENG-04] | EventStorming §4: Drill events only appear in the Coaching swimlane; spec M5 |
| **C2** | Add a "Dataset & Labelling" supporting context from M0 | **Accepted** as a **Supporting** context, code module `racket.dataset` (it already exists: `ManifestCheck`). Aggregates: `GoldSet` (frozen, versioned), `LabelSet`, `TrainingConsent` | Training on a user's video is a different purpose from analysing that user's match. It needs its own consent flag and retention. The legal basis is unverified [AQS G3.5] → NFR-070, OQ-06. Gold sets are frozen and never edited to raise a score [EP/ENG-27, EP/ENG-28] | `backend/src/racket/dataset/manifest.py`; decision-log 2026-10-03 (QA, ManifestCheck); FR-151, NFR-078 |
| **C3** | Split Vision Analysis into `analysis_jobs` (orchestration in the API repo) and `workers/*` (model stages): two modules of one context, sharing only artefact schemas | **Accepted.** One context, **two modules with different test layers**: `analysis_jobs` (job state machine, TDD, unit plus integration) and the vision stages under `worker`/`workers/*` (eval-driven). Clarification: the **job runtime** in `analysis_jobs` (`JobKey`, `JobQueue`, runner) is offered to other contexts as an Open Host Service, and each stage's code belongs to the context whose model it writes. The Sprint 0 `probe` stage writes `MediaAsset` facts, so it belongs to **Capture & Media** (relationship R7 below) | Transactional job code and model stages have different correctness evidence (tests vs evals) [EP/ENG-17, EP/ENG-27]. ENG §1.2 stage 0 (probe) produces media facts, not observations | sprint-00 §5 (`JobKey`, `Job` in `analysis_jobs`; `MediaFacts.from_ffprobe` in `video_ingest`); ADR 0012 seams `racket.analysis_jobs.queue:JobQueue`, `racket.video_ingest.repository:count_media_facts` |
| **C4** | Review & Correction lives in Match & Scoring, not a new context | **Accepted.** Corrections are commands on the `Match` aggregate that emit `ScoreCorrected`/`ShotCorrected` | A correction must re-run the rules replay atomically with the match record (ddd-guidelines §4.1) | EventStorming §4 Review swimlane: every correction command targets `Match` |
| C5 | Opponent scouting stays in Analytics until M6 | **Accepted** (unchanged) | Not MVP | spec M6 |

## 2. The map

```
                               ┌──────────────────────────┐
                               │   Identity & Players     │  Generic
                               │   (players)              │
                               └────────────┬─────────────┘
                                 OHS: current_account, ownership (R1)
          ┌──────────────────────────────┬──┴───────────────┬──────────────────────┐
          ▼                              ▼                  ▼                      ▼
 ┌──────────────────┐   C/S (R3)  ┌──────────────────┐ ACL (R4) ┌─────────────────────┐
 │ Capture & Media  │────────────▶│ Vision Analysis  │─────────▶│  Match & Scoring    │ Core
 │ (video_ingest)   │             │ (analysis_jobs + │          │ (matches, scoring)  │
 │ Supporting       │             │  vision stages)  │          │ incl. Review &      │
 └───┬──────────┬───┘             │ Core             │          │ Correction (C4)     │
     │          │  ◀── OHS job ───┤                  │          └──────┬───────┬──────┘
     │          │   runtime (R7)  └────────▲─────────┘                 │       │
     │          │                          │ C/S gold sets (R10)       │ C/S events (R6)
     │          └──── C/S media summary, MatchUploaded (R2) ──────────▶│       ▼
     │                                     │                    ┌──────┴───────────────┐
     │                          ┌──────────┴───────────┐        │     Analytics        │ Core
     └──── C/S (R9) ──────────▶ │ Dataset & Labelling  │◀─(R9)──│ (+ scouting to M6)   │
          consent-gated media   │ (dataset) Supporting │        └──────────┬───────────┘
                                └──────────────────────┘                   │ C/S (R8)
                                                                           ▼
 ┌───────────────────────────┐   Published Language (R5)        ┌─────────────────────┐
 │ Sport Plug-in: pickleball │ ───────────────────────────────▶ │ Coaching            │ Core
 │ (sports/pickleball) Core  │   to Match, Vision, Analytics,   │ (+ drills module,C1)│
 └───────────────────────────┘   Coaching                       └─────────▲───────────┘
                                                                          │ ACL (R11)
                                                                    LLM provider (external)
```

C/S = Customer/Supplier (the arrow points from supplier to customer); OHS = Open Host Service; ACL = Anticorruption Layer, owned by the downstream side.

## 3. Relationships

| # | Upstream → Downstream | Pattern | What crosses the boundary | Sprint |
|---|---|---|---|---|
| R1 | Identity & Players → every context | **Open Host Service**; the downstream contexts are **Conformist** on `AccountId` | The FastAPI dependency `current_account` (an `AccountId` UUID or 401) and the ownership-loading pattern `WHERE id = :id AND owner_id = :me` [AQS/SEC-09; AQS/STACK-01 G7.5]. No context reads account tables | S0 (dev identity), S1 (real sign-in) |
| R2 | Capture & Media → Match & Scoring | **Customer/Supplier** | The event `MatchUploaded(match_id, media_asset_id)` and the query port `video_ingest.media_summary(match_id) → {upload_state, facts \| None, probe_failed}`, which the match read model uses for `status`/`media` (API §5.1). Match & Scoring never reads `video_ingest` tables. **Sprint 0 exception:** `Match.mark_uploaded` runs in the same transaction as upload completion (ADR 0011; hotspot H3) | S0 |
| R3 | Capture & Media → Vision Analysis | **Customer/Supplier** | `MediaAsset` facts (fps, VFR, duration, resolution) and a presigned GET with a TTL of 15 min or less (NFR-055). Vision never sees upload mechanics, user file names or object keys | S2+ |
| R4 | Vision Analysis → Match & Scoring | **Anticorruption Layer** in Match & Scoring | Artefact schemas (`EventTrack`: hits, bounces, with confidences and `pipeline_version`), translated by the ACL into `Rally`/`Shot` language. Model vocabulary (boxes, heatmaps) stays out of the match record | R2 |
| R5 | Sport Plug-in → Match & Scoring, Vision, Analytics, Coaching | **Published Language** | `RulesConfig`, the rules state machine (a pure function), `CourtModel`, `ShotTaxonomy`, metric definitions, drill tags. Versioned by `rules_version`. New sports add plug-ins (NFR-082) | S1+ |
| R6 | Match & Scoring → Analytics | **Customer/Supplier** via domain events | `RallyScored`, `ScoreCorrected`, `MatchScored`, consumed idempotently after commit (ddd-guidelines §4.6) [AQS/OPS-02] | S1+ |
| R7 | Vision Analysis (`analysis_jobs` job runtime) → Capture & Media | **Open Host Service** | `JobQueue.enqueue(JobKey(match_id, pipeline_version, stage))`, the stage registry `racket.worker.stages:STAGES`, and the runner semantics: claim, requeue on SIGTERM, fail closed [AQS/OPS-02, AQS/SEC-12]. Capture & Media registers the `probe` stage and owns its code (C3 clarification) | S0 |
| R8 | Analytics → Coaching | **Customer/Supplier** | Metric snapshots with sample sizes and evidence links (rally IDs); weakness ranking input per ADR 0003 | R1 later sprints |
| R9 | Capture & Media, Match & Scoring → Dataset & Labelling | **Customer/Supplier**, gated by consent | `ShotCorrected`/`ScoreCorrected`, plus media references, flow to `LabelSet` **only if** `TrainingConsent` is granted for that account. Without consent nothing crosses (NFR-070; OQ-06) | R2 |
| R10 | Dataset & Labelling → Vision Analysis | **Customer/Supplier** | Frozen `GoldSet` versions (manifest plus sha256) for evals; Vision never edits a gold set [EP/ENG-27] | S0 (fixture manifest), R2 |
| R11 | LLM provider (external) → Coaching | **Anticorruption Layer** | The prompt builder sends pseudonymous aggregates only (NFR-068). The validator rejects unknown drill IDs and metrics before anything persists [AQS/SEC-08 API10] (NFR-059) | R2 |

**Removed edge:** Drill Library → Coaching (C1; now a module inside Coaching).

## 4. Rules that follow from the map

1. **No cross-context table reads.** A context reads another context's data only through that context's published port (a Python module `racket.<ctx>.public` or `racket.<ctx>.events`), never through its domain package, repository, ORM models or service. `racket.<ctx>.api` is the context's HTTP router, not a port; the one exception is `racket.players.api`, which hosts the R1 Open Host Service dependency `CurrentAccount`. The R7 job runtime is open to every context through `racket.analysis_jobs.{domain,queue,stage}`, and `racket.sports` is R5 Published Language. `racket.platform` (shared kernel), `racket.worker` and `racket.migrations` (composition roots) are not contexts. Enforced by `backend/tests/unit/test_architecture_context_imports.py` (amended 2026-10-03, R2-02: the port was named `.api` here while the code used `.public`).
2. **The domain layer imports no framework.** `racket.<ctx>.domain` imports no FastAPI, SQLAlchemy, boto3 or OpenTelemetry (ddd-guidelines §4.5). This is already enforced by `backend/tests/unit/test_architecture.py` (its `FORBIDDEN` set).
3. **IDs only across boundaries.** Aggregates reference other aggregates by UUID (ddd-guidelines §4.3).
4. **Every context's root carries `owner_id`**, and loads go through the R1 ownership pattern (ddd-guidelines §4.9).
5. **Stage code belongs to the context whose model it writes.** The job runtime (R7) is shared infrastructure, not a shared model.

## 5. Open questions

| # | Question | Owner | Needed by |
|---|---|---|---|
| CM-1 | Should the job runtime move from `analysis_jobs` to `platform/queue` once a second non-vision stage exists (normalise, R2)? Moving it changes the ADR 0012 seam `JOB_QUEUE` | principal-engineer, QA | Sprint 2 planning |
| CM-2 | Does an outbox replace the same-transaction exception in R2 once Analytics or Dataset consume `MatchUploaded`? | principal-engineer | When a second consumer appears |
| CM-3 | Do coaches author drills independently (which would split Drill Library out again, reversing C1)? | product-manager, domain coach | M5 |
