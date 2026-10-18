# Sprint 4 ST-062 (FR-124): following the plan through. "Not for me" swaps one drill for another
# reviewed drill that trains the same metric; "Mark done" is idempotent by the client's op id, so
# an offline client may replay it (api-sprint-04 §3). Real database, real drill library
# (content/drills), matches tagged through the API.
# Steps: backend/tests/features/test_plan_follow_through.py.
@M5 @story-ST-062 @coaching
Feature: Plan follow-through
  A player working through their plan marks sessions done, even when the phone was offline and
  sends the same mark twice, and says "Not for me" to a drill to get another one that trains the
  same weakness, as long as one fits their setup.

  Rule: "Not for me" swaps a drill only for one that fits

    Scenario: No alternative drill leaves the plan unchanged
      Given "ivy" has tagged the worked example
      And "ivy" has a plan as a solo player with a wall, 30 minutes per session, 3 sessions a week
      And "ivy" has said "Not for me" to the second drill of the first session until no other drill fits
      When "ivy" says "Not for me" to that drill again
      Then the answer is 409 "no_alternative" with the reason "No other drill fits your settings for this."
      And "ivy" reads the same plan at the same version as before

    Scenario: Swap a drill
      Given "ivy" has tagged the worked example
      And "ivy" has a plan as a solo player with a wall, 30 minutes per session, 3 sessions a week
      When "ivy" says "Not for me" to the second drill of the first session because "My wrist hurts"
      Then the answer is 200 with the session and the next plan version
      And the assignment keeps its id and gets another reviewed drill for the same metric
      And the plan still keeps every rule QD-PL-01 to QD-PL-03
      And the swapped-out drill is not offered again for that assignment

  Rule: Marking a session done is idempotent

    Scenario: Mark done offline twice
      Given "ivy" has tagged the worked example
      And "ivy" has a plan as a solo player with a wall, 30 minutes per session, 3 sessions a week
      When "ivy" marks the first session done with the op id "op-offline-1"
      And "ivy" sends the same op "op-offline-1" again when back online
      Then the second answer is the first one, replayed, at the same plan version
      And "ivy" reads the first session done once and the plan version raised by 1
