# Sprint 2 §7.1 and §14.3.5 (QA-ACC, written for ST-027). Owner: senior-qa-engineer.
# API binding: backend/tests/features/test_quick_tag.py (the outcome the API decides).
# Browser binding: web/e2e/sprint-02/quick-tag.spec.ts (on-screen copy, the video moment).
# Ivy is on side A with Dana; Carlos and Sam are side B. The scores are the provisional
# preset's (ADR 0009), so the score values themselves stay unofficial (FR-055). Rallies before
# the one a scenario names are the 6 journey rallies of `taglib.JOURNEY_TAGS`, then rallies won
# by B, A, B; so the call before rally 10 is "0-3-1" (the plan's "5-5-1" before rally 10 cannot
# be reached in 9 rallies: 10 points need at least 10 rallies; decision-log 2026-10-05).
@M0 @story-ST-027 @nfr-012
Feature: Quick Tag
  A player records each rally's outcome by hand; the rules engine scores it.

  Background:
    Given Ivy is tagging her doubles match "Saturday doubles"

  Rule: Each tagged rally is scored immediately

    Scenario: Tag a rally
      Given rally 7 has been marked from start to end
      When she records it as won by the other side with "unforced error" by herself
      Then rally 7 shows the new score
      And the error is attributed to her
      And the video continues from the end of rally 7, ready to mark rally 8

    Scenario: Responsible player skipped
      Given Ivy has tagged rally 8 without choosing a responsible player
      When she opens the score sheet
      Then rally 8 shows its winner and ending
      And rally 8 shows "player not tagged"

    Scenario Outline: Every ending can be recorded
      Given rally 9 has been marked from start to end
      When she records it as won by her side with ending "<ending>"
      Then rally 9 shows ending "<ending>" on the score sheet
      Examples:
        | ending         |
        | winner         |
        | unforced error |
        | forced error   |
        | fault          |

    Scenario: A replay does not change the score
      Given the score before rally 10 is "0-3-1"
      When she records rally 10 as a replay
      Then the score after rally 10 is still "0-3-1"

  Rule: A player on the wrong side cannot be blamed

    Scenario: Error attributed to the winning side
      Given rally 11 has been marked from start to end
      When she records it as won by her side with "unforced error" by her own partner
      Then she is told the player who made the error must be on the side that lost the rally

  @nfr-060
  Rule: Tagging needs a received video and the latest version

    Scenario: 14.3.5 Tag before the video is received
      Given Ivy's match has no video yet
      When she tries to tag a rally
      Then she is told to wait until the video is received
      And no rally is saved

    Scenario: Two devices tag at once
      Given Ivy tags the same match on her phone and her laptop
      When both record rally 8 at the same moment
      Then one tag is saved
      And the other device is told the match changed and shows the latest score
