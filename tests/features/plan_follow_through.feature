# Sprint 4 ST-062 (FR-124): following the plan through. "Mark done" is idempotent by the client's
# op id, so an offline client may replay it (api-sprint-04 §3.1). The "Not for me" swap rule is
# added by ST-062-part2. Real database, real drill library
# (content/drills), matches tagged through the API.
# Steps: backend/tests/features/test_plan_follow_through.py.
@M5 @story-ST-062 @coaching
Feature: Plan follow-through
  A player working through their plan marks sessions done, even when the phone was offline and
  sends the same mark twice.

  Rule: Marking a session done is idempotent

    Scenario: Mark done offline twice
      Given "ivy" has tagged the worked example
      And "ivy" has a plan as a solo player with a wall, 30 minutes per session, 3 sessions a week
      When "ivy" marks the first session done with the op id "op-offline-1"
      And "ivy" sends the same op "op-offline-1" again when back online
      Then the second answer is the first one, replayed, at the same plan version
      And "ivy" reads the first session done once and the plan version raised by 1
