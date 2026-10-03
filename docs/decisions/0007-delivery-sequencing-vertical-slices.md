# 0007. Delivery sequencing: Sprint 0 foundations, then one demonstrable vertical slice per sprint

- **Status:** Proposed. Sprint 0 does not depend on this ADR's open part. Sprints 1+ depend on ADR 0002 (OQ-02). The human product owner ratifies both at the Sprint 0 review (2026-10-16).
- **Date:** 2026-10-03
- **Deciders:** engineering-manager (R/A for sprint process, working-agreement §4); human product owner (approves release scope)
- **Consulted:** principal-engineer (technical sequencing), senior-qa-engineer (test readiness), product-manager (value order, via `brainstorm-product.md` §11), business-analyst (via the FR/NFR registers)
- **Related:** `docs/sprints/roadmap.md`, `docs/sprints/sprint-00.md`..`sprint-02.md`; ADR 0002 (release slicing), ADR 0009 (rules-engine readiness), ADR 0010 (estimation and capacity); OQ-01, OQ-02

## Context and problem statement

ADR 0002 (Proposed) cuts the MVP into R1 (walking skeleton on manual Quick Tag, no computer vision) and R2 (first automation plus LLM explanations). It leaves the sprint-by-sprint order to the engineering-manager. We must decide:

- what Sprint 0 contains;
- in which order the R1 and R2 epics are built;
- what each sprint demonstrates.

The order has to work while three blockers are open: the rulebook is unverified (OQ-01, [DOM G1]), the release slicing is not yet approved (OQ-02), and no legal review exists for a real-user beta (NFR-070, [AQS G3.5]).

## Decision drivers

- Every sprint ends with working software shown against a bullet-list sprint goal [EP/ENG-15].
- Small batches and robust testing, because AI adoption correlated with lower delivery stability [EP/ENG-22]; PRs of about 100 lines [EP/ENG-04].
- Start with the simplest thing that works and add complexity only when it helps [EP/ENG-25, DPA/AI-01].
- Code without tests is incomplete; unit tests gate every merge, and integration and E2E tests cover the interfaces [EP/ENG-20]. The test harness and gates must therefore exist before the first feature story.
- Long-running agent work needs a progress file, a smoke test at session start, and one feature at a time [EP/ENG-28].
- Spec §7 note: manual tagging comes first so that analytics and coaching can be built on real data while models are trained.
- The CV risks (GPU cost, ball-tracking domain gap, AGPL licences) need measured spike data before R2 work is committed (ENG §8; [DOM/CV-05], [DOM/CV-01]).

## Considered options

1. **Sprint 0 foundations, then one vertical slice per sprint along the R1 value chain** (upload → tag → score sheet → stats → plan), then hardening; R2 vision work starts only after spikes run in the ML lane during R1.
2. **Layered build:** all domain and backend work for R1 first (rules engine, analytics, coaching), the UI afterwards.
3. **Spec milestone order (M0 → M5):** the plan only arrives after four CV milestones. ADR 0002 already rejects this ordering.
4. **CV first:** start the ball-tracking and court-calibration work in Sprint 1, because it is the riskiest part.
5. **Do nothing:** plan each sprint on its own with no roadmap.

## Decision outcome

Chosen option: **Option 1.**

- **Sprint 0 (foundations and walking skeleton):** repo, Docker Compose parity, CI gates, agent hooks, test harness, the mandatory regression-suite scaffolds, and one thin path (create match → upload fixture → queue → worker probe → result on screen) with one trace across it. This is the smallest end-to-end path that exercises every deployable and backing service [EP/ENG-28, AQS/OPS-05].
- **Sprints 1-5 (R1):** each sprint adds the next link of the value chain, so each review shows a longer journey working end to end. The rules engine is built test-first in Sprint 1, in parallel with upload, because it is pure logic and the first TDD target [EP/ENG-18; testing-strategy §3].
- **ML lane during R1:** licence posture (SPIKE-01, Sprint 0), labelling tool and gold-set manifests (Sprint 3), then SPIKE-02/03/04/05/07 in Sprints 3-5. Each ends in an ADR with data before the matching R2 sprint is committed.
- **Sprints 6-9 (R2):** M1 (calibration, players), then ball/hit/bounce, then rally segmentation and review queue, then the LLM explanation and efficacy.
- **R3 and Later:** goals only; planned just in time.

## Pros and cons of the options

### Option 1: foundations, then vertical slices
- Good: every review demonstrates a user-visible journey, and the E2E journey test grows each sprint.
- Good: integration risk shows up in Sprint 0, while the codebase is still small.
- Good: CV risk is retired by spikes in parallel, without blocking R1 value.
- Bad: Sprint 0 shows little product value; the demo is a technical walking skeleton.
- Bad: front-end and back-end agents must coordinate inside each sprint (mitigated by contract-first API schemas, judgment).

### Option 2: layered
- Good: fewer cross-role hand-offs per sprint.
- Bad: nothing demonstrable to a user until late; UI and accessibility defects surface late (judgment).
- Bad: violates "each sprint ends with something demonstrable" from the request.

### Option 3: spec order
- Bad: rejected in ADR 0002 (no plan until M5; every CV risk delays all value).

### Option 4: CV first
- Good: attacks the largest technical risk early.
- Bad: no labelled pickleball data exists yet [DOM/DOMAIN-09, DOM/DOMAIN-10]; the labelling tool and consented footage come first (spec §8; OQ-06).
- Bad: the licence posture is undecided (OQ-12) [DOM/CV-05, DOM/CV-07].

### Option 5: do nothing
- Bad: no stable Definition of Ready horizon; scope creep.

## Consequences

- **Good:** a single roadmap (`docs/sprints/roadmap.md`) maps every FR/NFR to a sprint, and the traceability matrix carries those assignments.
- **Trade-offs accepted:**
  - Sprint 0's demo is technical.
  - R1 cannot be released to real users until NFR-070 (legal gate) is met, whatever the sprint progress. Demos use synthetic or team-recorded, consented footage only (OQ-06 recommendation).
  - Score sheets are labelled "unofficial scoring" until OQ-01 is answered (FR-055).
- **Follow-up work:**
  - Detailed sprint files exist only for Sprints 0-2. Sprint 3 onward is planned just in time at each sprint planning.
  - If the PO rejects ADR 0002, the EM re-plans Sprints 1+ and supersedes this ADR. Sprint 0 is valid under every option in ADR 0002.

## Evidence

| Claim | Evidence | Type |
|---|---|---|
| Sprint goal as short bullets; judge success against it; retro actions owned and dated | [EP/ENG-15] | verified source |
| Keep changes small (~100 lines) | [EP/ENG-04] | verified source |
| AI adoption correlated with lower stability; small batches | [EP/ENG-22] | verified source |
| Start simple; workflows before autonomy | [EP/ENG-25], [DPA/AI-01] | verified source |
| Code without tests is incomplete; layered test mix | [EP/ENG-20] | verified source |
| Progress file, smoke test, one feature at a time | [EP/ENG-28] | verified source |
| Dev/prod parity of backing services | [AQS/OPS-05] | verified source |
| Rules engine is the first TDD target; red-green-refactor | [EP/ENG-18]; testing-strategy §3 | verified source + accepted process doc |
| No mature open-source pickleball CV project or dataset | [DOM/DOMAIN-09], [DOM/DOMAIN-10] | verified source |
| Ultralytics and BoxMOT are AGPL-3.0 | [DOM/CV-05], [DOM/CV-07] | verified source |
| Manual tagging first so analytics/coaching use real data | spec §7 note | spec |
| Sprint-by-sprint content and order | (judgment), building on PROD §11 and ENG §9 | judgment |
| Test results | Not applicable: no code yet | — |

## Confirmation

- Each sprint review shows the sprint goal bullets with evidence (test reports, E2E run, demo script output).
- The E2E journey (QD §7) grows each sprint and is green on `main` for ≥ 5 nightly runs before the R1 review (QD-QG-S4).
- Retro 0 and retro 1 check whether the order held; any change is a superseding ADR.

## Notes
