# 0012. Red-first tests reach production code through one QA-owned seam contract

- **Status:** Proposed (accept at the Sprint 0 review, or earlier once BE and the principal-engineer confirm the seams at ST-005/ST-006/ST-007 start)
- **Date:** 2026-10-03
- **Deciders:** senior-qa-engineer (R); principal-engineer (A for API and module contracts)
- **Consulted:** senior-backend-engineer, sre-devops-engineer, security-privacy-engineer (the fault-injection seam)
- **Related:** ST-004, ST-012, ST-005..ST-009; testing-strategy §1.5-§1.6, §3, §5; ADR 0008 (code layout, test tooling); ADR 0011 (tus server, still to be written; the number is reserved in sprint-00 §3.1 and §9, so this ADR takes 0012)

## Context and problem statement

Sprint-00 §3.1 ST-012 asks QA to write the §7 scenarios, the regression suites and the integration tests IT-00-01..16 **before** ST-005..ST-009 start, so that they "fail red first" and the implementing stories turn them green [DPA/AI-08, EP/ENG-18]. Tests are immutable for implementers [EP/ENG-28]. A test written before the code has to name the code it calls: modules, functions, HTTP routes and response shapes. Sprint-00 §5/§6 names some of these (`Match`, `JobKey`, `MediaFacts.from_ffprobe`, `Settings`, tus HEAD/PATCH/409). It leaves out module paths, route paths for the dev sign-in and media facts, the worker entry point, and how a test makes a stage fail on purpose. If each test guesses these on its own, a single rename breaks dozens of "immutable" files. And a test that fails on `ImportError` at collection gives no per-test signal at all.

## Decision drivers

- Red for the right reason: each test fails on its own, with a message that names the missing piece and the story that provides it (EP/ENG-18 "confirm it fails for the right reason").
- Tests are immutable for implementers [EP/ENG-28], so the contract has to live in one QA-owned place that QA can change with an explanation.
- Black-box where it is cheap: drive the API over httpx `ASGITransport` with `dependency_overrides` [AQS/STACK-01]; run the worker as a real OS process for crash tests [AQS/OPS-02].
- No mocks in integration tests: real Postgres and the real S3-compatible store [AQS/OPS-05].
- No test-only behaviour may be live in production (NFR-054, AQS/SEC-12).

## Considered options

1. **One seam module** (`backend/tests/support/contract.py`). Every production name a test needs is a lazily loaded `Seam(target, story, note)`. Loading a missing seam calls `pytest.fail("RED until ST-xxx: seam … is not implemented yet")` inside the test.
2. **Direct imports in each test file**, marked `xfail(strict=True)` until the story lands.
3. **Do nothing:** write the scenarios only as `.feature` text and leave the step code to the implementers.

## Decision outcome

Chosen option: **1, one seam module**. It is the only option that keeps the tests immutable when a name changes (one edit, by QA), gives a red result per test with the owning story, and keeps the writer/reviewer split [DPA/AI-08]. Option 2 hides failures behind `xfail`, so a test that later passes for the wrong reason only shows as XPASS. It also fails at collection when a module is missing. Option 3 drops the test-first property ST-012 exists for.

### The seams as of 2026-10-03 (QA proposals unless sprint-00 names them)

| Seam | Story | Shape |
|---|---|---|
| `racket.platform.app:create_app` | ST-005 | `create_app(settings=None) -> FastAPI`; reads `Settings` from the environment and raises `ConfigurationError`/`MissingSettingError` (names the variable) |
| `racket.platform.settings:Settings`, `MissingSettingError`, `ConfigurationError` | ST-005 | `APP_ENV=prod` with `DEV_IDENTITY_ENABLED=true` raises an error that mentions development sign-in |
| `racket.platform.db:upgrade_to_head(url)`, `racket.platform.db:get_session` | ST-005 | migrations and the session dependency that tests override with a rolled-back session |
| `racket.platform.storage:ObjectStore.from_settings()` | ST-001/ST-008 | `list_keys(prefix='')`, `get_bytes(key)` |
| `racket.matches.api:get_match_service` | ST-006 | dependency that the error-body tests override with a failing service |
| `racket.matches.domain:Match`, `MatchId`, `OwnerId` | ST-006 | used by the `a_match().build()` / `an_owner().build()` builders |
| `racket.analysis_jobs.domain:JobKey`, `racket.analysis_jobs.queue:JobQueue` | ST-007 | `enqueue(key)` (idempotent per key), `claim(worker_id)`, `get(id)`, `for_match(match_id)`; Job has `id, key, status, attempts, failure_reason` |
| `python -m racket.worker`, `racket.worker.runner:run_until_idle()` | ST-007 | worker process and in-process drain |
| `racket.video_ingest.repository:count_media_facts(session, match_id)` | ST-009 | "exactly one set of media facts" |
| HTTP: `POST /dev/sign-in {"username"}` (cookie), `POST/GET /matches`, `GET /matches/{id}`, `GET /matches/{id}/media`, `POST /matches/{id}/uploads` (tus creation), `HEAD/PATCH /uploads/{id}` | ST-006, ST-008 | the tus routes may change with ADR 0011 |
| Logger `racket.security` | ST-006 | denied-access events, without personal data |
| `RACKET_FAULT_INJECTION` = `probe:sleep=<s>` or `probe:fail_after_partial_write` | ST-007 | **honoured only when `APP_ENV=test`**; a regression test (`test_fault_injection_is_ignored_outside_test_env`) proves it is inert in `dev` |
| Status codes `awaiting_upload`, `uploading`, `video_received`, `probe_failed` | ST-006..ST-009 | mapped to the UI labels in sprint-00 §7 |

## Pros and cons of the options

### Option 1: one seam module
- Good: one place to change; each test is red with the story that turns it green; collection never breaks.
- Good: BE can read the whole contract in one file at story start and push back before writing code.
- Bad: the module paths are guesses until BE confirms them, so an early rename is likely (one-line QA edits, logged in the decision log).
- Bad: the fault-injection seam is test-only behaviour in production code. It is mitigated by the `APP_ENV=test` guard, its regression test and the security review.

### Option 2: direct imports with `xfail(strict=True)`
- Good: familiar pytest idiom.
- Bad: a missing module breaks collection of the whole file; `xfail` hides the reason; every rename touches many immutable files.

### Option 3: feature text only
- Bad: implementers would write their own acceptance steps, which removes the writer/reviewer split [DPA/AI-08] and the red-first evidence ST-012 asks for.

## Consequences

- Good: 74 red tests each name their missing seam; 74 green tests already cover the harness, ManifestCheck and object-store parity (evidence below).
- Trade-off accepted: the contract is a proposal. The senior-backend-engineer confirms or amends it at the start of ST-005, ST-006 and ST-007. Amendments are QA edits to `contract.py`, with a row in `docs/sprints/00/decision-log.md`.
- Follow-up: the principal-engineer's ADR 0011 (tus server) may move the tus routes; QA then updates `UPLOAD_CREATE`/`UPLOAD_RESOURCE` and the BOLA matrix in the same PR.
- Follow-up: security-privacy-engineer reviews the `RACKET_FAULT_INJECTION` guard in the ST-007 PR.

## Evidence

| Claim | Evidence | Type |
|---|---|---|
| Red tests fail individually and name their story | `cd backend && uv run pytest -q` with DATABASE_URL and S3 set → `17 failed, 74 passed, 2 skipped, 57 errors`. All 74 red results carry `RED until ST-005: seam 'racket.platform.db:upgrade_to_head'` (72) or `'racket.platform.settings:ConfigurationError'` (2). Grouped from `--junitxml` on 2026-10-03 | test result |
| The test code can go green (it is not wrong in itself) | Throwaway in-memory fake of the HTTP seams (scratchpad only, never committed), loaded with `-p fakeimpl`: `51 passed, 3 failed` over the error-body, trace-header, BOLA, upload-resume, IT-00-01, IT-00-14 suites and four feature files. Two failures need the ObjectStore/worker seams the fake does not provide; the third passes alone and fails only because the fake keeps global state across tests | test result |
| Harness rollback works on real Postgres 16 | `uv run pytest tests/integration/harness` → `3 passed` (DATABASE_URL from `scripts/dev-postgres.sh start`) | test result |
| Writer/reviewer split; test-first; immutable tests | [DPA/AI-08], [EP/ENG-18], [EP/ENG-28] | verified source |
| httpx ASGITransport and dependency_overrides | [AQS/STACK-01] | verified source |
| Module paths and routes | (judgment), pending BE confirmation | judgment |

## Confirmation

ST-005..ST-009 PRs turn the red tests green without editing them (the CI test-immutability job from ST-003 enforces this). The sprint test report lists the count of red tests per story falling to zero.

## Notes

- **2026-10-03 (principal-engineer):** ADR 0011 keeps the tus routes the seams assume (`POST /matches/{match_id}/uploads`, `HEAD`/`PATCH /uploads/{upload_id}`), so `UPLOAD_CREATE` and `UPLOAD_RESOURCE` need no change. The API contract `docs/architecture/api-sprint-00.md` fixes the remaining choices the tests leave open. Those choices are: HEAD → 200; overflow PATCH → 413; anonymous → 401 on ID routes; list body `{"items", "next_cursor"}`; dev sign-in → 204 with an `HttpOnly` cookie, without `Secure` only when `APP_ENV=test`. Each choice is accepted by the existing assertions.
