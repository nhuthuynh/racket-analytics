# Canvas: Coaching (with the Drill Library module, C1)

- **Status:** Accepted (2026-10-03, principal-engineer)
- **Code modules:** `racket.coaching`, `racket.coaching.drills` (C1)
- **Aggregates:** `TrainingPlan` (owns `Session`, `DrillAssignment`), `Drill` (library entry, versioned by `library_version`). An **exercise** (PO word, 2026-11-12) is a `DrillAssignment`, not an aggregate (A1, ADR 0061 Rule 5)

- **R1 design (Sprint 4):** rules-only plan, no LLM: [`../coaching-plan.md`](../coaching-plan.md); HTTP: [`../api-sprint-04.md`](../api-sprint-04.md) §2-§3. Inbound is R8 through the ACL and R12 (context map).

## Purpose
Assemble training plans from the curated drill library for the player's ranked weaknesses. Explain each "why" with evidence, and score plans afterwards.

## Strategic classification
- **Domain:** Core. Plans traceable to a stat and a vetted drill (spec §2).
- **Evolution:** custom-built. The LLM sits behind an ACL.

## Domain roles
Decision support. A workflow: rules rank weaknesses → the LLM selects drills via tools → a validator checks IDs [AQS/AI-01].

## Inbound communication
`WeaknessesRanked`, metric snapshots and evidence from Analytics (R8). Pattern measures from Analytics (R8). Reference entries from the Sport Plug-in through the reference ACL `racket.coaching.reference` (planned), which only translates and filters (R13, ADR 0061). Drill tags from the Sport Plug-in (R5). Drill curation by the domain coach (module-internal after C1).

## Outbound communication
`TrainingPlanGenerated`, `PlanProposalRejected`, `TrainingPlanEvaluated`. Prompts to the LLM provider go through the **ACL** (R11).

## Ubiquitous language
Training plan, session, drill assignment (= exercise), drill, library version, "why" (evidence-linked), weakness, reference gap (weakness below / above, no clear gap, not enough data, no reference yet), point leak (= rallies lost attributable to a weakness, ADR 0003; see the glossary).

## Business decisions
- The LLM never invents drills. Every drill ID and metric is validated before persisting [AQS/SEC-08 API10] (NFR-059).
- Only pseudonymous aggregates are sent to the LLM (NFR-068).
- C1: drills are a module, not a separate context, until coaches author drills independently (context map CM-3).
- Reference gap (ADR 0061 Rule 3, in `racket.coaching.weakness`): a weakness only when the player's 95 % interval lies wholly on the worse side of the reference interval or band; ordered by gap size in reference widths, then rallies lost on the linked ADR 0003 cell. ADR 0003 still chooses the plan's top 3 targets (FR-121, `MAX_WEAKNESSES`); ranked gaps add no target, cite the reference on a target they share, and otherwise show as "not in this plan" with fitting drills (Rule 4). A drill fits a gap through `target_metrics` (Rule 5).

## Assumptions
About 80 drills at M5 (spec).

## Verification metrics
LLM-output regression suite (NFR-059); coaching evals with 20-50 cases [AQS/AI-03].

## Open questions
LLM provider SDK details (after SPIKE-03); plan efficacy claims (ADR 0005).
