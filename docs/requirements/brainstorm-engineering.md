# Requirements Brainstorm: Engineering Perspective

- **Date:** 2026-10-03
- **Status:** Brainstorm input for the business-analyst. Nothing here is an accepted requirement until it appears in the BA's FR/NFR register and an ADR where relevant.
- **Perspective:** principal-engineer (lead), senior-backend-engineer, senior-ml-cv-engineer, sre-devops-engineer, security-privacy-engineer.
- **Inputs read:** `docs/specs/2026-10-02-racket-analytics-design.md` (cited as "spec §n"), `.claude/agents/*.md` for the five roles, `docs/research/*.md`, `docs/process/*.md`.
- **Citation convention:** `<file>/<ID>` per `docs/process/working-agreement.md` §0 (EP, AQS, DPA, DOM). Anything not backed by a verified source is labelled **(judgment)**. Numbers marked (judgment) are starting targets to be replaced by spike data; they are not evidence.
- **Proposed IDs:** `ENG-FR-*`, `NFR-<area>-*`, `SPIKE-*`, `RISK-*` are suggestions for the BA to renumber.

---

## 0. Summary of positions

1. **The MVP is M0 + a thin slice of M1–M3, not M0–M5.** The first milestone ("upload a recorded match -> stats -> training plan") can be delivered end to end on **manual or assisted tagging** first (spec §7 already says this), with automation added stage by stage behind the same `Rally`/`Shot` contract (judgment).
2. **Licence blocker:** the spec's stack names Ultralytics and "YOLO + ByteTrack". Ultralytics is AGPL-3.0 or paid Enterprise [DOM/CV-05]; BoxMOT is AGPL-3.0 [DOM/CV-07]. For a closed SaaS, default to MIT/Apache components (ByteTrack MIT [DOM/CV-04], supervision MIT [DOM/CV-16], MMPose/RTMPose Apache-2.0 [DOM/CV-11], TrackNetV3 MIT [DOM/CV-01]) unless the human approves an Enterprise licence via ADR.
3. **GPU budget is at risk on the spec's own numbers.** TrackNetV3 reports 25.11 FPS [DOM/CV-01] and ByteTrack 29.6 FPS on a V100 [DOM/CV-04]. Running either at the spec's 60 fps capture rate would alone cost about 2.0–2.4 GPU-min per match-minute, above the spec's 1–2 budget (spec §8). Frame-rate strategy and batching must be proven in a spike before M2 is committed (§5, SPIKE-03).
4. **"≤1 correction per game" (spec M3) implies about 97% rally-outcome accuracy** (§5.4). That is not credible for a single phone camera that, per the spec's own premise, cannot make referee-grade line calls (spec §2). Re-define the M3 target (§5.4).
5. **"Height over the net" (spec §4 `Shot`) cannot be measured from a ground-plane homography** [DOM/CV-12]. Drop it from v1 or make it a later 3D spike.
6. **Two research gaps are release blockers, not sprint blockers:** pickleball rules are unverified [DOM G1, Gaps 1] and privacy law (GDPR, minors, video of third parties) is unverified [AQS G3.5, AQS Gaps]. Neither stops M0 engineering; both stop real-user beta.

---

## 1. Architecture

### 1.1 Shape (agree with spec §3, with changes)

- **Three deployables plus backing services** (judgment, consistent with [AQS/OPS-04], [AQS/STACK-01]):
  1. `api` (FastAPI, stateless, `def` routes unless fully async [AQS/STACK-02]); no CPU/GPU work in-process [AQS/STACK-01].
  2. `worker-cpu` (FFmpeg probe/normalise, audio onsets, rules replay, analytics, coaching workflow).
  3. `worker-gpu` (court, players, ball, pose, shot classification) on serverless GPU.
  4. Postgres, S3-compatible object storage, one job queue. Same three backing services in dev via Docker Compose; no SQLite [AQS/OPS-05], [AQS/STACK-03].
- **Queue choice (judgment): Postgres-backed queue first** (e.g. `SELECT ... FOR UPDATE SKIP LOCKED` job table) rather than Redis. Reasons: one fewer backing service, transactional enqueue with the domain write (outbox), and survival of sudden process death [AQS/OPS-02 requires a queue backend that survives this]. Revisit by ADR if queue throughput exceeds ~50 jobs/s (judgment; far above MVP load).
- **Serverless GPU interaction (judgment):** GPU workers pull stage tasks or are invoked per chunk by `worker-cpu`; either way each invocation is idempotent and keyed by `(match_id, pipeline_version, stage, chunk_idx)` [AQS/OPS-02]. Requeue on SIGTERM / preemption [AQS/OPS-02].
- **Workers do not get broad DB credentials.** GPU workers read a signed media URL and write stage artefacts to a job-scoped storage prefix; `worker-cpu` validates and commits them to Postgres. Least privilege for service accounts [AQS/SEC-06 13.2.2], short-lived tokens not static shared keys [AQS/SEC-06 13.2.1].
- **Chunked processing for wall-clock latency (judgment):** split normalised video into ~120 s chunks with ~2 s overlap; per-chunk GPU stages run in parallel; a CPU merge step stitches tracks and identities across chunk boundaries. This is the main lever for the turnaround SLO (§4.2) without paying for idle GPUs.
- **Live mode (M7) is out of scope for the MVP architecture.** Do not add streaming abstractions now; reviewers push back on speculative over-engineering [AQS/ENG-04]. Only constraint now: stage functions take a frame window + state, so they can later run windowed (judgment).

### 1.2 Pipeline stages (refines spec §3)

| # | Stage | Runs on | Input | Output artefact | Notes |
|---|---|---|---|---|---|
| 0 | Ingest & probe | CPU | uploaded object | `media.json` (container, codec, fps, VFR flag, duration, audio present) | Magic-byte / ffprobe type check, size and duration caps [AQS/SEC-02 5.2.1, 5.2.2] |
| 1 | Normalise | CPU | original | CFR 60 fps (or source fps if lower) mezzanine + 16 kHz mono WAV + 720p review proxy | Phones often record variable frame rate (judgment); CFR is required so frame index <-> time is exact for audio/video fusion |
| 2 | Quality gate | CPU/GPU light | sample frames | quality report (court visible, fps, resolution, lighting score) | Spec §8 "quality check on upload"; result drives graceful degradation |
| 3 | Court calibration | GPU light | sampled frames | homography H + reprojection error + method (`auto`/`manual`) | Use all line intersections, RANSAC; 4-corner manual fallback [DOM G6 H2] |
| 4 | Player detection + tracking | GPU | frames at reduced rate | tracks with boxes, foot points (court coords) | Tracker pinned in config [DOM G4 P3] |
| 5 | Identity resolution | CPU | tracks + user taps | 4 (or 2) stable player slots | Constraint: 2 per side; user confirms once per match [DOM G4 P4]; no face recognition (spec §8) |
| 6 | Pose | GPU or CPU | player crops | 17-kp COCO keypoints | RTMPose via ONNX Runtime [DOM G5 PO1, PO2] |
| 7 | Ball tracking | GPU | 60 fps frames | per frame `Frame, Visibility, X, Y` | TrackNetV3 baseline fine-tuned [DOM/CV-01] |
| 8 | Audio onsets | CPU | WAV | onset times + strength | librosa spectral flux; `delta`, `wait` as config [DOM/CV-14] |
| 9 | Event fusion | CPU | 4, 6, 7, 8 | `Event` (hit, bounce) with confidence | Bounce as separate learned step [DOM G3 B5] |
| 10 | Rally segmentation | CPU | events, audio | rally intervals + serve detection | M2 target (§5.4) |
| 11 | Shot classification | CPU/GPU | events, pose, positions | `Shot.type` + confidence | Hierarchical taxonomy (§5.5) |
| 12 | Rules replay | CPU | rally outcomes | score per rally | Pure function, `rules_version` [EP/ENG-17 via ddd-guidelines §4.5] |
| 13 | Analytics | CPU | match record | `MetricSnapshot` | Recomputed on `RallyScored` / `ScoreCorrected` |

Every stage is a checkpointed transaction: either the full artefact is committed or nothing is; a failed stage marks the job failed and rolls back partial writes [AQS/SEC-12]. "Score only, no shot detail" degradation (spec §8) is an explicit `analysis_level` state, not a partial write [AQS implications].

### 1.3 Interfaces between contexts

- Vision -> Match & Scoring is an **Anticorruption Layer**: model vocabulary (boxes, heatmaps, track IDs) never enters `Rally`/`Shot` [EP/ENG-13, ddd-guidelines §3].
- Coaching -> LLM provider is an ACL; LLM output is untrusted and validated [AQS/SEC-08 API10].
- **Contract tests (judgment):** each stage artefact has a versioned JSON Schema / Pydantic model; producer and consumer both test against the same fixture. Breaking a schema bumps `pipeline_version`.
- Trace context is injected on enqueue and extracted in the worker so one trace covers upload -> analysis -> plan [AQS/OPS-06], [AQS/OPS-07].

---

## 2. Bounded contexts (review of ddd-guidelines §2)

Mostly agree with the eight contexts in `docs/process/ddd-guidelines.md`. Proposed changes, all (judgment), to be confirmed at the first EventStorming [EP/ENG-11, EP/ENG-14]:

| # | Change | Reason |
|---|---|---|
| C1 | **Merge Drill Library into Coaching for the MVP** as a module (`coaching/drills`) with its own `library_version`. | One team, one deployable, ~80 drills (spec M5). A separate context adds a context-map edge without a separate model. Split later if coaches author drills independently. |
| C2 | **Add a "Dataset & Labelling" supporting context** (from M0). Aggregates: `LabelSet`, `GoldSet` (frozen, versioned), `TrainingConsent`. | Spec §2 says "every correction becomes training data" and spec §7 says manual tags become the labelled dataset. Using user video for model training is a separate purpose from analysing the user's own match; it needs its own consent flag and retention (legal basis unverified [AQS G3.5]: flag to human). Gold sets are frozen per sprint and never edited to raise a score [testing-strategy §6]. |
| C3 | **Split "Vision Analysis" into `analysis_jobs` (orchestration, in API repo) and `workers/*` (model stages)** as two modules of one context, sharing only artefact schemas. | The job state machine is ordinary transactional backend code with TDD; model stages are eval-driven. Different test layers [testing-strategy §2]. |
| C4 | **Review & Correction lives in Match & Scoring**, not a new context. Corrections are commands on the `Match` aggregate producing `ScoreCorrected`/`ShotCorrected`. | Corrections must re-run rules replay atomically with the match record (one aggregate, one transaction; ddd-guidelines §4.1). |
| C5 | **Opponent scouting stays in Analytics until M6** (agrees with ddd-guidelines). | Not MVP. |

Event additions to the Big Picture seed (ddd-guidelines §5): `MediaNormalised`, `QualityGateFailed`, `IdentityConfirmed`, `RallyOutcomeConfirmed`, `ShotCorrected`, `AnalysisLevelDegraded`, `TrainingConsentGranted`/`Revoked`, `MatchDeletionRequested`, `MatchDeleted`.

---

## 3. Data model (refines spec §4)

### 3.1 What goes in Postgres vs object storage

| Data | Volume estimate (judgment) | Store |
|---|---|---|
| Original video | 1080p60 phone H.264 ~15–20 Mbps -> ~110–150 MB per minute; 60 min match ~7–9 GB | Object storage, private bucket |
| Mezzanine (CFR) / review proxy (720p) | proxy ~25 MB/min | Object storage |
| Per-frame ball track, player boxes, pose | ~3,600 frames/min x 4 players x 17 keypoints -> too many rows | **Columnar artefact (Parquet) in object storage**, keyed by `(match_id, pipeline_version, stage)` |
| `Event` (hits, bounces) | ~10^1–10^2 per minute | Postgres |
| `Rally`, `Shot`, corrections, metrics, plans | small | Postgres |

Reason: Postgres row-per-frame would put ~10^6 rows per match into the OLTP database for data that is only read by re-processing (judgment). Spec §4 "Event kept for re-processing" is preserved at the event level; frame-level artefacts are retained per the retention policy (§6.1).

### 3.2 Entities (additions marked +)

- `Account` (+), `PlayerProfile`, `OpponentProfile` (creator-scoped [AQS/SEC-03 8.2.2]).
- `Match`: `id` (UUIDv4 public [AQS/SEC-09]), `owner_id`, sport, format, `scoring_system` (`side_out`|`rally`), **`rules_version`** (e.g. `USAP-2026`) [DOM G1 R1], `analysis_level` (+, `manual`|`score_only`|`full`), status.
- `MatchParticipant` (+): `match_id`, `slot` (A1, A2, B1, B2), `side`, nullable `player_profile_id` / `opponent_profile_id`, display label. Spec §4 leaves "who is in this match" implicit; identity is per match and user-assigned (spec §8).
- `MediaAsset` (+): kind (`original`|`mezzanine`|`proxy`|`clip`|`thumbnail`|`artefact`), generated object key [AQS/SEC-02 5.3.2], sha256, bytes, duration, fps, `retention_class`, `delete_after`.
- `UploadSession` (+): tus state (`offset`, `length`, `expires_at`) [AQS/STACK-06].
- `AnalysisJob` (+): `match_id`, `pipeline_version`, status; `StageRun` (+): `stage`, `chunk_idx`, attempt, status, `gpu_seconds`, `model_hash`, `config_hash`, started/finished. Unique key `(match_id, pipeline_version, stage, chunk_idx)` enforces idempotency [AQS/OPS-02].
- `CourtCalibration` (+): homography (9 floats), method, reprojection error, confirmed_by_user.
- `Event`: type (`hit`|`bounce`|`serve_start`|`dead_ball`), `t_ms`, frame, court x/y (only for ground-plane points [DOM/CV-12]), image x/y, `participant_slot`, sources (`video`|`audio`|`fused`), confidence, `pipeline_version`.
- `Rally`: `match_id`, `seq`, start/end ms, server slot, **outcome inputs** (`winner_side`, `ending` = winner|error|fault, fault type), confidence, `corrected_by_user`. **Score before/after is a projection** computed by rules replay, not an independently editable column (judgment): a correction to rally *n* replays *n..end* in the same transaction, so the score sheet can never disagree with `rules_version`.
- `Shot`: as spec §4, **minus "height over the net"** (see §0.5) **plus** `type_coarse`, `type_fine` (nullable), `type_confidence`, `source` (`auto`|`manual`).
- `Correction` (+, append-only audit): who, when, entity, field, old value, new value, reason. Corrections win over re-processing (ddd-guidelines §4.8).
- `MetricSnapshot`: per participant per match, with `n` (sample size) and `low_sample` flag (spec §5), `metric_def_version`.
- `TrainingPlan` -> `Session` -> `DrillAssignment` (spec §4) + `library_version`, `llm_model_id`, `prompt_version`, `evidence_refs[]`.
- `ShareGrant` (+): explicit sharing (spec §8 "sharing is explicit"); deny by default [AQS/SEC-03 8.2.1].
- `TrainingConsent` (+): see C2.

Every aggregate root carries `owner_id`; every load goes through an ownership dependency (ddd-guidelines §4.9, [AQS/STACK-01] G7.5).

---

## 4. Non-functional requirements (proposals)

SLIs are good-events / valid-events ratios with numeric SLOs and error budgets [AQS/REL-01], [AQS/REL-02]. Percentile targets are (judgment): the performance source defines response time, throughput and latency but prescribes no percentiles [DPA/DESIGN-16].

### 4.1 Performance

| ID | Requirement | Target |
|---|---|---|
| NFR-PERF-01 | API read endpoints (match, score sheet, dashboard) server latency | p95 ≤ 300 ms, p99 ≤ 800 ms at 50 RPS (judgment) |
| NFR-PERF-02 | Correction command (edit rally outcome -> replayed score + recomputed metrics visible) | p95 ≤ 1.5 s for a 3-game match (judgment) |
| NFR-PERF-03 | Upload throughput | Server never the bottleneck: sustain ≥ 50 Mbps per upload; client resumes after network loss without re-sending acknowledged bytes [AQS/STACK-06] |
| NFR-PERF-04 | Time-to-results (upload complete -> stats available), `full` analysis | p50 ≤ 0.5x match duration, p90 ≤ 1.0x match duration, hard cap 2 h (judgment; depends on chunk parallelism, SPIKE-04) |
| NFR-PERF-05 | Time-to-results, `manual` tagging path (M0) | Score sheet and stats p95 ≤ 5 s after last tag saved (judgment) |
| NFR-PERF-06 | Training plan generation | p95 ≤ 60 s (judgment), async with notification |
| NFR-PERF-07 | Unit test suite runtime | whole backend unit suite ≤ 60 s locally; each test milliseconds [EP/ENG-17] (the 60 s ceiling is judgment) |

### 4.2 Reliability (SLOs, monthly window)

| ID | SLI | SLO (judgment) | Error budget |
|---|---|---|---|
| NFR-REL-01 | API availability: non-5xx responses / all responses (excl. 429) | 99.5% | 0.5% ≈ 3.6 h/month [AQS/REL-02 formula] |
| NFR-REL-02 | Upload completion: uploads reaching full length / uploads started and resumed by a live client | 99.0% | 1.0% |
| NFR-REL-03 | Analysis success: jobs reaching `full` or an explicit degraded level / jobs that passed the quality gate | 97% | 3% |
| NFR-REL-04 | Analysis freshness: jobs finished within NFR-PERF-04 p90 | 90% | 10% |
| NFR-REL-05 | Data durability: no loss of committed match records or confirmed corrections | RPO ≤ 24 h for DB (daily backup + WAL), RPO 0 for objects already committed (judgment); restore drill once per quarter with measured RTO ≤ 4 h |

- Do not engineer beyond what we can sustain; 99.5% is chosen deliberately below "three nines" for a pre-PMF product [AQS/REL-01]. Internal SLO tighter than any future SLA [AQS/REL-01].
- Maintenance windows count against the budget unless explicitly accepted [AQS/REL-02].
- Error-budget policy: budget exhausted -> next sprint prioritises reliability work (judgment applying [AQS/REL-02]; specific SRE workbook policy rules are unverified [AQS Gaps]).
- Retries: per-stage max 3 attempts with exponential backoff, then a terminal `failed` state surfaced to the user and an alert (judgment; AWS retry guidance and DLQ patterns are unverified [AQS Gaps]).
- Idempotency: a re-run of any stage produces byte-identical row sets for the same inputs and `pipeline_version` (no duplicates) [AQS/OPS-02]; tested by the worker-crash suite [testing-strategy §5].
- Graceful shutdown: workers requeue on SIGTERM within 10 s; API drains in-flight requests within 30 s (judgment numbers) [AQS/OPS-02].

### 4.3 Scalability and capacity (judgment, sized for MVP)

- Design point: 1,000 MAU, 4 matches/user/month, 60 min average -> 240,000 match-minutes/month; peak 3x on weekends.
- At 1.5 GPU-min per match-minute: ~360,000 GPU-min/month ≈ 6,000 GPU-h/month. **This is the dominant cost and must be reported to the human as a spend decision** (escalation rule in sre-devops-engineer and principal-engineer agent files).
- Storage growth if originals kept 30 days: ~240,000 min x ~130 MB ≈ 31 TB rolling (judgment). This is why §6.1 proposes short original retention plus a 720p proxy.
- Horizontal scale: API and workers are stateless [AQS/OPS-04]; GPU concurrency capped by a config limit and by provider spending limits [AQS/SEC-10].

### 4.4 Cost per match-minute

| ID | Requirement | Target |
|---|---|---|
| NFR-COST-01 | GPU-seconds per match-minute, `full` analysis | ≤ 90 GPU-s (1.5 GPU-min) by end of M2, measured per job as a metric; hard alert at 120 GPU-s (spec §8 budget is 1–2 GPU-min) |
| NFR-COST-02 | Per-stage GPU-seconds recorded in `StageRun.gpu_seconds` and as an OTel metric | every job [AQS/OPS-07], [EP/ENG-20] |
| NFR-COST-03 | LLM tokens per training plan | ≤ 30k input + 4k output tokens (judgment); input is aggregated stats only, never video or raw events |
| NFR-COST-04 | Provider guardrails | Spending limits or billing alerts on GPU provider, LLM provider and object storage [AQS/SEC-10] |
| NFR-COST-05 | Per-user quotas | Monthly analysed match-minutes per plan tier (number set by PM), job-creation rate limit 10/hour/user (judgment) [AQS/SEC-07 2.4.1], [AQS/SEC-02 5.2.4] |
| NFR-COST-06 | Fully loaded $ per analysed match-minute (GPU + storage + LLM + egress) reported on a dashboard per sprint from M2 | Target set by PM against pricing; no verified provider pricing in research (judgment) |

### 4.5 Security (target OWASP ASVS 5.0 Level 2 [AQS/SEC-01])

| ID | Requirement | Source |
|---|---|---|
| NFR-SEC-01 | Every endpoint taking a resource ID enforces ownership or explicit `ShareGrant` in a FastAPI dependency; parametrised BOLA matrix proves user B gets 404 on all of user A's resources (404 preferred over 403 to avoid existence disclosure, judgment) | [AQS/SEC-09], [AQS/SEC-03 8.2.2], [AQS/STACK-01] |
| NFR-SEC-02 | Field-level authorisation: response schemas are explicit allowlists (no ORM object dumps); write schemas reject unknown fields | [AQS/SEC-03 8.2.3], [AQS/SEC-08 API3] |
| NFR-SEC-03 | Deny by default; authorisation only server-side | [AQS/SEC-03 8.2.1, 8.3.1] |
| NFR-SEC-04 | Uploads: size cap 10 GB and duration cap 150 min (judgment numbers), container/codec allowlist (MP4/MOV, H.264/HEVC) checked by magic bytes + ffprobe, generated object keys, never executed, `Content-Disposition: attachment` and sanitised filename on download | [AQS/SEC-02 5.2.1, 5.2.2, 5.3.1, 5.3.2, 5.4.1–5.4.2] |
| NFR-SEC-05 | User filenames never reach FFmpeg or the filesystem; FFmpeg runs in a worker sandbox with no network except the storage endpoint and memory/CPU/time limits | [AQS implications], [AQS/SEC-10] limits; [AQS/SEC-06 13.2.4] outbound allowlist |
| NFR-SEC-06 | Per-user storage quota and anti-automation on job creation | [AQS/SEC-02 5.2.4 (L3)], [AQS/SEC-07 2.4.1] |
| NFR-SEC-07 | Media served only via signed URLs with TTL ≤ 15 min (judgment), no long-lived tokens in URLs | [AQS/SEC-05 14.2.1] |
| NFR-SEC-08 | Secrets only in env/vault; no defaults; separate least-privilege service accounts per process (api, worker-cpu, worker-gpu) | [AQS/SEC-06 13.2.1–13.2.3, 13.3.1–13.3.2], [AQS/OPS-01] |
| NFR-SEC-09 | Security logging: when/where/who/what in UTC; all authn attempts and authz failures; no credentials; log-injection-safe encoding; logs shipped off-host | [AQS/SEC-04 16.2.1, 16.2.2, 16.3.1–16.3.4, 16.2.5, 16.4.1–16.4.3] |
| NFR-SEC-10 | Generic error bodies, no stack traces; central + fallback exception handler; fail closed | [AQS/SEC-04 16.5.1], [AQS/SEC-12] |
| NFR-SEC-11 | LLM output validated: every drill ID exists in the pinned `library_version`, every cited metric exists for that player; otherwise plan rejected and not saved | [AQS/SEC-08 API10] |
| NFR-SEC-12 | Business flows in order: analysis cannot start before upload is complete and checksum-verified; corrections only on matches in `scored` state | [AQS/SEC-07 2.3.1]; tus checksum extension [AQS/STACK-06] |
| NFR-SEC-13 | Hardening: debug off in prod, no VCS metadata, no directory listing; PWA security headers (CSP, nosniff, frame DENY) | [AQS/SEC-06 13.4.1–13.4.3], [AQS/STACK-04] |
| NFR-SEC-14 | Supply chain: pinned lockfiles, SBOM per build, dependency + secret scans in CI, licence check of models/weights/datasets | [AQS/SEC-11 A03] (controls are judgment per AQS G2.14) |
| NFR-SEC-15 | Prompt-injection surface: user free text (goals, opponent notes) is passed to the LLM inside delimited data tags and never as instructions; LLM has no tools except read-only drill lookup | [AQS/SEC-08 API10]; tool minimalism [AQS/AI-02] (applying it here is judgment) |
| NFR-SEC-16 | Agent team sandboxed at filesystem and network boundaries; CI review action with minimal permissions and bot-loop protection | [DPA/AI-07], [DPA/AI-11], [DPA/AI-13] |

Note: ASVS chapter/requirement numbers were captured through a summarising fetch; spot-check them against the raw ASVS markdown before they go into acceptance criteria [AQS caveats].

### 4.6 Privacy

| ID | Requirement | Source |
|---|---|---|
| NFR-PRIV-01 | Data classification with per-class encryption, retention and access rules documented before beta: High = original/mezzanine/proxy video, clips, thumbnails, pose artefacts; Medium = player/opponent names, notes; Low = aggregated metrics | [AQS/SEC-05 14.1.1, 14.1.2] |
| NFR-PRIV-02 | Videos private by default; sharing only via explicit `ShareGrant`; opponent profiles never readable by other users | spec §8, [AQS/SEC-03] |
| NFR-PRIV-03 | **No face recognition and no biometric templates**: identity is per match and user-assigned; re-id uses only within-match appearance features (clothing colour, position, side), discarded with frame artefacts | spec §8; (judgment on feature scope) |
| NFR-PRIV-04 | Scheduled automatic deletion per retention class (defaults in §6.1); user-initiated match deletion removes all objects and rows within 7 days (judgment) and is verified by an integration test | [AQS/SEC-05 14.2.7] |
| NFR-PRIV-05 | `Cache-Control: no-store` on match, player and plan responses; no sensitive data in browser storage beyond the session token; clear on logout | [AQS/SEC-05 14.3.1–14.3.3] |
| NFR-PRIV-06 | Training use of user video only with separate opt-in `TrainingConsent`, revocable; revocation removes the match from future label sets (frozen historical gold sets: human decision needed) | (judgment); legal basis unverified [AQS G3.5] |
| NFR-PRIV-07 | Data minimisation to LLM: only pseudonymous participant labels and aggregated stats are sent; no names, opponent notes, video, or frames | (judgment) applying [AQS/SEC-05] classification |
| NFR-PRIV-08 | Logs carry pseudonymous `user_id`, never names, emails or media URLs with signatures | [AQS/SEC-04 16.2.5] |
| **Blocker** | Lawful basis, consent wording, filming third parties and minors, and any biometric classification of pose data need a verified privacy/legal pass before any real-user beta. Escalate to the human product owner. | [AQS G3.5, Gaps] |

### 4.7 Observability

- Traces + metrics via OpenTelemetry; W3C Trace Context + Baggage composite propagator; injected into job payloads and extracted in workers; malformed `traceparent` never throws [AQS/OPS-06], [AQS/OPS-07].
- Structured JSON logs to stdout, UTC, with `trace_id`, `request_id`, pseudonymous `user_id`, `match_id`, `job_id`, `stage`, `pipeline_version` [AQS/OPS-03], [AQS/SEC-04], [EP/ENG-20].
- Workers log model versions, weight hashes and thresholds at startup [EP/ENG-20].
- Required metrics (judgment list): `stage_duration_seconds{stage}`, `stage_gpu_seconds{stage}`, `gpu_seconds_per_match_minute`, `job_outcome_total{level}`, `queue_depth`, `queue_oldest_age_seconds`, `upload_bytes_total`, `upload_resume_total`, `upload_409_total`, `llm_tokens_total{direction}`, `plan_validation_rejects_total`, `corrections_per_game` (product-quality signal), `low_confidence_calls_ratio`.
- Alerts tied to SLO burn, not raw thresholds, plus cost alerts (NFR-COST-01/04) [AQS/REL-02].
- Model quality is observed in production via corrections: `corrections_per_game` by stage and `pipeline_version` is the online counterpart of the offline gold-set metrics (judgment).

### 4.8 Maintainability

- Code by bounded context / domain module [AQS/STACK-01]; Ruff lint + format [AQS/STACK-05]; type checking strict on `scoring`, `analytics`, `coaching` domain packages (judgment).
- Coverage floors (judgment): branch coverage ≥ 95% for the rules engine, ≥ 85% for domain modules, no floor for model code (covered by eval layer instead).
- PRs ~100 changed lines, refactors separate [EP/ENG-04], tests with logic [EP/ENG-04].
- Every artefact schema, `rules_version`, `pipeline_version`, `library_version`, `metric_def_version`, `prompt_version` is explicit and recorded on output rows, so any number on screen can be traced to code + model + config (judgment; supports spec §2 traceability).
- Dependency health: MMPose's last release is 2024-01-04 [DOM/CV-11]; run RTMPose via ONNX Runtime so runtime does not depend on the training stack [DOM G5 PO2].
- DORA four keys tracked per sprint [EP/ENG-21]; DORA 2024 links AI adoption to lower stability, so weight change-failure rate [EP/ENG-22].

---

## 5. CV pipeline feasibility and accuracy targets

### 5.1 Feasibility verdict per stage (judgment, grounded where cited)

| Stage | Feasibility | Evidence | Main risk |
|---|---|---|---|
| Court calibration | High | Homography 8 DoF from point correspondences [DOM/CV-12]; keypoint detectors in prior art [DOM/CV-19], [DOM/CV-15] | Multi-court venues, partial court in frame; camera bumped mid-match |
| Player detection/tracking | High for detection, Medium for identity | ByteTrack MOTA 80.3 / IDF1 77.3 / HOTA 63.1 on MOT17 [DOM/CV-04]; sports ID switches known hard [DOM/CV-09], [DOM/CV-15] | Doubles crossings (stacking, switches); players on adjacent courts |
| Pose | High | RTMPose-m 75.8 AP COCO, 90+ FPS CPU, 430+ FPS GTX 1660 Ti [DOM/CV-10] | Small players at far baseline at 1080p |
| Ball tracking | **Medium** | TrackNetV3 F1 98.56% on badminton [DOM/CV-01]; but domain gap to amateur phone pickleball, and the only pickleball repo publishes no metrics [DOM/CV-02, DOMAIN-10] | Fence/background clutter, far-court ball a few pixels, labelled data volume |
| Audio hit | Medium-High | Spectral-flux onsets [DOM/CV-14] | Adjacent-court pops, wind, music; no source on pop acoustics [DOM Gaps 8] |
| Bounce + landing position | Medium | Separate learned step [DOM/CV-19]; ground-plane mapping valid for bounces [DOM/CV-12] | Bounce frame often not visible from baseline view; occlusion by net/players |
| Rally segmentation | Medium-High | (judgment) dead-ball gaps + audio silence + player reset positions | Let serves, ball retrieval, practice hits between rallies |
| Shot classification (coarse) | Medium | (judgment) | Label noise; taxonomy definitions unverified [DOM G2] |
| Shot classification (erne, ATP, speed-up vs drive) | **Low for MVP** | (judgment) rare classes, few examples | Class imbalance |
| Rally winner / fault reason | **Low-Medium** | Spec §2: one camera cannot referee line calls | In/out near lines, NVZ foot faults |

### 5.2 Challenges to the spec

1. **60 fps everywhere is unaffordable.** Proposed frame-rate plan (judgment, verify in SPIKE-03): ball tracking at full 60 fps (needed for hit/bounce timing), player detection at 15 fps with tracker motion interpolation, pose only on ±5 frames around fused hit events (not every frame), court calibration on ~30 sampled frames. Reference points: ByteTrack 29.6 FPS on V100 including detection [DOM/CV-04]; TrackNetV3 25.11 FPS [DOM/CV-01] (hardware not recorded in our research). Batching, FP16 and TensorRT/ONNX export are expected to raise throughput substantially but **no verified number exists**; SPIKE-03 must measure.
2. **Height over net** removed (§0.5). Replace with "ball apex height class" only if a later 3D trajectory spike succeeds.
3. **TrackNet fine-tuning data:** spec says "label about 50 matches". Frame-level ball labels for 50 matches are ~10^6 frames; that is not labelable. Propose: ball labels on ~15,000–25,000 frames sampled across ≥ 20 venues/lighting/camera heights (comparable scale to the original TrackNet dataset of 19,835 frames [DOM/CV-02]), plus event-level tags (hits, bounces, rally boundaries, shot types, outcomes) for ~50 matches via the M0 tool (judgment).
4. **Doubles identity:** spec mitigation is "team side plus clothing colour". Add the hard constraint of exactly 2 tracks per side, plus one user confirmation tap per player at match start [DOM G4 P4]; SAM 2 promptable tracking is a candidate for the tap UX or auto-labelling (Apache-2.0/BSD-3) [DOM/CV-17].
5. **Tracker pinning:** if any Ultralytics component is adopted under a commercial licence, pin the tracker explicitly since the default is TrackTrack and can change [DOM/CV-06].
6. **Audio is a hint, not ground truth.** Multi-court venues will produce neighbouring pops (judgment). Fuse audio onset with visual trajectory inflection and player proximity; never create a hit from audio alone.
7. **Capture spec:** "elevated if possible" should become a measured quality-gate requirement (whole court including both NVZ lines and baselines visible; far baseline width ≥ 25% of frame width, judgment) with the capture guide in-app (spec §8).

### 5.3 Evaluation protocol

- Frozen, versioned gold sets per sprint; never edited to improve a score [testing-strategy §6], [EP/ENG-28].
- Splits by venue, not by clip, to avoid leakage (judgment); minimum 3 venues held out.
- Tracking metrics via TrackEval: HOTA, DetA, AssA, MOTA, IDF1 [DOM/CV-08]. SportsMOT for evaluation research only (CC BY-NC) [DOM/CV-09].
- Ball: visibility-aware accuracy/precision/recall/F1/FPS [DOM/CV-01]; positive if predicted centre within **10 px at 1920x1080** (judgment, documented threshold per DOM G8 E4).
- Every model PR reports before/after on the gold set; regression gate tolerances in an ADR (senior-ml-cv-engineer agent file).

### 5.4 Accuracy targets (initial, judgment, to be confirmed by spikes)

| ID | Metric (on frozen gold set) | M1/M2 entry target | MVP-release target |
|---|---|---|---|
| CV-T01 | Auto court calibration succeeds without manual fallback | ≥ 70% of videos | ≥ 85% |
| CV-T02 | Calibration reprojection error of known court line points | ≤ 15 cm RMS on court plane | ≤ 8 cm RMS |
| CV-T03 | Player tracking HOTA (4 on-court players, after side constraint) | ≥ 65 | ≥ 75 |
| CV-T04 | Identity errors needing user fix after confirmation tap | ≤ 2 per game | ≤ 0.5 per game |
| CV-T05 | Ball detection F1 (visible frames, 10 px) | ≥ 80% | ≥ 90% |
| CV-T06 | Hit detection precision / recall (fused) | ≥ 85% / ≥ 85% | ≥ 93% / ≥ 93% |
| CV-T07 | Hit timing error | median ≤ 33 ms, p95 ≤ 100 ms | median ≤ 17 ms (1 frame @60 fps), p95 ≤ 50 ms |
| CV-T08 | Bounce detection recall; landing position error | ≥ 70%; p80 ≤ 60 cm | ≥ 85%; p80 ≤ 30 cm |
| CV-T09 | Rally segmentation F1 (rally matched if start and end within ±1.0 s, no merge/split) | ≥ 90% (spec M2) | ≥ 95% |
| CV-T10 | Shot classification macro-F1, coarse classes (serve, return, drive, drop, dink, lob, volley) | ≥ 0.70 | ≥ 0.80 |
| CV-T11 | Rally outcome (winner side) accuracy, auto | ≥ 85% | ≥ 93%, with low-confidence rallies routed to one-tap confirmation |
| CV-T12 | Pipeline throughput | ≤ 2.0 GPU-min per match-minute | ≤ 1.5 GPU-min per match-minute |

**Re-definition of spec M3 "≤1 correction per game".** A side-out doubles game plausibly has ~25–40 rallies (judgment; domain coach to confirm). One correction per game then requires ~96–97% accuracy on every score-affecting field. Proposal: split the metric into (a) **corrections per game** (user changes an auto value) ≤ 2.0 at MVP and ≤ 1.0 at a later milestone, and (b) **confirmations per game** (one tap on a flagged low-confidence rally) ≤ 5, with calibrated confidence so ≥ 95% of unflagged rallies are correct. This matches the human-in-the-loop posture (spec §2) and HAX-style confidence display [DPA/DESIGN-11].

### 5.5 Shot taxonomy

Hierarchical (judgment): coarse classes for MVP (serve, return, third-shot, drive, drop, dink, lob, volley), fine classes later (speed-up, reset, erne, ATP, hybrid third shot [DOM G2 C2]). Definitions owned by the domain coach and unverified [DOM G2]; classifier labels must not ship before definitions are verified.

---

## 6. Functional requirements from engineering (for the BA)

- **ENG-FR-01** Resumable upload per tus 1.0.0 incl. HEAD offset discovery, PATCH from offset, 409 on mismatch, checksum and expiration extensions; abandoned uploads expire after 24 h (judgment) [AQS/STACK-06].
- **ENG-FR-02** Upload quality gate with explicit result and reason codes shown to the user; failed gate offers manual-tagging path (judgment; spec §8).
- **ENG-FR-03** Court calibration: auto, then user confirms/edits 4 corners; reprojection error shown as pass/fail (judgment) [DOM G6].
- **ENG-FR-04** Identity confirmation: user taps each player once and assigns a participant slot; no face recognition (spec §8).
- **ENG-FR-05** Manual tagging (M0): rally start/end, server, winner side, ending type, optional shots; produces a score sheet through the same rules engine as auto analysis (spec M0).
- **ENG-FR-06** Rules engine: pure, versioned, side-out and rally scoring, singles and doubles; table-driven + property-based tests tagged `@needs-verification` until rule numbers are recorded [DOM G1], [testing-strategy §3].
- **ENG-FR-07** Corrections: any rally/shot field correctable; correction replays score and recomputes metrics atomically; audit trail; corrections survive re-processing (ddd-guidelines §4.8).
- **ENG-FR-08** Re-processing: user or operator can re-run a match on a new `pipeline_version`; prior results retained until the new run succeeds (judgment).
- **ENG-FR-09** Every automatic value displays a confidence; values below a per-field threshold are flagged for review (spec §2) [DPA/DESIGN-11].
- **ENG-FR-10** Analytics with sample size and `low_sample` flag (spec §5); metric definitions versioned.
- **ENG-FR-11** Coaching workflow: rules rank weaknesses by points lost per match -> LLM selects from tool-returned library entries -> validator -> save; no autonomous agent [AQS/AI-01], [DOM/CV-20].
- **ENG-FR-12** Clip links: every insight references `(match_id, t_start_ms, t_end_ms)`; clips are generated lazily from the proxy and served by signed URL (spec §6, NFR-SEC-07).
- **ENG-FR-13** Account and match deletion (NFR-PRIV-04); data export of the user's own match records as JSON/CSV (judgment).
- **ENG-FR-14** Analysis-ready notification (web push via VAPID per [AQS/STACK-04]; applying it is judgment) and email fallback.

### 6.1 Retention defaults (judgment, for human approval)

| Class | Default retention |
|---|---|
| Original + mezzanine | 30 days after analysis completes (then deleted; proxy kept) |
| 720p review proxy, clips, thumbnails | while the match exists |
| Frame-level artefacts (ball track, boxes, pose) | 90 days, unless `TrainingConsent` |
| Abandoned uploads | 24 h |
| Match records, corrections, metrics, plans | until user deletes match/account |
| Logs | 30 days (security logs 90 days) |

---

## 7. Technical risks

| ID | Risk | Likelihood / impact (judgment) | Mitigation |
|---|---|---|---|
| RISK-01 | AGPL contamination via Ultralytics/BoxMOT | High / High | MIT/Apache stack by default; ADR before any AGPL dependency [DOM/CV-05, CV-07] |
| RISK-02 | GPU cost over 2 GPU-min per match-minute | High / High | SPIKE-03; frame-rate plan §5.2; cost alerts [AQS/SEC-10] |
| RISK-03 | Ball tracking domain gap (amateur phone, fences, far court) | High / High | Labelled pickleball frames, venue-split eval; degrade to `score_only` |
| RISK-04 | Auto rally outcome accuracy too low for auto-scoring | High / Medium | Confirmation UX (§5.4); manual path always available |
| RISK-05 | Pickleball rules unverified -> wrong score sheets | Medium / High | Block rules-engine "Ready" on rule numbers [DOM G1] |
| RISK-06 | Privacy/legal basis for third parties and minors unverified | Medium / High | Block real-user beta on verified legal pass [AQS G3.5] |
| RISK-07 | Doubles identity swaps | High / Medium | Side constraint + tap confirmation [DOM G4 P4] |
| RISK-08 | Malicious media exploiting FFmpeg/decoders | Low / High | Sandboxed workers, no network, resource limits, type allowlist [AQS/SEC-02, SEC-10] |
| RISK-09 | Serverless GPU cold starts / preemption inflating latency and cost | Medium / Medium | Idempotent chunked stages, requeue [AQS/OPS-02]; SPIKE-04 |
| RISK-10 | MMPose unmaintained | Medium / Low | ONNX export, pin versions [DOM/CV-11] |
| RISK-11 | Labelling throughput too slow for gold sets | Medium / High | Labelling tool in M0; SAM 2-assisted labelling candidate [DOM/CV-17] |
| RISK-12 | LLM recommends nonexistent drills or leaks PII | Medium / Medium | Validator + eval set (20–50 cases) [AQS/SEC-08], [AQS/AI-03]; NFR-PRIV-07 |
| RISK-13 | Upload size/time on phones (7–9 GB per hour) causing abandonment | High / Medium | Resumable upload; recommend Wi-Fi; SPIKE-06 on on-device trimming of dead time (judgment) |
| RISK-14 | Phone VFR video breaks audio/video sync | Medium / Medium | CFR normalisation stage; sync test fixture |

## 8. Spikes (time-boxed, each ends in an ADR with data)

| ID | Question | Timebox (judgment) | Exit criteria |
|---|---|---|---|
| SPIKE-01 | Licence posture: MIT/Apache-only stack vs Ultralytics Enterprise | 2 days | ADR with licence table for every model, weight and dataset [DOM/CV-04..17] |
| SPIKE-02 | Ball tracking baseline: TrackNetV3 zero-shot and after fine-tune on ~3,000 labelled pickleball frames from ≥ 5 venues | 1 sprint | F1 at 10 px per venue; if fine-tuned F1 < 70%, escalate scope (degrade to score-only for MVP) |
| SPIKE-03 | Throughput and GPU-seconds per match-minute per stage at the §5.2 frame-rate plan, with batching and ONNX/TensorRT, on 2 candidate GPU types | 1 week | Measured GPU-s/match-min ≤ 120 or a costed alternative; numbers recorded in `docs/evals/` |
| SPIKE-04 | Serverless GPU provider behaviour: cold start, preemption, max concurrency, egress cost | 3 days | p95 cold start, job retry behaviour, $ per GPU-hour quoted from the provider; human approves spend |
| SPIKE-05 | Audio hit detection on real pickleball recordings incl. multi-court venues | 3 days | Precision/recall of audio-only vs fused hits; tuned `delta`, `wait` [DOM/CV-14]; documents pop frequency band (fills DOM Gap 8) |
| SPIKE-06 | Upload UX on phone browsers: tus client, background tab behaviour, 8 GB file | 3 days | Completion rate across iOS Safari / Android Chrome; decision on native app need (spec §3 defers Expo) |
| SPIKE-07 | Auto court calibration on varied amateur footage | 1 week | CV-T01/T02 measured on ≥ 30 videos |
| SPIKE-08 | Rally outcome inference: can winner side be inferred from last bounce + player reaction with calibrated confidence? | 1 sprint | Reliability diagram; share of rallies auto-accepted at ≥ 95% precision |
| SPIKE-09 | Postgres queue vs Redis-backed queue under worst-case fan-out (chunks x stages) | 2 days | Throughput and lock contention numbers; ADR |

## 9. Proposed MVP engineering slice and sequencing (judgment)

1. **Sprint 1–2 (M0):** skeleton (Compose parity, CI gates, OTel, BOLA suite scaffold), tus upload + quality probe, data model, manual tagging, rules engine (behind `@needs-verification`), score sheet, basic analytics with sample sizes. SPIKE-01, SPIKE-04, SPIKE-06 in parallel.
2. **Sprint 3:** coaching workflow on manually tagged matches (general plan only) with validator and 20-case eval; drill library seed (domain-coach-verified drills only). This **completes the first milestone end to end without CV** (spec M0 rationale).
3. **Sprint 4–6:** calibration + player tracking + identity (M1), ball + audio + events + rally segmentation (M2), each gated on gold-set targets in §5.4; SPIKE-02/03/05/07 inform these.
4. **Sprint 7+:** shot classification (coarse), auto-scoring with confirmation UX (M3), clip linking (M4).

Opponent scouting (M6) and live mode (M7) are not in the MVP.

## 10. Open questions for the human product owner

1. Approve an MIT/Apache-only CV stack, or budget for an Ultralytics Enterprise licence?
2. GPU and storage spend ceiling per month for beta (needed to set NFR-COST-05 quotas)?
3. Retention defaults in §6.1, especially deleting originals after 30 days?
4. Who obtains the 2026 USAP rulebook and a verified privacy/legal review (GDPR, minors, third parties) before beta, given both were egress-blocked?
5. Accept the re-defined M3 metric (corrections ≤ 2/game + confirmations ≤ 5/game) instead of "≤1 correction per game"?
6. May user videos be used for model training with an opt-in consent, and what happens to frozen gold sets on revocation?
7. Drop "height over the net" from v1?
8. Target regions/jurisdictions for beta (drives data residency and legal review)?
