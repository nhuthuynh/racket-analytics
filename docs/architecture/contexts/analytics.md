# Canvas: Analytics

- **Status:** Accepted (2026-10-03, principal-engineer). Hosts opponent scouting until M6 (C5).
- **Code module:** `racket.analytics`
- **Aggregates:** `MetricSnapshot` (read-model-like, recomputable); since Sprint 6 `PatternMeasure` snapshots in `racket.analytics.patterns` (planned) (ADR 0061). Design: [`../analytics-snapshots.md`](../analytics-snapshots.md) (Accepted for build 2026-10-07, review D3 open); HTTP: [`../api-sprint-03.md`](../api-sprint-03.md) §2-§3.

## Purpose
Turn scored matches into metrics, patterns and trends per player and match, always with sample sizes. Rank weaknesses by rallies lost (ADR 0003).

## Strategic classification
- **Domain:** Core. Insight is the product.
- **Evolution:** custom-built.

## Domain roles
Analysis and read models.

## Inbound communication
`RallyScored`, `ScoreCorrected`, `ShotCorrected` and `MatchScored` from Match & Scoring (R6), consumed idempotently. In R1 they arrive as one in-process event `ScoreSheetChanged(match_id, sheet_version)` after the scoring commit; the sheet is read through `racket.matches.public` (ADR 0040). Metric definitions and the low-sample thresholds from the Sport Plug-in's metric dictionary (R5; ADR 0041). Pattern definitions (data source, `interval_method`, min_n) from the Sport Plug-in (R5; ADR 0061); Full Tag labels for Full Tag patterns.

## Outbound communication
Metric snapshots, `WeaknessesRanked` and evidence links (rally IDs) to Coaching (R8). Pattern measures per (match, side) and the pooling function to Coaching (R8, ADR 0061); Analytics measures, Coaching judges. Dashboards to the Player.

## Ubiquitous language
Pattern measure (value, n, interval, `interval_method`, low_sample, rankable, unavailable reason), metric snapshot, sample size, low-sample metric (shown and flagged, never hidden), trend, rallies lost per game (split serve/receive), evidence link, scouting report (M6).

## Business decisions
- Weakness ranking uses rallies lost per game, split serve/receive, with points conceded shown separately (ADR 0003, Proposed). Attribution conservation is an invariant (FR-109).
- Low-sample rules and efficacy claims follow ADR 0005.
- Snapshots are recomputable and versioned by `metric_def_version` (NFR-075). Key (`match_id`, `metric_def_version`, `rules_version`); `sheet_version` guards the upsert, so a repeated or late event writes nothing (ADR 0040).
- The low-sample thresholds have one source, the metric dictionary (`min_sample` per entry, `low_sample.max_interval_width`); no environment setting (ADR 0041).
- A deleted match's snapshots are removed by the purge through `racket.analytics.public.purge_match` (ADR 0042).
- Pattern-measure snapshot key (`subject` = owner, match, side; pattern id; match version; `rules_version`; definition version), guarded like ADR 0040. A pattern whose data source the match lacks is unavailable with a reason, never zero (FR-171.R5). Interval maths stays in `racket.analytics.uncertainty` (ADR 0061 Rules 2-3). Measures are personal data (tier 2 for the snapshot code).

## Assumptions
Corrections are available before analytics are trusted (R1 flow).

## Verification metrics
FR-109 invariant property tests; coverage of 90% or more (NFR-071).

## Open questions
OQ-08 (rallies-lost unit confirmation by the PO); scouting context split at M6.
