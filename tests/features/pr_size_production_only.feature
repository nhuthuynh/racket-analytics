# Sprint 4, ticket CI-SIZE-PROD-ONLY (sre-devops-engineer). Written before the change.
# Binding: infra/tests/test_pr_size_production_only_scenarios.py (runs the pr-policy steps of
# .github/workflows/ci.yml against a real git checkout of the PR merge ref).
# PO decision 2026-10-28: keep the 400-line limit, count only production code (ADR 0054).
@M0 @story-ST-003 @nfr-077 @ticket-CI-SIZE-PROD-ONLY
Feature: The PR size check counts production code only

  Background:
    Given a pull request opened against main

  Rule: Production code over the limit still needs a waiver

    Scenario: Oversize production code fails even when tests come with it
      Given the pull request adds 401 lines to "backend/src/big.py"
      And the pull request adds 300 lines to "backend/tests/unit/test_big.py"
      When the PR policy checks run on the merge ref
      Then the PR size check fails, counting 401 production lines and excluding 300 lines

  Rule: Tests, docs and lockfiles do not count toward the limit

    Scenario: A test-heavy PR passes without a waiver
      Given the pull request adds 40 lines to "backend/src/small.py"
      And the pull request adds 300 lines to "backend/tests/unit/test_small.py"
      And the pull request adds 200 lines to "web/tests/unit/score.test.tsx"
      And the pull request adds 100 lines to "tests/features/small.feature"
      When the PR policy checks run on the merge ref
      Then the PR size check passes, counting 40 production lines and excluding 600 lines

    Scenario: Docs and lockfiles do not count
      Given the pull request adds 10 lines to "web/src/page.tsx"
      And the pull request adds 450 lines to "docs/decisions/0099-example.md"
      And the pull request adds 500 lines to "web/pnpm-lock.yaml"
      When the PR policy checks run on the merge ref
      Then the PR size check passes, counting 10 production lines and excluding 950 lines

  Rule: A move cannot hide production code

    Scenario: A test file moved into production code counts in full
      Given main has 1000 lines in "tests/helper.py"
      And the pull request moves "tests/helper.py" to "app/service.py" and changes 450 lines
      When the PR policy checks run on the merge ref
      Then the PR size check fails, counting 1000 production lines and excluding 1000 lines
