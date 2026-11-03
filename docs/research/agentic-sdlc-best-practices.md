# Agentic SDLC Best Practices: Sources and Practices

- **Status:** DRAFT for the product owner to read. Nothing in this file is approved, and no practice here is adopted until the PO says so.
- **Research date:** 2026-10-31 (six researchers, read-only). Independent fact-check after that. Live link check: 2026-11-03.
- **Citation prefix:** `ASB`. Cite a source as `[ASB/<ID>]`, for example [ASB/ANT-01]. See the citation table in `docs/process/working-agreement.md` §0.
- **Product context:** `docs/specs/2026-10-02-racket-analytics-design.md`. PO decisions are in `docs/requirements/po-input-2026-10-05.md` and take precedence over anything here.

## 1. Purpose

This file is the source register for the 2026-10-31 audit of the team's role files (`.claude/agents/*.md`) and process docs. It answers three questions:

1. Which sources do the corrected docs cite? (§3 and §4)
2. How was each source checked, and how can anyone check it again? (§2)
3. Which practices do the sources support, and how strong is each one? (§5)

It holds 173 sources in six groups. 137 are **Confirmed**, 2 were marked verified by the researcher but **Not confirmed** by the fact-checker, and 34 are **Unverified** (mostly because the host was blocked). It also lists 134 practices.

Source IDs are local to this file. `ANT-05` here is not the same as any ID in EP, AQS, DPA or DOM, which is why the `ASB/` prefix is mandatory.

## 2. How sources were verified

### 2.1 Three checks

1. **Researcher check (2026-10-31).** The researcher opened each page and read it. Pages were opened with WebFetch, curl, raw.githubusercontent.com, or a git clone of the publisher's own source repository when the website host was blocked (for example `dora-team/dora.dev`, `google/eng-practices`, `vercel/next.js` docs, `OWASP/CheatSheetSeries`). A source was marked *verified* only if its key point was on the page. Sources found only through web search were marked *not verified*.
2. **Independent fact-check.** A separate fact-checker re-opened every verified source and confirmed or rejected each key point, usually with line numbers and quotes. It also recorded redirects, overstatements and nuances. Its notes are reproduced in §4.
3. **Live link check (2026-11-03).** Every URL was requested again from the build container. The result is in the *Live check* column:
   - `200` means the URL answered.
   - `403` or `000` means the container's network policy blocked it. That does not mean the page is gone.
   - `github.com` web pages (`/blob/...`) answer `403` here, while raw and git access to the same files works. Those sources were read through raw or git.

### 2.2 Status values used in §3

| Status | Meaning | May it be cited as evidence? |
|---|---|---|
| Confirmed | The researcher marked it verified and the fact-checker confirmed the key points. | Yes, as `[ASB/<ID>]`. Mind any nuance in the fact-check note (§4). |
| Not confirmed: reason | The researcher marked it verified, but the fact-checker rejected one or more key points. | Only for the points the fact-checker confirmed; everything else is cited with **(unverified)**. |
| Unverified: reason | The page was not read (blocked host, paywall, book) or was seen only in search results. | Only as `[ASB/<ID>] (unverified)`. Never as a fact. |

A redirected URL counts as *not fetched* under the fact-check rule, so those rows say where the content was actually checked. Anthropic `/engineering/...` URLs now redirect (301 or 308) to the same path under `/research/...`. Cite the `/research/` URL in new text.

### 2.3 How to check a source yourself

1. Find the ID in §3 and open the URL.
2. If it is a `github.com/<owner>/<repo>/blob/<branch>/<path>` link and the page is blocked, open `https://raw.githubusercontent.com/<owner>/<repo>/<branch>/<path>` instead. It is the same file.
3. Read the key points and the fact-checker's note in §4. Search the page for the quoted words. Line numbers in the notes refer to the text the checker fetched (often the Markdown source), so they shift when a page changes. The quotes are the stable part.
4. To repeat the live check for one URL: `curl -sS -o /dev/null -w '%{http_code}\n' <URL>`. A `000` or `403` from inside the container usually means the host is not on the allowed network list (see §6.1), not that the page is dead.
5. If a point is no longer on the page, change the row's status in this file in the same PR that relies on it, and add **(unverified)** to every citation of that point.

### 2.4 What verification does not prove

- It proves the page says what we quote. It does not prove the advice is right for this project.
- Many sources are vendor or tool documentation (Anthropic, GitHub spec-kit, Microsoft playbook). Their advice is the vendor's opinion, even when it is official for that vendor's tool.
- Pages change. The check is a snapshot from 2026-10-31 to 2026-11-03.
- The Scrum Guide row (ASB/AGL-01) was read from a third-party verbatim mirror, not scrumguides.org, so it is marked not official.

### 2.5 Same URL under several IDs

Six researchers worked in parallel, so some pages appear under more than one ID. Each ID keeps its own researcher's key points (§4), so cite the ID whose key point you rely on.

| URL | IDs |
|---|---|
| https://code.claude.com/docs/en/sub-agents | ASB/ANT-01, ASB/RPD-01, ASB/REN-39 |
| https://code.claude.com/docs/en/best-practices | ASB/ANT-08, ASB/SDD-24 |
| https://www.anthropic.com/engineering/multi-agent-research-system | ASB/ANT-12, ASB/AGL-14, ASB/RPD-02 |
| https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents | ASB/ANT-16, ASB/SDD-26, ASB/AGL-15, ASB/REQ-21 |
| https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices | ASB/ANT-21, ASB/RPD-04 |
| https://raw.githubusercontent.com/github/spec-kit/main/spec-driven.md | ASB/SDD-01, ASB/REQ-08 |
| https://raw.githubusercontent.com/github/spec-kit/main/templates/spec-template.md | ASB/SDD-02, ASB/REQ-07 |
| https://raw.githubusercontent.com/github/spec-kit/main/templates/commands/specify.md | ASB/SDD-05, ASB/REQ-10 |
| https://raw.githubusercontent.com/github/spec-kit/main/templates/commands/analyze.md | ASB/SDD-07, ASB/REQ-09 |
| https://raw.githubusercontent.com/cucumber/docs/main/content/docs/bdd/_index.md | ASB/SDD-20, ASB/REQ-06 |
| https://raw.githubusercontent.com/cucumber/docs/main/content/docs/bdd/example-mapping.md | ASB/SDD-21, ASB/REQ-03, ASB/RPD-16 |
| https://raw.githubusercontent.com/cucumber/docs/main/content/docs/bdd/who-does-what.md | ASB/SDD-22, ASB/REQ-05, ASB/RPD-17 |
| https://raw.githubusercontent.com/cucumber/docs/main/content/docs/bdd/discovery-workshop.md | ASB/SDD-23, ASB/REQ-04 |
| https://alistairmavin.com/ears | ASB/SDD-27, ASB/REQ-22 |
| https://raw.githubusercontent.com/microsoft/code-with-engineering-playbook/main/docs/agile-development/team-agreements/definition-of-ready.md | ASB/AGL-08, ASB/REQ-16, ASB/RPD-13 |
| https://raw.githubusercontent.com/microsoft/code-with-engineering-playbook/main/docs/agile-development/ceremonies.md | ASB/AGL-09, ASB/RPD-12 |
| https://raw.githubusercontent.com/microsoft/code-with-engineering-playbook/main/docs/agile-development/backlog-management.md | ASB/AGL-12, ASB/REQ-18, ASB/RPD-14 |
| https://cloud.google.com/blog/products/devops-sre/sre-fundamentals-slis-slas-and-slos | ASB/REQ-12, ASB/REN-07 |
| https://sre.google/sre-book/service-level-objectives | ASB/REQ-25, ASB/REN-09 |

## 3. Source register

### 3.1 ANT: Anthropic guidance for agent teams on Claude Code

28 sources, 27 confirmed.

| ID | Title | Publisher | URL | Official? | Status | Live check 2026-11-03 |
|---|---|---|---|---|---|---|
| ASB/ANT-01 | Create custom subagents (Claude Code docs) | Anthropic | https://code.claude.com/docs/en/sub-agents | yes | Confirmed | 200 reachable |
| ASB/ANT-02 | How Claude remembers your project (CLAUDE.md / memory docs) | Anthropic | https://code.claude.com/docs/en/memory | yes | Confirmed | 200 reachable |
| ASB/ANT-03 | Hooks reference (Claude Code docs) | Anthropic | https://code.claude.com/docs/en/hooks | yes | Not confirmed: the fact-checker found the event list and the deny / exit-code-2 blocking on the page, but not 'hooks run deterministically' (that framing is from ASB/ANT-08 and ASB/ANT-02, and prompt or subagent hooks are not deterministic) and not 'plugin subagents ignore the hooks field' (that is on ASB/ANT-01). Cite this page only for the event list and the blocking mechanism | 200 reachable |
| ASB/ANT-04 | Settings files and precedence (Claude Code docs) | Anthropic | https://code.claude.com/docs/en/settings | yes | Confirmed | 200 reachable |
| ASB/ANT-05 | Configure permissions (Claude Code docs) | Anthropic | https://code.claude.com/docs/en/permissions | yes | Confirmed | 200 reachable |
| ASB/ANT-06 | Extend Claude with skills (Claude Code docs; slash commands merged here) | Anthropic | https://code.claude.com/docs/en/skills | yes | Confirmed | 200 reachable |
| ASB/ANT-07 | Run Claude Code programmatically (headless docs) | Anthropic | https://code.claude.com/docs/en/headless | yes | Confirmed | 200 reachable |
| ASB/ANT-08 | Best practices for Claude Code (docs page; the engineering-blog URL /engineering/claude-code-best-practices now serves this page) | Anthropic | https://code.claude.com/docs/en/best-practices | yes | Confirmed | 200 reachable |
| ASB/ANT-09 | Orchestrate teams of Claude Code sessions (agent teams docs) | Anthropic | https://code.claude.com/docs/en/agent-teams | yes | Confirmed | 200 reachable |
| ASB/ANT-10 | Subagents in the Agent SDK | Anthropic | https://code.claude.com/docs/en/agent-sdk/subagents | yes | Confirmed | 200 reachable |
| ASB/ANT-11 | Building effective agents | Anthropic Engineering | https://www.anthropic.com/engineering/building-effective-agents | yes | Confirmed (the cited URL redirects; content checked at the redirect target) | 200 reachable |
| ASB/ANT-12 | How we built our multi-agent research system | Anthropic Engineering | https://www.anthropic.com/engineering/multi-agent-research-system | yes | Confirmed (the cited URL redirects; content checked at the redirect target) | 200 reachable |
| ASB/ANT-13 | Effective context engineering for AI agents | Anthropic Engineering | https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents | yes | Confirmed (the cited URL redirects; content checked at the redirect target) | 200 reachable |
| ASB/ANT-14 | Writing effective tools for agents — with agents | Anthropic Engineering | https://www.anthropic.com/engineering/writing-tools-for-agents | yes | Confirmed (the cited URL redirects; content checked at the redirect target) | 200 reachable |
| ASB/ANT-15 | Equipping agents for the real world with Agent Skills | Anthropic Engineering | https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills | yes | Confirmed (the cited URL redirects; content checked at the redirect target) | 200 reachable |
| ASB/ANT-16 | Effective harnesses for long-running agents | Anthropic Engineering | https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents | yes | Confirmed (the cited URL redirects; content checked at the redirect target) | 200 reachable |
| ASB/ANT-17 | Demystifying evals for AI agents | Anthropic Engineering | https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents | yes | Confirmed (the cited URL redirects; content checked at the redirect target) | 200 reachable |
| ASB/ANT-18 | Harness design for long-running application development | Anthropic Engineering | https://www.anthropic.com/engineering/harness-design-long-running-apps | yes | Confirmed (the cited URL redirects; content checked at the redirect target) | 200 reachable |
| ASB/ANT-19 | Building a C compiler with a team of parallel Claudes | Anthropic Engineering | https://www.anthropic.com/engineering/building-c-compiler | yes | Confirmed (the cited URL redirects; content checked at the redirect target) | 200 reachable |
| ASB/ANT-20 | An update on recent Claude Code quality reports (Apr 23, 2026 postmortem) | Anthropic Engineering | https://www.anthropic.com/engineering/april-23-postmortem | yes | Confirmed (the cited URL redirects; content checked at the redirect target) | 200 reachable |
| ASB/ANT-21 | Prompting best practices (Claude API docs; former be-clear-and-direct, multishot, XML-tags, system-prompt/role and long-context pages now redirect here) | Anthropic | https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices | yes | Confirmed | 200 reachable |
| ASB/ANT-22 | Prompting Claude Opus 5 | Anthropic | https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-5 | yes | Confirmed | 200 reachable |
| ASB/ANT-23 | Skill authoring best practices (Claude API docs) | Anthropic | https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices | yes | Confirmed | 200 reachable |
| ASB/ANT-24 | anthropics/skills — skill-creator SKILL.md | Anthropic (GitHub) | https://raw.githubusercontent.com/anthropics/skills/main/skills/skill-creator/SKILL.md | yes | Confirmed | 200 reachable |
| ASB/ANT-25 | anthropics/claude-plugins-official — feature-dev code-reviewer and code-explorer agents | Anthropic (GitHub) | https://raw.githubusercontent.com/anthropics/claude-plugins-official/main/plugins/feature-dev/agents/code-reviewer.md | yes | Confirmed | 200 reachable |
| ASB/ANT-26 | anthropics/claude-code plugins/README.md | Anthropic (GitHub) | https://raw.githubusercontent.com/anthropics/claude-code/main/plugins/README.md | yes | Confirmed | 200 reachable |
| ASB/ANT-27 | anthropics/claude-code-action README | Anthropic (GitHub) | https://raw.githubusercontent.com/anthropics/claude-code-action/main/README.md | yes | Confirmed | 200 reachable |
| ASB/ANT-28 | anthropics/anthropic-cookbook README (redirects to claude-cookbooks) | Anthropic (GitHub) | https://raw.githubusercontent.com/anthropics/anthropic-cookbook/main/README.md | yes | Confirmed | 200 reachable |

### 3.2 SDD: Spec-driven development, BDD and ADRs

28 sources, 21 confirmed.

| ID | Title | Publisher | URL | Official? | Status | Live check 2026-11-03 |
|---|---|---|---|---|---|---|
| ASB/SDD-01 | Specification-Driven Development (SDD) - spec-driven.md | GitHub (github/spec-kit) | https://raw.githubusercontent.com/github/spec-kit/main/spec-driven.md | yes | Confirmed | 200 reachable |
| ASB/SDD-02 | spec-kit spec-template.md (Feature Specification template) | GitHub (github/spec-kit) | https://raw.githubusercontent.com/github/spec-kit/main/templates/spec-template.md | yes | Confirmed | 200 reachable |
| ASB/SDD-03 | spec-kit plan-template.md (Implementation Plan template) | GitHub (github/spec-kit) | https://raw.githubusercontent.com/github/spec-kit/main/templates/plan-template.md | yes | Confirmed | 200 reachable |
| ASB/SDD-04 | spec-kit tasks-template.md (Task list template) | GitHub (github/spec-kit) | https://raw.githubusercontent.com/github/spec-kit/main/templates/tasks-template.md | yes | Confirmed | 200 reachable |
| ASB/SDD-05 | spec-kit /specify command definition | GitHub (github/spec-kit) | https://raw.githubusercontent.com/github/spec-kit/main/templates/commands/specify.md | yes | Confirmed | 200 reachable |
| ASB/SDD-06 | spec-kit /clarify command definition | GitHub (github/spec-kit) | https://raw.githubusercontent.com/github/spec-kit/main/templates/commands/clarify.md | yes | Confirmed | 200 reachable |
| ASB/SDD-07 | spec-kit /analyze command definition | GitHub (github/spec-kit) | https://raw.githubusercontent.com/github/spec-kit/main/templates/commands/analyze.md | yes | Confirmed | 200 reachable |
| ASB/SDD-08 | spec-kit constitution-template.md | GitHub (github/spec-kit) | https://raw.githubusercontent.com/github/spec-kit/main/templates/constitution-template.md | yes | Confirmed | 200 reachable |
| ASB/SDD-09 | spec-kit /constitution command definition | GitHub (github/spec-kit) | https://raw.githubusercontent.com/github/spec-kit/main/templates/commands/constitution.md | yes | Not confirmed: the semver rules and the Governance-section rule are on the page, but the claim that the Sync Impact Report lists dependent templates to update is not; the page says dependent templates are not modified, and the report is temporary scratch material removed before commit | 200 reachable |
| ASB/SDD-10 | spec-kit /implement command definition | GitHub (github/spec-kit) | https://raw.githubusercontent.com/github/spec-kit/main/templates/commands/implement.md | yes | Confirmed | 200 reachable |
| ASB/SDD-11 | spec-kit README | GitHub (github/spec-kit) | https://raw.githubusercontent.com/github/spec-kit/main/README.md | yes | Confirmed | 200 reachable |
| ASB/SDD-12 | Kiro README (kirodotdev/Kiro) | Kiro (AWS) | https://raw.githubusercontent.com/kirodotdev/Kiro/main/README.md | yes | Confirmed | 200 reachable |
| ASB/SDD-13 | Kiro docs - Specs | Kiro (AWS) | https://kiro.dev/docs/specs/ | yes | Unverified: kiro.dev blocked in the research session; not fetched | 000 (no connection from the container; blocked, not necessarily dead) |
| ASB/SDD-14 | Understanding Spec-Driven-Development: Kiro, spec-kit, and Tessl (Birgitta Böckeler) | martinfowler.com | https://martinfowler.com/articles/exploring-gen-ai/sdd-3-tools.html | no | Unverified: martinfowler.com blocked; content seen only in search results | 000 (no connection from the container; blocked, not necessarily dead) |
| ASB/SDD-15 | Thoughtworks Technology Radar - Spec-driven development | Thoughtworks | https://www.thoughtworks.com/radar/techniques/spec-driven-development | no | Unverified: thoughtworks.com blocked; not fetched | 000 (no connection from the container; blocked, not necessarily dead) |
| ASB/SDD-16 | Documenting Architecture Decisions (Michael Nygard, 2011) | Cognitect | https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions | no | Unverified: cognitect.com blocked; not fetched | 000 (no connection from the container; blocked, not necessarily dead) |
| ASB/SDD-17 | adr-tools ADR template (Nygard format) | npryce/adr-tools | https://raw.githubusercontent.com/npryce/adr-tools/master/src/template.md | no | Confirmed | 200 reachable |
| ASB/SDD-18 | adr-tools ADR 0001 Record architecture decisions | npryce/adr-tools | https://raw.githubusercontent.com/npryce/adr-tools/master/doc/adr/0001-record-architecture-decisions.md | no | Confirmed | 200 reachable |
| ASB/SDD-19 | adr.github.io - Architectural Decision Records (index.md source) | GitHub adr organization | https://raw.githubusercontent.com/adr/adr.github.io/main/index.md | yes | Confirmed | 200 reachable |
| ASB/SDD-20 | Cucumber docs - Behaviour-Driven Development | Cucumber | https://raw.githubusercontent.com/cucumber/docs/main/content/docs/bdd/_index.md | yes | Confirmed | 200 reachable |
| ASB/SDD-21 | Cucumber docs - Example Mapping | Cucumber | https://raw.githubusercontent.com/cucumber/docs/main/content/docs/bdd/example-mapping.md | yes | Confirmed | 200 reachable |
| ASB/SDD-22 | Cucumber docs - Who Does What? (Three Amigos) | Cucumber | https://raw.githubusercontent.com/cucumber/docs/main/content/docs/bdd/who-does-what.md | yes | Confirmed | 200 reachable |
| ASB/SDD-23 | Cucumber docs - Discovery workshop | Cucumber | https://raw.githubusercontent.com/cucumber/docs/main/content/docs/bdd/discovery-workshop.md | yes | Confirmed | 200 reachable |
| ASB/SDD-24 | Best practices for Claude Code | Anthropic | https://code.claude.com/docs/en/best-practices | yes | Confirmed | 200 reachable |
| ASB/SDD-25 | Common workflows - Plan before editing | Anthropic | https://code.claude.com/docs/en/common-workflows | yes | Confirmed | 200 reachable |
| ASB/SDD-26 | Effective harnesses for long-running agents | Anthropic | https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents | yes | Confirmed (the cited URL redirects; content checked at the redirect target) | 200 reachable |
| ASB/SDD-27 | EARS - Easy Approach to Requirements Syntax (Alistair Mavin) | Alistair Mavin | https://alistairmavin.com/ears/ | no | Unverified: alistairmavin.com blocked; not fetched | 000 (no connection from the container; blocked, not necessarily dead) |
| ASB/SDD-28 | Specification by Example (Gojko Adzic) | Gojko Adzic | https://gojko.net/books/specification-by-example/ | no | Unverified: gojko.net blocked; not fetched, no claims drawn from it | 000 (no connection from the container; blocked, not necessarily dead) |

### 3.3 AGL: Agile project management, flow and DORA

20 sources, 15 confirmed.

| ID | Title | Publisher | URL | Official? | Status | Live check 2026-11-03 |
|---|---|---|---|---|---|---|
| ASB/AGL-01 | The Scrum Guide (November 2020), diffable Markdown copy | Ken Schwaber and Jeff Sutherland (CC BY-SA 4.0 text), mirrored on GitHub by alexandreaquiles. scrumguides.org and scrum.org are blocked in this session, so this is a third-party verbatim mirror, not the official host. | https://raw.githubusercontent.com/alexandreaquiles/scrum-guide/master/README.md | no | Confirmed | 200 reachable |
| ASB/AGL-02 | DORA's software delivery performance metrics (dora.dev guide, source file) | DORA (Google Cloud), Nathen Harvey; updated 2026-01-05 | https://raw.githubusercontent.com/dora-team/dora.dev/main/hugo/content/guides/dora-metrics/_index.md | yes | Confirmed | 200 reachable |
| ASB/AGL-03 | A history of DORA's software delivery metrics | DORA, Nathen Harvey, 2026-01-02 | https://raw.githubusercontent.com/dora-team/dora.dev/main/hugo/content/insights/dora-metrics-history/index.md | yes | Confirmed | 200 reachable |
| ASB/AGL-04 | Capabilities: Working in small batches | DORA; updated 2025-12-08 | https://raw.githubusercontent.com/dora-team/dora.dev/main/hugo/content/capabilities/working-in-small-batches/index.md | yes | Confirmed | 200 reachable |
| ASB/AGL-05 | Capabilities: Streamlining change approval | DORA; updated 2025-10-30 | https://raw.githubusercontent.com/dora-team/dora.dev/main/hugo/content/capabilities/streamlining-change-approval/index.md | yes | Confirmed | 200 reachable |
| ASB/AGL-06 | Capabilities: Work-in-process limits | DORA | https://raw.githubusercontent.com/dora-team/dora.dev/main/hugo/content/capabilities/wip-limits/index.md | yes | Confirmed | 200 reachable |
| ASB/AGL-07 | Capabilities: Generative organizational culture (Westrum) | DORA | https://raw.githubusercontent.com/dora-team/dora.dev/main/hugo/content/capabilities/generative-organizational-culture/index.md | yes | Confirmed | 200 reachable |
| ASB/AGL-08 | Code-With Engineering Playbook: Definition of Ready | Microsoft | https://raw.githubusercontent.com/microsoft/code-with-engineering-playbook/main/docs/agile-development/team-agreements/definition-of-ready.md | yes | Confirmed | 200 reachable |
| ASB/AGL-09 | Code-With Engineering Playbook: Agile ceremonies (re-verification of EP/ENG-15) | Microsoft | https://raw.githubusercontent.com/microsoft/code-with-engineering-playbook/main/docs/agile-development/ceremonies.md | yes | Confirmed | 200 reachable |
| ASB/AGL-10 | Code-With Engineering Playbook: Sections of a Working Agreement | Microsoft | https://raw.githubusercontent.com/microsoft/code-with-engineering-playbook/main/docs/agile-development/team-agreements/working-agreement.md | yes | Confirmed | 200 reachable |
| ASB/AGL-11 | Code-With Engineering Playbook: Agile Development (fundamentals, AI tooling considerations) | Microsoft | https://raw.githubusercontent.com/microsoft/code-with-engineering-playbook/main/docs/agile-development/README.md | yes | Confirmed | 200 reachable |
| ASB/AGL-12 | Code-With Engineering Playbook: Backlog Management | Microsoft | https://raw.githubusercontent.com/microsoft/code-with-engineering-playbook/main/docs/agile-development/backlog-management.md | yes | Confirmed | 200 reachable |
| ASB/AGL-13 | Orchestrate teams of Claude Code sessions (agent teams) | Anthropic (Claude Code docs) | https://code.claude.com/docs/en/agent-teams.md | yes | Confirmed | 200 reachable |
| ASB/AGL-14 | How we built our multi-agent research system (re-verification) | Anthropic Engineering | https://www.anthropic.com/engineering/multi-agent-research-system | yes | Confirmed (the cited URL redirects; content checked at the redirect target) | 200 reachable |
| ASB/AGL-15 | Effective harnesses for long-running agents (re-verification) | Anthropic Engineering | https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents | yes | Confirmed (the cited URL redirects; content checked at the redirect target) | 200 reachable |
| ASB/AGL-16 | Definition of Ready: What It Is and Why It's Dangerous | Mike Cohn, Mountain Goat Software | https://www.mountaingoatsoftware.com/blog/the-dangers-of-a-definition-of-ready | no | Unverified: mountaingoatsoftware.com blocked; search snippets only | 000 (no connection from the container; blocked, not necessarily dead) |
| ASB/AGL-17 | SPIDR: Five Simple but Powerful Ways to Split User Stories | Mike Cohn, Mountain Goat Software | https://www.mountaingoatsoftware.com/blog/five-simple-but-powerful-ways-to-split-user-stories | no | Unverified: mountaingoatsoftware.com blocked; search snippets only | 000 (no connection from the container; blocked, not necessarily dead) |
| ASB/AGL-18 | The Humanizing Work Show #175: How to Split a User Story | Humanizing Work (Richard Lawrence, Peter Green) | https://the-humanizing-work-show.castos.com/episodes/175-how-to-split-a-user-story | no | Unverified: not fetched; search snippet and third-party mirrors only | 000 (no connection from the container; blocked, not necessarily dead) |
| ASB/AGL-19 | The Kanban Guide (2025.5 edition, PDF) | Kanban Guides (Vacanti, Coleman et al.) | https://kanbanguides.org/the-kanban-guide/2025.5/pdf/kanban-guide.v2025.5.en.pdf | yes | Unverified: kanbanguides.org blocked; search snippet only | 000 (no connection from the container; blocked, not necessarily dead) |
| ASB/AGL-20 | Agile Retrospectives: Making Good Teams Great (Derby and Larsen), as referenced by the MS playbook | Esther Derby and Diana Larsen (book); link taken from AGL-09 | https://www.goodreads.com/book/show/721338.Agile_Retrospectives | no | Unverified: book, not fetched; two phases are confirmed second-hand via ASB/AGL-09 | 000 (no connection from the container; blocked, not necessarily dead) |

### 3.4 REQ: Requirements down to atomic level

30 sources, 21 confirmed.

| ID | Title | Publisher | URL | Official? | Status | Live check 2026-11-03 |
|---|---|---|---|---|---|---|
| ASB/REQ-01 | Gherkin Reference (Cucumber docs, content/docs/gherkin/reference.md) | Cucumber | https://raw.githubusercontent.com/cucumber/docs/main/content/docs/gherkin/reference.md | yes | Confirmed | 200 reachable |
| ASB/REQ-02 | Writing better Gherkin (content/docs/bdd/better-gherkin.md) | Cucumber | https://raw.githubusercontent.com/cucumber/docs/main/content/docs/bdd/better-gherkin.md | yes | Confirmed | 200 reachable |
| ASB/REQ-03 | Example Mapping (content/docs/bdd/example-mapping.md) | Cucumber | https://raw.githubusercontent.com/cucumber/docs/main/content/docs/bdd/example-mapping.md | yes | Confirmed | 200 reachable |
| ASB/REQ-04 | Discovery workshop (content/docs/bdd/discovery-workshop.md) | Cucumber | https://raw.githubusercontent.com/cucumber/docs/main/content/docs/bdd/discovery-workshop.md | yes | Confirmed | 200 reachable |
| ASB/REQ-05 | Who does what / The Three Amigos (content/docs/bdd/who-does-what.md) | Cucumber | https://raw.githubusercontent.com/cucumber/docs/main/content/docs/bdd/who-does-what.md | yes | Confirmed | 200 reachable |
| ASB/REQ-06 | Behaviour-Driven Development (content/docs/bdd/_index.md) | Cucumber | https://raw.githubusercontent.com/cucumber/docs/main/content/docs/bdd/_index.md | yes | Confirmed | 200 reachable |
| ASB/REQ-07 | spec-kit Feature Specification template (templates/spec-template.md) | GitHub | https://raw.githubusercontent.com/github/spec-kit/main/templates/spec-template.md | yes | Confirmed | 200 reachable |
| ASB/REQ-08 | Specification-Driven Development (spec-driven.md) | GitHub | https://raw.githubusercontent.com/github/spec-kit/main/spec-driven.md | yes | Confirmed | 200 reachable |
| ASB/REQ-09 | spec-kit /analyze command (templates/commands/analyze.md) | GitHub | https://raw.githubusercontent.com/github/spec-kit/main/templates/commands/analyze.md | yes | Confirmed | 200 reachable |
| ASB/REQ-10 | spec-kit /specify command (templates/commands/specify.md) | GitHub | https://raw.githubusercontent.com/github/spec-kit/main/templates/commands/specify.md | yes | Confirmed | 200 reachable |
| ASB/REQ-11 | spec-kit checklist template (templates/checklist-template.md) | GitHub | https://raw.githubusercontent.com/github/spec-kit/main/templates/checklist-template.md | yes | Confirmed | 200 reachable |
| ASB/REQ-12 | SRE fundamentals: SLIs, SLAs and SLOs | Google Cloud | https://cloud.google.com/blog/products/devops-sre/sre-fundamentals-slis-slas-and-slos | yes | Confirmed | 200 reachable |
| ASB/REQ-13 | arc42 Quality Model: ISO/IEC 25010 standard page (_standards/iso/iso-25010.md) | arc42 (secondary source on ISO/IEC 25010:2023) | https://raw.githubusercontent.com/arc42/quality.arc42.org-site/main/_standards/iso/iso-25010.md | no | Confirmed | 200 reachable |
| ASB/REQ-14 | arc42 Quality Model README (metamodel and authoring rules) | arc42 | https://raw.githubusercontent.com/arc42/quality.arc42.org-site/main/README.md | no | Confirmed | 200 reachable |
| ASB/REQ-15 | EARS syntax VS Code extension: README and snippets (BlueDotBrigade) | BlueDotBrigade (secondary; credits Alistair Mavin's EARS) | https://raw.githubusercontent.com/BlueDotBrigade/ears-syntax-vscode/main/snippets/ears.code-snippets | no | Confirmed | 200 reachable |
| ASB/REQ-16 | Definition of Ready (Microsoft Code-With Engineering Playbook) | Microsoft | https://raw.githubusercontent.com/microsoft/code-with-engineering-playbook/main/docs/agile-development/team-agreements/definition-of-ready.md | yes | Confirmed | 200 reachable |
| ASB/REQ-17 | Definition of Done (Microsoft Code-With Engineering Playbook) | Microsoft | https://raw.githubusercontent.com/microsoft/code-with-engineering-playbook/main/docs/agile-development/team-agreements/definition-of-done.md | yes | Confirmed | 200 reachable |
| ASB/REQ-18 | Backlog Management (Microsoft Code-With Engineering Playbook) | Microsoft | https://raw.githubusercontent.com/microsoft/code-with-engineering-playbook/main/docs/agile-development/backlog-management.md | yes | Confirmed | 200 reachable |
| ASB/REQ-19 | Performance (Microsoft Code-With Engineering Playbook, non-functional requirements) | Microsoft | https://raw.githubusercontent.com/microsoft/code-with-engineering-playbook/main/docs/non-functional-requirements/performance.md | yes | Confirmed | 200 reachable |
| ASB/REQ-20 | Claude Code best practices (code.claude.com/docs/en/best-practices.md) | Anthropic | https://code.claude.com/docs/en/best-practices.md | yes | Confirmed | 200 reachable |
| ASB/REQ-21 | Effective harnesses for long-running agents | Anthropic | https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents | yes | Confirmed (the cited URL redirects; content checked at the redirect target) | 200 reachable |
| ASB/REQ-22 | EARS: The Easy Approach to Requirements Syntax (Alistair Mavin) | Alistair Mavin | https://alistairmavin.com/ears/ | yes | Unverified: alistairmavin.com blocked (DNS failure); not fetched | 000 (no connection from the container; blocked, not necessarily dead) |
| ASB/REQ-23 | ISO/IEC/IEEE 29148:2018 Requirements engineering | ISO/IEC/IEEE | https://www.iso.org/standard/72089.html | yes | Unverified: iso.org blocked and the standard is paywalled; secondary search results only | 000 (no connection from the container; blocked, not necessarily dead) |
| ASB/REQ-24 | ISO/IEC 25010:2023 Product quality model | ISO/IEC | https://www.iso.org/standard/78176.html | yes | Unverified: iso.org blocked and the standard is paywalled; names come only from ASB/REQ-13 | 000 (no connection from the container; blocked, not necessarily dead) |
| ASB/REQ-25 | Site Reliability Engineering book, ch. 4 Service Level Objectives | Google | https://sre.google/sre-book/service-level-objectives/ | yes | Unverified: sre.google blocked (DNS failure); not fetched | 000 (no connection from the container; blocked, not necessarily dead) |
| ASB/REQ-26 | Introducing Example Mapping (Matt Wynne) | Cucumber | https://cucumber.io/blog/2015/12/08/example-mapping-introduction | yes | Unverified: cucumber.io blocked; not fetched | 000 (no connection from the container; blocked, not necessarily dead) |
| ASB/REQ-27 | How to Quantify Quality: Finding Scales of Measure (Tom Gilb, ACCU Overload 70) | ACCU | https://accu.org/journals/overload/13/70/gilb_299 | no | Unverified: accu.org blocked; search snippets only | 000 (no connection from the container; blocked, not necessarily dead) |
| ASB/REQ-28 | The new user story backlog is a map (Jeff Patton) | Jeff Patton & Associates | https://jpattonassociates.com/the-new-backlog/ | yes | Unverified: jpattonassociates.com blocked; cited from the researcher's prior knowledge only | 000 (no connection from the container; blocked, not necessarily dead) |
| ASB/REQ-29 | INVEST in Good Stories, and SMART Tasks (Bill Wake) | XP123 | https://xp123.com/articles/invest-in-good-stories-and-smart-tasks/ | yes | Unverified: xp123.com refused by the proxy; not fetched | 000 (no connection from the container; blocked, not necessarily dead) |
| ASB/REQ-30 | Leveraging LLMs for the Quality Assurance of Software Requirements (arXiv 2408.10886) | arXiv | https://arxiv.org/pdf/2408.10886 | no | Unverified: arxiv.org blocked; search snippet only | 000 (no connection from the container; blocked, not necessarily dead) |

### 3.5 RPD: Product roles: PM, BA, designer, EM, domain coach

26 sources, 19 confirmed.

| ID | Title | Publisher | URL | Official? | Status | Live check 2026-11-03 |
|---|---|---|---|---|---|---|
| ASB/RPD-01 | Create custom subagents (Claude Code docs) | Anthropic | https://code.claude.com/docs/en/sub-agents | yes | Confirmed | 200 reachable |
| ASB/RPD-02 | How we built our multi-agent research system | Anthropic Engineering | https://www.anthropic.com/engineering/multi-agent-research-system | yes | Confirmed (the cited URL redirects; content checked at the redirect target) | 200 reachable |
| ASB/RPD-03 | Building effective agents | Anthropic | https://www.anthropic.com/research/building-effective-agents | yes | Confirmed | 200 reachable |
| ASB/RPD-04 | Prompting best practices (Claude) | Anthropic | https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices | yes | Confirmed | 200 reachable |
| ASB/RPD-05 | WCAG 2.2 guidelines source (index.html, w3c/wcag repo) | W3C | https://raw.githubusercontent.com/w3c/wcag/main/guidelines/index.html | yes | Confirmed | 200 reachable |
| ASB/RPD-06 | WCAG 2.2 SC Consistent Help (sc/22/consistent-help.html) | W3C | https://raw.githubusercontent.com/w3c/wcag/main/guidelines/sc/22/consistent-help.html | yes | Confirmed | 200 reachable |
| ASB/RPD-07 | WCAG 2.2 SC Redundant Entry (sc/22/redundant-entry.html) | W3C | https://raw.githubusercontent.com/w3c/wcag/main/guidelines/sc/22/redundant-entry.html | yes | Confirmed | 200 reachable |
| ASB/RPD-08 | Understanding Conformance (WCAG 2.2) | W3C | https://raw.githubusercontent.com/w3c/wcag/main/understanding/conformance.html | yes | Confirmed | 200 reachable |
| ASB/RPD-09 | Understanding SC 4.1.1 Parsing (Obsolete and removed) | W3C | https://raw.githubusercontent.com/w3c/wcag/main/understanding/20/parsing.html | yes | Confirmed | 200 reachable |
| ASB/RPD-10 | Code-With Engineering Playbook: Accessibility | Microsoft | https://raw.githubusercontent.com/microsoft/code-with-engineering-playbook/main/docs/non-functional-requirements/accessibility.md | yes | Confirmed | 200 reachable |
| ASB/RPD-11 | Code-With Engineering Playbook: Design Reviews | Microsoft | https://raw.githubusercontent.com/microsoft/code-with-engineering-playbook/main/docs/design/design-reviews/README.md | yes | Confirmed | 200 reachable |
| ASB/RPD-12 | Code-With Engineering Playbook: Agile Ceremonies | Microsoft | https://raw.githubusercontent.com/microsoft/code-with-engineering-playbook/main/docs/agile-development/ceremonies.md | yes | Confirmed | 200 reachable |
| ASB/RPD-13 | Code-With Engineering Playbook: Definition of Ready | Microsoft | https://raw.githubusercontent.com/microsoft/code-with-engineering-playbook/main/docs/agile-development/team-agreements/definition-of-ready.md | yes | Confirmed | 200 reachable |
| ASB/RPD-14 | Code-With Engineering Playbook: Backlog Management | Microsoft | https://raw.githubusercontent.com/microsoft/code-with-engineering-playbook/main/docs/agile-development/backlog-management.md | yes | Confirmed | 200 reachable |
| ASB/RPD-15 | Code-With Engineering Playbook: Agile/Scrum Roles | Microsoft | https://raw.githubusercontent.com/microsoft/code-with-engineering-playbook/main/docs/agile-development/roles.md | yes | Confirmed | 200 reachable |
| ASB/RPD-16 | Example Mapping (Cucumber docs) | Cucumber (SmartBear) | https://raw.githubusercontent.com/cucumber/docs/main/content/docs/bdd/example-mapping.md | yes | Confirmed | 200 reachable |
| ASB/RPD-17 | Who Does What? Roles and responsibilities in a BDD team (Cucumber docs) | Cucumber (SmartBear) | https://raw.githubusercontent.com/cucumber/docs/main/content/docs/bdd/who-does-what.md | yes | Confirmed | 200 reachable |
| ASB/RPD-18 | EventStorming Glossary & Cheat Sheet | DDD Crew | https://raw.githubusercontent.com/ddd-crew/eventstorming-glossary-cheat-sheet/master/README.md | no | Confirmed | 200 reachable |
| ASB/RPD-19 | DDD Starter Modelling Process | DDD Crew | https://raw.githubusercontent.com/ddd-crew/ddd-starter-modelling-process/master/README.md | no | Confirmed | 200 reachable |
| ASB/RPD-20 | The Scrum Guide (2020) | Schwaber & Sutherland | https://scrumguides.org/scrum-guide.html | yes | Unverified: scrumguides.org does not resolve here; search snippets only | 000 (no connection from the container; blocked, not necessarily dead) |
| ASB/RPD-21 | The Four Big Risks | SVPG (Marty Cagan) | https://svpg.com/four-big-risks/ | yes | Unverified: svpg.com does not resolve here; secondary summaries only | 000 (no connection from the container; blocked, not necessarily dead) |
| ASB/RPD-22 | Opportunity Solution Trees / Continuous Discovery (Product Talk) | Product Talk (Teresa Torres) | https://www.producttalk.org/opportunity-solution-trees/ | yes | Unverified: producttalk.org does not resolve here; secondary summaries only | 000 (no connection from the container; blocked, not necessarily dead) |
| ASB/RPD-23 | BABOK Guide (IIBA) | IIBA | https://www.iiba.org/career-resources/a-business-analysis-professionals-foundation-for-success/babok/ | yes | Unverified: iiba.org refused by the proxy; search snippet only | 000 (no connection from the container; blocked, not necessarily dead) |
| ASB/RPD-24 | HAX Toolkit: Guidelines for Human-AI Interaction | Microsoft Research | https://www.microsoft.com/en-us/haxtoolkit/ai-guidelines/ | yes | Unverified: the researcher could not reach www.microsoft.com; the fact-checker later reached the page (HTTP 200) and found '18 Guidelines', but did not check the guideline texts G1-G18 | 200 reachable |
| ASB/RPD-25 | 10 Usability Heuristics for User Interface Design | Nielsen Norman Group | https://www.nngroup.com/articles/ten-usability-heuristics/ | no | Unverified: nngroup.com blocked; listed only so nobody cites it as verified | 000 (no connection from the container; blocked, not necessarily dead) |
| ASB/RPD-26 | EventStorming (official site) | Alberto Brandolini | https://www.eventstorming.com/ | yes | Unverified: eventstorming.com blocked; the method is covered by ASB/RPD-18 and ASB/RPD-19 | 000 (no connection from the container; blocked, not necessarily dead) |

### 3.6 REN: Engineering roles: PE, backend, frontend, ML/CV, QA, security, SRE

41 sources, 34 confirmed.

| ID | Title | Publisher | URL | Official? | Status | Live check 2026-11-03 |
|---|---|---|---|---|---|---|
| ASB/REN-01 | Trunk-based development (DORA capability) | DORA (Google), source repo dora-team/dora.dev hugo/content/capabilities/trunk-based-development/index.md | https://github.com/dora-team/dora.dev/blob/main/hugo/content/capabilities/trunk-based-development/index.md | yes | Confirmed | 403 (github.com web page blocked here; raw/git access works) |
| ASB/REN-02 | DORA's software delivery performance metrics (guide) | DORA (Google), dora-team/dora.dev hugo/content/guides/dora-metrics/_index.md | https://github.com/dora-team/dora.dev/blob/main/hugo/content/guides/dora-metrics/_index.md | yes | Confirmed | 403 (github.com web page blocked here; raw/git access works) |
| ASB/REN-03 | Test automation (DORA capability) | DORA (Google), dora-team/dora.dev hugo/content/capabilities/test-automation/index.md | https://github.com/dora-team/dora.dev/blob/main/hugo/content/capabilities/test-automation/index.md | yes | Confirmed | 403 (github.com web page blocked here; raw/git access works) |
| ASB/REN-04 | Continuous integration (DORA capability) | DORA (Google), dora-team/dora.dev hugo/content/capabilities/continuous-integration/index.md | https://github.com/dora-team/dora.dev/blob/main/hugo/content/capabilities/continuous-integration/index.md | yes | Confirmed | 403 (github.com web page blocked here; raw/git access works) |
| ASB/REN-05 | Monitoring and observability (DORA capability) | DORA (Google), dora-team/dora.dev hugo/content/capabilities/monitoring-and-observability/index.md | https://github.com/dora-team/dora.dev/blob/main/hugo/content/capabilities/monitoring-and-observability/index.md | yes | Confirmed | 403 (github.com web page blocked here; raw/git access works) |
| ASB/REN-06 | Identifying and tracking toil using SRE principles | Google Cloud Blog | https://cloud.google.com/blog/products/management-tools/identifying-and-tracking-toil-using-sre-principles | yes | Confirmed | 200 reachable |
| ASB/REN-07 | SRE fundamentals: SLIs, SLAs and SLOs (re-verification of repo REL-01) | Google Cloud Blog | https://cloud.google.com/blog/products/devops-sre/sre-fundamentals-slis-slas-and-slos | yes | Confirmed | 200 reachable |
| ASB/REN-08 | SRE error budgets and maintenance windows (re-verification of repo REL-02) | Google Cloud Blog (J. Climent, 2020-06-22) | https://cloud.google.com/blog/products/management-tools/sre-error-budgets-and-maintenance-windows | yes | Confirmed | 200 reachable |
| ASB/REN-09 | Site Reliability Engineering book: Service Level Objectives / Embracing Risk / Eliminating Toil | Google (sre.google) | https://sre.google/sre-book/service-level-objectives/ | yes | Unverified: sre.google blocked; the fact-checker's retry also failed | 000 (no connection from the container; blocked, not necessarily dead) |
| ASB/REN-10 | Short-lived feature branches | trunkbaseddevelopment.com (Paul Hammant), source repo paul-hammant/tbd | https://github.com/paul-hammant/tbd/blob/master/content/short-lived-feature-branches/index.md | no | Confirmed | 403 (github.com web page blocked here; raw/git access works) |
| ASB/REN-11 | Google eng-practices: The Standard of Code Review (re-verify) | Google | https://github.com/google/eng-practices/blob/master/review/reviewer/standard.md | yes | Confirmed | 403 (github.com web page blocked here; raw/git access works) |
| ASB/REN-12 | Google eng-practices: What to look for in a code review (re-verify) | Google | https://github.com/google/eng-practices/blob/master/review/reviewer/looking-for.md | yes | Confirmed | 403 (github.com web page blocked here; raw/git access works) |
| ASB/REN-13 | Google eng-practices: Handling pushback / Speed of code reviews | Google | https://github.com/google/eng-practices/blob/master/review/reviewer/pushback.md | yes | Confirmed | 403 (github.com web page blocked here; raw/git access works) |
| ASB/REN-14 | Decision record template by Michael Nygard | Joel Parker Henderson, architecture-decision-record repo (reproduces Nygard 2011) | https://github.com/joelparkerhenderson/architecture-decision-record/blob/main/architecture-decision-record.github.io/src/content/locales/en-001/templates/decision-record-template-by-michael-nygard.md | no | Confirmed | 403 (github.com web page blocked here; raw/git access works) |
| ASB/REN-15 | Design Reviews (Code-With Engineering Playbook) | Microsoft | https://github.com/microsoft/code-with-engineering-playbook/blob/main/docs/design/design-reviews/README.md | yes | Confirmed | 403 (github.com web page blocked here; raw/git access works) |
| ASB/REN-16 | Testing FastAPI / Testing dependencies with overrides | FastAPI (S. Ramírez) | https://github.com/fastapi/fastapi/blob/master/docs/en/docs/advanced/testing-dependencies.md | yes | Confirmed | 403 (github.com web page blocked here; raw/git access works) |
| ASB/REN-17 | OWASP API Security Top 10 2023 (re-verification of repo SEC-08) | OWASP API Security Project | https://raw.githubusercontent.com/OWASP/API-Security/master/editions/2023/en/0x11-t10.md | yes | Confirmed | 200 reachable |
| ASB/REN-18 | Canon TDD | Kent Beck (newsletter) | https://newsletter.kentbeck.com/p/canon-tdd | yes | Unverified: newsletter.kentbeck.com blocked; search snippets only | 000 (no connection from the container; blocked, not necessarily dead) |
| ASB/REN-19 | Testing Library: Guiding Principles | Testing Library, testing-library-docs docs/guiding-principles.mdx | https://github.com/testing-library/testing-library-docs/blob/main/docs/guiding-principles.mdx | yes | Confirmed | 403 (github.com web page blocked here; raw/git access works) |
| ASB/REN-20 | Testing Library: About Queries, Priority | Testing Library, docs/queries/about.mdx | https://github.com/testing-library/testing-library-docs/blob/main/docs/queries/about.mdx | yes | Confirmed | 403 (github.com web page blocked here; raw/git access works) |
| ASB/REN-21 | Next.js docs: Testing (index) | Vercel, next.js docs/01-app/02-guides/testing/index.mdx | https://github.com/vercel/next.js/blob/canary/docs/01-app/02-guides/testing/index.mdx | yes | Confirmed | 403 (github.com web page blocked here; raw/git access works) |
| ASB/REN-22 | Next.js docs: Production checklist | Vercel, docs/01-app/02-guides/production-checklist.mdx | https://github.com/vercel/next.js/blob/canary/docs/01-app/02-guides/production-checklist.mdx | yes | Confirmed | 403 (github.com web page blocked here; raw/git access works) |
| ASB/REN-23 | React docs: Keeping Components Pure / You Might Not Need an Effect | React (Meta), reactjs/react.dev | https://github.com/reactjs/react.dev/blob/main/src/content/learn/you-might-not-need-an-effect.md | yes | Confirmed | 403 (github.com web page blocked here; raw/git access works) |
| ASB/REN-24 | web.dev: Performance budgets 101 / Defining Core Web Vitals thresholds | Google Chrome (GoogleChrome/web.dev repo, ARCHIVED, last commit 2023-10-29) | https://github.com/GoogleChrome/web.dev/blob/main/src/site/content/en/fast/performance-budgets-101/index.md | yes | Confirmed | 403 (github.com web page blocked here; raw/git access works) |
| ASB/REN-25 | Write tests. Not too many. Mostly integration. / The Testing Trophy | Kent C. Dodds (kentcdodds.com source repo) | https://github.com/kentcdodds/kentcdodds.com/blob/main/services/site/content/blog/the-testing-trophy-and-testing-classifications.mdx | no | Confirmed | 403 (github.com web page blocked here; raw/git access works) |
| ASB/REN-26 | Pact docs: Convince me (contract testing vs E2E) | Pact Foundation, docs.pact.io repo website/docs/faq/convinceme.md | https://github.com/pact-foundation/docs.pact.io/blob/master/website/docs/faq/convinceme.md | yes | Confirmed | 403 (github.com web page blocked here; raw/git access works) |
| ASB/REN-27 | Consumer-Driven Contract Testing (Code-With Engineering Playbook) | Microsoft | https://github.com/microsoft/code-with-engineering-playbook/blob/main/docs/automated-testing/cdc-testing/README.md | yes | Confirmed | 403 (github.com web page blocked here; raw/git access works) |
| ASB/REN-28 | Test planning (Code-With Engineering Playbook) | Microsoft | https://github.com/microsoft/code-with-engineering-playbook/blob/main/docs/automated-testing/test-planning.md | yes | Confirmed | 403 (github.com web page blocked here; raw/git access works) |
| ASB/REN-29 | OWASP Threat Modeling Cheat Sheet | OWASP Cheat Sheet Series | https://github.com/OWASP/CheatSheetSeries/blob/master/cheatsheets/Threat_Modeling_Cheat_Sheet.md | yes | Confirmed | 403 (github.com web page blocked here; raw/git access works) |
| ASB/REN-30 | Threat Modeling (Code-With Engineering Playbook) | Microsoft | https://github.com/microsoft/code-with-engineering-playbook/blob/main/docs/security/threat-modelling.md | yes | Confirmed | 403 (github.com web page blocked here; raw/git access works) |
| ASB/REN-31 | Threat Modeling Manifesto | Threat Modeling Manifesto working group | https://www.threatmodelingmanifesto.org/ | yes | Unverified: threatmodelingmanifesto.org blocked; the four questions are confirmed second-hand via ASB/REN-29 | 000 (no connection from the container; blocked, not necessarily dead) |
| ASB/REN-32 | OWASP ASVS 5.0: What is the ASVS (re-verification of repo SEC-01) | OWASP | https://github.com/OWASP/ASVS/blob/master/5.0/en/0x03-What-is-the-ASVS.md | yes | Confirmed | 403 (github.com web page blocked here; raw/git access works) |
| ASB/REN-33 | OWASP Top 10 Privacy Risks v2.0 (2021) | OWASP, www-project-top-10-privacy-risks tab_topprivacy.md | https://github.com/OWASP/www-project-top-10-privacy-risks/blob/master/tab_topprivacy.md | yes | Confirmed | 403 (github.com web page blocked here; raw/git access works) |
| ASB/REN-34 | Privacy: data handling (Code-With Engineering Playbook) | Microsoft | https://github.com/microsoft/code-with-engineering-playbook/blob/main/docs/non-functional-requirements/privacy/data-handling.md | yes | Confirmed | 403 (github.com web page blocked here; raw/git access works) |
| ASB/REN-35 | The ML Test Score: A Rubric for ML Production Readiness and Technical Debt Reduction (Breck et al., IEEE Big Data 2017) | Google Research | https://research.google/pubs/pub46555/ | yes | Unverified: research.google blocked; search snippets and a secondary slide only | 000 (no connection from the container; blocked, not necessarily dead) |
| ASB/REN-36 | Hugging Face Hub: Model Cards + Annotated Model Card Template | Hugging Face, hub-docs docs/hub/model-cards.md and model-card-annotated.md | https://github.com/huggingface/hub-docs/blob/main/docs/hub/model-card-annotated.md | yes | Confirmed | 403 (github.com web page blocked here; raw/git access works) |
| ASB/REN-37 | Model Cards for Model Reporting (Mitchell et al.) | arXiv 1810.03993 | https://arxiv.org/abs/1810.03993 | yes | Unverified: arxiv.org blocked; cited second-hand via ASB/REN-36 | 000 (no connection from the container; blocked, not necessarily dead) |
| ASB/REN-38 | DVC Get Started | Iterative, dvc.org content/docs/start/index.md | https://github.com/iterative/dvc.org/blob/main/content/docs/start/index.md | yes | Confirmed | 403 (github.com web page blocked here; raw/git access works) |
| ASB/REN-39 | Create custom subagents (Claude Code docs) | Anthropic | https://code.claude.com/docs/en/sub-agents | yes | Confirmed | 200 reachable |
| ASB/REN-40 | Domain-Driven Design Reference (Evans) / Effective Aggregate Design (Vernon) | Domain Language / dddcommunity.org | https://www.domainlanguage.com/ddd/reference/ | yes | Unverified: domainlanguage.com blocked; not fetched | 000 (no connection from the container; blocked, not necessarily dead) |
| ASB/REN-41 | ISTQB Certified Tester Foundation Level syllabus / glossary (risk-based testing, exploratory testing) | ISTQB | https://istqb.org | yes | Unverified: istqb.org blocked; not fetched, no definitions quoted | not recorded |

## 4. Key points per source

Each entry gives the researcher's key points and the fact-checker's note. For Not confirmed and Unverified sources, the points are **not** evidence; they are kept so the gap is visible.

### 4.1 ANT

#### ASB/ANT-01: Create custom subagents (Claude Code docs)

Status: Confirmed.

- Only `name` and `description` are required frontmatter. Optional fields include tools, disallowedTools, model (sonnet/opus/haiku/fable/full ID/inherit), permissionMode, maxTurns, skills, mcpServers, hooks, memory, background, effort, isolation: worktree, color, initialPrompt, omitClaudeMd.
- `tools`: if you leave it out, the subagent inherits every tool available to subagents. `disallowedTools` with a specifier such as Bash(git push *) still removes the whole tool.
- Claude uses each subagent's description to decide when to delegate. To encourage proactive delegation, include phrases like 'use proactively'.
- Official best-practices box: design focused subagents that excel at one task; write descriptions that single out one subagent; limit tool access; check project subagents into version control.
- Combined custom descriptions over 15,000 tokens trigger a startup warning. Keep descriptions short and move detail into the system prompt body, which only loads when the subagent runs.
- The body becomes the system prompt and replaces the default Claude Code system prompt. Custom subagents still load the CLAUDE.md hierarchy unless omitClaudeMd is set. A rule that must reach the subagent should be restated in the delegation prompt.
- Nested spawning is capped by CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH. To keep a reviewer read-only and non-spawning, omit Agent from tools or add it to disallowedTools. Agent(type) allowlists work only for a main-thread --agent.
- Background subagents (the default) keep only a fixed set of built-in tools, so the same definition can resolve to different tools in the foreground and the background.
- No message from any agent counts as approval for a permission prompt, and no agent message can change a subagent's permissions, CLAUDE.md or config.
- Agents can be disabled through permissions.deny with Agent(name). `claude plugin validate .claude/agents` finds frontmatter that does not parse.
- *Fact-checker's note:* 200, no redirect. All 10 points found. Only name and description are required (line 289). Model values include fable, a full ID and inherit (302). omitClaudeMd, initialPrompt, isolation: worktree, background and color all appear in the field table. Leaving out tools inherits every tool available to subagents (300). A disallowedTools entry such as Bash(git push *) still removes the whole tool (301, 488). 'use proactively' (838). The best-practices box (1282-1287) matches. The 15,000-token startup warning, with advice to move detail into the body, is at lines 27 and 840. A custom prompt replaces the default system prompt, CLAUDE.md still loads (877), and a rule that must reach the subagent should be restated in the delegation prompt (1110). To keep a reviewer from spawning, omit Agent or add it to disallowedTools (1074, 521). Agent(type) allowlists work only for a main-thread --agent (523). Background subagents keep a reduced built-in tool set (436). No agent message counts as approval (1152). permissions.deny Agent(name) (728). claude plugin validate .claude/agents (345). Nuance: background is the default only for subagents spawned from the main conversation.

#### ASB/ANT-02: How Claude remembers your project (CLAUDE.md / memory docs)

Status: Confirmed.

- Memory is context, not enforced configuration. To block an action regardless of what Claude decides, use a PreToolUse hook.
- Target under 200 lines per CLAUDE.md. Longer files consume more context and reduce adherence. Imports do not reduce context cost.
- Structure instructions with headers and bullets. If two instructions contradict each other, Claude may pick one arbitrarily, so review instruction files periodically.
- Be specific and verifiable: write 'API handlers live in src/api/handlers/', not 'Keep files organized'.
- Multi-step procedures, and content that matters for only part of the codebase, belong in skills or path-scoped .claude/rules/ (paths: frontmatter), not in CLAUDE.md.
- `/doctor prompt-audit` audits CLAUDE.md, rules, skills, commands and subagents for outdated, contradictory or dangling instructions and proposes edits. Nothing changes until you approve. Requires v2.1.283+.
- *Fact-checker's note:* 200. Memory is 'context, not enforced configuration'; use a PreToolUse hook to block an action (24, 80). Target under 200 lines; longer files reduce adherence; imports don't reduce context cost (88, 621). Headers and bullets; contradicting instructions may be resolved arbitrarily; review periodically (89-90). The src/api/handlers example (84). Multi-step procedures and part-of-codebase content go to skills or path-scoped rules (51, 88). /doctor prompt-audit covers subagents, skills, rules and commands, changes nothing until you ask, and needs v2.1.283+ (94-98).

#### ASB/ANT-03: Hooks reference (Claude Code docs) (not confirmed)

Status: Not confirmed: the fact-checker found the event list and the deny / exit-code-2 blocking on the page, but not 'hooks run deterministically' (that framing is from ASB/ANT-08 and ASB/ANT-02, and prompt or subagent hooks are not deterministic) and not 'plugin subagents ignore the hooks field' (that is on ASB/ANT-01). Cite this page only for the event list and the blocking mechanism.

- Lifecycle events include PreToolUse (can block a tool call), PostToolUse, Stop, SubagentStart/SubagentStop, TaskCreated/TaskCompleted, TeammateIdle and SessionStart.
- A PreToolUse hook can return permissionDecision deny, or block with exit code 2. Hooks run deterministically, outside the model's judgment.
- Hooks can also be scoped to a single subagent through its `hooks` frontmatter, but plugin subagents ignore that field.
- *Fact-checker's note:* 200. Point 1 is confirmed: the event table lists PreToolUse ('Can block it'), PostToolUse, Stop, SubagentStart/Stop, TaskCreated, TaskCompleted, TeammateIdle and SessionStart. Point 2 is partly confirmed: permissionDecision 'deny' (95, 106) and exit code 2 'Blocks the tool call' (985-990) are there. But 'Hooks run deterministically, outside the model's judgment' is NOT on this page; that framing comes from best-practices (ASB/ANT-08 lines 39-44) and memory (ASB/ANT-02 line 24). It also OVERSTATES: this page says hooks can be 'LLM prompts, or subagents' (line 13), and those are not deterministic. Point 3 is partly confirmed: subagent-frontmatter hooks are documented (249, 658-678). 'Plugin subagents ignore that field' is NOT on this page; it is on ASB/ANT-01 (lines 234, 308). Recommendation: cite ASB/ANT-01 and ASB/ANT-08 for those two points, and limit 'deterministic' to command and HTTP hooks.

#### ASB/ANT-04: Settings files and precedence (Claude Code docs)

Status: Confirmed.

- Shared project .claude/settings.json is committed for team permissions, hooks, plugins and env vars. .claude/settings.local.json holds personal overrides and stays out of git. Managed settings carry org policy.
- The file a setting is read from decides who it applies to.
- *Fact-checker's note:* 200. The scope table (25-30) says shared .claude/settings.json is committed and used for 'Team permissions, hooks, plugins, and the environment variables the project needs'; settings.local.json is personal and kept out of git; managed settings carry security policy and compliance. 'the file it reads a setting from decides who the setting applies to' (15).

#### ASB/ANT-05: Configure permissions (Claude Code docs)

Status: Confirmed.

- Rules are evaluated deny, then ask, then allow. The first match wins, and an allow rule cannot carve an exception out of a deny rule.
- A bare tool name in deny removes the tool from context. A scoped rule such as Bash(rm *) blocks only matching calls.
- A Bash rule matches the command text, not the program, so it is not a security boundary. Pair it with the sandbox when a restriction must hold.
- Read and Edit deny rules do not stop arbitrary subprocesses that read files themselves. OS-level enforcement requires the sandbox. .claudeignore has no effect, so use Read deny rules.
- *Fact-checker's note:* 200. Rules are evaluated deny, then ask, then allow; first match wins; an allow rule can't carve an exception out of a deny rule (56-58). A bare tool name in deny removes the tool from context (60, 103). A Bash rule matches command text and 'isn't a security boundary around the program'; use sandboxing for real enforcement (250, 260, 296). Read and Edit deny rules don't apply to arbitrary subprocesses (354). Sandboxing is the OS-level layer (729). .claudeignore 'has no effect', so use Read deny rules (337).

#### ASB/ANT-06: Extend Claude with skills (Claude Code docs; slash commands merged here)

Status: Confirmed.

- Custom commands have been merged into skills: .claude/commands/x.md and .claude/skills/x/SKILL.md both create /x. Prefer skills for new work. (/en/slash-commands serves the same page.)
- Create a skill when you keep pasting the same procedure, or when a CLAUDE.md section has grown into a procedure. A skill body loads only when the skill is used.
- The description should put the key use case first. description plus when_to_use is truncated at 1,536 characters in the listing. Unknown frontmatter fields are silently ignored.
- disable-model-invocation: true makes a skill manual-only, for side-effecting workflows such as deploys or commits. allowed-tools pre-approves tools for that turn only. context: fork runs the skill in a subagent.
- *Fact-checker's note:* 200. 'Custom commands have been merged into skills' (17); 'Prefer a skill for new work' (172). /en/slash-commands also returns 200 with the title 'Extend Claude with skills', so it serves the same page. 'keep pasting ... grown into a procedure'; the skill body loads only when used (11). Put the key use case first; description plus when_to_use is truncated at 1,536 characters (398-399). Unknown fields are ignored without an error (391). disable-model-invocation for deploys and commits, and context: fork (358). allowed-tools applies only during the invoking turn (404, 617).

#### ASB/ANT-07: Run Claude Code programmatically (headless docs)

Status: Confirmed.

- `claude -p` with --allowedTools auto-approves only the listed tools. --output-format json returns structured results, including total_cost_usd.
- --bare -p gives minimal, reproducible scripted runs.
- *Fact-checker's note:* 200. --allowedTools lets the listed tools run without prompting (307-309). --output-format json includes total_cost_usd (128). --bare is for CI and scripts 'where you need the same result on every machine' and is recommended for scripted calls (37-39, 71). Slight OVERSTATEMENT: the page never says 'only the listed tools', and it gives exceptions. Reads from network paths still prompt, and in auto mode a bare Bash entry is dropped and auto mode evaluates each command.

#### ASB/ANT-08: Best practices for Claude Code (docs page; the engineering-blog URL /engineering/claude-code-best-practices now serves this page)

Status: Confirmed.

- Keep CLAUDE.md short. It should hold only what Claude cannot work out from the code: exact test, lint and typecheck commands, misleading spots, decisions that are not in the repo, and anything corrected twice.
- Deterministic versus non-deterministic: a prompt alone cannot guarantee that something never happens, or always happens. Enforce rules that cannot have exceptions with hooks or deny rules. Conversely, delete hooks that encode mere preferences.
- 'What you can stop doing': don't add IMPORTANT or ALL CAPS (current models over-apply emphasized rules); don't use 'think hard'; don't tell it to 'keep going / don't be lazy' (this causes over-work); don't describe architecture or file layout in CLAUDE.md; delegating to a subagent does not make an answer better, but a fresh-context reviewer does help.
- Give Claude a check to run, such as tests, a Stop hook or a review step. A subagent can review a diff against SPEC.md for unmet requirements and untested edge cases.
- Before an unattended run, settle five questions: what done looks like, how it checks its own work, what it may touch, what stops it (max-turns or budget), and who signs off. A person approves the merge.
- If you have corrected the same thing twice, /clear and rewrite the prompt rather than stacking corrections. A second session is the easiest independent reviewer.
- *Fact-checker's note:* 200. Keep CLAUDE.md short: exact test, typecheck and lint commands, misleading spots, decisions not in the repo, anything corrected twice (132-140). There is a section titled 'Deterministic and non-deterministic instructions' (39-58): 'A prompt alone can't guarantee either' (30); delete hooks that are only preferences (67, 368). The 'What you can stop doing' table (610-622) covers IMPORTANT and ALL CAPS ('over-apply'), think hard, 'keep going / don't be lazy' ('over-work'), architecture and file layout, and that delegating doesn't make answers better but a fresh reviewer does help. Give Claude a check to run; a subagent reviews the diff against SPEC.md (233-263). Five questions before an unattended run, including max-turns and budget and a person approving the merge (530-536). After two failed corrections, /clear (508, 514). A second session as reviewer (608).

#### ASB/ANT-09: Orchestrate teams of Claude Code sessions (agent teams docs)

Status: Confirmed.

- Agent teams are experimental and disabled by default (CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1). Check whether subagents or cross-session messaging is enough first.
- Teams add coordination overhead and significantly more tokens. They are poor for sequential tasks, same-file edits or many dependencies.
- Start with 3-5 teammates; three focused teammates often beat five scattered ones. Aim for about 5-6 self-contained tasks per teammate, each with a clear deliverable.
- Teammates do not inherit the lead's history, so put task-specific context in the spawn prompt. Avoid file conflicts by giving each teammate its own set of files. Monitor and steer; don't let the team run unattended too long.
- *Fact-checker's note:* 200. Experimental and off by default; CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1 (11, 48); check lighter options first (15). Coordination overhead, significantly more tokens, poor for sequential, same-file or many-dependency work (26). Start with 3-5 teammates; 'Three focused teammates often outperform five scattered ones'; 5-6 tasks per teammate; self-contained deliverables (384-396). No inherited history, so give context in the spawn prompt (313, 367). Each teammate owns a different set of files (410-412). Monitor and steer; don't run unattended too long (414-416).

#### ASB/ANT-10: Subagents in the Agent SDK

Status: Confirmed.

- AgentDefinition has description (when to use), prompt (behavior) and tools (a read-only reviewer example uses Read, Grep, Glob).
- Delegation can be capped through CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH, CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS (default 20) and maxBudgetUsd / max_budget_usd.
- *Fact-checker's note:* 200. The example reviewer has a description ('tells Claude when to use'), a prompt and read-only tools Read, Grep and Glob (39-67). The caps table (640-642) lists CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH (default 3), CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS (default 20) and maxBudgetUsd / max_budget_usd.

#### ASB/ANT-11: Building effective agents

Status: Confirmed (the cited URL redirects; content checked at the redirect target).

- Find the simplest solution possible, and only increase complexity when needed.
- Three principles: simplicity, transparency (show planning steps explicitly), and a carefully crafted agent-computer interface through documentation and testing.
- Agents need ground truth from the environment at each step. Include stopping conditions such as maximum iterations.
- Evaluator-optimizer pays off when evaluation criteria are clear and iteration gives measurable value. Orchestrator-workers suits complex multi-file coding changes.
- *Fact-checker's note:* REDIRECTED: 301 to https://www.anthropic.com/research/building-effective-agents (same article), so fetched=false per the brief; content checked at the target. All points stated. 'finding the simplest solution possible, and only increasing complexity when needed' (38). Three core principles: simplicity, transparency about planning steps, and the ACI through documentation and testing (112-115). 'ground truth' from the environment at each step; stopping conditions such as a maximum number of iterations (98). Evaluator-optimizer needs clear evaluation criteria and measurable value from iteration (93). Coding products making complex multi-file changes are the orchestrator-workers example (88). Fix: cite the /research/ URL.

#### ASB/ANT-12: How we built our multi-agent research system

Status: Confirmed (the cited URL redirects; content checked at the redirect target).

- Each subagent needs an objective, an output format, guidance on which tools and sources to use, and clear task boundaries. Without detailed task descriptions, agents duplicate work, leave gaps or misread the task.
- Scale effort to query complexity.
- Multi-agent systems use about 15x the tokens of chat (single agents about 4x).
- Start evaluating immediately with small samples (about 20 real queries). Think like your agents by watching their step-by-step behavior.
- *Fact-checker's note:* REDIRECTED: 301 to /research/multi-agent-research-system; content checked there. Objective, output format, tool and source guidance, and task boundaries; duplicate work and gaps; subagents 'misinterpreted the task' (49). Scale effort to query complexity (50). About 4x tokens for agents and 15x for multi-agent, versus chat (39). Start evaluating with about 20 queries (59). 'Think like your agents' by watching step-by-step (48). Context: the 15x figure supports a counter-argument; the article says multi-agent pays off only when the task value is high.

#### ASB/ANT-13: Effective context engineering for AI agents

Status: Confirmed (the cited URL redirects; content checked at the redirect target).

- Aim for the smallest possible set of high-signal tokens. 'Minimal' does not necessarily mean short.
- Write system prompts at the 'right altitude', avoiding both brittle hardcoded if-else logic and vague guidance that falsely assumes shared context.
- Organize prompts into distinct sections with XML tags or Markdown headers.
- Avoid stuffing a laundry list of edge cases into a prompt; curate diverse, canonical examples instead. Bloated or overlapping tool sets create ambiguous decision points.
- Subagents explore with clean context windows and return condensed summaries, often 1,000-2,000 tokens. For long horizons, use compaction and structured note-taking.
- *Fact-checker's note:* REDIRECTED: 301 to /research/effective-context-engineering-for-ai-agents; content checked there. Smallest set of high-signal tokens (41); 'minimal does not necessarily mean short' (45). Right altitude, between brittle if-else hardcoding and guidance that falsely assumes shared context (42-43). Laundry list of edge cases versus diverse, canonical examples (49). Bloated tool sets and ambiguous decision points (48). Condensed summaries, often 1,000-2,000 tokens (76). Compaction (65) and structured note-taking (69). Slight OVERSTATEMENT by omission: the XML/Markdown sections advice (44) comes with the hedge 'the exact formatting of prompts is likely becoming less important as models become more capable'.

#### ASB/ANT-14: Writing effective tools for agents — with agents

Status: Confirmed (the cited URL redirects; content checked at the redirect target).

- Choose which tools to implement (and which not to), namespace them to set clear boundaries, return meaningful context, and keep responses token-efficient.
- Prompt-engineer tool descriptions. Build an evaluation of realistic, multi-step tasks and measure changes against it.
- *Fact-checker's note:* REDIRECTED: 301 to /research/writing-tools-for-agents; content checked there. Lines 34-38 list choosing tools to implement and not to implement, namespacing for clear boundaries, returning meaningful context, token-efficient responses, and prompt-engineering tool descriptions. Build evaluations to measure tool performance (39, 55-56). Realistic tasks: 'Strong evaluation tasks might require multiple tool calls—potentially dozens' (59).

#### ASB/ANT-15: Equipping agents for the real world with Agent Skills

Status: Confirmed (the cited URL redirects; content checked at the redirect target).

- SKILL.md must start with YAML frontmatter containing name and description. Only that metadata is pre-loaded at startup, which is the first level of progressive disclosure.
- Start with evaluation: find real capability gaps on representative tasks before writing a skill. Pay special attention to name and description.
- *Fact-checker's note:* REDIRECTED: 301 to /research/equipping-agents-for-the-real-world-with-agent-skills; content checked there. SKILL.md 'must start with YAML frontmatter' containing name and description, pre-loaded at startup, which is 'the first level of progressive disclosure' (34-36). 'Start with evaluation': find gaps on representative tasks (57). 'Pay special attention to the name and description' (59).

#### ASB/ANT-16: Effective harnesses for long-running agents

Status: Confirmed (the cited URL redirects; content checked at the redirect target).

- Work on only one feature at a time; incremental progress counters the tendency to do too much at once.
- Leave the environment in a clean state and leave structured progress artifacts for the next session.
- Keep the feature list in JSON, which the model is less likely to overwrite than Markdown. Agents may change only the passes field. 'It is unacceptable to remove or edit tests.'
- *Fact-checker's note:* REDIRECTED: 301 to /research/effective-harnesses-for-long-running-agents; content checked there. 'work on only one feature at a time', which addresses the tendency to do too much at once (57, 31). Clean state and structured progress artifacts such as claude-progress.txt (33-36). JSON feature list, edited only through the passes field; JSON is less likely to be overwritten than Markdown (55). 'It is unacceptable to remove or edit tests' is quoted correctly (55). Context: the article itself calls this a 'strongly-worded instruction'. That emphatic style is what ASB/ANT-08 and ASB/ANT-21 now advise against for current models, so don't copy the wording; the JSON-plus-passes mechanism is the transferable part.

#### ASB/ANT-17: Demystifying evals for AI agents

Status: Confirmed (the cited URL redirects; content checked at the redirect target).

- 20-50 simple tasks drawn from real failures is a great start.
- A good task is one where two domain experts would independently reach the same pass/fail verdict. Build balanced sets that test both should-occur and should-not-occur cases.
- Grade what the agent produced, not the path it took. Read transcripts to check that the graders work.
- Capability evals start with a low pass rate; regression evals should pass at close to 100%.
- *Fact-checker's note:* REDIRECTED: 301 to /research/demystifying-evals-for-ai-agents; content checked there. '20-50 simple tasks drawn from real failures is a great start' (210). Two domain experts reaching the same verdict independently (214). Balanced problem sets covering should-occur and shouldn't-occur cases (216-217). 'grade what the agent produced, not the path it took' (223). Read transcripts to know whether graders work (230-231). Capability evals start at a low pass rate; regression evals should be at 'nearly 100%' (115-116).

#### ASB/ANT-18: Harness design for long-running application development

Status: Confirmed (the cited URL redirects; content checked at the redirect target).

- A planner / generator / evaluator architecture. Self-evaluation is lenient, and tuning a standalone skeptical evaluator is far more tractable than making a generator critical of its own work.
- Before each sprint, the generator and evaluator negotiate a 'sprint contract' that defines done before any code is written. QA then exercises the running app (Playwright) against the contract's test criteria.
- Every harness component encodes an assumption about what the model can't do on its own. Stress-test those assumptions, because they go stale as models improve.
- *Fact-checker's note:* REDIRECTED: 301 to /research/harness-design-long-running-apps; content checked there. Planner, generator and evaluator (29). Self-evaluation is too generous; tuning a standalone skeptical evaluator is 'far more tractable' (35-36). Sprint contract negotiated before each sprint; evaluator exercises the running app through Playwright against its test criteria (59-60, 94). Every harness component encodes an assumption, to be stress-tested because assumptions 'go stale' (105). SIGNIFICANT OMISSION, likely cherry-picked: in the same article the author then REMOVED the sprint construct entirely ('Removing the sprint construct', 108-111) once Opus 4.6 could handle the work without decomposition, and moved the evaluator to a single pass at the end. That run's evaluator was useful only near the edge of what the model could do alone. For a team that runs in sprints, this is the strongest counter-evidence in the source set and should be presented to the PO.

#### ASB/ANT-19: Building a C compiler with a team of parallel Claudes

Status: Confirmed (the cited URL redirects; content checked at the redirect target).

- Write extremely high-quality tests: the task verifier must be nearly perfect, or Claude solves the wrong problem. Add tests as new failure modes are observed.
- Parallel agents claim tasks with a simple lock file (current_tasks/) so two agents don't solve the same problem. Specialized agents handle docs, code quality and sub-tasks.
- Maintain extensive READMEs and progress files. Use a known-good oracle (GCC) when tests saturate.
- *Fact-checker's note:* REDIRECTED: 301 to /research/building-c-compiler; content checked there. 'Write extremely high-quality tests': the verifier must be 'nearly perfect' or Claude solves the wrong problem; new tests were added as failure modes appeared (57-58). Lock files in current_tasks/ (50-51). Specialized agents for documentation, code quality and sub-tasks (47, 71). Extensive READMEs and progress files (62). GCC as a known-good oracle (69).

#### ASB/ANT-20: An update on recent Claude Code quality reports (Apr 23, 2026 postmortem)

Status: Confirmed (the cited URL redirects; content checked at the redirect target).

- A one-line system-prompt instruction to reduce verbosity caused a measurable quality drop (3% on one eval). Internal evals did not catch it at first.
- Remedy: run a broad per-model eval suite for every system-prompt change, keep running line-by-line ablations, and use soak periods and gradual rollout for changes that could trade off against intelligence.
- *Fact-checker's note:* REDIRECTED: 301 to /research/april-23-postmortem; content checked there. A system-prompt instruction to reduce verbosity ('Length limits: keep text between tool calls to ≤25 words...', 57) hurt quality; ablations showed a 3% drop on one eval (59). Weeks of internal testing showed no regressions at first (58). Remedy: a broad per-model eval suite for every system-prompt change, continued ablations, soak periods, gradual rollouts (62). Minor nuance: the source says the change hurt quality 'in combination with other prompt changes' (33), and the instruction was two sentences rather than strictly one line.

#### ASB/ANT-21: Prompting best practices (Claude API docs; former be-clear-and-direct, multishot, XML-tags, system-prompt/role and long-context pages now redirect here)

Status: Confirmed.

- Treat Claude as a brilliant but new employee. Key test: a colleague with minimal context should be able to follow the prompt. Use numbered steps when order or completeness matters.
- Give the context and motivation (the why) behind instructions.
- Use 3-5 relevant, diverse examples wrapped in <example>/<examples> tags.
- Use consistent, descriptive XML tag names to separate instructions, context, examples and inputs.
- A role in the system prompt focuses behavior; even one sentence makes a difference.
- Put long documents at the top and the query at the end (up to 30% better).
- Newer models overtrigger on aggressive language. Replace 'CRITICAL: You MUST' with 'Use this tool when...' and remove over-prompting.
- Watch for subagent overuse. Say when subagents are warranted (parallel, isolated, independent work) and when to work directly.
- Ask for general solutions, not ones that only pass the tests. If a test is wrong, report it rather than working around it.
- *Fact-checker's note:* 200. 'brilliant but new employee'; the minimal-context colleague test; numbered steps when order or completeness matters (40-45). Give the motivation behind instructions (63). 3-5 examples in <example>/<examples> tags (89-92). 'consistent, descriptive tag names' (101). 'Even a single sentence makes a difference' for a role (106). Long data at the top, query at the end, 'up to 30 percent' better (243-246). Soften 'CRITICAL: You MUST' and remove over-prompting (488, 527). The source ties the overtriggering to Opus 4.5 and 4.6. Watch for subagent overuse; say when subagents are warranted (parallel, isolated, independent) (925-930). General solutions, not test-specific ones; 'if any of the tests are incorrect, please inform me rather than working around them' (981-996).

#### ASB/ANT-22: Prompting Claude Opus 5

Status: Confirmed.

- Opus 5 verifies its own work without being told. Remove explicit verification instructions such as 'use a subagent to verify', which cause over-verification; legacy verification scaffolding has the same effect.
- Opus 5 delegates more readily. Delegate only large, genuinely independent work; don't use subagents to double-check your own work; keep spawn counts low or set deterministic caps (spawn depth, concurrency, max_budget_usd).
- Constrain scope on narrow tasks: deliver what was asked, and flag a better approach in one sentence instead of silently changing the task.
- Match document length to what the task needs, with no filler sections or redundant summaries.
- *Fact-checker's note:* 200. Opus 5 verifies its own work; remove instructions like 'use a subagent to verify'; legacy verification scaffolding has the same effect (61, 81). Delegates more readily; delegate only large, independent work; don't use subagents to double-check your own work; keep spawn counts low or set deterministic caps (spawn depth, concurrency, max_budget_usd) (71-77). Constrain scope: deliver what was asked and flag a better approach in a sentence (63-66). Match document length; no filler sections or redundant summaries (53-56). Counterpoint for the PO: this conflicts with the project's heavy layered verification steps (fact-checkers and repeated QA re-runs). ASB/ANT-08 separates self-verification, which is redundant, from an independent fresh-context reviewer, which is useful, so independent review is still supported.

#### ASB/ANT-23: Skill authoring best practices (Claude API docs)

Status: Confirmed.

- Concise is key; the context window is a public good. Assume Claude is already very smart and challenge each paragraph: 'Does this justify its token cost?'
- Set degrees of freedom to match how fragile the task is: exact scripts for fragile ops, prose for context-dependent ones.
- Descriptions are always written in third person and state both what the skill does and when to use it. name is at most 64 characters, lowercase/digits/hyphens only.
- SKILL.md body under 500 lines. References one level deep. A table of contents for reference files over 100 lines.
- Build evaluations first (at least three scenarios), establish a baseline without the skill, write minimal instructions, then iterate.
- *Fact-checker's note:* 200. 'Concise is key'; context window is 'a public good'; 'Claude is already very smart'; 'Does this paragraph justify its token cost?' (13-30). Set degrees of freedom by fragility (61, 111). Descriptions 'Always write in third person'; name at most 64 characters, lowercase letters, digits and hyphens (153-154, 206). Body under 500 lines; references one level deep; table of contents for reference files over 100 lines (257, 382, 410). Build evaluations first: three scenarios, a baseline without the skill, minimal instructions, iterate (748-758; checklist 'At least three evaluations', 1172).

#### ASB/ANT-24: anthropics/skills — skill-creator SKILL.md

Status: Confirmed.

- The description is the primary triggering mechanism; all 'when to use' info goes there, not in the body. Claude tends to undertrigger skills, so descriptions should be slightly 'pushy' and list trigger contexts.
- Keep SKILL.md under 500 lines and add hierarchy when approaching that. Draft test cases, run evals, and rewrite from the results.
- The repo's template/SKILL.md is just name plus description frontmatter and an instructions body.
- *Fact-checker's note:* 200. The description is 'the primary triggering mechanism'; 'All "when to use" info goes here, not in the body'; Claude tends to 'undertrigger', so make descriptions 'a little bit "pushy"' (67). Keep SKILL.md under 500 lines and add hierarchy when approaching the limit (90, 96). Draft test cases, run evals, iterate (16, 22). Also fetched template/SKILL.md (200): name plus description frontmatter and an instructions body. Tension to note: 'pushy' descriptions here versus ASB/ANT-21's warning that current models overtrigger on aggressive language. The two cover different things (skill triggering versus instruction emphasis), but the docs should not merge them.

#### ASB/ANT-25: anthropics/claude-plugins-official — feature-dev code-reviewer and code-explorer agents

Status: Confirmed.

- The official reviewer agent is 46 lines (explorer 51) with frontmatter name, description, tools, model: sonnet and color.
- The reviewer's tools are read-only (Glob, Grep, LS, Read, NotebookRead, WebFetch, TodoWrite, WebSearch, KillShell, BashOutput): no Edit, Write or Bash.
- The body has a role sentence, then Review Scope, Core Responsibilities, a confidence rubric (0-100) with 'Only report issues with confidence >= 80', and Output Guidance (file:line, guideline reference, concrete fix, grouped by severity, and an explicit 'no issues' summary).
- *Fact-checker's note:* 200. The file is 46 lines (wc -l). Frontmatter: name, description, tools, model: sonnet, color: red. Tools are exactly Glob, Grep, LS, Read, NotebookRead, WebFetch, TodoWrite, WebSearch, KillShell, BashOutput; no Edit, Write or Bash. The body has a role sentence, Review Scope, Core Review Responsibilities, Confidence Scoring 0-100, 'Only report issues with confidence ≥ 80', and Output Guidance (file path and line, guideline reference, concrete fix, grouped by severity, a brief summary if no issues). code-explorer.md is also 200, 51 lines, with the same tool list. Nuance: KillShell can terminate background shells, so 'read-only' really means no file writes and no new shells.

#### ASB/ANT-26: anthropics/claude-code plugins/README.md

Status: Confirmed.

- Official plugins moved to anthropics/claude-plugins-official.
- Plugin layout: .claude-plugin/plugin.json, commands/, agents/, skills/, hooks/; installable via /plugin or .claude/settings.json.
- *Fact-checker's note:* 200. 'Anthropic's plugins are developed in claude-plugins-official'; new plugins belong there. The layout shows .claude-plugin/plugin.json, commands/, agents/, skills/, hooks/ and .mcp.json. Plugins install with /plugin or through .claude/settings.json. Wording nuance: the marketplace in this repo 'still lists them', so 'moved' means development moved, not that the listing was removed.

#### ASB/ANT-27: anthropics/claude-code-action README

Status: Confirmed.

- A GitHub Action for PRs and issues, configured through unified `prompt` and `claude_args` inputs aligned with the Claude Code SDK. It responds to @claude mentions or runs explicit automation prompts.
- *Fact-checker's note:* 200. A general-purpose action for GitHub PRs and issues; responds to @claude mentions, issue assignments, or automation tasks with explicit prompts; 'Unified prompt and claude_args inputs ... aligned with Claude Code SDK'.

#### ASB/ANT-28: anthropics/anthropic-cookbook README (redirects to claude-cookbooks)

Status: Confirmed.

- Includes a sub-agents notebook (Haiku as sub-agent with Opus) and a cost-optimization checklist that measures pass rate and cost per task to find the Pareto-optimal agent configuration.
- *Fact-checker's note:* 200. The raw URL itself did not redirect (0 redirects) but serves the 'Claude Cookbooks' README. Recipe table: 'Sub-agents: Learn how to use Haiku as a sub-agent in combination with Opus' and 'Cost optimization: ... measuring pass rate and cost per task to find the Pareto-optimal configuration'. Both points confirmed.

### 4.2 SDD

#### ASB/SDD-01: Specification-Driven Development (SDD) - spec-driven.md

Status: Confirmed.

- 'The Power Inversion': specs become the source of truth, and plans and code are 'continuously regenerated output'.
- Core principles include 'Continuous Refinement' (consistency is checked all the time, not once at a gate) and 'Bidirectional Feedback' (production metrics and incidents feed back into the spec).
- Templates hold the LLM back from leaking implementation details early, force explicit [NEEDS CLARIFICATION] markers, and use checklists and constitutional gates (Simplicity, Anti-Abstraction).
- Test-first file order: 'contracts -> integration -> e2e -> unit', then the source files that make the tests pass.
- 'No speculative or "might need" features'. Every feature must trace back to a concrete user story with clear acceptance criteria.
- The page is vendor philosophy. It offers no empirical evidence that SDD improves outcomes.
- *Fact-checker's note:* HTTP 200, 26229 bytes. All key points are stated. 'The Power Inversion' heading is at line 3. Line 15: 'specifications as the central source of truth, with implementation plans and code as the continuously regenerated output'. Continuous Refinement is at line 53 and Bidirectional Feedback at line 57. Premature implementation details: line 169. [NEEDS CLARIFICATION] is mandated at lines 182-190. Checklists are called 'unit tests for the specification' at line 194. The Simplicity and Anti-Abstraction gates are at lines 213/218. Test order at line 245 is 'contract → integration → e2e → unit', then line 246 'Create source files to make tests pass'. The page credits this order to 'The implementation template'. The 'might need' checklist line is at 256, and line 260 says 'Every feature must trace back to a concrete user story with clear acceptance criteria.' A grep for evidence, study, percent or benchmark-as-result found no empirical evidence, so the 'vendor philosophy' caveat holds. Caveat for the audit: the 'test-first' framing conflicts with ASB/SDD-04, which makes tests OPTIONAL. Article IX (line 342) is 'Integration-First Testing', which 'Prioritizes real-world testing over isolated unit tests'.

#### ASB/SDD-02: spec-kit spec-template.md (Feature Specification template)

Status: Confirmed.

- Mandatory sections: User Scenarios & Testing, Requirements, Success Criteria. Other sections: Edge Cases, Key Entities, Assumptions.
- User stories are prioritised (P1, P2, ...). Each one must be INDEPENDENTLY TESTABLE and a viable MVP slice, and carries 'Why this priority', 'Independent Test' and Given/When/Then acceptance scenarios.
- Functional requirements are written as 'FR-001: System MUST ...'. Unclear points are marked [NEEDS CLARIFICATION: ...].
- Success criteria (SC-001...) 'must be technology-agnostic and measurable'.
- Assumptions are written down explicitly when the input left details unspecified.
- *Fact-checker's note:* HTTP 200. The template marks User Scenarios & Testing (line 11), Requirements (line 81) and Success Criteria (line 106) '(mandatory)'. Edge Cases, Key Entities ('include if feature involves data') and Assumptions are also present. Line 15: 'Each user story/journey must be INDEPENDENTLY TESTABLE', and a single one should still be a 'viable MVP'. P1/P2/P3 priorities, 'Why this priority', 'Independent Test' and Given/When/Then are all present. The template uses 'FR-001: System MUST' and [NEEDS CLARIFICATION: ...] (lines 98-99), and says success criteria 'must be technology-agnostic and measurable' (line 110). The Assumptions section covers 'reasonable defaults chosen when the feature description did not specify certain details'. Accurate.

#### ASB/SDD-03: spec-kit plan-template.md (Implementation Plan template)

Status: Confirmed.

- The plan links back to the spec and holds a Technical Context: language, dependencies, storage, testing, platform, performance goals, constraints, scale. Unknowns are marked NEEDS CLARIFICATION.
- 'Constitution Check - GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.'
- Phase outputs: research.md, data-model.md, quickstart.md, contracts/. tasks.md comes from a separate step.
- 'Complexity Tracking' table (Violation | Why Needed | Simpler Alternative Rejected Because), filled only when a constitution violation has to be justified.
- *Fact-checker's note:* HTTP 200. Spec link at line 3. Technical Context (lines 21-37) covers Language, Dependencies, Storage, Testing, Platform, Project Type, Performance, Constraints and Scale, mostly 'or NEEDS CLARIFICATION'. Storage uses 'or N/A' instead, a trivial difference. Line 41: 'GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.' Lines 52-56 list the phase outputs research.md, data-model.md, quickstart.md and contracts/, and note that tasks.md is 'NOT created by' the plan command. Complexity Tracking is at line 106: 'Fill ONLY if Constitution Check has violations that must be justified', with the columns Violation | Why Needed | Simpler Alternative Rejected Because. Accurate.

#### ASB/SDD-04: spec-kit tasks-template.md (Task list template)

Status: Confirmed.

- Task format is '[ID] [P?] [Story] Description': [P] means it can run in parallel (different files, no dependencies), and [Story] is the user-story label. Descriptions include exact file paths.
- Tasks are grouped by user story so each story can be implemented, tested and delivered on its own. A 'Foundational' phase blocks all story work. Each story ends with a 'Checkpoint'.
- Test tasks: 'Write these tests FIRST, ensure they FAIL before implementation'.
- The template also says 'Tests are OPTIONAL - only include them if explicitly requested in the feature specification'. This repo's rule is stricter: tests are mandatory.
- *Fact-checker's note:* HTTP 200. The format line '[ID] [P?] [Story] Description' is at line 16. [P] means 'different files, no dependencies' and [Story] is defined at line 19. Line 20: 'Include exact file paths'. Tasks 'MUST be organized by user story', each 'Implemented independently / Tested independently / Delivered as an MVP increment'. The Foundational phase is a 'CRITICAL: No user story work can begin until this phase is complete'. Each story has a Checkpoint. Line 85: 'Write these tests FIRST, ensure they FAIL before implementation'. Line 12: 'Tests are OPTIONAL - only include them if explicitly requested in the feature specification.' The key points are accurate, and the researcher correctly flagged that the repo's rule is stricter.

#### ASB/SDD-05: spec-kit /specify command definition

Status: Confirmed.

- 'Focus on WHAT users need and WHY. Avoid HOW to implement (no tech stack, APIs, code structure). Written for business stakeholders, not developers.'
- 'LIMIT: Maximum 3 [NEEDS CLARIFICATION] markers total', kept for critical decisions only. Each one becomes a question with options A/B/C/Custom.
- The spec-quality checklist includes: no implementation details; no [NEEDS CLARIFICATION] left; requirements testable and unambiguous; success criteria technology-agnostic. Validation runs at most 3 iterations.
- 'Think like a tester: every vague requirement should fail the testable and unambiguous checklist item.'
- *Fact-checker's note:* HTTP 200. Quick Guidelines (lines 286-288) contain the WHAT/WHY quote, 'Avoid HOW to implement (no tech stack, APIs, code structure)' and 'Written for business stakeholders, not developers.' Line 132: 'LIMIT: Maximum 3 [NEEDS CLARIFICATION] markers total'. Line 303 limits these to critical decisions. Questions use an option table A/B/C/Custom (lines 217-222). The checklist items appear at lines 161-171. Line 200 says 'max 3 iterations'. Line 308 is the 'Think like a tester' quote. Accurate.

#### ASB/SDD-06: spec-kit /clarify command definition

Status: Confirmed.

- A structured ambiguity and coverage scan marks each category Clear / Partial / Missing.
- At most 5 questions per session, presented 'EXACTLY ONE question at a time'. Each is multiple choice (2-5 options) or a short answer of 5 words or fewer.
- Only questions whose answers materially change architecture, data model, task breakdown, test design, UX, operations or compliance are asked. They are ranked by Impact x Uncertainty.
- The answers are written back into the spec.
- *Fact-checker's note:* HTTP 200. Line 73: 'mark status: Clear / Partial / Missing'. Line 130: 'Maximum of 5 total questions across the whole session'. Line 141: 'Present EXACTLY ONE question at a time'. Questions are multiple choice with 2-5 options or '<=5 words' (lines 132-133). The materiality list at line 134 matches the key point. Answers are integrated into and saved back to the spec after each one (lines 182-208). Slight overstatement: the page uses Impact * Uncertainty to pick the top 5 only 'If more than 5 categories remain unresolved' (line 138). It does not say every question is ranked that way.

#### ASB/SDD-07: spec-kit /analyze command definition

Status: Confirmed.

- A 'non-destructive cross-artifact consistency and quality analysis across spec.md, plan.md, and tasks.md' run before implementation. It is 'STRICTLY READ-ONLY'.
- Detection passes: duplication, ambiguity, underspecification, constitution alignment, coverage gaps, inconsistency (including terminology drift).
- Severity: CRITICAL = violates a constitution MUST, a core artifact is missing, or a requirement with zero coverage blocks baseline function. HIGH = conflicting requirement or untestable acceptance criterion. MEDIUM = terminology drift or missing NFR coverage.
- Metrics: coverage % (requirements with at least one task), ambiguity count, duplication count, critical count.
- Constitution conflicts are fixed in the spec, plan or tasks, never by watering down the principle. Changing a principle needs a separate, explicit constitution update.
- *Fact-checker's note:* HTTP 200. The 'non-destructive cross-artifact consistency and quality analysis across spec.md, plan.md, and tasks.md' quote is at line 2, and 'STRICTLY READ-ONLY' is at line 58. Passes A-F (lines 119-148) are Duplication, Ambiguity, Underspecification, Constitution Alignment, Coverage Gaps and Inconsistency, with 'Terminology drift' under F. The severity definitions at lines 157-159 match. The metrics at lines 187-190 match. Line 60: constitution conflicts 'require adjustment of the spec, plan, or tasks—not dilution, reinterpretation, or silent ignoring', and a principle change 'must occur in a separate, explicit constitution update'. Accurate. Minor point: HIGH also covers 'Duplicate' and 'ambiguous security/performance attribute', and MEDIUM also covers 'underspecified edge case'.

#### ASB/SDD-08: spec-kit constitution-template.md

Status: Confirmed.

- Structure: Core Principles (example: 'Test-First (NON-NEGOTIABLE)'), additional constraints, development workflow and quality gates, Governance.
- Example governance text: 'Constitution supersedes all other practices; Amendments require documentation, approval, migration plan'; 'All PRs/reviews must verify compliance; Complexity must be justified'.
- Footer: 'Version | Ratified | Last Amended'.
- *Fact-checker's note:* HTTP 200. Core Principles includes the example 'III. Test-First (NON-NEGOTIABLE)'. Sections 2 and 3 have the examples 'Additional Constraints...' and 'Development Workflow, Review Process, Quality Gates'. The Governance comments read 'Constitution supersedes all other practices; Amendments require documentation, approval, migration plan' and 'All PRs/reviews must verify compliance; Complexity must be justified'. The footer is 'Version | Ratified | Last Amended'. Accurate. Note that all of these are example placeholder comments, not prescriptions.

#### ASB/SDD-09: spec-kit /constitution command definition (not confirmed)

Status: Not confirmed: the semver rules and the Governance-section rule are on the page, but the claim that the Sync Impact Report lists dependent templates to update is not; the page says dependent templates are not modified, and the report is temporary scratch material removed before commit.

- The version moves by semver. MAJOR = backward-incompatible removal or redefinition of a principle. MINOR = a new principle or materially expanded guidance. PATCH = clarification or wording.
- The Governance section must list the amendment procedure, the versioning policy and the compliance-review expectations.
- A Sync Impact Report (old -> new version, changed principles, dependent templates to update) is produced for human review of each amendment.
- *Fact-checker's note:* HTTP 200. Two of the three key points are confirmed. The semver MAJOR/MINOR/PATCH definitions are at lines 101-103, and line 110 says 'Ensure Governance section lists amendment procedure, versioning policy, and compliance review expectations.' NOT CONFIRMED: the claim that the Sync Impact Report lists 'dependent templates to update'. Lines 112-119 list the report contents as version change, modified principles, added sections, removed sections and follow-up TODOs. The Scope Guard (lines 22-23) says the opposite: 'Dependent templates and commands read the constitution at runtime and are not modified here.' The 'for human review' part is supported, but the page adds that the report is 'temporary scratch material ... expected to be removed before the amended constitution file is committed'. The key point leaves out that it is temporary.

#### ASB/SDD-10: spec-kit /implement command definition

Status: Confirmed.

- Checklists are a read-only gate. If any checklist has unchecked items, the status is FAIL and the agent asks before going on.
- '[x] means the reviewer determined the requirements-quality criterion is satisfied; it does NOT mean implementation work is complete.'
- *Fact-checker's note:* HTTP 200. Line 57: 'Treat checklist markers as a read-only gate'. Line 77 marks the status FAIL when any checklist has unchecked items. Line 81 then says STOP and ask 'Do you want to proceed with implementation anyway? (yes/no)'. The [x] quote at line 59 is verbatim, but it is scoped 'For custom checklists'. Accurate. Note for the audit: this is a soft gate, because the user can answer yes and go on, so it is not a hard block.

#### ASB/SDD-11: spec-kit README

Status: Confirmed.

- Minimal flow: constitution (once per project) -> specify -> plan -> tasks -> implement -> converge, repeated per feature.
- Run the steps 'one at a time, reviewing each result before continuing'.
- 'Repeat implement and converge until convergence reports Converged.'
- *Fact-checker's note:* HTTP 200. Lines 105-107: 'Create a constitution once per project and repeat the remaining steps for each feature ... one at a time, reviewing each result before continuing.' The flow constitution, specify, plan, tasks, implement, converge is at lines 113-118. Line 121: 'Repeat implement and converge until convergence reports `Converged`.' Accurate. clarify, checklist and analyze are not in the minimal flow; the README defers them to 'the SDD walkthrough'.

#### ASB/SDD-12: Kiro README (kirodotdev/Kiro)

Status: Confirmed.

- 'Use Specs to structure requirements, design decisions, and implementation tasks, then run Requirements Analysis to find contradictions, ambiguities, and gaps before coding begins.'
- 'Use correctness with property-based testing to turn requirements into executable properties and exercise them across generated inputs that example-based tests may miss.'
- Checkpoints and rewind let you inspect or undo agent changes.
- *Fact-checker's note:* HTTP 200. Line 41 states the Specs and Requirements Analysis quote verbatim. Line 42 states the property-based testing quote verbatim. Line 46 mentions 'inspect or undo changes with checkpoints and rewind'. Accurate. The README links to kiro.dev for detail, and that site is unverified (ASB/SDD-13).

#### ASB/SDD-13: Kiro docs - Specs (unverified)

Status: Unverified: kiro.dev blocked in the research session; not fetched.

- NOT FETCHED: kiro.dev is outside this session's allowed network (DNS failure and a 403 from the proxy). It is widely reported that Kiro specs are requirements.md (EARS notation), design.md and tasks.md, but this was not checked against the page.
- *Fact-checker's note:* none; unverified sources were not re-checked.

#### ASB/SDD-14: Understanding Spec-Driven-Development: Kiro, spec-kit, and Tessl (Birgitta Böckeler) (unverified)

Status: Unverified: martinfowler.com blocked; content seen only in search results.

- NOT FETCHED: martinfowler.com is not allowed in this session. Secondary search results only, unverified: it defines three levels (spec-first, spec-anchored, spec-as-source), finds spec-kit verbose, and notes that agents ignored parts of the constitution.
- *Fact-checker's note:* none; unverified sources were not re-checked.

#### ASB/SDD-15: Thoughtworks Technology Radar - Spec-driven development (unverified)

Status: Unverified: thoughtworks.com blocked; not fetched.

- NOT FETCHED: thoughtworks.com is not allowed in this session. The ring and the blip text are unknown.
- *Fact-checker's note:* none; unverified sources were not re-checked.

#### ASB/SDD-16: Documenting Architecture Decisions (Michael Nygard, 2011) (unverified)

Status: Unverified: cognitect.com blocked; not fetched.

- NOT FETCHED: cognitect.com is not allowed in this session. Its template is reproduced in ASB/SDD-17 (verified). Rules often attributed to it (ADRs are immutable once accepted, superseded ADRs stay in place, 1-2 pages long) were NOT verified.
- *Fact-checker's note:* none; unverified sources were not re-checked.

#### ASB/SDD-17: adr-tools ADR template (Nygard format)

Status: Confirmed.

- Sections: '# NUMBER. TITLE', Date, Status, Context ('the issue motivating this decision, and any context that influences or constrains the decision'), Decision ('the change that we're proposing or have agreed to implement'), Consequences ('what becomes easier or more difficult to do and any risks introduced by the change that will need to be mitigated').
- *Fact-checker's note:* HTTP 200, 364 bytes. The file matches the key point exactly: '# NUMBER. TITLE', Date, Status, plus the Context, Decision and Consequences wording, all verbatim.

#### ASB/SDD-18: adr-tools ADR 0001 Record architecture decisions

Status: Confirmed.

- The canonical first ADR adopts ADRs 'as described by Michael Nygard'. It is numbered, dated and has Status: Accepted.
- *Fact-checker's note:* HTTP 200. The ADR is '# 1. Record architecture decisions', dated 2016-02-12, Status Accepted, and adopts 'Architecture Decision Records, as described by Michael Nygard'. Accurate. The Nygard link points to the old thinkrelevance.com domain.

#### ASB/SDD-19: adr.github.io - Architectural Decision Records (index.md source)

Status: Confirmed.

- 'An Architectural Decision Record (ADR) captures a single AD and its rationale'. An AD addresses 'a functional or non-functional requirement that is architecturally significant'.
- 'The collection of ADRs created and maintained in a project constitute its decision log.'
- ADR use 'can be extended to design and other decisions ("any decision record")'.
- The site points to the Y-statement format (Zdun et al.) and to MADR.
- *Fact-checker's note:* HTTP 200. Line 11: 'An Architectural Decision Record (ADR) captures a single AD and its rationale'. Line 9 covers the architecturally significant functional or non-functional requirement. Line 13 is the decision log quote. Line 14 covers 'any decision record'. Line 34 mentions Zdun et al. and the Y-statement format. Weak support for 'points to MADR': in this index.md source, MADR appears only in the filename of a German JavaLand 2026 talk PDF (line 24), not as a recommendation. The rendered site navigation may link MADR, but that was not checked. Treat that sub-claim as thin.

#### ASB/SDD-20: Cucumber docs - Behaviour-Driven Development

Status: Confirmed.

- BDD's three practices are Discovery ('what it could do'), Formulation ('what it should do') and Automation. Each works on a small change, for example a user story.
- 'If you're new to BDD, discovery is the right place to start. You won't get much joy from the other two practices until you've mastered discovery.'
- Documentation and automated tests are 'nice side-effects'. The real goal is working software reached through conversation.
- Writing executable specifications together gives a shared language and 'problem-domain terminology all the way down into the code'.
- *Fact-checker's note:* HTTP 200. Line 45 names the practices Discovery, Formulation and Automation. Line 56 has Discovery as 'What it could do' and line 74 has Formulation as 'What it should do'. Line 39 says to take a small change, a User Story. Line 72 is the 'new to BDD ... discovery' quote, verbatim. Line 62 calls documentation and automated tests 'nice side-effects', with the real goal of 'valuable, working software' reached through conversations. Line 83 covers the shared language and 'problem-domain terminology all the way down into the code'. Accurate.

#### ASB/SDD-21: Cucumber docs - Example Mapping

Status: Confirmed.

- Before a story is pulled into development, a conversation clarifies and confirms its acceptance criteria.
- Card types: story (yellow), rules or acceptance criteria (blue), examples (green), open questions (red). New or deferred stories are split out.
- Keep going 'until the group is satisfied that the scope of the story is clear, or we run out of time'.
- *Fact-checker's note:* HTTP 200. The page opens: 'Before you pull a user story into development, it's crucial to have a conversation to clarify and confirm the acceptance criteria.' The cards are yellow for the story, blue for rules or acceptance criteria, green for examples and red for questions. New stories are 'sliced and deferred out of scope'. The stopping quote is verbatim. Accurate.

#### ASB/SDD-22: Cucumber docs - Who Does What? (Three Amigos)

Status: Confirmed.

- Three Amigos: the product owner (owns scope and decides which edge cases are in scope), the tester (scenarios and edge cases) and the developer (steps and technical constraints) discover examples together.
- Gherkin can later be written by a developer + tester pair 'as long as their output is actively reviewed by the product owner'.
- *Fact-checker's note:* HTTP 200. Lines 19-21: the product owner owns scope and 'is responsible for deciding what is within scope' for the edge cases the tester raises; the tester writes scenarios and edge cases; the developer writes Steps and covers 'roadblocks or requirements behind the scenes'. Lines 33-35: a developer and tester pair 'as long as their output is actively reviewed by the product owner (or business representative)'. Accurate. The page also says the whole team should write the Gherkin at first, and that meetings need not be limited to three people. The page opens by saying who does what 'depends on several factors', so it is not a fixed rule.

#### ASB/SDD-23: Cucumber docs - Discovery workshop

Status: Confirmed.

- Hold it 'as late as possible before development on a new User Story begins'.
- 3-6 people, with at least the Three Amigos present.
- 'About 25-30 minutes per story. If you need any more time than this, it's likely the story is far too large and should be broken down, or some of the specifics are missing.'
- *Fact-checker's note:* HTTP 200. Line 28: 'As late as possible before development on a new User Story begins'. Line 32: 'A good rule-of-thumb is 3-6 people, but at a bare minimum your Three Amigos'. Line 36: 'should ideally only last about 25-30 minutes per story...' with the story-too-large consequence. Accurate. The key point drops 'rule-of-thumb' and 'ideally'; these are heuristics, not rules.

#### ASB/SDD-24: Best practices for Claude Code

Status: Confirmed.

- Already cited in docs/research; re-verified today. https://www.anthropic.com/engineering/claude-code-best-practices serves the same page.
- 'Brainstorm with Claude first': 'Interview me until you could write the spec, then write it to SPEC.md'. Then 'start a fresh session to build from it, so the build begins with a clean context and a written definition of done.'
- 'Review against your spec': ask a reviewer to 'check every requirement is implemented and the listed edge cases have tests, report gaps that affect correctness and skip style'. Warning: 'A reviewer that's asked to find problems will always find something. If you fix every finding, you end up with extra abstraction layers and tests for cases that can't happen.'
- Instructions come in two kinds. Non-deterministic: prompt, CLAUDE.md, skills, 'no guarantee that it'll follow'. Deterministic: hooks, deny rules, managed settings, tests, CI, branch protection. 'If something has to happen every time, make it a hook, a deny rule, or a managed setting.'
- Keep CLAUDE.md short. It is loaded every session, and each line takes attention. The memory guide recommends staying under 200 lines.
- *Fact-checker's note:* HTTP 200. The alternate URL https://www.anthropic.com/engineering/claude-code-best-practices redirects here and serves a byte-identical page (cmp is identical). The page contains 'Interview me until you could write the spec, then write it to SPEC.md' and 'start a fresh session to build from it, so the build begins with a clean context and a written definition of done.' It also contains the review prompt 'check every requirement is implemented and the listed edge cases have tests, report gaps that affect correctness and skip style' and the 'will always find something ... extra abstraction layers and tests for cases that can't happen' warning, both verbatim. The deterministic/non-deterministic table lists prompt, CLAUDE.md and skills against hooks, deny rules, managed settings, tests, CI and branch protection, plus 'there's no guarantee that it'll follow your instructions' and 'If something has to happen every time, make it a hook, a deny rule, or a managed setting.' On CLAUDE.md: 'loads CLAUDE.md into every session, which means every line in it takes a little of Claude's attention', and 'The memory guide recommends staying under 200.' Accurate.

#### ASB/SDD-25: Common workflows - Plan before editing

Status: Confirmed.

- Plan mode: 'Claude reads files and proposes a plan but makes no edits until you approve.'
- Hand codebase exploration to subagents so that only the findings come back into the main context.
- *Fact-checker's note:* HTTP 200. 'Claude reads files and proposes a plan but makes no edits until you approve' is verbatim under 'Plan before editing'. Under 'Delegate research to subagents': 'Delegate the exploration so only the findings come back.' Accurate.

#### ASB/SDD-26: Effective harnesses for long-running agents

Status: Confirmed (the cited URL redirects; content checked at the redirect target).

- Already cited in docs/research; re-verified today.
- 'Based on the input spec, set up a structured JSON file with a list of end-to-end feature descriptions'. Each feature has steps and 'passes': false. Agents may only change the passes field: 'It is unacceptable to remove or edit tests'.
- JSON was chosen because 'the model is less likely to inappropriately change or overwrite JSON files compared to Markdown files'.
- Work on 'only one feature at a time'. Commit with descriptive messages and keep a progress file. A new session starts by reading the progress notes, the git log and a basic test.
- *Fact-checker's note:* The URL returns HTTP 308, a permanent redirect to https://www.anthropic.com/research/effective-harnesses-for-long-running-agents. Under the 'redirected URL is fetched=false' rule this is fetched=false, and the citation URL should be updated. The content at the redirect target (HTTP 200) confirms every key point. It has 'set up a structured JSON file with a list of end-to-end feature descriptions' with "passes": false. Agents edit 'only by changing the status of a passes field', with the instruction 'It is unacceptable to remove or edit tests because this could lead to missing or buggy functionality'. JSON was chosen because 'the model is less likely to inappropriately change or overwrite JSON files compared to Markdown files'. Agents work on 'only one feature at a time' and 'commit its progress to git with descriptive commit messages and ... write summaries of its progress in a progress file'. A session starts by reading the progress notes and git logs and running a basic test. Small precision point: the page says agents were 'prompted' to edit only the passes field ('strongly-worded instructions'). It was not a technical restriction.

#### ASB/SDD-27: EARS - Easy Approach to Requirements Syntax (Alistair Mavin) (unverified)

Status: Unverified: alistairmavin.com blocked; not fetched.

- NOT FETCHED: the host is not allowed in this session, and Wikipedia is also blocked. The EARS keyword templates (While / When / Where / If-Then ... the <system> shall ...) were not checked against the source.
- *Fact-checker's note:* none; unverified sources were not re-checked.

#### ASB/SDD-28: Specification by Example (Gojko Adzic) (unverified)

Status: Unverified: gojko.net blocked; not fetched, no claims drawn from it.

- NOT FETCHED: the host is not allowed in this session. No claims are drawn from it.
- *Fact-checker's note:* none; unverified sources were not re-checked.

### 4.3 AGL

#### ASB/AGL-01: The Scrum Guide (November 2020), diffable Markdown copy

Status: Confirmed.

- Three commitments: the Product Backlog has the Product Goal, the Sprint Backlog has the Sprint Goal, and the Increment has the Definition of Done.
- 'The Sprint Goal is the single objective for the Sprint.' The whole Scrum Team collaborates to define it, and it 'must be finalized prior to the end of Sprint Planning'. Scope can be renegotiated with the PO 'without affecting the Sprint Goal'.
- 'If a Product Backlog item does not meet the Definition of Done, it cannot be released or even presented at the Sprint Review. Instead, it returns to the Product Backlog for future consideration.'
- If the DoD is an organizational standard, every team follows it as a minimum. Multiple teams on one product 'must mutually define and comply with the same Definition of Done'.
- Three accountabilities: Developers, Product Owner and Scrum Master. 'Within a Scrum Team, there are no sub-teams or hierarchies.' The team is 'typically 10 or fewer people'.
- The PO 'may delegate the responsibility to others. Regardless, the Product Owner remains accountable.' 'The Product Owner is one person, not a committee.'
- Developers are always accountable for: creating the Sprint Backlog, instilling quality by adhering to a DoD, adapting their plan each day toward the Sprint Goal, and holding each other accountable.
- How to decompose PBIs into work items 'of one day or less' is 'at the sole discretion of the Developers'. 'The Developers who will be doing the work are responsible for the sizing.'
- 'Product Backlog items that can be Done by the Scrum Team within one Sprint are deemed ready for selection.' Refinement is an ongoing activity. The term 'Definition of Ready' does not appear anywhere in the guide (grep: only 2 hits for 'ready', both 'ready for selection').
- Timeboxes: Sprints are one month or less. For a one-month Sprint, Planning is at most 8 hours, the Daily Scrum is 15 minutes, Review at most 4 hours and Retrospective at most 3 hours. Shorter Sprints usually have shorter events.
- In Planning, forecast confidence comes from 'past performance, their upcoming capacity, and their Definition of Done'. Burn-downs, burn-ups and cumulative flows 'do not replace the importance of empiricism'.
- Retrospective: inspect individuals, interactions, processes, tools and the DoD. 'The most impactful improvements are addressed as soon as possible. They may even be added to the Sprint Backlog for the next Sprint.'
- Sprint Review is 'a working session' and not just a presentation. 'The Sprint Review should never be considered a gate to releasing value.' Multiple Increments may be created within a Sprint.
- Only the PO can cancel a Sprint, and only when the Sprint Goal becomes obsolete. The Product Goal is the long-term objective: the team must 'fulfill (or abandon) one objective before taking on the next'.
- *Fact-checker's note:* HTTP 200, 24800 bytes, 'November 2020'. All 14 key points were found verbatim or as faithful paraphrase. Matching lines: 75/79 (no sub-teams, typically 10 or fewer), 83 (three accountabilities), 105 (may delegate / remains accountable), 145 (one month or less), 159 (only the PO can cancel), 171 (whole team collaborates; finalized prior to end of Planning), 177 (past performance, capacity, DoD), 185/205/215 (8h/4h/3h, 'for shorter Sprints, the event is usually shorter'), 191 (15-minute), 232 (ready for selection; refinement is an ongoing activity), 241 (fulfill (or abandon)), 250 (single objective), 258 (multiple Increments; never a gate to releasing value), 269/271 (organizational-standard DoD; must mutually define). 'Definition of Ready' has 0 hits. CORRECTION: the claim 'grep: only 2 hits for ready, both ready for selection' is inaccurate. A case-insensitive grep for 'ready' matches 2 lines: line 157 is 'already happened' and line 232 is 'ready for selection'. So there is only ONE whole-word 'ready', and it is 'ready for selection'. The conclusion (no DoR in the guide) still holds. Caveat: this is a third-party mirror, not scrumguides.org (official=false is correctly flagged).

#### ASB/AGL-02: DORA's software delivery performance metrics (dora.dev guide, source file)

Status: Confirmed.

- DORA now uses five metrics. Throughput: change lead time, deployment frequency and failed deployment recovery time. Instability: change fail rate and deployment rework rate.
- Deployment rework rate is 'the ratio of deployments that are unplanned but happen as a result of an incident in production'.
- Pitfalls: setting metrics as a goal (Goodhart's law), relying on one metric, comparing different applications, siloed ownership, competing between teams, and measuring at the expense of improving.
- Apply the metrics per application or service, because context matters. Blending them across teams is problematic.
- Improvement loop: set a baseline, talk about friction, have the whole team commit to improving the biggest constraint, turn that into a plan with leading indicators (e.g. how long code reviews take), do the work, check progress in retrospectives, then repeat.
- *Fact-checker's note:* HTTP 200; updated 2026-01-05; author Nathen Harvey. The five metrics split as Throughput (change lead time, deployment frequency, failed deployment recovery time) and Instability (change fail rate, deployment rework rate). Rework rate is defined verbatim. The pitfalls are confirmed: metrics as goal / Goodhart, one metric to rule them all, disparate comparisons, siloed ownership, competing, measurement at the expense of improvement. The list also includes 'using industry as a shield', which the key point omits but does not contradict. The 'Context matters... blend metrics across multiple teams... problematic' passage is confirmed. The improvement loop (baseline, conversation, whole team commits, plan with leading indicators such as code review time, do the work, check progress incl. retrospectives, repeat) is confirmed.

#### ASB/AGL-03: A history of DORA's software delivery metrics

Status: Confirmed.

- In 2023, MTTR / time to restore service was renamed and redefined as failed deployment recovery time. The new metric counts only impairments caused by a change, not external outages.
- In 2024 DORA added a fifth metric, deployment rework rate, and moved from the four keys to five metrics grouped as throughput and instability.
- 'Reliability' is an operational-performance measure, not a fifth delivery metric. The 2021 report 'inaccurately called' it that.
- This closes the gap listed in docs/research/engineering-process.md ('dora.dev blocked ... unverified').
- *Fact-checker's note:* HTTP 200; dated 2026-01-02. Points 1-3 are confirmed. 2023: MTTR / time to restore was renamed and redefined as failed deployment recovery time, distinguishing change-caused failures from external factors such as a data-centre outage. 2024: deployment rework rate was added, giving five metrics in two factors. The 2021 report 'inaccurately called' reliability the fifth metric. FLAG: point 4 ('This closes the gap listed in docs/research/engineering-process.md') is the researcher's own repo-internal inference, not something the source states. It should be labelled as a researcher note, not a key point of the source.

#### ASB/AGL-04: Capabilities: Working in small batches

Status: Confirmed.

- Recommends the INVEST principle for each batch: Independent, Negotiable, Valuable, Estimable, Small ('hours to a couple days') and Testable ('tested, monitored, and verified as working in the way users expect'). This is a verified primary-ish citation for INVEST, which the repo DoR calls 'unverified'.
- 'Any batch of code that takes longer than a week to complete and check is too big.'
- Pitfall: working in small batches and then regrouping them before testing or release.
- AI note: AI tools tend to generate large features. Avoid massive PRs, because 'the cognitive load required to review a small chunk of machine-generated code may be higher per line than reviewing human-written code.'
- Small batches act as 'a safety net for AI adoption', countering the AI-linked rise in delivery instability. Start at the service/API layer, and use dark launches or feature toggles.
- *Fact-checker's note:* HTTP 200; updated 2025-12-08. The INVEST list is confirmed verbatim, including Small = 'hours to a couple days' and Testable = 'tested, monitored, and verified as working in the way users expect'. Also verbatim: 'Any batch of code that takes longer than a week to complete and check is too big'; the regrouping pitfall; the AI Note on massive PRs and per-line review cognitive load; 'safety net for AI adoption'; and starting at the service/API layer with dark launching or feature toggles. OVERSTATEMENT: calling this 'a verified primary-ish citation for INVEST' overstates it. DORA only recommends INVEST and links to Wikipedia; INVEST originates with Bill Wake (2003). It is a verified authoritative secondary endorsement, not a primary source. Also, 'We recommend' is DORA's wording, so the citation should say 'DORA recommends', not imply that a standard mandates it.

#### ASB/AGL-05: Capabilities: Streamlining change approval

Status: Confirmed.

- Approval by an external body (a CAB or senior manager) hurts delivery performance. DORA found 'no evidence' that more formal approval lowers change fail rates.
- Meet segregation of duties through peer review inside the development platform, plus continuous testing, CI and monitoring.
- Pitfall 'Treating all changes equally': applying the same approval process to every change makes review inefficient, so reviewers cannot focus on the changes whose risk calls for concentration.
- Goal: make the regular change process fast and reliable enough to use for emergency changes too.
- *Fact-checker's note:* HTTP 200. Confirmed: external body (CAB or senior manager) approval has a negative impact; 'no evidence to support the hypothesis that a more formal approval process is associated with lower change fail rates'; peer review in the development platform plus continuous testing, CI and monitoring/observability satisfies segregation of duties; the 'Treating all changes equally' pitfall is close to verbatim; the 'regular change management process fast and reliable enough that you can use it to make emergency changes too' goal. Context worth adding: the page also recommends flagging high-risk changes for additional scrutiny (risk-tiered review). That supports the key point, and it bears on whether this repo's uniform PE + senior + QA gate on every PR (including docs) is over-applied.

#### ASB/AGL-06: Capabilities: Work-in-process limits

Status: Confirmed.

- Prioritize work, limit how much people work on at once, and focus on finishing a small number of high-priority tasks.
- Set a WIP limit per board column based on team capacity, and pull work instead of pushing it. 'Only by imposing WIP limits and following this pull-based process do you actually create a Kanban board.'
- Stick to the limits. When work stalls, fix the process causing the delay instead of raising the limit.
- Measure the lead time of work through the whole value stream (mean and variability) to improve flow.
- *Fact-checker's note:* HTTP 200. Confirmed: prioritize, limit WIP, focus on a small number of high-priority tasks; WIP limit per column; 'Only by imposing WIP limits and following this pull-based process do you actually create a Kanban board' (verbatim); limits set by team capacity; 'Stick to the limits', improve the process instead of raising the limit; measure lead time with mean and variability across the whole value stream. 'Pull instead of push' is a fair paraphrase; the page describes pulling from the previous column.

#### ASB/AGL-07: Capabilities: Generative organizational culture (Westrum)

Status: Confirmed.

- 'Failure leads to inquiry.' Hold blameless postmortems, because blaming individuals creates a negative culture.
- Survey item: 'On my team, failures are treated primarily as opportunities to improve the system.'
- The learning-culture capability (same repo) also says to make it safe to fail and hold blameless postmortems.
- *Fact-checker's note:* HTTP 200. Confirmed: 'Failure leads to inquiry' (lines 39, 75); 'Hold blameless postmortems' (88, 110); 'Blaming individuals for failures creates a negative culture' (111); the survey item 'On my team, failures are treated primarily as opportunities to improve the system' (160). The learning-culture page at .../capabilities/learning-culture/index.md (HTTP 200) confirms 'Make it safe to fail... hold blameless postmortems' (lines 43-44).

#### ASB/AGL-08: Code-With Engineering Playbook: Definition of Ready

Status: Confirmed.

- DoR is the team's agreement on how complete a story must be to be a candidate for estimation in sprint planning. It can be codified as GitHub issue templates.
- Example items: details and inputs, clear and measurable acceptance criteria, addresses the business need, small enough yet valuable, and not blocked by unfinished work or another team's deliverable.
- Update the DoR when missing information 'recurrently impacts the planning'.
- What to avoid: DoR items should 'apply broadly', not to only one or two stories, because that becomes overhead.
- When top-priority work is not Ready, use refinement and prioritization, and split blocked stories to unblock part of their scope. Do not simply stop.
- *Fact-checker's note:* HTTP 200. Confirmed: DoR is an agreement on how complete a story should be 'to be selected as candidate for estimation in the sprint planning', codifiable as GitHub Issue Templates (or Azure DevOps templates); the example checklist items match; update when missing info 'recurrently impacts the planning'; 'should contain items that apply broadly... may become an overhead'; refinement, prioritization and splitting blocked stories. MILD OVERSTATEMENT: 'Do not simply stop' is the researcher's directive gloss. The source says 'it still may be possible to make forward progress' and offers 'strategies that may help', which is permissive, not imperative. Also note the page frames DoR as a checklist helping the PO; it does not address Cohn's stage-gate criticism (ASB/AGL-16, unverified).

#### ASB/AGL-09: Code-With Engineering Playbook: Agile ceremonies (re-verification of EP/ENG-15)

Status: Confirmed.

- 'Effective sprint goals are a concise bullet point list of items.' This conflicts with the Scrum Guide's 'single objective'.
- Estimation: t-shirt sizes, a single 'fits in one sprint?' indicator, or planning poker. 'Avoid converting story points or t-shirt sizes to days.' Track estimation accuracy, and 'If the sprint goal is met: does anything else matter?'
- Retro action items 'are in the backlog, assigned, and prioritized to be fixed by a date agreed upon (default being next retrospective)'.
- Retro formats by phase, citing Derby and Larsen's 'Agile Retrospectives': Gather Data (Triple Nickels, Timeline, Mad Sad Glad, Team Radar) and Generate Insights (5 Whys, Fishbone, Patterns and Shifts).
- AI note: some teams use short, lightweight or continuous planning cadences with AI tools, but must always validate and adapt AI output.
- Self-assignment can favour the loudest or most experienced voices, so the dev lead balances assignments.
- *Fact-checker's note:* HTTP 200. Confirmed verbatim: 'Effective sprint goals are a concise bullet point list of items'; t-shirt / single indicator / planning poker; 'Avoid converting story points or t-shirt sizes to days'; 'If the sprint goal is met: does anything else matter?'; retro items 'in the backlog, assigned, and prioritized to be fixed by a date agreed upon (default being next retrospective)'; Gather Data (Triple Nickels, Timeline, Mad Sad Glad, Team Radar) and Generate Insights (5 Whys, Fishbone, Patterns and Shifts); the AI note ('always validate and adapt output collaboratively'). The 'conflicts with the Scrum Guide' remark is the researcher's interpretation. It is fair, but the page itself hedges: 'Consider defining a sprint goal, or list of goals'. STRETCHES: (a) the phase lists link to the Derby/Larsen book via 'Consider other retro formats', but the page does not explicitly attribute the phase names to the book, so 'citing' is a mild overstatement. (b) 'the dev lead balances assignments' is a stretch. The source flags the loudest/most-experienced-voice risk and says 'it is the dev lead responsibility to ensure each engineer gets the opportunity to work on what makes sense for their growth', which is about growth, not explicitly balancing voices.

#### ASB/AGL-10: Code-With Engineering Playbook: Sections of a Working Agreement

Status: Confirmed.

- The working agreement is created by the team, stored in the repository, and each team composes its own.
- Sections: General, Communication, Work-life balance, Quality (DoD), Scrum rhythm (an activity, when, duration, who, accountable and goal table), Process Lead, Backlog management, Code management.
- The Process Lead makes sure every action item has an owner and a due date, and guarantees follow-up on retrospective action items.
- Backlog management: new tasks must match the story's acceptance criteria, otherwise discuss with the PM (scope-creep guard). Close items only when Done.
- *Fact-checker's note:* HTTP 200. Confirmed: 'created by the team at the beginning of the project, and is stored in the repository'; 'each team should compose their own'. The sections are General, Communication, Work-life Balance, 'Quality and not Quantity' (DoD), Scrum Rhythm (columns Activity/When/Duration/Who/Accountable/Goal), Process Lead, Backlog Management, Code Management. The Process Lead ensures each action item has an owner and a due date and will 'Guarantee the tracking/following up on action items from retrospectives'. Confirmed: new tasks must match the story's acceptance criteria, otherwise discuss with the PM ('to avoid scope creep'), and tasks close only when done per the DoD. Minor: the key point's section name 'Quality' is shortened from 'Quality and not Quantity'.

#### ASB/AGL-11: Code-With Engineering Playbook: Agile Development (fundamentals, AI tooling considerations)

Status: Confirmed.

- Fundamentals: a shared backlog, iterations with clear goals, clarity on ready and done, progress in one place, regular reflection, clear roles, and a team agreement.
- 'Favor frequent, lightweight planning and validation over rigid, fixed-length cadences when it helps accelerate feedback loops and reduce cycle time.' Keep human oversight of AI output.
- 'These are patterns, not prescriptions.'
- *Fact-checker's note:* HTTP 200. The fundamentals list is confirmed (shared backlog, iterations with clear goals, DoR, DoD, progress in one place, regular reflection, roles, team agreement). The 'Favor frequent, lightweight planning and validation over rigid, fixed-length cadences when it helps accelerate feedback loops and reduce cycle time' quote is verbatim. 'maintaining human oversight and review' is confirmed. 'These are patterns, not prescriptions' is verbatim. Note that the fundamentals are explicitly about goals, not methods ('We care about the goal for each activity, but not necessarily about how they are accomplished').

#### ASB/AGL-12: Code-With Engineering Playbook: Backlog Management

Status: Confirmed.

- Treat backlog refinement as an ongoing activity, not only a meeting.
- A story that needs design work should have its design done before it is added to a Sprint.
- Plan the paydown of technical debt.
- *Fact-checker's note:* HTTP 200. Confirmed: 'Consider the backlog refinement as an ongoing activity, that expands outside of the typical Refinement meeting'; 'a design for a story that needs it should be done before it is added in a Sprint'. MILD NUANCE: 'Plan the paydown of technical debt' drops the source's primary stance. The source says 'Shortcuts should generally be avoided' and that planning later improvement is the recommended approach only 'in some rare instances where they happen'. Also, 'Consider' is the source's verb for refinement, so it is a suggestion, not a mandate.

#### ASB/AGL-13: Orchestrate teams of Claude Code sessions (agent teams)

Status: Confirmed.

- 'Start with 3-5 teammates for most workflows.' 'Three focused teammates often outperform five scattered ones.' Token cost scales linearly with teammates, and coordination overhead grows.
- Size tasks as 'self-contained units that produce a clear deliverable'. Too small and coordination overhead exceeds the benefit. Too large and teammates work too long without check-ins. About '5-6 tasks per teammate' is suggested.
- 'Two teammates editing the same file leads to overwrites. Break the work so each teammate owns a different set of files.'
- Teammates do not inherit the lead's conversation history, so spawn prompts must contain the task-specific details.
- For sequential tasks, same-file edits or work with many dependencies, a single session or subagents beat a team. Tasks can depend on each other, and TaskCreated/TaskCompleted hooks can block task creation or completion.
- Monitor and steer: letting a team run unattended too long increases wasted effort.
- *Fact-checker's note:* HTTP 200, 42596 bytes. Confirmed verbatim: 'Start with 3-5 teammates for most workflows' (line 384); 'Three focused teammates often outperform five scattered ones' (386); 'Token costs scale linearly' and 'Coordination overhead increases' (380-381); too small / too large / 'self-contained units that produce a clear deliverable' (390-392); 'Having 5-6 tasks per teammate' (396); 'Two teammates editing the same file leads to overwrites. Break the work so each teammate owns a different set of files' (412); the lead's conversation history does not carry over, so include task-specific details in the spawn prompt (313, 367); 'For sequential tasks, same-file edits, or work with many dependencies, a single session or subagents are more effective' (26); task dependencies (191, 247); TaskCreated/TaskCompleted hooks can block with exit code 2 (219-220); 'Letting a team run unattended for too long increases the risk of wasted effort' (416). Context: agent teams are an experimental, opt-in feature, and this project uses workflow-spawned subagents, not agent teams. The applicability of the guidance (especially 3-5 teammates) to this repo's roughly 10-role subagent roster is the researcher's inference.

#### ASB/AGL-14: How we built our multi-agent research system (re-verification)

Status: Confirmed (the cited URL redirects; content checked at the redirect target).

- Each subagent needs 'an objective, an output format, guidance on the tools and sources to use, and clear task boundaries'. Vague briefs led to duplicated work and gaps.
- Scale effort to complexity: 1 agent with 3-10 tool calls for simple fact-finding, 2-4 subagents for comparisons, and more than 10 subagents only for complex research with clearly divided responsibilities.
- *Fact-checker's note:* REDIRECTED: curl -sI returns HTTP/2 308 with location /research/multi-agent-research-system, so per the rule this counts as fetched=false. The content at the redirect target (same publisher, HTTP 200) DOES state both key points verbatim: 'Each subagent needs an objective, an output format, guidance on the tools and sources to use, and clear task boundaries. Without detailed task descriptions, agents duplicate work, leave gaps...'; 'Simple fact-finding requires just 1 agent with 3-10 tool calls, direct comparisons might need 2-4 subagents with 10-15 calls each, and complex research might use more than 10 subagents with clearly divided responsibilities.' Action: re-cite as https://www.anthropic.com/research/multi-agent-research-system. Also note the scaling rules are for research queries, not software-delivery teams.

#### ASB/AGL-15: Effective harnesses for long-running agents (re-verification)

Status: Confirmed (the cited URL redirects; content checked at the redirect target).

- Agents were asked to work on 'only one feature at a time'. This was critical to countering the tendency to do too much at once.
- Failure mode: a later agent sees progress and 'declare[s] the job done', or marks features as passing prematurely. The fix is a JSON feature list where only a 'passes' field is changed, after careful testing.
- Without prompting, agents tested with unit tests or curl but missed that features did not work end-to-end. Browser automation 'as a human user would' fixed this.
- End each session with a git commit and a progress update, leaving the environment clean.
- *Fact-checker's note:* REDIRECTED: HTTP/2 308 to /research/effective-harnesses-for-long-running-agents, so per the rule this counts as fetched=false. The content at the redirect target confirms all 4 points. 'asked to work on only one feature at a time. This incremental approach turned out to be critical to addressing the agent's tendency to do too much at once.' A later agent would 'see that progress had been made, and declare the job done'. The fix is a JSON feature list where agents edit only the 'passes' field, marking features passing only after careful testing. 'Absent explicit prompting, Claude tended to make code changes, and even do testing with unit tests or curl commands... but would fail [to] recognize that the feature didn't work end-to-end'; browser automation 'as a human user would' fixed this. End the session 'by writing a git commit and progress update', leaving a clean state. Action: re-cite as https://www.anthropic.com/research/effective-harnesses-for-long-running-agents.

#### ASB/AGL-16: Definition of Ready: What It Is and Why It's Dangerous (unverified)

Status: Unverified: mountaingoatsoftware.com blocked; search snippets only.

- NOT FETCHED (host blocked). Per search snippets only: if DoR rules require that something 'must be 100 percent finished before a story can be brought into an iteration', the DoR becomes 'a huge step towards a sequential, stage-gate approach' and prevents overlapping work (concurrent engineering). Cohn grants it can solve problems in some cases, e.g. dependencies on other teams.
- *Fact-checker's note:* none; unverified sources were not re-checked.

#### ASB/AGL-17: SPIDR: Five Simple but Powerful Ways to Split User Stories (unverified)

Status: Unverified: mountaingoatsoftware.com blocked; search snippets only.

- NOT FETCHED (host blocked). Per search snippets: split by Spike, Path, Interface, Data, Rules. A spike is usually not the first technique to reach for.
- *Fact-checker's note:* none; unverified sources were not re-checked.

#### ASB/AGL-18: The Humanizing Work Show #175: How to Split a User Story (unverified)

Status: Unverified: not fetched; search snippet and third-party mirrors only.

- NOT FETCHED. Per search snippet: two steps, first get a decent (if large) story, then apply splitting patterns that each target a kind of functional complexity. The pattern list (workflow steps as thin end-to-end slices, operations/CRUD, business-rule variations, etc.) was seen only on third-party mirrors and is unverified. The humanizingwork.com guide page itself was not reachable or located.
- *Fact-checker's note:* none; unverified sources were not re-checked.

#### ASB/AGL-19: The Kanban Guide (2025.5 edition, PDF) (unverified)

Status: Unverified: kanbanguides.org blocked; search snippet only.

- NOT FETCHED (kanbanguides.org and prokanban.org blocked). Per search snippet: the Definition of Workflow includes a definition of work items, when items start and finish, and how WIP is controlled. The flow-metric names (WIP, throughput, work item age, cycle time) are not verified here. ASB/AGL-06 is the verified substitute for WIP limits and lead-time measurement.
- *Fact-checker's note:* none; unverified sources were not re-checked.

#### ASB/AGL-20: Agile Retrospectives: Making Good Teams Great (Derby and Larsen), as referenced by the MS playbook (unverified)

Status: Unverified: book, not fetched; two phases are confirmed second-hand via ASB/AGL-09.

- The book was not fetched. ASB/AGL-09 (verified) cites it and names two of its phases, Gather Data and Generate Insights. The full five-stage sequence (Set the stage, Gather data, Generate insights, Decide what to do, Close) is NOT verified from a primary source in this session.
- *Fact-checker's note:* none; unverified sources were not re-checked.

### 4.4 REQ

#### ASB/REQ-01: Gherkin Reference (Cucumber docs, content/docs/gherkin/reference.md)

Status: Confirmed.

- Re-verified; repo research already cites it as DPA/PROD-01.
- 'The purpose of the Rule keyword is to represent one business rule that should be implemented'; a Rule groups one or more scenarios that illustrate it.
- 'we recommend 3-5 steps per example'; too many steps make the example lose its power as a specification.
- Given puts the system in a known state; 'Avoid talking about user interaction in Given's'.
- A Then step should check an observable output (report, UI, message), 'not a behaviour deeply buried inside the system (like a record in a database)'.
- Keywords are ignored when steps are matched, so identical step text forces 'a less ambiguous, more clear domain language' (e.g. 'my account has a balance of £430').
- *Fact-checker's note:* All points found word for word. L116: 'The purpose of the `Rule` keyword is to represent one *business rule* that should be implemented'. 'we recommend 3-5 steps per example ... lose its expressive power as a specification'. L197-198 has the Given point, including 'Avoid talking about user interaction in `Given`'s'. 'not a behaviour deeply buried inside the system (like a record in a database)' is there. L171 says keywords are not taken into account when matching, then 'less ambiguous, more clear domain language' with 'my account has a balance of £430' at L185. One nuance: the Then rule is phrased as 'should', not 'must'.

#### ASB/REQ-02: Writing better Gherkin (content/docs/bdd/better-gherkin.md)

Status: Confirmed.

- Re-verified; repo research already cites it as DPA/PROD-02.
- Scenarios describe what, not how: 'When "Bob" logs in' is a functional requirement, while click-by-click steps are a 'procedural reference'.
- Self-test: 'Will this wording need to change if the implementation does?' If yes, rewrite it.
- Use declarative style; concrete values and UI mechanics belong in step definitions.
- *Fact-checker's note:* Found: 'When "Bob" logs in, is a functional requirement ... procedural reference'. Also found: 'Will this wording need to change if the implementation does?' / 'If the answer is "Yes", then you should rework it'. Declarative style and 'specified in the step definitions' are at L82. Nuance: L43 says imperative tests 'in some contexts ... is appropriate', so declarative is a recommendation, not an absolute rule.

#### ASB/REQ-03: Example Mapping (content/docs/bdd/example-mapping.md)

Status: Confirmed.

- Held before a story is pulled into development, to clarify and confirm its acceptance criteria.
- Card colours: yellow = story, blue = each rule or acceptance criterion, green = examples under each rule, red = questions that cannot be answered in the session.
- New stories found during the session are 'sliced and deferred out of scope'.
- Keep going until the scope is clear or time runs out. Credits Matt Wynne's blog as the origin.
- *Fact-checker's note:* Found: before a story is pulled into development, have a conversation to clarify and confirm acceptance criteria. Card colours match: yellow story, blue rule or acceptance criterion, green example, red question. Found 'sliced and deferred out of scope' and 'until the group is satisfied that the scope of the story is clear, or we run out of time'. Slight overstatement: the page only says 'For more details, see Matt Wynne's blog'. It does not call the blog the origin of the method.

#### ASB/REQ-04: Discovery workshop (content/docs/bdd/discovery-workshop.md)

Status: Confirmed.

- About 25-30 minutes per story. Needing longer means the story is 'far too large and should be broken down', or more research is needed.
- 3-6 people, with at least the Three Amigos: product owner, developer, tester.
- Hold it 'as late as possible before development on a new User Story begins'.
- *Fact-checker's note:* Found: 'about 25-30 minutes per story ... far too large and should be broken down, or some of the specifics are missing' (in that case, set the story aside and research more). '3-6 people' is given as a 'good rule-of-thumb', with the Three Amigos as the bare minimum. Found: 'As late as possible before development on a new User Story begins'. Nuance: the page says 'ideally', so this is guidance, not a hard limit.

#### ASB/REQ-05: Who does what / The Three Amigos (content/docs/bdd/who-does-what.md)

Status: Confirmed.

- The product owner decides what is in scope; the tester produces scenarios and edge cases; the developer adds steps and finds technical roadblocks.
- Later a developer and a tester can do it as a pair, 'as long as their output is actively reviewed by the product owner'.
- *Fact-checker's note:* Found: the PO is 'responsible for deciding what is within scope'; the tester generates 'lots of Scenarios, and lots of edge cases'; the developer 'will add many of the Steps' and thinks about 'roadblocks'. Pair writing is allowed 'as long as their output is actively reviewed by the product owner (or business representative)'. Context: this applies 'Later', after the whole team has first established the Gherkin language together.

#### ASB/REQ-06: Behaviour-Driven Development (content/docs/bdd/_index.md)

Status: Confirmed.

- Three practices: Discovery, Formulation, Automation.
- Keep breaking user problems into small pieces; each automated example starts with an automated test that guides the code.
- *Fact-checker's note:* L45: 'We call these practices _Discovery_, _Formulation_, and _Automation_'. L33: 'continuously breaking down your user's problems into small pieces'. L41: 'starting with an automated test to guide the development of the code'. L89: the test fails first, then you implement.

#### ASB/REQ-07: spec-kit Feature Specification template (templates/spec-template.md)

Status: Confirmed.

- User stories are prioritised (P1, P2, ...) and each 'must be INDEPENDENTLY TESTABLE', with an explicit 'Independent Test' line.
- Acceptance scenarios use Given/When/Then; there is a mandatory Edge Cases section.
- Requirements use the form 'FR-001: System MUST [specific capability]'. Unclear ones are marked inline, e.g. '[NEEDS CLARIFICATION: retention period not specified]'.
- Success Criteria SC-### 'must be technology-agnostic and measurable'. Assumptions are listed explicitly.
- *Fact-checker's note:* Found: 'must be INDEPENDENTLY TESTABLE', P1/P2/P3 priorities, an '**Independent Test**' line, Given/When/Then lines, and 'FR-001: System MUST [specific capability...]'. Found the marker '[NEEDS CLARIFICATION: retention period not specified]' (FR-007). Success criteria: 'These must be technology-agnostic and measurable'. There is an Assumptions section. Small inaccuracy: Edge Cases is a ### subsection inside the '(mandatory)' User Scenarios & Testing section. It is not labelled mandatory itself, so 'mandatory Edge Cases section' slightly overstates it.

#### ASB/REQ-08: Specification-Driven Development (spec-driven.md)

Status: Confirmed.

- Specs must be 'precise, complete, and unambiguous enough to generate working systems'.
- Focus on WHAT and WHY; avoid HOW (no tech stack, APIs or code structure).
- 'Mark all ambiguities' and 'Don't guess', using [NEEDS CLARIFICATION] markers.
- Checklists act as 'unit tests' for the spec: no markers remain, requirements are testable and unambiguous, success criteria are measurable.
- 'Every technical choice links back to specific requirements' (traceable decisions).
- *Fact-checker's note:* L51: 'Specifications must be precise, complete, and unambiguous enough to generate working systems'. L174-175: 'Focus on WHAT users need and WHY' / 'Avoid HOW to implement (no tech stack, APIs, code structure)'. L186-187: 'Mark all ambiguities' / 'Don't guess'. L194: checklists 'act as "unit tests" for the specification', with the three items listed. L159: 'Every technical choice links back to specific requirements'. Counter-point for the audit: 'Don't guess' here contradicts ASB/REQ-10, which says 'Make informed guesses' and allows at most 3 markers. spec-kit's own command template overrides this philosophy doc. Do not cite both as one consistent rule.

#### ASB/REQ-09: spec-kit /analyze command (templates/commands/analyze.md)

Status: Confirmed.

- Flags vague adjectives such as 'fast, scalable, secure, intuitive, robust' that have no measurable criteria.
- Flags 'Requirements with verbs but missing object or measurable outcome'.
- Coverage gaps: requirements with zero tasks, and tasks with no mapped requirement or story. Reports a coverage %.
- Severity HIGH for a duplicate or conflicting requirement, an ambiguous security or performance attribute, or an untestable acceptance criterion.
- *Fact-checker's note:* L126: 'Flag vague adjectives (fast, scalable, secure, intuitive, robust) lacking measurable criteria'. L131: 'Requirements with verbs but missing object or measurable outcome'. L142-143: requirements with zero tasks, and tasks with no mapped requirement or story. L187: 'Coverage % (requirements with >=1 task)'. L158: HIGH = 'Duplicate or conflicting requirement, ambiguous security/performance attribute, untestable acceptance criterion'. All confirmed.

#### ASB/REQ-10: spec-kit /specify command (templates/commands/specify.md)

Status: Confirmed.

- 'Make informed guesses', 'Document assumptions', 'Maximum 3 [NEEDS CLARIFICATION] markers', prioritised scope > security/privacy > UX > technical details.
- 'Think like a tester: Every vague requirement should fail the "testable and unambiguous" checklist item'.
- Success criteria must be Measurable, Technology-agnostic, User-focused and Verifiable. It lists 'API response time is under 200ms' as a bad (too technical) success criterion.
- *Fact-checker's note:* L301-308: 'Make informed guesses', 'Document assumptions', 'Maximum 3 [NEEDS CLARIFICATION] markers', 'scope > security/privacy > user experience > technical details', 'Think like a tester: Every vague requirement should fail the "testable and unambiguous" checklist item'. L327-329: Technology-agnostic, User-focused, Verifiable. L340: '"API response time is under 200ms" (too technical, use "Users see results instantly")'. All confirmed. The 'Measurable' point is backed by L140 ('Create measurable, technology-agnostic outcomes'). Counter-point: its suggested replacement, 'Users see results instantly', is itself unmeasurable, so it conflicts with ASB/REQ-09/REQ-14. For NFRs, keep a measurable SLI/threshold at the NFR level even if spec-level success criteria stay technology-agnostic.

#### ASB/REQ-11: spec-kit checklist template (templates/checklist-template.md)

Status: Confirmed.

- The checklist is a reviewer-owned review of requirements quality.
- '[x] means the criterion has been reviewed and satisfied for requirements quality. It does not mean implementation work is complete.'
- *Fact-checker's note:* Found word for word: 'Review Ownership: This checklist is a reviewer-owned requirements-quality review artifact' and 'Marker Semantics: `[x]` means the criterion has been reviewed and satisfied for requirements quality. It does not mean implementation work is complete.'

#### ASB/REQ-12: SRE fundamentals: SLIs, SLAs and SLOs

Status: Confirmed.

- Re-verified; repo research already cites it under AQS.
- SLO: 'a precise numerical target for system availability'.
- SLI: a direct measurement, e.g. the frequency of successful probes; 'you must be able to measure the rates of successful and unsuccessful queries as your SLIs'.
- Example wording: 'an availability SLO of 99.9% over one month, with an internal availability SLO of 99.95%'.
- 'If you're building a system from scratch, make sure that SLIs and SLOs are part of your system requirements.'
- Don't make the system more reliable than you intend to commit to.
- *Fact-checker's note:* HTML stripped and searched. Found: 'a precise numerical target for system availability ... availability Service-Level Objective (SLO)'. Found: 'direct measurement of a service's behavior: the frequency of successful probes'. Found: 'you must be able to measure the rates of successful and unsuccessful queries as your SLIs'. Found: 'an availability SLO of 99.9% over one month, with an internal availability SLO of 99.95%'. In context, 99.9% is the looser figure in the SLA, so it is an SLA-vs-internal-SLO example. Found: 'If you're building a system from scratch, make sure that SLIs and SLOs are part of your system requirements'. Found: 'Don't make your system overly reliable if you don't intend to commit to it to being that reliable'. Paraphrase fine.

#### ASB/REQ-13: arc42 Quality Model: ISO/IEC 25010 standard page (_standards/iso/iso-25010.md)

Status: Confirmed.

- Nine product-quality characteristics: Functional Suitability, Performance Efficiency, Compatibility, Interaction Capability ('Formerly Usability'), Reliability, Security, Maintainability, Flexibility ('Formerly Portability'), Safety.
- Lists sub-characteristics such as Inclusivity, User Engagement, Self Descriptiveness, Faultlessness, Resistance, Scalability and Fail Safe.
- Caution (my own knowledge, not verified against ISO): the page puts Testability under Flexibility, but I believe 25010:2023 keeps it under Maintainability. Check against the ISO text before quoting.
- References ISO/IEC 25010:2023 at iso.org/standard/78176.html.
- *Fact-checker's note:* The page lists nine characteristics: Interaction Capability '(Formerly Usability)', Flexibility '(Formerly Portability)', and Safety. Sub-characteristics include Inclusivity, User Engagement, Self Descriptiveness, Faultlessness, Resistance, Scalability and Fail Safe. It links iso.org/standard/78176.html. The researcher's caution is right: the page does put Testability under Flexibility. From my own knowledge of ISO/IEC 25010:2023 (not checked against the paywalled ISO text), Testability belongs under Maintainability, and Maintainability's list here is missing it. Treat ASB/REQ-13 as a secondary source that contains at least this one likely error. Do not quote it as if it were the ISO text.

#### ASB/REQ-14: arc42 Quality Model README (metamodel and authoring rules)

Status: Confirmed.

- A requirement example is 'A specific, measurable expectation for a system, often expressed as a quality scenario or acceptance criterion'.
- Authoring rules: 'Use specific, testable metrics with units' and 'Focus on what must be achieved, not how'.
- Quality dimensions such as #secure and #reliable are 'intentionally broad and overlapping, so they need further refinement'.
- *Fact-checker's note:* L47: Requirement Example = 'A specific, measurable expectation for a system, often expressed as a quality scenario or acceptance criterion'. L238-239: 'Use specific, testable metrics with units' / 'Focus on _what_ must be achieved, not _how_'. L45: dimensions such as #secure and #reliable are 'intentionally broad and overlapping, so they need further refinement'. Context: these are authoring rules for content on the arc42 site, not general standards guidance.

#### ASB/REQ-15: EARS syntax VS Code extension: README and snippets (BlueDotBrigade)

Status: Confirmed.

- Ubiquitous: 'The <system name> shall <system response>.'
- State: 'While <in state>, the <system name> shall <system response>.'
- Event: 'When <trigger>, the <system name> shall <system response>.'
- Optional feature: 'Where <feature is included>, the <system name> shall <system response>.'
- Unwanted behaviour: 'If <trigger>, then the <system name> shall <system response>.'
- Complex: 'While <in state>, when <trigger>, the <system name> shall <system response>.'
- The README links to alistairmavin.com/ears as the origin.
- *Fact-checker's note:* All six templates are present exactly as quoted, with prefixes 'EARS Ubiquitous', 'EARS State', 'EARS Event', 'EARS Optional Feature', 'EARS Complex Condition'. The unwanted-behaviour pattern 'If <trigger>, then the <system name> shall <system response>.' is labelled 'ERROR HANDLING' in the snippets, not 'Unwanted behaviour'. That is a labelling difference only (Mavin's term is unconfirmed because ASB/REQ-22 is blocked). The README (fetched separately, HTTP 200) credits Alistair Mavin and links https://alistairmavin.com/ears/. Third-party extension, so this is secondary evidence for EARS.

#### ASB/REQ-16: Definition of Ready (Microsoft Code-With Engineering Playbook)

Status: Confirmed.

- Checklist questions: 'clear and complete acceptance criteria?', 'Can we measure the acceptance criteria?', small enough yet valuable, blocked by dependencies?
- 'The ready checklist should contain items that apply broadly. Don't include items or details that only apply to one or two user stories.'
- Update the DoR whenever missing information keeps hurting planning. Blocked stories can be split to unblock part of their scope.
- *Fact-checker's note:* Found the checklist items 'clear and complete acceptance criteria?', 'Can we measure the acceptance criteria?', 'small enough ... but large enough to provide value', 'Is the user story blocked?'. Found word for word: 'The ready checklist should contain items that apply broadly. Don't include items or details that only apply to one or two user stories.' Found: update the DoR when missing information 'recurrently impacts the planning'. Found: 'Blocked user stories can often be broken down in a way that unblocks a portion'. Nuance: the page offers these as 'Examples of Ready Checklist Items', not a required list.

#### ASB/REQ-17: Definition of Done (Microsoft Code-With Engineering Playbook)

Status: Confirmed.

- Re-verified; repo research already cites it as EP/ENG-16.
- At story level, 'Acceptance criteria are met' is one DoD item among generic ones (builds, unit tests, review, docs, merged).
- At story level: 'The feature is signed off by the product owner'.
- *Fact-checker's note:* The Feature/User Story list includes 'Acceptance criteria are met' among generic items: builds, unit tests, code review, docs, merged into default branch. It also includes 'The feature is signed off by the product owner'. Nuance: the page calls these 'some examples of checks' and says the team 'should decide together' on its own DoD. End-to-end and performance tests appear only in the Sprint Goal list, not the story list.

#### ASB/REQ-18: Backlog Management (Microsoft Code-With Engineering Playbook)

Status: Confirmed.

- 'User stories have a clear acceptance criteria and definition of done' (two separate things).
- The team must share an understanding of 'what constitutes good acceptance criteria'. Refinement is ongoing.
- *Fact-checker's note:* Found under Goals: 'User stories have a clear acceptance criteria and definition of done'. The researcher overstated the second point: 'The team must share an understanding ...' is a Suggestion in the source, phrased 'The team should have a clear understanding of what constitutes good acceptance criteria'. 'Refinement is ongoing' is also a suggestion ('Consider the backlog refinement as an ongoing activity'). Change 'must' to 'should' and mark it as a suggestion.

#### ASB/REQ-19: Performance (Microsoft Code-With Engineering Playbook, non-functional requirements)

Status: Confirmed.

- Re-verified; repo research already cites it as DPA/DESIGN-16.
- Performance metrics: response time, throughput, latency, resource utilisation. Validate under varying load and monitor continuously.
- Gives no percentile values.
- *Fact-checker's note:* Found the metrics 'response time, throughput, latency, and resource utilization'. 'Performance Testing ... validate system performance across varying load scenarios' and 'Continuous Monitoring' are listed. grep for 'percentile' returns 0 hits, so 'gives no percentile values' is confirmed. It also lists scalability, concurrency, stability and fault tolerance. The page is descriptive and sets no numeric targets, so it cannot back any specific threshold.

#### ASB/REQ-20: Claude Code best practices (code.claude.com/docs/en/best-practices.md)

Status: Confirmed.

- 'Interview me until you could write the spec, then write it to SPEC.md': multiple-choice questions on undecided parts, including what is out of scope.
- Build in a fresh session from SPEC.md, 'a written definition of done'.
- Review against the spec with a subagent: 'check every requirement is implemented and the listed edge cases have tests'.
- Before leaving a task to run: 'Does it know what done looks like? A goal condition, a spec file, or a failing test it has to turn green.'
- *Fact-checker's note:* L126: 'Interview me until you could write the spec, then write it to SPEC.md'. L129: 'multiple-choice questions ... what's out of scope'. L131: 'start a fresh session to build from it ... a written definition of done'. L263/L482: subagent review, 'check every requirement is implemented and the listed edge cases have tests'. L532: 'Does it know what done looks like? A goal condition, a spec file, or a failing test it has to turn green.' All confirmed word for word. Context: L526 adds 'have a person approve the result at the end'.

#### ASB/REQ-21: Effective harnesses for long-running agents

Status: Confirmed (the cited URL redirects; content checked at the redirect target).

- Re-verified; repo research cites it under EP.
- An initializer writes a feature list (over 200 end-to-end features, all initially 'failing') as JSON with category, description, steps and 'passes': false.
- Agents may only change the passes field: 'It is unacceptable to remove or edit tests'. JSON is used because the model is less likely to overwrite it than Markdown.
- Work on one feature at a time. Without explicit prompting, Claude marked features done after unit tests or curl but missed end-to-end failures; browser automation fixed this.
- Its example steps are imperative UI steps ('Click the New Chat button').
- *Fact-checker's note:* The cited URL returns HTTP 308 to /research/effective-harnesses-for-long-running-agents, so fetched=false under the redirect rule. Update the citation to https://www.anthropic.com/research/effective-harnesses-for-long-running-agents. The redirect target (HTTP 200) supports every key point: 'over 200 features', all 'initially marked as "failing"'; JSON with category/description/steps/'passes': false; edit only the passes field; 'It is unacceptable to remove or edit tests'; JSON because 'the model is less likely to inappropriately change or overwrite JSON files compared to Markdown'; 'work on only one feature at a time'; without explicit prompting Claude used unit tests or curl but missed end-to-end failures; the example step is "Click the 'New Chat' button" (imperative UI step). Overstatement: 'browser automation fixed this'. The source says Claude 'mostly did well' once prompted, that it 'dramatically improved performance', and that 'Some issues remain' (e.g. it cannot see browser-native alert modals). Reword to 'greatly improved'. Counter-point: its imperative UI steps conflict with ASB/REQ-02's declarative guidance.

#### ASB/REQ-22: EARS: The Easy Approach to Requirements Syntax (Alistair Mavin) (unverified)

Status: Unverified: alistairmavin.com blocked (DNS failure); not fetched.

- Primary EARS source. The host is blocked in this session (DNS ENOTFOUND), so I could not fetch it. Pattern content is taken only from ASB/REQ-15.
- *Fact-checker's note:* none; unverified sources were not re-checked.

#### ASB/REQ-23: ISO/IEC/IEEE 29148:2018 Requirements engineering (unverified)

Status: Unverified: iso.org blocked and the standard is paywalled; secondary search results only.

- Not fetched: iso.org is blocked here and the standard is paywalled.
- A web search (secondary sources only) says clause 5.2.5 lists the characteristics of individual requirements: necessary, appropriate, unambiguous, complete, singular, feasible, verifiable, correct, conforming. Sources disagree on the count. Treat this as unverified.
- *Fact-checker's note:* none; unverified sources were not re-checked.

#### ASB/REQ-24: ISO/IEC 25010:2023 Product quality model (unverified)

Status: Unverified: iso.org blocked and the standard is paywalled; names come only from ASB/REQ-13.

- URL taken from ASB/REQ-13. Not fetched (iso.org blocked, standard paywalled). The 2023 characteristic names come only from ASB/REQ-13.
- *Fact-checker's note:* none; unverified sources were not re-checked.

#### ASB/REQ-25: Site Reliability Engineering book, ch. 4 Service Level Objectives (unverified)

Status: Unverified: sre.google blocked (DNS failure); not fetched.

- Host blocked (ENOTFOUND). The SLI-template details I expected (aggregation interval, measurement point, percentiles over averages) are NOT verified. Only ASB/REQ-12's wording is verified.
- *Fact-checker's note:* none; unverified sources were not re-checked.

#### ASB/REQ-26: Introducing Example Mapping (Matt Wynne) (unverified)

Status: Unverified: cucumber.io blocked; not fetched.

- URL taken from ASB/REQ-03's link. cucumber.io is blocked here. The '25-minute timebox' and 'many red cards = not ready' heuristics come from this blog, so they are unverified; only ASB/REQ-04's 25-30 min guidance is verified.
- *Fact-checker's note:* none; unverified sources were not re-checked.

#### ASB/REQ-27: How to Quantify Quality: Finding Scales of Measure (Tom Gilb, ACCU Overload 70) (unverified)

Status: Unverified: accu.org blocked; search snippets only.

- Found by web search, not fetched (blocked). Search snippets say Scale defines the unit of measure, Meter is the practical method of measuring, and Goal is the minimum acceptable level. All unverified.
- *Fact-checker's note:* none; unverified sources were not re-checked.

#### ASB/REQ-28: The new user story backlog is a map (Jeff Patton) (unverified)

Status: Unverified: jpattonassociates.com blocked; cited from the researcher's prior knowledge only.

- Host blocked (HTTP 000). The story-mapping practice (backbone of activities, walking skeleton, release slices) is cited from my prior knowledge only.
- *Fact-checker's note:* none; unverified sources were not re-checked.

#### ASB/REQ-29: INVEST in Good Stories, and SMART Tasks (Bill Wake) (unverified)

Status: Unverified: xp123.com refused by the proxy; not fetched.

- Proxy denied xp123.com (403 on CONNECT). INVEST is still unverified, as the repo DoR already says.
- *Fact-checker's note:* none; unverified sources were not re-checked.

#### ASB/REQ-30: Leveraging LLMs for the Quality Assurance of Software Requirements (arXiv 2408.10886) (unverified)

Status: Unverified: arxiv.org blocked; search snippet only.

- Found by web search. Its snippet says it tabulates 29148 characteristics (appropriate, complete, conforming, correct, feasible, necessary, singular, ...). Not fetched (arxiv.org blocked).
- *Fact-checker's note:* none; unverified sources were not re-checked.

### 4.5 RPD

#### ASB/RPD-01: Create custom subagents (Claude Code docs)

Status: Confirmed.

- Fetched with curl on 2026-10-31 (HTTP 200, 967 KB).
- Best practices, quoted: 'Design focused subagents: each subagent should excel at one specific task'; 'Write descriptions that single out one subagent: Claude uses the description to decide when to delegate'; 'Limit tool access: grant only necessary permissions for security and focus'; 'Check into version control'.
- Descriptions load into context. When the combined descriptions exceed 15,000 tokens, Claude Code warns at startup, and the doc advises moving detail into each subagent's system prompt, which only loads when that subagent runs.
- Each subagent runs in its own context window with a custom system prompt, specific tool access and independent permissions.
- *Fact-checker's note:* HTTP 200, 967735 bytes, no redirect. All four best-practice quotes appear verbatim, including the 15,000-token warning. The page says to 'Trim the description fields ... and move detail into each subagent's system prompt, which only loads when that subagent runs'. It also says 'Each subagent runs in its own context window with a custom system prompt, specific tool access, and independent permissions.' Precision note: the 15,000-token count excludes built-in subagents ('except the built-in ones'), and Claude Code 'still loads every subagent' after the warning.

#### ASB/RPD-02: How we built our multi-agent research system

Status: Confirmed (the cited URL redirects; content checked at the redirect target).

- Fetched with curl on 2026-10-31 (HTTP 200). Already cited in the repo; re-verified here.
- Quoted: 'Each subagent needs an objective, an output format, guidance on the tools and sources to use, and clear task boundaries. Without detailed task descriptions, agents duplicate work, leave gaps, or fail to find necessary information.'
- *Fact-checker's note:* The cited URL is REDIRECTED: curl without -L returns 308 to https://www.anthropic.com/research/multi-agent-research-system. Under the fact-check rule a redirected URL counts as fetched=false. So the researcher's 'HTTP 200' claim is inaccurate for the cited URL: 200 comes back only after following the redirect. The researcher flagged this kind of redirect for ASB/RPD-03 but missed it here. The repo cites the /engineering/ URL 3 times in .claude/ and docs/. The quote 'Each subagent needs an objective, an output format, guidance on the tools and sources to use, and clear task boundaries. Without detailed task descriptions, agents duplicate work, leave gaps, or fail to find necessary information.' is verbatim on the target page.

#### ASB/RPD-03: Building effective agents

Status: Confirmed.

- Fetched with curl on 2026-10-31. The URL the repo cites (/engineering/building-effective-agents) now answers 308 and redirects to /research/building-effective-agents. The citation still resolves, but the canonical URL has changed.
- Quoted: 'we recommend finding the simplest solution possible, and only increasing complexity when needed.'
- Agents need 'ground truth' from the environment at each step and can pause for human feedback at checkpoints. The evaluator-optimizer pattern works best 'when we have clear evaluation criteria'.
- *Fact-checker's note:* HTTP 200 at the cited /research/ URL, no redirect. Confirmed that the old /engineering/building-effective-agents URL returns 308 to this one; the repo still cites the old URL 4 times. Verbatim on the page: 'we recommend finding the simplest solution possible, and only increasing complexity when needed', 'ground truth from the environment at each step', 'pause for human feedback at checkpoints or when encountering blockers', and the evaluator-optimizer is 'particularly effective when we have clear evaluation criteria'. The paraphrase 'works best' slightly strengthens 'particularly effective'; that is acceptable.

#### ASB/RPD-04: Prompting best practices (Claude)

Status: Confirmed.

- Fetched with curl on 2026-10-31 (HTTP 200).
- 'Give Claude a role': a role in the system prompt focuses behaviour and tone.
- 'Be clear and direct': explicit, specific instructions. 'Providing context or motivation behind your instructions, such as explaining to Claude why such behavior is important' gives more targeted responses.
- *Fact-checker's note:* HTTP 200, no redirect. 'Give Claude a role: Setting a role in the system prompt focuses Claude's behavior and tone' and 'Be clear and direct: Claude responds well to clear, explicit instructions' are both present. Attribution slip: the 'context or motivation behind your instructions' quote sits under a separate heading, 'Add context to improve performance', not under 'Be clear and direct'. Mild overstatement: the source says it 'CAN give Claude more information ... and help it deliver more targeted responses'; the key point says it 'gives' more targeted responses.

#### ASB/RPD-05: WCAG 2.2 guidelines source (index.html, w3c/wcag repo)

Status: Confirmed.

- Fetched from raw GitHub on 2026-10-31, because www.w3.org is blocked in this session.
- Success criteria that are new in 2.2 (from sc/22/ includes): focus-not-obscured-minimum, focus-not-obscured-enhanced, focus-appearance, dragging-movements, target-size-minimum, consistent-help, redundant-entry, accessible-authentication-minimum, accessible-authentication-enhanced.
- *Fact-checker's note:* HTTP 200, 65256 bytes. The sc/22/ includes are exactly the 9 listed: accessible-authentication-enhanced/minimum, consistent-help, dragging-movements, focus-appearance, focus-not-obscured-enhanced/minimum, redundant-entry, target-size-minimum. Caveat the key points do not state: the w3c/wcag main branch is the editor's draft, not the published W3C Recommendation. It currently matches 2.2, but it is not normative.

#### ASB/RPD-06: WCAG 2.2 SC Consistent Help (sc/22/consistent-help.html)

Status: Confirmed.

- Level A, New.
- Help mechanisms that are repeated across a set of pages (human contact details, human contact mechanism, self-help option, fully automated contact mechanism) must occur in the same relative order, unless the user initiates a change.
- *Fact-checker's note:* HTTP 200. Level A, change 'New'. The four mechanisms are listed exactly, and they 'occur in the same order relative to other page content, unless a change is initiated by the user'. The key point says 'same relative order'; the source says 'same order relative to other page content'. That is close enough. The source adds that order is judged within the same page variation (zoom or orientation); the key point leaves this out.

#### ASB/RPD-07: WCAG 2.2 SC Redundant Entry (sc/22/redundant-entry.html)

Status: Confirmed.

- Level A, New.
- Information the user already entered, or was given, that is needed again in the same process must be auto-populated or available to select. Exceptions include cases where re-entering is essential.
- *Fact-checker's note:* HTTP 200. Level A, New. 'Information previously entered by or provided to the user that is required to be entered again in the same process is either auto-populated, or available for the user to select.' There are three exceptions: essential, security, and no longer valid. The key point says 'Exceptions include', which correctly signals the list is not exhaustive. Even so, the security and no-longer-valid exceptions should be stated wherever a role doc relies on this criterion.

#### ASB/RPD-08: Understanding Conformance (WCAG 2.2)

Status: Confirmed.

- Quoted: 'For Level AA conformance, the web page satisfies all the Level A and Level AA success criteria, or a Level AA conforming alternate version is provided.'
- Conformance applies to full pages only, and 'all web pages in the process conform' (complete processes).
- *Fact-checker's note:* HTTP 200. Verbatim: 'For Level AA conformance, the web page satisfies all the Level A and Level AA success criteria, or a Level AA conforming alternate version is provided.' Requirement 2: 'Conformance ... is for full web page(s) only'. Complete processes: 'all web pages in the process conform at the specified level or better'.

#### ASB/RPD-09: Understanding SC 4.1.1 Parsing (Obsolete and removed)

Status: Confirmed.

- Quoted: 'This criterion has been removed from WCAG 2.2.' The issues it used to catch now fail Info and Relationships or Name, Role, Value.
- *Fact-checker's note:* HTTP 200. 'This criterion has been removed from WCAG 2.2.' is verbatim. Mild overstatement: the source says 'MANY issues that would have failed this criterion will fail Info and Relationships or Name, Role, Value', and that others are excepted. The key point implies that all such issues now fail those criteria.

#### ASB/RPD-10: Code-With Engineering Playbook: Accessibility

Status: Confirmed.

- Re-verified 2026-10-31. The repo already cites it in DPA.
- 'automated tooling alone is not enough - make sure to augment your automated tests with manual ones.' Names Accessibility Insights and the axe-core linter.
- Note: its Resources section links WCAG 2.0, which is outdated next to the project's 2.2 target.
- *Fact-checker's note:* HTTP 200. Line 45 is verbatim: 'automated tooling alone is not enough - make sure to augment your automated tests with manual ones.' Accessibility Insights and the axe Accessibility Linter for VS Code (axe-core rules) are named. The Resources section links https://www.w3.org/TR/WCAG20/, so the 'outdated WCAG 2.0' note is correct.

#### ASB/RPD-11: Code-With Engineering Playbook: Design Reviews

Status: Confirmed.

- Re-verified 2026-10-31 (DPA/DESIGN-15).
- Measures: Cost of Change (before or after implementation), Reviewer Participation (a low number such as the same 2 individuals on every review 'might indicate a limited set of perspectives'), Time to Potential Solutions (multiple options), Time to Decisions.
- When no quorum is reached, 'the person with the most context on the problem (typically story owner) should make the final decision ... Disagree and commit!'
- The dev crew attends every review. Domain experts and customer SMEs attend as needed.
- *Fact-checker's note:* HTTP 200. The four measures are present: Cost of Change; Reviewer Participation, where 'same 2 individuals only on every review ... might indicate a limited set of perspectives'; Time To Potential Solutions (multiple); and Time to Decisions. No-quorum rule: 'the person with the most context on the problem (typically story owner) should make the final decision. Prioritize delivering value and learning. Disagree and commit!' Participation: 'The dev crew should always participate in all design review sessions'; domain experts, including customer SMEs, participate 'as needed'.

#### ASB/RPD-12: Code-With Engineering Playbook: Agile Ceremonies

Status: Confirmed.

- Re-verified 2026-10-31 (EP/ENG-15).
- Stories are designed and Ready before planning. The sprint goal is a concise bullet list, used at review ('was the goal achieved?', 'If not, why?').
- Retro action items go 'in the backlog, assigned, and prioritized to be fixed by a date agreed upon (default being next retrospective)'. Retros ask hard questions. 'Bring in a neutral facilitator for project retros or retros that introspect after a difficult period.'
- New note on AI tools: AI-drafted plans and acceptance criteria must be validated and adapted collaboratively with the team.
- *Fact-checker's note:* HTTP 200. Line 9 says stories are 'designed and ready before the planning'. Lines 17-22 say 'Effective sprint goals are a concise bullet point list', used at review ('was the goal achieved?', 'If not, why?'). Line 128 has retro items 'in the backlog, assigned, and prioritized to be fixed by a date agreed upon (default being next retrospective)'. Line 129 covers hard questions, and line 138 covers the neutral facilitator. The AI note (line 13) is 'always validate and adapt output collaboratively with the team'. Overstatement to flag: the sprint goal itself is framed as optional ('CONSIDER defining a sprint goal'). The key point presents it as a given. The repo's practice of a mandatory sprint goal goes beyond this source; it does not come from it.

#### ASB/RPD-13: Code-With Engineering Playbook: Definition of Ready

Status: Confirmed.

- Example Ready items: description includes the input values; clear and complete acceptance criteria; addresses the business need; criteria are measurable; small enough yet valuable; not blocked by unfinished work or another team's deliverable.
- Written by the PO in agreement with the dev team and the Process Lead. Update it 'anytime the scrum team observes that there are missing information in the user stories that recurrently impacts the planning'.
- Avoid: 'items or details that only apply to one or two user stories'.
- Blocked stories can often be split so that part of the scope is unblocked.
- *Fact-checker's note:* HTTP 200. The six example checklist items match. 'Update ... anytime the scrum team observes that there are missing information in the user stories that recurrently impacts the planning.' 'Don't include items or details that only apply to one or two user stories.' 'Blocked user stories can often be broken down in a way that unblocks a portion'. Mild overstatement: the source says the checklist 'CAN be written by a Product Owner in agreement with the development team and the Process Lead'. The key point says it is 'Written by the PO'.

#### ASB/RPD-14: Code-With Engineering Playbook: Backlog Management

Status: Confirmed.

- User stories have clear acceptance criteria and a DoD. Design for a story that needs it is done before the story enters a sprint.
- Refinement is an ongoing activity, not only a meeting. Shortcuts that create tech debt should be avoided, and any that happen are planned for later reduction.
- *Fact-checker's note:* HTTP 200. Goals: stories have 'a clear acceptance criteria and definition of done'; 'a design for a story that needs it should be done before it is added in a Sprint'. Suggestions: refinement is 'an ongoing activity'. 'Shortcuts should GENERALLY be avoided. In some rare instances where they happen, prioritizing and planning improvement activities to reduce this debt at a later time is the recommended approach.' Note: everything except the two Goals is under 'Suggestions', so it is advice, not a rule.

#### ASB/RPD-15: Code-With Engineering Playbook: Agile/Scrum Roles

Status: Confirmed.

- 'We prefer using "process lead" over "scrum master". It describes the same role.' It defers role definitions to the Scrum Guide, which is not fetchable here (ASB/RPD-21).
- *Fact-checker's note:* HTTP 200, 631 bytes. 'We prefer using "process lead" over "scrum master". It describes the same role.' is verbatim, and role definitions are linked to scrumguides.org. ERROR in the key point: it says the Scrum Guide is 'not fetchable here (ASB/RPD-21)'. The Scrum Guide is ASB/RPD-20; ASB/RPD-21 is SVPG Four Big Risks. The cross-reference is wrong.

#### ASB/RPD-16: Example Mapping (Cucumber docs)

Status: Confirmed.

- 'Before you pull a user story into development, it's crucial to have a conversation to clarify and confirm the acceptance criteria.'
- Cards: story (yellow), rules/acceptance criteria (blue), examples per rule (green), open questions or assumptions (red), plus new or deferred stories. 'We keep going until the group is satisfied that the scope of the story is clear, or we run out of time.'
- *Fact-checker's note:* HTTP 200. Opening sentence is verbatim: 'Before you pull a user story into development, it's crucial to have a conversation to clarify and confirm the acceptance criteria.' Cards: yellow story, blue rules/acceptance criteria, green examples, red questions. New or deferred user stories are mentioned but have no colour assigned. 'We keep going until the group is satisfied that the scope of the story is clear, or we run out of time.' is verbatim.

#### ASB/RPD-17: Who Does What? Roles and responsibilities in a BDD team (Cucumber docs)

Status: Confirmed.

- Three Amigos: the product owner (scope; decides what is in scope when the tester raises edge cases), the tester (scenarios and edge cases) and the developer (steps and technical details). It is 'essential' that they discover examples together. Example Mapping and Event Storming are named as techniques.
- After the style is established, a developer and tester pair can write the Gherkin, 'as long as their output is actively reviewed by the product owner (or business representative)'.
- Gherkin rules: a scenario that cannot be described in one sentence should be split; a Given describes one thing; say the same thing the same way every time.
- *Fact-checker's note:* HTTP 200. Three Amigos roles are confirmed, including that the PO decides scope when the tester raises edge cases. 'it is *essential* that all of these roles have conversations to discover examples *together*'. Example Mapping and Event Storming are named. The pair rule is confirmed: 'as long as their output is actively reviewed by the product owner (or business representative)'. The Gherkin rules are hedged in the source: a scenario you cannot describe in one sentence is 'PROBABLY trying to cover too much', and a Given 'IN GENERAL ... should describe only one thing'. The key points drop these hedges. The page also says Three Amigos is 'at least' three people and should not be held only once; the key points leave this out.

#### ASB/RPD-18: EventStorming Glossary & Cheat Sheet

Status: Confirmed.

- Re-verified 2026-10-31 (EP/ENG-14). Cites Brandolini's leanpub books as image sources.
- Domain Event: relevant to domain experts, a verb in the past tense (orange). HotSpot (neon pink) captures conflicts, inconsistencies in language, questions and dissent.
- Three levels: Big Picture, Process Modelling and Software Design. In the Software Design level, 'Constraint' replaces the legacy word 'aggregate' with business stakeholders.
- 'you want to have a dedicated facilitator' with 'a neutral role so that you can cut long discussions short and visualise them with hotspots'. Invite 'everyone who brings knowledge and who needs the knowledge, usually domain experts and the engineers'.
- *Fact-checker's note:* HTTP 200. Image sources cite leanpub books by Brandolini (ddd_first_15_years, introducing_eventstorming). Domain Event: 'relevant for the domain experts', 'a verb at the past tense', orange. HotSpot: neon pink, for conflicts, inconsistencies (in language), questions, dissent. Three levels: Big Picture, Process modelling and Software Design. Constraint: 'It was called an aggregate before which is now officially a legacy word in EventStorming, since we prefer not to use the word aggregate with business stakeholders'. Facilitator: 'you want to have a dedicated facilitator' and 'a neutral role so that you can cut long discussions short and visualise them with hotspots'. Invite: 'everyone who brings knowledge and who needs the knowledge, usually domain experts and the engineers'. Correctly marked official=false (community source).

#### ASB/RPD-19: DDD Starter Modelling Process

Status: Confirmed.

- Re-verified 2026-10-31 (EP/ENG-11).
- Discover: 'This is the most crucial aspect of DDD. You cannot skip discovery.' 'Discovery is Continuous' ... 'Teams who are successful with DDD are practicing discovery techniques on a frequent basis.'
- Discover tools: Domain Storytelling, Example Mapping, EventStorming, User Journey Mapping, User Story Mapping. Who to involve: builders and testers, people with domain knowledge, product strategy owners, people who understand customer needs, 'Real end users'.
- 'not a linear sequence of steps that you should standardise as a best practice'.
- *Fact-checker's note:* HTTP 200. Line 167: 'This is the most crucial aspect of DDD. You cannot skip discovery.' Line 173-175: 'Discovery is Continuous ... Teams who are successful with DDD are practicing discovery techniques on a frequent basis.' The Discover tools (Domain Storytelling, Example Mapping, User Journey Mapping, User Story Mapping) are listed, and 'People who have domain knowledge' and 'Real end users' appear among who to involve. Line 9: 'not a linear sequence of steps that you should standardise as a best practice', in a process the page says 'is for beginners'. Correctly marked official=false.

#### ASB/RPD-20: The Scrum Guide (2020) (unverified)

Status: Unverified: scrumguides.org does not resolve here; search snippets only.

- NOT FETCHED: scrumguides.org does not resolve in this session (WebFetch ENOTFOUND; curl CONNECT 403). EP already recorded the block on 2026-10-03.
- Search snippets only, not verified: the 2020 edition introduced the Product Goal and replaced 'roles' with 'accountabilities'; scrum.org quotes the PO accountability 'Developing and explicitly communicating the Product Goal'. The Scrum Master accountability list could not be checked.
- *Fact-checker's note:* none; unverified sources were not re-checked.

#### ASB/RPD-21: The Four Big Risks (unverified)

Status: Unverified: svpg.com does not resolve here; secondary summaries only.

- NOT FETCHED: www.svpg.com does not resolve (ENOTFOUND). The URL comes from WebSearch results.
- Secondary summaries only: value, usability, feasibility and viability risks are addressed in discovery before delivery. Which role owns which risk (PM: value and viability; designer: usability; engineer: feasibility) was NOT attributable to SVPG in the results.
- *Fact-checker's note:* none; unverified sources were not re-checked.

#### ASB/RPD-22: Opportunity Solution Trees / Continuous Discovery (Product Talk) (unverified)

Status: Unverified: producttalk.org does not resolve here; secondary summaries only.

- NOT FETCHED: www.producttalk.org does not resolve (ENOTFOUND).
- Secondary summaries only: continuous discovery = 'at a minimum, weekly touchpoints with customers, by the team building the product ... in pursuit of a desired product outcome'. The OST runs outcome -> opportunities -> solutions -> assumption tests, and the product trio does discovery together.
- *Fact-checker's note:* none; unverified sources were not re-checked.

#### ASB/RPD-23: BABOK Guide (IIBA) (unverified)

Status: Unverified: iiba.org refused by the proxy; search snippet only.

- NOT FETCHED: www.iiba.org was refused by the proxy (CONNECT 403 in agentproxy status).
- Search snippet only: BABOK v3 defines six knowledge areas that 'logically organize tasks but do not specify a sequence, process, or methodology', plus the BACCM core concept model. No task-level detail could be verified.
- *Fact-checker's note:* none; unverified sources were not re-checked.

#### ASB/RPD-24: HAX Toolkit: Guidelines for Human-AI Interaction (unverified)

Status: Unverified: the researcher could not reach www.microsoft.com; the fact-checker later reached the page (HTTP 200) and found '18 Guidelines', but did not check the guideline texts G1-G18.

- NOT re-fetched this session (www.microsoft.com is blocked). The repo's DPA/DESIGN-11 records all 18 guidelines (G1-G18) as fetched verbatim from https://www.microsoft.com/en-us/haxtoolkit/library/ on 2026-10-03. I could not re-verify that today.
- *Fact-checker's note:* COUNTER-FINDING on a source marked verified=false. The researcher wrote 'www.microsoft.com is blocked', but from this session curl -sSL returned HTTP 200 (131375 bytes, no redirect). The page states 'Learn about the 18 Guidelines in the HAX Design Library', which supports the count of 18. I did not fetch the individual guideline texts G1-G18 (the /haxtoolkit/library/ page), so the repo's DPA/DESIGN-11 verbatim claims remain unconfirmed. They can be re-verified now rather than treated as blocked. The other verified=false sources (ASB/RPD-20, 21, 22, 23, 25, 26) returned curl 000 (unreachable) from this session too, which matches the researcher's statement that they are blocked.

#### ASB/RPD-25: 10 Usability Heuristics for User Interface Design (unverified)

Status: Unverified: nngroup.com blocked; listed only so nobody cites it as verified.

- NOT FETCHED (blocked, as DPA also recorded). Listed only so that nobody cites it as verified.
- *Fact-checker's note:* none; unverified sources were not re-checked.

#### ASB/RPD-26: EventStorming (official site) (unverified)

Status: Unverified: eventstorming.com blocked; the method is covered by ASB/RPD-18 and ASB/RPD-19.

- NOT FETCHED (blocked). Brandolini's method is verified only through the DDD Crew pages ASB/RPD-18 and ASB/RPD-19, which cite his leanpub books.
- *Fact-checker's note:* none; unverified sources were not re-checked.

### 4.6 REN

#### ASB/REN-01: Trunk-based development (DORA capability)

Status: Confirmed.

- Have three or fewer active branches in the application's code repository.
- Merge branches to trunk at least once a day.
- Don't have code freezes and don't have integration phases.
- Pitfall: 'An overly heavy code-review process ... requires multiple approvals before changes can be merged into trunk'.
- Pitfall: performing code reviews asynchronously; further reviews should be performed synchronously.
- *Fact-checker's note:* All 5 points are stated. Lines 92-94 have the three-or-fewer active branches, merging at least once a day, and no code freezes or integration phases. Lines 101-121 have both pitfalls. CONTEXT FLAG for challenge note (1): DORA's objection is narrower than the note says. The pitfall is a heavyweight process with multiple approvals that is 'laborious and takes hours or days', which leads developers to batch changes. DORA does not object to multiple approvals as such. A multi-approval rule is in tension with the source only if it makes reviews slow, so the right test is to measure review latency and PR size. The note's 'goes against that' overstates it. The synchronous-review point is accurate: 'If further reviews are required, they should be performed synchronously.'

#### ASB/REN-02: DORA's software delivery performance metrics (guide)

Status: Confirmed.

- DORA now uses five metrics, not four keys. Throughput: change lead time, deployment frequency, failed deployment recovery time. Instability: change fail rate, deployment rework rate.
- MTTR was replaced by Failed Deployment Recovery Time.
- Pitfalls: setting metrics as a goal (Goodhart's law), one metric to rule them all, disparate comparisons, competing, siloed ownership.
- Reduce batch size: 'Teams should make each change as small as possible'.
- *Fact-checker's note:* Lines 14-17: there are five metrics, moved from the 'original four keys', and MTTR became Failed Deployment Recovery Time. Lines 32-43: throughput is change lead time, deployment frequency and failed deployment recovery time; instability is change fail rate and deployment rework rate. Lines 61-66 list all five pitfalls, including Goodhart's law. Line 81 says 'Teams should make each change as small as possible'.

#### ASB/REN-03: Test automation (DORA capability)

Status: Confirmed.

- High performers practice TDD and get feedback from tests in less than ten minutes.
- Testers work alongside developers throughout the lifecycle; testers have 'an essential role performing exploratory testing and usability testing'.
- When an error turns up in an acceptance test or during exploratory testing, add a unit test.
- Pitfall: 'Tolerating unreliable tests' / don't tolerate flaky tests.
- *Fact-checker's note:* Line 11 has TDD and feedback 'in less than ten minutes'. Line 153: testers 'play an essential role performing exploratory testing and usability testing'. Line 190: add a unit test when an acceptance or exploratory test finds an error. Lines 199-201: 'Tolerating unreliable tests' and 'don't tolerate flaky' tests.

#### ASB/REN-04: Continuous integration (DORA capability)

Status: Confirmed.

- Each commit should trigger a build and a series of automated tests that give feedback in a few minutes.
- When the automated tests fail, the team stops what it is doing to fix the problem.
- Developers merge into a shared trunk at least daily.
- *Fact-checker's note:* Lines 50-52: each commit triggers a build and automated tests with 'feedback in a few minutes'. Line 38: 'the team stops what they are doing to fix' it. Line 91: merge into the shared trunk 'at least daily'.

#### ASB/REN-05: Monitoring and observability (DORA capability)

Status: Confirmed.

- Avoid cause-based alerting, i.e. enumerating every error condition and writing an alert for each; prefer symptom-based alerting.
- *Fact-checker's note:* Lines 249-253: listing every error condition and writing an alert for each is 'cause-based alerting', which 'you should avoid ... as much as possible'; focus on symptom-based alerting. Small nuance: the source says 'avoid as much as possible', not an absolute ban.

#### ASB/REN-06: Identifying and tracking toil using SRE principles

Status: Confirmed.

- Quotes SRE book ch.5: 'Toil is the kind of work that tends to be manual, repetitive, automatable, tactical, devoid of enduring value, and that scales linearly as a service grows.'
- 'Within Google SRE, we aim to keep toil below 50% of each SRE's time'; if exceeded, plan work explicitly to reduce it.
- Identify toil by tracking tickets and surveying the team, and prioritise by aggregate human time.
- *Fact-checker's note:* The page quotes the SRE book ch.5 definition of toil word for word. It says 'Within Google SRE, we aim to keep toil below 50% of each SRE's time', and that if over the threshold 'we plan work explicitly' to reduce it. It recommends surveying the team (with a sample survey) and looking at tickets, surveys and on-call, and to 'prioritize based on the aggregate human time spent'. Note that the 50% figure is Google's own internal target, not a universal rule.

#### ASB/REN-07: SRE fundamentals: SLIs, SLAs and SLOs (re-verification of repo REL-01)

Status: Confirmed.

- The SLO is a precise numerical target for system availability, and decisions about reliability and design work are made against it.
- Availability shouldn't be much better than the SLO (the sentence was truncated in my extract).
- *Fact-checker's note:* The page says 'we wanted to set a precise numerical target for system availability. We term this target the availability Service-Level Objective', and that future reliability and design or architecture discussions are made against it. The sentence the researcher marked as truncated reads in full: 'because of the principle that availability shouldn't be much better than the SLO, the availability SLO in the SLA is normally a looser objective than the internal availability SLO.'

#### ASB/REN-08: SRE error budgets and maintenance windows (re-verification of repo REL-02)

Status: Confirmed.

- Setting SLOs gives you an error budget.
- An error budget is the amount of error a service can accumulate over a period before users start being unhappy.
- Budget freeze with a small number of 'silver bullet' exceptions for business-critical launches.
- *Fact-checker's note:* The author and date match (Jesus Climent, June 22, 2020). The page says 'You set your service-level objectives, which in turn gives you an error budget' and 'an error budget is the amount of error that your service can accumulate over a certain period of time before your users start being unhappy'. It defines 'silver bullets' as 'a very small number of exceptions for truly business-critical emergency launches, despite the budget maintenance window freeze'. The key point leaves out 'emergency'; this is minor.

#### ASB/REN-09: Site Reliability Engineering book: Service Level Objectives / Embracing Risk / Eliminating Toil (unverified)

Status: Unverified: sre.google blocked; the fact-checker's retry also failed.

- NOT FETCHED: sre.google is outside the session's allowed network. Ask for it to be allowed before citing the book directly. ASB/REN-06/07/08 quote it second-hand from official Google Cloud posts.
- *Fact-checker's note:* The researcher marked this unverified. My re-try also failed (curl exit 000, host blocked). Cite ASB/REN-06/07/08 instead.

#### ASB/REN-10: Short-lived feature branches

Status: Confirmed.

- 'the branch should only last a couple of days. Any longer than two days, and there is a risk of the branch becoming a long-lived feature branch'.
- Addresses agentic coding: the unit is one developer and their coding agents.
- The Feature Flags page lists flag tech debt as a pitfall (flags must be removed).
- *Fact-checker's note:* Lines 39-41 quote the couple-of-days and two-days rule word for word. Line 52: 'With agentic coding: the unit is one developer and their coding agents.' The feature-flags page (content/feature-flags/index.md, line 93) has the 'Tech Debt - pitfall' section and advises remediating flags about a month after release. One addition relevant to the team's worktree-per-agent setup: lines 153-159 and 176-182 warn that each agent worktree counts as a short-lived branch, and that review and merge capacity, not branch creation, becomes the limit. This supports counter-idea (1).

#### ASB/REN-11: Google eng-practices: The Standard of Code Review (re-verify)

Status: Confirmed.

- Reviewers should favor approving a CL once it definitely improves overall code health, even if it isn't perfect; there is no such thing as 'perfect' code.
- 'Technical facts and data overrule opinions and personal preferences'; on style, the style guide is the authority.
- Prefix optional polish comments with 'Nit:'.
- *Fact-checker's note:* Lines 31-34 cover favouring approval once a CL definitely improves code health even if it isn't perfect, and line 42 says there is no such thing as 'perfect' code. The Principles section has 'Technical facts and data overrule opinions and personal preferences' and says the style guide 'is the absolute authority' on style. 'Nit:' prefixes appear in two places. The page also says nothing justifies a CL that definitely worsens code health. Include that caveat when citing this source for counter-idea (2).

#### ASB/REN-12: Google eng-practices: What to look for in a code review (re-verify)

Status: Confirmed.

- Sections: Design, Functionality, Complexity (incl. over-engineering), Tests, Naming, Comments, Style, Documentation.
- 'Will the tests actually fail when the code is broken?' Tests are code that must be maintained.
- Encourage developers to solve the problem they know needs solving now, not speculative future ones.
- *Fact-checker's note:* Section headings include Design, Functionality, Complexity, Tests, Naming, Comments, Style and Documentation. The list in the key point is incomplete: Consistency, Every Line, Context and Good Things are missing, which is acceptable as a summary. Line 74 asks 'Will the tests actually fail when the code is broken?' and line 79 says tests are code that has to be maintained. Lines 57-59 say to solve the problem needed now, not a speculative future one.

#### ASB/REN-13: Google eng-practices: Handling pushback / Speed of code reviews

Status: Confirmed.

- 'Cleaning It Up Later': deferred cleanups usually don't happen, so ask for cleanup now or require a filed bug.
- When the developer is right, let the issue drop.
- speed.md: 'One business day is the maximum time it should take to respond' to a review request.
- *Fact-checker's note:* Line 15: when the developer is right, 'let the issue drop'. Lines 42-60 are 'Cleaning It Up Later': unless the cleanup happens immediately 'it never happens', so insist on cleanup now; new complexity 'must be cleaned up before submission unless it is an emergency', and for surrounding problems the developer 'should file a bug'. speed.md line 36: 'One business day is the maximum time it should take to respond'.

#### ASB/REN-14: Decision record template by Michael Nygard

Status: Confirmed.

- ADR sections: Title, Status (proposed, accepted, rejected, deprecated, superseded), Context, Decision, Consequences ('What becomes easier or more difficult').
- The original Nygard post (cognitect.com) could not be fetched because the host is blocked.
- *Fact-checker's note:* The sections Title, Status (proposed, accepted, rejected, deprecated, superseded, etc.), Context, Decision and Consequences ('What becomes easier or more difficult to do because of this change?') are all present. Minor correction: the page links Nygard's original at thinkrelevance.com/blog/2011/11/15/..., not cognitect.com as the researcher wrote.

#### ASB/REN-15: Design Reviews (Code-With Engineering Playbook)

Status: Confirmed.

- Front-load decisions before implementation, when they cost the least.
- Measure reviewer participation (same 2 people on every review means limited perspectives) and time to decision.
- If no quorum is reached, the person with the most context decides: 'Disagree and commit!'.
- *Fact-checker's note:* Line 38 covers front-loading 'decisions when they cost the least'. Line 19 covers reviewer participation, with the example 'same 2 individuals only on every review' meaning limited perspectives. There is a 'Time to Decisions' section. Line 31: when there is no quorum, the person with the most context decides, 'Disagree and commit!'.

#### ASB/REN-16: Testing FastAPI / Testing dependencies with overrides

Status: Confirmed.

- Use app.dependency_overrides to replace external-service dependencies, e.g. a paid auth provider, in tests.
- tutorial/testing.md: TestClient (httpx-based) used directly with pytest.
- security/index.md: OAuth2 expects the app to be served over HTTPS.
- *Fact-checker's note:* testing-dependencies.md lines 11-23 describe overriding an external auth provider that charges per request, using app.dependency_overrides. tutorial/testing.md says TestClient is based on HTTPX and works with pytest directly. tutorial/security/index.md line 33 says OAuth2 'expects you to have your application served with HTTPS'.

#### ASB/REN-17: OWASP API Security Top 10 2023 (re-verification of repo SEC-08)

Status: Confirmed.

- API1 BOLA, API2 Broken Authentication, API3 Broken Object Property Level Authorization, API4 Unrestricted Resource Consumption, API5 Broken Function Level Authorization, API6 Unrestricted Access to Sensitive Business Flows, API7 SSRF, API8 Security Misconfiguration, API9 Improper Inventory Management, API10 Unsafe Consumption of APIs.
- *Fact-checker's note:* The names API1 to API10 for 2023 match the table on lines 5-14 exactly.

#### ASB/REN-18: Canon TDD (unverified)

Status: Unverified: newsletter.kentbeck.com blocked; search snippets only.

- NOT FETCHED (host blocked). Seen in search results only: start with a test list of scenarios, turn exactly one item into a concrete runnable test, make it and all previous tests pass, refactor, and add newly discovered cases to the list.
- *Fact-checker's note:* Unverified. Re-try failed (000). The Canon TDD steps rest on search snippets only and must not be quoted as confirmed.

#### ASB/REN-19: Testing Library: Guiding Principles

Status: Confirmed.

- 'The more your tests resemble the way your software is used, the more confidence they can give you.'
- Deal with DOM nodes rather than component instances.
- *Fact-checker's note:* The page has the 'more your tests resemble the way your software is used' principle and says to deal with DOM nodes rather than component instances.

#### ASB/REN-20: Testing Library: About Queries, Priority

Status: Confirmed.

- Priority: queries accessible to everyone first, getByRole first ('if you can't, it's possible your UI is inaccessible'); getByTestId only as a last resort because users cannot see or hear test ids.
- *Fact-checker's note:* Lines 102-110 put getByRole first, with '(if you can't, it's possible your UI is inaccessible)'. Line 132: getByTestId, 'The user cannot see (or hear) these, so this is only' recommended as a last resort.

#### ASB/REN-21: Next.js docs: Testing (index)

Status: Confirmed.

- Defines unit, component, integration, E2E and snapshot testing.
- Because async Server Components are new, 'we recommend using End-to-End Testing over Unit Testing for async components'.
- *Fact-checker's note:* The page defines unit, component, integration, E2E and snapshot tests. It says async Server Components are new, so 'we recommend using End-to-End Testing over Unit Testing for async components'.

#### ASB/REN-22: Next.js docs: Production checklist

Status: Confirmed.

- Check 'use client' boundaries to avoid growing the client JS bundle.
- eslint-plugin-jsx-a11y to catch accessibility issues early.
- Server Actions: verify authn/authz inside each action, not only at layout or page level; consider a CSP.
- Lighthouse is a simulated test and should be paired with field data (Core Web Vitals, useReportWebVitals).
- *Fact-checker's note:* Line 46: check 'use client' boundaries to avoid growing the client JS bundle. Line 93: eslint-plugin-jsx-a11y. Line 100: Server Actions should 'Verify authentication and authorization inside each action. Do not rely on Proxy or layout or page level checks alone'. Line 105 says 'Consider adding' a CSP; the key point correctly says 'consider'. Lines 133-137: Lighthouse 'is a simulated test and should be paired with looking at field data (such as Core Web Vitals)', and the useReportWebVitals hook.

#### ASB/REN-23: React docs: Keeping Components Pure / You Might Not Need an Effect

Status: Confirmed.

- React assumes every component is a pure function: same inputs, same output (keeping-components-pure.md).
- Effects are an escape hatch for syncing with external systems; you don't need Effects to transform data for rendering.
- *Fact-checker's note:* you-might-not-need-an-effect.md line 7 calls Effects 'an escape hatch' for syncing with external systems, and line 26 says 'You don't need Effects to transform data for rendering.' keeping-components-pure.md line 24 says 'Same inputs, same output', and line 7 says to write components as pure functions.

#### ASB/REN-24: web.dev: Performance budgets 101 / Defining Core Web Vitals thresholds

Status: Confirmed.

- A performance budget is a set of limits on metrics that affect performance. Use quantity-based, milestone-timing and rule-based metrics, and add budgets to the build process.
- CWV thresholds are assessed at the 75th percentile of page views; LCP good is 2.5 s or less, CLS good is 0.1 or less.
- CAVEAT: the archived thresholds article still uses FID (100 ms). The current INP metric could not be verified because web.dev is blocked.
- *Fact-checker's note:* performance-budgets-101 has the definition of a budget as 'a set of limits imposed on metrics that affect site performance', the quantity-based, milestone-timing and rule-based metric types, and a section titled 'Add performance budgets to your build process'. defining-core-web-vitals-thresholds (updated 2022-07-18) has the 75th percentile, LCP of 2500 ms or less, CLS of 0.1 or less and FID of 100 ms or less. ARCHIVED STATUS CONFIRMED: README.md at HEAD is titled 'web.dev [Archived]' and says the repo is read-only, and a blobless fetch shows the last commit at 2023-10-29 08:33 +0100. RESOLVES THE CAVEAT: the official GoogleChrome/web-vitals repo on GitHub has a CHANGELOG entry '[BREAKING] Remove the deprecated onFID() function', its README lists INP as a Core Web Vital, and it gives INPThresholds as [200, 500]. So 'INP replaced FID' and 'INP good is 200 ms or less' can be cited from that repo, and any doc citing FID is stale.

#### ASB/REN-25: Write tests. Not too many. Mostly integration. / The Testing Trophy

Status: Confirmed.

- The trophy layers are static, unit, integration and E2E, with most effort on integration.
- write-tests.mdx warns against mandating 100% coverage; returns diminish beyond roughly 70% (the author says the number is made up).
- *Fact-checker's note:* The trophy layers (End to End, Integration, Unit, Static) and the 'Mostly integration' framing are on the page. write-tests.mdx lines 60-63 say mandating 100% coverage for applications is 'a really bad idea' with 'diminishing returns ... much beyond 70% (I made that number up...)'. CONTEXT FLAG: lines 76-80 say most of the author's open-source libraries do have 100% coverage, so the warning is about mandating it for applications, not about high coverage in general. Keep that nuance if it is used to challenge a coverage floor.

#### ASB/REN-26: Pact docs: Convince me (contract testing vs E2E)

Status: Confirmed.

- Consumer-driven contract tests reduce or eliminate tests that need a deployed environment.
- They let the consumer (UI) be developed before the provider (API) and drive provider requirements.
- *Fact-checker's note:* Line 15 covers 'reducing the number of, or even eliminating, tests that need to run in a deployed environment'. Lines 78-79 cover developing the consumer (UI) before the provider (API) and driving out provider requirements.

#### ASB/REN-27: Consumer-Driven Contract Testing (Code-With Engineering Playbook)

Status: Confirmed.

- CDC tests components in isolation while checking the provider meets consumer expectations.
- E2E tests are slow, break easily, and are expensive and hard to maintain.
- *Fact-checker's note:* Line 3 defines CDC as testing components in isolation while ensuring the provider meets consumer expectations. Lines 9-11: E2E tests 'are slow', 'break easily', and 'are expensive and hard to maintain'.

#### ASB/REN-28: Test planning (Code-With Engineering Playbook)

Status: Confirmed.

- Derive test cases from acceptance criteria while designing the story; this also clarifies the criteria.
- Identify and prioritise test cases by risk to focus on the most critical areas.
- *Fact-checker's note:* Lines 9-13 cover defining test cases from acceptance criteria while designing the story, which 'helps clarify the acceptance criteria'. Line 89 covers 'identifying and prioritizing test cases based on risk ... focus on the most critical areas'.

#### ASB/REN-29: OWASP Threat Modeling Cheat Sheet

Status: Confirmed.

- Four questions (citing the Threat Modeling Manifesto): What are we working on? What can go wrong? What are we going to do about it? Did we do a good enough job?
- DFDs with trust boundaries, data flows, stores, processes and external entities, saved in a form the team can update.
- STRIDE as prompts against components, flows and boundaries.
- Perform early (design phase), keep it maintained alongside the system, and make it a standard SDLC step, not an add-on.
- *Fact-checker's note:* Lines 14-19 give the four questions, citing the Threat Modeling Manifesto. Lines 47-49 say to save DFDs 'in a form the team can update', with trust boundaries, data flows, data stores, processes and external entities. Lines 77-98 cover STRIDE as prompts against components, flows and boundaries. Line 12: perform early in design, maintain it alongside the system, as 'a standard and necessary step ... not an add-on'. The page also recommends LINDDUN for privacy threats (line 101), which the researcher did not capture and which is relevant to the security-privacy role.

#### ASB/REN-30: Threat Modeling (Code-With Engineering Playbook)

Status: Confirmed.

- Phases: Diagram, Identify (STRIDE), Mitigate, Validate.
- *Fact-checker's note:* The phases are Diagram, Identify (STRIDE framework), Mitigate and Validate.

#### ASB/REN-31: Threat Modeling Manifesto (unverified)

Status: Unverified: threatmodelingmanifesto.org blocked; the four questions are confirmed second-hand via ASB/REN-29.

- NOT FETCHED (host blocked). The four questions are verified second-hand via ASB/REN-29. Values such as 'continuous refinement over a single delivery' were seen only in search snippets.
- *Fact-checker's note:* Unverified. Re-try failed (000). The four questions are confirmed second-hand through ASB/REN-29. The 'values' are not confirmed.

#### ASB/REN-32: OWASP ASVS 5.0: What is the ASVS (re-verification of repo SEC-01)

Status: Confirmed.

- Three levels L1-L3; start at L1 and move up as needed.
- Documented security decisions: documentation requirements come first in a chapter and pair with an implementation requirement. Verifying the documentation and verifying the implementation are two separate activities.
- There is no such thing as scope for attackers; evaluate ASVS alongside CI/CD, hosting and operations.
- *Fact-checker's note:* Line 73: three levels, start with the first and move up as needed. Line 59: documentation requirements come first in a chapter and pair with an implementation requirement, and verifying each is 'two separate activities'. Line 11: 'There is no such thing as scope for attackers', so evaluate ASVS alongside CI/CD, hosting and operations. OMISSION FLAG: line 101 says of Level 2 that 'Most applications should be striving to achieve this level of security'. Citing only 'start at L1' could support an L1-only target the source does not endorse for an app that handles personal video data.

#### ASB/REN-33: OWASP Top 10 Privacy Risks v2.0 (2021)

Status: Confirmed.

- Includes P1 Web Application Vulnerabilities, P2 Operator-sided Data Leakage, P3 Insufficient Data Breach Response, P4 Consent on Everything, P6 Insufficient Deletion of Personal Data, P7 Insufficient Data Quality, P8 Missing/insufficient Session Expiration, P9 Inability of users to access and modify data, P10 Collection of data not required for the user-consented purpose.
- *Fact-checker's note:* The page is 'Version 2.0 ... from 2021'. All the listed titles match. P5 'Non-transparent Policies, Terms and Conditions' is left out, which is fine because the key point says 'Includes'.

#### ASB/REN-34: Privacy: data handling (Code-With Engineering Playbook)

Status: Confirmed.

- Always apply data minimisation; state the intended purpose explicitly; define data retention a priori; prefer anonymised data.
- *Fact-checker's note:* Line 46: 'Always apply data minimization'. Line 69: 'Explicitly state the intended purpose'. Line 33: 'define a priori the data retention policies'. Line 49: request anonymized data. Context: the page is written for engagements with customer data, so it is guidance, not a regulation.

#### ASB/REN-35: The ML Test Score: A Rubric for ML Production Readiness and Technical Debt Reduction (Breck et al., IEEE Big Data 2017) (unverified)

Status: Unverified: research.google blocked; search snippets and a secondary slide only.

- NOT FETCHED (research.google and storage.googleapis are blocked). Search results only: a rubric of 28 tests and monitoring needs in four areas (data/features, model development, ML infrastructure, monitoring); the final score is the minimum across the areas (from a secondary slide).
- *Fact-checker's note:* Unverified. Re-try failed (000). The 28-test rubric and the minimum-score rule are not confirmed.

#### ASB/REN-36: Hugging Face Hub: Model Cards + Annotated Model Card Template

Status: Confirmed.

- A model card covers intended uses and limitations, including biases (citing Mitchell et al. 2018, arXiv 1810.03993), and evaluation results.
- Template sections: Model Details, Uses (Direct, Downstream, Out-of-Scope), Bias, Risks and Limitations, Training Details (Data, Procedure), Evaluation (Testing Data, Factors and Metrics, Results), Environmental Impact, Technical Specifications.
- Model cards are Markdown with YAML metadata (e.g. datasets used).
- *Fact-checker's note:* model-card-annotated.md headings match the template sections: Model Details; Uses (Direct, Downstream [optional], Out-of-Scope); Bias, Risks, and Limitations; Training Details (Training Data, Training Procedure); Evaluation (Testing Data, Factors & Metrics, Results); Environmental Impact; Technical Specifications [optional]. Point 1 (intended uses and limitations including biases, citing Mitchell 2018, plus evaluation results) and point 3 (Markdown with YAML metadata, datasets) come from the sibling page model-cards.md, lines 10-13 and 25. Both pages were fetched and confirmed. Note that several sections are marked [optional] in the template.

#### ASB/REN-37: Model Cards for Model Reporting (Mitchell et al.) (unverified)

Status: Unverified: arxiv.org blocked; cited second-hand via ASB/REN-36.

- NOT FETCHED (arxiv blocked). Cited by ASB/REN-36.
- *Fact-checker's note:* Unverified. Re-try failed (000). The only confirmed citation is through ASB/REN-36 (model-cards.md line 10).

#### ASB/REN-38: DVC Get Started

Status: Confirmed.

- Version large datasets and models alongside code without storing them in Git ('Git for data'); switch data versions with git checkout; data pipelines, metrics and experiment tracking.
- *Fact-checker's note:* The page covers tracking large datasets and models, 'Git for data' (line 28), switching versions with git checkout followed by dvc checkout (lines 353-368), and pipelines, metrics and experiments (line 5).

#### ASB/REN-39: Create custom subagents (Claude Code docs)

Status: Confirmed.

- Frontmatter: only name and description are required. Supported fields include tools, disallowedTools, model, permissionMode, memory, skills, isolation and more. 'Claude Code ignores a field it doesn't recognize without reporting an error'.
- Keep descriptions short; there is a warning when combined descriptions exceed 15,000 tokens. Move detail into the system prompt body.
- Check project subagents (.claude/agents/) into version control.
- Include 'use proactively' in the description to encourage delegation; persistent memory scope 'project' is the recommended default.
- *Fact-checker's note:* Line 289: 'Only name and description are required'. Line 223 lists the fields: tools, disallowedTools, model, permissionMode, memory, skills, isolation and more. Line 291: 'Claude Code ignores a field it doesn't recognize without reporting an error'. Line 27: keep descriptions short, with a warning above 15,000 tokens; move detail into the body. Line 166: check .claude/agents/ into version control. Line 838: include phrases like 'use proactively'. Line 666: 'project is the recommended default scope'. CHALLENGE NOTE (4) CHECKED against origin/main: security-privacy-engineer.md has 'tools: Read, Grep, Glob, Bash' and calls itself a '(read-only reviewer)'. The body (line 11) already limits Bash to 'read-only inspection and scanners', so the gap is that read-only is enforced only by the prompt, not by the tools list. Bash can still write. That is a real gap but softer than 'mislabelled'.

#### ASB/REN-40: Domain-Driven Design Reference (Evans) / Effective Aggregate Design (Vernon) (unverified)

Status: Unverified: domainlanguage.com blocked; not fetched.

- NOT FETCHED (host blocked). For DDD, rely on the repo's existing ENG-11..14 (ddd-crew), which are already verified.
- *Fact-checker's note:* Unverified. Re-try failed (000).

#### ASB/REN-41: ISTQB Certified Tester Foundation Level syllabus / glossary (risk-based testing, exploratory testing) (unverified)

Status: Unverified: istqb.org blocked; not fetched, no definitions quoted.

- NOT FETCHED (host blocked). No ISTQB definitions are quoted in this research; the risk-based and exploratory practices rest on ASB/REN-03 and ASB/REN-28.
- *Fact-checker's note:* Unverified. Re-try failed (000). The risk-based and exploratory testing claims rest only on ASB/REN-03 and ASB/REN-28, both of which are confirmed.

## 5. Practices by area

These are the practices the researchers derived from the sources. They are inputs for the audit, not rules. A practice becomes a team rule only when the PO approves the change that adopts it, and it never overrides a PO decision.

**Strength** is the researcher's grade:

- **official**: stated by the publisher of the tool or standard in question (for example Anthropic for Claude Code, DORA for its metrics).
- **strong-consensus**: several independent, reputable sources say the same thing.
- **expert-opinion**: one practitioner or vendor source, or the researcher's synthesis.

Counts: 80 official, 27 strong-consensus, 27 expert-opinion.

A source ID followed by **(unverified)** is not Confirmed (§3). Where a practice rests partly on such a source, the row says so, and that part should be treated as unconfirmed whatever the grade. Each practice also has a *Check* clause where the researcher gave one: that is how to test whether a doc follows it.

### 5.1 Anthropic guidance for agent teams on Claude Code

| Practice | Strength | Sources | Applies to |
|---|---|---|---|
| **ASB/P-ANT-01**: Every role file has valid YAML frontmatter with `name` (lowercase-hyphen, unique across .claude/agents/, no ':') and `description`. Check: `claude plugin validate .claude/agents` passes, and no two files share a name. | official | [ASB/ANT-01] | role files (all roles); ci-cd |
| **ASB/P-ANT-02**: The `description` states WHEN to delegate, with concrete trigger situations unique to that role (not just a job title), and is specific enough that no two roles' descriptions route the same request. Check: for each pair of roles, name a request that would route to one and not the other. Add 'Use proactively when X' only where proactive use is wanted. Keep descriptions short; all custom descriptions combined must stay well under 15,000 tokens. | official | [ASB/ANT-01], [ASB/ANT-24] | role files (all roles) |
| **ASB/P-ANT-03**: Least-privilege tools. Every role file sets an explicit `tools` list (omitting it inherits all tools). Review-only roles get no Write/Edit and, where possible, no Bash, or have them removed with disallowedTools. Roles that must not spawn subagents omit `Agent`. Check: each tool listed is justified by a duty in the body; reviewers mirror the official read-only code-reviewer (ASB/ANT-25). Counter-check for this repo: principal-engineer and principal-designer currently list Write and Edit (see gaps). | official | [ASB/ANT-01], [ASB/ANT-05], [ASB/ANT-10], [ASB/ANT-25] | role files (principal-engineer, principal-designer, security-privacy-engineer, senior-qa-engineer, all roles) |
| **ASB/P-ANT-04**: Rules that must never bend (no merge without the gate, no force-push, no test deletion, no secret reads) are enforced deterministically by hooks, deny rules, CI branch protection or a merge script, not only by prose in role files or the working agreement. Prose that duplicates an enforced rule names its enforcing mechanism. Check: every 'must/never' rule in working-agreement and DoD maps to an enforcing hook, deny rule or CI check, or is explicitly marked advisory. *Note: rests partly on unconfirmed source(s) ASB/ANT-03.* | official | [ASB/ANT-02], [ASB/ANT-03] (unverified), [ASB/ANT-05], [ASB/ANT-08] | working-agreement; definition-of-done; ci-cd; role files (all roles) |
| **ASB/P-ANT-05**: No shouting. Don't use IMPORTANT, CRITICAL, MUST or ALL CAPS emphasis to make a rule stick; current models over-apply emphasized rules. Write a plain line, and if it still gets missed, convert it to a hook or shorten the file. Check: count emphasis tokens per file; each one needs a justification. | official | [ASB/ANT-08], [ASB/ANT-21] | role files (all roles); working-agreement; requirements |
| **ASB/P-ANT-06**: Keep always-loaded instructions short and high-signal. Target under 200 lines for CLAUDE.md. Role bodies hold only what the agent cannot infer from the repo (exact commands, non-obvious decisions, things corrected twice). Don't describe architecture or file layout the agent can read. Move procedures to skills or path-scoped rules. Check: line counts, and for each paragraph ask 'would removing this cause a mistake?'. | official | [ASB/ANT-02], [ASB/ANT-08], [ASB/ANT-13], [ASB/ANT-23] | role files (all roles); working-agreement; testing-strategy; ddd-guidelines |
| **ASB/P-ANT-07**: No contradictions across instruction files. A rule lives in one canonical place (for example DoD) and other files reference it rather than restate it. Check: run `/doctor prompt-audit` (v2.1.283+) over CLAUDE.md, .claude/agents, skills and rules before each sprint, and diff overlapping rules such as DoD versus working-agreement versus role files. | official | [ASB/ANT-02] | working-agreement; definition-of-done; definition-of-ready; role files (all roles); retro |
| **ASB/P-ANT-08**: Structure role bodies in clear sections (XML tags or Markdown headers): role (one sentence), responsibilities/scope, constraints, tools guidance, and an explicit output format. Give the why behind non-obvious rules. Check: each role file has a defined output/report format, as in the official reviewer (findings with file:line, evidence and fix, plus an explicit 'nothing found' form). | official | [ASB/ANT-13], [ASB/ANT-21], [ASB/ANT-25] | role files (all roles) |
| **ASB/P-ANT-09**: Every delegation (ticket assignment or spawn prompt) contains an objective, output format, tools/sources guidance, clear boundaries (files owned, what not to touch), and a definition of done. Subagents don't see the lead's history. Check: sprint-planning ticket templates include these five fields. | official | [ASB/ANT-09], [ASB/ANT-12] | sprint-planning; definition-of-ready; working-agreement |
| **ASB/P-ANT-10**: Parallel work is partitioned by file ownership, with a claim/lock mechanism so two agents never edit the same file or solve the same task. Shared status files are written by one designated owner. Check: the plan maps each ticket to disjoint paths, and the working agreement names who may edit shared logs. | official | [ASB/ANT-09], [ASB/ANT-19] | sprint-planning; working-agreement |
| **ASB/P-ANT-11**: Right-size the team and the tasks. Start with 3-5 parallel workers and about 5-6 self-contained tasks each (a function, a test file, a review). Only add agents when the work is genuinely independent; multi-agent runs cost about 15x a chat. Check: the sprint plan justifies its number of concurrent agents, and no ticket is a one-tool-call task delegated to a subagent. | official | [ASB/ANT-09], [ASB/ANT-12], [ASB/ANT-22], [ASB/ANT-11] | sprint-planning; working-agreement |
| **ASB/P-ANT-12**: Define done before implementation as a checkable contract: acceptance criteria plus the exact commands or tests that prove them, agreed between implementer and evaluator (a 'sprint contract'). QA exercises the running app against it. Check: each story has executable acceptance tests linked before work starts. | official | [ASB/ANT-18], [ASB/ANT-08], [ASB/ANT-16] | definition-of-ready; definition-of-done; sprint-planning; testing-strategy; requirements |
| **ASB/P-ANT-13**: Independent evaluation uses a separate agent with fresh context, tuned to be skeptical, with explicit gradable criteria, rather than self-review. Grade the outcome, not the path. Check: reviewer and QA role files contain concrete grading criteria and a confidence/severity threshold, and the reviewer is never the author. | official | [ASB/ANT-18], [ASB/ANT-08], [ASB/ANT-17], [ASB/ANT-25] | role files (principal-engineer, senior-qa-engineer, security-privacy-engineer); definition-of-done; working-agreement |
| **ASB/P-ANT-14**: Counter-guidance to weigh against P-ANT-13: on Opus 5, remove generic 'add a verification step' or 'use a subagent to verify' instructions inside a single agent's prompt; they cause over-verification. Keep independent review as a process gate, but don't also instruct every implementer to self-verify through subagents. Check: role files don't contain blanket self-verification or 'double-check with a subagent' lines. | official | [ASB/ANT-22], [ASB/ANT-08] | role files (all roles); working-agreement |
| **ASB/P-ANT-15**: Work incrementally: one feature or ticket at a time per agent, leave the environment clean, and update structured progress artifacts (prefer JSON for machine-updated status). Test edits are forbidden unless explicitly approved. Check: the working agreement requires a clean worktree at hand-off and a status update, and test-change rules (TCR) exist. | official | [ASB/ANT-16], [ASB/ANT-21] | working-agreement; definition-of-done; testing-strategy |
| **ASB/P-ANT-16**: Verifiers must be near-perfect. Invest in high-quality tests and oracles, add a test for each newly observed failure mode, and tell agents to report incorrect tests rather than work around them or hardcode for them. Check: testing-strategy requires a regression test per escaped defect and the retro tracks new failure modes. | official | [ASB/ANT-19], [ASB/ANT-21], [ASB/ANT-17] | testing-strategy; retro; role files (senior-qa-engineer, senior-backend-engineer, senior-frontend-engineer, senior-ml-cv-engineer) |
| **ASB/P-ANT-17**: Treat role files and process docs as prompts that need evals. Keep a small set (about 3 minimum, ideally 20-50) of representative tasks with unambiguous pass/fail, balanced positive and negative cases, a baseline, and transcript review. Re-run them on every change to a role file or shared instruction, and ablate lines to see each one's effect. Check: a prompt-change PR includes before/after eval evidence, not only reviewer approval. | official | [ASB/ANT-17], [ASB/ANT-20], [ASB/ANT-23], [ASB/ANT-15], [ASB/ANT-12] | role files (all roles); ci-cd; retro; working-agreement |
| **ASB/P-ANT-18**: Every scaffold rule encodes an assumption about what the model can't do alone. In each retro, list process rules and ask whether each is still load-bearing for the current model; drop stale scaffolding. Check: the retro template has a 'rules to remove' section. | official | [ASB/ANT-18], [ASB/ANT-08] | retro; working-agreement |
| **ASB/P-ANT-19**: Unattended or background runs must answer five questions: what done looks like, how it checks its work, what it may touch (permissions, worktree, branch), what stops it (maxTurns, budget, spawn-depth/concurrency caps), and who signs off. A human approves irreversible steps such as merge or deploy. Check: role files or orchestration set maxTurns or a budget, and the working agreement names the human sign-off point. | official | [ASB/ANT-08], [ASB/ANT-10], [ASB/ANT-22], [ASB/ANT-11] | working-agreement; ci-cd; role files (engineering-manager) |
| **ASB/P-ANT-20**: Use the right mechanism for each kind of instruction. CLAUDE.md holds always-true facts and commands. .claude/rules/ with paths: holds area-specific rules. Skills (SKILL.md, third-person description with key use case first, body under 500 lines, references one level deep, disable-model-invocation for side-effecting workflows) hold procedures. Subagents hold specialized roles. Hooks hold must-always rules. Check: no multi-step procedure lives in CLAUDE.md or a role body when it could be a skill. | official | [ASB/ANT-02], [ASB/ANT-06], [ASB/ANT-23], [ASB/ANT-24], [ASB/ANT-15] | working-agreement; role files (all roles); ci-cd |
| **ASB/P-ANT-21**: Write instructions at the right altitude: neither brittle if-else rule lists covering every edge case, nor vague guidance that assumes shared context. Prefer a few diverse canonical examples (3-5, in <example> tags) to long rule lists. Check: no role file has a laundry list of more than about 15 bullets without examples, and the 'new colleague' test passes. | official | [ASB/ANT-13], [ASB/ANT-21] | role files (all roles); working-agreement; requirements |
| **ASB/P-ANT-22**: Constrain scope explicitly. An agent delivers what was asked; if it sees a better approach it says so in one sentence and continues, rather than silently widening or narrowing the task. Match document length to need, with no filler or redundant summaries. Check: role files contain a scope rule, and generated docs carry no boilerplate sections. | official | [ASB/ANT-22] | role files (all roles); working-agreement |
| **ASB/P-ANT-23**: Commit shared team configuration (.claude/settings.json with permissions and hooks, .claude/agents/) to version control. Keep personal overrides in settings.local.json. Block secret reads with Read deny rules (not .claudeignore), and remember Bash/Read deny rules are not a security boundary without the sandbox. Check: settings.json has deny rules for secrets and the security doc doesn't overstate them. | official | [ASB/ANT-04], [ASB/ANT-05], [ASB/ANT-01] | ci-cd; working-agreement; role files (security-privacy-engineer, sre-devops-engineer) |
| **ASB/P-ANT-24**: Start simple and add agents or process steps only when they measurably help. Prefer one agent or a workflow over a multi-agent team for sequential or same-file work. Check: each added ceremony or extra reviewer in the process docs names the failure it prevents (ideally from a retro). | official | [ASB/ANT-11], [ASB/ANT-09], [ASB/ANT-22] | working-agreement; sprint-planning; retro |

### 5.2 Spec-driven development, BDD and ADRs

| Practice | Strength | Sources | Applies to |
|---|---|---|---|
| **ASB/SDD-P01**: Every story spec or FR states WHAT and WHY in user and business terms, with no HOW (no framework, library, table or endpoint names). Its success criteria are measurable and technology-agnostic. Check: grep the story and FR files for stack names. Any hit outside a 'Constraints' or plan section fails. | expert-opinion | [ASB/SDD-02], [ASB/SDD-05] | requirements; definition-of-ready; role:business-analyst; role:product-manager |
| **ASB/SDD-P02**: Open questions are explicit inline markers ([NEEDS CLARIFICATION: <question>], or a red example-mapping card), capped at a few per story. The Definition of Ready requires zero open markers. Clarifying questions to the PO are asked one at a time, as multiple choice (2-5 options) or short answers, and only when the answer changes architecture, data model, task breakdown, tests, UX, operations or compliance. Each answer is written back into the spec. | expert-opinion | [ASB/SDD-05], [ASB/SDD-06], [ASB/SDD-21], [ASB/SDD-24] | requirements; definition-of-ready; role:business-analyst; role:product-manager |
| **ASB/SDD-P03**: A story spec has these sections: user stories with priority (P1..Pn); 'Independent Test' for each story, so the story can be built, tested and demoed on its own; Given/When/Then acceptance scenarios; an Edge Cases list; numbered requirements (FR-### '... MUST ...'); Key Entities; success criteria SC-###; and Assumptions. | expert-opinion | [ASB/SDD-02], [ASB/SDD-04] | requirements; definition-of-ready; role:business-analyst |
| **ASB/SDD-P04**: The plan (design doc or ADR) is a separate artifact that links its spec. It records Technical Context, with unknowns marked. It passes a gate against the project constitution/working agreement BEFORE research and again AFTER design. Every deliberate deviation is justified in a 'Violation \| Why needed \| Simpler alternative rejected because' table. Its outputs (research notes, data model, contracts) are listed. | expert-opinion | [ASB/SDD-03], [ASB/SDD-01] | sprint-planning; ddd-guidelines; definition-of-ready; role:principal-engineer |
| **ASB/SDD-P05**: Every task carries an ID, a parallel-safe flag (different files, no dependency), the story it belongs to and the exact file paths. Tasks are grouped by story, with a blocking 'foundational' phase first and a checkpoint at the end of each story. Test tasks come before implementation tasks and must be seen failing. Check: the sprint ticket map gives each ticket its story ID, files touched and parallel/dependency info. | expert-opinion | [ASB/SDD-04], [ASB/SDD-01] | sprint-planning; testing-strategy; role:engineering-manager |
| **ASB/SDD-P06**: Before implementation starts, run a READ-ONLY cross-artifact analysis of requirements, stories/plan and tickets. Report: coverage % (requirements with at least one ticket or test), duplicates, ambiguous terms (fast, robust, ...), terminology drift against the glossary, and untestable acceptance criteria. Severity rules: a constitution/working-agreement MUST violation or an uncovered core requirement is CRITICAL and blocks implementation. A conflict with a principle is fixed in the artifact, never by quietly weakening the principle. | expert-opinion | [ASB/SDD-07], [ASB/SDD-12] | definition-of-ready; sprint-planning; requirements; role:principal-engineer; role:senior-qa-engineer; role:business-analyst |
| **ASB/SDD-P07**: The team constitution (here: the working agreement plus the DoR and DoD) is versioned with semver: MAJOR for a removed or redefined rule, MINOR for a new rule, PATCH for wording. It shows Ratified and Last-Amended dates and has a Governance section naming the amendment procedure and the compliance-review expectation. Each amendment lists the dependent docs (role files, templates) that must be updated with it. *Note: rests partly on unconfirmed source(s) ASB/SDD-09.* | expert-opinion | [ASB/SDD-08], [ASB/SDD-09] (unverified) | working-agreement; definition-of-ready; definition-of-done |
| **ASB/SDD-P08**: Each phase (spec -> plan -> tasks -> implement) is reviewed by a human or a designated reviewer before the next one starts. Implementation does not start while a requirements-quality checklist has unchecked items. A checked box means the requirement quality was confirmed, not that the work is done. | expert-opinion | [ASB/SDD-11], [ASB/SDD-10] | working-agreement; definition-of-ready; sprint-planning |
| **ASB/SDD-P09**: Spec-based review: the reviewer's brief is to check that every requirement and acceptance criterion is implemented and every listed edge case has a test, and to report gaps that affect correctness. Style comments are skipped or clearly marked as non-blocking. The process should NOT require fixing every finding, because a reviewer told to find problems always finds something. | official | [ASB/SDD-24] | working-agreement; definition-of-done; role:principal-engineer; role:senior-qa-engineer |
| **ASB/SDD-P10**: Any rule that must hold every time (merge gates, test immutability, PR size, branch rules) is enforced deterministically by a hook, CI check, deny rule or branch protection. Prose in role files or the working agreement is only guidance. Check: for every MUST in the working agreement and role files, name the script, hook or CI job that enforces it, or mark it explicitly as 'guidance (not enforced)'. | official | [ASB/SDD-24] | working-agreement; ci-cd; definition-of-done; role:engineering-manager; role:sre-devops-engineer |
| **ASB/SDD-P11**: The written spec is the build input and the definition of done. Implementation starts in a fresh agent context that is given the spec file, not a long conversation history. Role files tell implementers to read the ticket spec first and the reviewers to review against it. | official | [ASB/SDD-24], [ASB/SDD-25] | working-agreement; definition-of-done; role:senior-backend-engineer; role:senior-frontend-engineer; role:senior-ml-cv-engineer |
| **ASB/SDD-P12**: Engineer role files require a plan step before editing: read the relevant files, propose a plan, and edit only after approval (plan mode or an equivalent). Broad codebase exploration goes to subagents that return only findings. | official | [ASB/SDD-25], [ASB/SDD-24] | role:senior-backend-engineer; role:senior-frontend-engineer; role:senior-ml-cv-engineer; role:sre-devops-engineer; working-agreement |
| **ASB/SDD-P13**: Track acceptance status in a machine-readable file (JSON): one entry per end-to-end feature or acceptance scenario, with steps and a pass/fail field. Agents may only flip the status, never delete or edit entries. Work goes one feature or ticket at a time, and each session ends with a commit and a progress note. Check against the repo's status.json and goal scorecard. | official | [ASB/SDD-26] | sprint-planning; definition-of-done; testing-strategy; role:engineering-manager |
| **ASB/SDD-P14**: An ADR records ONE decision and has Number, Title, Date, Status, Context, Decision and Consequences (what gets easier or harder, and risks). The set of ADRs is the decision log. Process and other decisions may use the same format ('any decision record'), but significant architecture decisions must stay easy to find among them (for example a type tag or a separate index). | strong-consensus | [ASB/SDD-17], [ASB/SDD-18], [ASB/SDD-19] | working-agreement; definition-of-ready; role:principal-engineer; role:engineering-manager |
| **ASB/SDD-P15**: Stories are discovered before they are formulated. Run a short Three Amigos / example-mapping session (PO = scope, tester = edge cases, developer = feasibility) as late as possible before development: rules as acceptance criteria, examples under each rule, open questions as red cards. If a story needs more than about 25-30 minutes, split it or send it back for research. Gherkin may then be drafted by a developer + tester pair but must be reviewed by the PO or the BA as PO proxy. | strong-consensus | [ASB/SDD-20], [ASB/SDD-21], [ASB/SDD-22], [ASB/SDD-23] | definition-of-ready; sprint-planning; requirements; role:business-analyst; role:senior-qa-engineer; role:product-manager |
| **ASB/SDD-P16**: The spec is a living artifact. Incidents, retro findings and production metrics become new or changed NFRs or acceptance criteria in the requirements files, not only process rules. Check: each retro item that changes product behaviour links an FR/NFR change. | expert-opinion | [ASB/SDD-01], [ASB/SDD-20] | retro; requirements; role:business-analyst |
| **ASB/SDD-P17**: No speculative scope. Every ticket traces to a story with acceptance criteria, and every FR/NFR traces to at least one scenario and test (requirement -> story -> scenario -> test file). Coverage gaps are reported as a number, not left as prose. | expert-opinion | [ASB/SDD-01], [ASB/SDD-07], [ASB/SDD-05] | requirements; definition-of-ready; definition-of-done; role:business-analyst |
| **ASB/SDD-P18**: Where a requirement states a general invariant (for example score rules or deletion/retention guarantees), express it as an executable property (property-based test) as well as Gherkin examples, so generated inputs reach cases the example scenarios miss. | expert-opinion | [ASB/SDD-12] | testing-strategy; role:senior-qa-engineer; role:senior-backend-engineer |

### 5.3 Agile project management, flow and DORA

| Practice | Strength | Sources | Applies to |
|---|---|---|---|
| **ASB/AGL-P01**: Name the three Scrum commitments explicitly and give each one exact home: one Product Goal (stored with the Product Backlog), one Sprint Goal per sprint (in the sprint plan), and the Definition of Done (for the Increment). Check: working-agreement §3 and sprint-planning docs point to where the Product Goal lives, and every sprint-NN.md links to it. Today the PM only 'states the product goal' at planning, and no doc holds it. | official | [ASB/AGL-01] | working-agreement; sprint-planning; requirements; role files (.claude/agents/product-manager.md) |
| **ASB/AGL-P02**: Make the Sprint Goal a single objective that says why the sprint is valuable, defined by the whole team (PO, EM and developers) and finalized before planning ends. A bullet list may sit under it as the measurable scorecard. Counter-idea for the PO: the repo follows the MS playbook's 'concise bullet point list' [ASB/AGL-09], which the Scrum Guide's 'single objective' contradicts. Pick one deliberately and record the choice in an ADR. Check: sprint-NN.md opens with one goal sentence, and goal-scorecard.md rows trace back to it. | official | [ASB/AGL-01], [ASB/AGL-09] | sprint-planning; working-agreement; role files (.claude/agents/engineering-manager.md) |
| **ASB/AGL-P03**: When a ticket misses the DoD by sprint end, it returns to the backlog. It is not reported as done, 'partly done' or demoed at review. Scope may be renegotiated with the PO only without endangering the Sprint Goal, and only the PO cancels a sprint when its goal becomes obsolete. Check: definition-of-done.md and the review/retro docs contain this carry-over rule, and the scorecards never count a non-DoD item. | official | [ASB/AGL-01] | definition-of-done; sprint-planning; retro; working-agreement |
| **ASB/AGL-P04**: Replace the phrase 'Scrum Guide timeboxes are unverified' (working-agreement §3) with the verified figures: sprint at most one month; for a one-month sprint, planning at most 8h, review at most 4h and retro at most 3h; Daily Scrum 15 min, all shorter for shorter sprints. Then state openly that agent-only bursts use their own goal-bounded cadence, a choice MS explicitly allows ('frequent, lightweight planning ... over rigid, fixed-length cadences'). Check: no doc calls these facts unverified, and the agent cadence is labelled as a deliberate deviation. | official | [ASB/AGL-01], [ASB/AGL-11], [ASB/AGL-09] | working-agreement; sprint-planning |
| **ASB/AGL-P05**: Use Scrum accountabilities, not a RACI chart. The Scrum Guide defines exactly three accountabilities (PO, Scrum Master, Developers), with no sub-teams or hierarchies, and the PO stays accountable even when backlog work is delegated (here, to the PM and BA). If the RACI table stays, check that every row has exactly one A, and that the A for backlog ordering and value is the human PO. Counter-idea: a 13-column RACI over 12 agents adds the hierarchy Scrum avoids. Mapping each agent to Developers, PO-delegate or Scrum-Master-delegate may be simpler. Note that the 'exactly one A' rule itself comes from general RACI convention and is unverified here. | expert-opinion | [ASB/AGL-01] | working-agreement; role files (.claude/agents/engineering-manager.md, product-manager.md, business-analyst.md) |
| **ASB/AGL-P06**: Treat the Definition of Ready as a lightweight checklist, not a hard 100% gate. Scrum's only readiness criterion is 'can be Done within one Sprint'. DoR items must apply broadly (conditional items such as UI or security are flagged 'when applicable'). Revise the DoR only when missing information recurrently hurts planning. When top work is not Ready, split it and refine it instead of blocking. Counter-idea: the repo DoR says 'Only a story that meets every item may be pulled' and requires an approved design doc and a coach-verified rule before pull. Per Cohn (unverified), that is a stage-gate that stops concurrent work. Consider letting a design spike or coach verification be a ticket inside the sprint. *Note: rests partly on unconfirmed source(s) ASB/AGL-16.* | strong-consensus | [ASB/AGL-01], [ASB/AGL-08], [ASB/AGL-12], [ASB/AGL-16] (unverified) | definition-of-ready; sprint-planning; role files (.claude/agents/business-analyst.md, engineering-manager.md) |
| **ASB/AGL-P07**: Cite INVEST from DORA's working-in-small-batches page, which defines Independent, Negotiable, Valuable, Estimable, Small ('hours to a couple days') and Testable. Add an INVEST check to the DoR. Check: definition-of-ready.md no longer says 'INVEST is unverified', and every story is checked against all six letters. | official | [ASB/AGL-04] | definition-of-ready; requirements; role files (.claude/agents/business-analyst.md) |
| **ASB/AGL-P08**: Split work into vertical, end-to-end slices of hours to a couple of days, never more than a week, starting at the service/API layer and using dark launch or toggles. Do not regroup slices before test or release. Check: the plan's ticket map shows each ticket as a thin slice with its own end-to-end verification and its own PR, with no 'integration ticket' that batches them. Story-splitting patterns (SPIDR; Humanizing Work's workflow steps, CRUD operations and rule variations) are useful heuristics but unverified in this session, so cite them as (judgment) until fetched. *Note: rests partly on unconfirmed source(s) ASB/AGL-17, ASB/AGL-18.* | official | [ASB/AGL-04], [ASB/AGL-17] (unverified), [ASB/AGL-18] (unverified) | sprint-planning; definition-of-ready; requirements; role files (.claude/agents/business-analyst.md, engineering-manager.md) |
| **ASB/AGL-P09**: Developers own sizing and how a story is decomposed into tasks. The PO influences trade-offs but does not size. Use relative sizes (t-shirt or 'fits in one sprint?'), never convert sizes to days, and track planned against actual. Base planning on past performance, upcoming capacity and the DoD. Check: the EM role file does not size on behalf of the implementing engineers, and the retro template's 'accuracy of size estimates' row is filled. | official | [ASB/AGL-01], [ASB/AGL-09] | sprint-planning; retro; role files (.claude/agents/engineering-manager.md, senior-backend-engineer.md, senior-frontend-engineer.md, senior-ml-cv-engineer.md) |
| **ASB/AGL-P10**: For agent-only teams, plan capacity in parallel agents and file ownership, not hours. Run about 3-5 concurrent implementers and about 5-6 self-contained tasks each, with no two in-flight tickets editing the same file, and declare dependencies between tasks. Use a single session or subagents for sequential or same-file work. Check: the sprint plan shows a lane-by-file ownership map and a dependency list. The existing rule that ticket PRs must not touch the shared decision-log/status/progress files matches this guidance. | official | [ASB/AGL-13], [ASB/AGL-14] | sprint-planning; working-agreement; role files (.claude/agents/engineering-manager.md) |
| **ASB/AGL-P11**: Every delegated agent brief states an objective, an output format, the tools and sources to use, and clear task boundaries, plus all task-specific context, because teammates do not inherit the lead's conversation. Scale the number of agents to the complexity of the task. Check: each role file and each EM ticket brief has these four fields. | official | [ASB/AGL-13], [ASB/AGL-14] | role files (all roles); working-agreement; sprint-planning |
| **ASB/AGL-P12**: Limit work in process. Each agent works on one feature or ticket at a time, and the team sets a WIP limit per stage (e.g. 'in review', 'awaiting QA') sized to reviewer and QA capacity. When work is waiting, fix the bottleneck instead of starting more. Check: the working agreement states WIP limits per column, and the progress or status files show how long each ticket has waited in each stage. | official | [ASB/AGL-06], [ASB/AGL-15] | working-agreement; sprint-planning; role files (all implementer roles) |
| **ASB/AGL-P13**: Update the metrics to DORA's current five: change lead time, deployment frequency, failed deployment recovery time, change fail rate and deployment rework rate. Retire 'time to restore service' and MTTR. Report them per service, never as targets or for comparing agents. Check: the retro template's §2 rows and definition-of-done's sprint-level 'DORA metrics' item use the five names and the current definitions. The template still lists the four keys with 'Time to restore service'. | official | [ASB/AGL-02], [ASB/AGL-03] | retro; definition-of-done; ci-cd; working-agreement |
| **ASB/AGL-P14**: Add flow measures alongside DORA: mean lead time and its variability across the whole value stream, time spent waiting in review and QA, and the age of in-flight items. Use them as leading indicators chosen in the retro (e.g. 'how long code reviews take'). Check: the retro facts table has a review-wait and a QA-wait row. The Kanban Guide's metric set (WIP, throughput, work item age, cycle time) is unverified here, so cite DORA instead until it is fetched. *Note: rests partly on unconfirmed source(s) ASB/AGL-19.* | official | [ASB/AGL-02], [ASB/AGL-06], [ASB/AGL-19] (unverified) | retro; working-agreement; ci-cd |
| **ASB/AGL-P15**: Base the review gate on risk. DORA finds that heavyweight or external approval gives no lower change fail rate and slows delivery, and names 'treating all changes equally' as a pitfall. Segregation of duties is met by peer review in the platform plus automated tests and CI. Counter-idea for the PO: today every PR, docs-only ones included, needs a principal engineer, a senior engineer, the QA gate and a gated merge. Consider a lighter tier for docs-only or low-risk changes (one reviewer plus CI) and the full chain for code that touches domain, security or data. Check: the working agreement defines review tiers by risk, with criteria. | official | [ASB/AGL-05] | working-agreement; definition-of-done; ci-cd; role files (.claude/agents/principal-engineer.md, senior-qa-engineer.md) |
| **ASB/AGL-P16**: Keep each change small. Machine-generated code can cost more review effort per line, so AI-heavy teams should weight small batches even more. Check: the PR size rule (about 100, at most 400 production lines) stays, and any waiver is logged before the PR, not after. | official | [ASB/AGL-04] | working-agreement; definition-of-done; ci-cd |
| **ASB/AGL-P17**: Run the retrospective in phases, with data before opinions: gather data, generate insights (5 Whys, Fishbone), then decide. Inspect processes, tools, interactions and the DoD itself. Each action item has one owner and a due date (default: next retro) and goes into the backlog, and the most impactful item goes into the next sprint's backlog. The facilitator reviews the previous actions first. Check: the retro template has these sections, and the next sprint plan contains at least one retro-action ticket. The full five-stage Derby and Larsen sequence is unverified (only Gather Data and Generate Insights are verified via MS), so cite the book via ASB/AGL-09 only for those two. *Note: rests partly on unconfirmed source(s) ASB/AGL-20.* | official | [ASB/AGL-01], [ASB/AGL-09], [ASB/AGL-10], [ASB/AGL-20] (unverified) | retro; sprint-planning; role files (.claude/agents/engineering-manager.md) |
| **ASB/AGL-P18**: Retros and incident write-ups are blameless: failures lead to inquiry about the system (prompts, process, tooling), not blame on an agent. Check: the retro template's 'Root cause' column refers to system causes, and the blameless rule cites DORA instead of '(judgment)'. | official | [ASB/AGL-07] | retro; working-agreement |
| **ASB/AGL-P19**: The Sprint Review is a working session with the PO and stakeholders. It inspects the outcome against the Product Goal and adapts the backlog, and it is not a release gate, since Increments may ship before it. Agents demo the live system end to end, as a user would, and not only unit-test output. Check: the review section of the working agreement says it adapts the backlog, and the scorecard is measured live. | official | [ASB/AGL-01], [ASB/AGL-15] | working-agreement; sprint-planning; definition-of-done; testing-strategy |
| **ASB/AGL-P20**: Guard against premature 'done' claims by agents. Keep a machine-readable feature or ticket list where an agent may only flip a pass/fail field after testing, require end-to-end verification, and end each session with a commit and a progress note. Check: status.json is edited only through a defined field, and the DoD requires end-to-end evidence. | official | [ASB/AGL-15] | definition-of-done; testing-strategy; working-agreement; role files (.claude/agents/senior-qa-engineer.md) |
| **ASB/AGL-P21**: The working agreement is the team's own living document, stored in the repo, with a rhythm table (activity, when, duration, who, accountable, goal) and a named process lead who owns follow-up of action items. New tasks outside a story's acceptance criteria go back to the PM or PO, as a guard against scope creep. Check: working-agreement.md has a rhythm table, and the scope-change rule is stated. | official | [ASB/AGL-10], [ASB/AGL-11] | working-agreement; role files (.claude/agents/engineering-manager.md) |
| **ASB/AGL-P22**: Refine the backlog continuously, not only at planning. Design for stories that need it happens before they enter a sprint, and technical-debt paydown is planned explicitly. Check: the plan names refinement owners and a debt line, and the stories pulled in that need design link to an approved design. | official | [ASB/AGL-01], [ASB/AGL-12] | sprint-planning; definition-of-ready; requirements |

### 5.4 Requirements down to atomic level

| Practice | Strength | Sources | Applies to |
|---|---|---|---|
| **ASB/RE-01**: One requirement per statement. Each FR has its own ID, one subject, one modal verb (MUST/shall) and one observable response. A description that joins obligations with 'and', or has more than one sentence of obligations, is split into separate IDs (FR-011 -> FR-011a/b/c). Check: no FR description holds more than one 'MUST/shall/can' clause. *Note: rests partly on unconfirmed source(s) ASB/REQ-23, ASB/REQ-30.* | strong-consensus | [ASB/REQ-07], [ASB/REQ-15], [ASB/REQ-23] (unverified), [ASB/REQ-30] (unverified) | requirements; role file: business-analyst; definition-of-ready |
| **ASB/RE-02**: Write each FR statement in an EARS pattern: Ubiquitous 'The <system> shall <response>'; State 'While <state>, ...'; Event 'When <trigger>, ...'; Optional 'Where <feature>, ...'; Unwanted 'If <trigger>, then the <system> shall ...'; Complex 'While <state>, when <trigger>, ...'. Each 'If ... then' (unwanted behaviour) clause becomes the negative scenario. Check: every FR starts with one of these keyword frames or is labelled ubiquitous. *Note: rests partly on unconfirmed source(s) ASB/REQ-22.* | expert-opinion | [ASB/REQ-15], [ASB/REQ-22] (unverified) | requirements; role file: business-analyst |
| **ASB/RE-03**: Mark open ambiguity inline as '[NEEDS CLARIFICATION: <question>]' and record every defaulted choice in an 'Assumptions' list on the story. A story with any open marker on scope, security/privacy or a domain rule is not Ready. Check: grep the story for NEEDS CLARIFICATION, and confirm the story has an Assumptions section. | strong-consensus | [ASB/REQ-07], [ASB/REQ-08], [ASB/REQ-10] | definition-of-ready; requirements; role file: business-analyst |
| **ASB/RE-04**: Each atomic requirement becomes one Gherkin 'Rule:', and each Rule has at least one concrete Example plus one negative or edge Example. Each Example has 3-5 steps; Given has no user interaction; Then asserts an output the user or an external system can see, never a database row; the wording passes the test 'would this change if the implementation changed?'. Check: count Rules per FR (>= 1), count Examples per Rule (>= 2, one negative), lint for UI verbs (click/type/press) and DB words in Then. | official | [ASB/REQ-01], [ASB/REQ-02] | requirements; definition-of-ready; testing-strategy; role file: business-analyst; role file: senior-qa-engineer |
| **ASB/RE-05**: Run an Example Mapping session (yellow story, blue rules, green examples, red questions) for each story before it is marked Ready. Attend with at least the Three Amigos roles (PO or product-manager for scope, an engineer, senior-qa-engineer for edge cases), and hold it as late as possible before development. Timebox it to about 25-30 minutes; if it overruns, split the story or send it back for research. Red cards go to open-questions.md. New stories found are sliced out and deferred. Check: the story file links its example map, and blue cards map 1:1 to Rules. *Note: rests partly on unconfirmed source(s) ASB/REQ-26.* | official | [ASB/REQ-03], [ASB/REQ-04], [ASB/REQ-05], [ASB/REQ-26] (unverified) | sprint-planning; definition-of-ready; working-agreement; role file: business-analyst; role file: senior-qa-engineer; role file: product-manager |
| **ASB/RE-06**: Each NFR row names exactly one ISO/IEC 25010 characteristic or sub-characteristic, one metric with a unit (Scale), how it is measured including tool, load and client profile (Meter), the target (Goal), the failure threshold if different (Fail/Tolerable), and a baseline if known (Past). Rows with (a)/(b)/(c) sub-targets are split into separate IDs. Check: every NFR row has non-empty Scale, Meter and Goal columns and no '(a)'. *Note: rests partly on unconfirmed source(s) ASB/REQ-27.* | expert-opinion | [ASB/REQ-13], [ASB/REQ-14], [ASB/REQ-27] (unverified), [ASB/REQ-09] | requirements; role file: business-analyst; role file: principal-engineer; testing-strategy |
| **ASB/RE-07**: State runtime reliability and latency NFRs as an SLI and an SLO. SLI = good events / valid events, measured at a named point (load balancer, server or client). SLO = target % over a stated window (e.g. 99.9% over one month). Keep SLIs and SLOs in the requirements register, not only in ops docs. Lab or performance-test NFRs instead state the sample size per run. Check: every NFR with a percentile or availability target names a measurement point and a window or sample size. *Note: rests partly on unconfirmed source(s) ASB/REQ-25.* | official | [ASB/REQ-12], [ASB/REQ-25] (unverified) | requirements; role file: sre-devops-engineer; definition-of-done; ci-cd |
| **ASB/RE-08**: Lint requirements for vague words before Ready. Words such as fast, quickly, scalable, secure, intuitive, robust, user-friendly, appropriate, 'etc.' are flagged unless a metric sits beside them. Also flag requirements whose verb has no object or no measurable outcome. An ambiguous security or performance attribute, or an untestable criterion, is HIGH severity and blocks Ready. Check: run a word-list grep over FR/NFR registers and story files; zero unresolved HIGH flags. | strong-consensus | [ASB/REQ-09], [ASB/REQ-10] | definition-of-ready; requirements; role file: business-analyst; role file: senior-qa-engineer |
| **ASB/RE-09**: Keep traceability both ways and make it machine-checkable. Every FR/NFR maps to at least one story and one test, and every story and test maps back to a requirement. Test paths are full repo paths. A script reports coverage %, unmapped requirements and orphan tests, and runs in CI or at least at sprint review. Check: run the script; 0 broken paths; coverage % stated in the sprint report. | strong-consensus | [ASB/REQ-09], [ASB/REQ-08] | requirements; definition-of-done; ci-cd; role file: business-analyst |
| **ASB/RE-10**: Keep acceptance criteria (AC) and the DoD separate. AC are specific to one story and live in the story as Gherkin Rules and Examples. The DoD is a generic checklist that applies to every story, and 'all AC pass as executable tests' is one item in it. Story-specific items never enter the DoD or DoR; conditional items are explicitly marked '(when applicable)' with a trigger. Check: every DoD/DoR item either applies broadly or names its trigger condition. | strong-consensus | [ASB/REQ-16], [ASB/REQ-17], [ASB/REQ-18] | definition-of-done; definition-of-ready; working-agreement |
| **ASB/RE-11**: Each story is a vertical slice that can be tested on its own, with a priority and an 'Independent Test:' line saying how it alone shows value. A story that cannot be tested alone is split. Check: every story file has a priority and an 'Independent Test' line. *Note: rests partly on unconfirmed source(s) ASB/REQ-29.* | strong-consensus | [ASB/REQ-07], [ASB/REQ-29] (unverified) | definition-of-ready; sprint-planning; role file: business-analyst; role file: engineering-manager |
| **ASB/RE-12**: For agent teams, keep a machine-readable list of each sprint's acceptance items (JSON, one entry per atomic requirement or scenario, all starting 'passes': false). Agents may only flip the status field after end-to-end verification as a user would do it, never by editing or deleting items. Agents work on one item at a time. Check: the sprint JSON exists; git history shows only status-field changes after creation, except by the BA or QA. | official | [ASB/REQ-21] | working-agreement; definition-of-done; role file: senior-qa-engineer; role file: engineering-manager |
| **ASB/RE-13**: Write specs by interview: the BA, or Claude for the PO, asks multiple-choice questions until scope, edge cases and out-of-scope items are pinned down. Then implement from the written spec in a fresh context. A reviewer subagent compares the diff against the spec and checks that every requirement is implemented and every listed edge case has a test. Check: the PR review records a requirement-by-requirement checklist against the story spec. | official | [ASB/REQ-20] | working-agreement; role file: principal-engineer; role file: senior-qa-engineer; role file: business-analyst |
| **ASB/RE-14**: Plan releases with a user story map: a backbone of user activities left to right, stories under each activity in priority order, and horizontal release slices (walking skeleton first). Each sprint goal names the slice it completes. Check: the roadmap or sprint plan references map slices. *Note: rests partly on unconfirmed source(s) ASB/REQ-28.* | expert-opinion | [ASB/REQ-28] (unverified) | sprint-planning; requirements; role file: product-manager |
| **ASB/PROC-FR**: Procedure to break an FR into atomic, tested requirements. (1) Write the story with value statement, priority and Independent Test [RE-11]. (2) Example Mapping: blue card = each business rule, green = examples, red = questions [RE-05]. (3) Rewrite each blue card as one EARS statement with its own ID (FR-nnn.k), one response per statement [RE-01, RE-02]; add an 'If ... then' statement for each unwanted case. (4) Lint for vague words and NEEDS CLARIFICATION; red cards block Ready [RE-03, RE-08]. (5) Write each statement as a Gherkin 'Rule:' with at least one happy and one negative Example, 3-5 declarative steps, Then on observable output [RE-04]. (6) Assign test levels: Example -> scenario test; boundary it crosses -> integration test; each invariant or branch inside the rule -> unit test, written first and seen failing. (7) Add rows to the traceability matrix with full paths: FR-nnn.k -> story -> Rule -> scenario -> test files [RE-09]. (8) Add an entry to the sprint acceptance JSON as failing [RE-12]. Worked example (FR-011): FR-011.1 'When the owner signs out, the client shall delete authenticated data from local storage, session storage and IndexedDB.'; FR-011.2 'When the owner signs out, the client shall delete every Cache Storage entry holding authenticated data.'; FR-011.3 'The service worker shall not cache media responses.'; FR-011.4 'If sign-out fails at the server, then the client shall still delete local authenticated data and show <message>.' [NEEDS CLARIFICATION: message]. Each becomes a Rule with Examples. FR-011.3 is unit plus integration tested (SW fetch handler); FR-011.1/2 are E2E tested (Playwright, offline reopen). | expert-opinion | [ASB/REQ-01], [ASB/REQ-02], [ASB/REQ-03], [ASB/REQ-07], [ASB/REQ-09], [ASB/REQ-15], [ASB/REQ-21] | requirements; definition-of-ready; sprint-planning; testing-strategy; role file: business-analyst; role file: senior-qa-engineer |
| **ASB/PROC-NFR**: Procedure to break an NFR into atomic, tested requirements. (1) Classify it under one ISO/IEC 25010:2023 characteristic or sub-characteristic (e.g. Performance efficiency > Time behaviour) [RE-06]. (2) Replace every adjective with a Scale (unit) and a Meter (tool, load, client profile, measurement point) [RE-06, RE-08]. (3) Set Goal (target), Fail/Tolerable (gate threshold) and Past (baseline or 'none: judgment'). (4) For runtime properties write the SLI as good/valid events and the SLO with a window; for lab properties state samples per run [RE-07]. (5) Split each sub-target into its own ID: NFR-012 (a) and (b) -> NFR-012.1 'p95 tap->updated score <= 200 ms on reference profile, >= 200 samples per run' and NFR-012.2 'p95 tap->visual feedback <= 100 ms ...'. (6) Choose the verifying test level and the CI or nightly job that runs it, and the release it gates. (7) Write one Gherkin 'Rule:' per NFR where it can be observed (e.g. 'Rule: correction is confirmed within 1.5 s at p95'), backed by a performance or E2E test that fails when the threshold is broken; add a negative test that injects delay and asserts the gate turns red. (8) Add traceability rows and the sprint-JSON entry [RE-09, RE-12]. *Note: rests partly on unconfirmed source(s) ASB/REQ-27.* | expert-opinion | [ASB/REQ-12], [ASB/REQ-13], [ASB/REQ-14], [ASB/REQ-19], [ASB/REQ-27] (unverified), [ASB/REQ-09] | requirements; testing-strategy; ci-cd; role file: business-analyst; role file: sre-devops-engineer; role file: principal-engineer |

### 5.5 Product roles: PM, BA, designer, EM, domain coach

| Practice | Strength | Sources | Applies to |
|---|---|---|---|
| **ASB/PM-1**: The product-manager role file requires one product or milestone goal plus a sprint goal written as a short bullet list of outcomes. Each committed story names the goal bullet it serves, and the sprint review answers 'was the goal achieved? if not, why?'. Check the doc: every story row in sprint-NN.md maps to a goal bullet, and the retro or review records the yes/no per bullet. *Note: rests partly on unconfirmed source(s) ASB/RPD-20.* | strong-consensus | [ASB/RPD-12], [ASB/RPD-20] (unverified) | role:product-manager; sprint-planning; retro |
| **ASB/PM-2**: Before an epic is committed, the PM records its four product risks (value, usability, feasibility, viability), the evidence for each and the role that owns the test. Any risk without evidence becomes a discovery task, not a build story. Check: each epic in backlog.md has a 4-row risk table. Caveat: the SVPG source could not be fetched, so cite this as (judgment) until it is verified. *Note: rests partly on unconfirmed source(s) ASB/RPD-21.* | expert-opinion | [ASB/RPD-21] (unverified) | role:product-manager; requirements; definition-of-ready |
| **ASB/PM-3**: Link outcome to opportunity to solution to assumption test for each milestone (an opportunity solution tree), and state which assumptions need a real-user touchpoint. Because agents have no access to customers, every such assumption must appear as a human-only 'waiting on P-n' item (PO decision P12) and never as validated. Check: the backlog shows the tree, and no assumption is marked validated without human evidence. Source unverified, so mark (judgment). *Note: rests partly on unconfirmed source(s) ASB/RPD-22.* | expert-opinion | [ASB/RPD-22] (unverified) | role:product-manager; requirements; sprint-planning |
| **ASB/PM-4**: In Three Amigos / Example Mapping, the PM (product owner proxy) is the one who decides whether an edge case the tester raises is in or out of scope. Out-of-scope cards become new or deferred stories. Check: each story records scope decisions with the decider named, and deferred stories exist in the backlog. | strong-consensus | [ASB/RPD-17], [ASB/RPD-16] | role:product-manager; role:business-analyst; definition-of-ready |
| **ASB/PM-5**: Anti-patterns to name in the PM file: output metrics (stories or points closed) used as the success measure instead of goal outcomes; changing priorities inside a sprint without going through the PO; AI-drafted plans or acceptance criteria accepted without collaborative validation. | strong-consensus | [ASB/RPD-12] | role:product-manager; working-agreement |
| **ASB/BA-1**: Run Example Mapping on every story before it is pulled into a sprint, producing the story, its rules (= acceptance criteria), examples per rule (= future Gherkin scenarios), open questions or assumptions, and deferred stories. A story with any unresolved question card is not Ready. Check: each story file has a rules/examples/questions section, and the DoR has an item 'no open question cards'. | strong-consensus | [ASB/RPD-16], [ASB/RPD-13] | role:business-analyst; definition-of-ready; requirements |
| **ASB/BA-2**: Gherkin is discovered together by PO/PM, tester (senior-qa-engineer) and developer (Three Amigos). Once the style is settled, a dev+QA pair may write it, but the PO or business representative must actively review it. Check: each story or PR records the three perspectives, and a PM/PO review note exists on the scenarios. | strong-consensus | [ASB/RPD-17] | role:business-analyst; role:senior-qa-engineer; working-agreement; testing-strategy |
| **ASB/BA-3**: Gherkin quality rules that can be checked mechanically: each scenario title is a single sentence; each Given/When/Then line describes one thing (no 'and' joining two actions); identical meanings use identical step text across features (a shared step vocabulary that matches the ubiquitous language). The existing BA file already has declarative, 3-5 steps, Scenario Outline and Rule:, and these rules can be added next to them. | strong-consensus | [ASB/RPD-17] | role:business-analyst; testing-strategy; ddd-guidelines |
| **ASB/BA-4**: The DoR checklist holds only broadly applicable items: input values specified; clear, complete and measurable acceptance criteria; business need or goal link stated; small enough but valuable; not blocked (if blocked, split so the unblocked part can proceed). Update the DoR when missing information recurrently hurts planning. Do not add story-specific items (story-specific rules belong in the story, e.g. ADR 0009 split logic belongs in rules stories, not the generic DoR). | strong-consensus | [ASB/RPD-13], [ASB/RPD-14] | definition-of-ready; role:business-analyst; role:engineering-manager |
| **ASB/BA-5**: Do not cite BABOK knowledge areas or techniques in the BA role file as a verified basis, because the IIBA source was unfetchable. If BABOK framing is wanted (e.g. requirements life cycle management = the traceability matrix), label it (judgment) or obtain the guide from the PO. *Note: rests partly on unconfirmed source(s) ASB/RPD-23.* | expert-opinion | [ASB/RPD-23] (unverified) | role:business-analyst |
| **ASB/PD-1**: The designer's WCAG 2.2 AA checklist must cover ALL Level A and AA success criteria, because AA conformance requires both. Today the role lists only target size, contrast, dragging, accessible authentication, focus-not-obscured and captions. It omits two NEW 2.2 Level-A criteria: 3.2.6 Consistent Help (help mechanisms in the same relative order across pages) and 3.3.7 Redundant Entry (auto-populate or offer selection of data already entered in the same process, which matters for the multi-page match-setup flow). Check: the checklist in docs/design/* and the role file name both. | official | [ASB/RPD-05], [ASB/RPD-06], [ASB/RPD-07], [ASB/RPD-08] | role:principal-designer; role:senior-frontend-engineer; definition-of-done; testing-strategy |
| **ASB/PD-2**: Claim conformance per full page and per complete process: a multi-step flow (upload, match setup one-question-per-page, calibration) conforms only if every page in it conforms. Design specs and QA evidence must list every page of the process, not a sample. | official | [ASB/RPD-08] | role:principal-designer; role:senior-qa-engineer; testing-strategy |
| **ASB/PD-3**: Do not test for or cite SC 4.1.1 Parsing. It is removed in WCAG 2.2, and its issues are covered by 1.3.1 Info and Relationships and 4.1.2 Name, Role, Value. Check: no checklist row or test references 4.1.1. | official | [ASB/RPD-09] | role:principal-designer; testing-strategy |
| **ASB/PD-4**: Accessibility verification combines automated tooling (e.g. axe-core) with manual checks (keyboard path, screen reader, colour simulation). The DoD for UI stories requires evidence of both. Automated green alone is not 'WCAG 2.2 AA met'. | strong-consensus | [ASB/RPD-10] | role:principal-designer; definition-of-done; testing-strategy; ci-cd |
| **ASB/PD-5**: Hold design reviews before implementation, with multiple solution options. The domain expert/SME takes part when needed, and the reviewer set is wider than the same 2 agents every time. If there is no consensus, the story owner decides and the team disagrees and commits. Track cost of change (was the change found before or after implementation?) as a retro input. | strong-consensus | [ASB/RPD-11], [ASB/RPD-14] | role:principal-designer; role:pickleball-domain-coach; working-agreement; retro |
| **ASB/PD-6**: Keep the HAX G1-G18 checklist for automatic calls and AI recommendations, but cite it as DPA/DESIGN-11, verified 2026-10-03 and not re-verified 2026-10-31 (microsoft.com is blocked). Do not add HAX claims beyond what DPA recorded. *Note: rests partly on unconfirmed source(s) ASB/RPD-24.* | expert-opinion | [ASB/RPD-24] (unverified) | role:principal-designer; role:product-manager |
| **ASB/EM-1**: Every delegation brief names the objective, output format, tools and sources, and clear boundaries (plus the done-check), so agents do not duplicate work or leave gaps. Check: each task row in the sprint plan has those fields. The current EM file already does this, so keep it. | official | [ASB/RPD-02] | role:engineering-manager; sprint-planning; working-agreement |
| **ASB/EM-2**: Use the simplest orchestration that meets the goal, add complexity only when evidence shows it is needed, and gate each agent step on environment ground truth (command output, CI result) with human checkpoints at blockers. | official | [ASB/RPD-03] | role:engineering-manager; working-agreement; ci-cd |
| **ASB/EM-3**: Retro actions go into the backlog with an owner, a priority and a date (default: the next retro), and the next retro checks them first. For a retro after a difficult period, or one that examines the process the EM owns, use a neutral facilitator (a different agent, or the main session) rather than the EM alone. Check: the retro template has an owner/date/backlog-link per action and names the facilitator. | strong-consensus | [ASB/RPD-12] | role:engineering-manager; retro |
| **ASB/EM-4**: Make the EM file state explicitly that it holds the process-lead (Scrum Master) accountability: facilitating, removing impediments, coaching the team on the DoR and DoD. Keep that separate from being the task router. Whether the precise Scrum Guide accountability wording fits could not be verified, so cite it as (judgment) until scrumguides.org is reachable. *Note: rests partly on unconfirmed source(s) ASB/RPD-20.* | expert-opinion | [ASB/RPD-15], [ASB/RPD-20] (unverified) | role:engineering-manager; working-agreement |
| **ASB/EM-5**: Role-file hygiene: one focused job per subagent; a short, routing-specific description (combined budget 15k tokens); tools on least privilege; instructions that explain why. Process rules learned in retros (ADR 0030/0033/0037/0047 bullets) belong in working-agreement.md or the DoD with a pointer from the role file. They should not pile up as one long responsibilities list. Check: EM file word count (currently 1176 words, about 2x any other product-role file) and duplicated rules between the role file and the process docs. | expert-opinion | [ASB/RPD-01], [ASB/RPD-04] | role:engineering-manager; role:product-manager; role:business-analyst; role:principal-designer; role:pickleball-domain-coach; working-agreement |
| **ASB/DC-1**: The domain coach takes part in continuous, collaborative domain discovery (EventStorming, Example Mapping or Domain Storytelling) together with builders, testers and product people, not only in after-the-fact verification. Check: the coach's responsibilities include attending the Example Mapping or EventStorming session for each rules or coaching story, and the session output is linked from the story. | strong-consensus | [ASB/RPD-19], [ASB/RPD-17] | role:pickleball-domain-coach; ddd-guidelines; definition-of-ready |
| **ASB/DC-2**: In modelling sessions the coach is the domain expert and someone else is the dedicated neutral facilitator (e.g. BA or EM) who cuts discussions short and records HotSpots. Each unverified rule, terminology conflict or dissent becomes a HotSpot that is tracked to resolution, which maps onto the repo's 'needs-verification' items. | strong-consensus | [ASB/RPD-18] | role:pickleball-domain-coach; role:business-analyst; role:engineering-manager; ddd-guidelines |
| **ASB/DC-3**: Domain events are named in the past tense in the ubiquitous language reviewed by the coach (e.g. 'Rally Ended', 'Side Out Declared'). With non-technical stakeholders, use 'constraint' rather than 'aggregate'. Check: the ddd-guidelines glossary and event names follow past tense, and the coach signs off on terms. | strong-consensus | [ASB/RPD-18] | role:pickleball-domain-coach; ddd-guidelines |
| **ASB/DC-4**: A domain rule counts as verified only with edition, rule number and exact wording from an authoritative document that was obtained first-hand. Background knowledge is never verification. This is the repo's own existing standard, and no fetched external source states it, so mark it (judgment). The role file should POINT to docs/domain/rules-verified.md for current status rather than restating a dated status line ('As of 2026-10-03 NO pickleball rule ... is verified'), which goes stale. | expert-opinion |  | role:pickleball-domain-coach; requirements; definition-of-ready |

### 5.6 Engineering roles: PE, backend, frontend, ML/CV, QA, security, SRE

| Practice | Strength | Sources | Applies to |
|---|---|---|---|
| **ASB/PE-1**: Every significant decision is an ADR with Title, Status (proposed/accepted/rejected/deprecated/superseded), Context, Decision and Consequences ('what becomes easier or harder'), plus the options considered. Superseded ADRs are marked, not deleted. Check: every ADR in docs/adr has all five fields, and the role file requires them. | strong-consensus | [ASB/REN-14], [ASB/REN-15] | role files: principal-engineer; working-agreement |
| **ASB/PE-2**: Design review happens BEFORE implementation for cross-cutting or bounded-context changes. Record time-to-decision and who took part (not the same 2 reviewers every time). If there is no consensus, the person with most context decides (disagree and commit) and the decision is logged. | expert-opinion | [ASB/REN-15] | role files: principal-engineer; definition-of-ready; sprint-planning |
| **ASB/PE-3**: Code review standard: approve once the PR definitely improves code health, even if it is not perfect. Technical facts outrank opinion. Optional polish is prefixed 'Nit:' and never blocks. Review in the order design, functionality, complexity/over-engineering, tests ('would the test fail if the code broke?'), naming, docs. Respond within one business day. Do not accept 'clean up later' without a filed ticket. | official | [ASB/REN-11], [ASB/REN-12], [ASB/REN-13] | role files: principal-engineer; role files: senior-backend-engineer; role files: senior-frontend-engineer; working-agreement; definition-of-done |
| **ASB/PE-4**: COUNTER-IDEA to the current rule: DORA names 'an overly heavy code-review process' needing multiple approvals, and asynchronous review, as trunk-based-development pitfalls. The working agreement should state why PE + senior + QA approval is still worth it here (agent reviewers are cheap) and track review latency or PR age so the gate does not create long-lived branches. | official | [ASB/REN-01], [ASB/REN-10] | working-agreement; ci-cd; retro; role files: principal-engineer |
| **ASB/BE-1**: TDD per Canon TDD: write a test list of scenarios first, turn exactly one into a runnable failing test, make it and all previous tests pass, refactor, and add newly discovered cases to the list. The role file should require the test list to be visible in the PR or decision file. (The Kent Beck source was not fetched; DORA confirms high performers practise TDD with less than 10-minute feedback.) *Note: rests partly on unconfirmed source(s) ASB/REN-18.* | strong-consensus | [ASB/REN-18] (unverified), [ASB/REN-03] | role files: senior-backend-engineer; testing-strategy; definition-of-done |
| **ASB/BE-2**: FastAPI tests use TestClient with pytest. External or paid dependencies (auth provider, object store when not under test) are swapped with app.dependency_overrides and reset after each test, never with monkeypatching inside domain code. Integration tests still hit real Postgres or the object store via the dev scripts. | official | [ASB/REN-16] | role files: senior-backend-engineer; testing-strategy |
| **ASB/BE-3**: Every new or changed endpoint is checked against OWASP API Top 10 2023, at minimum API1 BOLA (object-level authz test with another user's id), API3 property-level authz (no mass assignment or over-exposure), API4 resource limits (size, rate, pagination) and API5 function-level authz. A negative test for each applicable item is part of the PR. | official | [ASB/REN-17] | role files: senior-backend-engineer; role files: senior-qa-engineer; definition-of-done |
| **ASB/BE-4**: DDD: domain layer free of framework imports, aggregates enforce invariants, ubiquitous language matches the glossary. Use the repo's existing ddd-crew sources (ENG-11..14) as the citation, because the Evans and Vernon primary texts could not be verified here. *Note: rests partly on unconfirmed source(s) ASB/REN-40.* | strong-consensus | [ASB/REN-40] (unverified) | role files: senior-backend-engineer; ddd-guidelines |
| **ASB/FE-1**: Component tests query by role and accessible name (getByRole, then label/text). getByTestId is a last resort and needs a justification in review. Tests assert user-visible behaviour on DOM nodes, not component internals. A test that cannot find an element by role is treated as a possible accessibility bug. | official | [ASB/REN-19], [ASB/REN-20] | role files: senior-frontend-engineer; testing-strategy; role files: senior-qa-engineer |
| **ASB/FE-2**: Async Server Components are covered by E2E (Playwright) rather than unit tests, per Next.js guidance. Unit, component and integration tests cover client components, hooks and pure functions. | official | [ASB/REN-21] | role files: senior-frontend-engineer; testing-strategy |
| **ASB/FE-3**: Performance budget in CI: set quantity budgets (JS bundle KB per route) and user-centric timings (LCP 2.5 s or less, CLS 0.1 or less at p75, plus the current interaction metric INP, which needs confirming against live web.dev). Fail the build when a budget regresses. Treat Lighthouse as a lab check and pair it with field data (useReportWebVitals). Do not cite FID: the archived web.dev source still uses it and it is superseded. | official | [ASB/REN-24], [ASB/REN-22] | role files: senior-frontend-engineer; ci-cd; requirements |
| **ASB/FE-4**: Production checklist items are reviewable: 'use client' boundaries kept minimal, eslint-plugin-jsx-a11y in lint, authn/authz checked inside each Server Action or route handler (not only in layout or middleware), CSP set. Components are pure, and no useEffect is used for data transformation. | official | [ASB/REN-22], [ASB/REN-23] | role files: senior-frontend-engineer; definition-of-done |
| **ASB/ML-1**: Score the pipeline against the ML Test Score rubric's four areas (data and features, model development, ML infrastructure, monitoring) and report the MINIMUM area score as readiness. Each sprint names which rubric tests were added. (The paper itself was not fetched; confirm against the PDF before citing test numbers.) *Note: rests partly on unconfirmed source(s) ASB/REN-35.* | expert-opinion | [ASB/REN-35] (unverified) | role files: senior-ml-cv-engineer; definition-of-done; sprint-planning |
| **ASB/ML-2**: Every shipped model or detector version has a model card in docs/ with: model details, intended and out-of-scope uses, bias/risks/limitations (e.g. lighting, camera angle, skin tone, court type), training data, evaluation data, factors and metrics with results, plus YAML metadata naming the datasets. *Note: rests partly on unconfirmed source(s) ASB/REN-37.* | official | [ASB/REN-36], [ASB/REN-37] (unverified) | role files: senior-ml-cv-engineer; definition-of-done |
| **ASB/ML-3**: Eval sets and golden clips are versioned (DVC or content-hash manifest) alongside code, so every reported metric names the exact data version and model version. The eval set is never used for training or tuning. | strong-consensus | [ASB/REN-38] | role files: senior-ml-cv-engineer; testing-strategy |
| **ASB/QA-1**: Test portfolio shape is chosen deliberately and documented: static checks, then many fast unit tests, then a substantial integration layer (trophy emphasis for UI code), then few E2E. Coverage targets are not mandated at 100%. Flaky tests are fixed or quarantined with a ticket, never tolerated or retried silently. | strong-consensus | [ASB/REN-25], [ASB/REN-03] | role files: senior-qa-engineer; testing-strategy; ci-cd |
| **ASB/QA-2**: Risk-based test planning: for each story, derive test cases from the acceptance criteria during refinement and rank them by risk (impact x likelihood). The QA verdict lists which high-risk cases were run. (ISTQB definitions not verified.) *Note: rests partly on unconfirmed source(s) ASB/REN-41.* | official | [ASB/REN-28], [ASB/REN-41] (unverified) | role files: senior-qa-engineer; definition-of-ready; sprint-planning |
| **ASB/QA-3**: Exploratory and usability testing is an explicit QA activity on the running stack each sprint (time-boxed charter plus notes). Every defect found exploratorily becomes an automated unit or integration regression test. | official | [ASB/REN-03] | role files: senior-qa-engineer; testing-strategy; definition-of-done |
| **ASB/QA-4**: Frontend-to-API and API-to-worker boundaries are covered by consumer-driven contract tests (e.g. Pact, or OpenAPI schema verification) so most compatibility checks run without a deployed environment. E2E is kept to critical user journeys. | expert-opinion | [ASB/REN-26], [ASB/REN-27] | role files: senior-qa-engineer; testing-strategy; ci-cd |
| **ASB/QA-5**: Quality gate: the CI test suite gives feedback within about 10 minutes, the build runs on every commit, and a red build stops feature work until fixed. The gate is defined in the DoD and enforced by the merge check, not by people's memory. | official | [ASB/REN-03], [ASB/REN-04] | role files: senior-qa-engineer; ci-cd; definition-of-done |
| **ASB/SEC-1**: Threat model per feature that touches data, auth or uploads, answering the four questions (what are we working on, what can go wrong, what will we do, did we do a good enough job). Include a DFD with trust boundaries, run STRIDE per element or flow, map each threat to a mitigation and a test, and update the model whenever the design changes (a living artifact, not one-off). *Note: rests partly on unconfirmed source(s) ASB/REN-31.* | official | [ASB/REN-29], [ASB/REN-30], [ASB/REN-31] (unverified) | role files: security-privacy-engineer; definition-of-ready; definition-of-done |
| **ASB/SEC-2**: Use ASVS 5.0 at an explicitly chosen level (L1 baseline, L2 for auth/PII). For each chapter in scope, verify the documentation requirement (the decision is written down) and the implementation requirement separately, and record both in the security review. | official | [ASB/REN-32] | role files: security-privacy-engineer; requirements |
| **ASB/SEC-3**: Privacy by design checks per feature: state the purpose; collect only data needed for the user-consented purpose (OWASP P10); define retention and deletion up front with a test (P6); give users access, correction and deletion (P9); no 'consent on everything' (P4); session expiry (P8); a breach-response path (P3). | official | [ASB/REN-33], [ASB/REN-34] | role files: security-privacy-engineer; requirements; definition-of-done |
| **ASB/SEC-4**: A role labelled read-only reviewer should be technically read-only. Claude Code subagent frontmatter supports disallowedTools and permissionMode. A Bash grant lets a 'read-only' agent write, so either remove Bash or restrict it. Unknown frontmatter keys are silently ignored, so verify field spelling. | official | [ASB/REN-39] | role files: security-privacy-engineer; role files: principal-engineer |
| **ASB/SRE-1**: SLOs are numerical, user-facing targets on SLIs; the error budget is derived from them. When the budget is exhausted, feature releases freeze except named emergency 'silver bullets'. The policy is written down before the first breach. *Note: rests partly on unconfirmed source(s) ASB/REN-09.* | official | [ASB/REN-07], [ASB/REN-08], [ASB/REN-09] (unverified) | role files: sre-devops-engineer; requirements; working-agreement |
| **ASB/SRE-2**: Toil (manual, repetitive, automatable, tactical, no enduring value, scales with service size) is tracked, for example as a ticket label or retro item, and kept below 50% of SRE time. Exceeding it creates explicit automation tickets. | official | [ASB/REN-06] | role files: sre-devops-engineer; retro |
| **ASB/SRE-3**: Measure delivery with DORA's FIVE current metrics (change lead time, deployment frequency, failed deployment recovery time, change fail rate, deployment rework rate), not the older four keys or MTTR. Never set them as targets (Goodhart) and never compare across unlike services. | official | [ASB/REN-02] | role files: sre-devops-engineer; retro; ci-cd |
| **ASB/SRE-4**: Trunk-based development: three or fewer active branches, merge to main at least daily, ticket branches live two days at most, no code freezes. Alerts are symptom-based (SLO burn), not one per cause. | official | [ASB/REN-01], [ASB/REN-10], [ASB/REN-05], [ASB/REN-04] | role files: sre-devops-engineer; ci-cd; working-agreement |
| **ASB/ALL-1**: Role-file hygiene: frontmatter uses only documented fields (name, description, tools/disallowedTools, model, ...). Descriptions are short trigger statements, with detail in the body. Role files live in .claude/agents/ under version control. Each role file has explicit Responsibilities, Inputs, Outputs, Quality checks and Anti-patterns sections so it can be audited against these practices. | official | [ASB/REN-39] | role files: principal-engineer; role files: senior-backend-engineer; role files: senior-frontend-engineer; role files: senior-ml-cv-engineer; role files: senior-qa-engineer; role files: security-privacy-engineer; role files: sre-devops-engineer |

## 6. Research gaps and blocked hosts

### 6.1 Hosts blocked during research

The research and fact-check sessions could not reach the hosts below (DNS failure, HTTP 000 or a proxy 403). Sources on them stay Unverified until the hosts are allowed in the environment's network settings and the pages are read. Where a host's content is also published in a GitHub repository, the repository was read instead, as noted.

| Host | Affected sources | Workaround used |
|---|---|---|
| scrumguides.org, scrum.org | ASB/RPD-20 | Scrum Guide 2020 read from a verbatim GitHub mirror (ASB/AGL-01, not official) |
| kanbanguides.org, prokanban.org | ASB/AGL-19 | none; ASB/AGL-06 used for WIP limits and lead time |
| dora.dev | none left | site source read from `dora-team/dora.dev` on GitHub |
| mountaingoatsoftware.com, humanizingwork.com | ASB/AGL-16, ASB/AGL-17, ASB/AGL-18 | none |
| xp123.com | ASB/REQ-29 | INVEST confirmed only through DORA (ASB/AGL-04) |
| alistairmavin.com (EARS) | ASB/SDD-27, ASB/REQ-22 | EARS patterns taken only from ASB/REQ-15 |
| iso.org, iso25000.com | ASB/REQ-23, ASB/REQ-24 | secondary sources only (ASB/REQ-13) |
| sre.google | ASB/REQ-25, ASB/REN-09 | Google Cloud blog posts ASB/REN-06, ASB/REN-07, ASB/REN-08, ASB/REQ-12 |
| cucumber.io | ASB/REQ-26 | Cucumber docs read from `cucumber/docs` on GitHub |
| accu.org | ASB/REQ-27 | none |
| jpattonassociates.com | ASB/REQ-28 | none |
| arxiv.org | ASB/REQ-30, ASB/REN-37 | model cards via ASB/REN-36 |
| kiro.dev | ASB/SDD-13 | none |
| martinfowler.com | ASB/SDD-14 | none |
| thoughtworks.com | ASB/SDD-15 | none |
| cognitect.com | ASB/SDD-16 | Nygard template via ASB/SDD-17 and ASB/REN-14 |
| gojko.net | ASB/SDD-28 | none |
| svpg.com | ASB/RPD-21 | none |
| producttalk.org | ASB/RPD-22 | none |
| iiba.org | ASB/RPD-23 | none |
| www.microsoft.com (HAX) | ASB/RPD-24 | the fact-checker reached it later; guideline texts not re-checked |
| nngroup.com | ASB/RPD-25 | none |
| eventstorming.com | ASB/RPD-26 | DDD Crew pages ASB/RPD-18, ASB/RPD-19 |
| w3.org | none left | WCAG read from `w3c/wcag` on GitHub (editor's draft, see ASB/RPD-05) |
| newsletter.kentbeck.com | ASB/REN-18 | none |
| threatmodelingmanifesto.org | ASB/REN-31 | four questions via ASB/REN-29 |
| research.google, storage.googleapis.com | ASB/REN-35 | none |
| domainlanguage.com | ASB/REN-40 | DDD via the repo's verified EP/ENG-11 to EP/ENG-14 |
| istqb.org | ASB/REN-41 | risk-based and exploratory testing via ASB/REN-03, ASB/REN-28 |
| web.dev, testing-library.com, nextjs.org, owasp.org | none left | read from their GitHub source repos (web.dev's repo is archived, 2023) |
| wikipedia.org, web.archive.org, github.blog, industrialempathy.com, atlassian.com, agilealliance.org, learn.microsoft.com, eur-lex, gdpr-info | none in the register | not used |

The GitHub API (`gh api`) was also refused for several repositories, so GitHub content was read through raw.githubusercontent.com or `git clone`.

### 6.2 Gaps and notes by area

These are the researchers' own notes, verbatim except that source IDs are written in `ASB/` form. Practice IDs such as P-ANT-24 or RE-09 refer to §5. Repo observations were measured on `origin/main` on 2026-10-31 and may have changed since.

Items marked CHALLENGE, COUNTER-IDEA or FINDING are design challenges or audit inputs for the PO. **They are not applied in this file or anywhere else in this draft**; the PO decides.

#### ANT: Anthropic guidance for agent teams on Claude Code

Scope: Official Anthropic guidance for agent teams built on Claude Code: subagent/role-file format, delegation, tool scoping, CLAUDE.md/memory, hooks, settings/permissions, skills, headless/SDK, prompt engineering, and evaluation of agent instructions (researched 2026-10-31)

Sources: 28; researcher-verified: 28; practices: 24.

- CHALLENGE TO THE ORIGINAL PROCESS (counter-idea): Anthropic's Opus 5 guidance (ASB/ANT-22) says to remove 'use a subagent to verify' scaffolding and to delegate only large independent work. Its agent-teams docs (ASB/ANT-09) warn that teams cost far more tokens and suit independent work. The PO's process requires principal-engineer plus senior-engineer plus QA review on every PR, including docs-only ones. Anthropic does endorse a separate skeptical evaluator (ASB/ANT-18), so independent review is supported, but the number of serial gates per small PR is not backed by any Anthropic source. Consider scaling review depth to risk (P-ANT-24, P-ANT-18). This is a judgment for the PO, not a finding of error.
- CHALLENGE TO THE AUDIT ITSELF: Anthropic's own practice (ASB/ANT-20, ASB/ANT-17, ASB/ANT-23) is to validate prompt and instruction changes with evals and line ablations, not only human review. Correcting role files by reviewer opinion alone, even against these practices, would not meet that bar. A small eval set of representative delegation and review tasks run before and after each role-file change would make the corrections testable.
- Repo observations (measured on origin/main 2026-10-31; not yet a full audit): 12 role files of 55-85 lines (engineering-manager has 1,176 words). Every file has an explicit tools list and a model. Descriptions are 300-425 characters each, well under the 15k-token budget. principal-engineer and principal-designer (reviewer roles) list Write and Edit, and principal-engineer also lists Bash; this conflicts with the least-privilege reviewer pattern in ASB/ANT-25 unless their duties require authoring. pickleball-domain-coach has 1 ALL-CAPS emphasis token. There is no CLAUDE.md on origin/main. .claude/settings.json has Read deny rules for secrets and PreToolUse/PostToolUse/Stop hooks, which aligns with P-ANT-04 and P-ANT-23.
- The engineering-blog URL /engineering/claude-code-best-practices now serves the Claude Code docs 'Best practices' page (ASB/ANT-08), so the original April 2025 blog text was not separately readable. All /engineering/ URLs 301 to /research/ but resolve.
- The former separate prompt-engineering pages (be-clear-and-direct, multishot-prompting, use-xml-tags, system-prompts, long-context-tips) now redirect to one consolidated page (ASB/ANT-21); facts were verified there.
- The anthropics/claude-agent-sdk-python README and the claude-code-auto-mode post were downloaded but not analysed, so they are not cited. GitHub API access (gh api) to anthropics/* was blocked in this session, so examples were read through raw.githubusercontent.com only. Official plugin agents now live in anthropics/claude-plugins-official.
- Version-sensitive facts: omitClaudeMd (v2.1.271+), /doctor prompt-audit (v2.1.283+) and CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS depend on the installed Claude Code version. Run `claude --version` in the environment before relying on them.
- Agent teams (ASB/ANT-09) are experimental and off by default. This project's 'team' is orchestrated subagents through workflow scripts, so agent-team-specific guidance (3-5 teammates, 5-6 tasks each) applies by analogy rather than directly.
- No official Anthropic source sets a hard line limit for subagent bodies. The 200-line limit is for CLAUDE.md and the 500-line limit for SKILL.md. Official example agents are about 46-56 lines, which suggests (but does not mandate) a compact size.

#### SDD: Spec-driven development, BDD and ADRs

Scope: Spec-driven development (SDD) with AI coding agents and the practices it grew out of: GitHub spec-kit, AWS Kiro specs, BDD / Specification by Example (Cucumber), ADRs (Nygard, adr.github.io), and Anthropic's guidance on planning before coding. Covers what a spec, a plan and a task should contain, who writes and reviews each, how specs stay the source of truth, traceability, and known pitfalls. Researcher: sdd. All work was read-only. Date: 2026-10-31.

Sources: 28; researcher-verified: 22; practices: 18.

- NETWORK: these hosts are outside this session's allowed network, so the sources on them are verified=false and no practice rests on them: kiro.dev, martinfowler.com, thoughtworks.com, cognitect.com, alistairmavin.com (EARS), gojko.net, en.wikipedia.org, cucumber.io (docs read from the GitHub source instead), github.blog, industrialempathy.com. To verify them, the PO must allow these domains in the environment network settings.
- UNVERIFIED CLAIMS NOT TO USE yet: the EARS templates (Kiro requirements format); Böckeler's spec-first / spec-anchored / spec-as-source levels and her criticisms; the Thoughtworks Radar ring for SDD; Nygard's rules on ADR immutability, superseding and length; Gojko Adzic's Specification by Example patterns; Google-style design-doc sections.
- Gherkin reference, better-gherkin, MADR and joelparkerhenderson ADR are already cited in docs/research (design-product-ai-agents.md, engineering-process.md) and were not re-fetched. code.claude.com/docs/en/best-practices and effective-harnesses-for-long-running-agents were re-verified today.
- EVIDENCE GAP: no independent empirical study showing that SDD improves outcomes was found or fetched. ASB/SDD-01..ASB/SDD-12 are vendor/tool documentation (GitHub spec-kit, Kiro), so their prescriptions are expert opinion, not proven practice.
- CHALLENGE / counter-idea 1 (the repo is stricter than SDD tooling): spec-kit's tasks template makes tests OPTIONAL (ASB/SDD-04), while this repo mandates TDD with scenario + integration + unit tests on every ticket. The audit should not 'correct' the repo toward spec-kit here. If anything, it should question whether docs-only and process tickets need the full test triple; the PO rules already give docs-only tickets 'relevant checks instead'.
- CHALLENGE / counter-idea 2 (review intensity): Anthropic warns that 'a reviewer that's asked to find problems will always find something' and that fixing every finding adds needless abstraction and tests (ASB/SDD-24). The working agreement requires a disposition row for every finding, including nits, plus principal + senior + QA approval. The audit should check whether the review briefs say 'correctness gaps against the spec; skip style', rather than only adding more review steps.
- CHALLENGE / counter-idea 3 (prose vs enforcement): docs/process/working-agreement.md on origin/main is 209 lines, many of them dated retro rules. Anthropic's guidance (ASB/SDD-24) is that prose instructions are not guaranteed to be followed, that the always-loaded memory file should stay short (under 200 lines), and that must-always rules belong in hooks or CI. Counter-proposal: map each MUST to its enforcing script or CI job (merge_ready.py, check_pr_size.py and check_test_immutability.py already exist) and move the history out to the ADRs, instead of adding more rules to the docs.
- CHALLENGE / counter-idea 4 (single spec vs per-feature specs): the repo has one design spec (docs/specs/2026-10-02-racket-analytics-design.md) plus global FR/NFR files and story files. spec-kit uses one specs/<feature>/ folder per feature (spec, plan, tasks). Neither is proven better. The audit should check for drift between the 2026-10 design spec and the 54+ later ADRs (is the spec still the source of truth, or have the ADRs overtaken it?) rather than impose a folder layout.
- CHALLENGE / counter-idea 5 (ADR scope): adr.github.io defines an ADR as an architecturally significant decision but allows 'any decision record' (ASB/SDD-19). Many repo ADRs are process decisions (for example 0039, 0047, 0052, 0054). This is allowed, but architecture decisions may be getting buried. Consider a type field or index, not renumbering.
- CHALLENGE / counter-idea 6 (who writes Gherkin): Cucumber says the PO owns scope and actively reviews the Gherkin (ASB/SDD-22). In this repo the BA writes it and the human PO does not review each scenario. The audit should say explicitly who acts as PO proxy for scenario review, and which scope calls must go back to the human PO.
- Did not check whether the repo's DoR or role files already contain cross-artifact coverage metrics or the semver/versioning of the working agreement. The auditor should check SDD-P06 and SDD-P07 against the actual files. I only grepped definition-of-ready.md, working-agreement.md and business-analyst.md.

#### AGL: Agile project management, flow and DORA

Scope: Agile project management best practices (Scrum Guide 2020, Kanban/flow, refinement, DoR and its criticism, INVEST, story splitting, estimation, planning, review, retrospectives, DORA metrics, working agreements, RACI vs accountabilities), with notes on where agent-only teams differ. Researcher: agile, Sprint 5 pre-audit, 2026-10-31. Read-only: nothing was edited.

Sources: 20; researcher-verified: 15; practices: 22.

- Network allowlist: scrumguides.org, www.scrum.org, kanbanguides.org, prokanban.org, dora.dev, mountaingoatsoftware.com, humanizingwork.com, xp123.com, atlassian.com, agilealliance.org, wikipedia, learn.microsoft.com and web.archive.org are all unreachable from this session (DNS ENOTFOUND or proxy CONNECT 403). WebFetch was told to stop retrying. These hosts would have to be allowed in the session's network settings to verify the primary pages.
- The Scrum Guide 2020 was verified from a third-party verbatim GitHub mirror (alexandreaquiles/scrum-guide, CC BY-SA, dated November 2020), not from scrumguides.org. Wording matched the passages quoted by search snippets, but it is still a mirror (official=false).
- DORA was verified from the dora.dev site source on GitHub (dora-team/dora.dev), which is first-party content. This closes the 'dora.dev blocked' gap in docs/research/engineering-process.md.
- NOT verified: the Kanban Guide (flow metrics: WIP, throughput, work item age, cycle time), Mike Cohn's SPIDR and 'Dangers of a Definition of Ready', the Humanizing Work splitting guide and flowchart (the article URL could not be located), Bill Wake's original INVEST article (INVEST is verified only via DORA), Derby and Larsen's full five retro stages (only Gather Data and Generate Insights via the MS playbook), and any RACI standard (e.g. PMI) for the 'exactly one Accountable' rule. Practices that depend on these are labelled accordingly.
- Observation for the auditors: the repo's retro files are dated in the future (e.g. docs/retros/2026-12-11-sprint-04.md, while today is 2026-10-31). Either the sprint calendar is simulated or the dates are wrong. Worth a check, because the retro template also requires 'dated' action items.
- Observation: definition-of-ready.md says 'INVEST is unverified' and working-agreement.md §3 says 'The Scrum Guide's timeboxes are unverified'. Both can now be cited (ASB/AGL-04, ASB/AGL-01). The retro template and the DoD still use the old four-key DORA set with 'Time to restore service' (ASB/AGL-02, ASB/AGL-03).
- Agent-only teams differ from human teams in ways no agile standard covers: timeboxes in hours, Daily Scrum attendance, capacity in person-days and psychological safety do not transfer directly. The only verified agent-specific guidance is from Anthropic (ASB/AGL-13 to ASB/AGL-15) and DORA's AI notes (ASB/AGL-04). Everything else about agent adaptation is (judgment).
- Not researched in depth: Scrum Master accountabilities beyond the timebox duty, Nexus or scaled Scrum, #NoEstimates and Monte Carlo forecasting, Atlassian or Google SRE retrospective and postmortem playbooks (blocked hosts).

#### REQ: Requirements down to atomic level

Scope: Breaking requirements down to atomic level: ISO/IEC/IEEE 29148 qualities, EARS, Gherkin, Example Mapping, measurable NFRs (ISO/IEC 25010:2023, Planguage, SLI/SLO), acceptance criteria vs DoD, traceability, story mapping. Includes a step-by-step procedure for FRs and NFRs and a read-only audit of the racket-analytics requirement docs on origin/main (as of 2026-10-31).

Sources: 30; researcher-verified: 21; practices: 16.

- NETWORK: many primary sources could not be fetched; each failed with DNS ENOTFOUND, HTTP 000 or a proxy 403. Blocked hosts: alistairmavin.com (EARS), iso.org (29148, 25010), iso25000.com, sre.google (SRE book), cucumber.io (Wynne blog), xp123.com (INVEST), jpattonassociates.com (story mapping), scrumguides.org, accu.org (Gilb), arxiv.org, agilealliance.org, martinfowler.com, learn.microsoft.com. To verify ASB/REQ-22..ASB/REQ-30, these hosts must be allowed in the session's network settings. GitHub API (gh api) was also refused for these repos; only raw.githubusercontent.com, cloud.google.com, anthropic.com and code.claude.com were reachable.
- UNVERIFIED CLAIMS kept out of the practices: the exact 29148 list and count; the SRE-book SLI template fields (aggregation interval, measurement region, percentiles over means); Planguage keyword definitions; the Example Mapping 25-minute timebox and 'many red cards' heuristic; INVEST; story mapping. Practices that rest on these are graded expert-opinion, not official.
- AUDIT-FINDING A1 (verified): the business-analyst role file (.claude/agents/business-analyst.md, <outputs> and <responsibilities>) names docs/requirements/functional.md, non-functional.md, traceability.md, stories/<id>.md and features/. All five are ABSENT on origin/main ('git cat-file -e origin/main:<path>' failed for each). The real files are functional-requirements.md, non-functional-requirements.md and traceability-matrix.md. The role file points agents at paths that do not exist.
- AUDIT-FINDING A2 (verified against a secondary source only): non-functional-requirements.md §0 rule 3 says ISO 25010 'could not be fetched' and files NFRs under the 2011 names (Usability, Portability; no Safety). The 2023 edition (ASB/REQ-13) renames these to Interaction capability and Flexibility and adds Safety. The doc already labels its choice as (judgment) and warns to re-check before quoting externally, so this is low severity. ASB/REQ-13 itself seems to misplace Testability, so check against ISO before changing anything.
- AUDIT-FINDING A3 (verified examples): some FRs are not atomic and their acceptance criteria are incomplete. FR-011 holds three obligations (clear client storage; clear SW caches; never cache media) but has one scenario and no negative path. FR-010 lists 5 data kinds and 2 formats, but its only scenario checks just 'every rally and its score'. HEURISTIC counts from a Python scan of functional-requirements.md and non-functional-requirements.md: 64 of 83 FRs have <= 1 scenario; 61 of 83 descriptions have more than one sentence; 11 of 82 NFR rows have (a)/(b) sub-targets (NFR-002, 005, 007, 012, 016, 027, 036, 038, 046, 066, 076). Caveat: a multi-sentence description is not always non-atomic, so these numbers are pointers for manual review, not defects.
- AUDIT-FINDING A4 (heuristic): 10 NFR rows with percentile targets name no window or sample size (NFR-006, 010, 011, 012, 013, 014, 017, 018, 019, 044). NFR-010 does give its load condition (50 RPS, server-side) but no window. Lab-measured rows (e.g. NFR-011) need a sample count rather than a time window.
- AUDIT-FINDING A5 (tested; my first test was wrong): traceability-matrix.md has 139 test-path references. My first grep reported 8 'missing' files; that was a regex false positive (it cut 'infra/tests/...' down to 'tests/...'). Re-check with full-path matching: 13 are exact repo paths and 126 are abbreviated suffixes (e.g. 'features/test_quick_tag.py') that each resolve to exactly one file. 0 broken, 0 ambiguous. So the matrix is not broken, but it cannot be checked by machine without suffix matching. Recommend full paths plus a CI check (RE-09).
- AUDIT-FINDING A6 (verified): 'git grep -iE "EARS|29148|Planguage|example mapping|story map|three amigos" origin/main -- docs .claude' finds no requirement-technique mentions (the only hits were 'appears'). The DoR requires Gherkin but names no discovery technique, no rule-to-requirement mapping and no ambiguity marker.
- AUDIT-FINDING A7 (judgment): the story-level DoD has no PO acceptance or sign-off (ASB/REQ-17 has 'signed off by the product owner' per story); the repo has it only at release level. The PO's own rules hand story acceptance to the senior-qa-engineer plus principal-engineer, so this is a question for the PO, not a correction.
- AUDIT-FINDING A8 (judgment): the DoR mixes broad items with conditional ones (UI, security, domain). ASB/REQ-16 advises only broadly applicable items. The repo's items are scoped by trigger ('For UI...', 'For security-relevant work...'), which is an acceptable variant (RE-10).
- COUNTER-IDEA C1 (over-atomisation): splitting 83 FRs and 82 NFRs into single-obligation IDs could produce several hundred IDs and a heavy traceability burden. Alternative: keep the FR ID as the unit of priority and traceability, and make the atom the Gherkin 'Rule:' inside it (ASB/REQ-01: one Rule = one business rule). Number them FR-011.R1..R3 rather than new register rows.
- COUNTER-IDEA C2 (EARS vs Gherkin duplication): writing both an EARS sentence and a Gherkin Rule doubles the text and lets the two drift apart. Alternative: write the Rule line itself in EARS form, so there is one source; the Examples then illustrate it.
- COUNTER-IDEA C3 (never guess vs informed guess): the BA role file says 'never silently pick an interpretation'. spec-kit (ASB/REQ-10) says make informed guesses, document assumptions and cap clarifications at 3. These are compatible if every default goes into an explicit Assumptions list that the PO reviews. The current role file has no Assumptions section.
- COUNTER-IDEA C4 (technical vs user-facing criteria): spec-kit lists 'API response time under 200ms' as a bad success criterion, while Google SRE (ASB/REQ-12) says SLIs/SLOs belong in system requirements. Resolution: two layers, a user-outcome success criterion and a system SLO NFR. The repo already does this in conflict K16 (200 ms client vs 1.5 s server), which supports the original design.
- COUNTER-IDEA C5 (declarative vs imperative): Anthropic's harness (ASB/REQ-21) uses imperative UI steps for its agent-verified feature list, against Cucumber's declarative guidance (ASB/REQ-02). Suggestion: keep declarative Gherkin as the requirement, and put imperative click-paths only in E2E specs and step definitions. Do not ban imperative steps outright.
- COUNTER-IDEA C6 (Planguage cost): full Planguage (Scale/Meter/Past/Goal/Fail/Wish) on every NFR is heavyweight. Apply it to release-gating NFRs only, and keep metric/target/how-tested for the rest.
- SELF-CHALLENGE: the heuristic counts in A3 and A4 are rough indicators. A5 shows how easily a check can mislead, so every audit claim was re-run before reporting. A2 rests on a secondary source with a likely error. No document was changed; this is a read-only research step, and corrections wait for PO review.

#### RPD: Product roles: PM, BA, designer, EM, domain coach

Scope: Role best practices for product-manager, business-analyst, principal-designer, engineering-manager (delivery lead) and pickleball-domain-coach (domain expert). This is a read-only audit input for the Sprint 5 pre-sprint doc review. Researcher: roles-product, 2026-10-31. Nothing was edited.

Sources: 26; researcher-verified: 19; practices: 25.

- NETWORK: these hosts are blocked in this session, so the topic's named primary sources could NOT be verified: scrumguides.org (Scrum Guide 2020: Product Goal, PO and SM accountabilities), svpg.com (Cagan), producttalk.org (Torres), iiba.org (BABOK), w3.org (worked around via the w3c/wcag GitHub source), microsoft.com (HAX, so DPA/DESIGN-11 was not re-verified), nngroup.com, eventstorming.com. They have to be allowed in the session's network settings before ASB/RPD-20..26 can be upgraded to verified. Every practice built on them is marked expert-opinion / (judgment).
- No source tested or verified: 'Teresa Torres product trio', the 'PM owns value+viability / designer usability / engineer feasibility' split, and the Scrum Master impediment-removal wording. These are commonly quoted but not checked here.
- CITATION DRIFT: the repo cites https://www.anthropic.com/engineering/building-effective-agents, which now answers 308 and redirects to /research/building-effective-agents. The content still says 'simplest solution possible'. The auditor should decide whether to update the URL (low severity).
- FINDING (verified, PD-1): principal-designer.md's WCAG 2.2 AA list omits two new Level A criteria, 3.2.6 Consistent Help and 3.3.7 Redundant Entry. AA conformance requires all A and AA criteria (ASB/RPD-08).
- FINDING (judgment, DC-4): pickleball-domain-coach.md has a dated status line ('As of 2026-10-03 NO pickleball rule ... is verified') that duplicates docs/domain/rules-verified.md. It is still accurate on origin/main today (rules-verified.md §Status: NOTHING IS VERIFIED), but it will go stale silently.
- FINDING (judgment, EM-5): engineering-manager.md is 1176 words against 501-623 for the other four product roles. Its responsibilities have grown with per-retro ADR patches (0030, 0033, 0037, 0047). Anthropic advises focused subagents, and the playbook advises DoR/process items that apply broadly. Consolidate them into working-agreement.md/DoD instead of the role file.
- FINDING (judgment, DC-1/DC-2): the domain coach file covers verification and drills but no collaborative modelling (EventStorming/Example Mapping participation) and no facilitator split. The BA file has no Example Mapping or Three Amigos step, although Cucumber names these as the way to discover acceptance criteria.
- COUNTER-IDEA 1 (challenge to the PO's process): 'every ticket = its own PR with unit+integration tests' is mismatched for docs-only role-file corrections. The playbook DoR says avoid items that apply to only some stories. A doc PR's test is a checkable review against cited sources (e.g. this practice list), so the 'docs-only: relevant checks instead' clause should define those checks explicitly (link check, source-ID check, word-count/duplication check) to avoid ritual tests.
- COUNTER-IDEA 2 (challenge to the original role design): continuous discovery and real-user touchpoints (Torres; DDD Crew 'Real end users') cannot be performed by agents. The PM and designer files should say plainly that user-value claims are hypotheses until the human PO supplies evidence. Otherwise agent 'discovery' is self-referential.
- COUNTER-IDEA 3: the EM acts as router, process owner, retro facilitator and metrics owner at once. The playbook recommends a neutral facilitator for retros after difficult periods, and EventStorming requires a neutral facilitator. Consider rotating facilitation (e.g. the main session or BA) so the EM is not grading its own process.
- COUNTER-IDEA 4 (challenge to the audit itself): many current role-file citations point to the repo's own research IDs (DPA/EP), which were verified once on 2026-10-03. Re-verifying a sample (as done here for ASB/RPD-02/03/10/11/12/18/19) found them still accurate, but the PM's 'prioritisation frameworks unverified' stance and the designer's HAX citation still depend on unreachable hosts. The audit should report confidence per claim rather than declare the docs 'validated'.
- Microsoft playbook accessibility page (ASB/RPD-10) still links WCAG 2.0 in Resources. Do not use it as a WCAG-version authority; use ASB/RPD-05..09.

#### REN: Engineering roles: PE, backend, frontend, ML/CV, QA, security, SRE

Scope: Role best practices for 7 engineering roles (principal-engineer, senior-backend-engineer, senior-frontend-engineer, senior-ml-cv-engineer, senior-qa-engineer, security-privacy-engineer, sre-devops-engineer), meant for auditing .claude/agents/<role>.md and the process docs. Researcher: roles-eng, read-only, 2026-10-31. METHOD: this session's network only allows github.com (git and raw), cloud.google.com and anthropic/claude.com domains. sre.google, dora.dev, research.google, arxiv.org, martinfowler.com, testing-library.com, nextjs.org, web.dev, owasp.org, threatmodelingmanifesto.org, kentbeck newsletter, domainlanguage.com, eur-lex and istqb.org all failed (DNS or proxy 403). So I read most primary sources from their official GitHub source repos with blobless git clones and 'git show HEAD:<path>': dora-team/dora.dev, vercel/next.js docs, reactjs/react.dev, testing-library-docs, OWASP CheatSheetSeries/ASVS/API-Security, fastapi docs, huggingface/hub-docs, iterative/dvc.org, paul-hammant/tbd, google/eng-practices, joelparkerhenderson ADR, kentcdodds.com, microsoft code-with-engineering-playbook, OWASP top-10-privacy-risks. These count as verified because I read the text myself. Sources I found only through WebSearch are verified=false. CHALLENGE NOTES (counter-ideas to the team's current process, each backed by a verified source): (1) DORA lists 'an overly heavy code-review process' needing multiple approvals as a trunk-based pitfall. Our rule needs principal + senior + QA approval per PR, which goes against that, so the team should either justify it (agent reviewers are cheap and fast) or measure review latency. (2) Kent C. Dodds warns against mandating 100% coverage, and Google eng-practices says to favor approving a CL once it definitely improves code health, not when it is perfect. (3) The web.dev GitHub repo is ARCHIVED (last commit 2023-10-29) and its CWV thresholds article still uses FID. INP replaced FID, but I could not verify that because web.dev is blocked, so any doc citing FID is stale. (4) Anthropic's subagent docs: Claude Code silently ignores unrecognised frontmatter fields, and descriptions should stay short because all of them load into context. Our descriptions are 300-425 chars, which is fine, but 'security-privacy-engineer' is labelled read-only yet has Bash. KEYWORD SCAN (grep on origin/main role files, a hint only and not a substantive audit): no frontend mention of getByRole, Core Web Vitals or performance budgets; no QA mention of risk-based, exploratory or contract testing; no ML mention of model cards or data versioning; no SRE mention of toil or trunk-based; no security mention of STRIDE (threat-model is mentioned).

Sources: 41; researcher-verified: 34; practices: 29.

- Network blocked these primary hosts: sre.google, dora.dev (worked around via the GitHub source repo), research.google and storage.googleapis (ML Test Score PDF), arxiv.org (Model Cards paper), martinfowler.com (Practical Test Pyramid), testing-library.com and nextjs.org (worked around via GitHub), web.dev (only the archived 2023 GitHub repo was readable), owasp.org, threatmodelingmanifesto.org, newsletter.kentbeck.com (Canon TDD), domainlanguage.com (Evans DDD Reference), eur-lex and gdpr-info (GDPR Art. 25), istqb.org, cognitect.com (Nygard original). To verify ASB/REN-09/18/31/35/37/40/41 directly, these hosts must be allowed in the session's network settings.
- INP thresholds (current Core Web Vital) are NOT verified; the archived web.dev source still uses FID.
- No primary source verified for GDPR Article 25 / Cavoukian's 7 Privacy by Design principles; privacy practices rest on OWASP Top 10 Privacy Risks and the Microsoft playbook.
- No verified primary source for ISTQB risk-based or exploratory testing definitions, or for Fowler's test pyramid (the DORA page links Cohn's pyramid only by reference).
- The keyword scan of role files is a grep hint only, not an audit; a role-by-role read against these practices is still needed (e.g. frontend: no getByRole/CWV/budget terms; QA: no risk-based/exploratory/contract terms; ML: no model card/data versioning terms; SRE: no toil/trunk terms; security: Bash granted despite 'read-only').
- The ML Test Score rubric details (28 tests, min-of-four scoring) come from search snippets and a secondary slide, not the paper.

### 6.3 Cross-cutting gaps

- No independent empirical study shows that spec-driven development improves outcomes. ASB/SDD-01 to ASB/SDD-12 are tool documentation, so their prescriptions are expert opinion.
- Nothing in any agile standard covers agent-only teams (timeboxes in hours, Daily Scrum attendance, capacity in person-days). The only verified agent-specific guidance is Anthropic's (ASB/AGL-13 to ASB/AGL-15) and DORA's AI notes (ASB/AGL-04). Anything else about adapting agile to agents is (judgment).
- Not verified from a primary source: INP thresholds for Core Web Vitals, GDPR Article 25 and the Privacy by Design principles, ISTQB definitions, Fowler's test pyramid, the Kanban Guide flow metrics, Bill Wake's INVEST article, the full five-stage retrospective sequence, any RACI standard, and the EARS templates.
- Version-sensitive Claude Code facts (for example `omitClaudeMd`, the `/doctor` prompt audit, `CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS`) depend on the installed version. Run `claude --version` before relying on them.

