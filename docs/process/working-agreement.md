# Working Agreement: racket-analytics agent team

- **Status:** Accepted (see ADR 0001)
- **Date:** 2026-10-03
- **Owner:** engineering-manager
- **Human product owner:** the repository owner. They hold final say on scope, priorities, releases, spend, legal and privacy.

## 0. Citation convention

Evidence is cited as `<file>/<ID>`:

| Prefix | File |
|---|---|
| EP | `docs/research/engineering-process.md` |
| AQS | `docs/research/architecture-quality-security.md` |
| DPA | `docs/research/design-product-ai-agents.md` |
| DOM | `docs/research/domain-pickleball-cv.md` |

The prefix is mandatory because the same ID means different things in different files. For example, `AI-05` is the evals post in DPA but the Claude Code best-practices page in AQS. Only sources marked verified may be cited. Anything else is labelled **(judgment)**.

## 1. The team

The agents are defined in `.claude/agents/`, one role per file. Each has a single responsibility, a tool allowlist and a specific system prompt [DPA/AI-09].

| Agent | Role summary | Can edit code? |
|---|---|---|
| engineering-manager | Orchestrates, plans sprints, runs retros, owns the process | docs only (judgment) |
| product-manager | Value, priority, MVP slice | docs only |
| business-analyst | FR/NFR, stories, Gherkin acceptance criteria, traceability | docs only |
| principal-engineer | Architecture, domain model, technical design review | docs only |
| principal-designer | UX, HAX, WCAG 2.2 AA, design review | docs only |
| senior-backend-engineer | FastAPI, domain, rules engine, analytics, coaching service | yes |
| senior-ml-cv-engineer | Vision pipeline, eval sets, GPU cost | yes |
| senior-frontend-engineer | Next.js PWA, accessibility | yes |
| senior-qa-engineer | Test strategy, scenarios, integration/E2E, eval suites | tests and test docs |
| security-privacy-engineer | Threat models, security review | no (read-only reviewer) |
| sre-devops-engineer | CI/CD, hooks, observability, SLOs, cost | infra and config |
| pickleball-domain-coach | Rules, strategy, drills, domain verification | docs only |

## 2. SDLC flow

Every story moves through these stages. A stage's output is the next stage's input.

```
discover -> requirements -> design -> TDD implement -> review -> test -> release -> retro
```

| Stage | Responsible agent | Output | Exit gate |
|---|---|---|---|
| Discover | PM, with the coach and principal-engineer | Problem statement, research notes, EventStorming events [EP/ENG-14] | PM accepts the problem and value |
| Requirements | BA | FR/NFR, story, Gherkin acceptance criteria [DPA/PROD-01, DPA/PROD-02] | Definition of Ready |
| Design | principal-engineer, principal-designer | Design doc or ADR, reviewed as a PR *before* implementation [DPA/DESIGN-15] | Design review approved |
| TDD implement | senior engineers | Code plus tests, red -> green -> refactor [EP/ENG-18] | Local gates green, with evidence |
| Review | fresh-context reviewers (§6) | Findings | No open Blocking findings |
| Test | senior-qa-engineer | Integration, E2E and eval results; test report | Story DoD met |
| Release | sre-devops-engineer, EM | Deployed increment, release notes | Human product owner signs off [EP/ENG-16] |
| Retro | EM, facilitating | `docs/retros/<date>-sprint-<nn>.md` | Action items owned and dated [EP/ENG-15] |

Agents follow explore -> plan -> implement -> commit inside a stage. They skip the plan only when the diff can be described in one sentence [EP/ENG-24].

## 3. Sprint cadence

- **Length:** 2 weeks of calendar time, or one sprint goal for agent-only bursts, whichever comes first (judgment). The Scrum Guide's timeboxes are unverified in our research [EP Gaps], so this is our own choice.
- **Sprint planning (day 1):**
  - The PM states the product goal.
  - The EM writes the sprint goal as a short bullet list [EP/ENG-15].
  - Only stories that meet the Definition of Ready are pulled in.
  - Stories are sized relatively (t-shirt sizes) [EP/ENG-15].
- **Daily sync (async):** each agent appends to `docs/sprints/<nn>/progress.md` with what it did, what it will do next, and blockers. `status.json` holds pass/fail per feature and test [EP/ENG-28].
- **Design review:** held before implementation for any new component or UI flow [DPA/DESIGN-15].
- **Sprint review (last day):**
  - Show working software against the sprint goal [EP/ENG-15].
  - Show evidence: test reports, eval reports and DORA metrics [EP/ENG-21].
  - The human product owner accepts or rejects the increment.
- **Retrospective (last day):**
  - Use the template in `docs/retros/TEMPLATE.md` and rotate the format.
  - Produce owned, dated action items that go into the backlog [EP/ENG-15].
  - Review the previous retro's action items first.
- **Priorities stay stable inside a sprint.** Changes go through the human product owner [EP/ENG-22].

Sprints follow the spec milestones (M0 -> M7). M0 comes first: upload, storage, queue, schema, the manual tagging UI and the rules engine with tests.

## 4. RACI

R = Responsible, A = Accountable, C = Consulted, I = Informed. Human PO is the human product owner.

| Activity | PM | BA | EM | PrincEng | PrincDes | BE | ML/CV | FE | QA | Sec | SRE | Coach | Human PO |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Backlog priority and MVP slice | R | C | C | C | C | I | I | I | I | I | I | C | A |
| FR/NFR and acceptance criteria | C | R | I | C | C | C | C | C | C | C | C | C | A |
| Pickleball rule verification | I | C | I | I | I | I | I | I | C | I | I | R | A |
| Architecture and domain model | I | C | I | R/A | C | C | C | C | I | C | C | C | I |
| UX and accessibility design | C | C | I | C | R/A | I | I | C | C | I | I | C | I |
| Backend implementation | I | I | I | C | I | R | C | C | C | C | I | C | I |
| CV pipeline and model evals | I | I | I | C | I | C | R | I | C | I | C | C | I |
| Frontend implementation | I | I | I | C | C | C | I | R | C | C | I | I | I |
| Test strategy and scenarios | I | C | I | C | I | C | C | C | R/A | C | I | C | I |
| Security and privacy review | I | C | I | C | I | C | C | C | C | R/A | C | I | I |
| CI/CD, observability, SLOs | I | I | I | C | I | C | C | C | C | C | R/A | I | I |
| Sprint process and retros | C | C | R/A | C | C | C | C | C | C | C | C | C | I |
| Release sign-off | C | I | R | C | C | I | I | I | C | C | C | I | A |
| ADR for a decision | the decider is R; the EM is A for completeness of the log ||||||||||||| I |

## 5. Branching, commits and pull requests

- **Branching:** trunk-based, with short-lived branches `<type>/<story-id>-<slug>` off `main` (judgment). Every merge to `main` passes CI.
- **Commits:** Conventional Commits 1.0.0, in the form `<type>[scope]: <description>`.
  - `feat` maps to a MINOR release, `fix` to PATCH, and `!` or `BREAKING CHANGE:` to MAJOR [EP/ENG-08].
  - Scope is the bounded context, e.g. `feat(scoring): ...`.
- **Commit and PR descriptions:** an imperative first line. The body states the problem, the approach, the trade-offs, links (story, ADR) and the evidence (commands and output) [EP/ENG-07].
- **PR size:** aim for about 100 changed lines. About 1000 lines is too large, and so is a small change spread over many files [EP/ENG-04]. The hard ceiling is about 400 lines (judgment, from AQS implications). Split anything larger.
- **One concern per PR.** Tests ride with the logic they cover. Refactors go in separate PRs [EP/ENG-04].
- Only the orchestrator (the main session) runs git commits and merges. Agents propose commit messages.
- **Commit unit (2026-10-03, ADR 0022):** the orchestrator commits one story, or one PR-sized slice of a story, at a time, even without a remote. A commit over 400 changed lines needs an EM waiver row in `docs/sprints/<nn>/decision-log.md`. Sprint 0 landed as two ~15k-line commits (retro 0, M1).
- **Slices are planned, waivers come first (2026-10-05, ADR 0030).** The EM's brief for an M or L story names its slices, each planned at 400 changed lines or less and green on its own (ST-020 is the model). A waiver row must exist **before** the commit. If no waiver row exists, the commit waits or is split. In Sprint 1, 12 of 82 commits were over 400 lines and 11 of them had no waiver at commit time (retro 1, M6).

## 6. Code review rules

- **Standard:** approve when the change definitely improves overall code health, even if it is not perfect [EP/ENG-03].
- **Checklist:** design, functionality (including whether it serves users), complexity, tests, naming, comments that explain why, style, and docs [EP/ENG-05].
- **Comment etiquette:**
  - Comment on the code, never the author, and explain why.
  - Label severity: **Blocking** (unlabelled), `Nit:`, `Optional:`/`Consider:`, `FYI:` [EP/ENG-06].
- **Automation first:** linters and static analysis run before any reviewer, so reviews focus on design and function [EP/ENG-19]. Hooks enforce this [DPA/AI-10].
- **Fresh context:** the reviewer is a different agent invocation from the writer, with no access to the writer's reasoning [DPA/AI-08].
  - Reviewers flag only correctness, security or stated-requirement gaps, to avoid over-engineering [EP/ENG-24].
- **Turnaround:** for agents, review runs immediately after the PR is opened and before the writer starts its next task. For humans, the limit is one business day [EP/ENG-02].
- **Who reviews what:**

| Change touches | Required reviewers |
|---|---|
| Any code | senior-qa-engineer (tests vs acceptance criteria) plus one engineer peer or principal-engineer |
| New component, schema, API contract, cross-context interaction | principal-engineer |
| Auth, uploads, storage, media URLs, secrets, logging, LLM calls, personal data | security-privacy-engineer |
| UI | principal-designer (UX, WCAG 2.2 AA) |
| Rules, scoring, shot taxonomy, drills, coaching copy | pickleball-domain-coach |
| CI, infra, hooks | sre-devops-engineer, plus security-privacy-engineer for secrets and permissions |
| Model or pipeline accuracy | senior-ml-cv-engineer peer review of the eval report, plus senior-qa-engineer |

## 7. Auto-review and auto-fix loop

The loop runs automatically in the background for every PR.

1. **Deterministic gates.** These run as hooks and CI, not as prompt instructions, because hooks always run [DPA/AI-10, EP/ENG-24]:
   - format and lint on every Edit/Write (PostToolUse);
   - blocked writes to secret paths, and a Bash audit log (PreToolUse);
   - unit tests must pass before a turn may end (Stop);
   - CI runs lint, type checks, unit, integration, E2E, axe-core, BOLA suite, dependency and secret scans.
1a. **Integration smoke before review (2026-10-03, ADR 0022).** Before review round 1, the orchestrator runs these on the integrated tree and attaches the output to the review input: a fresh-volume `docker compose up --wait`, the full Playwright suite, and the backend suite with no ambient service variables (retro 0, M6).
   - **Isolated evidence (2026-10-05, ADR 0030).** Every suite count used as evidence (smoke, review, status) comes from an isolated run: its own `RA_DEV_STATE` Postgres and object store, or a fresh Compose project, and the command shows which. The smoke and every reviewer run start with `df -h /`. At least 10 GB must be free; if not, the SRE prunes first (retro 1, M4).
2. **Fresh-context review.** The reviewers from the table in §6 review in parallel. Each returns findings labelled by severity [DPA/AI-08].
3. **Auto-fix.** The owning engineer gets the Blocking findings and fixes them test-first. For a bug, it writes a failing test first [EP/ENG-24]. It must not edit or delete accepted tests [EP/ENG-28]. Nits and Optionals are fixed only when cheap. Otherwise they are recorded.
   - **Routing by owner (2026-10-03, ADR 0022).** Each finding goes to the role that can close it, in the same round: code to the owning engineer; API contract and ADR amendments to the principal-engineer; test-change approvals to the senior-qa-engineer; sprint artifacts (`status.json`, `progress.md`, retro) to the engineering-manager; environment, repo-admin and legal items to the human product owner via the EM. A finding marked "not my lane" is an EM routing defect, not a fix iteration (retro 0, M2/M3).
   - **Threat controls are acceptance criteria (2026-10-03, ADR 0022).** A threat-model control that names a story is an acceptance criterion of that story, with a red test (retro 0, M4).
3b. **Disposition per finding (2026-10-05, ADR 0030).** Before the next round starts, every finding of the round has one row in `docs/sprints/<nn>/review-rounds.md` with exactly one disposition: **fixed** (with evidence), **deferred** (to a named backlog row with an owner and a sprint), or **rejected** (with a reason the reviewer accepts). Minors and nits may be deferred, but never left blank. The EM checks that the number of findings matches the number of rows (retro 1, M1).
3c. **EM status step (2026-10-05, ADR 0030).** The last step of every fix round is the EM refreshing `status.json` and `progress.md` from the round's commits and runs. Re-review starts after it (retro 1, M2).
4. **Re-review.** The same reviewers re-check the changed lines and their findings. *(2026-10-05, ADR 0030)* They also re-check every earlier finding of theirs that is not dispositioned as fixed, or deferred, or rejected. Sprint 1 round-1 design blockers were never re-checked because their code did not change (retro 1, M1).
5. **Iteration limit:**
   - Iterations 1 and 2 run in the same context.
   - If both fail, iteration 3 starts in a **fresh context with an improved prompt** [EP/ENG-24].
   - If iteration 3 also fails, the EM **escalates to the human product owner**.
   - The maximum is therefore **3 fix iterations per PR**. The limit is judgment, based on the two-failed-corrections rule.
6. **Evidence.** Every iteration appends the commands run and their output to the PR description and to `progress.md` [EP/ENG-24].
7. **CI review bot (optional).** Uses `anthropics/claude-code-action@v1` with:
   - least-privilege permissions;
   - `--max-turns`, timeouts and concurrency limits;
   - bots blocked from triggering runs [DPA/AI-11, DPA/AI-13].
8. **Sandbox.** Autonomous runs are sandboxed at both the filesystem and the network boundary [DPA/AI-07].

## 8. Escalation to the human product owner

The EM escalates, with a short note covering the question, the options, a recommendation, the evidence and the deadline, when:

- a fix loop hits its 3-iteration limit;
- two agents still disagree after one round of exchanging evidence. Both options are recorded in an ADR, and the human decides; then everyone disagrees and commits [DPA/DESIGN-15];
- scope, priority or a milestone's "Done when" would change;
- a new paid dependency, licence or spend is needed. Examples: an AGPL-3.0 licence decision for Ultralytics or BoxMOT [DOM/CV-05, DOM/CV-07], or GPU or LLM budgets;
- anything touches law, privacy, minors or residual security risk. GDPR and related law is unverified in our research [AQS Gaps];
- a domain rule cannot be verified [DOM G1];
- a release is ready for sign-off;
- an SLO error budget is exhausted [AQS/REL-02].

Until the human answers, agents continue only with work that does not depend on the decision.

## 9. Decision logging

Every significant decision is an ADR in `docs/decisions/`. Each ADR carries:

- evidence: source IDs, data and test results;
- reasoning: the alternatives considered.

The format is in `docs/decisions/README.md` [EP/ENG-09, EP/ENG-10]. An accepted ADR is never rewritten. A change of decision gets a new ADR that supersedes the old one.

## 10. Metrics reviewed each sprint

- **DORA four keys:** deployment frequency, lead time, change failure rate and time to restore [EP/ENG-21].
- **PR time-to-merge** [EP/ENG-19].
- **Review and fix:** iterations per PR, and escalations (judgment).
- **Quality:** model eval and coaching eval results.
- **Cost:** GPU-seconds per match-minute.
