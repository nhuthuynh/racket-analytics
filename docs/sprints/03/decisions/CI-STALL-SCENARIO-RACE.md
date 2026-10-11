# CI-STALL-SCENARIO-RACE decisions

Small decisions for ticket CI-STALL-SCENARIO-RACE. Main run 38103354166 (push, head `16a81bf`, the merge of PR #71) failed job 114363664369 "Infra, hooks and CI-script tests" on one test: `infra/tests/test_ci_e2e_stall_report_scenarios.py::test_a_run_that_reaches_the_global_timeout_names_the_interrupted_test_and_keeps_a_report` (`tests/features/ci_e2e_stall_report.feature`, from CI-E2E-JOURNEYS-TIMEOUT PR #57, `4d08e31`). The same tree failed on PR #71 run 402 and passed on run 403. One file per ticket (PO rule 2026-10-07).

## The failing run

Output of the stand-in run (job log, 2026-10-11T02:00:50Z), elapsed 5.69 s:

```text
  ✓  1 stall.spec.ts:3:5 › first test passes (2ms)
::error ::Timed out waiting 5s for the test suite to run
::error ::Timed out waiting 5s for the teardown for test suite to run
::notice title=🎭 Playwright Run Summary::  1 did not run%0A  1 passed (5.0s)
  1 did not run
  1 passed (5.0s)
  2 errors were not a part of any test, see above for details
```

The assertion at line 113 looked for the `list` reporter's `✘ … second test waits` line and found none.

## Root cause: two races, and the stated one is the smaller

The ticket's hypothesis was that start-up used up the 5 s before the second test began. That race exists, but it is not what main run 38103354166 shows. Evidence:

1. **"1 did not run" is printed on passing runs too.** Unloaded run of the stand-in with the gated reporters (`playwright test -c playwright.config.cjs --reporter=github,list,html --global-timeout=5000`), second test started about 1 s after launch:

   ```text
   ::notice title=🎭 Playwright Run Summary::  1 did not run%0A  1 passed (5.0s)
     1 did not run
     1 passed (5.0s)
     2 errors were not a part of any test, see above for details
     ✘  2 stall.spec.ts:4:5 › second test waits (4.1s)
   ```

   The `✘` line comes **after** the summary. The old scenario passed only because this late line arrived before the process exited.
2. **Playwright 1.56.1 does not wait for it.** `lib/runner/taskRunner.js:97`: the teardown runs with the same `deadline`, which has passed, so it times out at once ("Timed out waiting 5s for the teardown for test suite to run"); `dispatcher.stop()` has sent `__stop__` to the worker but is not awaited. `onEnd` prints the summary, then `program.js:254` calls `gracefullyProcessExitDoNotHang`, which exits as soon as there are no browsers to close. The worker's end of the interrupted test is reported only if it arrives before that exit.
3. **Deterministic reproduction of the CI output with the second test started 4 s before the deadline.** Same command; the harness waited for the second test's marker (worker pid), then `kill -STOP <worker pid>`: output identical to the CI log above (no `✘` line), `rc=1`. So a slow worker answer, not a late start, is enough to lose the line.
4. **The start-up race also exists under heavier load.** Old scenario (origin/main `16a81bf`), all processes pinned to CPU 0 with 6 busy loops: 20/20 failed, each with `2 did not run`: neither test began within 5 s.

The CI step this scenario protects has the same gap: when the 18 min global timeout of the gated E2E step fires, its output names the running test only if the worker answers before Playwright exits.

## Decisions

| # | Decision | Why | Alternatives rejected |
|---|---|---|---|
| D1 | New reporter `web/e2e/helpers/interrupted-tests-reporter.ts` on the gated E2E step (`--reporter=github,./e2e/helpers/interrupted-tests-reporter.ts,list,html`). It records tests that began and have not ended, and when the run ends `timedout` prints `Interrupted by the global timeout: <file>:<line>:<col> › <titles>` for each. | `onEnd` always runs before Playwright exits, and `onTestBegin` has been delivered for every test the runner knew was running, so the line does not depend on the worker's answer. Fixes the CI step itself, not only the scenario. | Accept "did not run" (forbidden: loses what the scenario protects). Retries (forbidden). Upgrade Playwright: not evaluated, a version bump is a change of its own. A `globalTeardown` hook: it also runs against the expired deadline. |
| D2 | The scenario's global timeout is `max(5 s, ceil(3 × start-up))`, start-up measured in a warm-up run of the same stand-in (no global timeout; stopped as soon as the second test writes its marker). A new step checks that the second test started before the timeout. | Makes "the second test has started" a precondition the scenario establishes instead of a race (D4 evidence: 6 busy loops on one CPU made start-up longer than 5 s). Factor 3 leaves the measured run room to be up to three times slower than the warm-up, which also takes the cold transform cache. Unloaded the timeout stays 5 s or 6 s. | A fixed larger timeout: still a race under enough load. A marker that "starts" the timeout: Playwright's deadline starts with the run and cannot be moved from outside. |
| D3 | New scenario: the same run with the worker frozen (`SIGSTOP`) from the second test's start until Playwright has exited. | The exact CI-run-38103354166 output, made deterministic; it is the red test for D1. | Reproduce only under CPU load: not deterministic. |
| D4 | "fails within 60 seconds" becomes "within 30 seconds of its global timeout", and the run must still end before the second test's 120 s. | With D2 the timeout may exceed 5 s on a slow runner; for 5 s the bound is 35 s, tighter than 60 s. | Keep 60 s: breaks when D2 raises the timeout. |
| D5 | The harness lives in `infra/tests/e2e_stall_harness.py`; each Playwright run gets its own process group and is killed (`SIGCONT` + `SIGKILL` for the frozen worker) in `finally`. | No stray frozen workers on the runner or in local loops. | |
| D6 | Test change to the accepted feature and binding: TCR row 2026-10-11 in `test-change-requests.md`, pending the senior-qa-engineer's decision and the `qa-approved-test-change` label. | Working agreement; ADR 0014. | |

## TDD evidence

Red (`840d3df`), `cd infra && uv run pytest -q -p no:cacheprovider tests/test_ci_e2e_stall_report_harness.py tests/test_ci_e2e_stall_report_scenarios.py`:

```text
FAILED tests/test_ci_e2e_stall_report_harness.py::test_the_gated_step_names_the_tests_a_global_timeout_interrupts   (AssertionError: ['github', 'list', 'html'])
FAILED tests/test_ci_e2e_stall_report_scenarios.py::test_a_run_that_reaches_the_global_timeout_names_the_interrupted_test_and_keeps_a_report   (no "Interrupted by the global timeout: … second test waits"; "Timed out waiting 6s", "1 did not run", late "✘ 2 stall.spec.ts:6:5 › second test waits (5.1s)")
FAILED tests/test_ci_e2e_stall_report_scenarios.py::test_the_interrupted_test_is_named_even_when_its_worker_does_not_answer_the_stop_in_time   (same as CI: "1 did not run", no ✘ line)
3 failed, 11 passed in 18.00s
```

`cd web && pnpm exec vitest run tests/unit/e2e-interrupted-tests-reporter.test.ts`: `Error: Failed to resolve import "../../e2e/helpers/interrupted-tests-reporter"`, `Test Files 1 failed`.

Green (`4e401be`, refactor `2b5b392`):

- `uv run pytest -q -p no:cacheprovider tests/test_ci_e2e_stall_report_harness.py tests/test_ci_e2e_stall_report_scenarios.py tests/test_ci_e2e_bounded_scenarios.py` → `21 passed in 19.53s`.
- `pnpm exec vitest run tests/unit/e2e-interrupted-tests-reporter.test.ts` → `Tests 9 passed (9)`.
- Manual frozen-worker run with the new reporter (`--reporter=github,<web>/e2e/helpers/interrupted-tests-reporter.ts,list,html --global-timeout=5000`, worker `SIGSTOP`ped after its marker): `Interrupted by the global timeout: stall.spec.ts:4:5 › second test waits` printed before the summary, `rc=1`.

## Loops under load

Script: `loop.sh <label> <n> <busy loops>` runs `taskset -c 0 uv run pytest -q -p no:cacheprovider tests/test_ci_e2e_stall_report_scenarios.py` n times, each with a fresh `TMPDIR` (cold Playwright transform cache, as on a fresh runner), with the given number of `taskset -c 0 python3 -c "while True: pass"` loops on the same CPU. 4-CPU sandbox.

| Tree | Load | Iterations | Passed | Failed |
|---|---|---|---|---|
| before: origin/main `16a81bf` | none (first run in the new worktree) | 1 | 0 | 1 (output not kept) |
| before: origin/main `16a81bf` | 8 busy loops, unpinned | 20 | 20 | 0 |
| before: origin/main `16a81bf` | CPU 0, 3 busy loops | 50 | 50 | 0 |
| before: origin/main `16a81bf` | CPU 0, 6 busy loops | 20 | 0 | 20 (`2 did not run`) |
| after: this branch (both scenarios each iteration, 39.7-43.4 s per iteration) | CPU 0, 6 busy loops | 50 | 50 | 0 |

Plus the frozen-worker scenario, which fails on every run of the old reporters and is part of the after loop.

## Full suites (this branch)

- `cd infra && uv run pytest -q -p no:cacheprovider -m "unit or integration"` → `1087 passed, 4 skipped in 407.73s`.
- `cd web && pnpm exec vitest run` → `Test Files 79 passed (79)`, `Tests 681 passed (681)`; `pnpm exec eslint --max-warnings=0 .` clean; `pnpm exec tsc --noEmit` clean.
- `cd infra && uv run ruff check` and `uv run ruff format --check` on the three changed Python files: clean.

## Not done here

- Done also needs this PR's CI and 3 consecutive green main runs after merge; the merge step and the sprint's DOCS ticket record those.
