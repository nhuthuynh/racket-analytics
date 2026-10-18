# FIX-04-1b (goal scorecard G04-02; api-sprint-04 §2.1; ADR 0014, ADR 0033 rule 2).
# Owner: senior-backend-engineer. Binding: infra/tests/test_live_plan_request_body_scenarios.py
# (live_plan.py against the QA-HARNESS-4a HTTPS stub, made strict: POST /me/plan answers 422
# with the contract's field codes unless the body keeps the §2.1 table).
@ticket-FIX-04-1b
Feature: The live plan harness generates with the body the plan contract requires

  Scenario: A strict stack refuses a generate body without equipment and level
    Given a strict stub stack whose plan keeps every rule
    When a client posts a generate body without equipment and level
    Then the stack answers 422 naming "equipment" and "level" as required

  Scenario: The journey gets a plan from a strict stack and times every generation
    Given a strict stub stack whose plan keeps every rule
    When the plan harness runs 1 run with determinism 3
    Then it exits 0
    And every generate body the stack saw was accepted
    And the summary times 4 generations and 1 done

  Scenario: The load mode gets a plan from a strict stack before it measures GET /me/plan
    Given a strict stub stack whose plan keeps every rule
    When the plan harness runs the load mode at 20 RPS for 1 second
    Then it exits 0
    And every generate body the stack saw was accepted
    And the load summary counts 20 requests and none unexpected
