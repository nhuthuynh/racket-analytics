# FIX-04-2c (goal scorecard G04-03 a and c). Owner: senior-qa-engineer.
# Binding: backend/tests/features/test_goal_metric_markers.py: a real pytest run of the coaching
# unit suites with --junitxml, then scripts/measure/junit_rate.py as the scorecard §4 runs it.
# Root cause: `--require weakness_golden` matched test ids, and a JUnit report names no marker,
# so the method failed closed on a passing run. Negative scenario first.
@ticket-FIX-04-2c
Feature: The G04-03 method finds the golden and property tests by their markers

  Scenario: A marker that no test in the report carries fails closed and is named
    Given the JUnit report of a run of "-m weakness_golden" on the coaching unit suites
    When the pass rate is read requiring the marker "plan_property"
    Then the pass rate check fails
    And it names the missing marker "plan_property"

  Scenario: The golden run meets the method by its marker
    Given the JUnit report of a run of "-m weakness_golden" on the coaching unit suites
    When the pass rate is read requiring the marker "weakness_golden"
    Then the pass rate check passes
    And 9 tests are selected, every one passed and none skipped

  Scenario: The property run meets the method by its marker
    Given the JUnit report of a run of "-m plan_property" on the coaching unit suites
    When the pass rate is read requiring the marker "plan_property"
    Then the pass rate check passes
    And 1 test is selected, every one passed and none skipped
