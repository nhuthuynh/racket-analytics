# Canvas: Analytics

- **Status:** Accepted (2026-10-03, principal-engineer). Hosts opponent scouting until M6 (C5).
- **Code module:** `racket.analytics`
- **Aggregates:** `MetricSnapshot` (read-model-like, recomputable)

## Purpose
Turn scored matches into metrics, patterns and trends per player and match, always with sample sizes. Rank weaknesses by rallies lost (ADR 0003).

## Strategic classification
- **Domain:** Core. Insight is the product.
- **Evolution:** custom-built.

## Domain roles
Analysis and read models.

## Inbound communication
`RallyScored`, `ScoreCorrected`, `ShotCorrected` and `MatchScored` from Match & Scoring (R6), consumed idempotently. Metric definitions from the Sport Plug-in (R5).

## Outbound communication
Metric snapshots, `WeaknessesRanked` and evidence links (rally IDs) to Coaching (R8). Dashboards to the Player.

## Ubiquitous language
Metric snapshot, sample size, low-sample metric (shown and flagged, never hidden), trend, rallies lost per game (split serve/receive), evidence link, scouting report (M6).

## Business decisions
- Weakness ranking uses rallies lost per game, split serve/receive, with points conceded shown separately (ADR 0003, Proposed). Attribution conservation is an invariant (FR-109).
- Low-sample rules and efficacy claims follow ADR 0005.
- Snapshots are recomputable and versioned by `metric_def_version` (NFR-075).

## Assumptions
Corrections are available before analytics are trusted (R1 flow).

## Verification metrics
FR-109 invariant property tests; coverage of 90% or more (NFR-071).

## Open questions
OQ-08 (rallies-lost unit confirmation by the PO); scouting context split at M6.
