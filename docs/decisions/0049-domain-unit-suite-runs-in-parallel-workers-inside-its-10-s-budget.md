# 0049. The domain unit suite runs in parallel workers inside its 10 s budget

- **Status:** Proposed (principal-engineer decides; senior-qa-engineer consulted as owner of the pytest config and selection)
- **Date:** 2026-10-09
- **Deciders:** principal-engineer
- **Consulted:** sre-devops-engineer (author, implementation), senior-qa-engineer
- **Related:** CI-DOMAIN-BUDGET, NFR-073, ADR 0048 (integration suite on xdist), ADR 0014 (gates fail closed), QA-R1-07 (the domain budget measures the default Hypothesis profile), ST-054 (analytics joined `DOMAIN_TEST_PATHS`)

## Context and problem statement

NFR-073 gives the "rules + domain" unit suite (`DOMAIN_TEST_PATHS`) 10 s of wall time. CI
measures it with `run_with_budget.py`, which times the whole `uv run pytest` process: interpreter
start, plugin load, collection and the tests. Main runs 37882972340 (PR #37 merge) and
37918385248 (scheduled, job 113780057556) stopped the step at 10 s with exit 124. In the second
run all 1,237 tests passed in 8.97 s of pytest time; start-up and collection took the rest. The
margin shrank when `tests/unit/analytics` joined the paths (ST-054: 8.2-8.3 s locally, "margin
about 2 s").

Where the time goes (this host, warm bytecode, `-p no:cacheprovider`):

- Collection alone: `pytest --collect-only` on the paths → `1237 tests collected in 1.01s`, wall 2.1 s.
  The root `conftest.py` import is 0.57 s of that (`python -X importtime`: SQLAlchemy, Hypothesis,
  `tests.support.db`).
- Tests: `--durations=40`: about 30 Hypothesis property tests take 0.06-0.48 s each; everything
  else is 0.01 s or less. cProfile of `sports + matches + analytics`: 11.2 s of 13.3 s of test
  time inside Hypothesis `run_engine`, mostly example generation (`generate_new_test_cases`,
  `generate_mutations_from`, `ConjectureData.draw`); the code under test is a small share.

So the suite is CPU-bound Hypothesis generation in one process, plus about 2 s of fixed start-up.

## Decision drivers

- NFR-073: 10 s, unchanged.
- The same selection: `-m "unit and not red_until" $DOMAIN_TEST_PATHS`, no skips, no deselection.
- The domain budget measures the default Hypothesis profile (QA-R1-07); the `ci` profile stays in its own step.
- Fail closed (ADR 0014); a budget that fails at random is a gate nobody trusts.
- At least 25% headroom: wall time ≤ 7.5 s on the CI runner.

## Considered options

1. **pytest-xdist in the domain step (`-n auto --dist worksteal`).** Same command otherwise; the budget still times start-up and collection.
2. **Lower Hypothesis `max_examples` in the domain run** (a `domain` profile or per-test settings). Rejected: it changes what the gate checks (QA-R1-07, the decision-log row of 2026-10-06 rejected it too), and fuzz depth is QA's to set.
3. **Move the property tests out of the domain step** into the property step only. Rejected: it changes the selection, which the ticket forbids.
4. **Stop timing start-up and collection.** Rejected for now: the budget should keep measuring what a developer waits for, and option 1 is enough without it.
5. **Raise the budget.** Not allowed (NFR-073).

## Decision outcome

Chosen option: **1**. The domain step runs
`run_with_budget.py "$DOMAIN_UNIT_BUDGET_S" --json ../reports/budget/domain-unit.json -- uv run --no-sync pytest -q -n auto --dist worksteal -m "unit and not red_until" $DOMAIN_TEST_PATHS`.
`pytest-xdist` is already in the backend dev group and lock (CI-PERF-GATES). `worksteal` lets idle
workers take the long property tests that `load` would leave queued behind one worker.
`ubuntu-24.04` runners for this public repository have 4 vCPUs, so `auto` is 4 workers.

Rules that follow:

1. The domain step keeps budget 10 s, the selection, the default profile, and no narrowing flags (`-k`, `--deselect`, `--ignore`, `-x`, `--maxfail`, `-p`, `-o`). Guarded by `infra/tests/test_ci_domain_budget.py`.
2. The parallel run executes the same test ids with the same outcomes as one process. Guarded by the scenario in `tests/features/ci_domain_budget.feature` (real suite, junit compared test by test).
3. Each CI run keeps the wall time (`reports/budget/domain-unit.json` in the `junit-unit` artifact), so the margin is visible per run.
4. The G03-11 (d) scorecard run uses the same workers as CI.

## Consequences

- Good: the gate checks the same tests at the same depth, and the measured time includes start-up.
- Good: room to grow; the CPU-bound part scales with runner cores.
- Bad: worker start-up (each worker imports the root conftest and collects) is a fixed cost of about 1-2 s.
- Bad: on a host shared with other CPU-heavy work (this dev container during Playwright runs, load 7-9 on 4 cores), both serial and parallel runs exceed 10 s; local timings there are not evidence. CI's dedicated runner is the measurement.
- Neutral: Hypothesis results are independent of which worker runs a test; the example database is a directory that tolerates concurrent writers.

## Evidence

- CI: runs 37882972340 and 37918385248, step "Domain unit suite < 10 s (NFR-073)", exit 124 at 10 s.
- Local (before host load rose, load ≈ 2): serial wall 8.5-11.5 s; `-n 4 --dist worksteal` 5.4-6.0 s; `-n auto` 6.0-6.3 s; `-n 2` 6.7-6.8 s.
- Red → green: `cd infra && uv run --no-sync pytest -q -p no:cacheprovider tests/test_ci_domain_budget.py tests/test_ci_domain_budget_scenarios.py` → `3 failed, 10 passed` → `13 passed`.
- Done when 3 consecutive CI runs at the PR head show domain wall time ≤ 7.5 s and pass (PR body and `decisions/CI-DOMAIN-BUDGET.md`).
