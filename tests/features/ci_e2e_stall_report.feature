# CI-E2E-JOURNEYS-TIMEOUT (NFR-074). Owner: senior-qa-engineer. Bound by
# infra/tests/test_ci_e2e_stall_report_scenarios.py, which runs the real Playwright of web/.
# CI-STALL-SCENARIO-RACE: the timeout is set past the measured start-up of the second test, and
# the interrupted test is named by a line printed when the run ends, not by the worker's late
# answer to the stop (docs/sprints/03/decisions/CI-STALL-SCENARIO-RACE.md).
@nfr-074 @ci-e2e-journeys-timeout
Feature: A Playwright run cut short by its global timeout still says what it was doing
  The gated E2E step stops itself at its global timeout instead of running into the job limit.
  That only helps if the stopped run still names the test it interrupted, prints the durations
  of the tests that ended, and writes its HTML report.

  Scenario: A run that reaches the global timeout names the interrupted test and keeps a report
    Given the gated Playwright step's reporters from the CI workflow, with a global timeout of at least 5 seconds set past the measured start-up of the second test
    When Playwright runs a spec whose first test passes and whose second test waits for 120 seconds
    Then the second test had started before the global timeout
    And the run fails within 30 seconds of its global timeout
    And the output names the second test as the one the timeout stopped
    And the output prints the first test with its duration
    And the HTML report is written

  @ci-stall-scenario-race
  Scenario: The interrupted test is named even when its worker does not answer the stop in time
    Given the gated Playwright step's reporters from the CI workflow, with a global timeout of at least 5 seconds set past the measured start-up of the second test
    When Playwright runs a spec whose first test passes and whose second test waits for 120 seconds, with its worker frozen from the second test's start until the run has ended
    Then the second test had started before the global timeout
    And the run fails within 30 seconds of its global timeout
    And the output names the second test as the one the timeout stopped
    And the HTML report is written
