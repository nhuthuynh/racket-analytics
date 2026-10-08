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

    Scenario: The principal-engineer requesting changes on the head refuses the merge
      Given a pull request into main whose CI is green on the head
      And the principal-engineer and the senior-qa-engineer approved the head
      And the principal-engineer then requested changes on the head
      When the orchestrator runs the merge check on the head
      Then the merge is refused naming "principal-engineer: Verdict: CHANGES REQUESTED"

    Scenario: An approval posted by an outside GitHub user does not count
      Given a pull request into main whose CI is green on the head
      And the principal-engineer approved the head
      And an outside GitHub user posted an approval as the senior-qa-engineer
      When the orchestrator runs the merge check on the head
      Then the merge is refused naming "senior reviewer: no latest"

    Scenario: An approval that was never submitted does not count
      Given a pull request into main whose CI is green on the head
      And the principal-engineer approved the head
      And the senior-qa-engineer has an unsubmitted approval on the head
      When the orchestrator runs the merge check on the head
      Then the merge is refused naming "senior reviewer: no latest"

    Scenario: A newer CI run that failed refuses the merge despite an older green run
      Given a pull request into main whose CI was green on the head
      And a newer CI run of the same workflow then failed on the head
      And the principal-engineer and the senior-qa-engineer approved the head
      When the orchestrator runs the merge check on the head
      Then the merge is refused naming "check 'ci-gate' is failure"

    Scenario: A label re-run supersedes the cancelled CI run it replaced
      Given a pull request into main whose CI run was cancelled by a label re-run
      And the label re-run of the same workflow is green on the head
      And the principal-engineer and the senior-qa-engineer approved the head
      When the orchestrator runs the merge check on the head
      Then the merge is allowed

    Scenario: Green CI and both approvals on the head allow the merge
      Given a pull request into main whose CI is green on the head
      And the principal-engineer and the senior-qa-engineer approved the head
      When the orchestrator runs the merge check on the head
      Then the merge is allowed
