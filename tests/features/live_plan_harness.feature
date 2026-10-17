# QA-HARNESS-4a (goal scorecard G04-01..G04-03; QD-PL-01..04, QD-PL-06; ADR 0014, ADR 0033).
# Owner: senior-qa-engineer. Binding: infra/tests/test_live_plan_harness.py (live_plan.py against
# a local HTTPS stub of api-sprint-04 and a fake Mailpit). The harness never reads as a pass
# when it cannot see (fail closed).
@ticket-QA-HARNESS-4a
Feature: The live plan harness reports a broken plan as a failed step

  Scenario Outline: A plan breaking a rule is a failed step
    Given a stub stack whose plan <defect>
    When the plan harness runs 1 run with determinism 3
    Then it exits 1
    And the "<step>" step names "<rule>"

    Examples:
      | defect                                  | step          | rule                |
      | has a session over its 30-minute budget | plan_rules    | QD-PL-01            |
      | starts a session without a warm-up      | plan_rules    | QD-PL-03            |
      | cites a value the stats do not show     | citations     | QD-PL-04            |
      | changes its content on every generation | determinism   | differs             |
      | ranks the weaknesses in another order   | ranking       | ranking order       |
      | omits the limited-data note             | limited_data  | limited_data        |
      | replays a done as a new completion      | done          | replayed            |
      | keeps the drill on Not for me           | swap          | swap 200            |
      | swaps to a drill citing another metric  | swap          | swap 200            |
      | shows the plan to a second account      | other_account | other account codes |

  Scenario: Determinism is checked over 3 generations when no k is given
    Given a stub stack whose plan changes its content on every generation
    When the plan harness runs 1 run with the default determinism
    Then it exits 1
    And the "determinism" step names "differs across 3 generations"
    And the summary reports determinism k 3

  Scenario: It refuses a determinism k below 2, which could not see a difference
    Given a stub stack whose plan keeps every rule
    When the plan harness runs 1 run with determinism 1
    Then it exits 2
    And the stub saw no request

  Scenario: It refuses to start when the stack cannot be read
    Given no stack listening
    When the plan harness runs 1 run with determinism 3
    Then it exits 2

  Scenario: It refuses to start below the disk floor
    Given a stub stack whose plan keeps every rule
    When the plan harness runs with a disk floor above the free space
    Then it exits 2
    And the stub saw no request

  Scenario: A plan that keeps every rule passes every step, the timings and the reference
    Given a stub stack whose plan keeps every rule
    When the plan harness runs 1 run with determinism 3
    Then it exits 0
    And every step passed, with 4 generation timings, 1 done timing and 9 reference rows

  Scenario: The load mode measures GET /me/plan at the asked rate
    Given a stub stack whose plan keeps every rule
    When the plan harness runs the load mode at 20 RPS for 1 second
    Then it exits 0
    And the load summary counts 20 requests and none unexpected
