# Sprint 4 ST-062 (FR-124): "Not for me" guards (review round 1 on PR #128). A swap re-reads the
# stats and scans the drill library, so it is limited per account (threat-notes-sprint-04
# T4-PL-6, SEC-S4-TM-01); and it needs the live citations, so it never runs on a plan whose
# source match was deleted (T4-PL-9). Real database, real drill library (content/drills),
# matches tagged through the API.
# Steps: backend/tests/features/test_plan_swap_guards.py.
@M5 @story-ST-062 @coaching
Feature: Plan swap guards
  A player who says "Not for me" many times in a row is asked to wait, and a player whose plan
  cites a match they deleted is asked to reload the plan instead of getting a drill that cites it.

  Rule: Swaps are limited to 120 per account per hour

    Scenario: The 121st swap in an hour is refused with a time to retry
      Given "ivy" has tagged the worked example
      And "ivy" has a plan as a group of 4 with every kind of equipment
      And "ivy" has sent 120 swaps in the last hour
      When "ivy" says "Not for me" to the second drill of the first session because "My wrist hurts"
      Then the answer is 429 "rate_limited" with a time to retry
      And the saved plan is unchanged and stores no reason
      And "carlos" can still send a swap

  Rule: A swap never cites a deleted match

    Scenario: A swap after a source match is deleted asks to reload the plan
      Given "ivy" has tagged the worked example
      And "ivy" has a plan as a group of 4 with every kind of equipment
      And "ivy" has deleted the worked example match
      When "ivy" says "Not for me" to the second drill of the first session because "My wrist hurts"
      Then the answer is 409 "plan_conflict" with the reason "Your plan changed. Reload it."
      And the saved plan is unchanged and stores no reason
