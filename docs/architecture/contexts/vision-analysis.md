# Canvas: Vision Analysis

- **Status:** Accepted (2026-10-03, principal-engineer). Model choices wait for SPIKE-01 and OQ-12.
- **Code modules (C3):** `racket.analysis_jobs` (job runtime and job state machine; TDD), `racket.worker` (entry point and stage registry), and the vision stages under `workers/*` (eval-driven, R2).
- **Aggregates:** `Job` / `AnalysisJob` (keyed by `JobKey(match_id, pipeline_version, stage)`), `CourtCalibration`, `EventTrack`

## Purpose
Turn a match video into time-stamped, confidence-scored observations (court, players, ball, hits, bounces, rallies, shot types), and run every pipeline stage reliably.

## Strategic classification
- **Domain:** Core. Automatic observations from one phone camera are the differentiator.
- **Business model role:** the main cost driver (GPU minutes, spec §8; NFR on cost).
- **Evolution:** custom-built, with stages evaluated against gold sets.

## Domain roles
Analysis and execution engine. The job runtime is an Open Host Service to other contexts (R7).

## Inbound communication
| From | What | Kind |
|---|---|---|
| Capture & Media | media facts and a presigned GET | C/S (R3) |
| Any context | `enqueue(JobKey)`; stage registration | OHS (R7) |
| Player | `ConfirmCourtCalibration`, `ConfirmIdentity` (R2) | commands |
| Dataset & Labelling | frozen gold sets for evals | C/S (R10) |

## Outbound communication
| To | What | Kind |
|---|---|---|
| Match & Scoring | `EventTrack` artefacts and `AnalysisCompleted`, through the ACL in Match & Scoring | R4 |
| GPU provider (ext) | stage execution (R2) | infrastructure |

## Ubiquitous language
- **Job, job key, stage, attempt:** the unit of queued work, its identity, its step, and how many times it has run.
- **Claim:** a worker taking a job.
- **Requeue:** returning a job to the queue on SIGTERM, within 10 s.
- **Fail closed:** a failed stage leaves no partial writes.
- **Pipeline version:** the model and config set behind a result.
- **Court calibration:** the homography; valid only on the court plane [DOM/CV-12].
- **Visibility:** unknown, not guessed [DOM/CV-01].
- **Event:** a hit or bounce.
- **Confidence:** how sure an automatic call is.
- **Analysis level:** full, or explicitly degraded.

## Business decisions
- Jobs are idempotent and reentrant per key. A worker requeues on SIGTERM, and a failing stage rolls back and marks the job `failed` [AQS/OPS-02; AQS/SEC-12] (NFR-046, NFR-047).
- W3C trace context is injected on enqueue and extracted in the worker [AQS/OPS-06].
- No CV/ML work runs in the API process [AQS/STACK-01, AQS/STACK-02].
- No face recognition (NFR-065).
- AGPL and non-commercial components need an ADR (NFR-062) [DOM/CV-05, DOM/CV-07].

## Assumptions
- A Postgres `SKIP LOCKED` queue is adequate for the MVP (ADR 0008 B; SPIKE-09 measures it).
- 60 fps capture (spec §2).

## Verification metrics
- Worker-crash suite: requeue within 10 s and 0 duplicate rows (IT-00-04).
- Fail-closed suite (IT-00-05).
- Analysis success SLO 97% (NFR-043, R2).
- Accuracy targets per ADR 0004.

## Open questions
- Licence posture for detector, tracker and pose models (SPIKE-01, OQ-12).
- GPU provider and spend ceiling (OQ-13).
- Whether the job runtime moves to `platform/queue` (context map CM-1).
