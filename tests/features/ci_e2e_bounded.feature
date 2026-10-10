# CI-E2E-JOURNEYS-TIMEOUT (NFR-073, NFR-074). Owner: senior-qa-engineer. Bound by
# infra/tests/test_ci_e2e_bounded_scenarios.py; the real-Playwright path is
# tests/features/ci_e2e_stall_report.feature.
@nfr-073 @nfr-074 @ci-e2e-journeys-timeout
Feature: The E2E job ends inside its budget, and a slow run stops itself with a report
  Main run 38016581726 (0c5d513): the tree that passed the Playwright journeys in 18.2 min on the
  PR run took over 42 min on a slower runner. Both browsers ran one after the other in one job
  with a 45 min limit, nothing bounded the run, and the cancel left no report, no per-test
  durations, no service logs and no runner facts.

  Scenario: Each browser runs in its own E2E job leg on its own stack
    Given the CI workflow
    Then the E2E job runs one leg per browser project: chromium and webkit
    And a failing leg does not cancel the other leg
    And both Playwright steps of a leg run only that leg's browser project
    And each leg keeps its Playwright report under its own name

  Scenario: The gated run stops itself before the job limit
    Given the CI workflow
    Then the gated Playwright step stops the run after at most 18 minutes
    And the gated step prints each test with its duration as it ends
    And the listed red-until step runs each of its leg's tests at once

  Scenario: The E2E job keeps what explains a slow or cancelled run
    Given the CI workflow
    Then the E2E job prints the runner's CPU model, CPU count and memory before the journeys
    And the E2E job prints the service logs when it fails or is cancelled
