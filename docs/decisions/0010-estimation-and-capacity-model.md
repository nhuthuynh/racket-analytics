# 0010. Estimation and capacity model for the agent team: t-shirt sizes, units, parallel streams and a load factor

- **Status:** Accepted. Every number below is (judgment) and is recalibrated with measured data at retro 0 and retro 1 through a dated note or a superseding ADR.
- **Date:** 2026-10-03
- **Deciders:** engineering-manager (R/A for sprint process)
- **Consulted:** principal-engineer (stream boundaries), senior-qa-engineer (review load)
- **Related:** `docs/sprints/roadmap.md` §3; sprint files; working-agreement §3, §7; ADR 0001; ADR 0007

## Context and problem statement

The working agreement says stories are sized relatively with t-shirt sizes [EP/ENG-15], but no rule turns sizes into a sprint commitment for a team of AI agents. Agents can run several invocations in parallel, but every PR passes a review loop with fresh-context reviewers and up to 3 fix iterations (working-agreement §7). The human product owner's time is limited. Without a capacity model, sprint commitments are guesses and estimation accuracy cannot be measured, which [EP/ENG-15] asks us to collect.

## Decision drivers

- Relative sizing; collect estimation-accuracy data; judge success against the sprint goal, not points alone [EP/ENG-15].
- Small PRs of about 100 lines [EP/ENG-04].
- One feature at a time per agent session [EP/ENG-28].
- Multi-agent work costs about 15x the tokens of chat; fan out only where the value justifies it [DPA/AI-02, EP/ENG-26].
- Delegated briefs must not overlap [EP/ENG-26].

## Considered options

1. Story points with Planning Poker and velocity.
2. **T-shirt sizes mapped to "units", per-lane parallel streams, and a load factor.**
3. No estimates: count stories only.
4. Hour estimates.

## Decision outcome

Chosen option: **Option 2.**

| Size | Units | Typical shape (judgment) |
|---|---|---|
| XS | 0.5 | one PR, ≤ 100 changed lines |
| S | 1 | about 2 PRs of ~100 lines each, through the full review loop |
| M | 2 | about 4 PRs |
| L | 4 | about 8 PRs; must be splittable into independently mergeable PRs |
| XL | — | not allowed; split before planning (DoR "small enough to land in PRs of about 100 lines" [EP/ENG-04]) |

- A unit includes writing tests, the fresh-context review, up to 3 fix iterations and evidence (working-agreement §7).
- **Implementation lanes:** senior-backend-engineer (BE), senior-frontend-engineer (FE), senior-ml-cv-engineer (ML), senior-qa-engineer (QA), sre-devops-engineer (SRE).
- **Streams:** each lane may run at most **2 parallel streams**, and only when they work in disjoint modules or bounded contexts. Each stream works on one story at a time [EP/ENG-28].
- **Nominal capacity:** 8 units per stream per sprint, so 16 per lane.
- **Load factor:** 70% in Sprint 0 (no data, tooling still being built), 80% in Sprint 1. From Sprint 2 it is the lower of 85% and the median completed-units ratio of the last two sprints.
- **Docs-only roles** (PM, BA, principal-engineer, principal-designer, security-privacy-engineer, pickleball-domain-coach, EM) carry named tasks with due days, not units. Their review effort is already inside each story's units.
- **Stretch items** are marked "stretch". They are pulled only when every committed story is done, and they do not count toward the commitment.
- **Human product owner time (assumption, to be confirmed at Sprint 0 planning):** about 2 hours at each sprint review, plus answers to escalations within 3 business days. Work that needs an answer continues only where it does not depend on it (working-agreement §8).
- **Measurement:** `docs/sprints/<nn>/status.json` records planned and completed units per story. The retro reports estimate accuracy (retro template §2).

## Pros and cons of the options

### Option 1: story points
- Good: familiar.
- Bad: points have no anchor for a new agent team; Planning Poker needs independent estimators, and agents sharing one model may not be independent (judgment).

### Option 2: sizes, units, streams, load factor
- Good: relative sizing as [EP/ENG-15] asks, with an explicit link to PR size [EP/ENG-04] and to parallelism.
- Good: easy to recalibrate from `status.json`.
- Bad: "units" are invented; the first two sprints' numbers are guesses.

### Option 3: no estimates
- Good: zero overhead.
- Bad: gives no estimation-accuracy data to improve on [EP/ENG-15].

### Option 4: hours
- Bad: agent wall-clock time is a poor proxy for review load and human time (judgment).

## Consequences

- **Good:** each sprint file states planned units per lane against capacity.
- **Trade-offs accepted:** possible over- or under-commitment in Sprints 0-1; the low load factors cushion it.
- **Follow-up work:** retro 0 compares planned and completed units and sets the Sprint 2 load factor.

## Evidence

| Claim | Evidence | Type |
|---|---|---|
| Relative sizing (t-shirt, Planning Poker); collect estimation accuracy; judge by sprint goal | [EP/ENG-15] | verified source |
| ~100-line changes; ~1000 too large | [EP/ENG-04] | verified source |
| One feature at a time; progress file and JSON status | [EP/ENG-28] | verified source |
| Multi-agent ≈ 15x tokens; fan out only where valuable | [DPA/AI-02], [EP/ENG-26] | verified source |
| Delegation briefs must not overlap | [EP/ENG-26] | verified source |
| Unit sizes, 8 units per stream, 2 streams, load factors, PO time | (judgment) | judgment |

## Confirmation

- `status.json` of Sprints 0 and 1 holds planned and completed units for every story.
- Retro 0 and retro 1 record estimate accuracy and the load factor used next.

## Notes

- **2026-10-03 (engineering-manager, retro 0):** Sprint 0 measurement from `docs/sprints/00/status.json`: 28 units planned. 19 units (68%) were implemented and verified locally; 9 units are partial (ST-002, ST-010, SPIKE-01); 0 units meet the full story DoD, because no CI run has happened and the test-change approvals are pending. Every unit of the shortfall is "external evidence" work (a GitHub CI run, WebKit, peer, human or design reviews), not build effort. **Recalibration:** the Sprint 1 load factor stays at 80% as planned. From Sprint 1, every story card lists its external-evidence items with their owner and due date, and `status.json` records `implemented_units` and `dod_done_units` separately. For the Sprint 2 rule ("lower of 85% and the median completed ratio"), the completed ratio is the **dod_done** ratio (judgment).
- **2026-10-05 (product-manager, recording the human product owner):** The PO accepted the PO-time assumption in §Decision outcome (about 2 hours at each sprint review, escalation answers within 3 business days) as part of "accept all recommendations" (ADR 0023). It is no longer an assumption to be confirmed.
