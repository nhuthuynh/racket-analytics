# Sprint 2 §7.1 (QA-ACC, written for ST-028a). Owner: senior-qa-engineer.
# Browser binding only: web/e2e/sprint-02/keyboard-tagging.spec.ts (E2E-02-02); nothing here is
# decided by the API.
@M0 @story-ST-028 @nfr-034
Feature: Keyboard tagging
  Rule: Keyboard and touch give the same result

    Scenario: Keyboard only
      Given Ivy uses a keyboard and no pointer
      When she tags rallies 1 to 6 of the fixture match using keys only
      Then the score sheet is identical to tagging the same rallies with taps

  Rule: Shortcuts are discoverable and can be changed

    Scenario: Show the key map
      Given Ivy is on the tagging screen
      When she presses "?"
      Then she sees every tagging shortcut and what it does

    Scenario: Turn single-key shortcuts off
      Given Ivy has turned single-key shortcuts off
      When she presses "1" while the video has focus
      Then no winner is recorded
