# Design, Product, Accessibility and AI-Agent Research

- **Date:** 2026-10-03
- **Author role:** Senior research analyst (product, business analysis, UX/design, accessibility, Anthropic agent and AI-engineering guidance)
- **Scope:** The verified sources and rules that the racket-analytics agent team (Engineering Manager, Product Manager, Principal Engineer, Principal Designer, Senior Engineers, Business Analyst, Senior QA, domain coach) uses for:
  1. writing requirements and acceptance criteria (BDD/Gherkin),
  2. UX and human-AI interaction design for a product whose automatic calls carry confidence scores and can be corrected,
  3. accessibility (WCAG 2.2 AA plus platform guidance),
  4. design reviews and non-functional requirements,
  5. building and running the Claude-based agent team itself (subagents, hooks, review, evals, context management, sandboxing) and the in-product coaching LLM.
- **Product context:** `docs/specs/2026-10-02-racket-analytics-design.md`. Companion file: `docs/research/engineering-process.md` (SDLC, TDD, DDD, code review, ADRs, retrospectives, DORA).

## Method and evidence rules

- **What "verified = yes" means.** The source was fetched with WebFetch on 2026-10-03, and the fetched text contained the guidance attributed to it.
- **Star counts** are the values on the GitHub page at fetch time.
- **Blocked hosts.** This environment's egress proxy blocked many canonical hosts: www.w3.org, www.nngroup.com, cucumber.io, m3.material.io, www.agilealliance.org, www.agilebusiness.org, xp123.com, hbr.org, www.christenseninstitute.org, www.gov.uk, web.dev, pair.withgoogle.com, research.google, www.iso.org, dannorth.net and www.mountaingoatsoftware.com.
- **GitHub mirrors.** Where the publisher keeps the primary text in its own GitHub repository, the raw GitHub file was fetched instead, and the table says so:
  - WCAG: `w3c/wcag`
  - Cucumber docs: `cucumber/docs`
  - GOV.UK Design System: `alphagov/govuk-design-system`
  - Microsoft playbook: `microsoft/code-with-engineering-playbook`
- **Judgment.** Statements marked **(judgment)** are the analyst's own recommendations and are not attributed to any source.
- **IDs:**
  - `DESIGN-*` covers design, UX and accessibility.
  - `PROD-*` covers product and business analysis.
  - `AI-*` covers Anthropic agent and AI-engineering guidance.

## Source register

| ID | Title | Publisher / author | URL | Type | Credibility signal | Verified |
|---|---|---|---|---|---|---|
| DESIGN-01 | WCAG 2.2: guidelines index (spec source) | W3C AG Working Group | https://raw.githubusercontent.com/w3c/wcag/main/guidelines/index.html (repo: https://github.com/w3c/wcag) | standard | W3C standard. The repo has 1.5k stars | yes. Fetched from the W3C's own repo because www.w3.org is blocked. It confirms WCAG 2.2 and the new SCs 2.4.11, 2.4.12, 2.4.13, 2.5.7, 2.5.8, 3.2.6, 3.3.7, 3.3.8 and 3.3.9 |
| DESIGN-02 | WCAG 2.2 SC 2.5.8 Target Size (Minimum) | W3C | https://raw.githubusercontent.com/w3c/wcag/main/guidelines/sc/22/target-size-minimum.html | standard | W3C | yes. AA, 24×24 CSS px, five exceptions. (The fetch summarizer mislabelled it "2.5.5"; DESIGN-01 confirms the number is 2.5.8) |
| DESIGN-03 | WCAG SC 1.4.3 Contrast (Minimum) | W3C | https://raw.githubusercontent.com/w3c/wcag/main/guidelines/sc/20/contrast-minimum.html | standard | W3C | yes. AA, 4.5:1, or 3:1 for large text |
| DESIGN-04 | WCAG SC 1.4.11 Non-text Contrast | W3C | https://raw.githubusercontent.com/w3c/wcag/main/guidelines/sc/21/non-text-contrast.html | standard | W3C | yes. AA, 3:1 for UI components and graphical objects |
| DESIGN-05 | WCAG 2.2 SC 2.5.7 Dragging Movements | W3C | https://raw.githubusercontent.com/w3c/wcag/main/guidelines/sc/22/dragging-movements.html | standard | W3C | yes. AA |
| DESIGN-06 | WCAG 2.2 SC 3.3.8 Accessible Authentication (Minimum) | W3C | https://raw.githubusercontent.com/w3c/wcag/main/guidelines/sc/22/accessible-authentication-minimum.html | standard | W3C | yes. AA |
| DESIGN-07 | WCAG 2.2 SC 2.4.11 Focus Not Obscured (Minimum) | W3C | https://raw.githubusercontent.com/w3c/wcag/main/guidelines/sc/22/focus-not-obscured-minimum.html | standard | W3C | yes. AA |
| DESIGN-08 | WCAG SC 1.2.2 Captions (Prerecorded) | W3C | https://raw.githubusercontent.com/w3c/wcag/main/guidelines/sc/20/captions-prerecorded.html | standard | W3C | yes. Level A |
| DESIGN-09 | WCAG SC 1.2.3 Audio Description or Media Alternative (Prerecorded) | W3C | https://raw.githubusercontent.com/w3c/wcag/main/guidelines/sc/20/audio-description-or-media-alternative-prerecorded.html | standard | W3C | yes. Level A |
| DESIGN-10 | Make apps more accessible | Google (Android Developers) | https://developer.android.com/guide/topics/ui/accessibility/apps | official doc | Google, FAANG platform owner | yes. 48dp touch targets, contrast and content descriptions |
| DESIGN-11 | HAX Toolkit: Guidelines for Human-AI Interaction (Design Library) | Microsoft Research | https://www.microsoft.com/en-us/haxtoolkit/library/ (project page: https://www.microsoft.com/en-us/research/project/guidelines-for-human-ai-interaction/) | official doc / research | Microsoft Research. The project page cites the CHI 2019 paper "Guidelines for Human-AI Interaction" | yes. All 18 guidelines (G1 to G18) fetched verbatim from the library page. The CHI paper itself was **not** fetched |
| DESIGN-12 | GOV.UK Design System: Question pages pattern | UK Government Digital Service | https://raw.githubusercontent.com/alphagov/govuk-design-system/main/src/patterns/question-pages/index.md | official design system (repo) | UK GDS. Repo has 676 stars | yes. Raw GitHub, because gov.uk is blocked |
| DESIGN-13 | GOV.UK Design System: Error summary component | UK Government Digital Service | https://raw.githubusercontent.com/alphagov/govuk-design-system/main/src/components/error-summary/index.md | official design system (repo) | UK GDS | yes |
| DESIGN-14 | Code-With Engineering Playbook: Accessibility (NFR) | Microsoft | https://raw.githubusercontent.com/microsoft/code-with-engineering-playbook/main/docs/non-functional-requirements/accessibility.md | official playbook (repo) | Microsoft. Repo has 2.7k stars (per ENG-15 in engineering-process.md) | yes. Note: it cites WCAG **2.0**, which is outdated; we use 2.2 [DESIGN-01] |
| DESIGN-15 | Code-With Engineering Playbook: Design reviews | Microsoft | https://raw.githubusercontent.com/microsoft/code-with-engineering-playbook/main/docs/design/design-reviews/README.md | official playbook (repo) | Microsoft | yes |
| DESIGN-16 | Code-With Engineering Playbook: Performance (NFR) | Microsoft | https://raw.githubusercontent.com/microsoft/code-with-engineering-playbook/main/docs/non-functional-requirements/performance.md | official playbook (repo) | Microsoft | yes. Defines response time, throughput and latency. It does **not** prescribe percentile targets |
| PROD-01 | Gherkin Reference | Cucumber | https://raw.githubusercontent.com/cucumber/docs/main/content/docs/gherkin/reference.md | official doc (repo) | Official Cucumber docs. Repo has 156 stars and was **archived 2026-05-17** (docs moved to github.com/cucumber/website) | yes. Raw GitHub, because cucumber.io is blocked. The content is the last official version |
| PROD-02 | Writing better Gherkin | Cucumber | https://raw.githubusercontent.com/cucumber/docs/main/content/docs/bdd/better-gherkin.md | official doc (repo) | Official Cucumber docs (archived repo) | yes |
| AI-01 | Building effective agents | Anthropic (engineering blog) | https://www.anthropic.com/engineering/building-effective-agents | engineering blog | Anthropic, 2024-12-19 | yes |
| AI-02 | How we built our multi-agent research system | Anthropic (engineering blog) | https://www.anthropic.com/engineering/multi-agent-research-system | engineering blog | Anthropic, 2025-06-13 | yes |
| AI-03 | Writing effective tools for agents, with agents | Anthropic (engineering blog) | https://www.anthropic.com/engineering/writing-tools-for-agents | engineering blog | Anthropic, 2025-09-11 | yes |
| AI-04 | Effective context engineering for AI agents | Anthropic (engineering blog) | https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents | engineering blog | Anthropic, 2025-09-29 | yes |
| AI-05 | Demystifying evals for AI agents | Anthropic (engineering blog) | https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents | engineering blog | Anthropic, 2026-01-09 | yes |
| AI-06 | Equipping agents for the real world with Agent Skills | Anthropic (engineering blog) | https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills | engineering blog | Anthropic, 2025-10-16 | yes |
| AI-07 | Claude Code sandboxing | Anthropic (engineering blog) | https://www.anthropic.com/engineering/claude-code-sandboxing | engineering blog | Anthropic, 2025-10-20 | yes |
| AI-08 | Best practices for Claude Code | Anthropic | https://code.claude.com/docs/en/best-practices (308 redirect from anthropic.com/engineering/claude-code-best-practices) | official doc | Anthropic | yes (same source as ENG-24) |
| AI-09 | Create custom subagents | Anthropic | https://code.claude.com/docs/en/sub-agents | official doc | Anthropic | yes |
| AI-10 | Automate actions with hooks | Anthropic | https://code.claude.com/docs/en/hooks-guide | official doc | Anthropic | yes |
| AI-11 | Claude Code GitHub Actions | Anthropic | https://code.claude.com/docs/en/github-actions | official doc | Anthropic | yes |
| AI-12 | Prompting best practices | Anthropic | https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices (redirect from docs.claude.com) | official doc | Anthropic | yes |
| AI-13 | anthropics/claude-code-action | Anthropic | https://github.com/anthropics/claude-code-action | repo | 9.4k stars, 2.2k forks, MIT | yes |
| AI-14 | anthropics/skills | Anthropic | https://github.com/anthropics/skills | repo | 179.5k stars as reported on the page. Apache 2.0 for most skills; the document skills are source-available | yes |
| AI-15 | anthropics/claude-cookbooks (formerly anthropic-cookbook) | Anthropic | https://github.com/anthropics/anthropic-cookbook (now serves anthropics/claude-cookbooks) | repo | 53.2k stars, 6.4k forks, MIT | yes. Repo overview only; individual notebooks were not fetched |

**Total verified: 33** (16 DESIGN, 2 PROD, 15 AI).

## Guidelines

### 1. Requirements and acceptance criteria (BA, PM, QA)

- **G-REQ-1.** Write acceptance criteria as Gherkin, using these keywords:
  - `Feature`: groups related behaviour.
  - `Rule`: one business rule, since Gherkin v6.
  - `Example`/`Scenario`: a concrete illustration of a rule.
  - `Given` sets the initial context, `When` describes the event, and `Then` describes the expected outcome. [PROD-01]
- **G-REQ-2.** Keep scenarios to about **3 to 5 steps**. A `Background` should be short (about 4 lines at most), and a Feature or Rule can have only one. [PROD-01]
- **G-REQ-3.** `Then` steps assert on **observable outputs**, not on database records. `Given` steps set state and do not describe user interaction. [PROD-01]
- **G-REQ-4.** Use `Scenario Outline` / `Examples` tables for the same behaviour with different data. [PROD-01] Pickleball scoring edge cases are a natural fit: side-out vs rally scoring, server 1 vs server 2, game-point states. (judgment)
- **G-REQ-5.** Write **declarative** scenarios that describe behaviour, not implementation. The test: "Will this wording need to change if the implementation does?" If yes, remove the implementation detail. [PROD-02]
- **G-REQ-6.** Ask only for the information you need, and know why each question is asked. Mark optional fields "(optional)" rather than marking mandatory fields with asterisks. Pre-populate known answers. [DESIGN-12] This applies to onboarding, match setup and player profile forms.
- **G-REQ-7.** State NFRs in measurable terms: response time, throughput, latency, validated by performance tests under varying load. [DESIGN-16] Use percentile targets such as p95: the source does not prescribe them, so this part is (judgment).
- **G-REQ-8.** A self-contained spec names the files and interfaces involved, states what is out of scope, and ends with an end-to-end verification step. [AI-08]

### 2. Human-AI interaction design (Principal Designer, PM)

The product's posture is that every automatic call has a confidence and can be corrected. The 18 HAX guidelines [DESIGN-11] map directly onto it:

- **G-HAI-1.** "Make clear what the system can do" (G1) and "Make clear how well the system can do what it can do" (G2).
- **G-HAI-2.** "Support efficient correction" (G9) and "Support efficient dismissal" (G8).
- **G-HAI-3.** "Make clear why the system did what it did" (G11).
- **G-HAI-4.** "Scope services when in doubt" (G10).
- **G-HAI-5.** "Encourage granular feedback" (G15), "Learn from user behavior" (G13) and "Update and adapt cautiously" (G14).
- **G-HAI-6.** "Convey the consequences of user actions" (G16), "Provide global controls" (G17) and "Notify users about changes" (G18).
- **G-HAI-7.** "Mitigate social biases" (G6) and "Match relevant social norms" (G5).
- **G-HAI-8.** "Time services based on context" (G3) and "Show contextually relevant information" (G4).

### 3. Forms and error handling (Designer, Senior Engineers)

- **G-FORM-1.** Ask **one question per page** for multi-step flows. Put a Back link at the top and label the submit button "Continue". [DESIGN-12]
- **G-FORM-2.** Validation errors:
  - Always show an error summary, even for a single error.
  - Place it at the top of the page, give it the heading "There is a problem", and move keyboard focus to it.
  - Link each entry to the field that has the error.
  - Use the same wording in the summary and at the field.
  - Prefix the page title with "Error:". [DESIGN-13]

### 4. Accessibility (Designer, Engineers, QA). Target: WCAG 2.2 Level AA

- **G-A11Y-1.** Make pointer targets at least **24×24 CSS px**. The exceptions are spacing, an equivalent control, inline targets, user-agent controls and essential presentation (SC 2.5.8, AA). [DESIGN-02]
  - On Android, the platform recommends touch targets of **48dp × 48dp** or larger. [DESIGN-10]
  - Use the larger platform target on touch surfaces. (judgment)
- **G-A11Y-2.** Text contrast must be at least **4.5:1**, or **3:1** for large text (SC 1.4.3, AA). [DESIGN-03]
  - UI components and graphical objects need **3:1** against adjacent colours (SC 1.4.11, AA). [DESIGN-04]
  - SC 1.4.11 covers heatmap colour scales, court-zone overlays and chart marks. (judgment)
- **G-A11Y-3.** Anything that uses dragging must also work with a single pointer without dragging, unless dragging is essential (SC 2.5.7, AA). [DESIGN-05]
- **G-A11Y-4.** Authentication must not require a cognitive function test, such as remembering a password or solving a puzzle, unless an alternative or mechanism is provided (SC 3.3.8, AA). [DESIGN-06]
- **G-A11Y-5.** A focused component must not be entirely hidden by author content such as sticky headers, cookie banners or bottom sheets (SC 2.4.11, AA). [DESIGN-07]
- **G-A11Y-6.** Prerecorded synchronized media needs captions for its audio (SC 1.2.2, A). It also needs audio description or a media alternative for its video (SC 1.2.3, A). [DESIGN-08, DESIGN-09]
- **G-A11Y-7.** Content descriptions:
  - Describe purpose and result, not visuals.
  - Don't repeat the role ("Submit", not "Submit button").
  - Make each description unique within a list.
  - Hide purely decorative elements from assistive technology. [DESIGN-10]
- **G-A11Y-8.** Combine automated tools (axe-core / Accessibility Insights) with manual testing, because tooling alone is not enough. [DESIGN-14]

### 5. Design reviews (Principal Designer, Principal Engineer)

- **G-DR-1.** Hold design reviews **before implementation** to keep the cost of change low.
  - Keep design docs, decision logs and trade studies in the repo, and review them as PRs, which allows asynchronous review.
  - Bring in domain experts as well as developers.
  - "Disagree and commit" when consensus stalls. [DESIGN-15]

### 6. Agent architecture and orchestration (EM, Principal Engineer)

- **G-AG-1.** Start simple. Prefer **workflows**, which are predefined code paths, for well-defined tasks. Use **agents** only for open-ended problems whose steps cannot be hardcoded, and test them in a sandbox with guardrails. [AI-01]
  - The named patterns are prompt chaining, routing, parallelization, orchestrator-workers and evaluator-optimizer. [AI-01]
- **G-AG-2.** Be transparent: show the agent's planning steps. Put as much effort into the agent-computer interface (tool docs, examples, poka-yoke) as into a human interface. [AI-01]
- **G-AG-3.** Orchestrator-worker setup:
  - The lead agent gives each subagent an objective, an output format, tool guidance and boundaries, so their work does not overlap. [AI-02]
  - Scale effort to complexity: a simple task needs one agent with 3 to 10 tool calls, and complex work may need 10 or more subagents. [AI-02]
- **G-AG-4.** Multi-agent systems used about **15× the tokens of chat** in Anthropic's measurement. Budget for this, and use multi-agent only where the task's value justifies it. [AI-02]
- **G-AG-5.** Build resumable execution with checkpoints instead of full restarts, let agents adapt to tool failures, and monitor decision patterns. [AI-02]
- **G-AG-6.** Subagent definitions:
  - Store them as Markdown with YAML frontmatter in `.claude/agents/`, checked into version control.
  - `name` and `description` are required. `tools`, `model`, `permissionMode`, `memory`, `maxTurns`, `skills` and `mcpServers` are optional. [AI-09]
  - Give each one a single responsibility, an allowlist of tools, and a specific system prompt.
  - Write a `description` that says when to delegate. Adding "use proactively" encourages automatic delegation. [AI-09]
- **G-AG-7.** Choose the model by task complexity, for example a cheaper model for log analysis and a stronger one for architecture. Use `permissionMode: plan` for planner agents that must not edit. [AI-09]
- **G-AG-8.** Skills (`SKILL.md` with a required `name` and `description`) load by **progressive disclosure**: metadata first, then the body, then referenced files. Use skills for domain knowledge that is needed only sometimes. Use CLAUDE.md for rules that apply broadly. [AI-06, AI-08, AI-14]

### 7. Context and prompt engineering (all agents)

- **G-CTX-1.** Treat context as a finite budget ("context rot"). Aim for "the smallest possible set of high-signal tokens". Retrieve information just in time, using lightweight identifiers. For long tasks, use compaction, structured notes and sub-agents. [AI-04]
- **G-CTX-2.** CLAUDE.md:
  - Keep it short. For each line, ask "Would removing this cause Claude to make mistakes?"
  - Include commands, style rules that differ from defaults, test instructions, repo etiquette and architectural decisions.
  - Leave out anything derivable from the code. [AI-08]
- **G-CTX-3.** Explain *why* an instruction matters. Use XML tags to separate instructions, context and inputs. Treat Claude as a "brilliant but new employee". [AI-12]
- **G-CTX-4.** Work that spans several context windows:
  - Write tests first and track them in a structured file such as `tests.json`. Tell the agent it is "unacceptable to remove or edit tests".
  - Keep free-text progress notes in `progress.txt`, and use git as the state log.
  - Provide an `init.sh` script.
  - When a session starts fresh, review progress, tests and the git log before starting new features. [AI-12]
- **G-CTX-5.** "Never speculate about code you have not opened." Prompt against over-engineering by asking the agent to change only what was requested. [AI-12]
- **G-CTX-6.** Explore, plan, implement, commit. If the diff can be described in one sentence, skip the plan. After two failed corrections, clear the context and write a better prompt. [AI-08]

### 8. Verification, review and auto-fix loops (QA, EM)

- **G-VER-1.** Give each agent a check it can run, such as tests, a build, a linter or a screenshot diff. Ask it to show **evidence** (the command and its output) rather than claim success. [AI-08]
- **G-VER-2.** Add an adversarial review: a **fresh-context subagent** reviews the diff against the plan. Its context should not include the implementer's reasoning. [AI-08]
  - Tell the reviewer to flag only gaps that affect correctness or the stated requirements, so that the fixes do not over-engineer the code. [AI-08]
- **G-VER-3.** Use a Writer/Reviewer split. For tests, one agent writes the tests and another writes the code that makes them pass. [AI-08]
- **G-VER-4.** Hooks are **deterministic**; CLAUDE.md is advisory. Use hooks for actions that must always happen:
  - **PostToolUse:** format or lint after `Edit|Write`.
  - **PreToolUse:** block protected paths or dangerous commands. Exit code 2 denies the call, and when several hooks disagree, the most restrictive answer wins.
  - **Stop:** gate the end of a turn on a passing check.
  - **ConfigChange:** keep an audit log.
  - A PreToolUse hook can also append every Bash command to a log. [AI-10]
- **G-VER-5.** CI review through `anthropics/claude-code-action@v1` [AI-11, AI-13]:
  - Put review standards in CLAUDE.md.
  - Store keys as GitHub Secrets only and grant the workflow the fewest permissions it needs.
  - Cap runs with `--max-turns`, workflow timeouts and concurrency controls.
  - Only actors with write access can trigger runs, and bots are rejected unless listed in `allowed_bots`, which prevents trigger loops.
- **G-VER-6.** Sandbox autonomous agents at **two boundaries**: the filesystem and the network. Without both, a prompt-injected agent can exfiltrate data or escape its restrictions. [AI-07]

### 9. Tools and evals for the in-product coaching LLM (Principal Engineer, QA)

- **G-TOOL-1.** Tool design:
  - Expose a few task-specific tools rather than wrappers around every endpoint.
  - Namespace them with consistent prefixes.
  - Return human-readable identifiers, not opaque UUIDs.
  - Paginate, filter and truncate with sensible defaults. For reference, Claude Code caps tool responses at 25,000 tokens by default.
  - Write tool descriptions as if onboarding a new teammate. [AI-03]
- **G-EVAL-1.** Start evals early with **20 to 50 realistic tasks** taken from real failures. [AI-05] Anthropic's research system started with about 20 queries. [AI-02]
- **G-EVAL-2.** Combine three kinds of grader [AI-05]:
  - Code graders are fast and objective but brittle.
  - Model graders (LLM-as-judge, scoring against a rubric) need calibration against human judgment.
  - Human graders are the gold standard but slow.
- **G-EVAL-3.** Track **pass@k** (at least one success in k tries) and **pass^k** (all k tries succeed, which measures consistency). Read transcripts regularly. An eval at 100% only catches regressions. Build evals before the capability exists. [AI-05]
- **G-EVAL-4.** LLM-as-judge rubric dimensions used by Anthropic: factual accuracy, citation accuracy, completeness, source quality and tool efficiency. Add human review to catch hallucinations. [AI-02]

## Implications for racket-analytics

1. **Requirements format (BA, QA).**
   - Every user story in `docs/requirements/` carries Gherkin acceptance criteria: declarative, 3 to 5 steps, and `Then` asserting on outputs the user can see [PROD-01, PROD-02].
   - The pickleball rules engine (M0) gets a `Rule:` per scoring rule and `Scenario Outline` tables for score states. These become executable tests (pytest-bdd or similar). (judgment)
   - The video pipeline's accuracy targets come from the spec (≥90% of rallies segmented in M2, ≤1 correction per game in M3). They become NFR scenarios checked against a labelled test set, not single-run asserts. (judgment)
2. **Confidence and correction UX (Designer).** HAX [DESIGN-11] becomes a design checklist for the review timeline:
   - Show a confidence for every automatic shot, bounce and score call (G2).
   - Make correction one tap, with keyboard support (G9).
   - Each training-plan drill shows its "why", linked to the metric and clips (G11; this matches spec §6).
   - When the sample is too small, mark the metric as low-sample instead of asserting it (G10; matches spec §5).
   - Record corrections as granular feedback and training data (G13, G15).
   - Change models cautiously and tell users when re-processing changes past stats (G14, G18).
   - Avoid bias when describing player tendencies: no face recognition, and identity is assigned by the user (G6; matches spec §8). (judgment on mapping)
3. **Accessibility NFRs (Designer, QA).** The baseline NFR is **WCAG 2.2 AA** [DESIGN-01]. The concrete, testable rules:
   - 24×24 CSS px minimum targets, raised to 48dp-equivalent on touch screens [DESIGN-02, DESIGN-10].
   - 4.5:1 text contrast, and 3:1 for heatmaps, court overlays and chart marks [DESIGN-03, DESIGN-04]. Heatmaps also need a non-colour encoding such as values or patterns. (judgment)
   - Calibration currently means dragging 4 corner handles, so it needs a non-drag alternative: tap to select a corner, then arrow keys or tap to place it [DESIGN-05].
   - Login must not depend on a memorised password alone: support passkeys or magic links and allow password managers [DESIGN-06].
   - Sticky video controls and bottom sheets must not hide focused elements [DESIGN-07].
   - In-app tutorial and capture-guide videos need captions [DESIGN-08, DESIGN-09].
   - The player's own match footage is user-generated. Whether SC 1.2.x applies to it is an open question. Our recommendation is to provide the rally/score timeline as the text alternative. (judgment)
   - CI runs axe-core on every PR, and QA does a manual screen-reader pass each sprint [DESIGN-14].
4. **Upload and setup flows (Designer, Engineers).**
   - Match setup follows the one-question-per-page pattern: sport, format, scoring system, players, then upload [DESIGN-12].
   - Upload and quality-check failures use the error-summary pattern [DESIGN-13].
5. **Design governance (Principal Designer, Principal Engineer).**
   - Each milestone's UX and architecture gets a design review *before* the sprint's implementation starts.
   - The review is held as a PR on `docs/decisions/` (ADRs) and must include the domain coach as an SME reviewer [DESIGN-15].
6. **Agent team structure (EM).**
   - Implement each role as a single-responsibility subagent in `.claude/agents/<role>.md` with an allowlisted `tools` list [AI-09]:
     - The PM, BA and Designer agents get read and write access to docs only.
     - The Principal Engineer runs with `permissionMode: plan` for design work.
     - Senior Engineers get edit and Bash access inside a sandbox [AI-07].
     - QA gets test-running tools.
   - Use orchestrator-workers, with the EM as orchestrator, only where parallel work pays for the roughly 15× token cost [AI-02]. Sprint ceremonies should otherwise be fixed **workflows**, not free-form agents [AI-01].
   - Domain knowledge (pickleball rules, the drill taxonomy) goes into skills, which load progressively. CLAUDE.md stays short [AI-06, AI-08].
7. **Auto-review, auto-fix and decision logging (EM, QA).**
   - **Hooks:**
     - PostToolUse runs the formatter and linter.
     - PreToolUse blocks writes to `.env`, migrations and secrets, and logs every Bash command to an audit file.
     - A Stop hook gates on tests passing [AI-10].
   - **Fresh-context review:** a reviewer subagent checks each diff against the sprint plan and flags only gaps that affect correctness or requirements [AI-08].
   - **CI:** `claude-code-action@v1` runs the PR review with minimal permissions, `--max-turns`, timeouts and concurrency limits, and with bots blocked from triggering it [AI-11, AI-13].
   - **Evidence:** agents must show the command and output as evidence in every decision record [AI-08]. ADRs carry the evidence links (see the ADR sources in engineering-process.md).
   - **State:** each sprint keeps a `tests.json`-style status file and a progress note, and relies on git history [AI-12].
8. **Coaching LLM (Principal Engineer, QA).**
   - **Workflow shape:** the coaching service is a workflow, not an agent: a rules layer ranks weaknesses, then one LLM call picks drills from the library (a prompt chain) [AI-01]. This matches spec §2, which says the LLM selects drills and does not invent them.
   - **Tools:** expose namespaced tools such as `drills_search` and `metrics_get`. They return human-readable drill names and paginated, truncated results [AI-03].
   - **Evals:** build the coaching eval set (20 to 50 player profiles drawn from real tagged matches) *before* M5. [AI-05]
     - A code grader checks that every drill exists in the library and links to a metric.
     - A model grader scores relevance and clarity against a rubric, calibrated by the domain coach.
     - Track pass^k for consistency [AI-05].
9. **Prompt hygiene for every agent.**
   - Explain the "why" and use XML-tagged sections [AI-12].
   - Do not speculate about unread code [AI-12].
   - Clear context after two failed corrections [AI-08].
   - Measure context and keep tool outputs small [AI-04].

## Gaps / unverified

| Item | Status | Why / workaround |
|---|---|---|
| Nielsen Norman Group: 10 Usability Heuristics | **Unverified** | www.nngroup.com is blocked by the egress proxy. It is not cited above. HAX [DESIGN-11] and GOV.UK [DESIGN-12, DESIGN-13] cover the overlapping ground. |
| W3C site (w3.org/TR/WCAG22) and the W3C "Understanding" pages | Partially verified | w3.org is blocked. The normative SC text was fetched from the W3C's own `w3c/wcag` repo instead. The exact Recommendation publication date was not confirmed from the fetched text. |
| Apple Human Interface Guidelines (accessibility, 44pt targets) | **Unverified** | The page fetched, but its body was a JavaScript shell with no content. A first summarizer pass returned generic text that could not be traced to the page, so it was discarded. The 44pt figure is **not** cited. |
| Material Design 3 (m3.material.io) | **Unverified** | Blocked. Android Developers [DESIGN-10] is used for the 48dp guidance instead. |
| INVEST (Bill Wake; Agile Alliance glossary) | **Unverified** | xp123.com and agilealliance.org are blocked. Teams may still use INVEST as a checklist, but it is (judgment), not cited. |
| MoSCoW prioritisation (DSDM / Agile Business Consortium) | **Unverified** | agilebusiness.org is blocked. Its use for MVP scoping is (judgment). |
| Jobs-to-be-Done (Christensen et al., HBR 2016; Christensen Institute) | **Unverified** | hbr.org and christenseninstitute.org are blocked. |
| Dan North "What's in a story?"; Mike Cohn user stories | **Unverified** | Both hosts are blocked. The Gherkin rules rely on PROD-01 and PROD-02 only. |
| Google PAIR People + AI Guidebook | **Unverified** | pair.withgoogle.com is blocked. HAX [DESIGN-11] used instead. |
| Google HEART framework paper (Rodden et al.) | **Unverified** | research.google is blocked. Product metrics framework still to be sourced. |
| ISO/IEC 25010 quality model | **Unverified** | iso.org is blocked. The NFR categories rely on the Microsoft playbook [DESIGN-14, DESIGN-16] and (judgment). |
| GOV.UK Service Standard; web.dev tap targets | **Unverified** | gov.uk and web.dev are blocked. |
| HAX CHI 2019 paper (Amershi et al.) full text | Not fetched | Only Microsoft's guideline library and project pages were fetched. |
| Microsoft playbook NFR index (`docs/non-functional-requirements/README.md`) | Fetch failed (404) | The individual NFR pages fetched fine. |
| Primer design system (github.com/primer/design) | Fetched, not used | The repo is archived (2025-07-07) and only its metadata was fetched. |
| Percentile-based latency targets (p95/p99) | No source | DESIGN-16 does not specify them, so any targets we set are (judgment). |
| Claude cookbooks individual notebooks | Not fetched | Only the repo overview [AI-15] was fetched. |
