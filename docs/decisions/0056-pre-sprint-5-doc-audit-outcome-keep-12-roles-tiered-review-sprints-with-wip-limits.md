# 0056. Pre-Sprint 5 doc audit outcome: keep 12 roles (measure cost), review depth tiered by risk, sprints with WIP limits

- **Status:** Accepted (human product owner, 2026-11-03; `docs/requirements/po-input-2026-10-05.md`, addendum "Audit decisions")
- **Date:** 2026-11-03
- **Deciders:** human product owner
- **Consulted:** engineering-manager, principal-engineer, senior-qa-engineer (audit, red team and doc tests of 2026-10-31); orchestrator
- **Related:** amends ADR 0039 rule 3 (reviewers); retires ADR 0022 decision 3 (commit unit), ADR 0030 decision 4 (waiver before the commit; the slice plan stays) and ADR 0047 rules 3 and 4 (sprint branch); ADR 0050 (one merge at a time), ADR 0052 (draft first), ADR 0054 (PR size); research register `docs/research/agentic-sdlc-best-practices.md`; audit record `docs/process/audit-2026-10-31-open-items.md`

## Context and problem statement

Before Sprint 5 the PO asked for the role files and process docs to be researched, audited, tested and challenged (addendum "Way of working", 2026-10-31). The audit produced 62 findings and the red team 12 challenges to the original design. Three challenges needed a PO decision: the 12-role team shape, the depth of review on every PR, and Scrum sprints against a Kanban flow. No source in the register measures this team's cost per PR, and the PO's 2026-10-31 rule put principal-engineer, senior engineer and QA review on every PR, docs included.

## Considered options

1. **Team shape.** Keep 12 roles, or move to about 5 standing agents with stack knowledge in skills [ASB/ANT-09] (agent teams cost more tokens and suit independent work).
2. **Review depth.** The same full panel on every PR, or depth by risk. DORA lists an overly heavy multi-approval review process as a trunk-based pitfall [ASB/REN-01]; Anthropic supports a separate skeptical evaluator [ASB/ANT-18] but no Anthropic source sets the number of serial gates.
3. **Cadence.** Keep sprints, or switch to goal-sized increments in a Kanban flow.

## Decision outcome

1. **Keep the 12 role agents.** Measure cost per PR (tokens and wall time per review, fix and CI round) for one sprint before reconsidering the shape. Each ticket's decisions file records it, and the engineering-manager reports it at the Sprint 5 reflection (working-agreement §10, retro template §2).
2. **Review depth is tiered by risk** (working-agreement §6):
   - **Tier 0, docs and process text:** one fresh-context reviewer plus automated doc checks (referenced paths exist, citations resolve, agent front matter parses).
   - **Tier 1, ordinary code:** principal-engineer review plus the senior-qa-engineer test review (which fills the senior slot) plus green CI.
   - **Tier 2, risky changes** (security, personal data, schema or API contracts): the full panel, with the specialist reviewers in §6.
   - **Enforcement:** `scripts/ci/merge_ready.py` still requires a principal-engineer and a senior-* APPROVE on the head of every PR. Until a Sprint 5 ticket teaches it the tiers and adds the automated doc checks, every PR, Tier 0 included, still needs those two verdicts.
3. **Keep sprints** with the kickoff and reflection the PO asked for, and add WIP limits per stage and flow metrics (cycle time, throughput, work item age) to the sprint metrics. The starting limits are in working-agreement §3 "Flow and WIP limits": in progress 5, in review 3, awaiting QA 2, awaiting merge 1 (judgment, reviewed at the Sprint 5 reflection). The metrics are defined in working-agreement §10 and reported in the retro template §2 table.
4. **The audit findings applied in `drafts/docs-audit` are accepted**, including the red team's amendments. The 15 findings marked for PO decision and the other red-team design challenges stay open in the audit record, `docs/process/audit-2026-10-31-open-items.md`, which also says which of them decisions 1 to 3 answer.
5. **Superseded rules.** The audit corrections retire or amend these earlier rules (working-agreement §9: a change of decision gets a new ADR):
   - **ADR 0022 decision 3 (commit unit) and ADR 0030 decision 4 (waiver before the commit) are retired.** ADR 0054 decision 5 kept them, measuring production lines. Since Sprint 3 every change reaches `main` as one ticket PR (ADR 0039, PO P13), `check_pr_size.py` measures the PR diff, the `size-waiver` is decided while the PR is a draft (ADR 0052), and red-first commits are pushed with their green commit, so a per-commit ceiling has no check and would push lanes to split commits. The size unit is now one PR at 400 production lines or fewer (working-agreement §5 "Size unit"). ADR 0030's slice plan stays: the slices of an M or L story are planned at planning, one PR each.
   - **ADR 0047 rules 3 and 4, sprint-branch parts, are retired.** There has been no sprint branch since P13 ("Per-ticket PRs for Sprint 3 too") and the po-input row "One PR per ticket". Rule 3's fast-forward push of the sprint branch and CI dispatch becomes a check that CI is green on `main` and on every open ticket PR, with the run ids in `ci-status.md` (working-agreement §7 3e). Rule 4's "the sprint branch only takes merges from ticket branches" becomes "each ticket branch starts from current `main` and merges into `main` through its own PR" (working-agreement §5). The rest of rule 4 stays.
   - **ADR 0039 rule 3 (reviewers) is amended by decision 2.** The required verdicts depend on the tier, and in tier 1 the senior-qa-engineer's test verdict fills the senior slot. A reviewer still never reviews a PR its own role authored. Until `merge_ready.py` enforces the tiers, rule 3's principal-engineer plus senior-* APPROVE on the head SHA still applies to every PR. Working-agreement §6's former "Any code" row (senior-qa-engineer plus one engineer peer or principal-engineer) is replaced by the tier row.
   - **Working-agreement §5 "only the orchestrator runs git commits and merges"** (2026-10-03) was already replaced in practice by the separation-of-duties rule of 2026-10-09 (ADR 0050 context: lanes commit on their ticket branch, only the gated merge step merges). The working agreement now states that rule.

## Consequences

- Sprint 5 planning must include the `merge_ready.py` tier ticket (sre-devops-engineer, test-first) and the doc-check CI job.
- The 12-role cost measurement needs a per-PR cost record (working-agreement §10); without it the question cannot be revisited with evidence.
- `docs/ops/branch-protection.md` §4 (`size-waiver` row) now states the per-PR, production-lines rule.
