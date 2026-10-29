# Sprint 4 SRE-VERIFY04R3-01 (G04-02 c; NFR-019 read side; coaching-plan §3 scope, §8): reading the plan
# again while nothing in its scope changed reuses the ranking and citations; any change of a
# scope match is read live. Steps: backend/tests/features/test_plan_read_scope.py.
@M5 @story-SRE-VERIFY04R3-01 @coaching
Feature: Reading the plan again is cheap and never out of date
  A player opens her plan many times a week. While her matches did not change, the plan is read
  without replaying them; a tag or a correction shows in the next read.

  Rule: A change of a scope match is read live

    Scenario: A correction after a read shows in the next read
      Given "ivy" has tagged the worked example and has a plan
      And "ivy" has read the plan
      When "ivy" corrects rally 3 of the match
      And "ivy" reads the plan
      Then the ranking read differs from the one read before

  Rule: An unchanged scope is not replayed

    Scenario: Reading the plan again replays none of the matches
      Given "ivy" has tagged the worked example and has a plan
      And "ivy" has read the plan
      When "ivy" reads the plan
      Then the plan read is the plan read before
      And the read replayed no scorebook and wrote nothing
