# Sprint 6, ticket CI-FIX-PR-CHECK (sre-devops-engineer). Written before the implementation.
# Since 2026-10-05, 205 of about 1,645 CI runs failed; 136 of the 287 failing jobs were PR-policy
# gates (PR size 77, test/gold immutability 35, red first 14, decisions ledger 4), the rest doc
# checks, Ruff and the unit suites. Every one of those checks is a script that runs locally, but
# nothing ran them before a push. scripts/pr-check.sh runs them with ci.yml's commands, and the
# .githooks/pre-push hook (`make hooks`) runs it before a ticket branch is pushed.
# Binding: infra/tests/test_pr_check_scenarios.py. It runs the real scripts/pr-check.sh and the
# real hook on a throwaway git checkout with a local bare `origin`, a recording `uv` and a
# recording `gh` on PATH, and the local GitHub API stub for the PR's labels.
@M0 @story-ST-002 @nfr-077 @ticket-CI-FIX-PR-CHECK
Feature: One local command runs CI's PR policy, doc, lint and unit gates before a push

  Rule: pr-check fails where CI would fail, naming the CI step

    Scenario Outline: A branch that breaks a PR policy gate fails pr-check naming the step
      Given a ticket branch off main that <breaks>
      When pr-check runs on the branch
      Then pr-check exits non-zero
      And its summary reports FAIL for "<step>"

      Examples:
        | breaks                                     | step                                            |
        | adds 401 lines of production code          | PR size (EP/ENG-04)                             |
        | edits an existing unit test                | Test and gold immutability (EP/ENG-28, NFR-078) |
        | changes production code without a red step | Red first (R3-IN-1, C4-RED)                     |

    Scenario: A clean branch passes every check
      Given a ticket branch off main that adds a test and then the code it tests
      When pr-check runs on the branch
      Then pr-check exits 0
      And its summary reports no FAIL
      And its summary reports SKIP for "Cost per PR table (PRC-11.3)", which needs an open pull request
      And ruff check, ruff format --check and the unit suites ran in backend

    Scenario: Every check runs after one has failed
      Given a ticket branch off main that edits an existing unit test, then changes production code without a red step
      When pr-check runs on the branch
      Then pr-check exits non-zero
      And its summary has one line for each check, in order
      And its summary reports FAIL for "Test and gold immutability (EP/ENG-28, NFR-078)"
      And its summary reports FAIL for "Red first (R3-IN-1, C4-RED)"
      And its summary reports PASS for "PR size (EP/ENG-04)"

    Scenario: An open pull request's labels and title count as they do in CI
      Given a ticket branch off main that adds 401 lines of production code
      And its open pull request is titled "[CI-FIX-PLANTED] planted" and carries the "size-waiver" label
      When pr-check runs on the branch
      Then its summary reports PASS for "PR size (EP/ENG-04)"
      And its summary reports FAIL for "Cost per PR table (PRC-11.3)"

    Scenario: --fast skips the unit suites and nothing else
      Given a ticket branch off main that adds a test and then the code it tests
      When pr-check runs on the branch with "--fast"
      Then pr-check exits 0
      And its summary reports SKIP for "Unit suites (scripts/test-unit.sh)"
      And the unit suites did not run

  Rule: The pre-push hook gates ticket branches only

    Scenario: The hook blocks the push of a ticket branch that fails pr-check
      Given the hooks are installed with "make hooks"
      And a branch "s06/planted" off main that adds 401 lines of production code
      When the branch is pushed to origin
      Then the push is refused
      And origin has no branch "s06/planted"
      And the push output reports FAIL for "PR size (EP/ENG-04)"

    Scenario: The hook lets a ticket branch that passes pr-check through
      Given the hooks are installed with "make hooks"
      And a branch "s06/clean" off main that adds a test and then the code it tests
      When the branch is pushed to origin
      Then the push succeeds
      And origin has the branch "s06/clean"

    Scenario Outline: The hook does not run pr-check for <push>
      Given the hooks are installed with "make hooks"
      And a branch "<branch>" off main that adds 401 lines of production code
      When the branch is pushed to origin <how>
      Then the push succeeds
      And origin has the branch "<branch>"
      And pr-check did not run

      Examples:
        | push                          | branch                | how              |
        | a branch that is not a ticket | deps/security-audit   | as is            |
        | a push with --no-verify       | s06/planted-no-verify | with --no-verify |
