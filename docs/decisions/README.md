# Decision Log (Architecture Decision Records)

Every significant decision made by the agent team or the human product owner is recorded here as an ADR,
together with the **evidence** behind it and the **alternatives** considered.

## Why

- An ADR records **one** decision, its rationale, the options with their pros and cons, and timestamps [EP/ENG-09].
- This project uses the MADR structure (Markdown Architectural Decision Records). MADR files live in
  `docs/decisions/` and are named `nnnn-title-with-dashes.md` [EP/ENG-10].
- Design docs and decision logs live in the repo and are reviewed as PRs [DPA/DESIGN-15].

The citation prefixes (EP, AQS, DPA, DOM) are explained in `docs/process/working-agreement.md` §0.

## What counts as "significant" (judgment)

Write an ADR for any of the following:

- **Technology and architecture:** a choice of technology, library, model, dataset or licence; a change to
  architecture, a context boundary, an API contract or the data schema; or an NFR target such as an SLO,
  a coverage threshold or an eval tolerance.
- **Domain:** an interpretation of a pickleball rule or of coaching content.
- **Process:** a change to the working agreement, DoD or DoR.
- **Risk and cost:** accepting a risk (security, privacy, quality) or a cost commitment.
- **Changing course:** reversing or superseding an earlier decision.
- **Escalations:** anything escalated to the human product owner, together with their answer.

## Rules

1. Number ADRs sequentially with four digits and never reuse a number: `0001-...`, `0002-...` [EP/ENG-10].
2. **Evidence is mandatory.** Every claim cites one of the following:
   - a verified research source, e.g. `[AQS/SEC-09]`;
   - data, such as eval metrics or benchmarks with their dataset version;
   - test results, given as the command and its output, or a CI link.

   Anything else is labelled **(judgment)**. Never invent URLs.
3. **Alternatives are mandatory.** List at least two considered options, including "do nothing" where it
   applies, each with pros and cons.
4. **Do not rewrite history.** Once an ADR is Accepted, only dated notes may be appended. A changed
   decision gets a new ADR, and the old one becomes `Superseded by NNNN` [EP/ENG-09].
5. The **deciders** are named by role (agent name, or "human product owner").
6. An ADR from a read-only agent (security-privacy-engineer) is returned as a draft and saved by the
   engineering-manager.
7. Statuses: `Proposed`, `Accepted`, `Rejected`, `Deprecated`, `Superseded by NNNN`.

## Template

Copy this into `docs/decisions/NNNN-short-title.md`:

```markdown
# NNNN. <Short title of the decision>

- **Status:** Proposed | Accepted | Rejected | Deprecated | Superseded by NNNN
- **Date:** YYYY-MM-DD
- **Deciders:** <agent roles / human product owner>
- **Consulted:** <agent roles>
- **Related:** <story IDs, FR/NFR IDs, other ADRs>

## Context and problem statement
<What is the situation and what question must be answered? 2-5 sentences.>

## Decision drivers
- <driver, e.g. "NFR-SEC-01 BOLA on every resource ID">
- <driver, e.g. "GPU cost <= 2 GPU-min per match-min (spec §8)">

## Considered options
1. <Option A>
2. <Option B>
3. <Option C / do nothing>

## Decision outcome
Chosen option: "<Option X>", because <justification tied to drivers>.

## Pros and cons of the options
### Option A
- Good, because ...
- Bad, because ...
### Option B
- ...

## Consequences
- Good: ...
- Bad / trade-offs accepted: ...
- Follow-up work: ...

## Evidence
| Claim | Evidence | Type |
|---|---|---|
| <claim> | [AQS/SEC-09] | verified source |
| <claim> | `pytest tests/integration/test_bola.py` -> 42 passed (CI run link) | test result |
| <claim> | HOTA 61.2 on gold-set v3 (docs/evals/2026-11-01.md) | data |
| <claim> | (judgment) | judgment |

## Confirmation
<How will we know the decision is implemented and working? e.g. test, eval gate, metric, review.>

## Notes
<Dated notes appended after acceptance; never edit the sections above once Accepted.>
```

## Index

| # | Title | Status | Date |
|---|---|---|---|
| 0001 | [Adopt ADRs and an AI agent team with a defined working agreement](0001-adopt-adrs-and-agent-team.md) | Accepted | 2026-10-03 |
| 0002 | [MVP scope: walking skeleton and release slicing](0002-mvp-scope-walking-skeleton-release-slicing.md) | Proposed | 2026-10-03 |
| 0003 | [Weakness ranking by rallies lost](0003-weakness-ranking-by-rallies-lost.md) | Proposed | 2026-10-03 |
| 0004 | [Measurable definitions for the M2 and M3 accuracy targets](0004-accuracy-target-definitions-m2-m3.md) | Proposed | 2026-10-03 |
| 0005 | [Low-sample and efficacy-claim rules](0005-low-sample-and-efficacy-claim-rules.md) | Proposed | 2026-10-03 |
| 0006 | [Retention and deletion defaults](0006-retention-and-deletion-defaults.md) | Proposed | 2026-10-03 |
| 0007 | [Delivery sequencing in vertical slices](0007-delivery-sequencing-vertical-slices.md) | Proposed | 2026-10-03 |
| 0008 | [Stack confirmation for Sprint 0](0008-stack-confirmation-for-sprint-0.md) | Accepted (Sprint 0) | 2026-10-03 |
| 0009 | [Rules-engine readiness split](0009-rules-engine-readiness-split.md) | Proposed | 2026-10-03 |
| 0010 | [Estimation and capacity model](0010-estimation-and-capacity-model.md) | Accepted | 2026-10-03 |
| 0011 | [tus server: tus 1.0.0 core inside FastAPI, not a tusd sidecar](0011-tus-server-fastapi-core.md) | Accepted (Sprint 0) | 2026-10-03 |
| 0012 | [Red-first tests reach production code through one QA-owned seam contract](0012-red-first-test-seam-contract.md) | Proposed | 2026-10-03 |
| 0013 | [Agent hooks: deterministic gates that never wedge a session](0013-agent-hooks-design.md) | Proposed | 2026-10-03 |
| 0014 | [CI merge gates: fail closed, one required check, pinned actions, SBOM-based licence gate](0014-ci-merge-gates-fail-closed.md) | Proposed | 2026-10-03 |
| 0015 | [CV licence posture: MIT/Apache code by default, pretrained weights judged by their training data, no AGPL](0015-cv-licence-posture.md) | Proposed (PO decides OQ-12) | 2026-10-03 |

Adversarial review findings and their fixes are logged in [review-log.md](review-log.md).
