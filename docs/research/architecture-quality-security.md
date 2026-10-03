# Research: Architecture, Quality, Security, Reliability, Operations and Stack Practices

- **Date:** 2026-10-03
- **Author role:** Senior research analyst (architecture / NFR / security / reliability / ops / Python + TypeScript stack)
- **Product:** racket-analytics (see `docs/specs/2026-10-02-racket-analytics-design.md`)
- **Scope:** A verified source base for the agent team (Engineering Manager, Product Manager, Principal Engineer, Principal Designer, Senior Engineers, Business Analyst, Senior QA, domain coach) covering non-functional requirements, application/API security, reliability (SLOs, error budgets), operations (config, logs, process model, observability), the FastAPI / Next.js stack, engineering process (code review, change size), and building LLM/agent features (the coaching service and the agent team itself).
- **Out of scope:** Computer-vision model research, sports domain rules, UX/accessibility (covered by other research files).

## How verification was done

Every source below was fetched with WebFetch on 2026-10-03. A source is marked **verified = yes** only when the fetch succeeded and the returned content contained the guidance attributed to it. WebFetch returns a model-produced summary of the page, so short quoted phrases are as returned by that summary; treat them as close paraphrase, and re-open the URL before quoting in an external document.

The sandbox's egress proxy blocked many primary domains (owasp.org, sre.google, 12factor.net, fastapi.tiangolo.com, opentelemetry.io, nextjs.org, AWS, ISO, EU law sites, several FAANG blogs). Where the publisher maintains the canonical text in a public GitHub repository, the GitHub copy was fetched instead (e.g. OWASP ASVS, OWASP API Security, OWASP Top 10, Twelve-Factor, FastAPI docs, Next.js docs, OpenTelemetry). These are the publishers' own source repositories, not third-party mirrors. Blocked sources are listed in "Gaps / unverified".

## Source register

| ID | Title | Publisher / author | URL | Type | Credibility signal | Verified |
|---|---|---|---|---|---|---|
| SEC-01 | OWASP Application Security Verification Standard (repo) + "What is the ASVS" (levels) | OWASP | https://github.com/OWASP/ASVS ; https://github.com/OWASP/ASVS/blob/master/5.0/en/0x03-What-is-the-ASVS.md | Standard | OWASP flagship; 3.6k stars; **v5.0.0, May 2025** | yes |
| SEC-02 | ASVS 5.0 V5 File Handling | OWASP | https://github.com/OWASP/ASVS/blob/master/5.0/en/0x14-V5-File-Handling.md | Standard | as SEC-01 | yes |
| SEC-03 | ASVS 5.0 V8 Authorization | OWASP | https://github.com/OWASP/ASVS/blob/master/5.0/en/0x17-V8-Authorization.md | Standard | as SEC-01 | yes |
| SEC-04 | ASVS 5.0 V16 Security Logging and Error Handling | OWASP | https://github.com/OWASP/ASVS/blob/master/5.0/en/0x25-V16-Security-Logging-and-Error-Handling.md | Standard | as SEC-01 | yes |
| SEC-05 | ASVS 5.0 V14 Data Protection | OWASP | https://github.com/OWASP/ASVS/blob/master/5.0/en/0x23-V14-Data-Protection.md | Standard | as SEC-01 | yes |
| SEC-06 | ASVS 5.0 V13 Configuration | OWASP | https://github.com/OWASP/ASVS/blob/master/5.0/en/0x22-V13-Configuration.md | Standard | as SEC-01 | yes |
| SEC-07 | ASVS 5.0 V2 Validation and Business Logic | OWASP | https://github.com/OWASP/ASVS/blob/master/5.0/en/0x11-V2-Validation-and-Business-Logic.md | Standard | as SEC-01 | yes |
| SEC-08 | OWASP API Security Top 10 – 2023 (list) | OWASP API Security Project | https://github.com/OWASP/API-Security/blob/master/editions/2023/en/0x11-t10.md | Standard / awareness list | OWASP project; 2023 edition | yes |
| SEC-09 | API1:2023 Broken Object Level Authorization | OWASP API Security Project | https://github.com/OWASP/API-Security/blob/master/editions/2023/en/0xa1-broken-object-level-authorization.md | Standard | as SEC-08 | yes |
| SEC-10 | API4:2023 Unrestricted Resource Consumption | OWASP API Security Project | https://github.com/OWASP/API-Security/blob/master/editions/2023/en/0xa4-unrestricted-resource-consumption.md | Standard | as SEC-08 | yes |
| SEC-11 | OWASP Top 10 (repo; 2025 edition categories) | OWASP Top 10 project | https://github.com/OWASP/Top10 ; https://github.com/OWASP/Top10/tree/master/2025/docs/en | Awareness standard | OWASP flagship; 6.2k stars; **2025 final**, supersedes 2021 | yes |
| SEC-12 | A10:2025 Mishandling of Exceptional Conditions | OWASP Top 10 project | https://github.com/OWASP/Top10/blob/master/2025/docs/en/A10_2025-Mishandling_of_Exceptional_Conditions.md | Awareness standard | as SEC-11 | yes |
| REL-01 | SRE fundamentals: SLIs, SLAs and SLOs | Google Cloud Blog (J. Judkowitz, M. Carter), 2018-07-19 | https://cloud.google.com/blog/products/devops-sre/sre-fundamentals-slis-slas-and-slos | FAANG blog | Google SRE product team | yes |
| REL-02 | SRE error budgets and maintenance windows | Google Cloud Blog (J. Climent), 2020-06-22 | https://cloud.google.com/blog/products/management-tools/sre-error-budgets-and-maintenance-windows | FAANG blog | Google CRE team | yes |
| OPS-01 | The Twelve-Factor App (source repo) – III. Config | Heroku / A. Wiggins et al. | https://github.com/heroku/12factor ; https://github.com/heroku/12factor/blob/main/content/en/config.md | Methodology | Canonical source of 12factor.net (README says so); 3.8k stars | yes |
| OPS-02 | Twelve-Factor – IX. Disposability | Heroku | https://github.com/heroku/12factor/blob/main/content/en/disposability.md | Methodology | as OPS-01 | yes |
| OPS-03 | Twelve-Factor – XI. Logs | Heroku | https://github.com/heroku/12factor/blob/main/content/en/logs.md | Methodology | as OPS-01 | yes |
| OPS-04 | Twelve-Factor – VI. Processes | Heroku | https://github.com/heroku/12factor/blob/main/content/en/processes.md | Methodology | as OPS-01 | yes |
| OPS-05 | Twelve-Factor – X. Dev/prod parity | Heroku | https://github.com/heroku/12factor/blob/main/content/en/dev-prod-parity.md | Methodology | as OPS-01 | yes |
| OPS-06 | OpenTelemetry Specification – Propagators API | OpenTelemetry (CNCF) | https://github.com/open-telemetry/opentelemetry-specification/blob/main/specification/context/api-propagators.md | Standard / spec | CNCF project; 4.3k stars | yes |
| OPS-07 | OpenTelemetry docs – Signals | OpenTelemetry (CNCF) | https://github.com/open-telemetry/opentelemetry.io/blob/main/content/en/docs/concepts/signals/_index.md | Official doc | Source of opentelemetry.io | yes |
| STACK-01 | FastAPI Best Practices | zhanymkanov (community) | https://github.com/zhanymkanov/fastapi-best-practices | Repo | 18.1k stars | yes |
| STACK-02 | FastAPI docs – Concurrency and async/await | FastAPI (S. Ramírez) | https://github.com/fastapi/fastapi/blob/master/docs/en/docs/async.md | Official doc | Official docs source; ~103k stars | yes |
| STACK-03 | Full Stack FastAPI Template | FastAPI org | https://github.com/fastapi/full-stack-fastapi-template | Repo (reference architecture) | 45.9k stars; official FastAPI org | yes |
| STACK-04 | Next.js docs – Progressive Web Apps guide | Vercel | https://github.com/vercel/next.js/blob/canary/docs/01-app/02-guides/progressive-web-apps.mdx | Official doc | Official docs source; 143k+ stars | yes |
| STACK-05 | Ruff | Astral | https://github.com/astral-sh/ruff | Repo / tool | 49.9k stars | yes |
| STACK-06 | tus resumable upload protocol (repo + protocol.md) | tus.io / Transloadit | https://github.com/tus/tus-resumable-upload-protocol ; https://github.com/tus/tus-resumable-upload-protocol/blob/main/protocol.md | Open protocol spec | 1.7k stars; **v1.0.0** | yes |
| ENG-01 | Google eng-practices – Speed of code reviews | Google | https://github.com/google/eng-practices/blob/master/review/reviewer/speed.md | FAANG guideline | 23.3k stars; repo archived (read-only) 2025-11-21 | yes |
| ENG-02 | Google eng-practices – Small CLs | Google | https://github.com/google/eng-practices/blob/master/review/developer/small-cls.md | FAANG guideline | as ENG-01 | yes |
| ENG-03 | Google eng-practices – The standard of code review | Google | https://github.com/google/eng-practices/blob/master/review/reviewer/standard.md | FAANG guideline | as ENG-01 | yes |
| ENG-04 | Google eng-practices – What to look for in a code review | Google | https://github.com/google/eng-practices/blob/master/review/reviewer/looking-for.md | FAANG guideline | as ENG-01 | yes |
| AI-01 | Building effective agents | Anthropic Engineering (Erik S., Barry Zhang, as listed on page), 2024-12-19 | https://www.anthropic.com/engineering/building-effective-agents | Anthropic blog | Anthropic | yes |
| AI-02 | Writing effective tools for agents | Anthropic Engineering, 2025-09-11 | https://www.anthropic.com/engineering/writing-tools-for-agents | Anthropic blog | Anthropic | yes |
| AI-03 | Demystifying evals for AI agents | Anthropic Engineering, 2026-01-09 | https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents | Anthropic blog | Anthropic | yes |
| AI-04 | How we built our multi-agent research system | Anthropic Engineering, 2025-06-13 | https://www.anthropic.com/engineering/multi-agent-research-system | Anthropic blog | Anthropic | yes |
| AI-05 | Best practices for Claude Code | Anthropic (Claude Code docs; old URL anthropic.com/engineering/claude-code-best-practices redirects here) | https://code.claude.com/docs/en/best-practices | Official doc | Anthropic | yes |

36 verified pages from 14 publishers/repositories. Failed fetches are listed under "Gaps / unverified".

## Guidelines

### G1. Quality model and NFR framing
- G1.1 Every service must have an explicit, numeric availability SLO tied to a business objective. Do not engineer reliability beyond what you can commit to sustaining [REL-01].
- G1.2 SLI = measured ratio of good events to valid events (e.g. successful vs unsuccessful requests). An SLO is the internal target and an SLA is the external promise. Internal SLOs should be tighter than any SLA (example given: internal 99.95% vs SLA 99.9%) [REL-01].
- G1.3 Error budget = 100% − SLO (99.9% SLO → 0.1% budget). Use it to balance feature work against reliability work [REL-02].
- G1.4 Planned maintenance counts against the error budget unless the business has explicitly accepted it, it is communicated in advance, and there is no plan to remove it. Non-counted windows need an execution plan, exit criteria, rollback and low-traffic scheduling [REL-02].
- G1.5 ISO/IEC 25010 characteristics could NOT be verified this session (see Gaps). Until they are, NFR categories are organised by the verified sources above: security (OWASP), reliability (SRE), operability (12-factor, OTel), maintainability (eng-practices) (judgment).

### G2. Application and API security (target: ASVS 5.0 Level 2)
- G2.1 Pick an ASVS level by risk. L1 (~20% of requirements) is the minimum. L2 (L1+L2 ≈ 70% of requirements) is the level "most applications should be striving" for. L3 is for the highest-assurance systems [SEC-01].
- G2.2 **Object-level authorization on every record access.** Check authorization in every function that uses a client-supplied ID to fetch a record (API1 / BOLA). Use random, unpredictable IDs. Write tests for the authorization mechanism [SEC-09]. ASVS 8.2.2 (L1): data-specific access only for consumers with explicit permission to that item [SEC-03].
- G2.3 **Field-level authorization:** restrict which properties a consumer can read or write (BOPLA; ASVS 8.2.3, L2; API3:2023) [SEC-03][SEC-08].
- G2.4 **Function-level authorization, deny by default:** ASVS 8.2.1 (L1). Enforce rules at a trusted service layer, never in client JavaScript (8.3.1, L1) [SEC-03].
- G2.5 **Input validation:** positive validation against expected structure and limits (2.2.1, L1), always enforced server-side (2.2.2, L1). Business flows run only in the expected step order (2.3.1, L1). Multi-step changes are transactional, all or nothing (2.3.3, L2) [SEC-07].
- G2.6 **Anti-automation and resource limits:** rate limits and anti-automation controls against quota exhaustion and resource overuse (ASVS 2.4.1, L2) [SEC-07]. Cap upload sizes, string lengths and array sizes. Limit container memory, CPU, restarts, file descriptors and processes. Validate pagination parameters server-side. **Set spending limits or billing alerts on every paid provider** (API4) [SEC-10].
- G2.7 **File uploads (ASVS V5):** accept only files of appropriate size (5.2.1, L1). Check the extension AND the content type via magic bytes (5.2.2). Never use user-supplied filenames for storage; generate internal names (5.3.2, L1). Uploaded files must never execute as server code (5.3.1, L1). Set Content-Disposition and sanitise filenames on download (5.4.1–5.4.2, L2). Antivirus-scan untrusted files before serving them (5.4.3, L2). Per-user storage quotas (5.2.4, L3) [SEC-02].
- G2.8 **Secrets:** keep secrets out of source code and build artefacts and store them in a vault or KMS (13.3.1, L2). Least-privilege access to secrets (13.3.2) [SEC-06]. The config litmus test: the codebase could be open-sourced at any moment without exposing credentials [OPS-01].
- G2.9 **Service-to-service auth:** individual service accounts or short-lived tokens, not static shared keys (13.2.1, L2). Least privilege for backend accounts (13.2.2). No default credentials (13.2.3). Allowlist outbound connections (13.2.4–13.2.5) [SEC-06].
- G2.10 **Hardening:** debug mode off in production (13.4.2). No .git or other VCS metadata exposed (13.4.1, L1). No directory listing (13.4.3) [SEC-06].
- G2.11 **SSRF:** validate any user-supplied URI before the API fetches it (API7:2023) [SEC-08].
- G2.12 **Third-party/API consumption:** do not trust data coming back from integrated services, LLM APIs included (API10:2023) [SEC-08].
- G2.13 **Inventory:** keep an accurate inventory of API versions and endpoints. Retire deprecated and debug endpoints (API9:2023) [SEC-08].
- G2.14 **Supply chain:** "Software Supply Chain Failures" is A03 in the OWASP Top 10:2025 [SEC-11]. Dependency pinning, SBOM and update cadence are the controls (judgment; the specific controls were not fetched from the A03 page).
- G2.15 **Exceptional conditions (A10:2025):** catch errors where they occur. Fail closed and roll back the whole transaction rather than recovering partway. Use a central error handler plus a global fallback handler. Monitor for repeated errors [SEC-12].

### G3. Data protection and privacy controls
- G3.1 Identify and classify all sensitive data into protection levels (14.1.1, L2), and document the encryption, integrity, retention and access requirements for each level (14.1.2, L2) [SEC-05].
- G3.2 Delete outdated or unneeded sensitive data automatically on a defined schedule (14.2.7, L3) [SEC-05].
- G3.3 No sensitive data (API keys, session tokens) in URLs or query strings (14.2.1, L1) [SEC-05].
- G3.4 Send `Cache-Control: no-store` on sensitive responses (14.3.2, L2). Clear authenticated data from client storage on logout (14.3.1, L1). Keep sensitive data out of browser storage, session tokens excepted (14.3.3, L2) [SEC-05].
- G3.5 GDPR / data-protection-law obligations (lawful basis, data minimisation, storage limitation, data protection by design, children's data, biometric data) were **not verified** this session. See Gaps. Do not cite GDPR articles in requirements until a privacy research pass verifies them.

### G4. Security logging and error handling
- G4.1 Each log entry records when, where, who and what (16.2.1). All components use synchronised time in UTC or with an explicit offset (16.2.2) [SEC-04].
- G4.2 Log every authentication attempt, successful or not (16.3.1), and every failed authorization (16.3.2). Log attempts to bypass validation, business-logic or anti-automation controls (16.3.3), plus unexpected errors and security-control failures (16.3.4) [SEC-04].
- G4.3 Never log credentials. Hash or mask session tokens, depending on data classification (16.2.5). Encode log data to prevent log injection (16.4.1). Protect logs from tampering (16.4.2) and ship them to an isolated system (16.4.3) [SEC-04].
- G4.4 Return generic error messages. No stack traces, queries, secrets or tokens in responses (16.5.1) [SEC-04].

### G5. Reliability and the process model
- G5.1 Processes are stateless and share nothing. Persistent data lives in backing services. Local disk or memory is only a brief single-transaction cache. No sticky sessions [OPS-04].
- G5.2 Fast startup (ideally a few seconds). Graceful shutdown on SIGTERM: web processes stop accepting new requests and finish in-flight ones [OPS-02].
- G5.3 **Workers return their job to the queue on shutdown** (NACK or requeue). Jobs must be reentrant: wrap results in a transaction or make the operation idempotent. Use a queue backend that survives sudden process death [OPS-02].
- G5.4 Resumable uploads (tus 1.0.0): the client uses HEAD to find the server's `Upload-Offset` and PATCHes from that offset. The server MUST answer 409 Conflict on an offset mismatch, without changing the upload. Optional extensions cover creation, checksums (SHA1 required when the extension is supported), expiration of abandoned uploads, and concatenation for parallel chunks [STACK-06].

### G6. Operations, configuration and observability
- G6.1 Config lives in environment variables, never in constants in code [OPS-01].
- G6.2 Logs are an unbuffered event stream to stdout. The app never manages log files or routing [OPS-03].
- G6.3 Dev/prod parity: deploy within hours of writing code, keep authors involved in deploying, and **do not use different backing services in dev and prod** (e.g. SQLite in dev with Postgres in prod), even behind adapters [OPS-05].
- G6.4 OpenTelemetry's stable signal set is traces, metrics, logs and baggage. Events and profiles are still in development or proposal [OPS-07].
- G6.5 Configure propagation as the composite W3C Trace Context + Baggage propagator (the spec's default when pre-configured). A malformed incoming header must not throw and must not overwrite a valid existing context [OPS-06].

### G7. Python / FastAPI backend practices
- G7.1 If unsure, declare path operations with plain `def`: FastAPI runs them in a threadpool. Use `async def` only when every call inside is awaitable [STACK-02].
- G7.2 Never block inside an `async` route, because it freezes the event loop. CPU-heavy work (e.g. video decoding or inference) belongs in a task queue or multiprocessing, not threads [STACK-01].
- G7.3 Organise code by domain module (`router.py`, `schemas.py`, `models.py`, `service.py`, `dependencies.py`, `exceptions.py`, …) under `src/`, not by file type [STACK-01]. This lines up with DDD bounded contexts (judgment).
- G7.4 Rely heavily on Pydantic validators (enums, patterns). Use a custom base model for datetime/serialisation conventions. Split `BaseSettings` per module [STACK-01].
- G7.5 Use dependencies for validation that needs a DB lookup (e.g. "match exists and belongs to user"). Chain them, and rely on per-request caching [STACK-01]. This is the natural place for BOLA checks (G2.2) (judgment).
- G7.6 Tests: an async test client from day one (httpx `ASGITransport`), and `app.dependency_overrides` for fakes rather than monkeypatching [STACK-01].
- G7.7 Lint and format with Ruff, which replaces Flake8+plugins, Black, isort, pyupgrade and autoflake and has 900+ rules [STACK-05][STACK-01].
- G7.8 Reference architecture: the FastAPI org's template uses FastAPI + SQLModel + Pydantic + PostgreSQL, JWT auth with password hashing, Docker Compose, Traefik for HTTPS, Pytest, Playwright E2E and GitHub Actions CI [STACK-03].

### G8. Next.js PWA client practices
- G8.1 A PWA needs a web app manifest (`app/manifest.ts`) and a service worker, and must be served over HTTPS (`next dev --experimental-https` for local testing) [STACK-04].
- G8.2 Set security headers in `next.config.js`: `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, a Content-Security-Policy, and cache-control rules for the service worker script [STACK-04].
- G8.3 Web push uses VAPID keys and server actions for subscriptions [STACK-04]. This is relevant for "your analysis is ready" notifications (judgment).

### G9. Engineering process: change size and code review
- G9.1 A change is one self-contained concern. About 100 lines is reasonable and about 1000 is usually too large; spread across many files counts against it [ENG-02].
- G9.2 Every behaviour change ships with new or updated tests. Refactorings ship separately from feature changes [ENG-02].
- G9.3 **Reviewers respond within one business day at most** [ENG-01].
- G9.4 Approve once the change definitely improves overall code health, even if it is not perfect. Prefix optional comments with "Nit:". Technical facts and data outrank opinion, and the style guide is the authority on style [ENG-03].
- G9.5 Reviewers check design, functionality, complexity, tests, naming, comments, style, docs, every line, and context. They ask for unit, integration or E2E tests as appropriate, and confirm the tests themselves are valid. They push back on speculative over-engineering [ENG-04].

### G10. LLM features and the agent team
- G10.1 Prefer simple, composable patterns over frameworks. Use **workflows** (predefined code paths) for well-defined tasks and **agents** only where flexibility is needed and success is verifiable [AI-01].
- G10.2 Patterns available: prompt chaining, routing, parallelisation, orchestrator-workers, evaluator-optimiser [AI-01]. AI-04 reports the orchestrator-worker pattern beating a single agent by 90.2% on their internal research eval, at roughly 15x the tokens of chat [AI-04].
- G10.3 Tool design: consolidate tools around tasks rather than wrapping every endpoint. Namespace tool names. Return high-signal, human-meaningful identifiers rather than opaque UUIDs. Paginate and truncate with sensible defaults. Write unambiguous tool descriptions [AI-02].
- G10.4 Evals: start with 20–50 tasks drawn from real failures. Combine code-based, model-based and human graders. Keep capability evals separate from regression evals (~100% pass expected). Report pass@k / pass^k for non-determinism. **Read the transcripts.** Isolate trials [AI-03].
- G10.5 Agent workflow: give the agent a check it can run (tests, build, lint) and have it show evidence rather than assert success. Explore, then plan, then implement, then commit. Write the failing test first when fixing a bug. Use a Writer/Reviewer split, or an adversarial review subagent working in a fresh context. Tell reviewers to flag only correctness or requirement gaps so the work does not get over-engineered [AI-05].
- G10.6 Use hooks for rules that must be enforced every time, since CLAUDE.md instructions are only advisory. Keep CLAUDE.md short and pruned [AI-05].
- G10.7 Delegation prompts need clear task boundaries, an output format, and effort scaled to complexity [AI-04].

## Implications for racket-analytics

Proposed requirement IDs are suggestions for the Business Analyst. They are (judgment) unless a source is cited.

### Security posture
- **Target ASVS 5.0 L2 for the API and client** [SEC-01]. Footage of identifiable people, possibly minors (spec §8), is more sensitive than a "limited data" startup case (judgment). Add L3 V5 items 5.2.4 (per-user quotas) and 5.2.6 (pixel-flood/oversize images) because video upload is the core flow [SEC-02].
- **BOLA is the top API risk for us**: every `/matches/{id}`, `/rallies/{id}`, `/shots/{id}`, `/players/{id}`, `/plans/{id}`, clip and thumbnail URL is an object reference [SEC-09]. Suggested NFR-SEC-01: "Every endpoint that takes a resource ID enforces ownership or explicit sharing via a FastAPI dependency. A parametrised authorization test suite checks that user B gets 404/403 on every one of user A's resources." Use UUIDs for public IDs [SEC-09].
- **Opponent profiles** are user-created records about third parties. They must be scoped to the creating user and never be readable across users (8.2.2) [SEC-03].
- **Upload pipeline**: enforce a maximum file size and duration. Check the container type with magic bytes (e.g. ffprobe) and do not trust the extension. Store under generated object keys. Serve via short-lived signed URLs with Content-Disposition [SEC-02]. Never pass user filenames to FFmpeg (judgment, from 5.3.2).
- **Cost controls (API4)**: GPU minutes and LLM tokens are spending vectors. Suggested NFR-COST-01: per-user monthly analysis quota, rate limits on job creation, and spending limits or billing alerts on the GPU provider and the Anthropic API [SEC-10]. This ties to the spec's 1–2 GPU-min per match-min target (§8).
- **LLM output is untrusted input** [SEC-08 API10]. The coaching service must check that every drill ID the LLM returns exists in the curated library, and that every cited metric exists, before saving a plan. This also enforces the spec's "does not invent drills" decision (spec §2).
- **Secrets** (DB, S3, GPU provider, Anthropic key) come only from env or a vault, with no defaults committed. Workers authenticate to the API and storage with their own least-privilege credentials [SEC-06][OPS-01].

### Privacy
- Classify data: raw video and clips (high), player and opponent names (medium), metrics (low/medium). Document retention per class [SEC-05]. Implement the spec's "retention controls" as scheduled automatic deletion (14.2.7) [SEC-05].
- Signed media URLs must never contain long-lived tokens. Sensitive API responses use `Cache-Control: no-store` [SEC-05].
- No face recognition (spec §8) stays a hard constraint. Legal basis, consent wording and children's-data rules need a verified GDPR/privacy research pass before M0 ships to real users (see Gaps).

### Reliability and SLOs (proposed starting targets, judgment, to be tuned from data)
- Define SLIs per user journey: upload success rate (resumable uploads finished / started), analysis job success rate, analysis latency (job finished within N× video duration), API availability, and plan generation success. Each gets a numeric SLO and an error budget [REL-01][REL-02].
- Error budget policy: when an SLO's budget is exhausted, the next sprint prioritises reliability work (judgment, applying [REL-02]'s velocity/reliability trade-off). Record the policy in `docs/process/`.
- Analysis jobs must be idempotent and reentrant, keyed by (match_id, pipeline_version, stage). A worker killed mid-job leaves its job requeued, and a re-run overwrites rather than duplicates `Event`/`Shot` rows [OPS-02]. This fits the spec's "Event kept for re-processing".
- Make the pipeline stages checkpointed transactions. A failing stage marks the job failed and rolls back its partial writes (fail closed) [SEC-12]. Graceful degradation ("score only, no shot detail", spec §8) should be an explicit state, not a partial write (judgment).
- Use tus 1.0.0 (or an S3 multipart equivalent) for "resumable, chunked" phone uploads. Enable the checksum and expiration extensions to clean up abandoned uploads [STACK-06].

### Architecture and operations
- API and workers are stateless 12-factor processes. Video goes straight to object storage, never to local disk beyond a single job's scratch space [OPS-04].
- Dev uses Postgres + S3-compatible storage (e.g. MinIO) + the same queue as prod via Docker Compose, with no SQLite shortcut [OPS-05][STACK-03].
- Logs are structured JSON to stdout with UTC timestamps. Each entry carries request_id/trace_id, user_id (pseudonymous), match_id and job_id [OPS-03][SEC-04].
- Instrument the API, queue and workers with OpenTelemetry traces + metrics and W3C Trace Context propagation through the job queue (inject on enqueue, extract in worker), so one trace covers upload → analysis → plan [OPS-06][OPS-07]. Emit GPU-seconds per job as a metric for the cost NFR.

### Stack conventions
- FastAPI code organised by bounded context: `matches`, `video_ingest`, `analysis_jobs`, `scoring` (rules engine), `analytics`, `coaching`, `players` [STACK-01]. Use `def` routes unless every call is async. All CV/ML work goes to workers via the queue, never into the API process [STACK-02][STACK-01].
- Ruff for lint and format in pre-commit and CI [STACK-05]. Pytest + httpx async client + `dependency_overrides` for API tests [STACK-01]. Playwright for E2E flows [STACK-03].
- Next.js PWA with manifest, service worker, HTTPS, and baseline security headers (CSP, nosniff, frame DENY) from sprint 1 [STACK-04].

### Process and tests (for EM, QA and the agent team)
- PR size target of ≤ ~400 changed lines, ideally ~100 [ENG-02] (the 400 ceiling is judgment). Tests in the same PR. Refactors in separate PRs.
- Review turnaround of ≤ 1 business day. For agent reviewers, review runs immediately after each PR is opened [ENG-01]. Approval standard is "improves code health". Nits are labelled [ENG-03].
- Every implementing agent must attach evidence (test output, command run) to its decision-log entry. A separate fresh-context reviewer agent checks each diff against the sprint's requirements and flags only correctness or requirement gaps [AI-05].
- Enforce deterministic gates (tests, ruff, type check, authz test suite) with hooks/CI, not prompt instructions [AI-05].
- Coaching LLM: build it as a **workflow** (rules layer ranks weaknesses → LLM selects drills from a tool returning library entries → validator checks IDs). It does not need an autonomous agent [AI-01]. Build a 20–50 case eval set of player stat profiles with expected drill categories. Use code graders for the "only library drills" and "every drill cites a metric" rules, and a model grader for the quality of the explanations. Track regression evals in CI [AI-03].
- Test scenarios QA should own from this file: BOLA matrix (G2.2), upload limits/magic-byte rejection (G2.7), upload resume after network loss incl. 409 offset mismatch (G5.4), worker kill mid-job → requeue → no duplicate rows (G5.3), malformed traceparent header doesn't break requests (G6.5), generic error bodies (G4.4), LLM returns unknown drill ID → rejected (G10/API10).

## Gaps / unverified

Fetch attempts that failed (egress proxy blocked the domain unless noted). Nothing from these is cited as verified above.

| Intended source | URL attempted | Result | Mitigation |
|---|---|---|---|
| ISO/IEC 25010 quality model | https://iso25000.com/index.php/en/iso-25000-standards/iso-25010 ; https://www.iso.org/standard/78176.html | Blocked | Characteristics and 2011 vs 2023 edition unverified. Re-fetch before using 25010 vocabulary in requirements. |
| OWASP site pages (ASVS, API Top 10) | https://owasp.org/... | Blocked | Used OWASP's own GitHub source repos instead (SEC-01..12). |
| Google SRE book "Service Level Objectives" and SRE workbook "Error budget policy" | https://sre.google/sre-book/service-level-objectives/ ; https://sre.google/workbook/error-budget-policy/ | Blocked | Used Google Cloud Blog SRE posts (REL-01, REL-02). The specific error-budget-policy rules (release freeze, postmortem thresholds) remain unverified. |
| Twelve-Factor site | https://12factor.net/ | Blocked | Used canonical source repo heroku/12factor (OPS-01..05). |
| FastAPI docs site | https://fastapi.tiangolo.com/async/ | Blocked | Used docs source in fastapi/fastapi repo (STACK-02). |
| OpenTelemetry docs site | https://opentelemetry.io/docs/concepts/signals/ | Blocked | Used opentelemetry.io source repo (OPS-07). |
| Next.js docs site | https://nextjs.org/docs/app/guides/progressive-web-apps | Blocked | Used docs source in vercel/next.js repo (STACK-04). |
| AWS Well-Architected pillars; AWS Builders' Library "Timeouts, retries and backoff with jitter" | docs.aws.amazon.com/...; aws.amazon.com/builders-library/... | Blocked | Retry/backoff/jitter guidance is unverified. Do not cite AWS. |
| Google Cloud Architecture Framework – reliability pillar, graceful degradation | https://docs.cloud.google.com/architecture/framework/reliability (redirect target) | Blocked | Unverified. |
| Google Cloud blog CRE escalation post | https://cloud.google.com/blog/products/devops-sre/applying-the-escalation-policy-cre-life-lessons | 404 (URL guessed and wrong) | Dropped. |
| ASVS "Using ASVS" chapter | https://github.com/OWASP/ASVS/blob/master/5.0/en/0x03-Using-ASVS.md | 404 (wrong filename) | Levels verified from 0x03-What-is-the-ASVS.md instead. |
| GDPR text (Art. 5, 8, 9, 25) | https://eur-lex.europa.eu/eli/reg/2016/679/oj ; https://gdpr-info.eu/art-25-gdpr/ | Blocked | **High-priority gap.** Privacy and legal-basis requirements for filming third parties and minors are unverified. |
| UK ICO data-protection principles | https://ico.org.uk/... | Blocked | Unverified. |
| EDPB Guidelines 3/2019 on video devices | https://www.edpb.europa.eu/... | Blocked | Unverified. Highly relevant to video of people. |
| Netflix Cosmos media-processing platform | https://netflixtechblog.com/the-netflix-cosmos-platform-35c14d9351ad | Blocked | No verified FAANG video-pipeline architecture source. Pipeline design rests on 12-factor + OWASP + judgment. |
| Meta video-processing post | https://engineering.fb.com/2022/07/26/video-engineering/meta-video-processing/ | Blocked (URL also unconfirmed) | Dropped. |
| Uber reliable reprocessing / DLQ | https://www.uber.com/blog/reliable-reprocessing/ | Blocked | Dead-letter-queue pattern unverified. Treat as judgment. |
| Martin Fowler "Practical Test Pyramid" | https://martinfowler.com/articles/practical-test-pyramid.html | Blocked | Test-pyramid proportions unverified here. |
| TrackNet paper (arXiv 1907.03698) | https://arxiv.org/abs/1907.03698 | Blocked | Out of scope for this file. The CV research file should verify it. |

Other caveats:
- WebFetch content is summarised by a helper model. Requirement numbers (e.g. ASVS 5.2.2) and level tags should be spot-checked against the raw markdown before they go into contracts or external docs.
- google/eng-practices was archived (read-only) on 2025-11-21. The guidance is still published but no longer maintained.
- The OWASP Top 10:2025 category list was read from file names in the repo. Only A10:2025 was opened in full.
- No source in this file covers performance budgets for video processing, WCAG/accessibility, or DDD/TDD method. Those belong to other research files.
