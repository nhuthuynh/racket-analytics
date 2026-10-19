# Sprint 4 ST-063c (FR-124; flows-sprint-04 §4 P-03; HAX G8, G15): the "Not for me" UI half of
# tests/features/plan_follow_through.feature (ST-062, API): "Not for me" swaps a drill. Bound by
# Vitest + Testing Library in web/tests/features/plan-not-for-me-ui.test.tsx (the contract test
# web/tests/contract/plan-follow-through.test.ts covers the wire).
@M5 @story-ST-063c @coaching @web
Feature: Swapping a drill, on the plan page
  A player swaps a drill that is not for them for another that works on the same thing.

  Background:
    Given a plan whose first session is "Session 1 of 3" with the drill "Serve to a target"

  Rule: "Not for me" swaps for a drill that works on the same thing (FR-124)

    Scenario: No other drill fits
      Given no other drill fits "Serve to a target"
      When the player says "Not for me" to "Serve to a target" with the reason "too hard"
      Then the dialog says "No other drill fits your setup for this. Your plan is unchanged."
      And the plan still has "Serve to a target"

    Scenario: Swap a drill
      When the player says "Not for me" to "Serve to a target"
      Then "Deep serves" replaces it and has the focus
      And the page says "Swapped for Deep serves."
