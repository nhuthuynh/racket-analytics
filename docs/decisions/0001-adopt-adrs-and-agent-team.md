# 0001. Adopt ADRs and an AI agent team with a defined working agreement

- **Status:** Accepted (pending ratification by the human product owner at the first sprint review)
- **Date:** 2026-10-03
- **Deciders:** engineering-manager
- **Consulted:** research files in `docs/research/` (process, architecture/security, design/product/agents, domain/CV)
- **Related:** `docs/process/working-agreement.md`, `definition-of-done.md`, `definition-of-ready.md`, `testing-strategy.md`, `ddd-guidelines.md`, `.claude/agents/*.md`

## Context and problem statement

racket-analytics will be built mostly by Claude Code subagents, each playing an engineering role, with a
human product owner. The user asked for three things:

- specialised agents whose behaviour is grounded in verified standards;
- delivery in sprints using SDLC, TDD and DDD, with test scenarios, integration tests and unit tests every sprint, and a retrospective after each sprint;
- background auto-review and auto-fix, with every decision logged together with its evidence and reasoning.

We need to decide how to structure the team, how decisions are recorded, and which process rules the
agents follow.

## Decision drivers

- Traceability: every decision must be backed by evidence and its alternatives (user request).
- Quality: AI adoption correlated with lower delivery stability, so we need small batches and robust testing [EP/ENG-22].
- Simplicity and cost: multi-agent setups use about 15x the tokens of chat. Start simple [EP/ENG-25, DPA/AI-02].
- Reliability of the rules: CLAUDE.md is advisory and hooks are deterministic [DPA/AI-10, EP/ENG-24].
- Reviewer bias: someone who reviews their own work misses things [DPA/AI-08].
- Domain risk: no pickleball rule has been verified yet [DOM G1].

## Considered options

1. **Role-specialised subagents in `.claude/agents/`.** A written working agreement, MADR-style ADRs in `docs/decisions/`, and a bounded auto-review/auto-fix loop.
2. **A single general-purpose agent.** It does all the roles, guided only by a long CLAUDE.md, and keeps decisions in commit messages.
3. **A fully autonomous multi-agent swarm.** Agents negotiate freely with no fixed workflow and no iteration limits.

## Decision outcome

Chosen option: **Option 1**. It meets every driver, and it keeps orchestration as fixed workflows. Agent
autonomy is used only inside a well-scoped task [EP/ENG-25, DPA/AI-01].

Specifically:

- **Team.**
  - Twelve subagents, one role each, with tool allowlists and specific prompts [DPA/AI-09]:
    engineering-manager, product-manager, principal-engineer, principal-designer, business-analyst,
    senior-backend-engineer, senior-ml-cv-engineer, senior-frontend-engineer, senior-qa-engineer,
    security-privacy-engineer, sre-devops-engineer, pickleball-domain-coach.
  - Tool access by kind of role:
    - Reviewers and advisors write docs only.
    - security-privacy-engineer is read-only.
    - Engineers have full tool access.
- **Decision log.** MADR-structured ADRs in `docs/decisions/nnnn-title.md`, with mandatory Evidence and Considered Options sections [EP/ENG-09, EP/ENG-10].
- **Process.** As set out in the working agreement:
  - SDLC flow, with 2-week sprints (judgment) and a written sprint goal [EP/ENG-15];
  - three-level DoD [EP/ENG-16];
  - TDD [EP/ENG-18];
  - DDD starter process and canvases [EP/ENG-11, EP/ENG-12];
  - Conventional Commits [EP/ENG-08];
  - PRs of about 100 lines [EP/ENG-04];
  - retrospectives with owned, dated actions [EP/ENG-15].
- **Auto-review and auto-fix.**
  - Deterministic hooks and CI gates [DPA/AI-10].
  - Fresh-context reviewers that flag only correctness and requirement gaps [DPA/AI-08, EP/ENG-24].
  - At most 3 fix iterations. Iteration 3 runs in a fresh context, following the "after two failed corrections, restart" rule [EP/ENG-24]. After that, the EM escalates to the human product owner.

## Pros and cons of the options

### Option 1: specialised subagents, ADRs and a bounded loop
- Good: each agent's context stays small and focused [DPA/AI-04]. Fresh-context review reduces self-review bias [DPA/AI-08]. Decisions can be audited.
- Good: the role prompts encode the verified standards, so behaviour is consistent across sessions.
- Bad: more tokens and more coordination overhead than a single agent [DPA/AI-02].
- Bad: twelve prompts must be maintained as the research changes.

### Option 2: a single generalist agent
- Good: the cheapest and simplest option [EP/ENG-25].
- Bad: no independent review, because the writer reviews its own work [DPA/AI-08]. A long CLAUDE.md is advisory and degrades as it grows [DPA/AI-08, DPA/AI-04].
- Bad: decisions hidden in commits lose their alternatives and evidence. This fails the user's logging requirement.

### Option 3: an autonomous swarm with no limits
- Good: the most parallelism.
- Bad: unbounded token cost [DPA/AI-02]. Agents would be used for well-defined tasks where workflows fit better [DPA/AI-01]. A fix loop could run forever without a human checkpoint. Failures are harder to diagnose [EP/ENG-26].

## Consequences

- **Good:**
  - Every story has a clear owner, reviewer and gates.
  - Every decision has a home and an evidence trail.
- **Trade-offs accepted:**
  - Higher token use, mitigated by fanning out only where it pays.
  - Process overhead on small changes, mitigated because one-sentence diffs skip the plan [EP/ENG-24].
- **Follow-up work:**
  - sre-devops-engineer implements the hooks and CI gates described in working agreement §7, under a separate ADR.
  - pickleball-domain-coach verifies the 2026 rulebook before any rules-engine story becomes Ready [DOM G1].
  - The human product owner ratifies this ADR and the 3-iteration escalation limit at the first sprint review.
  - The following choices are (judgment) and will be revisited at retro 1: sprint length, coverage thresholds, the PR ceiling of about 400 lines, and the iteration limit.

## Evidence

| Claim | Evidence | Type |
|---|---|---|
| Subagents are Markdown with YAML frontmatter in `.claude/agents/`. `name` and `description` are required; `tools` and `model` are optional. Use single responsibility and tool allowlists | [DPA/AI-09] | verified source |
| ADRs record one decision with options, pros and cons; never rewrite them, supersede them | [EP/ENG-09] | verified source |
| MADR sections and the `docs/decisions/nnnn-title.md` naming | [EP/ENG-10] | verified source |
| Start simple; prefer workflows over autonomous agents | [EP/ENG-25], [DPA/AI-01] | verified source |
| Multi-agent setups use about 15x the tokens of chat | [DPA/AI-02], [EP/ENG-26] | verified source |
| Fresh-context reviewer should flag only correctness and requirement gaps | [DPA/AI-08], [EP/ENG-24] | verified source |
| After two failed corrections, restart with a fresh context | [EP/ENG-24] | verified source |
| Hooks are deterministic; CLAUDE.md is advisory | [DPA/AI-10], [EP/ENG-24] | verified source |
| Tests are immutable for agents; track a feature list and progress file | [EP/ENG-28], [DPA/AI-12] | verified source |
| Three-level DoD | [EP/ENG-16] | verified source |
| Sprint goal as bullets; retro actions owned and dated | [EP/ENG-15] | verified source |
| AI adoption correlated with lower stability; keep batches small and testing robust | [EP/ENG-22] | verified source |
| No pickleball rule is verified yet | [DOM G1, Gaps] | verified research status |
| 2-week sprints, 3-iteration limit, coverage thresholds, ~400-line PR ceiling | (judgment) | judgment |
| Test results | Not applicable: no code yet | — |

## Confirmation

- All 12 agent files exist and each one contains a mission, responsibilities, cited standards, behaviours, a DoD, outputs and the ADR rule. The EM checks this at sprint 0.
- From sprint 1, every merged PR links to the story and to any ADR it needed. The EM samples PRs at retro.
- Retro 1 reviews the loop's metrics (iterations per PR, escalations) and adjusts the judgment parameters through a superseding ADR.

## Notes

- 2026-10-03: Created during team setup. The research files were verified on 2026-10-03. Many canonical hosts were egress-blocked, so the gaps listed in each research file still apply.
