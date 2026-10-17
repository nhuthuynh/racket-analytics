# 0051. Sprint 4 lands a runnable prototype first; R1 privacy and quotas ship behind default-off flags with interim wording; the R2 spikes wait on the PO; the roadmap is renumbered

- **Status:** Accepted (the engineering-manager is R/A for sprint scope and order, working-agreement §4). The human product owner may veto it at the Sprint 4 review on 2026-12-11.
- **Date:** 2026-10-17 (Sprint 4 planning, ticket PLAN-04)
- **Deciders:** engineering-manager
- **Consulted:** product-manager (goal wording, interim wording), principal-engineer (slicing, contexts, flag design), business-analyst (FR/NFR traceability, DoR), senior-qa-engineer (test plan, eval design, fail-closed methods)
- **Related:** ADR 0002 (release slicing), ADR 0003 (rallies-lost unit, OQ-08), ADR 0005 (Wilson, minimum n), ADR 0006 (deletion and retention windows), ADR 0007 (sequencing), ADR 0010 (capacity), ADR 0023 (PO decisions), ADR 0030 (PR size), ADR 0039 (ticket PRs), ADR 0044 (`coach-reviewed` vs `verified`), ADR 0046 (red-first E2E), ADR 0047 (gate phase), ADR 0050 (merge discipline); `docs/sprints/sprint-04.md`; `docs/sprints/04/goal-scorecard.md`; `docs/sprints/roadmap.md` §2, §5, §6, §7, §12

## Context and problem statement

The product owner's goal for this session (2026-10-17, relayed by the orchestrator): "resume Sprint 4 and try to complete the MVP so it can run as a prototype". The PO's Sprint 4 brief names three groups in a fixed order: (0) CI first; (1) the Sprint 3 carry-over; (2) the prototype spine, so that the R1 journey upload → Quick Tag → score sheet → stats → plan (QD §7) runs on `make up` + `make demo`; (3) R1 privacy and quotas behind flags, because OQ-05, OQ-06, OQ-07 and OQ-13 are still open. It also takes three items out of scope: SPIKE-02, SPIKE-03 and SPIKE-05 need consented footage or GPU budget that the PO has not supplied (RM-06, OQ-06, OQ-13).

The roadmap outline for S4 (roadmap §6) mixes these groups with no order, lists the three spikes, and still shows the R2 sprints as S6-S9 although the Go-port decision (PO, 2026-10-06) moved them to S7-S10. Sprint 3's retro asks for slicing at planning (B4) and the gate phase (ADR 0047 rule 2).

Facts at planning:

- `main` CI is green at `c170ef0`: run 39015002522 (`schedule`, `ci.yml`) → success; the last push run 38894723692 at `d8b0a34` → success (`actions_list list_workflow_runs branch=main`). No CI-fix ticket is needed first.
- The Sprint 3 goal ledger has 2 open blocker/major rows: `python3 scripts/measure/open_defects.py docs/sprints/03/review-rounds.md` → rc 1, `open 2`: PD-R1S3-01 with QA-R3S3-06 (blocker group, waits on the chair's DR-03 "Held" record) and EM-PR27-01 (major, a senior verdict on PR #27's merged head). PE-PR24-01, named in the PO brief, is already Fixed (FIX-03-2b; scorecard §12.3).
- What exists for the plan: the `racket.coaching.drills` module (schema v1, lint, lock; ST-053) with three fixture drills; the analytics context's per-match stats and evidence; `make demo` seeding 12 rallies (MVP-03). Nothing exists for weakness ranking, plans, age confirmation, retention choice, training consent, quotas or billing alerts.

## Decision drivers

- A prototype the PO can run is worth more now than a complete R1 privacy surface that no real user can see yet (no real users before NFR-070; roadmap §4).
- PO rules: CI first; one PR per ticket; TDD and DDD; tests of three levels in every PR; two verdicts; goals measured live; human-only items reported as "not met: waiting on P-n" (P12).
- Open PO decisions must not block code, and must not be guessed silently either (ADR 0023, ADR 0047 rule 5).
- Slices of ≤ 400 changed lines from unbuilt work (retro 3 B4).

## Considered options

1. **Order by dependency and value: gates, then carry-over and the prototype spine in parallel, then privacy behind flags** (chosen).
2. **Roadmap outline as written, all S4 items in parallel.** Rejected: the privacy items would compete with the spine for the BE and FE lanes, and the PO asked for the prototype first.
3. **Wait for OQ-05/06/07/13 before building any privacy item.** Rejected: it leaves R1 with no privacy code at S5, and the PO asked for flags with interim wording.
4. **Keep the spikes in S4 on synthetic data.** Rejected: SPIKE-02 and SPIKE-05 measure real-footage behaviour, and SPIKE-03 needs GPU spend; synthetic results would not answer their questions (roadmap §7.1).

## Decision outcome

Chosen: option 1.

1. **Order.** CI first (no red `main`; a red `main` pre-empts every ticket). Then the ADR 0047 gate tickets (PE-4 contract and design, PD-4 flows, SEC-4 threat notes, COACH-4 weakness catalogue and drill protocol, PM-4 ADR 0005) run first and in parallel with the carry-over tickets C4-*. The prototype spine (ST-055..ST-067, QA-HARNESS-4) starts as soon as its gates are merged. The privacy and quota tickets (ST-068..ST-073) depend on the spine's API ticket (BE) or its last UI ticket (FE), so they can only take a lane after the spine.
2. **Weakness unit is provisional behind config.** FR-120 ranks by rallies lost per game, split serve/receive (ADR 0003). Because OQ-08 is open, the unit is a setting (`COACHING_WEAKNESS_UNIT`, only value `rallies_lost_per_game`), and the API and UI label it "provisional". The side-out part stays `@needs-verification` (FR-120, ADR 0009).
3. **Drills.** The pickleball-domain-coach agent authors the starter library (≥ 20 drills, drill schema v1, unchanged) and moves each drill to `coach-reviewed` after its review checklist (COACH-4), as ADR 0044 did for metrics. `verified` needs a human coach (new PO item P15). Until then the feature file is `@needs-verification` and the plan page says the drills are not yet checked by a human coach (interim wording, PD-4). Plans use only `coach-reviewed` or `verified` drills (FR-121).
4. **Privacy and quotas behind flags, default off.** `FEATURE_AGE_GATE` (FR-003), `FEATURE_RETENTION_SETTING` (FR-008), `FEATURE_TRAINING_CONSENT` (FR-009) and `FEATURE_QUOTAS` (FR-160, NFR-023) are settings in `racket.platform.settings`, off in `infra/env.example`, so `make up` + `make demo` and the existing E2E suites behave as today. Each has interim wording owned by the product-manager and marked "interim, pending PO decision OQ-nn" in the flows file. Interim values: age 18 (FR-003), retention choices 30/90/365 days/until I delete with default 90 (FR-008, ADR 0006), consent off by default (FR-009), 10 match creations per hour and a storage quota of 20 GB per user (FR-160; the 20 GB is (judgment) until OQ-13, P8). The verifier measures each flag on and off (G04-09, G04-10). The existing sign-in and upload rate limits are unchanged.
5. **Billing alerts are configuration only** (NFR-022): alert rules at 50/80/100% of a monthly budget for the LLM provider and the object store, with the budget a setting and no paid provider attached. A rule test proves they fire at the thresholds.
6. **Out of scope, blocked on the PO:** SPIKE-02 and SPIKE-05 (consented footage, OQ-06, P11), SPIKE-03 (GPU budget, OQ-13, P8). They are not ticketed. Human-only items (coach sign-off, PO decisions, screen-reader pass, repository visibility, storage provider) are never ticketed; they are sprint-DoD rows "not met: waiting on P-n".
7. **Roadmap renumbered.** S6 is the Go port (PO 2026-10-06). The R2 outlines move from S6-S9 to S7-S10, the R3 outline from S10-S12 to S11-S13, and the spikes with them. The calendar in roadmap §2 is rewritten to match.

## Consequences

- Good: the PO can run the whole R1 journey locally at the end of the spine, before the privacy tickets start, and every later ticket keeps it green (E2E-04-01 in CI).
- Good: no PO decision is guessed silently. Every interim value is a setting with a named OQ, so a PO answer is a config change plus a TCR row where a test pins the value.
- Bad: privacy code that is off by default can rot. Mitigation: each flag has an integration test in CI with the flag on, and G04-09/G04-10 measure it live.
- Bad: drills checked only by an agent coach may be wrong. Mitigation: `@needs-verification`, the interim notice, safety notes (QD-DR-04), and P15.
- Bad: R2 entry evidence (roadmap §7.1) still has no spike data. RM-06, RM-07 and RM-08 stay open; R2 planning at S7 will have to re-plan if P11 and P8 are still unanswered.

## Confirmation

At the Sprint 4 close:

- `main` CI green at the close head, every job incl. `ci-gate` (G04-12).
- `make up` + `make demo` on a fresh stack show the demo user's plan (G04-06), and the live journey passes 5 of 5 runs (G04-01).
- Each flag has a passing on/off measurement (G04-09, G04-10).
- No ticket for SPIKE-02/03/05 exists; the sprint report lists them as blocked on P8/P11.

## Evidence

- `main` CI at planning: run 39015002522 at `c170ef0` → `conclusion: success`; run 38894723692 at `d8b0a34` (push) → success.
- Open ledger rows at planning: `python3 scripts/measure/open_defects.py docs/sprints/03/review-rounds.md` → rc 1, `open 2`: `PD-R1S3-01`/`QA-R3S3-06` (line 524) and `EM-PR27-01` (line 525).
- Existing coaching code: `ls backend/src/racket/coaching/drills` → `lint.py lock.py rules.py schema.json schema_check.py`; `ls content/drills` → three `pb.fixture.*` drills and `library.lock`.
