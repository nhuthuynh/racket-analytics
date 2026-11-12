# EM-CLOSE-CHECKS (story PRC-05; atomic items PRC-6.1, PRC-6.2, PRC-6.3; goal metric G05-12;
# retro 4 F1/F3, lessons L22-L24). Owner: engineering-manager. Written before implementation.
# Binding: infra/tests/test_close_checks_scenarios.py runs
# docs/sprints/05/close-checks/retro_ready.py and retro05_check.py over HTTP against the local
# GitHub REST stub (infra/tests/close_checks_stub.py).
@ticket-EM-CLOSE-CHECKS
Feature: The sprint is closed once, and the close is checked against GitHub
  Rule: RETRO-05 starts only when VERIFY-05 is merged and every VERIFY-05 finding is Fixed;
        the close's PR set and its Open blocker rows are derived from GitHub, never by reasoning

    Scenario: An open VERIFY PR keeps the retro from starting
      Given a merged VERIFY-05 PR
      And an open VERIFY-05 PR
      When the retro trigger is checked
      Then the retro is not ready, naming "#302"

    Scenario: A VERIFY finding that is not Fixed keeps the retro from starting
      Given a merged VERIFY-05 PR
      And the ledger holds "QA-VERIFY05R1-01" as "Open"
      When the retro trigger is checked
      Then the retro is not ready, naming "QA-VERIFY05R1-01"

    Scenario: The retro starts once VERIFY is merged and its findings are Fixed
      Given a merged VERIFY-05 PR
      And the ledger holds "QA-VERIFY05R1-01" as "Fixed"
      When the retro trigger is checked
      Then the retro is ready

    Scenario: A merged Sprint 5 PR missing from the status map fails the close
      Given merged Sprint 5 PRs 201 and 202
      And the status map lists PR 201
      When the close is checked
      Then the close is not met, naming "on GitHub, not in status.json: #202"

    Scenario: An Open blocker row whose cause is closed fails the close
      Given merged Sprint 5 PRs 201 and 202
      And the status map lists PRs 201 and 202
      And an Open blocker row names the closed cause "#150"
      When the close is checked
      Then the close is not met, naming "#150"

    Scenario: The close is met when the sets agree and every Open cause is open
      Given merged Sprint 5 PRs 201 and 202
      And the status map lists PRs 201 and 202
      And an Open blocker row names the open cause "#151"
      When the close is checked
      Then the close is met

    Scenario: GitHub cannot be read
      Given the GitHub API fails
      When the close is checked
      Then the close is unknown
