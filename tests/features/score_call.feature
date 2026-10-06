# Sprint 2 §7.2 (QA-ACC, written for ST-029). Owner: senior-qa-engineer.
# Browser binding only: web/e2e/sprint-02/announcements.spec.ts (E2E-02-03).
@M0 @story-ST-029 @needs-verification
Feature: Score call and announcement
  The three-number call format is unverified [DOM G1 R6].

  Rule: Every tag is announced without moving focus

    Scenario: Screen-reader user tags a rally
      Given Ivy uses a screen reader while tagging
      When she tags rally 7 as won by the other side
      Then she hears the rally number, the winner and the new score
      And her focus stays on the tagging controls
