# Flag-on browser specs (QA-VERIFY04R3-05/-06; scorecard G04-07, G04-08; api-sprint-04 §10).
# Bound in the browser by the Playwright test whose title starts with the scenario's E2E id
# (web/e2e/sprint-04/flags-on/*.spec.ts, project `flags-on`); the binding is checked by
# web/tests/unit/e2e-helpers-sign-in.test.ts. On the flags-on stack the age question (A-10) comes
# between the sign-in link and the first page, so every flag-on spec answers it once, as an adult,
# through the shared sign-in helper before it reaches its own screen.
@M5 @story-ST-071 @story-ST-072b
Feature: Flag-on screens are reached and checked with every Sprint 4 flag on
  With the age question, the video setting, the training choice and the quotas all on, a new
  player signs in, answers the age question as an adult, and reaches the privacy settings (R-01)
  and the over-limit messages (Q-10). Each screen passes axe and the 24 by 24 px target check at
  320 and 360 px wide.

  @E2E-04-07
  Scenario: retention choice with deletion dates and training use, by keyboard, at 320 and 360 px
    Given every Sprint 4 flag is on and Ivy signs in with a new address
    And she answers "Yes, I am 18 or over"
    When she chooses "30 days" and turns training use on, by keyboard
    Then the privacy settings show both choices saved
    And the page passes axe and the target check at 320 and 360 px with no sideways scrolling

  @E2E-04-08
  Scenario: Match limit: Q-07 says when a new match can start and keeps the answers, at 320 and 360 px
    Given every Sprint 4 flag is on and Ivy signs in with a new address
    And she answers "Yes, I am 18 or over"
    And she has reached the hourly match limit
    When she creates a match on "Check your answers"
    Then the alert says when she can start a new match and that her answers are kept
    And the page passes axe and the target check at 320 and 360 px with no sideways scrolling

  @E2E-04-08
  Scenario: Storage full: U-01 says how much is used of the limit, at 320 and 360 px
    Given every Sprint 4 flag is on and Ivy signs in with a new address
    And she answers "Yes, I am 18 or over"
    And her storage is almost full
    When she creates a match on "Check your answers"
    Then the alert says how much of the limit she has used and that nothing was saved
    And the page passes axe and the target check at 320 and 360 px with no sideways scrolling
