@fix-04-1c @g04-03
Feature: The G04-03 golden and property checks name the tests they require
  Goal metric G04-03 (a) and (c) are measured by pytest runs selected with the markers
  weakness_golden and plan_property, then checked with junit_rate.py. A JUnit test id is
  "file|classname::name"; a pytest marker is not part of it. A --require pattern that is a
  marker name therefore never matches, and junit_rate.py exits 1 although every selected test
  passed (QA-V04R1-01). The scorecard's checks require each coach comparison and the property
  test by their JUnit names instead.

  Scenario: A marker name used as a required pattern matches no JUnit test id
    Given the JUnit report of the real weakness_golden run
    When junit_rate.py checks it with "--require weakness_golden"
    Then junit_rate.py exits 1 and reports "weakness_golden" missing

  Scenario: The scorecard's golden check passes on the real golden run
    Given the G04-03 method in the Sprint 4 goal scorecard
    When its weakness_golden pytest run and its golden junit_rate.py check run as written
    Then the check exits 0 with nothing missing
    And each of the 7 scorecard comparisons is required by its own pattern

  Scenario: The scorecard's property check passes on the real property run
    Given the G04-03 method in the Sprint 4 goal scorecard
    When its plan_property pytest run and its property junit_rate.py check run as written
    Then the check exits 0 with nothing missing
    And the property test is required by its JUnit name
