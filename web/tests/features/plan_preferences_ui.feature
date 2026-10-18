# ST-063b P-02 "Your practice setup" (FR-121 UI step; flows-sprint-04 §3; api-sprint-04 §2.1).
# The domain scenarios of FR-121 are tests/features/training_plan.feature (backend steps); this
# file is the player's side of "she asks for a plan". Owner: senior-frontend-engineer.
# Component bindings: web/tests/unit/st-063b-plan-preferences-scenarios.test.tsx (Vitest).
# Browser journey: ST-065 E2E-04-01 (generate plan) and E2E-04-05 (keyboard, 320/360 px).
@M5 @story-ST-063b @coaching
Feature: The player tells the app her practice setup and asks for a plan
  Rule: The setup is checked before a plan is asked for

    Scenario: Minutes outside 15 to 180 are refused before any request
      Given Ivy is on "Your practice setup" for the first time
      When she enters 10 minutes per session and answers the other questions
      And she presses "Make my plan"
      Then the error summary says "Enter a number between 15 and 180"
      And no plan is requested

    Scenario: Without a tagged match she is sent to tag one and her answers stay
      Given Ivy has no tagged match
      And Ivy is on "Your practice setup" for the first time
      When she enters 30 minutes per session and answers the other questions
      And she presses "Make my plan"
      Then she is told "Tag a match first. Your plan is built from the rallies you tag."
      And the link "Your matches" goes to her matches
      And her answers stay

  Rule: A complete setup asks for the plan (FR-121)

    Scenario: Solo player with 30 minutes, 3 sessions a week and a wall
      Given Ivy is on "Your practice setup" for the first time
      When she enters 30 minutes per session and answers the other questions
      And she presses "Make my plan"
      Then the plan is requested for 30 minutes, 3 sessions a week, 1 player, a wall and intermediate level
      And she is taken to her training plan

  Rule: Regenerating keeps the last preferences

    Scenario: Changing the setup starts from the last answers
      Given Ivy's current plan was made for 45 minutes, 2 sessions a week, 2 players, a ball machine and advanced level
      When she opens "Your practice setup"
      Then those answers are already chosen
      And she is told "This replaces your current plan."
