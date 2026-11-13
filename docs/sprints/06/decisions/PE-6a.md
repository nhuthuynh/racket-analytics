# PE-6a decisions

Per-ticket decision file (working-agreement §3). Ticket: PE-6a, "ADR 0061: reference patterns and player-vs-reference comparison" (`docs/sprints/sprint-06.md` §3.2, wave 1 gates; story-level gate for ST-170, ST-171, ST-172, ST-173). Owner: principal-engineer. Review tier 0 (ADR 0056): one fresh-context reviewer plus the automated doc checks. Atomic items: A1, A4 (`docs/sprints/06/requirements-breakdown.md` §6).

**TDD does not apply:** the ticket changes architecture text only (ADR 0061, the context map, three canvases, two glossary references, one ledger row and this file). There is no executable behaviour to drive with a failing test. The rules it fixes are tested by the tickets that build them, each red first: ST-172a (gap states and order, Rule 3), ST-173a (flag-off plan unchanged, Rule 4), ST-171e (snapshot key, Rule 2), ST-170a (lint refuses `measured` and point values, Rule 1 and Rule 3.3), QA-REF-GOLD (vectors, Rule 6). Doc checks run instead (below).

## 1. Decisions

| Date | Role | Decision | Evidence | Reason |
|---|---|---|---|---|
| 2026-11-13 | principal-engineer | **Placement:** `PatternDefinition` and `ReferenceSet` are Sport Plug-in Published Language (R5), coach-owned content; `PatternMeasure` is Analytics (`racket.analytics.patterns` (planned)); the reference gap is Coaching (`racket.coaching.weakness`); `racket.coaching.reference` (planned) is only the ACL read side (R13) | ADR 0061 Rule 1; context map R5, R8, R13 | One owner per concept (PE-PLAN06-05, PE-PLAN06-12) [EP/ENG-13] |
| 2026-11-13 | principal-engineer | **Measured references refused in Sprint 6** by the lint until ADR 0062 (planned) defines a committed provenance export | ADR 0061 Rule 1 | The content lint cannot read Capture & Media tables; fail closed (FR-170.R3) |
| 2026-11-13 | principal-engineer | **Keys:** measure snapshot `(subject = owner, match, side; pattern id; match version; rules_version; definition version)`; gap result = pooled measure keys + reference set id and version, computed on read in Sprint 6 | ADR 0061 Rule 2 | PE-PLAN06-04; NFR-075.1 |
| 2026-11-13 | principal-engineer | **Gap rule:** non-overlap of 95 % intervals (`wilson` or `order_statistic_median`) on the worse side by `better_direction`, touching ends = overlap; min_n; size in reference widths; order (−size, −rallies lost on the linked ADR 0003 cell, catalogue order, pattern id) | ADR 0061 Rule 3 | ADR 0005; conservative by design (p ≈ 0.006, computed) |
| 2026-11-13 | principal-engineer | **AN-04 not rankable as defined** (no interval method); recommendation to COACH-6a: compare the AN-07 unforced-error share instead | ADR 0061 Rule 3.1; `backend/src/racket/analytics/starter_stats.py` | No interval → no honest gap |
| 2026-11-13 | principal-engineer | **A4: ADR 0003 not superseded.** Plan = ADR 0003 top 3, then ranked gaps not already covered, up to 5 targets; flag off → identical plan | ADR 0061 Rule 4 | Reference values are judgment or secondary statistics until P11/P15 (judgment) |
| 2026-11-13 | principal-engineer | **A1: exercise = `DrillAssignment`**, linked by `target_metrics` and the catalogue §5 `share:` rule; `Citation` gains reference fields | ADR 0061 Rule 5 | No new aggregate [AQS/ENG-04] |
| 2026-11-13 | principal-engineer | **Pure code for the S7 port:** stdlib-only domain modules; QA-REF-GOLD JSON vectors are the port's conformance suite | ADR 0061 Rule 6 | P21 pending; keep both answers cheap |
| 2026-11-13 | principal-engineer | **ADR index not edited** here: README and decision-log index rows are added at the sprint close (RETRO-06), as for ADRs 0057-0060, so parallel ADR tickets (PE-6b) do not conflict on the same lines | `docs/decisions/README.md` index ends at 0056 | Avoid a merge conflict between gate tickets (judgment) |

## 2. Cost per PR (ADR 0056 decision 1)

| Round | wall_time_min | total_cost_usd | Note |
|---|---|---|---|
| Author build | not measured | not measured | the session does not expose per-ticket wall time or cost to the agent |
