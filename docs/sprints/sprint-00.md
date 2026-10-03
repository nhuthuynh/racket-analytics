# Sprint 0: Foundations and walking skeleton

- **Dates:** Mon 2026-10-05 → Fri 2026-10-16 (2 weeks, working-agreement §3)
- **Planning:** 2026-10-05 · **Sprint review:** 2026-10-16 · **Retrospective:** 2026-10-16
- **Retro file:** `docs/retros/2026-10-16-sprint-00.md`, copied from [`docs/retros/TEMPLATE.md`](../retros/TEMPLATE.md). Format: **Timeline**. Focus area: **tooling, hooks and the auto-review loop** [EP/ENG-15].
- **Status:** Planned (engineering-manager, with principal-engineer and senior-qa-engineer)
- **Release:** R1 "walking skeleton" (ADR 0002, Proposed). Sprint 0 is valid under every option of ADR 0002 (ADR 0007).
- **Progress and status:** `docs/sprints/00/progress.md` and `docs/sprints/00/status.json` [EP/ENG-28]. This file is the sprint plan.
- **Related ADRs:** 0001, 0007 (sequencing), 0008 (stack), 0010 (capacity). Citation prefixes: `docs/process/working-agreement.md` §0.

## 1. Sprint goal

- Running one Compose command brings up the API, worker, web app, Postgres, the S3-compatible store and Mailpit, with the same backing services as production [AQS/OPS-05].
- Every PR runs the CI gates (lint, types, unit, integration, scenario, E2E with axe, secret, dependency and licence scans, coverage). A red gate blocks the merge.
- The walking skeleton works end to end. A dev-seeded user creates a match and uploads the 60-second fixture clip through tus. A worker probes the clip, and the match page shows its duration, frame rate and resolution. One trace covers API → queue → worker [AQS/OPS-06].
- The mandatory regression-suite scaffolds exist and pass: BOLA (match), error bodies, malformed `traceparent`, worker crash and requeue, fail closed, and the tus offset-mismatch 409 [testing-strategy §5].
- Agent hooks format and lint on every edit, block writes to secret paths and run unit tests before a turn ends [DPA/AI-10].
- Sprint 1 stories are Ready: Big Picture EventStorming, context canvases, threat model v0, and design flows for sign-in, setup and upload.

**What we will demo:** the walking skeleton, a red CI gate blocking a bad PR, and a hook blocking a secret write (§9).

**Not in this sprint:** real sign-in (Sprint 1), match setup with participants (Sprint 1), upload validation and resume UI (Sprint 1), the rules engine (Sprint 1), any CV model.

## 2. Capacity (ADR 0010)

Load factor 70%: 16 units per lane × 0.7 = **11.2 units per lane**. Sizes: XS 0.5 · S 1 · M 2 · L 4.

| Lane | Committed units | Capacity | Notes |
|---|---|---|---|
| sre-devops-engineer (SRE) | 8 | 11.2 | Two streams: environment and CI; hooks |
| senior-backend-engineer (BE) | 8 | 11.2 | Two streams: platform and match; queue and upload |
| senior-frontend-engineer (FE) | 4 | 11.2 | One stream; slack is for ST-010 integration with BE contracts |
| senior-qa-engineer (QA) | 5 | 11.2 | Writes acceptance tests before implementation [DPA/AI-08] |
| senior-ml-cv-engineer (ML) | 3 | 11.2 | Probe stage and SPIKE-01 |
| **Total** | **28** | 56 | Deliberately light; foundations overrun (judgment) |

## 3. Committed backlog

Story IDs are new (traceability-matrix §5 gap 2). Each story's Gherkin is in §7, and its file is `tests/features/<file>.feature`.

| Story | Title | FR / NFR | Owner (R) | Required reviewers (working-agreement §6) | Size | Depends on |
|---|---|---|---|---|---|---|
| ST-001 | Dev environment with production parity | NFR-080, NFR-081 | SRE | principal-engineer, security-privacy-engineer | M | — |
| ST-002 | CI pipeline and merge gates | NFR-015, NFR-024 (matrix skeleton), NFR-027 (axe job), NFR-056, NFR-062, NFR-071, NFR-073, NFR-074, NFR-077 | SRE | QA, security-privacy-engineer | L | ST-001 |
| ST-003 | Agent hooks and test-immutability guard | NFR-078 (tests), working-agreement §7.1 | SRE | security-privacy-engineer, QA | M | ST-002 |
| ST-004 | Test harness, tags and test-data builders | NFR-073, NFR-075 (harness); QD-TR-01..03 | QA | principal-engineer, BE | M | ST-001 |
| ST-005 | API skeleton: health, errors, headers, logs, tracing | NFR-058, NFR-061 (API), NFR-069, NFR-076, NFR-081 | BE | QA, principal-engineer, security-privacy-engineer | M | ST-001, ST-004 |
| ST-006 | Ownership seam, minimal `Match` aggregate and BOLA matrix | FR-002 (match), NFR-051, NFR-052, NFR-057 (authz failures), NFR-064 | BE | QA, principal-engineer, security-privacy-engineer | M | ST-005 |
| ST-007 | Postgres-backed job queue and worker, including SPIKE-09 | FR-080 (queue base), NFR-046, NFR-047, NFR-076 (queue propagation) | BE | QA, principal-engineer, sre-devops-engineer | M | ST-005 |
| ST-008 | tus core upload into object storage (creation, HEAD, PATCH, 409) | FR-022 (core), NFR-026 (core), NFR-053 (generated keys), NFR-060 | BE | QA, principal-engineer, security-privacy-engineer | M | ST-006, ST-007 |
| ST-009 | Media probe stage in a sandboxed worker | FR-081 (probe), FR-025 (facts), NFR-025 (fixtures), NFR-054 | ML | QA, BE peer, security-privacy-engineer | M | ST-007, ST-011 |
| ST-010 | PWA shell and walking-skeleton screens | NFR-015, NFR-027, NFR-029 (tokens), NFR-061 (client), NFR-067 (baseline) | FE | QA, principal-designer, security-privacy-engineer | L | ST-005, ST-008 |
| ST-011 | Synthetic fixture clip and gold-set manifest check | FR-151 (manifest check), NFR-078 (gold) | QA (with ML) | ML peer, sre-devops-engineer | S | ST-002 |
| ST-012 | Acceptance scenarios and regression-suite scaffolds, written first | testing-strategy §5 suites: BOLA, error bodies, trace header, worker crash, fail closed, upload resume (core) | QA | principal-engineer, security-privacy-engineer | M | ST-004 |
| SPIKE-01 | CV licence posture: MIT/Apache-only vs Ultralytics Enterprise | NFR-062; OQ-12 | ML (with principal-engineer) | principal-engineer, security-privacy-engineer | S (2 days) | — |

**Stretch (not committed):** none. Slack goes to fixing the first red-gate findings (judgment).

### 3.1 Acceptance notes per story (beyond the Gherkin in §7)

- **ST-001:** `infra/compose.yaml` runs Postgres, SeaweedFS (ADR 0008), Mailpit, `api`, `worker` and `web`. All configuration comes from environment variables, and the API refuses to start when a required variable is missing [AQS/OPS-01]. No SQLite anywhere [AQS/OPS-05]. A parity script shows SeaweedFS handles multipart upload, presigned GET with expiry, and delete; if not, the SRE raises a superseding ADR.
- **ST-002:** GitHub Actions jobs: `ruff check` and `ruff format --check` [AQS/STACK-05]; `mypy` (strict on `scoring`, `analytics`, `coaching`, `sports/`); unit tests with a time budget (NFR-073: domain suite < 10 s, backend unit suite ≤ 60 s); integration tests on Compose (< 10 min); pytest-bdd scenarios; ESLint, `tsc --noEmit` and Vitest; Playwright with axe-core (0 serious or critical violations, NFR-027); first-route JS ≤ 200 KB gzipped (NFR-015); gitleaks; pip-audit and `npm audit`; CycloneDX SBOM; a licence check that fails on AGPL or non-commercial packages in the shipped graph (NFR-062); a coverage gate on changed lines (testing-strategy §8); a flaky-test report (NFR-074). The Playwright config has Chromium and WebKit projects as the skeleton of the NFR-024 browser matrix.
- **ST-003:**
  - `.claude/settings.json` hooks [DPA/AI-10]: PostToolUse runs `ruff format` and `ruff check --fix` (Python) or ESLint `--fix` (TypeScript) on the edited file. PreToolUse blocks writes to `.env*`, `**/*.pem`, `**/*.key` and `infra/secrets/**`, and appends every Bash command to an audit log. Stop runs the unit suite and blocks the end of the turn on failure.
  - A CI job fails any PR that modifies or deletes files under `backend/tests/`, `web/e2e/` or `fixtures/gold/` unless the PR carries the `qa-approved-test-change` label applied by the senior-qa-engineer [EP/ENG-28]. The label mechanism is (judgment).
- **ST-004:** pytest markers `unit`, `integration`, `scenario`, `slow`, `needs_verification`; pytest-bdd maps Gherkin tags `@needs-verification`, `@M0`, `@story-ST-nnn`, `@nfr-nnn` (testing-strategy §4); a Hypothesis profile `ci` with ≥ 1,000 examples; an httpx `ASGITransport` client fixture with `dependency_overrides` [AQS/STACK-01]; transaction-rollback DB fixtures on the Compose Postgres; a Playwright project with an axe helper; a test-report script that lists `@needs-verification` scenarios separately (QD-QG-P5). Builder skeletons: `a_match()`, `an_owner()` (QD-TR-03).
- **ST-005:** `GET /healthz` (liveness) and `GET /readyz` (DB, store and queue reachable). One central exception handler plus a global fallback return `{"error": {"code", "message", "support_ref"}}` with no stack trace or internals (NFR-058) [AQS/SEC-04] [AQS/SEC-12]. Security headers `nosniff`, `X-Frame-Options: DENY` and `Cache-Control: no-store` on authenticated JSON (NFR-061, NFR-067). JSON logs to stdout with UTC timestamp, `trace_id`, `request_id`, pseudonymous `user_id` (NFR-076b) [AQS/OPS-03]. OpenTelemetry tracing with W3C Trace Context [AQS/OPS-06]. Settings are logged at startup with secrets redacted [EP/ENG-20].
- **ST-006:** A dev/test-only identity provider (seeded users "ivy" and "carlos"). The API refuses to start with it enabled when `APP_ENV=prod` (security-privacy-engineer must confirm). `POST /matches`, `GET /matches`, `GET /matches/{id}` with UUIDv4 IDs [AQS/SEC-09]. Every ID route loads through an ownership dependency and returns the same 404 for "not yours" and "does not exist" [AQS/STACK-01 G7.5; AQS/SEC-03]. Authorisation failures are security-logged without personal data. An endpoint-inventory test lists every route with a path ID and fails if a route is missing from the BOLA matrix (NFR-051). Response models are explicit allowlists; unknown request fields are rejected (NFR-052).
- **ST-007:** Job table keyed uniquely by `(match_id, pipeline_version, stage)` [AQS/OPS-02]. Worker claims with `SKIP LOCKED` or the library chosen in SPIKE-09 (ADR 0008 part B). SIGTERM returns the in-flight job to the queue within 10 s (NFR-046b). A failing stage rolls back its writes and marks the job `failed` (NFR-047) [AQS/SEC-12]. The trace context is injected on enqueue and extracted in the worker [AQS/OPS-06]. SPIKE-09 (2 days) records claim throughput and lock contention for 4 workers × 1,000 jobs as a dated note on ADR 0008.
- **ST-008:** The principal-engineer holds a design review on day 2 (tusd sidecar or FastAPI tus core) and records ADR 0011. Required behaviours [AQS/STACK-06]: `POST` creation with `Upload-Length`; `HEAD` returns `Upload-Offset`; `PATCH` from the offset; 409 on offset mismatch with the upload unchanged. Object keys are generated server-side and never derived from user input [AQS/SEC-02 5.3.2]. The probe job is enqueued only after the final byte is stored (NFR-060) [AQS/SEC-07 2.3.1]. Checksum and expiration extensions, validation and the resume UI come in Sprint 1.
- **ST-009:** Stage 0 of ENG §1.2. It runs `ffprobe` on a presigned URL and records container, codec, fps, VFR flag, duration and audio presence as `MediaAsset` facts. The worker container has no network route except the object store, has CPU, memory and wall-clock limits, and never passes user-supplied filenames to tools (NFR-054) [AQS/SEC-06 13.2.4] [AQS/SEC-10]. The worker logs tool versions at startup [EP/ENG-20].
- **ST-010:** Next.js App Router PWA with `app/manifest.ts`, a service worker that never caches media or authenticated responses, HTTPS in dev, and CSP, `nosniff` and `X-Frame-Options: DENY` [AQS/STACK-04]. Design tokens from the principal-designer meet 4.5:1 text and 3:1 non-text contrast (NFR-029) [DPA/DESIGN-03, DPA/DESIGN-04]. Screens: dev sign-in picker; matches list with empty state; "New match" (title and format only); upload with % and MB progress (tus-js-client); match detail with status and probe facts. Every screen has empty, loading and error states (DoD UI).
- **ST-011:** `fixtures/clips/synthetic-60s/` is generated by a committed script that uses FFmpeg test patterns and tone bursts: 60 s, 1920×1080 at 60 fps, AAC audio, no people, so there is no consent issue. Its `manifest.json` follows QD §8 (id, version, sha256 per file, licence, consent status "synthetic"). CI fails when a file's sha256 differs from the manifest without a version bump (FR-151, NFR-078).
- **ST-012:** QA writes the §7 scenarios and the regression-suite skeletons **before** ST-005..ST-009 start. The suites fail red first, and the implementing stories turn them green [DPA/AI-08, EP/ENG-18].
- **SPIKE-01:** a licence table for every candidate model, weight and dataset in DOM (CV-01..CV-19) and ENG §8, with "usable in product / eval only / needs ADR". Output: ADR "CV licence posture" for the PO (OQ-12) [DOM/CV-05, DOM/CV-07, DOM/CV-09].

## 4. Task breakdown per role agent

Implementation lanes carry the stories above. Docs roles carry dated tasks; "D3" means sprint day 3.

| Agent | Tasks this sprint | Due | Done-check |
|---|---|---|---|
| engineering-manager | Create `docs/sprints/00/progress.md` and `status.json`; brief each agent with objective, output, tools, boundaries and done-check [EP/ENG-26]; run the review loop and escalations; collect DORA and PR metrics; facilitate the retro | D1, daily, D10 | Every story has an owner and reviewer; retro file has owned, dated actions |
| product-manager | Send the PO the escalation pack (§10) with need-by dates; ask the PO to ratify ADRs 0001, 0002, 0007, 0009 at the review | D2 | Pack sent; answers logged as ADR notes |
| business-analyst | Write Sprint 1 stories (ST-013..ST-025) with Gherkin, NFR links and the (a)/(b) split for rules stories (ADR 0009); update the traceability matrix with test files as they land | D8 | Sprint 1 stories pass the DoR checklist |
| principal-engineer | Run Big Picture EventStorming [EP/ENG-14] and write `docs/architecture/contexts/*.md` canvases [EP/ENG-12] and the context map [EP/ENG-13], deciding ENG §2 C1-C4; update the "Point leak" glossary entry per ADR 0003; ST-008 design review (ADR 0011); review SPIKE-01 and SPIKE-09; start the `Match` aggregate design doc for Sprint 2 | D2 (review), D6, D10 | Canvases merged; ADR 0011 written |
| principal-designer | Design tokens and the component accessibility checklist; flows with every state for sign-in, first run, capture guide, setup and upload (Sprint 1 DoR) [DPA/DESIGN-12, DPA/DESIGN-13]; review ST-010 | D4, D8 | Flows include empty, loading, error states; WCAG 2.2 AA checklist done |
| security-privacy-engineer | Threat model v0 for upload, auth, media URLs and the worker sandbox; ASVS 5.0 L2 checklist skeleton (NFR-050) [AQS/SEC-01]; confirm licence interpretations in ADR 0008; review ST-001..ST-009 | D5, ongoing | Threat model attached to Sprint 1 security stories (DoR) |
| pickleball-domain-coach | Create `docs/domain/rules-verified.md` (empty table: rule, edition, number, wording); draft capture-guide wording (FR-020); draft metric-dictionary entries AN-01..AN-07 (status `draft`) | D5, D9 | Files exist; nothing marked verified without a rule number [DOM G1] |
| sre-devops-engineer | ST-001, ST-002, ST-003 | D3, D7, D8 | §8 gates run on a sample PR |
| senior-backend-engineer | ST-005, ST-006, ST-007 (+SPIKE-09), ST-008 | D4, D6, D7, D9 | Scenarios in §7 green with evidence |
| senior-ml-cv-engineer | SPIKE-01; ST-009; help QA with ST-011 | D3, D9 | Licence ADR drafted; probe scenario green |
| senior-frontend-engineer | ST-010 | D9 | Playwright walking-skeleton journey and axe green |
| senior-qa-engineer | ST-004, ST-011, ST-012; Sprint 0 test report; verify the sprint DoD | D3, D4, D10 | Test report lists every suite, its counts and the command used |

## 5. TDD plan (red → green → refactor, negative case first) [EP/ENG-18]

Unit tests use no I/O, sleeps or network, and run in milliseconds [EP/ENG-17]. The order is the order in which the first failing tests are written.

| Domain object / unit | Context | First tests, in order |
|---|---|---|
| `Settings` | platform | 1. missing required variable → startup error naming the variable; 2. `APP_ENV=prod` with the dev identity provider enabled → startup error; 3. secrets are redacted in the startup log line |
| `ErrorMapper` | platform | 1. unknown exception → generic 500 body with `support_ref` and no stack trace; 2. domain `NotFound` → 404 generic body; 3. validation error → 422 without echoing secrets |
| `MatchId`, `OwnerId` | matches | 1. non-UUID input rejected; 2. generated IDs are UUIDv4 |
| `Match` (aggregate root, minimal) | matches | 1. creating without an owner fails; 2. unknown format fails; 3. a new match has status `awaiting_upload`; 4. `mark_uploaded(media_id)` twice fails; 5. `can_be_read_by(other_owner)` is false |
| `JobKey` | analysis_jobs | 1. two keys with the same `(match_id, pipeline_version, stage)` are equal; 2. a different stage gives a different key |
| `Job` state machine | analysis_jobs | 1. `complete` from `queued` fails (must be `running`); 2. `fail` from `running` → `failed` with reason; 3. `requeue` from `running` → `queued` with attempt + 1; 4. `complete` twice is idempotent |
| `UploadSession` | video_ingest | 1. PATCH with offset ≠ current offset → `OffsetMismatch`, state unchanged; 2. PATCH beyond `Upload-Length` → error; 3. PATCH at the right offset advances it; 4. `is_complete` only when offset equals length |
| `ObjectKeyPolicy` | video_ingest | 1. user filename never appears in the key; 2. keys are unique per call |
| `MediaFacts.from_ffprobe` | video_ingest | 1. JSON with no video stream → `NotAVideo`; 2. missing duration → error; 3. `r_frame_rate` ≠ `avg_frame_rate` → `vfr = True`; 4. a 1080p60 fixture JSON → expected facts |
| `ManifestCheck` | dataset (proposed context) | 1. file sha256 differs from manifest → failure naming the file; 2. extra file not in the manifest → failure; 3. matching set → pass |

Front-end (Vitest): `formatBytes`/`formatDuration` (1. negative input rejected; 2. human units), upload progress reducer (1. offset regression is ignored; 2. % never exceeds 100).

## 6. Integration tests

Integration tests run against the real Compose services, never SQLite [AQS/OPS-05]; API tests use the httpx async client with `dependency_overrides` [AQS/STACK-01].

| ID | Boundary | Test | Story |
|---|---|---|---|
| IT-00-01 | API ↔ Postgres | Create, get and list a match; list returns only the caller's matches | ST-006 |
| IT-00-02 | API ↔ Postgres | BOLA matrix: user B gets 404 on every ID route of user A; endpoint-inventory diff is empty | ST-006 |
| IT-00-03 | Queue ↔ worker | Enqueue, claim, complete; a second claim of the same key does nothing | ST-007 |
| IT-00-04 | Queue ↔ worker | Kill the worker mid-stage; the job is requeued within 10 s; the re-run leaves no duplicate rows | ST-007 |
| IT-00-05 | Worker ↔ Postgres | A stage that raises after a partial write leaves no rows and marks the job `failed` | ST-007 |
| IT-00-06 | API ↔ object store | tus creation, HEAD, PATCH in 3 chunks, final object sha256 equals the source | ST-008 |
| IT-00-07 | API ↔ object store | PATCH with a wrong offset → 409; HEAD afterwards returns the unchanged offset | ST-008 |
| IT-00-08 | API ↔ queue | No probe job exists until the final byte is stored | ST-008 |
| IT-00-09 | Worker ↔ object store | Probe stage on the synthetic fixture records 60 s, 60 fps, 1920×1080, audio present | ST-009 |
| IT-00-10 | Worker sandbox | From inside the worker container, a request to a public host fails; the object store succeeds | ST-009 |
| IT-00-11 | API → queue → worker | One trace ID appears on the API span, the enqueue span and the worker span (in-memory exporter) | ST-005, ST-007 |
| IT-00-12 | API | A malformed `traceparent` header still gets a 2xx and a new trace | ST-005 |
| IT-00-13 | API | Forced exceptions return the generic error body only | ST-005 |
| IT-00-14 | API | Security headers are present on HTML, JSON and error responses | ST-005, ST-010 |
| IT-00-15 | Logs | Log scanner over the integration run finds no email address, nickname or signed URL (NFR-069) | ST-005 |
| IT-00-16 | Object store parity | Multipart upload, presigned GET that expires, delete (ADR 0008 part C) | ST-001 |

**E2E (Playwright, on merge to `main` and nightly):** E2E-00-01 walking skeleton: dev sign-in → new match → upload synthetic fixture → match page shows "Duration 1:00 · 60 fps · 1920×1080", with axe run on every page.

## 7. Gherkin scenarios

Declarative, about 3-5 steps, observable `Then` [DPA/PROD-01, DPA/PROD-02]. Background is at most about 4 lines. "Ivy" and "Carlos" are the dev-seeded users.

```gherkin
# tests/features/walking_skeleton.feature
@M0 @story-ST-008 @story-ST-009 @story-ST-010
Feature: Walking skeleton from upload to media facts
  A signed-in player can upload a match video and see what the system learned about the file.

  Background:
    Given Ivy is signed in

  Rule: A completed upload is probed and its facts are shown on the match

    Scenario: Upload the fixture clip and see its facts
      Given Ivy has created a match called "Skeleton test"
      When she uploads the 60-second synthetic fixture clip to that match
      Then the match shows the status "Video received"
      And the match shows duration "1:00", frame rate "60 fps" and resolution "1920×1080"

    Scenario: No probing before the upload is complete
      Given Ivy's upload to match "Skeleton test" is 50% done
      When she opens the match
      Then the match shows the status "Uploading"
      And no media facts are shown
```

```gherkin
# tests/features/object_level_authorisation.feature
@M0 @story-ST-006 @nfr-051 @nfr-064
Feature: Object-level authorisation for matches
  Every resource ID is checked against its owner.

  Rule: Another user cannot see or change my match

    Scenario Outline: Carlos tries to use Ivy's match
      Given Ivy owns a match
      When Carlos tries to <action> that match by its ID
      Then Carlos gets the same "not found" result as for a match that does not exist
      And the attempt appears in the security log without Ivy's details
      Examples:
        | action       |
        | open         |
        | upload to    |
        | see facts of |

    Scenario: My match list shows only my matches
      Given Ivy owns 2 matches and Carlos owns 1 match
      When Carlos opens his matches list
      Then he sees exactly 1 match

  Rule: Every route that takes an ID is covered by the BOLA matrix

    Scenario: A new route without BOLA coverage
      Given a route that takes a match ID is added without a BOLA matrix entry
      When the regression suite runs
      Then the suite fails and names the uncovered route
```

```gherkin
# tests/features/upload_resume_core.feature
@M0 @story-ST-008 @nfr-026
Feature: Resumable upload protocol core
  Uploads follow tus 1.0.0 so that a client can always find where to resume.

  Rule: The server reports the stored offset and refuses mismatched chunks

    Scenario: Resume from the server's offset
      Given Ivy has started an upload and the server has stored 40% of it
      When her client asks the server for the current offset
      Then the server reports the offset at 40%
      And sending the rest from that offset completes the upload

    Scenario: Chunk sent from the wrong offset
      Given the server has stored 40% of Ivy's upload
      When her client sends a chunk that starts at 30%
      Then the chunk is refused as a conflict
      And the stored upload is still at 40%

    Scenario: Stored names never come from the user's file name
      Given Ivy uploads a file named "../../etc/passwd.mp4"
      When the upload completes
      Then the stored object name contains none of the original file name
```

```gherkin
# tests/features/job_resilience.feature
@M0 @story-ST-007 @nfr-046 @nfr-047
Feature: Analysis jobs survive worker failure without leaving partial results
  Workers are disposable; jobs are idempotent and fail closed.

  Rule: A job interrupted by a worker shutdown is retried exactly once more

    Scenario: Worker stops in the middle of probing
      Given a probe job is running for Ivy's match
      When the worker is told to shut down
      Then the job is back in the queue within 10 seconds
      And after it runs again the match has exactly one set of media facts

  Rule: A failing stage leaves nothing behind

    Scenario: Probe stage fails after writing part of its result
      Given the probe stage will fail after writing part of its result
      When the job runs
      Then the job is marked failed
      And the match shows no media facts
      And the match shows "We could not read this video"
```

```gherkin
# tests/features/errors_and_tracing.feature
@M0 @story-ST-005 @nfr-058 @nfr-076
Feature: Safe errors and end-to-end tracing

  Rule: Error responses never reveal internals

    Scenario: An unexpected server error
      Given the match service fails unexpectedly
      When Ivy opens one of her matches
      Then she gets a generic error with a support reference
      And the response contains no stack trace, query or internal identifier

  Rule: A request can be followed from the API to the worker

    Scenario: One trace covers upload to probe
      Given tracing is enabled
      When Ivy completes an upload and the probe job runs
      Then the API request, the enqueue and the probe stage share one trace ID

    Scenario: A malformed trace header is ignored safely
      Given a request carries a malformed "traceparent" header
      When the request reaches the API
      Then the request succeeds
      And it is recorded under a new trace
```

```gherkin
# tests/features/gold_set_integrity.feature
@M0 @story-ST-011 @nfr-078
Feature: Fixture and gold-set integrity
  Nobody edits a gold set or fixture to make a test pass.

  Rule: Every frozen file matches its manifest

    Scenario: A fixture file changes without a new version
      Given the synthetic fixture set version 1 is frozen
      When one of its files changes and the version stays the same
      Then the integrity check fails and names the changed file

    Scenario: An unlisted file is added
      Given the synthetic fixture set version 1 is frozen
      When a file that is not in its manifest is added to the set
      Then the integrity check fails and names the unlisted file
```

```gherkin
# tests/features/dev_environment.feature
@M0 @story-ST-001 @nfr-080 @nfr-081
Feature: Development environment matches production's backing services

  Rule: Configuration comes only from the environment

    Scenario: A required setting is missing
      Given the database address is not set
      When the API starts
      Then it refuses to start and names the missing setting

    Scenario: Development identities cannot run in production
      Given the environment is production and the development sign-in is enabled
      When the API starts
      Then it refuses to start and says development sign-in is not allowed
```

## 8. Quality gates

Per PR (blocking; hooks and CI, working-agreement §7.1):

| Gate | Threshold | Source |
|---|---|---|
| Ruff lint and format; mypy strict on domain modules; ESLint and `tsc` | 0 errors | [AQS/STACK-05]; NFR-077 |
| Unit suites | 100% pass; domain suite < 10 s; backend unit suite ≤ 60 s | [EP/ENG-17]; NFR-073 |
| Integration and scenario suites on Compose | 100% pass; < 10 min | [EP/ENG-20]; NFR-073 |
| Mandatory regression suites present so far (BOLA, error bodies, trace header, worker crash, fail closed, upload-resume core) | 100% pass | testing-strategy §5 |
| Coverage on changed lines | per testing-strategy §8 (API ≥ 85%, worker deterministic ≥ 85%, frontend ≥ 80%) | NFR-071 (judgment thresholds) |
| axe-core | 0 serious or critical violations | NFR-027 [DPA/DESIGN-14] |
| First-route JS | ≤ 200 KB gzipped | NFR-015 |
| gitleaks; dependency audit; licence check; SBOM produced | 0 secrets; 0 open critical findings; 0 AGPL/non-commercial in the shipped graph | NFR-056, NFR-062 |
| Test and gold immutability | no unapproved change under tests or gold paths | NFR-078 [EP/ENG-28] |
| PR size | about 100 changed lines; > 400 needs an EM waiver | [EP/ENG-04]; NFR-077 |
| Fresh-context review | no open Blocking findings; ≤ 3 fix iterations, then escalate | working-agreement §6-§7 |

Per sprint: all suites green on `main`; the walking-skeleton E2E green on ≥ 3 consecutive nightly runs before the review (judgment for Sprint 0; QD-QG-S4 asks for 5 from R1 review onward); flaky tests quarantined within 1 day with an owner (NFR-074).

## 9. Definition of Done

Every story meets the story-level DoD in `docs/process/definition-of-done.md`. The sprint meets the sprint-level DoD there. Sprint 0 adds:

- [ ] Every gate in §8 runs in CI on `main`. A deliberately failing sample PR shows each gate blocking (evidence: CI run links).
- [ ] Every hook in ST-003 is demonstrated: a format-on-edit, a blocked write to `.env`, a Stop hook blocking on a failing unit test.
- [ ] ADR 0011 (tus server) and the SPIKE-01 licence ADR are written. ADR 0008 has a dated SPIKE-09 note.
- [ ] Context canvases and the context map are merged (principal-engineer).
- [ ] Sprint 1 stories meet the DoR.
- [ ] `docs/sprints/00/status.json` holds planned and completed units per story (ADR 0010).
- [ ] Retrospective written with owned, dated actions.

## 10. Escalations to the human product owner this sprint

Sent by the product-manager on D2, with the EM's recommendation (working-agreement §8):

| OQ / ADR | Need-by | Blocks |
|---|---|---|
| OQ-02 / ADR 0002, ADR 0007 | Sprint 0 review, 2026-10-16 | Sprint 1+ scope |
| ADR 0009 (rules-engine readiness split) | Sprint 0 review | ST-020, ST-021 in Sprint 1 |
| OQ-01 (rulebook PDFs) | As early as possible; latest Sprint 3 planning (2026-11-16) for official scoring in R1 | NFR-003, every `@needs-verification` row |
| OQ-06 (consent for footage) | Sprint 1 planning (2026-10-19) | Team-recorded fixture and gold footage (ST-025) |
| OQ-12 (CV licence posture) | Sprint 1 review, with the SPIKE-01 ADR | R2 Ready |
| OQ-13 (spend ceiling) | Sprint 2 review | SPIKE-04 GPU provider in Sprint 3 |
| OQ-17 (reference device, browsers) | Sprint 1 planning | NFR-011, NFR-024 targets |
| OQ-20 (recruit testers, second coach) | Sprint 3 planning | R1 usability test (Sprint 5), QD-AN-03 |
| ADR 0010 PO-time assumption | Sprint 0 planning | All sprints |

## 11. Risks for this sprint

| Risk | Signal | Response |
|---|---|---|
| SeaweedFS lacks a feature we need | ST-001 parity script fails | Superseding ADR (ADR 0008 part C); MinIO dev-only with a licence note, or a cloud test bucket |
| Hooks slow agents down too much | Edit-to-green time rises; agents bypass hooks | Measure in retro; move slow checks from PostToolUse to Stop or CI |
| Review loop overload (every PR needs QA plus a peer) | PR time-to-merge > 1 day [EP/ENG-02] | EM batches reviews per story; reviewers flag only correctness and requirement gaps [EP/ENG-24] |
| Dev identity provider leaks into production | ST-006 prod-start test | Startup refusal plus security review |

## 12. Demo script (sprint review, 2026-10-16)

Run by the engineering-manager; evidence is captured into `docs/sprints/00/demo.md`.

1. `docker compose -f infra/compose.yaml up -d` → show `GET /readyz` returning ready for DB, store and queue.
2. Open the PWA, choose dev user "Ivy", see the empty matches list with its empty state.
3. Create match "Skeleton test", upload `fixtures/clips/synthetic-60s/clip.mp4`. Show % and MB progress.
4. Status changes to "Video received" and the facts appear: 1:00, 60 fps, 1920×1080.
5. Open the trace viewer: one trace with the API request, enqueue and probe spans.
6. Switch to dev user "Carlos" and paste Ivy's match URL → "not found". Show the security-log line.
7. Kill the worker during a probe (`docker compose kill -s SIGTERM worker`) → job requeued; one set of facts afterwards.
8. Show a sample PR with a failing unit test and an unformatted file: CI red, merge blocked. Show the PreToolUse hook refusing a write to `.env`.
9. Show the SPIKE-01 licence table and ask the PO for OQ-12.
10. Ask the PO to ratify ADR 0001, 0002, 0007, 0009 and confirm the ADR 0010 time assumption.

## 13. Retrospective

- **Date:** 2026-10-16, after the review.
- **File:** `docs/retros/2026-10-16-sprint-00.md` from [`docs/retros/TEMPLATE.md`](../retros/TEMPLATE.md).
- **Format:** Timeline. **Focus:** tooling, hooks and the auto-review loop.
- **Must cover:** planned vs completed units (ADR 0010 recalibration), hook friction, review iterations per PR, escalations, and whether the ADR 0001 judgment parameters still hold.
