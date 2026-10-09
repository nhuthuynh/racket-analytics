# 0049. The domain unit suite runs in parallel workers inside its 10 s budget

- **Status:** Proposed (principal-engineer decides; senior-qa-engineer consulted, owner of the pytest selection)
- **Date:** 2026-10-09
- **Deciders:** principal-engineer
- **Consulted:** sre-devops-engineer (author), senior-qa-engineer
- **Related:** CI-DOMAIN-BUDGET, NFR-073, ADR 0048 (integration suite on xdist), ADR 0014, QA-R1-07 (the domain budget measures the default Hypothesis profile), ST-054

## Context and problem statement

NFR-073 gives the "rules + domain" unit suite (`DOMAIN_TEST_PATHS`) 10 s of wall time. `run_with_budget.py` times the whole `uv run pytest` process (start-up, collection, tests). Main runs 37882972340 and 37918385248 stopped the step at 10 s (exit 124) with every test passing: 1,237 tests in 8.97 s of pytest time, plus start-up and collection. The margin shrank when `tests/unit/analytics` joined the paths (ST-054).

Where the time goes (warm bytecode, `-p no:cacheprovider`): collection alone `1237 tests collected in 1.01s`, wall 2.1 s, of which the root conftest import is 0.57 s (`-X importtime`). `--durations=40`: about 30 Hypothesis property tests at 0.06-0.48 s each; every other test ≤ 0.01 s. cProfile (`sports matches analytics`): 11.2 s of 13.3 s of test time inside Hypothesis `run_engine`, mostly example generation. The suite is CPU-bound Hypothesis generation in one process plus about 2 s of fixed start-up; there are no heavy fixtures and no repeated JSON or lock loading.

## Considered options

1. **pytest-xdist in the domain step (`-n auto --dist worksteal`)**; everything else unchanged, start-up still timed.
2. **Fewer Hypothesis examples in the domain run.** Rejected: weakens the gate (QA-R1-07); fuzz depth is QA's call.
3. **Property tests only in the property step.** Rejected: changes the selection.
4. **Stop timing start-up and collection.** Not needed once option 1 is in place; the budget keeps measuring what a developer waits for.
5. **Raise the budget.** Not allowed (NFR-073).

## Decision outcome

Chosen option: **1**. `pytest-xdist` is already locked (CI-PERF-GATES). `worksteal` lets idle workers take the long property tests. `ubuntu-24.04` runners for this public repo have 4 vCPUs, so `auto` gives 4 workers.

Rules:

1. Budget 10 s, selection `-m "unit and not red_until" $DOMAIN_TEST_PATHS`, default profile, no narrowing flags. Guarded by `infra/tests/test_ci_domain_budget.py`.
2. The parallel run executes the same test ids with the same outcomes as one process: `tests/features/ci_domain_budget.feature` (real suite, junit compared test by test).
3. Each run keeps its wall time (`reports/budget/domain-unit.json` in the `junit-unit` artifact).
4. The G03-11 (d) scorecard run uses CI's workers.
5. (PE-R1-DB-01) An unbudgeted step before it fills Hypothesis's local-constants cache (`scripts/ci/warm_hypothesis_constants.py`, same selection, no test run). On a fresh checkout each worker's first example otherwise parsed every local module: 1.26-1.67 s per worker, ~1 s of wall locally. A cache, like the bytecode warm-up; generated values are unchanged.

## Consequences

- Good: same tests, same depth, start-up still measured; the CPU-bound part scales with cores.
- Bad: each worker imports the conftest and collects, a fixed cost of about 1-2 s.
- Bad: on a host shared with CPU-heavy work (this dev container during Playwright runs, load 7-9 on 4 cores) both serial and parallel runs exceed 10 s, so local timing there is not evidence. The CI runner is the measurement.

## Evidence

Locally at load ≈ 2: serial wall 8.5-11.5 s; `-n 4 --dist worksteal` 5.4-6.0 s; `-n auto` 6.0-6.3 s. Red → green: `cd infra && uv run --no-sync pytest -q -p no:cacheprovider tests/test_ci_domain_budget.py tests/test_ci_domain_budget_scenarios.py` → `3 failed, 10 passed` → green. CI run 37933402495 (cee8c00, cold cache): 10 s, exit 124. CI run 37935969739 (dc75b07, warmed): `budget: finished in 7.7s`. Locally, cold vs warmed: 6.5-6.8 s vs 5.6-6.1 s. The `bringing up nodes`/`98%` timestamps in the step log are block-buffered stdout, not phase times (unbuffered: first line at 0.66 s). Done when 3 consecutive CI runs at the PR head show domain wall ≤ 7.5 s and pass.
