# Sprint 4 ST-056 (FR-121; QD-PL-01..03): the rules-only TrainingPlan assembly, pure domain (no API,
# no database). Steps: backend/tests/features/test_training_plan.py. The steps build a small
# coach-reviewed test library (the reviewed starter drills arrive with ST-058a..c); IT-04-02a runs
# the same assembly over the real content/drills library. ST-061a adds the last rule: the plan
# saved through the repository on the real database (migration 0018) and read back by its owner.
@M5 @story-ST-056 @coaching
Feature: Rules-only training plan assembly
  From the top 3 weaknesses, the player's preferences and the reviewed drill library, a
  deterministic workflow builds a 2-week plan that never breaks the player's constraints.

  Background:
    Given the reviewed test library with warm-ups, wall, ball-machine and 4-player drills
    And the top weaknesses are "unforced errors" on "AN-04", "serve faults" on "AN-05" and "errors under pressure" on "AN-07:forced-error"

  Rule: Only drills that fit the player's setup are used (QD-PL-02)

    Scenario: No ball machine, no ball-machine drill
      Given a solo player with a wall and no ball machine, 30 minutes per session, 3 sessions a week
      When the plan is assembled
      Then the plan has 6 sessions over 2 weeks
      And no session uses a drill that needs a ball machine
      And no session uses a drill for more than 1 player
      And only coach-reviewed or verified drills that are not deprecated are used

    Scenario: A weakness that no drill fits is named instead of breaking a constraint
      Given a solo player with a wall and no ball machine, 30 minutes per session, 3 sessions a week
      When the plan is assembled
      Then the weakness "errors under pressure" is named "no drill fits your setup"
      And no session has a drill for "errors under pressure"

    Scenario: The same drill that needs a ball machine is used once the player has one
      Given a solo player with a wall and a ball machine, 30 minutes per session, 3 sessions a week
      When the plan is assembled
      Then some session uses a drill that needs a ball machine

  Rule: Plans fit the player's time (QD-PL-01; FR-121)

    Scenario: Solo player with 30 minutes
      Given a solo player with a wall and no ball machine, 30 minutes per session, 3 sessions a week
      When the plan is assembled
      Then every session lasts at most 30 minutes
      And every drill can be done by one player without a ball machine

    Scenario: Weekly time
      Given a player with 4 players, every setup, 60 minutes per session, 3 sessions a week and 150 minutes a week
      When the plan is assembled
      Then each week's sessions total at most 150 minutes
      And every session lasts at most 50 minutes

  Rule: Every session starts with a warm-up and no drill takes more than 40% (QD-PL-03)

    Scenario: Every session starts with a warm-up drill
      Given a solo player with a wall and no ball machine, 30 minutes per session, 3 sessions a week
      When the plan is assembled
      Then the first drill of every session is a "warm-up" drill of 5 to 10 minutes
      And no other drill of a session is a "warm-up" drill

    Scenario: No drill takes more than 40% of its session
      Given a solo player with a wall and no ball machine, 20 minutes per session, 2 sessions a week
      When the plan is assembled
      Then no drill is given more than 8 minutes

    Scenario: Without a warm-up that fits, no plan is made
      Given the library has no warm-up drill
      And a solo player with a wall and no ball machine, 30 minutes per session, 3 sessions a week
      When the plan is assembled
      Then no plan is made, with the reason "no_plan_fits"

  Rule: Assembly is deterministic

    Scenario: Same input, same plan
      Given a solo player with a wall and no ball machine, 30 minutes per session, 3 sessions a week
      When the plan is assembled 3 times, each time from the library in a different order
      Then the 3 plans are identical and have the same content digest

  Rule: A saved plan belongs to its owner and reads back identical (ST-061a; FR-121; NFR-051)

    @story-ST-061a
    Scenario: Another player's saved plan is not visible
      Given a solo player with a wall and no ball machine, 30 minutes per session, 3 sessions a week
      And the plan is assembled and saved for "ivy"
      When "carlos" reads his saved plan
      Then "carlos" has no saved plan

    @story-ST-061a
    Scenario: A saved plan reads back identical
      Given a player with 4 players, every setup, 60 minutes per session, 3 sessions a week and 150 minutes a week
      And the plan is assembled and saved for "ivy"
      When "ivy" reads her saved plan
      Then the plan read back is identical to the one saved, with the same content digest and version
