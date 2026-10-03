# 0009. Split rules-engine work: the parameterised engine is Ready now; the USAP-2026 preset waits for verification

- **Status:** Proposed. It interprets the "Domain truth" item of the Definition of Ready, so the human product owner ratifies it at the Sprint 0 review (2026-10-16), before Sprint 1 planning. Escalated under working-agreement §8 ("a domain rule cannot be verified").
- **Date:** 2026-10-03
- **Deciders:** engineering-manager (proposer, owns the DoR process); senior-qa-engineer and pickleball-domain-coach (consulted owners of the tests and the rules); human product owner (approver)
- **Consulted:** principal-engineer, business-analyst, senior-backend-engineer
- **Related:** FR-040..FR-049, FR-053, FR-055; NFR-001, NFR-002, NFR-003, NFR-072, NFR-079; OQ-01; ADR 0007; stories ST-020, ST-021, ST-023 (Sprint 1); ST-029, ST-032, ST-034, ST-035 (Sprint 2)

## Context and problem statement

The Definition of Ready says a story whose acceptance criteria rest on a pickleball rule is **not Ready** until the domain coach records the rulebook edition and rule number [DOM G1]. No rule has been verified: the rulebook sites were egress-blocked, and OQ-01 asks the human product owner to supply the 2026 rulebook. Eleven R1 Must FRs are `needs-verification`.

Read literally, the DoR blocks the whole rules engine, and with it the Quick Tag → score sheet slice (Sprint 2) and every later R1 sprint. But FR-040 already requires every unverifiable rule to be a `RulesConfig` field, not a constant. The testing strategy already expects rules scenarios to be tagged `@needs-verification` until the coach records rule numbers [testing-strategy §3]. And FR-055 already labels score sheets "unofficial scoring" while any rule is unverified. We must decide what can be committed in Sprint 1.

## Decision drivers

- Do not ship an unverified rule as fact; make clear how well the system can do what it does [DPA/DESIGN-11] G2; FR-055.
- Keep the R1 value chain moving while OQ-01 is open (ADR 0002, ADR 0007).
- The rules engine is pure logic and the first TDD target [EP/ENG-18; EP/ENG-17].
- A `@needs-verification` scenario must never count as satisfying a Must FR (QD-QG-P5).
- Changing an accepted test needs QA approval; tests are not edited to make code pass [EP/ENG-28].

## Considered options

1. **Literal DoR:** commit no rules-engine story until OQ-01 is answered.
2. **Split each rules story in two:**
   - **(a) Engine mechanics**, Ready now. Acceptance criteria are stated against an explicit `RulesConfig` (for example "given `points_to_win = 11` and `win_by = 2`"), not as rulebook claims. They cover the state machine, fold/replay, typed domain errors, purity, determinism and the property invariants that hold for *any* config.
   - **(b) Preset values** (`USAP-2026`: target score, win-by, first-service exception, call format, singles court parity, fault outcomes). Not Ready until the coach records rule numbers. Until then a preset named `PROVISIONAL-UNVERIFIED` carries the values from QD §2.2, every score sheet shows "unofficial scoring", and the SOD/F/SOS/M/C tables run tagged `@needs-verification`.
3. **Proceed as if verified:** treat QD §2.2 as the rules and fix later.

## Decision outcome

Chosen option: **Option 2.**

- It respects the intent of the DoR: no unverified rule is ever presented as official (FR-055, QD-QG-R3).
- It unblocks the R1 value chain. When OQ-01 is answered, only config values and test-table rows change (FR-040), plus the `@rule-<n>` tags (QD-TR-07).
- Changing a provisional table row after verification is a *requirement change*. It is made by the senior-qa-engineer with an ADR note, not by the implementer [EP/ENG-28].

Rules for applying it:

1. A rules story's (a) part is Ready when its acceptance criteria name the config values they assume and contain no rulebook claim.
2. The (b) part stays in the backlog as `needs-verification` and is pulled into the sprint in which the coach records the rule numbers.
3. Test reports list `@needs-verification` scenarios separately and never count them toward a Must FR's DoD (QD-QG-P5).
4. No preset may be named after a federation (e.g. `USAP-2026`) until every row it relies on is verified (NFR-003).

## Pros and cons of the options

### Option 1: literal DoR
- Good: zero chance of encoding a wrong rule.
- Bad: blocks Sprints 1-5 on an external dependency with no date; the team idles or builds out of order.

### Option 2: split
- Good: progress without false claims; the change after verification is configuration plus test data.
- Bad: two steps of work for each rules story; a risk that provisional values get treated as truth. This is mitigated by the label (FR-055), the preset name, and QD-QG-P5.

### Option 3: proceed as verified
- Bad: contradicts [DOM G1] and the DoR; wrong score sheets are the RISK-05 failure mode (ENG §7).

## Consequences

- **Good:** ST-020, ST-021 and ST-023 (Sprint 1) and ST-029, ST-032, ST-034 and ST-035 (Sprint 2) can be committed.
- **Bad / trade-offs accepted:** R1 cannot be called "official scoring" until OQ-01 is answered and NFR-003 passes on QD-GD-02.
- **Follow-up work:**
  - The pickleball-domain-coach opens `docs/domain/rules-verified.md` and fills it as soon as the PO supplies the rulebook.
  - The business-analyst writes each rules story with separate (a) and (b) parts.
  - The senior-qa-engineer adds the `@needs-verification` count to every sprint test report.

## Evidence

| Claim | Evidence | Type |
|---|---|---|
| No pickleball rule is verified; rulebook egress-blocked | [DOM G1], [DOM Gaps 1]; OQ-01 | verified research status |
| Unverifiable rules must be `RulesConfig` fields; engine is a pure function | FR-040; ddd-guidelines §4.5; [EP/ENG-17] | requirement + verified source |
| Rules scenarios stay `@needs-verification` until rule numbers are recorded | testing-strategy §3; QD-TR-07 | accepted process doc |
| `@needs-verification` scenarios do not satisfy a Must FR | QD-QG-P5 | team input |
| Make clear how well the system can do what it does | [DPA/DESIGN-11] G2 | verified source |
| Tests are immutable for implementers | [EP/ENG-28] | verified source |
| Red-green-refactor; negative cases first | [EP/ENG-18] | verified source |
| Split is the better trade-off | (judgment) | judgment |

## Confirmation

- The Sprint 1 test report lists the 19 provisional rows (SOD-01..SOD-12, SOD-16, F-01..F-06) as `@needs-verification`, separately from the Ready engine-mechanics scenarios, which include M-01..M-08. The Sprint 2 report adds SOD-13..SOD-15, the SOS rows and C-01..C-04, reaching the ≥ 46 rows of NFR-001. (Count corrected in principal-engineer review, 2026-10-03, review-log RL-04: the earlier "≥ 30" could not be reached because SOD-13..15 move to Sprint 2.)
- Every score sheet in the Sprint 2 demo shows "unofficial scoring (rules not yet verified)".
- When the coach records rule numbers, a dated note here lists the rows that changed, if any.

## Notes
