# 0017. Job runtime: a hand-written `SKIP LOCKED` queue with leases, not procrastinate

- **Status:** Proposed (accept at the ST-007 review; principal-engineer A, sre-devops-engineer and senior-qa-engineer consulted)
- **Date:** 2026-10-03
- **Deciders:** senior-backend-engineer (R, ST-007 and SPIKE-09); principal-engineer (A)
- **Consulted:** senior-qa-engineer (ADR 0012 seams), sre-devops-engineer (Compose `stop_grace_period`, heartbeat file)
- **Related:** ST-007, SPIKE-09, ST-008, ST-009; FR-080, NFR-046, NFR-047, NFR-076; ADR 0008 part B (this ADR settles its "library or hand-written" question), ADR 0011 (transactional enqueue), ADR 0012 (seams `JobQueue`, `run_until_idle`, `STAGES`, `RACKET_FAULT_INJECTION`)

## Context and problem statement

ADR 0008 part B chose a Postgres-backed queue and named `procrastinate` (MIT) as the candidate library, with a hand-written `SELECT … FOR UPDATE SKIP LOCKED` table as the fallback, to be settled by SPIKE-09 inside ST-007. The QA red-first suites fix the required behaviour: enqueue idempotent per `(match_id, pipeline_version, stage)` (IT-00-03), SIGTERM hands the in-flight job back within 10 s with attempt + 1 and the worker exits 0 (IT-00-04, NFR-046b), SIGKILL does not lose the job (IT-00-04), a failing stage leaves no rows and marks the job `failed` (IT-00-05, NFR-047), and one trace covers API → enqueue → stage (IT-00-11). The question: which queue implementation meets these, and how does a dead worker's job come back?

## Decision drivers

- D1. Requeue on SIGTERM, not "finish first": the job must be `queued` again within 10 s even when the stage would run for 60 s (IT-00-04; NFR-046b) [AQS/OPS-02].
- D2. Survive sudden death (SIGKILL, OOM, node loss) without an operator (IT-00-04) [AQS/OPS-02].
- D3. One job per key for the job's whole life, not only while queued (IT-00-03; AQS/OPS-02 idempotency).
- D4. The enqueue shares the upload-completion transaction (ADR 0011 D2; NFR-060).
- D5. Stage writes and "job done" commit together; failures roll back (NFR-047) [AQS/SEC-12].
- D6. The ADR 0012 seams (`JobQueue(session).enqueue/claim/get/for_match`, `run_until_idle`) stay as QA wrote them.
- D7. Fewest moving parts [AQS/ENG-04].

## Considered options

1. **procrastinate** (MIT): async worker, `defer`, queueing locks, heartbeats and a periodic "retry stalled jobs" task.
2. **Hand-written queue**: a `jobs` table with a unique key, `FOR UPDATE SKIP LOCKED` claims, a lease (`lease_expires_at`) extended by a heartbeat thread, and a runner that raises a shutdown signal inside the stage on SIGTERM.
3. **Do nothing**: run the probe inline in the API request. Breaks AQS/STACK-01 (no CPU work in the API process) and every resilience test.

## Decision outcome

**Chosen option: 2, the hand-written queue with leases.** It is the only option that meets D1-D3 without extra machinery, and SPIKE-09 shows its claim cost is far below the MVP's needs (Evidence E5-E7).

Design (as implemented in `backend/src/racket/analysis_jobs/` and `backend/src/racket/worker/`):

- `Job` is a pure domain state machine (`queued → running → done | failed`, `running → queued` on requeue with attempt + 1). `attempts` is the number of the current attempt, starting at 1. `fail(reason)` accepts only a short code, never exception text.
- `jobs` has `UNIQUE (match_id, pipeline_version, stage)`; `enqueue` is `INSERT … ON CONFLICT DO NOTHING RETURNING id` and runs in the caller's transaction (D3, D4). It opens a PRODUCER span "job enqueue" and stores the W3C carrier on the job.
- `claim` selects the oldest row that is `queued`, **or `running` with an expired lease**, `FOR UPDATE SKIP LOCKED LIMIT 1`. Reclaiming an expired lease counts as a new attempt. The claim commits before the stage runs, so other connections see `running`.
- While a stage runs, a heartbeat thread extends the lease every lease/3 (default lease 15 s, `WORKER_LEASE_SECONDS`). A killed worker stops extending it, so another worker reclaims the job after at most one lease (D2).
- The stage runs in its own transaction. At the end the runner re-locks the job (`status = running AND worker_id = me`), marks it `done`, and commits stage writes and `done` together (D5). If the lease was lost meanwhile, it rolls back and abandons the job to its new owner.
- SIGTERM: the handler sets `stop`; if a stage is running it raises `ShutdownRequested` (a `BaseException`, so stage code cannot swallow it) inside the stage. The runner rolls the stage back, requeues the job (attempt + 1) and the process exits 0 (D1). SIGTERM between jobs only stops the loop.
- A stage failure rolls the stage back, then a fresh transaction marks the job `failed` with the stage's reason code and calls the stage's `on_failure` (the probe stage marks the media asset `probe_failed`).

## Pros and cons of the options

### Option 1: procrastinate
- Good: maintained library; heartbeats and stalled-job detection exist; MIT.
- Bad (D1): on SIGTERM "the worker … waits for all running jobs to complete"; aborting needs `shutdown_graceful_timeout` plus jobs that honour `should_abort`, and an aborted job is not requeued by itself (E1).
- Bad (D2): a SIGKILLed worker leaves jobs in `doing`; they are retried only by a periodic task the app must add (the documented example runs every 10 minutes) (E2).
- Bad (D3): a queueing lock only stops a job appearing "more than once in the queue"; it does not make a key unique after the job is done (E3).
- Bad (D6): async-first worker API; the seams would need an adapter layer over its tables.

### Option 2: hand-written queue with leases
- Good: meets D1-D7; about 200 lines (`queue.py`, `runner.py`); the suites prove it (E4).
- Good: one transaction for enqueue and for "stage writes + done".
- Bad: we own the code, including lease tuning. A job whose worker is stopped (not killed) longer than the lease without heartbeats could run twice; the final re-lock (`worker_id = me`) makes the loser roll back, so its writes never commit (judgment, covered by the unique media-facts key).
- Bad: no built-in retry policy, scheduling or dashboards. None is needed in Sprint 0 (judgment).

### Option 3: inline in the API
- Bad: CPU/tool work in the request path [AQS/STACK-01]; no resilience; fails IT-00-04/05.

## Consequences

- Good: every ST-007 suite is green without test edits (E4). SPIKE-09 numbers are in ADR 0008's notes.
- Trade-offs accepted: SIGKILL recovery takes up to one lease (15 s default; IT-00-04's SIGKILL test took 17.0 s end to end, E4). Shorter leases mean more heartbeat writes.
- Follow-up work:
  - SRE: run `python -m racket.platform.migrate` before `api`/`worker` start in Compose and CI (the API migrates at startup only when `APP_ENV=dev`).
  - Sprint 1+: retry policy with backoff for transient stage errors (today any exception fails the job); a metric for queue depth and lease losses (NFR-076).
  - CM-1 (context map): if the runtime moves to `platform/queue`, QA moves the `JOB_QUEUE` seam.

## Evidence

| ID | Claim | Evidence | Type |
|---|---|---|---|
| E1 | procrastinate waits for running jobs on SIGTERM; abort needs `shutdown_graceful_timeout` and cooperative jobs | `curl https://raw.githubusercontent.com/procrastinate-org/procrastinate/main/docs/howto/advanced/shutdown.md` → 200, sha256 `8873f9e966b9e9a8…` (2026-10-03) | fetched in this ADR |
| E2 | SIGKILLed workers leave `doing` jobs; retried by an app-defined periodic task (example `*/10 * * * *`) | `…/docs/howto/production/retry_stalled_jobs.md` → 200, sha256 `aa77ceb33ac7a72c…` | fetched in this ADR |
| E3 | Queueing locks only prevent duplicates while queued | `…/docs/howto/advanced/queueing_locks.md` → 200, sha256 `074152414515fb73…` | fetched in this ADR |
| E4 | The design meets IT-00-03/04/05/11 and the job-resilience scenarios | `cd backend && uv run pytest -q tests/integration/test_it_00_03_queue.py` → `4 passed`; `uv run pytest -q tests/regression/test_worker_crash.py tests/features/test_job_resilience.py tests/integration/test_it_00_15_log_scan.py --durations=5` → `7 passed in 22.24s` (SIGKILL test 17.03 s); `tests/regression/test_fail_closed.py`, IT-00-11 → green in the full run `280 passed, 2 skipped` | test result |
| E5 | Claim throughput, 4 workers × 1,000 jobs, no-op stage | `uv run python -m tests.perf.spike_09_queue_claim --workers 4 --jobs 1000` (Postgres 16.14, local) → 504-888 jobs/s over 4 runs; claim p50 2.2-2.8 ms, p95 3.5-6.7 ms, p99 8-14 ms | data |
| E6 | No double claims, no starvation | Same runs: every job `done` with `attempts = 1` (1,000/1,000), 0 empty claims while work remained, 200-304 jobs per worker | data |
| E7 | Lock contention is small | Same runs: `pg_stat_activity` sampled every 5 ms showed `Lock/transactionid` waits in 6-10 % of samples, at most 3 waiting backends; 0 waits with a 5 ms stage | data |
| E8 | Disposability and requeue on shutdown | [AQS/OPS-02] | verified source |
| E9 | Fail closed; all-or-nothing | [AQS/SEC-12]; [AQS/SEC-07] 2.3.3 | verified source |
| E10 | Lease length, heartbeat interval, `BaseException` shutdown signal | (judgment) | judgment |

## Confirmation

- IT-00-03, IT-00-04, IT-00-05, IT-00-11 and `tests/features/job_resilience.feature` stay green without edits.
- In Compose: `docker compose kill -s SIGTERM worker` during a probe requeues the job (sprint-00 §12 demo step 7).
