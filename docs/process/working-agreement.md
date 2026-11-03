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
| ASB | `docs/research/agentic-sdlc-best-practices.md` (agentic SDLC research, 2026-10-31; source IDs ANT, AGL, REN, REQ, RPD, SDD keep their own names, e.g. `ASB/ANT-05`) |

The prefix is mandatory because the same ID means different things in different files. For example, `AI-05` is the evals post in DPA but the Claude Code best-practices page in AQS. Only sources marked verified may be cited. In ASB, a source counts as verified only when it is marked verified **and** its fact-check confirmed it; any other ASB source is cited with **(unverified)** after the ID. Anything else is labelled **(judgment)**.

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

- **Length:** 2 weeks of calendar time, or one sprint goal for agent-only bursts, whichever comes first (judgment). The Scrum Guide 2020 sets a sprint of one month or less, with planning at most 8 h, review at most 4 h and retro at most 3 h for a one-month sprint, shorter for shorter sprints [ASB/AGL-01, a mirror of the Scrum Guide, not the official site]. Goal-bounded agent-only bursts are a deliberate deviation from that, which lightweight, goal-bounded cadences allow [ASB/AGL-11].
- **Sprint planning (day 1).** The steps below put the PO's 2026-10-31 planning instruction into practice. That instruction is known only **as relayed by the orchestrator** and is not yet quoted in `docs/requirements/po-input-2026-10-05.md`; the PO's own words go there first (ADR 0047 rule 5). The wording of these steps is the team's, not the PO's.
  1. **Kickoff:** read the previous retro's §5 (lessons) and §7 (action items) and the open rows in `review-rounds.md`. Each role states one lesson that applies to this sprint.
  2. The PM states the product goal and where it lives. The team agrees one sprint-goal sentence with a bullet scorecard [EP/ENG-15].
  3. The BA breaks the FRs and NFRs into atomic rules (`definition-of-ready.md`).
  4. Stories are split into tickets, one PR each. A ticket too big for one PR becomes a story with smaller ticket tasks. Size unit: §5. Stories are sized relatively (t-shirt sizes) [EP/ENG-15].
  5. The EM assigns each ticket to the role whose file fits it best, with disjoint file paths per lane. Each brief states the objective, the output, the files owned and the done-check [ASB/ANT-12, ASB/ANT-09]. Start with few lanes; a plan with more than 5 concurrent lanes says why [ASB/ANT-09, by analogy: it covers Claude Code agent teams].
  6. Only stories that meet the Definition of Ready are pulled in. A ticket is done only when its PR meets the story-level Definition of Done and the senior-qa-engineer has tested it.
- **Daily sync (async):** each ticket records its progress, decisions and evidence in its own `docs/sprints/<nn>/decisions/<TICKET-ID>.md` and in its PR description. Ticket PRs never edit `progress.md`, `status.json`, `decision-log.md` or `blockers.md`, because parallel PRs editing them conflict; only the sprint's DOCS/RETRO ticket consolidates them (`docs/sprints/sprint-04.md`, "Shared sprint files"). `status.json` holds pass/fail per goal item [EP/ENG-28].
- **Design review:** held before implementation for any new component or UI flow [DPA/DESIGN-15].
- **Sprint review (last day):**
  - Show working software against the sprint goal [EP/ENG-15].
  - Show evidence: test reports, eval reports and the DORA metrics in §10.
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
- **PR size:** aim for about 100 changed lines. About 1000 lines is too large, and so is a small change spread over many files [EP/ENG-04]. The hard ceiling is set in **Size unit** below.
- **Only production code counts (PO 2026-10-28, ADR 0054).** The size limits above count production code only. Tests (`backend/tests`, `web/tests`, `infra/tests`, `e2e`, `tests/`, `*.feature`, `*.spec.ts`, `*.test.ts(x)`, `conftest.py`), docs (`docs/`, `*.md`), lockfiles, fixtures and snapshots are excluded; `check_pr_size.py` prints both the counted and the excluded totals. Over 400 production lines still needs the EM's `size-waiver`. Never split a red-first commit to fit the limit.
- **Draft first, ready when green (2026-10-18, ADR 0052).** A ticket PR opens as a draft, and CI skips drafts. The PR-policy decisions (`size-waiver`, `qa-approved-test-change`) are made while it is a draft; red-first commits are pushed together with their green commit; the author marks it ready only when the local checks pass (`check_pr_size.py`, `check_test_immutability.py`, the touched suites). Reviews and merge start from the ready state.
- **One concern per PR.** Tests ride with the logic they cover. Refactors go in separate PRs [EP/ENG-04].
- **Commits and merges (orchestrator 2026-10-09).** Lanes commit on their own ticket branch, in their own git worktree, and never force-push or rewrite pushed history. Only the gated merge step merges, and only after `scripts/ci/merge_ready.py` exits 0. No other agent merges, enables auto-merge or marks a draft ready in order to merge it.
- **Ticket branches from planning (2026-10-08, ADR 0047).** When tickets ship as PRs (ADR 0039), the plan's ticket map names each ticket's base. The orchestrator creates every base and ticket branch at planning, lanes commit on their ticket branch, and the PR opens with the first pushed commit. Each ticket branch starts from current `main` and merges into `main` through its own PR. There is no sprint branch (po-input decision table, row "One PR per ticket", 2026-10-07; P13).
- **PO decisions are quoted, never written by agents (2026-10-08, ADR 0047).** In `po-input-*.md` and ADR 0023 notes, a PO decision is the PO's own words. Agent text there goes under a heading that names the role and says "not a PO decision" (retro 3, M7).
- **Size unit (canonical; ADR 0054 replaces the per-commit rules of ADR 0022 and ADR 0030):** one ticket = one PR, at 400 production lines or fewer as counted by `check_pr_size.py`. A PR over the limit needs the EM `size-waiver` label, decided while the PR is a draft (ADR 0052). The slices of an M or L story are planned at planning. Never split a red-first commit to fit the limit.

## 6. Code review rules

- **Standard:** approve when the change definitely improves overall code health, even if it is not perfect [EP/ENG-03].
- **Checklist:** design, functionality (including whether it serves users), complexity, tests, naming, comments that explain why, style, and docs [EP/ENG-05].
- **Comment etiquette:**
  - Comment on the code, never the author, and explain why.
  - Label severity: **Blocking** (unlabelled), `Nit:`, `Optional:`/`Consider:`, `FYI:` [EP/ENG-06].
- **Verdict format (CI-PR-GATE):** every PR review body starts with `Verdict: APPROVE` or `Verdict: CHANGES REQUESTED`, followed on the next line by `Reviewer: <role>`, and is submitted (not left pending). `scripts/ci/merge_ready.py` reads only that format before a merge; see `docs/ops/branch-protection.md` §3.
- **Automation first:** linters and static analysis run before any reviewer, so reviews focus on design and function [EP/ENG-19]. Hooks enforce this [DPA/AI-10].
- **Fresh context:** the reviewer is a different agent invocation from the writer, with no access to the writer's reasoning [DPA/AI-08].
  - Reviewers flag only correctness, security or stated-requirement gaps, to avoid over-engineering [EP/ENG-24].
- **Turnaround:** for agents, review runs immediately after the PR is opened and before the writer starts its next task. For humans, the limit is one business day [EP/ENG-02].
- **Who reviews what:**

| Change touches | Required reviewers |
|---|---|
| Every PR (code, tests, docs, config) | principal-engineer AND a senior-* engineer (whether a senior-qa-engineer APPROVE fills this slot is an open PO question), a different senior role from the author where possible (PO 2026-10-07, ADR 0039; enforced by `scripts/ci/merge_ready.py`). The rows below add reviewers and never replace these two |
| Any code | senior-qa-engineer tests the PR head against the acceptance criteria (PO 2026-10-31: "QA must test them first"). Whether this review also fills the senior slot above is the same open PO question |
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
   - **Disk check command (2026-10-05, QA-R2V-05).** The check is `bash scripts/disk-precheck.sh` (exit 3 below the floor). `scripts/measure/live_goal.py` refuses to start below it and records `disk_free_gb_start`/`_end`. Prune procedure: `docs/ops/disk-and-prune.md`.
   - **Self-cleaning, isolated evidence (2026-10-05, ADR 0033).** Every evidence stack is torn down with `down -v --rmi local` on its own Compose project. Every Playwright evidence run passes `--output <run dir>/pw-out` and holds `flock .local/evidence-e2e.lock` (also held for evidence Compose up/down). Goal-scorecard methods are dry-run end to end by their author, with the rc in the decision log, before the verifier runs them (retro 1 final close, M11-M13).
2. **Fresh-context review.** The reviewers from the table in §6 review in parallel. Each returns findings labelled by severity [DPA/AI-08]. *(2026-10-05, ADR 0033)* Each reviewer also appends one row per finding to `docs/sprints/<nn>/review-rounds.md` under its own heading, with the disposition **Open**, so a finding without an owner row still counts as open (retro 1 final close, M10).
3. **Auto-fix.** The owning engineer gets the Blocking findings and fixes them test-first. For a bug, it writes a failing test first [EP/ENG-24]. It must not edit or delete accepted tests [EP/ENG-28]. Nits and Optionals are fixed only when cheap. Otherwise they are recorded.
   - **Routing by owner (2026-10-03, ADR 0022).** Each finding goes to the role that can close it, in the same round: code to the owning engineer; API contract and ADR amendments to the principal-engineer; test-change approvals to the senior-qa-engineer; sprint artifacts (`status.json`, `progress.md`, retro) to the engineering-manager; environment, repo-admin and legal items to the human product owner via the EM. A finding marked "not my lane" is an EM routing defect, not a fix iteration (retro 0, M2/M3).
   - **Threat controls are acceptance criteria (2026-10-03, ADR 0022).** A threat-model control that names a story is an acceptance criterion of that story, with a red test (retro 0, M4).
3b. **Disposition per finding (2026-10-05, ADR 0030).** Before the next round starts, every finding of the round has one row in `docs/sprints/<nn>/review-rounds.md` with exactly one disposition: **fixed** (with evidence), **deferred** (to a named backlog row with an owner and a sprint), or **rejected** (with a reason the reviewer accepts). Minors and nits may be deferred, but never left blank. The EM checks that the number of findings matches the number of rows (retro 1, M1).
3c. **EM status step (2026-10-05, ADR 0030).** The last step of every fix round is the EM recording the round's status. During the sprint that goes in the ticket's own `decisions/<TICKET-ID>.md` and PR description; `status.json` and `progress.md` are refreshed only in the sprint's DOCS/RETRO ticket (§3). Re-review starts after it (retro 1, M2). *(2026-10-05, ADR 0033)* The step also runs `scripts/measure/open_defects.py` and states the count. When the scorecard or the open count changes, it rewrites `sprint-report.md` §1 (retro 1 final close, M14).
3d. **Reconciliation before the next step (2026-10-06, ADR 0037).** Every review or verification round ends with an EM reconciliation step. The orchestrator saves each reviewer's returned finding list. The EM checks that every returned id has a row in `review-rounds.md`, with a severity and a disposition column, and writes an Open row attributed to the reviewer for any id that is missing. This also covers reviewers that cannot write files. Goal verification and the next round start only after this step (retro 2, M1). The plan schedules each design-review decision cell as a task with a role, a brief and a date, like a lane, and a UI story whose flows are not approved does not start without a PO waiver recorded first (retro 2, M2). Goal items that depend on a human input due after the session are agreed with the PO at planning (retro 2, M3).
3e. **Gates first, rounds in series, CI each round (2026-10-08, ADR 0047).** Sprint planning lists the gate tasks (design, contract, threat notes, decider cells, coach review). The orchestrator runs them first, each with its brief, and then briefs a build lane only on stories whose DoR is met. A goal round never routes a story whose gate is open; it asks the PO for a waiver, recorded before the work starts. A review round and a verification round never run on the same head at the same time, and the EM's reconciliation log row for one round is the entry condition of the next. A verifier that finds a finished round with no log row reports the open-defect metric as not measurable. Every EM status step, and the step before each verification round, confirms that CI on `main` and on every open ticket PR is green; the run ids go in `ci-status.md` (retro 3, M1-M3, M5).
4. **Re-review.** The same reviewers re-check the changed lines and their findings. *(2026-10-05, ADR 0030)* They also re-check every earlier finding of theirs that is not dispositioned as fixed, or deferred, or rejected. Sprint 1 round-1 design blockers were never re-checked because their code did not change (retro 1, M1).
5. **Iteration limit:**
   - Iterations 1 and 2 run in the same context.
   - If both fail, iteration 3 starts in a **fresh context with an improved prompt** [EP/ENG-24].
   - If iteration 3 also fails, the EM **escalates to the human product owner**.
   - The maximum is therefore **3 fix iterations per PR**. The limit is judgment, based on the two-failed-corrections rule.
6. **Evidence.** Every iteration appends the commands run and their output to the PR description; the DOCS/RETRO ticket carries them into `progress.md` [EP/ENG-24].
7. **CI review bot (optional).** Uses `anthropics/claude-code-action@v1` with:
   - least-privilege permissions;
   - `--max-turns`, timeouts and concurrency limits;
   - bots blocked from triggering runs [DPA/AI-11, DPA/AI-13].
8. **Sandbox.** Autonomous runs should be sandboxed at both the filesystem and the network boundary [DPA/AI-07]. Today they rely on the host's sandbox (the cloud container and agent proxy); the repo does not configure one (`.claude/settings.json` has no sandbox settings). If a run is not sandboxed, the deny rules and hooks are guards against mistakes, not security boundaries [ASB/ANT-05].

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

- **DORA metrics (five; canonical list):** change lead time, deployment frequency, failed deployment recovery time, change fail rate and deployment rework rate. They are reported per service and never used as targets [ASB/AGL-02, ASB/AGL-03].
- **PR time-to-merge** [EP/ENG-19].
- **Review and fix:** iterations per PR, and escalations (judgment).
- **Quality:** model eval and coaching eval results.
- **Cost:** GPU-seconds per match-minute.
