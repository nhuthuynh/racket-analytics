# CI-PR-GATE (user request 2026-10-08; PO rule 2026-10-07). Owner: sre-devops-engineer.
# Written before implementation. Binding: infra/tests/test_merge_ready_scenarios.py runs
# scripts/ci/merge_ready.py over HTTP against a local GitHub API stub.
@ticket-CI-PR-GATE @nfr-077 @nfr-078
Feature: Merge readiness of a pull request into main
  Rule: A PR merges only when every CI job incl. ci-gate is green and the principal-engineer
        and a senior reviewer both approve its head SHA

    Scenario: A failed CI job refuses the merge
      Given a pull request into main whose CI job "Integration" failed on the head
      And the principal-engineer and the senior-qa-engineer approved the head
      When the orchestrator runs the merge check on the head
      Then the merge is refused naming "Integration"

    Scenario: An approval given on an older commit does not count
      Given a pull request into main whose CI is green on the head
      And the principal-engineer approved the head
      And the senior-qa-engineer approved only an older commit
      When the orchestrator runs the merge check on the head
      Then the merge is refused naming "senior"

    Scenario: A missing senior verdict refuses the merge
      Given a pull request into main whose CI is green on the head
      And the principal-engineer approved the head
      When the orchestrator runs the merge check on the head
      Then the merge is refused naming "senior"

    Scenario: A ci-gate still running refuses the merge
      Given a pull request into main whose ci-gate is still running on the head
      And the principal-engineer and the senior-qa-engineer approved the head
      When the orchestrator runs the merge check on the head
      Then the merge is refused naming "ci-gate"

    Scenario: Green CI and both approvals on the head allow the merge
      Given a pull request into main whose CI is green on the head
      And the principal-engineer and the senior-qa-engineer approved the head
      When the orchestrator runs the merge check on the head
      Then the merge is allowed
