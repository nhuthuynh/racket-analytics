# FIX-03-2b (goal metric G03-12-PE-PR24-01; ledger row PE-PR24-01). Owner: principal-engineer.
# Written before implementation. Binding: infra/tests/test_merged_verdict_scenarios.py runs
# scripts/measure/merged_verdict.py over HTTP against the local GitHub API stub.
@ticket-FIX-03-2b @nfr-077
Feature: A reviewer's verdict on the head a pull request was merged at
  Rule: a merged pull request meets the review rule for a role only when that role's latest
        verdict is "Verdict: APPROVE" given on the merged head

    Scenario: A changes-requested verdict on an earlier head is not a verdict on the merged head
      Given a pull request merged at its head
      And the principal-engineer's latest verdict is CHANGES REQUESTED on an earlier commit
      And a pending review by the repository owner on another commit
      When the principal-engineer verdict on the merged head is checked
      Then it is not met, naming "principal-engineer"

    Scenario: A pull request that is not merged has no merged head
      Given a pull request that is still open
      And the principal-engineer approved its head
      When the principal-engineer verdict on the merged head is checked
      Then it is not met, naming "not merged"

    Scenario: An approval on the merged head given after the merge meets the rule
      Given a pull request merged at its head
      And the principal-engineer's latest verdict is CHANGES REQUESTED on an earlier commit
      And the principal-engineer later approved the merged head
      When the principal-engineer verdict on the merged head is checked
      Then it is met
