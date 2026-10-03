# Canvas: Dataset & Labelling (new, C2)

- **Status:** Accepted (2026-10-03, principal-engineer)
- **Code module:** `racket.dataset` (exists: `manifest.py` with `ManifestCheck`, a filesystem adapter, and the `racket-manifest-check` CLI)
- **Aggregates:** `GoldSet` (frozen, versioned, manifest plus sha256), `LabelSet`, `TrainingConsent`

## Purpose
Build and protect the data that makes the vision pipeline better: frozen gold sets for evaluation, and labels from user corrections. Labels are collected **only** with explicit training consent.

## Strategic classification
- **Domain:** Supporting. It is essential to Core quality but is not user-facing.
- **Business model role:** the long-term moat (labelled data), and a compliance risk.
- **Evolution:** custom-built, small.

## Domain roles
Archive and gatekeeper: integrity of frozen sets, and the consent gate.

## Inbound communication
- Corrections from Match & Scoring and media references from Capture & Media, **consent-gated** (R9).
- `TrainingConsentGranted/Revoked` from Identity & Players.
- Fixture and gold files from QA/ML (FR-151).

## Outbound communication
Frozen `GoldSet` versions to Vision Analysis for evals (R10); the CI integrity check result.

## Ubiquitous language
- **Gold set:** frozen and versioned.
- **Fixture set:** synthetic, consent `synthetic`.
- **Manifest:** id, version, sha256 per file, licence, consent status.
- **Version bump.**
- **Label set.**
- **Training consent:** separate from analysis.
- **Split:** fixture, train, eval.

## Business decisions
- A file whose hash changes without a version bump fails CI. An unlisted file fails, and symlinks are refused (decision-log 2026-10-03, QA).
- Gold sets are never edited to raise a score [EP/ENG-27, EP/ENG-28] (NFR-078).
- No user footage enters a label set without `TrainingConsent` (NFR-070 gate). The legal basis is **unverified** [AQS G3.5] (OQ-05, OQ-06).

## Assumptions
Team-recorded footage needs consent from everyone filmed (OQ-06). The synthetic fixture needs none.

## Verification metrics
`racket-manifest-check` exits 0 on `main`; 0 gold-hash drifts (NFR-078).

## Open questions
Consent wording and withdrawal effects on trained models (PO and legal); retention of label sets (ADR 0006 follow-up).
