# 0061. Reference patterns and the player-vs-reference comparison: one owner per concept, a non-overlap gap rule, ADR 0003 kept as the plan's first ordering, exercises are drill assignments

- **Status:** Accepted (principal-engineer, owner of the domain model and the context map; tier 0 review per ADR 0056). The numeric defaults marked (judgment) are reviewed by the pickleball-domain-coach in COACH-6a and by QA-REF-GOLD; a change to a rule here is a new ADR (README rule 4).
- **Date:** 2026-11-13
- **Deciders:** principal-engineer
- **Consulted:** pickleball-domain-coach (owner of pattern definitions and reference values, COACH-6a/6c), senior-ml-cv-engineer (pattern sources, ML-6), senior-backend-engineer (ST-170a, ST-171a/e, ST-172a, ST-173a), business-analyst (FR-170..FR-173, glossary), security-privacy-engineer (measured sources, ADR 0062 (planned) by PE-6b)
- **Related:** ticket PE-6a, Sprint 6 wave 1 gates (`docs/sprints/sprint-06.md` §3.2, §3.7); FR-170..FR-173 and assumptions A1, A4, A6 (`docs/sprints/06/requirements-breakdown.md`); review findings PE-PLAN06-04, PE-PLAN06-05, PE-PLAN06-12 (`docs/sprints/06/review-rounds.md`); ADR 0003 (rallies-lost ranking), ADR 0005 (Wilson interval, min n, non-overlap), ADR 0041 (thresholds in the dictionary), ADR 0042 (purge), ADR 0044 (content status ladder), ADR 0047 (gates first); PO instruction 2026-11-12 (`docs/requirements/po-input-2026-10-05.md`, addendum "Video analysis (PO 2026-11-12)")

## Context and problem statement

The PO's instruction of 2026-11-12 asks for "getting best practices and patterns, then work out any weaknesses and provide or recommend the exercises to fix those weaknesses". Sprint 6 builds that as a tag-based slice: a cited **reference set** of patterns, the same patterns **measured** in the player's tagged matches, the **gaps** ranked with n and uncertainty, and **drills** that close the top gaps (sprint-06 §1).

Four concepts are new and three contexts could own each of them. The plan left five questions to this ADR:

1. **Placement.** Who owns `PatternDefinition`, `ReferenceSet`, `PlayerPatternMeasure` and the gap rule? PLAN-06 review found two owners named for references (PE-PLAN06-05) and a loader placed under `coaching/reference/` (PE-PLAN06-12).
2. **The gap statistic.** When is a difference from the reference a weakness, and how are weaknesses ordered (FR-172.R1-R4)?
3. **The relation to ADR 0003 (A4).** The product already ranks weaknesses by rallies lost per game, and the plan uses that ranking today. What happens to it?
4. **Drill linkage and A1.** How does a gap find a drill, and what is an "exercise"?
5. **Keys.** What identifies a stored measure and a gap result (PE-PLAN06-04, NFR-075.1)?

A further constraint is that a Go port is planned for Sprint 7, pending P21. Code written now must be easy to port.

## Decision drivers

- One model per bounded context, an explicit relationship on each edge, and an ACL where the downstream side must protect its language [EP/ENG-13]. Canvases and the context map record the result [EP/ENG-12, EP/ENG-11].
- The map's rules hold: no cross-context table reads, a pure domain layer, IDs only across boundaries (`docs/architecture/context-map.md` §4).
- The weakness view must not call a difference a weakness when the data cannot tell it from noise. ADR 0005 already settles a 95 % Wilson interval, a minimum n and a non-overlap rule for efficacy claims.
- Every value must say where it came from (FR-170.R5). A reference that was not measured from pro matches must never read as if it were.
- The rallies-lost ranking (ADR 0003) is accepted by the PO and drives the plan; changing the plan's ordering is a product change that needs evidence we do not have yet (judgment).
- No speculative machinery [AQS/ENG-04]: no new aggregate when an existing one carries the meaning; no new statistics library; no framework in domain code.
- Explanations must say why [DPA/DESIGN-11]; the coaching AI is a workflow of rules, selection and validation [DPA/AI-01], and nothing an LLM writes reaches the Why (none is used in Sprint 6).

## Considered options

### Q1. Where the four concepts live

1. **Coaching owns everything:** patterns, references, measures and gaps all in `racket.coaching`.
2. **Analytics owns everything:** Analytics measures, compares and ranks; Coaching consumes ranked gaps.
3. **Split by kind of knowledge (chosen):** definitions and reference values are sport content (Sport Plug-in, Published Language); measures are analysis of the player's matches (Analytics); the gap rule is a coaching judgement (Coaching, `weakness` module) and reads the other two through its ACL.

### Q2. The gap statistic

1. **Point comparison:** any player value on the worse side of the reference value is a gap.
2. **Hypothesis test per pattern:** a two-proportion z-test (or exact test) at α = 0.05.
3. **Non-overlap of 95 % intervals with a minimum n (chosen):** the player's interval lies wholly on the worse side of the reference interval or band.

### Q3. Relation to the ADR 0003 ranking (A4)

1. **Replace:** the reference-gap ranking becomes the plan's ordering; ADR 0003 is superseded.
2. **Merge into one score:** combine rallies lost and gap size into one number.
3. **Two views, ADR 0003 first (chosen):** the rallies-lost ranking keeps ordering the plan's first targets; reference gaps are a second, separately labelled list that adds targets after them and links to ADR 0003 only as a tie-break.

### Q4. What an exercise is (A1)

1. **New `Exercise` aggregate** with its own lifecycle and storage.
2. **Exercise = a `DrillAssignment` from the existing library (chosen),** linked to a gap through the drill's `target_metrics`.

## Decision outcome

### Rule 1. Placement: one owner per concept

| Concept | Owner (context, module) | Kind | Why |
|---|---|---|---|
| `PatternDefinition` (id `AN-nn`, definition version, data source, `better_direction`, `interval_method`, min_n, level bands) | **Sport Plug-in**, `racket.sports.pickleball` as a versioned file `patterns.json` (planned) with its own lock, next to the metric dictionary. The coach writes the definitions (COACH-6a); the code only loads them | Published Language (R5) | A pattern is sport knowledge, like a metric definition (ADR 0041). Analytics needs it to measure and Coaching needs it to judge; one published source keeps them from drifting |
| `ReferenceSet` and its entries (pattern × level band × format, value or band, n, interval, `source_type`, source id, status, version, provenance label) | **Sport Plug-in content**: files under `content/references/pickleball/` (planned) with a lock hash per published version; the schema, loader, lint (`racket-reference-lint`) and lock check in `racket.sports.references` (planned), a pure sport-neutral module | Published Language (R5), coach-owned content (ADR 0044 status ladder) | One owner (PE-PLAN06-05). Reference values are versioned content like drills, not state that users change; no table, no aggregate |
| `PatternMeasure` and its snapshot | **Analytics**, `racket.analytics.patterns` (planned): a pure `domain` that computes a measure from the score sheet (Quick Tag) and Full Tag labels, the interval functions (reusing `racket.analytics.uncertainty` unchanged), the snapshot repository, and the pooling function | Analytics model, published through `racket.analytics.public` | Measuring the player's matches is what Analytics does; the interval maths must have one home (`uncertainty.py`), as the existing `pooled_low_sample` port already shows |
| Reference gap (`GapResult`: state, side, size, the measure and reference it compares) and the gap ordering | **Coaching**, `racket.coaching.weakness`: a pure module next to `rank()` (`gap` (planned)) | Coaching model | Calling a difference a weakness is a coaching judgement and feeds the plan; it sits beside the ADR 0003 ranking it is ordered against |
| Exercise | **Coaching**, `racket.coaching.plan`: it is a `DrillAssignment` (Rule 5) | existing aggregate | A1 |

**ACL read side (closes PE-PLAN06-12).** `racket.coaching.reference` (planned) is **only** the Anticorruption Layer that turns published reference entries into Coaching's `ReferenceValue` (value or band, interval, width, `better_direction`, reference id, version, status, provenance label). It filters to `coach-reviewed` and `verified` entries (FR-170.R4) and fails closed: an entry it cannot translate is dropped and the pattern reads "no reference yet", never a guessed value. It holds no schema, no lint and no lock; those belong to the publisher. ST-170a's directories follow this rule: schema, loader, lint and lock in `racket.sports.references`; the ACL in `racket.coaching.reference`.

**Measured references.** An entry with `source_type: measured` needs a footage provenance record that permits "reference-library" (FR-170.R3), which lives in Capture & Media (ADR 0062 (planned), PE-6b). The content lint cannot read that context's tables, so in Sprint 6 the lint refuses every `measured` entry (fail closed) until ADR 0062 defines a committed, resolvable provenance export. Sprint 6 references are `published` (citation resolves in `docs/domain/sources.md` (planned)) or `judgment` (labelled "coach judgment, not measured from pro matches").

### Rule 2. Keys (closes PE-PLAN06-04 at the design level)

- **Measure snapshot key:** `(subject, pattern_id, match_version, rules_version, definition_version)`, where `subject = (owner_id, match_id, side)` and `match_version` is the score sheet's `sheet_version` (plus the Full Tag label-set version when the pattern reads Full Tag). The same `sheet_version` guard as ADR 0040 applies: a repeated or late event writes nothing. A deleted match's measures are removed by `racket.analytics.public.purge_match` (ADR 0042), and a revoked consent deletes derived measures within the ADR 0006 window (FR-174.R3).
- **Gap result key:** the sorted tuple of measure snapshot keys it pools, plus `(reference_set_id, reference_version)`. Gap results are **computed on read** in Sprint 6 (at most a few patterns per player, pure functions; NFR-010.10-.12 decides whether a cache is needed). If a cache is added, Coaching owns it, it uses this key, and any change of either half invalidates the row.

### Rule 3. The gap statistic (FR-172.R1-R4)

1. **Interval per measure.** Each measure carries a 95 % interval by its `interval_method`: `wilson` for proportions (the existing `uncertainty.wilson`, z = 1.95996, ADR 0005) and `order_statistic_median` for the AN-13 median (FR-171.R4). A pattern whose definition names no supported method gets no reference entry (the lint refuses one), so it is shown with its value and n in the state "no reference yet" and is never ranked; no new state is added to FR-172. In particular AN-04 (unforced errors per game, a count rate with no interval today) is not rankable as defined; the recommendation to COACH-6a is to compare the AN-07 unforced-error share (a proportion of the side's rally endings, Wilson; a new `AN-07:unforced-error` plan target the coach defines in the catalogue) and show AN-04 per game as context (judgment). Adding a method is a new ADR note with QA-REF-GOLD vectors.
2. **Minimum n.** Below the pattern's min_n (A6: 20 opportunities for proportions; ≥ 6 rallies for AN-13), or with `low_sample` set by the ADR 0041 dictionary rule, the measure is "not enough data" with n and the min_n it needs (FR-172.R2).
3. **Reference interval.** A `published` or `measured` entry with n has its 95 % interval by the same method as the pattern; the lint computes it from k and n where they are given, so it is never hand-typed. A `judgment` entry is a band `[low, high]` with no n. A point value with neither n nor band is refused by the lint.
4. **Weakness = non-overlap on the worse side.** The pattern is a weakness only when the player's interval lies wholly on the worse side of the reference interval or band, by `better_direction`: `higher` → player high < reference low; `lower` → player low > reference high; `inside_band` → either side, and the result names the side ("below band", "above band"). Touching end points count as overlap (no gap). Overlap, or the better side, is "no clear gap". No reference for the player's level band and format is "no reference yet" (FR-172.R3).
5. **Size and order.** Gap size = the distance from the player's interval edge nearest the reference to the reference edge on that side, divided by the reference width (band width, or interval width for an interval reference). Weaknesses sort by **(−size, −rallies lost on the linked ADR 0003 cell, catalogue order, pattern id)**. The linked cell is the weakness-catalogue cell whose primary metric (`docs/domain/weakness-catalogue.md` §5) is the pattern's AN id; with no linked cell the term is 0. The last key makes the order total, so the result is permutation-stable.
6. **Level band and format.** The player's level band is the plan `Preferences.level` (the drill library's `beginner` / `intermediate` / `advanced` enum); the format comes from `racket.matches.public.owned_format`. Pooled measures pool only matches of that format.

**Why non-overlap, which is conservative.** With equal standard errors, two 95 % intervals separate only when the difference exceeds 2 × 1.96 = 3.92 standard errors of one estimate, that is 3.92 / √2 ≈ 2.77 standard errors of the difference, a two-sided p of about 0.006 instead of 0.05 (computed; judgment that this is the right trade). The rule misses some real gaps, and it is meant to: telling an amateur "you are worse than the reference" on noise is the failure the PM-6 metric PM6-M2 counts. It is also the rule ADR 0005 already uses for efficacy claims, it works the same way for bands that have no n, and it needs no test statistic per interval method.

### Rule 4. Relation to the ADR 0003 ranking (A4)

- **ADR 0003 is not superseded.** The rallies-lost ranking stays the plan's primary ordering and stays visible in the weakness view, including when there is no clear gap (FR-172.R5).
- **The plan's targets** (ST-173a): the ADR 0003 top 3, as today, then the ranked reference gaps in Rule 3 order whose AN id is not already the primary metric of a chosen ADR 0003 weakness, up to **5 targets in total** (judgment; the coach may change the cap through the catalogue). Where a gap's AN id is already a chosen weakness's primary metric, no new target is added; that assignment's Why also cites the reference (FR-173.R2).
- **Ranked gaps beyond the cap** are listed in the weakness view with the drills that fit them, labelled "not in this plan", so each ranked weakness still yields at least one fitting drill (FR-173.R1).
- **Flag off, plan unchanged.** With `FEATURE_REFERENCE_PATTERNS` off, or with no ranked gap, plan generation produces exactly today's plan; ST-173a carries a regression test for this.
- Revisit trigger: a later ADR may let gaps lead the plan once plan efficacy can be measured (ADR 0005 efficacy rule) and a coach verifies references (P15).

### Rule 5. Exercises and drill linkage (A1)

- **An exercise is a `DrillAssignment`** from the existing library in the existing `TrainingPlan` aggregate. There is no `Exercise` aggregate, table or route. "Exercise" is UI wording only (glossary, `docs/process/ddd-guidelines.md` §6).
- **Linkage is by `target_metrics`.** A drill fits a gap when its `target_metrics` (schema pattern `^AN-[0-9]{2}$`, `backend/src/racket/coaching/drills/schema.json`) contains the pattern's AN id, and it fits players, equipment, level, time and safety class by the existing selection rules (QD-PL-02). A qualified pattern (for example an AN-07 category share) uses the existing `AN-nn:qualifier` plan-target form and matches as `docs/domain/weakness-catalogue.md` §5 already defines: the AN id in `target_metrics` plus the `share:` skill for an AN-07 share. The drill schema does not change. Pattern ids therefore reuse AN ids; FR-107 (AN-08..AN-14) gives the numbers.
- **The Why** is template text from cited fields only (FR-173.R2): pattern id, player value, n, interval and `interval_method`, reference value or band, reference id and version, status and provenance label. The plan `Citation` value object gains these fields (ST-173a); a plan stores the reference version it was built with, so a new reference version changes the Why only at the next plan generation and never rewrites an existing plan (FR-173.R4).
- **Coverage** (ST-173b): a rankable pattern × level × players × equipment cell with no fitting drill fails the coverage check, naming the cell (FR-173.R3).

### Rule 6. Pure code, ready for the Sprint 7 port

Every new domain module (`racket.sports.references`, `racket.analytics.patterns` domain, `racket.coaching.weakness` gap, the `racket.coaching.reference` translation) is standard library only: no I/O, clock, randomness, NumPy or SciPy in domain code (the Wilson interval and the binomial cut-off for the order-statistic interval are closed-form or a small loop). Values cross module boundaries as frozen dataclasses of ints, floats, strings and tuples, with rounding only at serialisation. QA-REF-GOLD's frozen input/output vectors (JSON) are the conformance suite a port must pass unchanged. `backend/tests/unit/test_architecture.py` and `backend/tests/unit/test_architecture_context_imports.py` already enforce the import rules for these paths.

## Pros and cons of the options

### Q1-1: Coaching owns everything
- Good: one module to read.
- Bad: Analytics would have to ask Coaching how to measure, or Coaching would compute measures from Analytics' sheet, breaking map rule 1. Reference content becomes a Coaching aggregate with two owners (PE-PLAN06-05).

### Q1-2: Analytics owns everything
- Good: measuring and comparing sit together.
- Bad: "weakness" and the plan link are coaching language; Analytics would need the drill catalogue and the ADR 0003 tie-break. The R8 ACL would carry judgements instead of facts.

### Q1-3: split by kind of knowledge (chosen)
- Good: each concept has one owner and one reason to change; the existing R5 and R8 edges carry the new data, so the map gains no new context; the domain code stays pure.
- Bad: three modules change for one feature, and the ACL needs a translation test (ST-172a). Judgment: worth it for the boundaries.

### Q2-1: point comparison
- Good: simple, always gives an answer.
- Bad: ranks noise as weakness at small n; contradicts ADR 0005 and FR-172.R1.

### Q2-2: hypothesis test per pattern
- Good: more power than non-overlap.
- Bad: needs a test per `interval_method` and has no meaning against a judgment band with no n; with several patterns per player it needs a multiplicity correction; it is harder to explain in the Why (judgment) [DPA/DESIGN-11].

### Q2-3: non-overlap with min n (chosen)
- Good: one rule for every interval method and for bands; matches ADR 0005; explainable as "your range does not touch the reference range".
- Bad: conservative (p ≈ 0.006 for equal widths), so real but small gaps read "no clear gap" until n grows.

### Q3-1: replace ADR 0003
- Good: one ranking.
- Bad: the reference values are coach judgment or secondary statistics until P11/P15; leading the plan with them would move an accepted PO decision (OQ-08, ADR 0023) on weaker evidence.

### Q3-2: merge into one score
- Good: one list.
- Bad: mixes units (rallies lost per game and band widths) with an arbitrary weight; not explainable [DPA/DESIGN-11]; speculative [AQS/ENG-04].

### Q3-3: two views, ADR 0003 first (chosen)
- Good: no regression for current users (flag off is identical); both views honest about their units; gaps still reach the plan.
- Bad: two lists to explain in the UI (PD-6 designs the labels).

### Q4-1: Exercise aggregate
- Good: room for exercise-only fields later.
- Bad: duplicates `DrillAssignment` (minutes, drill id, session, done state); a new table, routes and purge path for no new behaviour [AQS/ENG-04].

### Q4-2: Exercise = DrillAssignment (chosen)
- Good: no new model, reuses selection, coverage, eval and purge; the PO's word maps to an existing term.
- Bad: the `Citation` value object grows (reference fields); ST-173a carries that change.

## Consequences

- **Context map** (`docs/architecture/context-map.md`): R5 now carries pattern definitions and reference sets; R8 carries pattern measures; new row **R13** records that Coaching reads reference content through its ACL. No new context and no new edge in the drawing.
- **Canvases** updated: Sport Plug-in, Analytics, Coaching (`docs/architecture/contexts/`).
- **Tickets that follow this ADR:** ST-170a (schema, lint and lock in `racket.sports.references`; measured entries refused); ST-171a/e (measures and snapshot key in `racket.analytics.patterns`); ST-172a (gap rule, Rule 3, in `racket.coaching.weakness`); ST-172b (ACL and read API); ST-173a (plan targets per Rule 4, Citation fields per Rule 5); ST-173b (coverage axis); QA-REF-GOLD (vectors for Rules 3 and 6); COACH-6a (each pattern's `interval_method`, min_n and the AN-04 recommendation in Rule 3.1).
- **CI-TIERS-06** globs stay valid: `content/references/**` is content (tier 1 with the coach); the measure snapshot under `analytics/patterns/snapshot*` is personal data (tier 2).
- **Risk:** the reference values in Sprint 6 are coach judgment or published secondary statistics, not pro footage. Mitigation: provenance label on every value (FR-170.R5), `measured` refused until ADR 0062, conservative gap rule, and ADR 0003 still leading the plan.

## Evidence

| Claim | Evidence | Type |
|---|---|---|
| Context-mapping patterns, canvases, DDD starter process | [EP/ENG-13], [EP/ENG-12], [EP/ENG-11] | verified source |
| Wilson interval, z, min n, non-overlap rule already accepted | ADR 0005 (Accepted 2026-10-17, PM-4 note); `backend/src/racket/analytics/uncertainty.py` (`Z95`) | repo |
| Pooling helpers already live in Analytics' port | `backend/src/racket/analytics/public.py` (`pooled_low_sample`) | repo |
| Drill targets are AN ids and plan targets use the `AN-nn:qualifier` form | `backend/src/racket/coaching/drills/schema.json` (`target_metrics` pattern); `backend/src/racket/coaching/plan/domain/model.py` (`plan_targets` split on `:`); `docs/domain/weakness-catalogue.md` §5 (AN-07 shares through `share:` skills) | repo |
| AN-04 is a count per game with no interval today | `backend/src/racket/sports/pickleball/metrics.json` (AN-04 `count_per_game`); `backend/src/racket/analytics/starter_stats.py` (AN-04 has no interval) | repo |
| Level enum and format port exist | `backend/src/racket/coaching/plan/domain/model.py` (`Preferences.level`); `backend/src/racket/matches/public.py` (`owned_format`) | repo |
| Non-overlap of equal 95 % intervals ≈ p 0.006 | 3.92 / √2 = 2.77 standard errors of the difference; two-sided normal tail at 2.77 ≈ 0.0056 | computed |
| Push back on speculative engineering | [AQS/ENG-04] | verified source |
| Explanations should say why | [DPA/DESIGN-11] | verified source |
| Coaching AI as a workflow of rules, selection, validation | [DPA/AI-01] | verified source |
| Target cap 5, AN-04 recommendation, Q3 choice | — | judgment |

## Confirmation

- ST-172a unit and scenario tests cover each Rule 3 state (weakness below and above, no clear gap at touching ends, better side, not enough data, no reference yet including a pattern with no supported interval method) and the total order; a property test shows the order is permutation-stable.
- ST-173a regression test: with `FEATURE_REFERENCE_PATTERNS` off the plan equals today's plan for the GS-AN-1 fixture.
- `backend/tests/unit/test_architecture.py` and `backend/tests/unit/test_architecture_context_imports.py` stay green with the new modules (no framework in domain code, no cross-context import outside the ports).
- QA-REF-GOLD vectors pass on the Python code; the S7 port runs the same vectors.
- The reviewer on this PR confirms Rules 1-6 against FR-170..FR-173 and A1, A4.
