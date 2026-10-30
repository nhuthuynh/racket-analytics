# Sprint 4 fix wave, FIX-04-4a (senior-qa-engineer; VERIFY04R4-01, G04-11 (d)).
# Written before the fix. Binding: infra/tests/test_goal_scorecard_integration_budget_scenarios.py
# (real bash and the real scripts/ci/run_with_budget.py run the scorecard's commands and
# CI's steps; only the backend suite itself is replaced by a recorder of what would run).
@nfr-073 @ticket-FIX-04-4a
Feature: The goal method times the integration suite the way CI's NFR-073 gate does
  NFR-073 gives the backend suites 600 s. CI runs them in parallel workers after migrating
  the base database once, outside the budget (ADR 0048). A goal method that times another
  form of the suite measures something the gate never runs.

  Scenario: The integration line inherited from Sprint 3 is not the gate's form
    Given the integration budget line of the Sprint 3 method for G03-11
    When it is compared with CI's budgeted backend-suites step
    Then the method is reported as timing one serial process
    And the method is reported as timing another selection

  Scenario: The G04-11 method runs what CI's integration job runs
    Given the integration budget block of the Sprint 4 method for G04-11
    When the block and CI's migrate and budgeted steps run with the suite recorded, not run
    Then the budgeted suite runs with the same pytest arguments as CI's, report paths aside
    And the base database is migrated before the budgeted suite, outside the budget
