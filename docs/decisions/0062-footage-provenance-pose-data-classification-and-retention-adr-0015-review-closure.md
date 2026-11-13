# 0062. Footage provenance (rights basis, permitted uses, fail closed), pose-data classification and retention, licence rows per artefact; ADR 0015 review closure

- **Status:** Accepted (principal-engineer; tier 0 review per ADR 0056, reviewer security-privacy-engineer on the PE-6b PR). The legal adequacy of every consent and licence reading here is **not** decided: it is P16 (NFR-070, US + AU). This ADR fixes the engineering rules the Sprint 6 gates (ST-175a, ST-175b) and spike plans (ST-176b) build on.
- **Date:** 2026-11-13
- **Deciders:** principal-engineer (R/A)
- **Consulted:** security-privacy-engineer (required reviewer: classification, consent, ADR 0015 closure), senior-ml-cv-engineer (licence rows, SPIKE-07), senior-backend-engineer (ST-175a placement), sre-devops-engineer (ST-175b manifest gate), pickleball-domain-coach (pro-match footage use for the reference library)
- **Related:** ticket PE-6b, stories ST-175 (ST-175a, ST-175b) and ST-176 (ST-176b); FR-174.R1-R3, FR-009, FR-083, FR-151; NFR-062.1-.3, NFR-063 (NFR-063.4), NFR-065, NFR-066, NFR-070; OQ-06, P11, P16; ADR 0006 (retention windows), ADR 0014 (gates fail closed), ADR 0015 (CV licence posture; this ADR closes its pending reviews), ADR 0023 (OQ-06 interim rule), ADR 0042 (tombstones, objects before rows), ADR 0056 (tiered review), ADR 0058 (backup retention); `docs/security/data-classification.md`; `docs/architecture/context-map.md` R3, R7, R9, R10; `docs/sprints/sprint-06.md` §3.2 PE-6b

## Context and problem statement

The PO instruction of 2026-11-12 adds two new kinds of footage: video of the player's **training sessions** and video of **pro matches** ("analyse the videos from training, pro matches", `docs/requirements/po-input-2026-10-05.md`, addendum "Video analysis (PO 2026-11-12)"). The brief binds three footage rules: pro-match video only where we hold the rights, no scraping of broadcast or YouTube content, training video only with the players' consent. Pose or body tracking is personal data.

Today nothing enforces any of that. A media asset reaches the job runtime (`racket.analysis_jobs`, context map R7) without any statement of who owns it or what it may be used for; the only consent field in the code base is the per-clip `consent_record` of the dataset manifest (`backend/src/racket/dataset/manifest.py`, FR-151). NFR-063 names "pose/frame artefacts" as High, but no store, prefix or retention rule exists for them. ADR 0015 asked for a weights manifest and a follow-up decision on person-detector and pose weights before FR-083 is Ready, and its principal-engineer and security-privacy-engineer reviews have been pending since 2026-10-03.

This ADR answers four questions: (1) what a footage provenance record holds and where it lives; (2) when a job may use footage, and what fails closed; (3) how pose and keypoint artefacts are classified, kept and deleted; (4) what licence row every code, weights and dataset artefact carries. It also closes the ADR 0015 reviews.

**Word clash, fixed here.** "Training" means two things in Sprint 6. In this ADR and in the code: a **practice session** is the footage kind (the player's training session on court); **`training`** is the permitted use "train or fine-tune a model on it" (ADR 0015 rule 2, FR-009). A practice-session video may be permitted for `analysis` and not for `training`.

## Decision drivers

- FR-174.R1-R3: no record whose permitted uses include the job's use → no job and nothing decoded; consent for every filmed person; revocation reaches the reference set and derived measures within the ADR 0006 window.
- Fail closed on missing or unknown data, as every gate in this repo does (ADR 0014) [AQS/SEC-12].
- NFR-063: data classes documented with encryption, retention and access rules before beta; pose/frame artefacts are High [AQS/SEC-05].
- NFR-066: deletion within ≤ 1 min hidden, ≤ 7 days purged, scheduled retention 100 % on time [AQS/SEC-05].
- NFR-065: no face recognition, no biometric templates, re-identification within one match only.
- NFR-062: no AGPL or non-commercial component, weights or dataset in the shipped graph without an ADR [AQS/SEC-11]; ADR 0015 tiers U, E, A.
- R1 behaviour must not change for players who upload their own match: the R1 gates are met and live (judgment).
- Keep it simple: one record shape, one gate at one place, no new bounded context [AQS/ENG-04] (judgment that this is enough).

## Considered options

### Q1. Where the provenance record lives

1. **Do nothing:** keep consent only in the dataset manifest (`consent_record` per clip) and trust callers.
2. **In Dataset & Labelling** (`racket.dataset`), extending `manifest.py`.
3. **In Capture & Media** (`racket.video_ingest`), as part of the `MediaAsset` it describes, read by the job runtime through a query port; Dataset manifests carry the same record shape for files that never become a `MediaAsset` (chosen).
4. **A new "Footage Rights" bounded context.**

### Q2. Which assets the gate covers

1. **Every asset, every use, consent reference per filmed person** (the strict reading).
2. **Only the two new footage kinds** (practice session, pro match); player uploads stay outside the gate.
3. **Every asset has a record; the record's shape depends on its source; the per-person consent rule binds every use beyond the uploader's own analysis** (chosen).

### Q3. Pose and keypoint artefacts

1. **Do nothing** until a pose model ships.
2. **High class, derived-artefact retention (never longer than the source), deleted in the source's cascade; spike artefacts in an eval workspace with a hard expiry** (chosen).
3. **Do not store pose at all; compute it in memory per job.**

### Q4. Licence rows

1. **SBOM gate only** (ADR 0014, `scripts/ci/check_licences.py`).
2. **SBOM gate plus one manifest row per weights and dataset artefact, with the ADR 0015 tier, checked in CI** (chosen).

## Decision outcome

Chosen: **Q1 option 3, Q2 option 3, Q3 option 2, Q4 option 2.** Reasons per rule below; pros and cons in the next section.

### Rule 1. The provenance record (value object `FootageProvenance`, owned by Capture & Media)

Every media asset that any job may read has exactly one current provenance record. Fields:

| Field | Values | Notes |
|---|---|---|
| `source` | `player-upload`, `practice-session`, `pro-match`, `team-recorded` | `team-recorded` = gold and fixture footage under ADR 0023 (OQ-06) |
| `rights_holder` | text (Medium) | who owns the copyright in the recording |
| `rights_basis` | `owned`, `licensed`, `consented` | nothing else parses; an unknown value fails closed |
| `permitted_uses` | non-empty set of `analysis`, `reference-library`, `training` | an unknown value fails closed; empty fails closed |
| `expires_at` | timestamp; required on every record except `player-upload`, where it must be null | no "never" for licensed or consented footage: such a record without an expiry is refused (judgment: forces a review date on every licence and consent). A `player-upload` record has no stored expiry: its lifetime is derived from the asset's retention when the check runs (P4) |
| `licence_ref` | text; required when `rights_basis = licensed` | the licence or contract id and the clause that grants each permitted use |
| `filmed_person_count` | integer, required, 1-4 | how many people are in frame, declared by whoever registers the asset (for `player-upload`: 2 for a singles match, 4 for doubles, from the match format, `matches.public.owned_format`); a missing, zero or out-of-range value fails closed |
| `filmed_persons` | list of `{slot, consent_ref}` | `slot` is a court letter (`A1 A2 B1 B2`, gold-capture-protocol §2 step 7), never a name; at most `filmed_person_count` entries, slots unique |
| `revoked_at` | timestamp or null | set by revocation of any consent or the licence |

Shape rules (a record that breaks any of them is refused when written, error `provenance_invalid` with the rule id):

- **P1** A record lists a `consent_ref` for **every** filmed person, `len(filmed_persons) == filmed_person_count` and no `consent_ref` blank (FR-174.R2; error `consent_incomplete`), when **either** its `permitted_uses` include `reference-library` or `training`, **or** its `source` is `practice-session`, `pro-match` or `team-recorded`, whatever its `rights_basis`. The only records outside P1 are P4 records (`player-upload` with `permitted_uses = {analysis}`), the explicit exception below.
- **P2** `licensed` records carry a `licence_ref`; each filmed person's `consent_ref` names the licence clause that covers that person's image for each permitted use, or the record is refused (judgment: a broadcast licence for the picture is not consent to pose-track the people in it; P16 confirms).
- **P3** `pro-match` is only `licensed` or `owned`. There is no `pro-match` record from a scrape: the registration path takes an uploaded file plus the licence, never a URL to fetch (brief: no scraping of broadcast or YouTube content without a licence).
- **P4 (exception to P1)** `player-upload` records are created by the existing upload flow (no new user step): `rights_basis = owned`, `permitted_uses = {analysis}`, `filmed_person_count` = 2 or 4 from the match format (truthful: a doubles match has 4 people in frame), `filmed_persons` = one entry for the uploader with `consent_ref = upload-terms:<version>`, `expires_at` = null. P1 does not apply to this shape, so a doubles upload with one consent reference is valid for `analysis`. This is the R1 status quo written down, not a new consent: the uploader's analysis of their own match. Such a record can **never** gain `reference-library` or `training`: the moment its uses include either, P1 applies and the record needs a `consent_ref` for all `filmed_person_count` people; FR-009 training consent alone does not lift it for the other people in frame. Whether an uploader's attestation covers other filmed people even for `analysis` is a P16 question (open item OI-1).
  - **Lifetime (derived, not stored).** A P4 record lives exactly as long as its asset may be read: `footage_permit` computes the end at check time from the asset's current retention (ADR 0006: `R-ORIGINAL` from the player's ST-069 setting via `ReviewVideoSchedule.delete_at`, else `R-MATCH`). With `FEATURE_RETENTION_SETTING` off (the default, `backend/src/racket/platform/settings.py:284`) or the setting "until deleted", there is no date and the record lives while the asset exists; when the player changes the setting the next check sees the new end, so no stored copy goes stale. A derived end at or before `at` is `provenance_expired`. A `player-upload` record with a non-null `expires_at` is `provenance_invalid` (P4).
- **Examples** (each an ST-175a unit test; ✗ = refused, ✓ = accepted):
  - ✗ `practice-session`, `consented`, `filmed_person_count = 4`, 3 `consent_ref` → `consent_incomplete` (the FR-174 Gherkin row "4 players with 3 consent references").
  - ✗ `player-upload`, `permitted_uses = {analysis, reference-library}`, count 4, 1 `consent_ref` → `consent_incomplete` (P1 applies once the uses go beyond `analysis`).
  - ✗ `team-recorded`, `owned`, count 2, 1 `consent_ref` → `consent_incomplete` (P1 binds non-upload sources whatever the basis).
  - ✗ `player-upload` with `expires_at` set → `provenance_invalid` (P4); ✗ `practice-session` with `expires_at` null → `provenance_invalid`; ✗ `filmed_person_count` missing or 0 → `provenance_invalid`.
  - ✓ `player-upload` P4 record of a doubles match: count 4, 1 `consent_ref`, `expires_at` null, `FEATURE_RETENTION_SETTING` off → `Permit` for `analysis`, and `use_not_permitted` for `reference-library`.
- **P5** `team-recorded` records mirror the dataset manifest clip (`consent_record`, `consent_jurisdiction`, FR-151): one `consent_ref` per filmed slot. A gold set built from a `MediaAsset` copies the record; a manifest clip that never becomes a `MediaAsset` carries the same fields and `racket-manifest-check` applies P1-P3 to it (ST-175a extends the check; the record shape is the published language of Capture & Media, context map R10 consumers conform to it).

**Placement.** Domain code in `backend/src/racket/video_ingest/domain/` (module `provenance`), persistence beside `media_assets`, and a published query `video_ingest.public.footage_permit(media_asset_id, use, at) → Permit | Refusal(reason)`. Capture & Media owns it because the record describes the asset and its rights, which is Capture & Media's model (context map C3: the probe stage that reads the bytes already belongs there) (judgment). Dataset & Labelling (`TrainingConsent`, R9) stays the owner of the account-level opt-in; it reads the record, never writes it.

### Rule 2. The gate (fail closed, before any byte is decoded)

- **G1** A job is enqueued only after `footage_permit(asset, use, now)` returns `Permit`. The use of a job is fixed by its stage family: every user-path stage and every spike run is `analysis`; building a reference-set version from footage is `reference-library`; any training or fine-tuning run is `training`. The check runs in the API process at job creation (`analysis_jobs`, before `JobQueue.enqueue`) and again in the worker at claim time, before the presigned GET is issued (R3); a claim-time refusal fails the job with the same reason and decodes nothing (FR-174.R1 "nothing is decoded").
- **G2** `Refusal` reasons, each its own test (ST-175a): `provenance_missing`, `provenance_invalid`, `use_not_permitted`, `consent_incomplete`, `provenance_expired` (`expires_at ≤ at`, or for a P4 record the derived lifetime end `≤ at`), `provenance_revoked`. The API answer is HTTP 422 with the reason as the error code (FR-174 Gherkin). No reason is ever silently mapped to `Permit`; an exception inside the check is a refusal (ADR 0014).
- **G3** The probe stage of a `player-upload` runs under its P4 record, which the upload flow writes in the same transaction that completes the upload (context map R2, ADR 0011), so R1 upload behaviour is unchanged. Assets uploaded before ST-175a merges get their P4 record from the ST-175a migration (count from the match format, `expires_at` null, so every existing asset gets a valid record whatever its retention setting); the migration writes P4 records only for `player-upload` assets and leaves no other asset with a record (nothing else exists on main today: `grep -rn "pro-match\|practice-session" backend/src` → no match at origin/main 842b33b6).
- **G4** Revocation (FR-174.R3): setting `revoked_at` (a consent withdrawn, a licence ended, or `expires_at` passed, found by the daily retention job; a P4 record has no `expires_at`, and its asset's retention end already runs the C4 cascade as asset retention end) is a domain event `FootageRevoked(media_asset_id, at)`. It (a) refuses new jobs at once; (b) marks the asset excluded from the **next** reference-set version, so `racket-reference-lint` fails while a measured entry still names it (ST-170a); (c) starts the deletion cascade of Rule 3 for every derived artefact. Already published reference-set versions are not rewritten in place (gold sets and reference sets are frozen [EP/ENG-28]); the next version drops the asset and the old version is withdrawn from serving by the content status ladder (ADR 0044) (judgment).

### Rule 3. Pose and keypoint artefacts: classification, retention, deletion

- **C1 Class High** (NFR-063, `docs/security/data-classification.md` §1 already lists "pose and frame artefacts" under High). This covers keypoint arrays, skeleton tracks, per-frame person boxes with a track id, pose-derived features stored per person (joint angles, stance width per frame) and any frame crop. Aggregates that no longer describe one person per frame (for example "median kitchen arrival time over 40 rallies") are the class of the pattern measure they feed (ST-171e, NFR-063.3; Low today), decided per column by the security-privacy-engineer on that ticket.
- **C2 Store and prefix.** Object store, media bucket, key prefix `derived/pose/<media_asset_id>/<pipeline_version>/` (planned, first written by a later ticket; Sprint 6 writes none outside the eval workspace). Encryption `E-HIGH`/`E-S3`; access `A-HIGH`, and the worker role writes, the owner never receives raw keypoints through the API in Sprint 6 (judgment: no feature needs them). ST-175a adds the classification rows for every new column and prefix so IT-05-05 stays green (NFR-063.4: 0 unclassified columns or prefixes; pose rows High).
- **C3 Retention `R-POSE`** (new rule code, added to `data-classification.md` §2 by ST-175a): a pose artefact lives no longer than (a) its source asset's retention (`R-ORIGINAL`, ADR 0006), (b) its provenance record (`expires_at`, or the derived P4 lifetime; `revoked_at`) and (c) 30 days after the job that wrote it, whichever ends first (judgment: no Sprint 6 feature re-reads pose after the measures are written; the 30-day cap is reviewed when one does). Backups follow `R-BACKUP` (≤ 5 days, ADR 0058).
- **C4 Deletion cascade** (NFR-066): match delete, account delete, asset retention end, provenance revoked or expired each delete, in this order, objects before rows (ADR 0042): pose objects under `derived/pose/<asset>/`, other derived frame artefacts, then derived pattern-measure rows that name the asset (NFR-066.10, ST-171e), then the asset. Targets are the NFR-066 ones: hidden ≤ 1 min, purged ≤ 7 days, retention jobs 100 % daily. The integration test for each trigger asserts storage and DB empty (NFR-066 test level I).
- **C5 No identity.** Pose is never used to recognise a person across videos, never stored as a template, and track ids are scoped to one asset (NFR-065). A pose model whose output includes a face embedding or a ReID feature is not adopted (ADR 0015 C22, W9).
- **C6 Spikes** (SPIKE-07, ST-176b): pose runs only on `team-recorded` footage with P1 consent for every filmed slot and `permitted_uses ⊇ {analysis}`, CPU-only, inside a git-ignored eval workspace (gold-capture-protocol §2 step 6 rule: footage with people is never in git); outputs expire with the spike report or 30 days, whichever is first, and the report keeps only aggregate metrics (judgment). Until P11 supplies such footage, the spike plan runs on synthetic or empty-court clips only, and its pose rows say "not met: waiting on P11".

### Rule 4. Licence rows per code, weights and dataset artefact (NFR-062)

- **L1** Every artefact a shipped image or a job loads has one row in `models/manifest.json` (planned, created empty by ST-175b) with: `id`, `kind` (`code`, `weights`, `dataset`), `source` (repo or publisher, no fetched URL needed at runtime), `licence` (SPDX id, or `none`), `sha256` (weights and dataset files), `training_datasets` (weights only: list of dataset row ids), `tier` (ADR 0015: `U`, `E`, `A`), `decided_by` (ADR number). Python packages stay on the SBOM gate (`scripts/ci/check_licences.py`, ADR 0014); the manifest covers what the SBOM cannot see.
- **L2** CI fails (NFR-062.2): a row without `licence` or (for weights and dataset) without `sha256`; a weights row whose `tier` is better than the worst tier of its `training_datasets` (ADR 0015 rule 2: a model trained from an E checkpoint or E data is E); a `tier` `E` or `A` row referenced from a shipped path (worker image, `workers/src/`); a file under the model registry with no row. Unknown values fail.
- **L3** No runtime model download (NFR-062.3): weights are baked into the image or mounted read-only from a manifest-listed, hash-checked file; the worker test runs with the network denied (ST-175b).
- **L4** Footage is not a dataset row: footage rights live in Rule 1 records. A dataset built from footage (a gold set, a label set) has a dataset row whose licence is `proprietary-consented` and whose `decided_by` is this ADR, and its manifest's clips carry Rule 1 records (P5).
- **L5 Sprint 6 rows** (from ADR 0015's table, hashes re-checked below; nothing is shipped in Sprint 6, so every row is either `U` for the eval harness or `E` for eval-only):

| Artefact | kind | licence | tier | Sprint 6 use |
|---|---|---|---|---|
| ONNX Runtime (C17) | code | MIT | U | spike runtime |
| OpenCV (C13) | code | Apache-2.0 | U | calibration spike (homography) |
| MMPose / RTMPose code (C10) | code | Apache-2.0 | U | export to ONNX only; not in an image |
| RTMPose `aic-coco` / `body7` weights (W6, W7) | weights | Apache-2.0 code licence, training data includes AI Challenger | **E** | SPIKE-07 feasibility only, inside the eval workspace (C6); never in an image |
| RTMDet person detector `coco-obj365-person` (W5) | weights | COCO + Objects365 training data | **A** | SPIKE-07 may measure with it (ADR 0015 rule 4, "internal spikes may use W4/W5 to measure"); never shipped |
| TrackNetV3 checkpoints (W1) | weights | MIT (licensor grant) | U, provenance caveat | not used in Sprint 6 |
| Team-recorded gold footage (D10) | dataset | proprietary-consented | U once P1 consent exists | waiting on P11 |
| Licensed pro-match footage | dataset | per licence (P2) | U only for the uses its `licence_ref` grants | waiting on P11 |

- **L6** FR-083 (person detection and pose in the product) stays **not Ready**: ADR 0015 rule 4 asked for a follow-up ADR choosing (a) COCO-pretrained Apache weights on legal advice, (b) training on D10 plus permissive data, or (c) Ultralytics Enterprise. That choice needs SPIKE-07's measured accuracy and P16's legal reading, neither of which exists. This ADR does **not** make it; it fixes the eval-only boundary above and leaves the choice to a superseding ADR after SPIKE-07 (judgment: choosing now would be choosing on unmeasured accuracy, which NFR-006 and roadmap §7.1 forbid).

### Rule 5. ADR 0015 review closure

- **Principal-engineer review:** done on 2026-11-13 in this ticket. Method: re-ran ADR 0015's Method step 1 for eight LICENSE files and compared the sha256 with ADR 0015's Evidence table; re-tried the four non-GitHub pages. Findings:
  - **R1 (FYI)** all eight LICENSE hashes are unchanged (Evidence below); the U and A tiers based on them stand.
  - **R2 (blocking for FR-083, not for ADR 0015)** the "search, unverified" rows (COCO image terms, CrowdHuman, MOT17, AI Challenger, Ultralytics Enterprise) are still unverified: the four pages return HTTP `000` from this network on 2026-11-13. Owner: security-privacy-engineer, through P16. They stay "search, unverified"; no row is promoted.
  - **R3 (closed by this ADR)** ADR 0015's weights-manifest follow-up is Rule 4 (L1-L3), implemented by ST-175b.
  - **R4 (closed by this ADR, deferral recorded)** ADR 0015's "follow-up ADR on person detector and pose weights before FR-083 is Ready (Sprint 6)" is answered by L6: FR-083 is not Ready in Sprint 6, so the need-by moves with it; the choice is a superseding ADR after SPIKE-07 and P16.
  - **R5 (FYI)** the posture (MIT/Apache code, weights tiered by training data, no AGPL) is the right call and needs no change; no finding changes it, so no superseding ADR is required (ADR 0015 note of 2026-10-05).
- **Security-privacy-engineer review:** given as their review on the PE-6b pull request, which is the tier 0 reviewer slot for this ADR (ADR 0056). A dated note appended to ADR 0015 records both reviews and points here; the security-privacy-engineer's verdict, the head SHA it names and any finding are in that pull request's review, and any finding that changes a tier is a new ADR.

## Pros and cons of the options

### Q1 option 1: do nothing
- Good: no work.
- Bad: the PO's footage rules are unenforced; a pro-match file with no licence could be analysed (fails FR-174.R1). Rejected.

### Q1 option 2: Dataset & Labelling
- Good: the per-clip consent fields already live there (`manifest.py`).
- Bad: analysis of a player's own upload is not a dataset concern; context map C2 separates "training on a user's video" from "analysing that user's match". The job runtime would depend on Dataset for every job (judgment).

### Q1 option 3: Capture & Media, shared record shape (chosen)
- Good: the record sits with the asset it describes; one query at job creation and claim; R3 already makes Capture & Media the supplier to Vision.
- Good: Dataset keeps its manifest check and gains P1-P3 on the same shape, so gold sets and live assets cannot disagree.
- Bad: two code paths apply the same rules (asset record, manifest clip); mitigated by one shared pure function in `video_ingest/domain/` that the manifest check calls (judgment).

### Q1 option 4: new context
- Bad: a context with one value object and one query is speculative structure [AQS/ENG-04]. Rejected.

### Q2 option 1: strict, every asset
- Good: simplest rule to state.
- Bad: every R1 upload has three other people in frame whose consent the product has never collected; strict reading blocks the live R1 flow, a PO-level product change, and the per-person consent wording is itself unreviewed (P16).

### Q2 option 2: new kinds only
- Good: no R1 change.
- Bad: "anything else fails closed" is broken: an asset without a record would still be analysed, and a player upload could reach `reference-library` or `training` with no gate.

### Q2 option 3: every asset has a record, shape by source (chosen)
- Good: no asset is outside the gate; R1 is unchanged (P4 writes the status quo down); the new uses can never be reached without per-person consent.
- Bad: P4's attestation is weaker than per-person consent for `analysis` of player uploads; recorded as OI-1 for P16 rather than hidden.

### Q3 option 1: do nothing
- Bad: SPIKE-07 would produce pose files with no class, no expiry and no deletion path. Rejected.

### Q3 option 2 (chosen)
- Good: fits the existing classes and rule codes; deletion reuses ADR 0042's order; spikes have a hard expiry.
- Bad: one more retention rule code (`R-POSE`) to test.

### Q3 option 3: never store pose
- Good: nothing to delete.
- Bad: every re-measure re-runs pose (GPU cost, ADR 0010 capacity), and eval reports cannot be reproduced from stored outputs (judgment). Kept as the fallback if P16 says pose storage is unacceptable.

### Q4 option 1: SBOM only
- Bad: ADR 0015 found the gap is in weights and training data, which an SBOM does not list. Rejected.

### Q4 option 2 (chosen)
- Good: closes ADR 0015's weights-manifest follow-up with a CI check; the training-data inheritance rule is mechanical.
- Bad: a manual row per artefact; acceptable at single-digit artefact counts (judgment).

## Consequences

- Good: ST-175a, ST-175b and ST-176b have a fixed contract; the PO's three footage rules are enforced at one gate; pose has a class, a retention rule and a deletion path before any pose file exists.
- Trade-offs accepted: P4 records for player uploads rest on the uploader's attestation (OI-1); the FR-083 weights choice waits for SPIKE-07 and P16.
- Follow-up work (no new tickets: each lands in a Sprint 6 ticket that already exists):
  - ST-175a: `FootageProvenance` (with `filmed_person_count` and the Rule 1 examples as unit tests), `footage_permit` (with the derived P4 lifetime), gate at enqueue and claim, refusals G2, P4 migration, classification rows and `R-POSE` in `data-classification.md`, manifest check P1-P3 (P5).
  - ST-175b: `models/manifest.json` and the L2 lint, network-denied worker test (L3).
  - ST-176b: licence rows per artefact (L5) and the C6 spike rules in the SPIKE-07 plan.
  - CI-TIERS-06: `video_ingest/**/provenance*` and `**/pose*` are tier 2 (sprint-06 §3.2).
  - security-privacy-engineer: P16 question list (SEC-6) includes OI-1, OI-2 and R2.

## Open items

| Id | Item | Owner | Status |
|---|---|---|---|
| OI-1 | Does a player's upload attestation (P4) cover analysis of the other people in frame, in the US and AU? | security-privacy-engineer → P16 | Open; not a Sprint 6 blocker (R1 status quo) |
| OI-2 | Does a pro-match broadcast licence ever cover pose tracking of the players (P2)? Default: no, unless the licence says so | security-privacy-engineer → P16 | Open; no pro-match footage exists (P11) |
| OI-3 | Is the 30-day cap of `R-POSE` (C3) right once a feature re-reads pose? | principal-engineer | Review when such a feature is planned |

## Confirmation

- ST-175a: IT-06-08 red first (a job for an asset with no record is created today), unit test per G2 reason, IT-05-05 shows 0 unclassified columns or prefixes and pose rows High (NFR-063.4), a deletion IT per C4 trigger asserts storage and DB empty (NFR-066).
- ST-175b: `infra/tests/test_licence_gate.py` (planned) with a planted AGPL package, a weights row without licence and a weights row whose tier is better than its training data, each rc 1.
- ST-176b: the SPIKE-07 plan lists an L5 row for every artefact it loads and the C6 rules.
- Doc checks on this file: `python3 scripts/ci/check_docs.py --base origin/main --head HEAD` rc 0.

## Evidence

| Claim | Evidence | Type |
|---|---|---|
| No provenance or footage-use field in the code today, only `consent_record` per manifest clip | `grep -rn "provenance\|permitted_use\|rights_basis" backend/src` → no match at origin/main 842b33b6; `grep -n consent_record backend/src/racket/dataset/manifest.py` → the clip rule | test result, 2026-11-13 |
| Retention setting off by default; R-ORIGINAL has no date without it | `backend/src/racket/platform/settings.py:284` `feature_retention_setting=boolean("FEATURE_RETENTION_SETTING", default=False)`; `ReviewVideoSchedule.delete_at` returns `None` for "until deleted" (`backend/src/racket/video_ingest/domain/retention.py`); `data-classification.md` §2 `R-ORIGINAL` | repo, origin/main 842b33b6 |
| Match format gives the filmed-person count | `backend/src/racket/matches/public.py` `owned_format` → `singles`/`doubles` | repo, origin/main 842b33b6 |
| Pose/frame artefacts are High | `docs/security/data-classification.md` §1, class High row; NFR-063 | repo |
| ADR 0015 LICENSE hashes unchanged | `curl -sS https://raw.githubusercontent.com/<repo>/HEAD/LICENSE \| sha256sum` on 2026-11-13: TrackNetV3 `1eeb3168…0cd497`, ByteTrack `e9d83751…1696f9`, roboflow/trackers `c71d239d…0ab4`, mmpose `aa2c6f34…8909cb9`, ultralytics `0d96a4ff…abcb0`, boxmot `0d96a4ff…abcb0`, sam2 `c71d239d…0ab4`, onnxruntime `2f07c727…48922c`; every value equals ADR 0015's Evidence table; each fetch HTTP 200 | fetched 2026-11-13 |
| Non-GitHub licence pages still unreachable | `curl -sS -o /dev/null -w "%{http_code}"` → `000` for cocodataset.org, crowdhuman.org, motchallenge.net, ultralytics.com/license | test result, 2026-11-13 |
| Deletion order objects before rows | ADR 0042 | repo |
| Gold footage with people never in git; consent per clip and slot letters | `docs/data/gold-capture-protocol.md` §2 steps 6-7; `manifest.py` `people_in_git`, `consent_missing` | repo |
| A model trained from E data is E | ADR 0015 decision 2 | repo (judgment in ADR 0015) |
| P2, C3 30-day cap, Q1 placement, Q3 option 3 cost | (judgment) | judgment |
