# Canvas: Coaching (with the Drill Library module, C1)

- **Status:** Accepted (2026-10-03, principal-engineer)
- **Code modules:** `racket.coaching`, `racket.coaching.drills` (C1)
- **Aggregates:** `TrainingPlan` (owns `Session`, `DrillAssignment`), `Drill` (library entry, versioned by `library_version`)

## Purpose
Assemble training plans from the curated drill library for the player's ranked weaknesses. Explain each "why" with evidence, and score plans afterwards.

## Strategic classification
- **Domain:** Core. Plans traceable to a stat and a vetted drill (spec §2).
- **Evolution:** custom-built. The LLM sits behind an ACL.

## Domain roles
Decision support. A workflow: rules rank weaknesses → the LLM selects drills via tools → a validator checks IDs [AQS/AI-01].

## Inbound communication
`WeaknessesRanked`, metric snapshots and evidence from Analytics (R8). Drill tags from the Sport Plug-in (R5). Drill curation by the domain coach (module-internal after C1).

## Outbound communication
`TrainingPlanGenerated`, `PlanProposalRejected`, `TrainingPlanEvaluated`. Prompts to the LLM provider go through the **ACL** (R11).

## Ubiquitous language
Training plan, session, drill assignment, drill, library version, "why" (evidence-linked), weakness, point leak (= rallies lost attributable to a weakness, ADR 0003; see the glossary).

## Business decisions
- The LLM never invents drills. Every drill ID and metric is validated before persisting [AQS/SEC-08 API10] (NFR-059).
- Only pseudonymous aggregates are sent to the LLM (NFR-068).
- C1: drills are a module, not a separate context, until coaches author drills independently (context map CM-3).

## Assumptions
About 80 drills at M5 (spec).

## Verification metrics
LLM-output regression suite (NFR-059); coaching evals with 20-50 cases [AQS/AI-03].

## Open questions
LLM provider SDK details (after SPIKE-03); plan efficacy claims (ADR 0005).
