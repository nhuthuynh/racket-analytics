# Canvas: Sport Plug-in (pickleball)

- **Status:** Accepted (2026-10-03, principal-engineer)
- **Code module:** `racket.sports.pickleball` (`rules/`, `court_model/`, `metrics/`, `drills/` tags)
- **Building blocks:** `RulesEngine` (pure functions), `RulesConfig`, `CourtModel`, `ShotTaxonomy`, metric definitions

## Purpose
Everything specific to one sport, published as one versioned language that every other context consumes. A new sport is a new plug-in, not a change to the contexts (spec §3).

## Strategic classification
- **Domain:** Core, as a Published Language.
- **Business model role:** expansion to other racket sports.
- **Evolution:** custom-built. Its content is owned by the domain coach.

## Domain roles
Specification: the rules, geometry and taxonomy.

## Inbound communication
Domain coach: verified rule entries in `docs/domain/rules-verified.md` (rule, edition, number, wording).

## Outbound communication
Published Language (R5) to Match & Scoring, Vision Analysis, Analytics and Coaching, versioned by `rules_version`.

## Ubiquitous language
Side-out, server number, rally scoring, NVZ/kitchen, two-bounce rule, fault, third-shot drop/drive, dink, drive, drop, lob, volley, speed-up, reset, erne, ATP, transition zone. **All needs-verification** (ddd-guidelines §6) [DOM G1].

## Business decisions
- Rule constants and court dimensions live only in `RulesConfig`/`CourtModel` (NFR-079).
- Nothing is marked verified without a rule number [DOM G1].
- A stub second sport proves extensibility (NFR-082, R2).

## Assumptions
USAP rulebook edition 2026 (`USAP-2026`). Unverified until OQ-01 supplies the PDFs.

## Verification metrics
Unit tests per rule; mutation score of 85% or more (NFR-072); stub-sport contract test (NFR-082).

## Open questions
OQ-01 (rulebook PDFs); rally-scoring provisional rule (DOM G1 R3).
