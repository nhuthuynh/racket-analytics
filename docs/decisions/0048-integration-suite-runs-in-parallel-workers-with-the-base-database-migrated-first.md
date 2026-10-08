# 0048. The integration suite runs in parallel workers on one cluster, with the base database migrated first

- **Status:** Accepted (2026-10-08, principal-engineer, PR #15 review r1)
- **Date:** 2026-10-08
- **Deciders:** principal-engineer
- **Consulted:** sre-devops-engineer (author, implementation), senior-qa-engineer (pytest config and selection owner), senior-backend-engineer (migration 0012 owner)
- **Related:** CI-INTEG-BUDGET, CI-PERF-GATES (PR #13), NFR-073, NFR-071, C-32 (per-session test database), ST-042 (migration 0012), ADR 0014 (CI gates fail closed), ADR 0039 (ticket PRs)

## Context and problem statement

NFR-073 gives the integration job 600 s for the unit, integration, scenario and regression suites
with branch coverage (`run_with_budget.py "$INTEGRATION_BUDGET_S"`). After the Sprint 3 ITs joined
the gate (`be07fc1`) the step went over its budget on PR #4: runs 37715576115 and 37718386760 ended
with exit 124 at 600 s, and run 37719909230 passed at 542 s, so the budget was borderline. A local
replay of the CI selection with coverage took 649.31 s with no single slow test (blockers.md,
2026-10-08). The 600 s budget and the coverage inside it cannot change (that would weaken the
gate). How does the suite fit again?

A second question came up while checking the answer. Parallel workers share one Postgres
cluster, and each migrates its own session database (C-32). Migration 0012 (Sprint 3, ST-042)
creates the cluster-wide role `racket_media_worker` with check-then-create. Roles belong to the
cluster, not to a database, so per-database isolation does not cover them.

## Decision drivers

- NFR-073: 600 s budget, unchanged, with branch coverage inside it.
- NFR-071: changed-lines coverage (`diff-cover`, >= 85%) needs one combined coverage report.
- The same test selection as before (`-m "(unit or integration or scenario or regression) and not nightly and not red_until"`, the two IT-00-10 sandbox files left to their own job), the same selection the nightly flaky report runs.
- Fail closed (ADR 0014): a flaky race in setup is a red gate nobody can trust.
- Dev/prod parity (AQS/OPS-05): real Postgres, migrations applied the way Compose applies them.

## Considered options

1. **pytest-xdist on the one runner (`-n auto`), one session database per worker (C-32), the base database migrated once before the workers start.**
2. **Shard the job:** a matrix of N jobs, each with its own Compose stack and a slice of the selection; each uploads its `.coverage` data; a final job combines it and runs `diff-cover`.
3. **pytest-xdist without the migrate step** (PR #13 as first opened).
4. **Raise the budget, or time the suite without coverage.** Not allowed by the ticket: it weakens the gate.
5. **Do nothing.** The job stays red (exit 124).

## Decision outcome

Chosen option: **1**, because it brings the suite well inside 600 s on the same runner, keeps a
single coverage report for `diff-cover`, keeps the selection byte-for-byte, and removes the one
shared-state race the parallel run adds. The migrate step runs
`uv run --no-sync python -m racket.platform.migrate` in `backend` on the base `DATABASE_URL`,
after `uv sync` and before the budgeted step, outside the budget (setup, like Compose's `migrate`
service, which runs the same command).

Rules that follow:

1. The integration job migrates the base database before any parallel worker starts. Guarded by `infra/tests/test_workflows_integ_budget.py`.
2. The budgeted step and the nightly flaky report keep the same selection. Guarded by the scenario "The budget still times the full selection with coverage".
3. A migration that creates a cluster-wide object (role, tablespace, cluster setting) must be idempotent when it runs on several databases at once. The CI step makes this hold in CI only. For migration 0012 this is a **hard precondition of the ST-042 ticket PR**: that PR does not merge while 0012 creates its role with plain check-then-create (owner senior-backend-engineer; recorded as an owned row in `docs/sprints/03/decision-log.md`, 2026-10-08, PE-PR15-02).

## Pros and cons of the options

### Option 1: xdist on one runner, base database migrated first
- Good, because `-n 4` on the Sprint 3 tree took 203.90 s with coverage where one process took 743.63 s (PR #13 decision-log row; measured again here, see Evidence).
- Good, because pytest-cov combines worker data itself, so `diff-cover` reads one `coverage-backend.xml` as before.
- Good, because Mailpit is read per unique address and the object store per written key (QA-R3-02), so neither is shared state between workers.
- Bad, because a worker's crash costs only its own tests, but CPU contention can make timing-sensitive tests slower. Mitigation: `--durations=25` in every run, and the flaky report stays serial.
- Bad, because workers share the cluster: cluster-wide objects need the migrate step (rule 1) and idempotent migrations (rule 3).

### Option 2: sharded jobs
- Good, because each shard has its own cluster, so there is no shared state at all.
- Bad, because each shard pays runner setup, ffmpeg install and Compose start (about 2 min per job, judgment from the job logs), and needs a coverage upload and combine job before `diff-cover`.
- Bad, because a deterministic split must be kept equal to the selection: one more thing that can silently drop tests.
- Bad, because `ci-gate` needs one more job, and the NFR-073 budget would have to be redefined per shard (judgment).

### Option 3: xdist without the migrate step
- Good, because it is one change smaller.
- Bad, because it fails on a fresh cluster once migration 0012 is on `main`: 4 workers collide on `CREATE ROLE` (Evidence). CI's Compose Postgres is fresh on every run.

### Options 4 and 5
- Bad, because they weaken the gate or leave it red.

## Consequences

- Good: the integration job fits its budget with coverage and the same selection, and the run keeps its measured time (`reports/integration-budget.json`, from PR #13).
- Bad / trade-offs accepted: the job depends on workers sharing one cluster safely. Rule 1 covers CI. A developer running `pytest -n auto` on a fresh local cluster with migration 0012 present still has the race until a follow-up lands.
- Follow-up work:
  - senior-backend-engineer (merge precondition, not optional): migration 0012 creates its role with an exception handler for `duplicate_object` / `unique_violation`, so it is idempotent under concurrency anywhere (rule 3). This belongs to the ST-042 ticket PR, which brings 0012 to `main`; that PR cannot merge without it (PE-PR15-02).
  - senior-qa-engineer (optional, TCR): the `db_engine` fixture could serialise worker migrations on the base database with an advisory lock (`pg_advisory_lock` is per database, so the lock must be taken on the base database, not the session one). That fixes local `-n` runs without the CI step.

## Evidence

| Claim | Evidence | Type |
|---|---|---|
| The serial step is over budget | CI runs 37715576115 and 37718386760: step 9 exit 124 at 600 s; run 37719909230 passed at 542 s; local replay 649.31 s (blockers.md 2026-10-08) | test result |
| Parallel workers fit | PR #13 decision-log row: `origin/sprint-03` `efd5316`, one process `2646 passed, 19 skipped in 743.63s`; `-n 4` `2664 passed, 1 skipped in 203.90s` | test result |
| Workers race on the 0012 role on a fresh cluster | `origin/sprint-03`, 4 spawned processes each running `upgrade_to_head` on its own new database at once: 3, 2, 3, 3, 0 of 4 failed in 5 trials with `UniqueViolation … pg_authid_rolname_index` | test result |
| The race is deterministic in the regression test | `cd infra && uv run pytest -q tests/test_parallel_migrations.py::test_without_the_step_the_losing_workers_fail_on_the_cluster_role_only` → passed ×3 (3 of 4 workers fail on the role every time) | test result |
| The migrate step removes it | `cd infra && uv run pytest -q tests/test_workflows_integ_budget.py tests/test_integ_budget_scenarios.py tests/test_parallel_migrations.py` → 13 passed ×3 | test result |
| The full Sprint 3 suite, replayed as CI runs it | see "Live replay" below | test result |
| Sharding costs more wall time and complexity than it saves | (judgment) | judgment |

### Live replay

The integration job's backend steps replayed locally on `origin/sprint-03` (`efd5316`) merged with
the CI-INTEG-BUDGET branch: a fresh Postgres 16 cluster each run (`scripts/dev-postgres.sh`),
SeaweedFS (`scripts/dev-objectstore.sh`), Mailpit v1.27, `CI=true`, 4 cores (as the GitHub runner).
Same warm-up, same budgeted command (`run_with_budget.py 600 --json … pytest -n auto … --cov`).
Collected: `2676/2698 tests collected (22 deselected)`.

| Run | Migrate step | Result | Budget record |
|---|---|---|---|
| 0 | no | `2509 passed, 1 skipped, 166 errors in 228.37s`; all 166 are `UniqueViolation … pg_authid_rolname_index` (`racket_media_worker`) | 229.9 s, rc 1 |
| 1 | yes | `2675 passed, 1 skipped in 252.86s` | 254.7 s, rc 0 |
| 2 | yes | `2675 passed, 1 skipped in 220.65s` | 222.0 s, rc 0 |
| 3 | yes | `2675 passed, 1 skipped in 233.92s` | 235.2 s, rc 0 |

2675 + 1 = 2676, the collected selection: no test lost to parallelism.

## Confirmation

- `infra/tests/test_workflows_integ_budget.py`, `test_integ_budget_scenarios.py` and `test_parallel_migrations.py` pass in the `infra-tests` job.
- Done for CI-INTEG-BUDGET: 3 consecutive CI runs at the head keep the integration step under 600 s (`integration-budget.json`), with 0 failed and the same selection.

## Notes
