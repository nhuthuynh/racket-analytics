# Sprint 4, ticket CI-DRAFT-SKIP (sre-devops-engineer). Written before the fix.
# Binding: infra/tests/test_ci_draft_skip_scenarios.py (evaluates the job conditions of
# .github/workflows/ci.yml per event, runs the ci-gate step and scripts/ci/merge_ready.py).
# Incidents: CI run 39096605529 (PR #120, size check red before the EM waiver decision),
# CI run 39088063130 (PD-4b, a red-first commit pushed on its own). PO 2026-10-18.
@M0 @story-ST-002 @nfr-077 @ticket-CI-DRAFT-SKIP
Feature: CI runs on a pull request only once it is ready for review

  Rule: A draft pull request shows no CI result

    Scenario: No CI job runs for a draft pull request
      When CI is triggered for a draft pull request
      Then no CI job runs, not even ci-gate

    Scenario: A draft head is never merge ready
      Given a pull request whose CI jobs were all skipped because it is a draft
      And the principal-engineer and the senior-qa-engineer approved the head
      When the orchestrator runs the merge check on the head
      Then the merge is refused naming "ci-gate"

  Rule: Outside drafts every gate stays as strict as before

    Scenario Outline: Every gate runs for a <event>
      When CI is triggered for a <event>
      Then every CI job runs except <skipped>
      And ci-gate runs

      Examples:
        | event                         | skipped                    |
        | pull request ready for review | flaky-report               |
        | push to main                  | pr-policy and flaky-report |
        | nightly schedule              | pr-policy                  |
        | manual dispatch               | pr-policy                  |

    Scenario: Marking a draft ready for review starts CI
      Then CI is triggered when a pull request is marked ready for review or its labels change

    Scenario: ci-gate still fails a ready pull request whose policy job was skipped
      Given a ready pull request whose PR policy job was skipped and every other gate passed
      When the ci-gate step judges the results
      Then ci-gate fails naming "pr-policy: skipped"
