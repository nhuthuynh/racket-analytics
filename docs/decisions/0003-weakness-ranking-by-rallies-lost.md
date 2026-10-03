# 0003. Rank weaknesses by rallies lost per game (split serve/receive), not points lost per match

- **Status:** Proposed. It depends on an unverified rule and needs confirmation from the human product owner (OQ-08) and verification by the domain coach.
- **Date:** 2026-10-03
- **Deciders:** business-analyst (proposer); pickleball-domain-coach (verifies); human product owner (approver)
- **Consulted:** senior-qa-engineer and pickleball-domain-coach (QD X1); product-manager (PROD US-601)
- **Related:** FR-109, FR-120, FR-121; spec §6 step 1; conflict K3

## Context and problem statement

Spec §6 ranks weaknesses by "points lost per match attributable to each one". Under side-out scoring, only the serving side scores [DOM G1 R2, UNVERIFIED]. A rally lost while *serving* gives the opponent no point; it costs a serve. A rally lost while *receiving* gives the opponent a point. "Points lost" would therefore undercount serving-side errors, such as third-shot errors, which coaches care about (QD X1, judgment).

## Decision drivers

- The ranking must reflect every lost rally that the weakness caused (spec §6 intent).
- It must be testable with an invariant (QD-AN-00).
- It must work under both side-out and rally scoring (FR-040, FR-043).

## Considered options

1. **Points lost per match** (spec as written).
2. **Rallies lost per game, split into lost on serve and lost on receive**, with points conceded shown separately (QD X1).
3. **A weighted "expected points" model** that values a lost serve by the probability it would have scored (judgment).

## Decision outcome

Chosen option: **Option 2.**

- It counts every lost rally once, and the attribution-conservation invariant (FR-109) makes that testable.
- It coincides with Option 1 under rally scoring.
- It needs no probabilistic model, so it is explainable in the "why" text [DPA/DESIGN-11 G11].

## Pros and cons of the options

### Option 1: points lost per match
- Good: matches the spec wording, and is simple.
- Bad: blind to serving-side losses under side-out scoring, which biases plans towards return-side weaknesses.

### Option 2: rallies lost per game, split
- Good: complete, testable by invariant, explainable, and works for both scoring systems.
- Bad: treats a lost serve and a conceded point as equal in rank (judgment). The serve/receive split mitigates this by showing both.

### Option 3: expected points
- Good: the most "economically" correct.
- Bad: needs a calibrated model and more data than R1 has. It is harder to explain, and it is speculative engineering for the MVP [AQS/ENG-04].

## Consequences

- The FR-120 Gherkin and the coaching evals (QD-GD-05) use this unit.
- The glossary term "Point leak" in `docs/process/ddd-guidelines.md` §6 must be updated to "rallies lost attributable to a weakness". The principal-engineer owns that file.
- If the coach finds that the rule differs from the snippet [DOM G1 R2], this ADR is superseded.

## Evidence

| Claim | Evidence | Type |
|---|---|---|
| Only the serving side scores under side-out scoring | [DOM G1 R2], **UNVERIFIED** (search snippet) | unverified domain fact; blocks acceptance |
| "Points lost" undercounts serving-side errors | QD X1 reasoning | judgment |
| Reviewers push back on speculative over-engineering | [AQS/ENG-04] | verified source |
| Explanations should make clear why | [DPA/DESIGN-11] G11 | verified source |

## Confirmation

- FR-109 invariant unit tests pass on every PR.
- The coach records the side-out rule number and confirms the unit.
- The PO answers OQ-08.

## Notes
