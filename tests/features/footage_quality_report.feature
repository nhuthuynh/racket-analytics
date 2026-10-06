# Sprint 1 §7.6 (ST-019, stretch). Owner: senior-qa-engineer. Binding: web/e2e/sprint-01/footage-quality-report.spec.ts.
@M0 @story-ST-019
Feature: Footage quality report
  Rule: The report explains consequences and never blocks

    Scenario: 30 fps video
      Given Ivy uploaded a 1080p video recorded at 30 fps
      When the quality report is shown
      Then it says which results may be less accurate and which are unaffected
      And she can continue to tag the match
