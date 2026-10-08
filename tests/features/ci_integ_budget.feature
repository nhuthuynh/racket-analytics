@nfr-073 @ci-integ-budget
Feature: The integration suite stays inside its 600 s budget in parallel, without weakening the gate
  The NFR-073 integration budget (600 s) wraps the unit, integration, scenario and regression
  suites with branch coverage. The suite runs in parallel test workers, each on its own session
  database of one Postgres cluster. Some migrations create objects that belong to the whole
  cluster, not to one database (migration 0012 creates the role racket_media_worker), so
  workers that migrate their own databases at the same moment must not race to create them.

  Scenario: Workers on a fresh cluster race when nobody migrated the base database first
    Given a fresh Postgres cluster
    And a migration that creates a role for the whole cluster if it is missing
    When 4 test workers each migrate their own session database at the same moment
    Then at least one worker fails on the duplicate role

  Scenario: The integration job migrates the base database before the parallel workers start
    Given a fresh Postgres cluster
    And a migration that creates a role for the whole cluster if it is missing
    When the integration job's migrate step runs on the base database
    And 4 test workers each migrate their own session database at the same moment
    Then every worker's database reaches the migration head

  Scenario: The budget still times the full selection with coverage
    Given the CI workflow
    Then the budgeted step runs the nightly flaky-report selection with branch coverage
    And the integration budget is 600 seconds
    And the migrate step runs before the budgeted step and outside the budget
