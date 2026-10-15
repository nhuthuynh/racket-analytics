# FIX-03-2d (goal metric DEMO-03; sprint-03 §12 step 10; NFR-038, NFR-071, NFR-078; ADR 0014).
# Binding: infra/tests/test_demo_test_report_scenarios.py (the script run as the verifier runs it,
# on a report directory, a review-rounds ledger and a goal scorecard written to a temp dir).
# Step 10 of the demo shows the scorecard and the test report with "open defects (0)". The
# report is computed, never typed, so the demo is never reported as given while a blocker or
# major finding is open or a report file is missing (fail closed).
@ticket-FIX-03-2d
Feature: The sprint demo's step 10 test report is computed and fails closed
  As the engineering-manager running the sprint review demo
  I want step 10's test report computed from the verifier's reports and the live ledger
  So that "open defects (0)" and "12 of 12 met" are only shown when they are true

  Rule: Any open defect, short scorecard or missing report fails step 10

    Scenario: An open blocker in the ledger fails step 10 and is named
      Given a complete passing verifier report directory
      And a ledger with an open blocker "PD-R1S3-01" and an open major "PE-PR24-01"
      And a scorecard whose latest totals are "12 of 12 met"
      When the step 10 report runs
      Then step 10 fails
      And it names "open defects: 2 (PD-R1S3-01, PE-PR24-01)"

    Scenario: A scorecard short of every goal row fails step 10
      Given a complete passing verifier report directory
      And a ledger with no open blocker or major finding
      And a scorecard whose latest totals are "11 of 12 met"
      When the step 10 report runs
      Then step 10 fails
      And it names "scorecard: 11 of 12 met"

    Scenario: A missing mutation report fails step 10 instead of being skipped
      Given a complete passing verifier report directory
      And the report "mutation-stats.json" is missing
      And a ledger with no open blocker or major finding
      And a scorecard whose latest totals are "12 of 12 met"
      When the step 10 report runs
      Then step 10 fails
      And it names "mutation starter stats: missing mutation-stats.json"

    Scenario: A ledger without a review table is refused
      Given a complete passing verifier report directory
      And a ledger without a review table
      And a scorecard whose latest totals are "12 of 12 met"
      When the step 10 report runs
      Then the step 10 report is refused as unreadable

  Rule: Step 10 passes only when every item passes

    Scenario: Every report passing, 0 open defects and every goal met pass step 10
      Given a complete passing verifier report directory
      And a ledger with no open blocker or major finding
      And a scorecard whose latest totals are "12 of 12 met"
      When the step 10 report runs
      Then step 10 passes
      And it names "open defects: 0"
      And it names "evidence crawl: E2E-03-02 1/1 passed"
