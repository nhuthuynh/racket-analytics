# 0004. Measurable definitions for the M2 rally-segmentation and M3 auto-scoring targets

- **Status:** Accepted by the human product owner on 2026-10-05 (OQ-09, ADR 0023).
- **Date:** 2026-10-03
- **Deciders:** business-analyst (proposer); senior-ml-cv-engineer and senior-qa-engineer (measurement owners); human product owner (approver)
- **Consulted:** product-manager (PROD C8, C9), principal-engineer and senior-ml-cv-engineer (ENG §5.4 CV-T09, CV-T11), senior-qa-engineer (QD X9)
- **Related:** NFR-006, NFR-007, NFR-008; FR-057, FR-058, FR-087; conflicts K4, K5

## Context and problem statement

The spec states two accuracy targets that cannot be tested as written:

- **M2:** "≥ 90% of rallies segmented correctly". "Correctly" is undefined.
- **M3:** "≤ 1 correction per game on average".
  - The denominator is ambiguous: score corrections only, or also shot and identity corrections (PROD C8)?
  - A doubles game has about 25-40 rallies (ENG, judgment; the coach is to confirm). One correction per game then implies about 96-97% accuracy on every score-affecting field. That conflicts with the spec's own premise that one phone cannot make referee-grade calls (spec §2).

## Decision drivers

- Gold-set evaluation must be reproducible [EP/ENG-27; DOM G8].
- The human-in-the-loop posture: show confidence and let users correct (spec §2; [DPA/DESIGN-11] G2, G9).
- Every NFR must be measurable [DPA/DESIGN-16; BA DoD].

## Considered options

1. **Keep the spec wording.**
2. **PROD's definitions:**
   - M2: a rally is correct if its start and end are each within ±1.0 s and it is not merged or split; report P/R.
   - M3: count score-affecting corrections only, ≤ 1/game.
3. **ENG's split metric with QD's measurement:**
   - M2: rally-segmentation F1 ≥ 90%, using PROD's matching rule.
   - M3: (a) ≤ 2.0 score-affecting corrections per game at first release, ≤ 1.0 later; (b) ≤ 5 one-tap confirmations per game; (c) unflagged rallies ≥ 95% correct, with the pooled 95% CI lower bound ≥ 93%.
   - A score-affecting field is rally winner side, rally status (counted/replayed) or fault-by side. Corrections are counted by a scripted "oracle user" against the frozen gold set (QD X9).

## Decision outcome

Chosen option: **Option 3.**

- It is the only option that is both measurable and consistent with the confidence-plus-correction posture.
- For M2, F1 already contains P and R.
- For M3, separating *corrections* (the system was wrong) from *confirmations* (the system flagged doubt) rewards calibrated confidence. That is what HAX G2 asks for.
- The spec's ≤ 1.0 survives as the later target.

## Pros and cons of the options

### Option 1: keep the spec wording
- Bad: not testable; QA cannot write the gate.

### Option 2: PROD's definitions
- Good: M2 becomes testable.
- Bad: the M3 target is likely unreachable on a single phone (judgment). It also treats all doubt as failure.

### Option 3: ENG + QD
- Good: testable, honest about uncertainty, and gives a path to ≤ 1.0.
- Bad: three numbers instead of one. Confirmations still cost the user effort, so it is bounded by NFR-040 (≤ 5 min review per match).

## Consequences

- NFR-006 (R2 gate: rally F1 ≥ 90%) and NFR-007 (R3 gate) carry these definitions.
- NFR-008 (band calibration) becomes a prerequisite for (c).
- The regression tolerances still need their own ADR from the senior-ml-cv-engineer before R2 [testing-strategy §6].

## Evidence

| Claim | Evidence | Type |
|---|---|---|
| Evaluate on frozen gold sets; regression vs capability evals | [EP/ENG-27], [DOM G8 E1-E4] | verified source |
| Make clear how well the system can do what it does; support efficient correction | [DPA/DESIGN-11] G2, G9 | verified source |
| One camera cannot referee line calls | spec §2 | spec |
| ~25-40 rallies per game → ~96-97% accuracy needed | ENG §5.4 | judgment (coach to confirm rally counts) |
| ±1.0 s matching window, 95%/93% thresholds, ≤ 5 confirmations | PROD C9, ENG §5.4, QD X9 | judgment |
| No test results yet | — | Not applicable (no models yet) |

## Confirmation

- The model-quality layer reports rally F1 and the oracle-user metrics every sprint from R2.
- The PO answers OQ-09.

## Notes
- **2026-10-05 (product-manager, recording the human product owner):** PO accepted OQ-09. The M2/M3 "Done when" definitions in this ADR replace the spec wording; ≤ 1.0 correction per game stays a later target. Previous status line: "Proposed. It changes the spec's "Done when" criteria and needs approval from the human product owner (OQ-09).". See ADR 0023.
