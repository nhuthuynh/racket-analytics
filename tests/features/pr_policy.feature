# Sprint 3, ticket CI-POLICY-BASE (sre-devops-engineer). Written before the fix.
# Binding: infra/tests/test_pr_policy_scenarios.py (runs the pr-policy steps of
# .github/workflows/ci.yml against a real git checkout of the PR merge ref).
# Incident: CI run 37739461709, job 113186548205 (PR #6 blamed for PR #9's spec change).
@M0 @story-ST-003 @nfr-078 @nfr-077 @ticket-CI-POLICY-BASE
Feature: The PR policy judges only the pull request's own changes

  Background:
    Given a pull request opened against main

  Rule: Changes that reached main after the PR event are not the PR's

    Scenario: A docs-only PR is not blamed for a test edit merged to main meanwhile
      Given the pull request changes only documentation
      And another pull request changes an accepted end-to-end test on main after the event
      When the PR policy checks run on the merge ref
      Then the test immutability check passes
      And it does not name the end-to-end test changed on main

    Scenario: A small PR is not blamed for lines merged to main meanwhile
      Given the pull request changes 10 lines
      And another pull request adds 450 lines on main after the event
      When the PR policy checks run on the merge ref
      Then the PR size check passes and counts 10 changed lines

  Rule: The gate still catches the PR's own violations

    Scenario: A test edit in the PR is still caught after main moved
      Given the pull request edits an accepted unit test
      And another pull request changes an accepted end-to-end test on main after the event
      When the PR policy checks run on the merge ref
      Then the test immutability check fails naming only the edited unit test

    Scenario: An oversize PR still fails after main moved
      Given the pull request changes 401 lines
      And another pull request adds 30 lines on main after the event
      When the PR policy checks run on the merge ref
      Then the PR size check fails and counts 401 changed lines
