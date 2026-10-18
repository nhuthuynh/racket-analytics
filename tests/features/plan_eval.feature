# Sprint 4 ST-060 (NFR-005 a; QD-QG-S7; G04-04): the code-grader eval on rules-only plans.
# Steps: backend/tests/features/test_plan_eval.py. The eval set is backend/tests/evals/plan_cases
# (synthetic tag scripts plus preferences); the drills are the real content/drills library.
# IT-04-16 runs the same eval through the racket-plan-eval CLI.
@M5 @story-ST-060 @coaching
Feature: Code-grader eval on rules-only plans
  Every eval case is planned 3 times by the rules-only workflow and graded by code: every drill
  id@version exists in the library and is reviewed, every assignment cites a metric that the
  stats show with its value and n, and QD-PL-01..03 hold. A case passes only when all 3 runs
  pass and are byte-identical (pass^3).

  Scenario: A violating plan is caught
    Given the eval case "pe-13"
    And a planner that starts every session of its plan with a weakness drill instead of a warm-up
    When the eval runs 3 times
    Then the case "pe-13" fails under "QD-PL-03"
    And the eval exits 1

  Scenario: A citation the stats do not show is caught
    Given the eval case "pe-13"
    And a planner that cites one more serve than the stats show
    When the eval runs 3 times
    Then the case "pe-13" fails under "CITE"
    And the eval exits 1

  Scenario: A plan that changes between runs is caught
    Given the eval case "pe-13"
    And a planner whose second run gives a different plan
    When the eval runs 3 times
    Then the case "pe-13" fails under "pass^3"
    And the eval exits 1

  Scenario: The eval set passes at pass^3
    Given the eval set
    When the eval runs 3 times
    Then at least 30 cases ran
    And every case passed all 3 runs with byte-identical output
    And the eval exits 0
