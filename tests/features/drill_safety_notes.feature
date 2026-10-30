# QA-VERIFY04R3-09 (FR-140, FR-141; QD-DR-04; drill-review-checklist C5; G04-05 e).
# Owner: pickleball-domain-coach. CLI binding: backend/tests/features/test_drill_safety_notes.py
# (racket-drill-lint over one drill file and over content/drills). Negative scenarios first.
@needs-verification @story-QA-VERIFY04R3-09 @fr-140 @fr-141
Feature: Safety notes on reviewed movement drills
  A reviewed drill that makes the player move must say how to do it safely.

  Scenario Outline: A reviewed movement drill without a safety note
    Given a <status> drill tagged "<skill>" with an empty safety note
    When the drill is linted
    Then the lint fails naming the drill and "no safety note"
    Examples:
      | status         | skill    |
      | coach-reviewed | footwork |
      | verified       | movement |

  Scenario: A draft movement drill is not in the reviewed library
    Given a draft drill tagged "footwork" with an empty safety note
    When the drill is linted
    Then the lint passes

  Scenario: The starter library
    Given the starter drill library
    When the drill is linted
    Then the lint passes
    And the current version of pb.volley.line-volleys-no-step-in has a safety note
