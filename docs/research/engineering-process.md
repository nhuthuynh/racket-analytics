# Engineering Process Research: SDLC, Sprints, TDD, DDD, Code Review, Retrospectives, Delivery Metrics

- **Date:** 2026-10-03
- **Author role:** Senior research analyst (engineering process)
- **Scope:** The verified sources and rules the racket-analytics agent team (Engineering Manager, Product Manager, Principal Engineer, Principal Designer, Senior Engineers, Business Analyst, Senior QA, domain coach) uses for: the delivery lifecycle and sprint ceremonies, test-driven development and test strategy, domain-driven design, code review and commits, decision records, retrospectives, delivery metrics, and AI-agent working practices.
- **Product context:** see `docs/specs/2026-10-02-racket-analytics-design.md`.

## Method and evidence rules

Every source marked **verified = yes** was fetched with WebFetch on 2026-10-03, and the fetched page contained the guidance attributed to it below. Star counts are the values shown on the GitHub page when it was fetched. Many canonical hosts were **blocked by this environment's egress proxy**: google.github.io, martinfowler.com, tidyfirst.substack.com (Kent Beck), scrumguides.org, scrum.org, dora.dev, abseil.io, testing.googleblog.com, sre.google, atlassian.com, aws.amazon.com, wikipedia.org and web.archive.org. Where a primary source is mirrored in its own GitHub repository (Google eng-practices, Conventional Commits), the raw GitHub file was fetched instead, and that is noted. Statements marked **(judgment)** are the analyst's own recommendations and are not attributed to any source.

## Source register

| ID | Title | Publisher / author | URL | Type | Credibility signal | Verified |
|---|---|---|---|---|---|---|
| ENG-01 | google/eng-practices (repository) | Google | https://github.com/google/eng-practices | repo | 23.3k stars; Google; CC-BY 3.0; archived | yes: README and star count fetched |
| ENG-02 | Speed of Code Reviews | Google (eng-practices) | https://raw.githubusercontent.com/google/eng-practices/master/review/reviewer/speed.md | official doc (repo) | Google, part of ENG-01 | yes: fetched as raw GitHub file because google.github.io is blocked |
| ENG-03 | The Standard of Code Review | Google (eng-practices) | https://raw.githubusercontent.com/google/eng-practices/master/review/reviewer/standard.md | official doc (repo) | Google | yes: raw GitHub |
| ENG-04 | Small CLs | Google (eng-practices) | https://raw.githubusercontent.com/google/eng-practices/master/review/developer/small-cls.md | official doc (repo) | Google | yes: raw GitHub |
| ENG-05 | What to look for in a code review | Google (eng-practices) | https://raw.githubusercontent.com/google/eng-practices/master/review/reviewer/looking-for.md | official doc (repo) | Google | yes: raw GitHub |
| ENG-06 | How to write code review comments | Google (eng-practices) | https://raw.githubusercontent.com/google/eng-practices/master/review/reviewer/comments.md | official doc (repo) | Google | yes: raw GitHub |
| ENG-07 | Writing good CL descriptions | Google (eng-practices) | https://raw.githubusercontent.com/google/eng-practices/master/review/developer/cl-descriptions.md | official doc (repo) | Google | yes: raw GitHub |
| ENG-08 | Conventional Commits 1.0.0 | conventional-commits org | https://raw.githubusercontent.com/conventional-commits/conventionalcommits.org/master/content/v1.0.0/index.md | standard (community spec) | Widely adopted spec. The spec source was fetched from the site's own repo; star count not checked | yes: spec text fetched (www.conventionalcommits.org is blocked) |
| ENG-09 | architecture-decision-record | Joel Parker Henderson | https://github.com/joelparkerhenderson/architecture-decision-record | repo | 17.1k stars, 2.8k forks | yes |
| ENG-10 | MADR: Markdown Architectural Decision Records | adr org | https://github.com/adr/madr | repo / template standard | 2.5k stars | yes |
| ENG-11 | DDD Starter Modelling Process | DDD Crew | https://github.com/ddd-crew/ddd-starter-modelling-process | repo | 6,044 stars (ddd-crew org page) | yes |
| ENG-12 | Bounded Context Canvas | DDD Crew | https://github.com/ddd-crew/bounded-context-canvas | repo | 2,062 stars | yes |
| ENG-13 | Context Mapping | DDD Crew | https://raw.githubusercontent.com/ddd-crew/context-mapping/master/README.md | repo | 1,864 stars | yes |
| ENG-14 | EventStorming Glossary & Cheat Sheet | DDD Crew | https://raw.githubusercontent.com/ddd-crew/eventstorming-glossary-cheat-sheet/master/README.md | repo | 985 stars | yes |
| ENG-15 | Code-With Engineering Playbook: Agile ceremonies | Microsoft | https://raw.githubusercontent.com/microsoft/code-with-engineering-playbook/main/docs/agile-development/ceremonies.md | official playbook (repo) | Microsoft; repo has 2.7k stars | yes |
| ENG-16 | Code-With Engineering Playbook: Definition of Done | Microsoft | https://raw.githubusercontent.com/microsoft/code-with-engineering-playbook/main/docs/agile-development/team-agreements/definition-of-done.md | official playbook (repo) | Microsoft | yes |
| ENG-17 | Code-With Engineering Playbook: Unit testing | Microsoft | https://raw.githubusercontent.com/microsoft/code-with-engineering-playbook/main/docs/automated-testing/unit-testing/README.md | official playbook (repo) | Microsoft | yes |
| ENG-18 | Code-With Engineering Playbook: TDD example | Microsoft | https://raw.githubusercontent.com/microsoft/code-with-engineering-playbook/main/docs/automated-testing/unit-testing/tdd-example.md | official playbook (repo) | Microsoft | yes |
| ENG-19 | Code-With Engineering Playbook: Code review process guidance | Microsoft | https://raw.githubusercontent.com/microsoft/code-with-engineering-playbook/main/docs/code-reviews/process-guidance/README.md | official playbook (repo) | Microsoft | yes |
| ENG-20 | Code-With Engineering Playbook: Automated testing | Microsoft | https://raw.githubusercontent.com/microsoft/code-with-engineering-playbook/main/docs/automated-testing/README.md | official playbook (repo) | Microsoft | yes |
| ENG-21 | Using the Four Keys to measure your DevOps performance | Google Cloud blog | https://cloud.google.com/blog/products/devops-sre/using-the-four-keys-to-measure-your-devops-performance | FAANG blog | Google Cloud / DORA | yes. Editor's note: from 2022 DORA uses three clusters and dropped "Elite" |
| ENG-22 | Announcing the 2024 DORA report | Google Cloud blog | https://cloud.google.com/blog/products/devops-sre/announcing-the-2024-dora-report | FAANG blog (research summary) | Google Cloud / DORA, 2024-10-22 | yes |
| ENG-23 | dora-team/fourkeys | DORA team (Google) | https://github.com/dora-team/fourkeys | repo | 2.2k stars; **archived 2024-01-23** | yes (metric definitions only; tool is unmaintained) |
| ENG-24 | Best practices for Claude Code | Anthropic | https://code.claude.com/docs/en/best-practices (redirect from anthropic.com/engineering/claude-code-best-practices) | official doc | Anthropic | yes |
| ENG-25 | Building effective agents | Anthropic | https://www.anthropic.com/engineering/building-effective-agents | engineering blog | Anthropic, 2024-12-19 | yes |
| ENG-26 | How we built our multi-agent research system | Anthropic | https://www.anthropic.com/engineering/multi-agent-research-system | engineering blog | Anthropic, 2025-06-13 | yes |
| ENG-27 | Demystifying evals for AI agents | Anthropic | https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents | engineering blog | Anthropic | yes (publication date not captured) |
| ENG-28 | Effective harnesses for long-running agents | Anthropic | https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents | engineering blog | Anthropic | yes (publication date not captured) |

Unverified candidates are listed under "Gaps / unverified" and are not cited as evidence.

## Guidelines

### G1. Code review

1. **Approval standard.** Approve a change once it "definitely improves the overall code health of the system", even if it isn't perfect. Reviewers aim for continuous improvement, not perfection [ENG-03].
2. **Turnaround.** One business day is the maximum time to respond to a review request. Reviewers respond at their next natural break, not by interrupting focused work. If a full review must wait, send a quick reply with a timeline, another reviewer or preliminary comments [ENG-02]. Teams should set a review SLA in their working agreement and track the average time to merge a PR each sprint [ENG-19].
3. **Size.** One self-contained change per CL. "100 lines is usually a reasonable size … 1000 lines is usually too large." File spread counts too: 200 lines across 50 files is usually too large [ENG-04]. Reviewers should ask authors to split large CLs instead of delaying the review [ENG-02]. Defect discovery gets worse as review size grows [ENG-19].
4. **Tests ride with logic.** "A CL that adds or changes logic should be accompanied by new or updated tests for the new behavior." Refactorings go in separate CLs from feature changes [ENG-04].
5. **Review checklist:** design, functionality (including whether it is good for users), complexity (no over-engineering for hypothetical futures), tests (unit, integration or end-to-end as appropriate), naming, comments that explain *why* rather than *what*, style-guide compliance, and documentation updates [ENG-05].
6. **Comment etiquette.** Comment on the code, never the developer. Explain why. Label severity with `Nit:`, `Optional:`/`Consider:` or `FYI:` [ENG-03, ENG-06].
7. **Automate the nits.** Linting and static analysis should catch style issues before a human or agent reviews, so the review can focus on function and design [ENG-19].
8. **Independent reviewer.** Use a fresh context (a separate session or subagent) to review a diff, so the reviewer isn't biased toward code it just wrote. Tell the reviewer to flag only gaps that affect correctness or the stated requirements, because a reviewer prompted to find gaps will report some even when the work is sound, and chasing all of them leads to over-engineering [ENG-24].

### G2. Commits, change descriptions and versioning

1. Commit format: `<type>[optional scope]: <description>` with an optional body and footers. `feat` maps to a SemVer MINOR release, `fix` to PATCH, and `BREAKING CHANGE:` or `!` to MAJOR [ENG-08].
2. The first line is a short imperative summary of *what* the change does. The body covers the problem, why this approach, its trade-offs and links to bugs or design docs. "Fix bug" is not an acceptable description [ENG-07].

### G3. Architecture Decision Records (decision log)

1. Each ADR records **one** decision, with its rationale, the options considered with pros and cons, and timestamps [ENG-09].
2. Minimum template (Nygard): Title, Status, Context, Decision, Consequences [ENG-09]. Richer template (MADR): Context and Problem Statement, Decision Drivers, Considered Options, Decision Outcome, Consequences, Confirmation. Store ADRs in `docs/decisions/` named `nnnn-title.md` [ENG-10].
3. Don't rewrite history. Add dated notes, or write a new ADR that supersedes the old one when a decision changes [ENG-09].

### G4. Test-driven development and test strategy

1. **Red → Green → Refactor.** Write a failing test, make the smallest change that passes it, then refactor while the tests stay green. Write the negative test before the positive one so both get covered [ENG-18].
2. **Unit tests** must be reliable ("failures indicate a bug in the code"), fast (milliseconds each, and the whole suite in about a couple of seconds) and isolated. No sleeps, no disk reads, no real third-party API calls. Arrange/Act/Assert, with one thing tested in the Act step. Wrap third-party dependencies behind interfaces so they can be substituted in tests, and use mocks sparingly [ENG-17].
3. **Layered mix.** Unit tests run before every PR merge. Integration and end-to-end tests check components working together across interfaces and network hops. Load and performance tests run regularly. Code without tests is incomplete [ENG-20].
4. **Build for testability.** Parameterize instead of hard-coding. Log the configuration at startup. Log start and end markers for every activity. Propagate correlation IDs across services. Attach latency and other metadata to logs [ENG-20].
5. **Agents must self-verify.** Give the coding agent a pass/fail check (tests, build, linter, fixture diff). Have it show evidence (the command it ran and the output) instead of just claiming success. For bugs, "write a failing test that reproduces the issue, then fix it." One session can write tests while another writes code to pass them [ENG-24].
6. **Tests are immutable for agents.** Removing or editing tests to make them pass is unacceptable. Track features in a structured (JSON) list with pass/fail status, and run end-to-end checks before marking a feature done [ENG-28].

### G5. Sprint process, Definition of Done and retrospectives

1. **Sprint planning.** Stories should be designed and ready before planning. The sprint goal is a short bullet list and serves as the yardstick at sprint review [ENG-15].
2. **Estimation.** Use relative sizing (t-shirt sizes, Planning Poker). Collect data on estimation accuracy, and judge success against sprint goals rather than story points alone [ENG-15].
3. **Definition of Done, three levels** [ENG-16]:
   - *Story:* acceptance criteria met, builds with no errors, unit tests written and passing, code review complete, merged to the default integration branch.
   - *Sprint:* every story meets its DoD, and functional, integration, performance and end-to-end tests pass.
   - *Release:* the sprint goals are met, and the product owner marks the release ready for production.
4. **Retrospectives** must produce concrete, owned action items. They are tracked in the backlog, have a deadline, and are prioritized for completion before the next retrospective. Rotate formats (Timeline, 5 Whys, Fishbone, Focus, Mad/Sad/Glad) and choose a focus area for each retro [ENG-15]. Review-turnaround metrics feed the retrospective [ENG-19].
5. **Stable priorities.** DORA 2024 found that a "move fast and constantly pivot" mentality and unstable priorities hurt developer well-being and progress [ENG-22].

### G6. Domain-driven design

1. Follow the 8-step starter process: Understand → Discover (EventStorming) → Decompose (into sub-domains) → Strategize (find the core domain) → Connect → Organise (teams aligned to contexts) → Define (each bounded context's responsibilities) → Code [ENG-11].
2. Document every bounded context with the Bounded Context Canvas: Name, Purpose (in business language), Strategic Classification (core/supporting/generic), Domain Roles, Inbound and Outbound communication (commands, queries, events), Ubiquitous Language, Business Decisions, Assumptions, Verification Metrics, Open Questions [ENG-12].
3. Name each relationship between contexts with a context-mapping pattern: Partnership, Shared Kernel, Customer/Supplier, Conformist, Anticorruption Layer, Open Host Service, Published Language or Separate Ways. Use an Anticorruption Layer to translate an upstream model into your own model [ENG-13].
4. EventStorming notation: domain events are past-tense verbs (orange). Commands are blue, policies lilac ("whenever X happens, we do Y"), read models green, hotspots neon pink. There are three workshop levels: Big Picture, Process Modelling and Software Design [ENG-14].

### G7. Delivery metrics

1. The DORA keys: deployment frequency, lead time for changes (commit to production), change failure rate (share of deployments that cause a production failure) and time to restore service [ENG-21, ENG-23]. From 2022, DORA performance clusters are High, Medium and Low ("Elite" was dropped) [ENG-21].
2. AI adoption correlated with better documentation, code quality and review speed, but also with 1.5% lower delivery throughput and 7.2% lower stability. DORA recommends pairing AI with fundamentals: small batch sizes and robust testing [ENG-22].

### G8. AI-agent team operating practices

1. Start simple. Add multi-agent complexity only when simpler setups fall short, and test agents in sandboxes with guardrails [ENG-25].
2. Every subagent brief states an objective, an output format, guidance on tools and sources, and clear task boundaries. Scale effort to the complexity of the task [ENG-26].
3. Use full tracing and observability to diagnose agent failures. Multi-agent systems use about 15 times the tokens of a chat interaction, so use them only for high-value tasks [ENG-26].
4. Agent evals: start with 20–50 tasks taken from real failures. Combine code-based, model-based and human graders. Keep capability evals (low pass rate) separate from regression evals (pass rate near 100%). Read the transcripts. Use pass@k for exploratory tasks and pass^k where reliability is critical [ENG-27].
5. Long-running work: keep a progress file and git history. Start each session by reading the log and progress file and running a smoke test. Work on one feature at a time and leave the code production-ready [ENG-28].
6. Explore → Plan → Implement → Commit. Plan when the change spans several files or the approach is uncertain, and skip planning for a one-sentence diff. After two failed corrections, start a fresh context with a better prompt [ENG-24].
7. Use deterministic hooks for rules that must always run, such as lint after every edit, because CLAUDE.md instructions are only advisory [ENG-24].

## Implications for racket-analytics

- **Requirements (BA, PM).** Write every story with acceptance criteria that can become tests, and apply the three-level DoD [ENG-16]. Each milestone's "Done when" in the spec (§7) becomes a sprint-level DoD item. Examples: M0 "a correct score sheet from manual tags", and M2 "≥90% of rallies segmented correctly on the test set". The M2 and M3 accuracy targets should be held as regression evals with fixed labelled test sets, kept separate from exploratory capability evals [ENG-27] (judgment: the ENG-27 eval framing applies to the vision pipeline as well as to agents).
- **Domain model (Principal Engineer).** Run a Big Picture EventStorming over the "upload → stats → plan" flow, with past-tense events such as `MatchUploaded`, `CourtCalibrated`, `RallySegmented`, `ShotClassified`, `PointScored`, `ScoreCorrected`, `MetricSnapshotComputed` and `TrainingPlanGenerated` [ENG-14]. Then produce a Bounded Context Canvas for each candidate context [ENG-12]. Candidate contexts (judgment): *Match Capture/Ingest* (generic/supporting), *Vision Analysis* (core), *Rules & Scoring* (core, one per sport plug-in), *Analytics* (core), *Coaching/Training Plans* (core), *Drill Library* (supporting) and *Identity/Players* (generic). The sport plug-in boundary should be a Published Language or Open Host Service. The LLM integration in Coaching should sit behind an Anticorruption Layer so the model's vocabulary doesn't leak into the domain [ENG-13] (applying the patterns here is judgment).
- **TDD priorities (Senior Engineers, QA).** The pickleball rules engine (side-out scoring, serve order, faults) is pure logic, so it is the best first TDD target. Write negative cases (illegal serve, fault) before positive ones [ENG-18]. Analytics are "pure SQL/Python over event tables" per the spec, so unit-test them with fixture events. Keep GPU/model inference behind interfaces so unit tests stay millisecond-fast with no disk or network access [ENG-17]. Integration tests cover API → queue → worker → Postgres. End-to-end tests cover upload → score sheet → plan [ENG-20].
- **Testability and observability.** Pass a correlation ID from the upload through every pipeline stage. Log model versions and thresholds at startup. Record per-stage latency so the "1–2 GPU-minutes per match-minute" budget can be tracked [ENG-20].
- **Process (Engineering Manager).** Work in sprints with a written sprint goal [ENG-15]. Reviews get a 1-business-day SLA (in practice, for agents, review before the next task starts) [ENG-02]. Aim for PRs of about 100 changed lines, and treat anything near 1000 as too large [ENG-04]. Use Conventional Commits [ENG-08]. Put an ADR in `docs/decisions/` for every significant choice. Candidates already in the spec are FastAPI over Go, a Next.js PWA first, serverless GPU and LLM-chooses-from-a-curated-library [ENG-09, ENG-10]. Each retrospective goes in `docs/retros/` with owned, dated action items that are checked off at the next retro [ENG-15].
- **Agent team mechanics.** Each agent brief has an objective, output format, tools and boundaries [ENG-26]. Use a writer/reviewer split with a fresh-context reviewer limited to correctness and requirement gaps [ENG-24]. Agents must never edit tests to make them pass [ENG-28]. Every "done" claim must attach command output as evidence [ENG-24]. Use hooks (lint and test on edit) for rules that must not be skipped [ENG-24]. Keep a progress log and a JSON feature list across sessions [ENG-28].
- **Metrics.** Track a lightweight version of DORA per sprint: deployment frequency, lead time, change failure rate and time to restore [ENG-21]. Also track PR time-to-merge [ENG-19]. Because DORA found that AI adoption correlated with lower stability, an all-agent team should weight change failure rate and rework heavily and keep batches small [ENG-22] (that emphasis is judgment).

## Gaps / unverified

- **Scrum Guide 2020** (scrumguides.org, scrum.org, whatisscrum.org): fetch was blocked. A web-search snippet says the Sprint Retrospective is timeboxed to at most 3 hours for a one-month Sprint, but the primary text was **not verified**. Sprint length, Daily Scrum timebox, accountabilities and commitments are uncited here and should be re-verified before anyone treats them as standards.
- **Martin Fowler** (TestDrivenDevelopment, BoundedContext, TestPyramid, Practical Test Pyramid): martinfowler.com and web.archive.org are blocked. Not verified.
- **Kent Beck, "Canon TDD"** (tidyfirst.substack.com): blocked. Not verified. Red/Green/Refactor is cited from the Microsoft playbook [ENG-18] instead.
- **Software Engineering at Google** (abseil.io) and the **Google Testing Blog** (test sizes small/medium/large, the "80/15/5" split): blocked. Not verified, and no test-size ratio is asserted here.
- **dora.dev**: blocked. A web-search snippet says the 2023 and 2024 DORA models replaced MTTR with "failed deployment recovery time" and added a fifth metric, "deployment rework rate". This is **unverified** from a primary source, so G7 uses only the four keys verified via ENG-21 and ENG-23.
- **Google SRE book (blameless postmortems)**, **Atlassian Team Playbook (retrospectives)**, **AWS Builders' Library**: blocked. Not verified.
- **Conventional Commits star count** was not captured, and the GitHub API returned 403 for star lookups. The ddd-crew star counts come from the org page as rendered.
- **Publication dates** of ENG-27 and ENG-28 were not captured in the fetch.
- **Netflix and Meta engineering blogs**: not attempted, because of proxy limits and time.
