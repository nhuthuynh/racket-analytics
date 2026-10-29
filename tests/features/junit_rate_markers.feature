# Sprint 4 fix wave, QA-VERIFY04R3-02-08 (senior-qa-engineer; retro 4 C2; G04-03, G04-11 (a)).
# Written before the fix. Binding: infra/tests/test_junit_rate_markers_scenarios.py (real pytest
# runs of the backend and infra suites, the real scripts/measure/junit_rate.py).
@nfr-073 @ticket-QA-VERIFY04R3-02-08
Feature: The pass-rate method finds a test by its marker and every IT id by its name

  Rule: A required marker counts only when a selected test carries it

    Scenario: A marker no selected test carries is reported missing
      Given a JUnit report of the backend tests marked "weakness_golden"
      When the pass-rate method requires "plan_property"
      Then the method fails closed naming "plan_property" as missing

    Scenario: A required marker is found in the report of its tests
      Given a JUnit report of the backend tests marked "weakness_golden"
      When the pass-rate method requires "weakness_golden"
      Then the method passes with every selected test passed

  Rule: Every Sprint 4 IT id is found by its test name

    Scenario Outline: The G04-11 (a) method finds <id> in infra/tests
      Given a JUnit report of the infra file "<file>" without its live-stack variant
      When the G04-11 (a) method requires "<id>"
      Then the method passes with every selected test passed

      Examples:
        | id            | file                    |
        | test_it_04_11 | test_seed_demo_plan.py  |
        | test_it_04_15 | test_check_red_first.py |
