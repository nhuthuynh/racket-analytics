# Canvas: Capture & Media

- **Status:** Accepted (2026-10-03, principal-engineer)
- **Code module:** `racket.video_ingest`
- **Aggregates:** `UploadSession`, `MediaAsset` (with value object `MediaFacts`), `Clip` (R1 later)

## Purpose
Get a match video in safely and resumably, learn what the file is, and keep it private and only as long as allowed.

## Strategic classification
- **Domain:** Supporting. It is necessary, but tus and S3 are well understood.
- **Business model role:** reduces friction. A resumed upload is the first moment of value (NFR-042).
- **Evolution:** product. It follows the tus 1.0.0 protocol [AQS/STACK-06] and the in-app core of ADR 0011.

## Domain roles
Gateway (it guards the untrusted-file boundary) and execution (the probe stage).

## Inbound communication
| From | What | Kind |
|---|---|---|
| Player | `StartUpload(match_id, length)`, `SendChunk(offset, bytes)`, `HEAD` offset | commands / query (tus, API §6) |
| Job runtime (R7) | runs the `probe` stage registered by this context | OHS call |
| Retention scheduler (S1+) | `ExpireAbandonedUploads`, `PurgeOriginal` | commands |

## Outbound communication
| To | What | Kind |
|---|---|---|
| Match & Scoring | `MatchUploaded(match_id, media_asset_id)`; query `media_summary(match_id)` | C/S (R2) |
| Job runtime | `enqueue(JobKey(match_id, pipeline_version, "probe"))`, in the completion transaction | OHS (R7) |
| Vision Analysis | media facts and a presigned GET (≤ 15 min) | C/S (R3) |
| Object store (ext) | multipart upload, staging objects, presigned GET | infrastructure |

## Ubiquitous language
- **Upload session:** one resumable upload of one file for one match.
- **Offset:** bytes durably stored.
- **Upload length:** declared total size.
- **Chunk:** one PATCH body.
- **Media asset:** a stored video, plus what we know about it.
- **Media facts:** container, codec, fps, VFR, duration, resolution and audio.
- **Probe:** reading media facts with ffprobe.
- **Object key:** the server-generated storage name.
- **Original:** the uploaded file as received.
- **Abandoned upload:** an upload not completed within 24 h.

## Business decisions
- Object keys are generated (`originals/{uuid4 hex}`) and never derived from user input [AQS/SEC-02 5.3.2].
- A wrong offset gives 409, with the upload unchanged [AQS/STACK-06]. A PATCH is atomic (ADR 0011).
- Probing starts only after the final byte is stored (NFR-060) [AQS/SEC-07 2.3.1].
- User file names are never stored or passed to tools in Sprint 0 (NFR-054; data minimisation).
- In Sprint 1: validation by content (magic bytes via ffprobe), caps of 10 GB and 150 min (provisional), and the checksum and expiration extensions (FR-023, FR-024).

## Assumptions
- Phone uploads are MP4/MOV with H.264/HEVC (FR-023). The synthetic fixture is H.264 1080p60 (decision-log 2026-10-03).
- One upload per match in Sprint 0 (eventstorming H9).

## Verification metrics
- Upload completion SLO 99.0% (NFR-042).
- 0 keys derived from user input (scenario "Stored names never come from the user's file name").
- IT-00-06/07/08 green.
- 0 network destinations from the probe sandbox other than storage (and the queue DB; IT-00-10).

## Open questions
- Final caps (K12, R-05).
- Expiry window: ADR 0006 is Proposed (OQ-07).
- Mezzanine and 720p proxy formats (R2).
