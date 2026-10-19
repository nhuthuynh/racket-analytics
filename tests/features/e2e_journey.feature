# R1 journey (QD §7; sprint-04 §7.4, ST-065). Bound in the browser by the Playwright test whose
# title starts with the scenario's E2E id (web/e2e/sprint-04/journey-v3.spec.ts); the binding is
# checked by web/tests/unit/e2e-helpers-journey-binding.test.ts (an untagged or unbound scenario
# fails it). Rules are provisional (unofficial scoring), so the plan is too.
@M0 @story-ST-065
Feature: R1 journey

  @E2E-04-01
  Scenario: Upload to plan
    Given Ivy signs in on a fresh local stack
    When she uploads a match, Quick Tags it and opens the score sheet and the stats
    And she asks for a plan
    Then every drill in her plan cites a metric, its value, its n and the rallies behind it
    And she can mark a session done offline and swap a drill with "Not for me"
