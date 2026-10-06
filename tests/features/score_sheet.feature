# Sprint 2 §7.3 (QA-ACC, written for ST-030). Owner: senior-qa-engineer.
# API binding: backend/tests/features/test_score_sheet.py ("Read the match without the video",
# "Rules not yet verified"). Browser binding: web/e2e/sprint-02/score-sheet.spec.ts (all three,
# the narrow screen at 320 and 360 px).
@M0 @story-ST-030 @nfr-033
Feature: Score sheet
  Rule: The score sheet is a complete text record of the match

    Scenario: Read the match without the video
      Given Ivy has tagged a 3-game match
      When she opens the score sheet
      Then every rally shows its number, server, score before and after, winner and ending
      And corrected rallies are marked "corrected by you" in text

    Scenario: Narrow phone screen
      Given Ivy opens her score sheet on a screen 360 pixels wide
      Then every rally's details can be read without scrolling sideways

  Rule: Unverified rules are never presented as official

    Scenario: Rules not yet verified
      Given the active rules preset contains an unverified rule
      When Ivy opens any score sheet
      Then she sees "unofficial scoring (rules not yet verified)"
