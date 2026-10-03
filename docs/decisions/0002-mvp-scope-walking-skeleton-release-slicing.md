# 0002. MVP scope: a walking-skeleton R1 on manual tagging, then automation by release

- **Status:** Proposed. Needs approval from the human product owner, because it changes the scope of spec milestones M0 and M5 (OQ-02).
- **Date:** 2026-10-03
- **Deciders:** business-analyst (proposer); human product owner (approver)
- **Consulted:** product-manager, principal-engineer, senior-ml-cv-engineer, principal-designer, senior-qa-engineer, pickleball-domain-coach (through `docs/requirements/brainstorm-*.md`)
- **Related:** `docs/requirements/functional-requirements.md` §0.3 and conflicts K1, K2, K11; FR-100, FR-121, FR-125; E1-E16

## Context and problem statement

The spec's first milestone is "upload a recorded match → stats → training plan" (spec §2). The milestone table, however, delivers training plans only at M5, after four computer-vision milestones (spec §7). The spec also says M0 includes manual tagging, so that analytics and coaching can be built on real data before the models are ready (spec §7 note).

We need to decide what the MVP contains and how it is cut into releases. Sprint planning cannot start without that.

## Decision drivers

- Prove the whole value chain with real users as early as possible (spec §2 rationale for the first milestone).
- Start with the simplest working path and add complexity only when it is shown to help [DPA/AI-01, EP/ENG-25].
- Small batches and robust testing, since AI adoption correlated with lower delivery stability [EP/ENG-22].
- CV feasibility and cost are unproven:
  - ball tracking has a domain gap [DOM G3 B3];
  - GPU throughput on the spec's numbers is about 2.0-2.4 GPU-min per match-minute against a 1-2 budget (ENG §0.3, derived from [DOM/CV-01] and [DOM/CV-04] FPS figures);
  - auto rally outcome is rated "Low-Medium" (ENG §5.1, judgment).
- Pickleball rules are unverified [DOM G1]. Every release that scores needs a parameterised engine plus an "unofficial" label.

## Considered options

1. **Spec order (M0 → M5 before a plan exists).** The MVP is M0-M5.
2. **Walking skeleton by release (PROD C1):**
   - R1: upload → Quick Tag → score sheet → starter stats → rules-only plan.
   - R2: calibration, tracking, ball/hit/rally detection, LLM "why", efficacy.
   - R3: automatic scoring, shot types, full analytics.
   - Later: M6/M7.
   - The MVP is R1 + R2.
3. **ENG variant:** the coaching workflow *including the LLM* in R1 (sprint 3), and an MVP of "M0 + a thin slice of M1-M3" (ENG §0.1, §9).
4. **Do nothing:** leave the scope ambiguous and let each sprint decide.

## Decision outcome

Chosen option: **Option 2, with ENG's sprint sequencing inside it.**

- The value chain is closed in R1 with no CV dependency.
- Vision then *replaces manual effort* release by release instead of *unlocking value* at M5.
- The LLM waits for R2 because the eval set should exist before the capability [DPA/AI-05], and the rules-only plan is needed as the fallback anyway (PROD C10).
- Shot-level metrics (AN-08..AN-15) move to R3, because users would otherwise see metrics their own matches cannot produce (conflict K11).

## Pros and cons of the options

### Option 1: spec order
- Good: no change to the agreed milestones.
- Bad: no user sees a plan until four CV milestones succeed. Every CV risk (RISK-02, -03, -04 in ENG §7) delays all value.
- Bad: analytics and coaching are built on synthetic data for longer.

### Option 2: walking skeleton by release
- Good: real users can get the full chain in R1, and Quick Tag data becomes labelled data (spec §7 note).
- Good: every brainstorm (PROD, ENG, DES, QD) independently converged on it.
- Bad: R1 needs user effort of ≤ 15 min per match (judgment, NFR-036) that may be too high for some users. The R1 exit usability test measures this.
- Bad: two plan paths, rules-only and LLM, must be maintained. This is mitigated because rules-only is also the fallback.

### Option 3: LLM in R1
- Good: richer "why" text earlier.
- Bad: adds an untrusted-output surface [AQS/SEC-08] and an eval dependency before any real tagged profiles exist to build cases from [DPA/AI-05].

### Option 4: do nothing
- Bad: no stable Definition of Ready for sprint 1. Scope creep.

## Consequences

- **Good:** `functional-requirements.md` tags each FR with R1/R2/R3/Later. The traceability matrix maps them to epics E1-E16.
- **Bad / trade-offs accepted:**
  - Spec M0's "correct score sheet" stays blocked on rule verification. R1 can ship labelled "unofficial scoring" (FR-055, NFR-003).
  - M5's "~80 drills" becomes a coverage matrix with ≥ 20 drills in R1 (FR-141).
- **Follow-up work:**
  - The EM plans sprints against R1.
  - The PM runs the R1 exit criteria: a real user uploads, Quick Tags, and gets a score sheet, starter stats and a rules-only plan with median effort ≤ 15 min (PROD §11).

## Evidence

| Claim | Evidence | Type |
|---|---|---|
| Start with the simplest solution; workflows for well-defined tasks | [DPA/AI-01], [EP/ENG-25] | verified source |
| Build evals before the capability exists; 20-50 cases from real data | [DPA/AI-05] | verified source |
| AI adoption correlated with lower stability; keep batches small | [EP/ENG-22] | verified source |
| TrackNetV3 25.11 FPS; ByteTrack 29.6 FPS on V100 → GPU budget risk | [DOM/CV-01], [DOM/CV-04]; arithmetic in ENG §0.3 | verified source + derived (judgment) |
| Ball-tracking domain gap; no published pickleball metrics | [DOM G3 B3], [DOM/DOMAIN-10] | verified source |
| Rules unverified | [DOM G1], [DOM Gaps 1] | verified research status |
| Manual tagging in M0 is intended to feed analytics and coaching | spec §7 note | spec |
| All four brainstorms propose the same slicing | PROD C1/§11; ENG §0.1/§9; DES §10; QD §2.2, QD-TX-04 | team input |
| Effort targets, release contents | (judgment) | judgment |

## Confirmation

- The PO approves OQ-02.
- At the R1 sprint review, the E2E journey (QD §7) is green on `main` for ≥ 5 nightly runs (QD-QG-S4).
- The R1 usability panel meets NFR-036.

## Notes
