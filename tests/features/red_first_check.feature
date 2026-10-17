# Sprint 4, C4-RED (sre-devops-engineer; retro 3 B5, R3-IN-1). Written before the check. Binding:
# infra/tests/test_red_first_check_scenarios.py (real git, ci.yml pr-policy steps, merge ref).
@M0 @nfr-077 @ticket-C4-RED
Feature: A code commit in a pull request shows its red step first

  Background:
    Given a pull request opened against main

  Rule: A code commit without a red step fails the PR policy

    Scenario: A code commit with no red step fails
      Given the pull request has a commit "feat: add a rule" changing "backend/src/racket/rule.py" and its unit test together
      When the PR policy checks run on the merge ref
      Then the red-first check fails
      And it names the commit "feat: add a rule" and the path "backend/src/racket/rule.py"

    Scenario: A web code commit fails even when a later commit adds its tests
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

    Scenario Outline: A <kind> PR passes
      Given the pull request has a commit "<subject>" changing "<path>"
      When the PR policy checks run on the merge ref
      Then the red-first check passes

      Examples:
        | kind      | subject        | path                            |
        | docs-only | docs: notes    | docs/notes.md                   |
        | test-only | test: red rule | backend/tests/unit/test_rule.py |
