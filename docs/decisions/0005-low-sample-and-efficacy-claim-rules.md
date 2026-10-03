# 0005. Low-sample flagging and plan-efficacy claims use Wilson intervals with minimum n

- **Status:** Proposed. Requirement-level thresholds are (judgment) and are to be reviewed with the domain coach at the first analytics retro.
- **Date:** 2026-10-03
- **Deciders:** business-analyst (proposer); pickleball-domain-coach (metric owner)
- **Consulted:** product-manager (PROD US-501, US-1102), principal-designer (DES FR-UX-71, FR-UX-74, FR-UX-83), senior-qa-engineer and pickleball-domain-coach (QD X5, X6)
- **Related:** FR-101, FR-104, FR-123, FR-127; NFR-038; conflicts K6, K7

## Context and problem statement

The spec requires every metric to carry a sample size, and to be flagged rather than hidden when the sample is small (spec §5). It also requires plans to be scored after the next match (spec §6 step 4). The brainstorms proposed different rules:

- **PROD and DES:** flag at n < 10 rallies.
- **QD:** a 95% Wilson interval, flagging when n < 20 or the interval is wider than 30 percentage points; and claim plan efficacy only when both windows have n ≥ 20 and their intervals do not overlap.

## Decision drivers

- Don't over-claim. Make clear how well the system can do what it does, and scope services when in doubt [DPA/DESIGN-11] G2, G10.
- Must be unit-testable and configurable.
- Telling a player that a plan "worked" from noise erodes trust (QD X6, judgment).

## Considered options

1. **A flat n < 10** (PROD/DES).
2. **Wilson interval plus minimum n**, as QD proposes. Count metrics are flagged when fewer than 2 games are in scope.
3. **No flag; show raw values only.**

## Decision outcome

Chosen option: **Option 2.**

- It accounts for effect size, not just n. For example, 7/8 and 4/8 carry very different uncertainty.
- It gives one consistent rule for flags, trends and efficacy.
- All thresholds live in config, so changing them is a config change plus a superseding ADR, not a code change.

## Pros and cons of the options

### Option 1: flat n < 10
- Good: simple to explain.
- Bad: at n = 10 a proportion's 95% interval is still very wide (judgment, basic statistics). Users would see confident-looking numbers that are not.

### Option 2: Wilson interval plus minimum n
- Good: statistically grounded, one rule everywhere, and testable at the boundaries (n = min − 1, QD-TR-08).
- Bad: more "low sample" labels in R1, where single matches are small. This is mitigated because flagged metrics are still shown (spec §5).

### Option 3: no flag
- Bad: violates spec §5.

## Consequences

- FR-101 and FR-127 carry these rules.
- Metric-dictionary entries hold each metric's `min_sample` (FR-102).
- The UI shows "not enough data yet (n = x of 20)".

## Evidence

| Claim | Evidence | Type |
|---|---|---|
| Show sample size and flag small samples without hiding them | spec §5 | spec |
| Make clear how well the system does; scope services when in doubt | [DPA/DESIGN-11] G2, G10 | verified source |
| Wilson interval, n ≥ 20, 30 pp width, non-overlap rule | QD X5, X6 | judgment |

## Confirmation

- FR-101 Scenario Outline rows (n = 8 flagged, n = 40 not flagged) pass.
- The FR-127 scenario passes.
- The coach reviews the thresholds at the first analytics retro.

## Notes
