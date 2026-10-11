# Sprint 3, ticket CI-POLICY-LIVE-LABELS (sre-devops-engineer). Written before the fix.
# Binding: infra/tests/test_pr_policy_live_labels_scenarios.py (ci.yml pr-policy steps, real git).
# Incident: PR #71, CI runs 38094831495 and 38096137380 (waiver applied after the push, still red).
@M0 @nfr-077 @nfr-078 @ticket-CI-POLICY-LIVE-LABELS
Feature: The PR policy judges the pull request's labels as they are when the check runs

  Background:
    Given a pull request opened against main

  Rule: The PR's current labels win over the labels frozen in the triggering event

    Scenario: A waiver removed after the push no longer waives the size limit
      Given the pull request changes 401 lines
      And the event froze the labels "size-waiver"
      And the pull request now carries no labels
      When the PR policy checks run again without a new push
      Then the PR size check fails and counts 401 changed lines
      And the labels were read from the GitHub API

    Scenario: A QA approval removed after the push no longer approves a test edit
      Given the pull request edits an accepted unit test
      And the event froze the labels "qa-approved-test-change"
      And the pull request now carries no labels
      When the PR policy checks run again without a new push
      Then the test immutability check fails
      And the labels were read from the GitHub API

    Scenario: A waiver applied after the push is honoured without a new push
      Given the pull request changes 401 lines
      And the event froze no labels
      And the pull request now carries the label "size-waiver"
      When the PR policy checks run again without a new push
      Then the PR size check passes and counts 401 changed lines
      And the labels were read from the GitHub API

    Scenario: A QA approval applied after the push is honoured without a new push
      Given the pull request edits an accepted unit test
      And the event froze no labels
      And the pull request now carries the label "qa-approved-test-change"
      When the PR policy checks run again without a new push
      Then the test immutability check passes
      And the labels were read from the GitHub API

  Rule: When the GitHub API cannot answer, the event's labels are used and the log says so

    Scenario: The labels endpoint is down
      Given the pull request changes 401 lines
      And the event froze no labels
      And the pull request now carries the label "size-waiver"
      But the GitHub labels endpoint fails
      When the PR policy checks run again without a new push
      Then the PR size check fails and counts 401 changed lines
      And the labels were read from the event payload
