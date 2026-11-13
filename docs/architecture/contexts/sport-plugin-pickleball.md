# Canvas: Sport Plug-in (pickleball)

- **Status:** Accepted (2026-10-03, principal-engineer)
- **Code module:** `racket.sports.pickleball` (`rules/`, `court_model/`, `metrics/`, `drills/` tags)
- **Building blocks:** `RulesEngine` (pure functions), `RulesConfig`, `CourtModel`, `ShotTaxonomy`, metric definitions; since Sprint 6 (ADR 0061) `PatternDefinition` (`patterns.json` (planned), versioned by definition version) and the reference sets (`content/references/pickleball/` (planned), with schema, loader, lint and lock in `racket.sports.references` (planned))

## Purpose
Everything specific to one sport, published as one versioned language that every other context consumes. A new sport is a new plug-in, not a change to the contexts (spec §3).

## Strategic classification
- **Domain:** Core, as a Published Language.
- **Business model role:** expansion to other racket sports.
- **Evolution:** custom-built. Its content is owned by the domain coach.

## Domain roles
Specification: the rules, geometry and taxonomy.

## Inbound communication
Domain coach: verified rule entries in `docs/domain/rules-verified.md` (rule, edition, number, wording); pattern definitions (pattern catalogue, COACH-6a) and reference entries with a source that resolves (`docs/domain/sources.md` (planned), COACH-6c). Measured entries need a footage provenance record that permits "reference-library" (Capture & Media, ADR 0062 (planned)); until then the lint refuses them (ADR 0061 Rule 1).

## Outbound communication
Published Language (R5) to Match & Scoring, Vision Analysis, Analytics and Coaching, versioned by `rules_version`. Pattern definitions go to Analytics (to measure) and Coaching (to judge); reference sets go to Coaching through its ACL (R13).

## Ubiquitous language
Reference pattern, definition version, `better_direction`, `interval_method`, min_n, reference set, reference entry, `source_type` (`measured`, `published`, `judgment`), provenance label, level band. Side-out, server number, rally scoring, NVZ/kitchen, two-bounce rule, fault, third-shot drop/drive, dink, drive, drop, lob, volley, speed-up, reset, erne, ATP, transition zone. **All needs-verification** (ddd-guidelines §6) [DOM G1].

## Business decisions
- Rule constants and court dimensions live only in `RulesConfig`/`CourtModel` (NFR-079).
- Nothing is marked verified without a rule number [DOM G1].
- A stub second sport proves extensibility (NFR-082, R2).
- A published reference-set version is immutable; a change is a new version with a new lock hash (FR-170.R2). Every entry carries its source and provenance label; nothing reads "pro" unless its source is pro footage or a pro statistic (FR-170.R5; ADR 0061).

## Assumptions
USAP rulebook edition 2026 (`USAP-2026`). Unverified until OQ-01 supplies the PDFs.

## Verification metrics
Unit tests per rule; mutation score of 85% or more (NFR-072); stub-sport contract test (NFR-082).

## Open questions
OQ-01 (rulebook PDFs); rally-scoring provisional rule (DOM G1 R3).
