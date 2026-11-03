# 0056. Pre-Sprint 5 doc audit outcome: keep 12 roles (measure cost), review depth tiered by risk, sprints with WIP limits

- **Status:** Accepted (human product owner, 2026-11-03; `docs/requirements/po-input-2026-10-05.md`, addendum "Audit decisions")
- **Date:** 2026-11-03
- **Deciders:** human product owner
- **Consulted:** engineering-manager, principal-engineer, senior-qa-engineer (audit, red team and doc tests of 2026-10-31); orchestrator
- **Related:** ADR 0039 (one PR per ticket), ADR 0054 (PR size), research register `docs/research/agentic-sdlc-best-practices.md`

## Context and problem statement

Before Sprint 5 the PO asked for the role files and process docs to be researched, audited, tested and challenged (addendum "Way of working", 2026-10-31). The audit produced 62 findings and the red team 12 challenges to the original design. Three challenges needed a PO decision: the 12-role team shape, the depth of review on every PR, and Scrum sprints against a Kanban flow. No source in the register measures this team's cost per PR, and the PO's 2026-10-31 rule put principal-engineer, senior engineer and QA review on every PR, docs included.

## Considered options

1. **Team shape.** Keep 12 roles, or move to about 5 standing agents with stack knowledge in skills [ASB/ANT-09] (agent teams cost more tokens and suit independent work).
2. **Review depth.** The same full panel on every PR, or depth by risk. DORA lists an overly heavy multi-approval review process as a trunk-based pitfall [ASB/REN-01]; Anthropic supports a separate skeptical evaluator [ASB/ANT-18] but no Anthropic source sets the number of serial gates.
3. **Cadence.** Keep sprints, or switch to goal-sized increments in a Kanban flow.

## Decision outcome

1. **Keep the 12 role agents.** Measure cost per PR (tokens and wall time per review, fix and CI round) for one sprint before reconsidering the shape. The engineering-manager reports it at the Sprint 5 reflection.
2. **Review depth is tiered by risk** (working-agreement §6):
   - **Tier 0, docs and process text:** one fresh-context reviewer plus automated doc checks (referenced paths exist, citations resolve, agent front matter parses).
   - **Tier 1, ordinary code:** principal-engineer review plus the senior-qa-engineer test review (which fills the senior slot) plus green CI.
   - **Tier 2, risky changes** (security, personal data, schema or API contracts): the full panel, with the specialist reviewers in §6.
   - **Enforcement:** `scripts/ci/merge_ready.py` still requires a principal-engineer and a senior-* APPROVE on the head of every PR. Until a Sprint 5 ticket teaches it the tiers and adds the automated doc checks, every PR, Tier 0 included, still needs those two verdicts.
3. **Keep sprints** with the kickoff and reflection the PO asked for, and add WIP limits per stage (in review, awaiting QA) and flow metrics (cycle time, throughput, work item age) to the sprint metrics.
4. **The audit findings applied in `drafts/docs-audit` are accepted**, including the red team's amendments. The 15 findings marked for PO decision and the other red-team design challenges stay open in the audit record.

## Consequences

- Sprint 5 planning must include the `merge_ready.py` tier ticket (sre-devops-engineer, test-first) and the doc-check CI job.
- The 12-role cost measurement needs a per-PR cost record; without it the question cannot be revisited with evidence.
