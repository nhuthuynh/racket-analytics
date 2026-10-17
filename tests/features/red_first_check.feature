# Sprint 4, ticket C4-RED (sre-devops-engineer). Written before scripts/ci/check_red_first.py.
# Binding: infra/tests/test_red_first_check_scenarios.py (real git, the `Red first` step of the
# pr-policy job in .github/workflows/ci.yml run verbatim on the PR merge ref).
# Source: retro 3 B5 (A5), R3-IN-1; QA-R1S3-09/-10 (TDD order not shown in Sprint 3).
@M0 @nfr-077 @ticket-C4-RED
Feature: A code commit in a pull request shows its red step first

  A "code commit" adds or changes production code under backend/src or web/src. Its red step is
  either a "Red:" line in its own commit body or an earlier "test-only commit" in the same pull
  request (tests changed, no production code). Merge commits are not judged.

  Background:
    Given a pull request opened against main

  Rule: A code commit without a red step fails the PR policy

    Scenario: A code commit with no red step fails
      Given the pull request has a commit "feat: add a rule" changing "backend/src/racket/rule.py" and its unit test together
      When the PR policy checks run on the merge ref
      Then the red-first check fails
      And it names the commit "feat: add a rule" and the path "backend/src/racket/rule.py"

    Scenario: A web code commit with no red step fails even when a later commit adds tests
      Given the pull request has a commit "feat: add a screen" changing "web/src/app/screen.tsx"
      And the pull request has a test-only commit "test: screen spec" changing "web/tests/unit/screen.test.tsx"
      When the PR policy checks run on the merge ref
      Then the red-first check fails
      And it names the commit "feat: add a screen" and the path "web/src/app/screen.tsx"

  Rule: A red step before or inside the code commit passes

    Scenario: A test-only commit before the code commit passes
      Given the pull request has a test-only commit "test: red rule" changing "backend/tests/unit/test_rule.py"
      And the pull request has a commit "feat: add a rule" changing "backend/src/racket/rule.py"
      When the PR policy checks run on the merge ref
      Then the red-first check passes

    Scenario: A Red line in the code commit body passes
      Given the pull request has a commit "feat: add a rule" changing "backend/src/racket/rule.py" and its unit test together with the body line "Red: uv run pytest tests/unit/test_rule.py -> 1 failed"
      When the PR policy checks run on the merge ref
      Then the red-first check passes

  Rule: Pull requests without production code pass

    Scenario: A docs-only PR passes
      Given the pull request has a commit "docs: notes" changing "docs/notes.md"
      When the PR policy checks run on the merge ref
      Then the red-first check passes

    Scenario: A test-only PR passes
      Given the pull request has a test-only commit "test: red rule" changing "backend/tests/unit/test_rule.py"
      When the PR policy checks run on the merge ref
      Then the red-first check passes
