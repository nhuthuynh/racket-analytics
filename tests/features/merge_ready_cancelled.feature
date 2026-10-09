# CI-MERGE-READY-CANCELLED (bug in CI-PR-GATE). Owner: sre-devops-engineer.
# Written before the fix. Binding: infra/tests/test_merge_ready_cancelled_scenarios.py runs
# scripts/ci/merge_ready.py over HTTP against a local GitHub API stub.
@ticket-CI-MERGE-READY-CANCELLED @nfr-077 @nfr-078
Feature: A CI run cancelled by its concurrency group does not decide merge readiness
  Rule: A cancelled workflow run is not the current run when a non-cancelled run of the same
        workflow and event was created in the same second or later; among the others the
        newest counts

    Scenario: A newer cancelled CI run does not hide an older failure
      Given a pull request into main whose CI run failed on the head
      And a newer CI run of the same workflow was cancelled by the concurrency group
      And the principal-engineer and the senior-qa-engineer approved the head
      When the orchestrator runs the merge check on the head
      Then the merge is refused naming "check 'ci-gate' is failure"

    Scenario: A newer CI run still in progress refuses the merge despite an older green run
      Given a pull request into main whose CI run was green on the head
      And a newer CI run of the same workflow is still in progress on the head
      And the principal-engineer and the senior-qa-engineer approved the head
      When the orchestrator runs the merge check on the head
      Then the merge is refused naming "ci-gate"

    Scenario: Every CI run on the head was cancelled
      Given a pull request into main whose CI run was cancelled on the head
      And a newer CI run of the same workflow was cancelled by the concurrency group
      And the principal-engineer and the senior-qa-engineer approved the head
      When the orchestrator runs the merge check on the head
      Then the merge is refused naming "all CI runs on"

    Scenario: Two CI runs started together and the newer one was cancelled (PR #49)
      Given a pull request into main whose CI run was green on the head
      And a newer CI run of the same workflow was cancelled by the concurrency group
      And the principal-engineer and the senior-qa-engineer approved the head
      When the orchestrator runs the merge check on the head
      Then the merge is allowed

    Scenario: A newer CI run cancelled by hand, with no run after it, refuses the merge (PE-1)
      Given a pull request into main whose CI run was green on the head
      And a later CI run of the same workflow was cancelled by hand and nothing ran after it
      And the principal-engineer and the senior-qa-engineer approved the head
      When the orchestrator runs the merge check on the head
      Then the merge is refused naming "was cancelled and no later run replaced it"
