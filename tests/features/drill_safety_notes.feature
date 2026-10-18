# FIX-04-1d (G04-05 (e); QD-DR-04; drill-review-checklist C5; FR-141). Owner: pickleball-domain-coach.
# CLI binding: backend/tests/features/test_drill_safety_notes.py (racket-drill-lint over
# backend/tests/fixtures/drills-safety/ and content/drills).
@M5 @fr-141 @qd-dr-04
Feature: Safety notes on reviewed drills
  A reviewed drill whose content involves lobs, diving, sprints or footwork carries safety notes,
  so a player is never handed such a drill without them.

  Scenario: A reviewed footwork drill without safety notes is refused
    Given a coach-reviewed drill involving footwork with empty safety notes
    When the library is validated
    Then validation fails naming the drill and "safety notes missing"

  Scenario: A draft or deprecated drill is not yet handed to players
    Given a draft drill and a deprecated drill involving footwork with empty safety notes
    When the library is validated
    Then validation passes

  Scenario: Every reviewed drill of the library that needs safety notes has them
    # A safety trigger is lob, dive or diving, sprint, or footwork in the drill content.
    Given the drill library
    When the library is validated
    Then validation passes
    And no current reviewed drill with a safety trigger has empty safety notes
