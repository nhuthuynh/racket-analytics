# 0008. Stack confirmation for Sprint 0: keep the spec stack; Postgres-backed queue; Apache-licensed S3 store in dev; MIT/Apache test tooling

- **Status:** Accepted for Sprint 0. The CV/ML stack is **not** decided here; it waits for SPIKE-01 and OQ-12.
- **Date:** 2026-10-03
- **Deciders:** principal-engineer (architecture, R/A); engineering-manager (sprint plan)
- **Consulted:** sre-devops-engineer, senior-qa-engineer, senior-backend-engineer, senior-frontend-engineer, security-privacy-engineer (through `brainstorm-engineering.md` §1, §4.5, §8)
- **Related:** spec §3 "Stack (recommended)"; NFR-062, NFR-073, NFR-077, NFR-080, NFR-081; ADR 0007; SPIKE-01, SPIKE-09; stories ST-001..ST-011 (`docs/sprints/sprint-00.md`)

## Context and problem statement

Sprint 0 builds the repository, CI and the walking skeleton, so the stack must be fixed before day 1. The spec recommends FastAPI, Python workers, a Next.js PWA, Postgres, S3-compatible storage and "Redis or a Postgres-backed queue" (spec §3). It does not name the dev-time object store, the test and quality tooling, or how the code is laid out. NFR-062 forbids AGPL or non-commercial components in the product without an ADR. This ADR confirms the spec stack, settles the open choices Sprint 0 needs, and records the licence evidence we fetched.

## Decision drivers

- One backend language and shared domain models between API and workers (spec §3 rationale).
- Code organised by domain module; `def` routes unless fully async; no CPU/GPU work in the API process [AQS/STACK-01, AQS/STACK-02].
- Dev/prod parity: Postgres, an S3-compatible store and the same queue in dev; no SQLite [AQS/OPS-05].
- The queue backend must survive sudden process death; jobs are idempotent and requeued on SIGTERM [AQS/OPS-02].
- Lint and format with Ruff [AQS/STACK-05]; async test client and `dependency_overrides` [AQS/STACK-01]; Playwright E2E [AQS/STACK-03]; axe-core for accessibility [DPA/DESIGN-14].
- Resumable uploads follow tus 1.0.0 [AQS/STACK-06]. PWA needs manifest, service worker, HTTPS, security headers [AQS/STACK-04].
- Supply chain: no AGPL/non-commercial components without an ADR (NFR-062; [DOM/CV-05], [DOM/CV-07]).
- Start simple; avoid speculative over-engineering [EP/ENG-25, AQS/ENG-04].

## Considered options

**A. Overall stack**

1. **Keep the spec stack** (FastAPI API, Python workers in the same Python project, Next.js PWA, Postgres, S3-compatible storage).
2. Go API plus Python workers (the alternative the spec mentions).
3. Do nothing: let each story pick its tools.

**B. Job queue**

1. **Postgres-backed queue** (a job table claimed with `SELECT … FOR UPDATE SKIP LOCKED`, or a library built on that pattern), as ENG §1.1 proposes.
2. Redis-backed queue.

**C. S3-compatible object store for dev and CI**

1. MinIO.
2. **SeaweedFS S3 gateway**, with adobe/S3Mock as a fallback for unit-adjacent tests only.
3. A cloud bucket shared by developers.

**D. Load-test tool** (testing-strategy §2 named "k6/Locust (judgment)")

1. k6.
2. **Locust.**

## Decision outcome

**A: Option 1, keep the spec stack.** It satisfies every driver, and a second backend language before product-market fit adds cost without a requirement that needs it (spec §3; [EP/ENG-25]).

**B: Option 1, Postgres-backed queue (judgment), confirmed or reversed by SPIKE-09 inside story ST-007 in Sprint 0.** One fewer backing service, and the enqueue can share a transaction with the domain write (ENG §1.1). The candidate library `procrastinate` is MIT-licensed (fetched, below); whether it meets [AQS/OPS-02] (requeue on SIGTERM, survival of process death) is what SPIKE-09 tests. A hand-written `SKIP LOCKED` table is the fallback.

**C: Option 2, SeaweedFS for dev and CI (judgment).** MinIO's licence file is the GNU AGPL v3 (fetched, below). NFR-062 would need an ADR for it, and even for dev-only use the simpler course is an Apache-2.0 store. ST-001 must show that SeaweedFS supports what we use in production: multipart upload, presigned GET with expiry, and server-side delete. If it fails any of these, the SRE raises a superseding ADR (MinIO dev-only with a licence note, or a cloud test bucket).

**D: Option 2, Locust (judgment).** k6's licence file is the GNU AGPL v3 (fetched); Locust's is MIT. Testing-strategy §2 is amended by this ADR to "Locust".

**Further Sprint 0 choices (all judgment unless cited):**

| Area | Choice | Licence (fetched 2026-10-03 from the repo's LICENSE file) | Basis |
|---|---|---|---|
| API framework | FastAPI | MIT | spec §3; [AQS/STACK-01], [AQS/STACK-02] |
| ORM and migrations | SQLAlchemy 2 + Alembic, with **separate** Pydantic request/response schemas | SQLAlchemy and Alembic: MIT-style permission notice | (judgment): the FastAPI template uses SQLModel [AQS/STACK-03], but one class for table and API schema makes NFR-052's "responses built from explicit allowlist schemas" harder to guarantee, and keeps persistence out of domain objects (ddd-guidelines §4.5) |
| Postgres driver | psycopg 3 | LGPL-3.0 (used as an unmodified library; judgment, security-privacy-engineer to confirm in the NFR-062 licence check) | (judgment) |
| Python packaging | uv | MIT | (judgment) |
| Lint/format | Ruff | — | [AQS/STACK-05] |
| Type checking | mypy, strict on `scoring`, `analytics`, `coaching`, `sports/` | MIT | NFR-077 strict mode; tool choice (judgment) |
| Unit and API tests | pytest + httpx `ASGITransport` + `dependency_overrides` | — | [AQS/STACK-01] |
| BDD scenarios | pytest-bdd | MIT | testing-strategy §2 (judgment) |
| Property-based tests | Hypothesis | MPL-2.0 (test-only dependency, never shipped; judgment) | NFR-002; QD §2.3 |
| Integration backing services | Docker Compose services; testcontainers-python where a test needs an isolated instance | testcontainers-python: Apache-2.0 | [AQS/OPS-05]; testing-strategy §2 |
| Mutation testing | mutmut | BSD-style permission notice | NFR-072 (tool judgment) |
| Front end | Next.js PWA (App Router), TypeScript strict | Next.js: MIT | spec §3; [AQS/STACK-04] |
| Front-end unit tests | Vitest + Testing Library | Vitest: MIT | (judgment) |
| E2E and accessibility | Playwright + axe-core | Playwright: Apache-2.0; axe-core: MPL-2.0 (test-only) | [AQS/STACK-03], [DPA/DESIGN-14] |
| Resumable upload client | tus-js-client | MIT | [AQS/STACK-06] |
| Resumable upload server | **Open sub-decision for the Sprint 0 design review (ST-008):** tusd sidecar (MIT) or a tus 1.0.0 core implemented in FastAPI. Both must pass the upload-resume regression suite | tusd: MIT | [AQS/STACK-06] |
| Tracing and metrics | OpenTelemetry Python SDK, W3C Trace Context through the queue | Apache-2.0 | [AQS/OPS-06], [AQS/OPS-07] |
| Dev email (magic links, Sprint 1) | Mailpit in Compose | MIT | (judgment) |
| Secret scan | gitleaks | MIT | NFR-056 |
| Dependency audit | pip-audit; `npm audit` for the web app | pip-audit: Apache-2.0 | NFR-062 |
| SBOM | CycloneDX format (tool chosen in ST-002; licence checked at adoption) | not fetched | NFR-062 |
| Media probe | FFmpeg/ffprobe binaries, LGPL build only | FFmpeg: "Most files … LGPL v2.1 or later" per its LICENSE.md | ENG §1.2 stage 0; build flags (judgment; GPL components excluded) |
| CI | GitHub Actions | — | [AQS/STACK-03]; [DPA/AI-11] for the optional review bot |

**Code layout (judgment, consistent with [AQS/STACK-01] and ddd-guidelines §2):**

```
backend/                      one Python project; API and worker are two entry points
  src/racket_analytics/
    platform/                 config (env), logging, tracing, db, queue, storage, errors
    players/                  Identity & Players
    video_ingest/             Capture & Media
    analysis_jobs/            Vision Analysis, API side (job state machine)
    matches/                  Match & Scoring (aggregate, commands, corrections)
    scoring/                  application service around the rules engine
    sports/pickleball/        Sport Plug-in: rules/, court_model/, metrics/, drills/
    analytics/
    coaching/
    worker/                   worker entry point and stage registry
  tests/{unit,integration,features,regression,e2e_api}/
web/                          Next.js PWA; web/e2e/ holds Playwright journeys
infra/compose.yaml            Postgres, SeaweedFS, Mailpit, api, worker, web
fixtures/                     fixture clips and gold sets, each with manifest.json
.github/workflows/  .claude/settings.json  .claude/hooks/
```

**Explicitly not decided here:** player detector and tracker, pose model, ball tracker, GPU provider, LLM provider SDK details. These wait for SPIKE-01 (licence table), SPIKE-03/04 (cost) and OQ-12/OQ-13.

## Pros and cons of the options

### A1: spec stack
- Good: one backend language, shared domain models, verified best-practice sources for FastAPI and Next.js PWAs.
- Bad: Python API throughput is lower than Go (judgment); irrelevant at MVP load (NFR-010 targets 50 RPS).

### A2: Go API
- Good: matches another internal project's pattern (spec §3).
- Bad: a second backend language and duplicated domain models before product-market fit.

### A3: do nothing
- Bad: inconsistent tooling; CI gates cannot be written.

### B1: Postgres queue
- Good: one fewer service; transactional enqueue; adequate for MVP (ENG §1.1 estimates far below its limits, judgment).
- Bad: lock contention under heavy fan-out is untested; SPIKE-09 measures it.

### B2: Redis queue
- Good: widely used for job queues (judgment).
- Bad: another backing service in dev and prod; durability settings must be configured to meet [AQS/OPS-02].

### C1: MinIO
- Good: widely used S3-compatible store (judgment).
- Bad: AGPL-3.0 (fetched). Needs an NFR-062 licence ADR even if it never ships.

### C2: SeaweedFS
- Good: Apache-2.0 (fetched); runs in Compose.
- Bad: fewer team members know it (judgment); feature parity with the production store must be proven in ST-001.

### C3: shared cloud bucket
- Bad: breaks offline dev, adds a credential to every dev environment (NFR-056), and costs money.

### D1: k6 / D2: Locust
- k6: AGPL-3.0 (fetched). Locust: MIT (fetched). Both meet the performance test need; Locust avoids a licence ADR and is Python, like the backend.

## Consequences

- **Good:** Sprint 0 stories can name concrete files, tools and gates (DoR "names its files, interfaces and end-to-end verification step" [DPA/AI-08]).
- **Trade-offs accepted:** we depart from the FastAPI template's SQLModel choice [AQS/STACK-03] and from testing-strategy's "k6" mention.
- **Follow-up work:**
  - SPIKE-09 result is appended as a dated note here, or supersedes part B.
  - ST-001 confirms SeaweedFS parity; failure triggers a superseding ADR.
  - ST-008's design review records the tus server choice as ADR 0011.
  - SPIKE-01 produces the CV licence ADR before any R2 story is Ready.
  - security-privacy-engineer confirms the psycopg (LGPL-3.0) and FFmpeg (LGPL build) usage in the NFR-062 licence check during ST-002.

## Evidence

| Claim | Evidence | Type |
|---|---|---|
| Organise by domain module; CPU work out of the API; httpx async client and `dependency_overrides` | [AQS/STACK-01] | verified source |
| `def` routes unless every call is awaitable | [AQS/STACK-02] | verified source |
| FastAPI template: SQLModel, Postgres, Docker Compose, Pytest, Playwright, GitHub Actions | [AQS/STACK-03] | verified source |
| PWA manifest, service worker, HTTPS, security headers | [AQS/STACK-04] | verified source |
| Ruff replaces Flake8, Black, isort and more | [AQS/STACK-05] | verified source |
| tus 1.0.0: HEAD offset, PATCH, 409 on mismatch, checksum and expiration extensions | [AQS/STACK-06] | verified source |
| Dev/prod parity; disposability; config in env | [AQS/OPS-05], [AQS/OPS-02], [AQS/OPS-01] | verified source |
| W3C Trace Context propagation; OTel signals | [AQS/OPS-06], [AQS/OPS-07] | verified source |
| axe-core automated checks plus manual pass | [DPA/DESIGN-14] | verified source |
| Ultralytics AGPL-3.0 or Enterprise; BoxMOT AGPL-3.0 | [DOM/CV-05], [DOM/CV-07] | verified source |
| MinIO LICENSE is GNU AGPL v3 | fetched 2026-10-03: https://raw.githubusercontent.com/minio/minio/master/LICENSE | fetched in this ADR |
| k6 LICENSE.md is GNU AGPL v3 | fetched 2026-10-03: https://raw.githubusercontent.com/grafana/k6/master/LICENSE.md | fetched in this ADR |
| SeaweedFS Apache-2.0; S3Mock Apache-2.0 | fetched 2026-10-03: https://raw.githubusercontent.com/seaweedfs/seaweedfs/master/LICENSE ; https://raw.githubusercontent.com/adobe/S3Mock/main/LICENSE | fetched in this ADR |
| Locust MIT; procrastinate MIT; tusd MIT; tus-js-client MIT | fetched 2026-10-03: https://raw.githubusercontent.com/locustio/locust/master/LICENSE ; https://raw.githubusercontent.com/procrastinate-org/procrastinate/main/LICENSE.md ; https://raw.githubusercontent.com/tus/tusd/main/LICENSE.txt ; https://raw.githubusercontent.com/tus/tus-js-client/main/LICENSE | fetched in this ADR |
| FastAPI MIT; Next.js MIT; SQLAlchemy and Alembic MIT-style; psycopg LGPL-3.0 | fetched 2026-10-03: https://raw.githubusercontent.com/fastapi/fastapi/master/LICENSE ; https://raw.githubusercontent.com/vercel/next.js/canary/license.md ; https://raw.githubusercontent.com/sqlalchemy/sqlalchemy/main/LICENSE ; https://raw.githubusercontent.com/sqlalchemy/alembic/main/LICENSE ; https://raw.githubusercontent.com/psycopg/psycopg/master/LICENSE.txt | fetched in this ADR |
| pytest-bdd MIT; Hypothesis MPL-2.0; mutmut BSD-style; mypy MIT; uv MIT; testcontainers-python Apache-2.0 | fetched 2026-10-03: https://raw.githubusercontent.com/pytest-dev/pytest-bdd/master/LICENSE.txt ; https://raw.githubusercontent.com/HypothesisWorks/hypothesis/master/LICENSE.txt ; https://raw.githubusercontent.com/boxed/mutmut/main/LICENSE ; https://raw.githubusercontent.com/python/mypy/master/LICENSE ; https://raw.githubusercontent.com/astral-sh/uv/main/LICENSE-MIT ; https://raw.githubusercontent.com/testcontainers/testcontainers-python/main/LICENSE.txt | fetched in this ADR |
| Playwright Apache-2.0; axe-core MPL-2.0; Vitest MIT; OpenTelemetry Python Apache-2.0 | fetched 2026-10-03: https://raw.githubusercontent.com/microsoft/playwright/main/LICENSE ; https://raw.githubusercontent.com/dequelabs/axe-core/develop/LICENSE ; https://raw.githubusercontent.com/vitest-dev/vitest/main/LICENSE ; https://raw.githubusercontent.com/open-telemetry/opentelemetry-python/main/LICENSE | fetched in this ADR |
| gitleaks MIT; pip-audit Apache-2.0; Mailpit MIT | fetched 2026-10-03: https://raw.githubusercontent.com/gitleaks/gitleaks/master/LICENSE ; https://raw.githubusercontent.com/pypa/pip-audit/main/LICENSE ; https://raw.githubusercontent.com/axllent/mailpit/develop/LICENSE | fetched in this ADR |
| FFmpeg: most files LGPL v2.1+ | fetched 2026-10-03: https://raw.githubusercontent.com/FFmpeg/FFmpeg/master/LICENSE.md | fetched in this ADR |
| Licence *interpretations* (test-only MPL use, unmodified LGPL library use) | (judgment); security-privacy-engineer to confirm; legal review is not in our research [AQS Gaps] | judgment |
| Postgres queue adequacy; SeaweedFS parity | (judgment) until SPIKE-09 and ST-001 produce data | judgment |
| Test results | Not applicable: no code yet | — |

Note: the GitHub REST API was not reachable from this session, so star counts for the newly named tools were not captured. Only the licence files listed above were fetched.

## Confirmation

- ST-001 demo: `docker compose up` brings up every service in the layout above; the SeaweedFS parity checks pass.
- ST-002: CI runs every tool named above; the licence check passes with no AGPL or non-commercial package in the shipped dependency graph.
- SPIKE-09 numbers are appended as a dated note.

## Notes

- **2026-10-03 (senior-qa-engineer, ST-004):** The backend scaffold uses the import package `racket` (`backend/src/racket/...`), not `racket_analytics` as in the code-layout sketch above. The Sprint 0 task brief named `racket` for every lane. The distribution name stays `racket-analytics` in `backend/pyproject.toml`. The context sub-packages follow the layout above (`platform`, `players`, `video_ingest`, `analysis_jobs`, `matches`, `scoring`, `sports/pickleball`, `analytics`, `coaching`, `worker`), plus `dataset` for the proposed dataset context in sprint-00 §5 (ManifestCheck). Only the top-level name changes, so this is a dated note and not a superseding ADR (judgment). The principal-engineer may promote it to an ADR. Evidence: `cd backend && uv run mypy` → `Success: no issues found in 16 source files`.
- **2026-10-03 (senior-qa-engineer, IT-00-16):** Part C parity, locally without Docker. `scripts/dev-objectstore.sh start` (SeaweedFS 3.97, sha256-pinned by the SRE) followed by `cd backend && uv run pytest tests/integration/test_it_00_16_object_store_parity.py -v` → `4 passed`: multipart upload round trip (5 MiB + 1 KiB parts, sha256 equal), presigned GET works and then returns 403 after expiry (2 s TTL, checked at 3.5 s), a tampered presigned URL returns 403, and delete leaves HEAD at 404. No MinIO or moto fallback was needed. The Compose run in CI still has to confirm this (ST-001).

- **2026-10-03 (sre-devops-engineer, ST-001): part C confirmed. SeaweedFS 3.97 passes the parity checks; no superseding ADR needed.**
  - **Scope:** `infra/tests/test_object_store_parity.py` (IT-00-16) ran against two real SeaweedFS 3.97 servers, with no mocks:
    - the local binary launched by `scripts/dev-objectstore.sh`: release `linux_amd64.tar.gz`, sha256 `a5b73384efb1b3848e8ba464420475b2e0c12c17c32d7939546cd496728849a7`;
    - the Compose service `chrislusf/seaweedfs:3.97`.
  - **Results:** 7 passed on each, covering multipart upload (3 parts, sha256 round-trip), multipart abort, presigned GET that works and then returns 403 after expiry, a tampered presigned URL refused with 403, delete then 404, and a wrong secret refused with 403.
  - **Commands:**
    - `cd infra && uv run pytest -q tests/test_dev_postgres.py tests/test_object_store_parity.py` → `14 passed in 36.49s`;
    - `S3_ENDPOINT_URL=http://127.0.0.1:58333 ... uv run pytest -q tests/test_object_store_parity.py` → `7 passed in 5.09s`.
  - **Fallback not needed:** the brief's moto fallback was not needed, because the SeaweedFS binary downloaded from GitHub releases and its image pulled via `mirror.gcr.io` (Docker Hub answered 429).
  - **Caveat:** server-side encryption, object lock and lifecycle rules were not tested. They are not used in Sprint 0.

- **2026-10-03 (principal-engineer):** The open "Resumable upload server" row is decided by ADR 0011: a tus 1.0.0 core inside the FastAPI app, not a tusd sidecar. The reasons are that tusd has no blocking hook on HEAD/PATCH for per-request BOLA, its `post-finish` enqueue is non-blocking, and its S3 locking is per-process. The evidence is the tusd docs fetched and hashed in ADR 0011. tusd is not adopted, so its MIT licence entry stays informational.

- **2026-10-03 (senior-backend-engineer, SPIKE-09 / ST-007): part B confirmed (Postgres queue); the library question goes to the hand-written fallback, see ADR 0017.**
  - **Setup:** the production code path (`JobQueue.claim` + commit, then `lock_running` + `complete` + commit, as `racket.worker.runner` does), 4 worker processes, 1,000 pre-enqueued jobs, local Postgres 16.14 from `scripts/dev-postgres.sh` (fsync off, shared dev container with other lanes running). Script: `backend/tests/perf/spike_09_queue_claim.py`.
  - **Command:** `cd backend && uv run python -m tests.perf.spike_09_queue_claim --workers 4 --jobs 1000 [--work-ms 5]`.
  - **Claim throughput (no-op stage), 4 runs:** 888.1, 888.2, 681.4 and 504.2 jobs/s. Claim latency p50 2.17-2.76 ms, p95 3.49-6.68 ms, p99 8.21-14.26 ms, max 37-69 ms.
  - **With a 5 ms stage:** 401.0 jobs/s; p50 2.46 ms, p95 3.33 ms, p99 5.35 ms; jobs per worker 249/250/251/250.
  - **Lock contention:** 0 empty claims while work remained (SKIP LOCKED never starved a worker). `pg_stat_activity` sampled every 5 ms showed `Lock`/`transactionid` waits in 6-10 % of samples with the no-op stage (at most 3 waiting backends) and none with the 5 ms stage. Likely cause (judgment): rows locked by a `SKIP LOCKED` scan and then dropped by the re-check stay locked until that claim commits, so a concurrent `lock_running` waits for it briefly.
  - **Correctness:** every run ended with 1,000/1,000 jobs `done` at `attempts = 1`; no job was claimed twice.
  - **Reading:** the MVP load (ENG §1.1) is orders of magnitude below 500 claims/s, so lock contention is not a risk for R1 (judgment). Re-measure if fan-out per match grows past ~100 stages or workers past ~32.
  - **procrastinate:** not adopted. Its SIGTERM behaviour waits for running jobs instead of requeueing, SIGKILLed jobs need an app-defined periodic retry task, and queueing locks only hold while a job is queued (docs fetched and hashed in ADR 0017, E1-E3).
