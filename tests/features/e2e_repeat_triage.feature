# CI-FLAKE-RESUMABLE (CI run 37715576115). Owner: senior-qa-engineer. Written before implementation.
# Binding: backend/tests/features/test_e2e_repeat_triage.py (real e2e_repeat.sh and flaky_report.py,
# stand-in Playwright). The workflow file is checked by infra/tests/test_workflow_e2e_repeat.py.
@ticket-CI-FLAKE-RESUMABLE @nfr-074
Feature: Repeating an E2E in CI to triage a flaky test

  Rule: A repeat run fails on a flaky test and on a broken one, and passes only when every repeat passed

    Scenario: One failure in twenty repeats is a flaky test
      Given an E2E test that fails in 1 of 20 repeats
      When the E2E repeat job runs it 20 times
      Then the job fails
      And the flaky report names the test as flaky

    Scenario: Twenty passes in twenty repeats
      Given an E2E test that fails in 0 of 20 repeats
      When the E2E repeat job runs it 20 times
      Then the job passes
      And the flaky report says "0 flaky"

    Scenario: A test that fails in every repeat is broken, not flaky, and still fails the job
      Given an E2E test that fails in 20 of 20 repeats
      When the E2E repeat job runs it 20 times
      Then the job fails
      And the flaky report says "0 flaky"

  Rule: A dispatch runs the title filter as typed; a pull request runs the two resume titles (PE-PR10-M1)

    Scenario Outline: The title filter a repeat run uses
      Given a repeat run started by <event> with the title filter "<typed>"
      When the E2E repeat job starts Playwright
      Then Playwright is given the title filter "<used>"

      Examples:
        | event             | typed     | used                                                          |
        | workflow_dispatch |           |                                                               |
        | workflow_dispatch | Wording   | Wording                                                       |
        | pull_request      |           | Return after closing the tab\|A different file is chosen to resume |
