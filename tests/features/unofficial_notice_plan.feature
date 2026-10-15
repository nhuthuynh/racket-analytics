# Sprint 3, FIX-03-2c (PD-R1S3-01-PM; DR-03 R3-3 option a; FR-055, NFR-003; OQ-01).
# Written by product-manager in the ticket PR. Steps: infra/tests/test_unofficial_notice_scenarios.py.
# Integration: infra/tests/test_unofficial_notice_shipped.py. Unit: infra/tests/test_unofficial_notice.py.
# Checker: scripts/measure/unofficial_notice.py.
@story-FIX-03-2c @fr-055
Feature: The sprint plan places the "unofficial" notice where the product shows it
  While the rules are provisional, no number on a stats page may be read as official. The product
  says so once per stats page, before the first card (DR-03 R3-3). A plan that still promises the
  notice on every metric card contradicts the screen, the metric dictionary and the decision.

  Rule: A plan that contradicts the one-notice-per-page decision is reported

    Scenario: A plan that still says every metric card is reported
      Given a sprint plan whose rulebook line says "the score sheet and every metric card say \"unofficial\""
      And a metric dictionary whose rule 0.5 says "once, before the first card"
      When the plan is checked against the decision
      Then the check fails, naming "every metric card"

    Scenario: A plan without a rulebook line is refused
      Given a sprint plan with no rulebook line
      And a metric dictionary whose rule 0.5 says "once, before the first card"
      When the plan is checked against the decision
      Then the check is refused, naming "Rulebook PDFs later"

    Scenario: A metric dictionary that drops "before the first card" is reported
      Given a sprint plan whose rulebook line says "the score sheet and every stats page say \"unofficial\", once before the first card"
      And a metric dictionary whose rule 0.5 says "on each card"
      When the plan is checked against the decision
      Then the check fails, naming "metric-dictionary rule 0.5"

  Rule: The shipped plan and dictionary agree with the decision

    Scenario: The shipped sprint-03 plan says every stats page, once before the first card
      Given the shipped sprint-03 plan
      And the shipped metric dictionary
      When the plan is checked against the decision
      Then the check passes
