# CI-FLAKE-RESUMABLE (blockers.md 2026-10-08, CI run 37715576115). Owner: senior-qa-engineer.
# Written before implementation. Binding: backend/tests/features/test_e2e_repeat_triage.py runs
# scripts/ci/e2e_repeat.sh (the step of .github/workflows/e2e-repeat.yml) with a stand-in
# Playwright that writes the JUnit file a --repeat-each run writes; the verdict is the real
# scripts/ci/flaky_report.py. The workflow file itself is checked by infra/tests.
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
