# Sprint 4 ST-063a (FR-122; HAX G11; flows-sprint-04 §2): the UI half of drill_rationale.feature
# (tests/features/, ST-057, pure domain). P-01 shows each drill's reason as the player's own
# numbers, with "Show me" for the rallies behind them. Bound by Vitest + Testing Library in
# web/tests/features/drill-rationale-ui.test.tsx (the plan is read through MSW-free fakes there;
# the contract test web/tests/contract/plan.test.ts covers the wire).
@M5 @story-ST-063a @coaching @web
Feature: Every drill says why, on the plan page
  Each drill row on "Your training plan" says why it was chosen: the metric, its value and n,
  and "Show me" opens the rallies behind that number. A row without its reason is an error.

  Background:
    Given a plan whose drill "Serve to a target" targets "serve faults"
    And its citation is "AN-05" at 29% of 7 serves for side "A", low sample

  Rule: No drill row without a reason (QD-PL-04, HAX G11)

    Scenario: A drill whose citation is missing shows an error, not a blank
      Given the citation of "Serve to a target" is missing
      When the player opens their training plan
      Then the row "Serve to a target" says "We could not show why this drill was chosen."
      And the row "Serve to a target" has no "Show me" button

  Rule: The reason is the player's own numbers (FR-122)

    Scenario: Why this drill, on the plan page
      When the player opens their training plan
      Then the row "Serve to a target" says "Why: Serve faults: 29% of 7 serves"
      And the row "Serve to a target" says "low sample"

    Scenario: Show me the rallies behind the reason
      When the player opens their training plan
      And the player presses "Show me the rallies behind Serve faults, 29%"
      Then the evidence for "AN-05" side "A" of the cited match is shown
