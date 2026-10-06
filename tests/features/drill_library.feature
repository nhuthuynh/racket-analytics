# Sprint 3 §7.6 (QA-ACC-3, written for ST-053; FR-140). Owner: senior-qa-engineer.
# CLI binding: backend/tests/features/test_drill_library.py (racket-drill-lint over
# backend/tests/fixtures/drills-invalid/<rule>.json and content/drills).
@M5 @story-ST-053 @fr-140
Feature: Drill library integrity
  Scenario Outline: A drill file breaks a rule
    Given a drill file that <breaks>
    When the library is validated
    Then validation fails naming the drill and "<reason>"
    Examples:
      | breaks                                   | reason              |
      | targets metric "AN-99"                   | unknown metric      |
      | lists itself as its own progression      | progression cycle   |
      | lasts 46 minutes                         | duration over 45    |
      | has a success criterion with no number   | criterion no number |
      | has neither a source nor a rationale     | no source           |

  Scenario: Plan keeps a deprecated drill
    Given a drill at version 2 that was later deprecated
    When the library is validated
    Then version 2 is still present with its content
