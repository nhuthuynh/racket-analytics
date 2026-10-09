# CI-REDUNTIL-HANG (NFR-073, NFR-074). Owner: senior-qa-engineer. Bound by
# infra/tests/test_ci_reduntil_fail_fast_scenarios.py; the real-store path is
# backend/tests/integration/harness/test_ci_reduntil_step_bound.py.
@nfr-073 @ci-reduntil-hang
Feature: The listed red_until step ends fast and fails when a row waited instead of failing
  Main run 37961668800 ran the step for 15 minutes until the job limit cancelled it. Its rows
  send 174 MB to the object store while the store took writes at about 64 KiB/s, so each row
  sat until the 120 s per-test timeout, and the report counted a timed-out row as an
  expected red. A red_until row is expected to fail because its story is missing, not
  because it waited.

  Scenario: A row that timed out fails the report and is named
    Given a red_until run in which one row failed for its story and one row timed out
    When the red_until report reads the run
    Then the report fails
    And the report names the timed-out row

  Scenario: A run that stopped before every row ran fails the report
    Given a red_until run that collected 3 rows and reported 2
    When the red_until report reads the run
    Then the report fails
    And the report says that 2 of 3 rows ran

  Scenario: Every row ran and failed for its story
    Given a red_until run that collected 2 rows and reported 2 that failed for their story
    When the red_until report reads the run
    Then the report passes

  Scenario: The CI step bounds each row and the whole run
    Given the CI workflow
    Then the red_until step stops a row after at most 30 seconds
    And the red_until step stops the run after at most 90 seconds
    And the red_until step gives the report the number of rows it collected
    And the red_until step has its own time limit of at most 4 minutes
