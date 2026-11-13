# Sprint 6 wave 0 (CI FIRST), ticket CI-SCHEDULED-RED (sre-devops-engineer), story PRC-06, item PRC-9.1.
# Scheduled CI run 43007950254 (main b7bf0b7f, 2026-11-11) ended `failure` (Locust 50 RPS verdict);
# the red-run notice ran only as `skipped` on push events, and merge_ready.py kept merging, so the
# red reached no status record (sprint-06.md section 1, kickoff SRE-2).
# Binding: infra/tests/test_scheduled_red_scenarios.py. It replays the recorded payloads of runs
# 43007950254 and 43206773425 (infra/tests/fixtures/scheduled/) through scripts/measure/scheduled_red.py
# and through scripts/ci/merge_ready.py over HTTP against the local GitHub API stub.
# Written before the implementation.
@M0 @story-PRC-06 @ticket-CI-SCHEDULED-RED
Feature: A red scheduled run on main reaches the status record and blocks merges

  Rule: A red scheduled CI or Nightly quality run on main is reported with its run id (PRC-9.1)

    Scenario: the recorded red scheduled CI run is reported
      Given the recorded scheduled run 43007950254
      When the scheduled-red report runs
      Then it exits 1
      And it prints a red line naming "CI", run 43007950254 and "failure"

    Scenario: a later green scheduled CI run clears the report
      Given the recorded scheduled run 43007950254
      And the recorded scheduled run 43206773425
      When the scheduled-red report runs
      Then it exits 0
      And it prints no red line

    Scenario: a timed-out scheduled Nightly quality run is reported
      Given a scheduled "Nightly quality" run 51 on main that ended "timed_out"
      When the scheduled-red report runs
      Then it exits 1
      And it prints a red line naming "Nightly quality", run 51 and "timed_out"

  Rule: merge_ready.py refuses while the latest scheduled CI run on main is red (PRC-9.1)

    Scenario: a stubbed open pull request is refused while the scheduled CI run is red
      Given an open pull request whose head is green and approved
      And the recorded scheduled run 43007950254
      When the orchestrator runs the merge check on the head
      Then the merge is refused naming "43007950254"

    Scenario: the next green scheduled CI run allows the same pull request
      Given an open pull request whose head is green and approved
      And the recorded scheduled run 43007950254
      And the recorded scheduled run 43206773425
      When the orchestrator runs the merge check on the head
      Then the merge is allowed

    Scenario: a red Nightly quality run alone does not block the merge
      Given an open pull request whose head is green and approved
      And a scheduled "Nightly quality" run 51 on main that ended "failure"
      When the orchestrator runs the merge check on the head
      Then the merge is allowed

    Scenario: a fix proven by a green dispatched CI run on its head may merge
      Given an open pull request whose head is green and approved
      And the recorded scheduled run 43007950254
      And a dispatched CI run on the head that ended "success"
      When the orchestrator runs the merge check on the head
      Then the merge is allowed
