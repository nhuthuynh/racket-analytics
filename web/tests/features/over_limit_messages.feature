# Sprint 4 ST-072b (FR-160; NFR-023; flows-sprint-04 §7 Q-10; interim-wording-sprint-04 §5).
# Bound in web/tests/features/over-limit-messages.test.tsx: the real Q-07 (MatchSetup) with the
# API refusal of api-sprint-04 §7. Flag-on E2E: E2E-04-08. The storage half is ST-072b-part2.
@M5 @story-ST-072b @matches @web
Feature: The player is told when they can start a new match
  With quotas on, the API refuses a match over the hourly limit. The player sees when they can
  start a new match, in plain words, and keeps their answers.

  Rule: A refused match says when the player can start a new one

    Scenario: The 11th match refused without a time still gets a safe message
      Given the API refuses "Create match and upload" with "rate_limited" and no retry time
      When the player creates the match on "Check your answers"
      Then the alert says "You can start a new match within the hour."
      And the alert says "Your answers are kept."
      And the alert shows no error code

    Scenario: The 11th match refused with a time
      Given the API refuses "Create match and upload" with "rate_limited" until "2026-10-29T14:05:00Z"
      When the player creates the match on "Check your answers"
      Then the alert says "You can start a new match at" and that time in the player's local 24-hour "HH:MM"
