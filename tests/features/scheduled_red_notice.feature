# Sprint 5 Wave 0 (CI FIRST), ticket CI-NOTICE-CANCELLED (sre-devops-engineer), story PRC-05
# "The process rules are enforced by checks", atomic items PRC-1.1..1.3.
# Scheduled CI run 41622904539 (main 888760df, 2026-11-03) hit the Flaky-test report job's 45 min
# timeout; GitHub reported the run as `cancelled`, and the notice decided `none`, so nobody saw it.
# Binding: infra/tests/test_scheduled_red_notice_scenarios.py. It runs the REAL `run:` scripts of
# .github/workflows/scheduled-red-notice.yml and of ci.yml's flaky-report suite step with bash,
# with a recording `gh` and a stand-in `uv` on PATH. Written before the implementation.
@M0 @story-PRC-05 @ticket-CI-NOTICE-CANCELLED
Feature: A scheduled run that did not finish is red

  Rule: Cancelled and timed-out scheduled runs raise the [CI-RED] notice (PRC-1.1, PRC-1.2)

    Scenario: a cancelled scheduled run is red
      Given no notice issue is open
      When the scheduled "CI" run ends with "cancelled"
      Then gh opened an issue titled "[CI-RED] scheduled CI run failed" assigned to the repository owner
      And the issue body names the conclusion "cancelled" and the run

    Scenario: a timed-out scheduled run is red
      Given no notice issue is open
      When the scheduled "Nightly quality" run ends with "timed_out"
      Then gh opened an issue titled "[CI-RED] scheduled Nightly quality run failed" assigned to the repository owner
      And the issue body names the conclusion "timed_out" and the run

    Scenario: a second cancelled run comments on the open notice
      Given notice issue 91 is open
      When the scheduled "CI" run ends with "cancelled"
      Then gh commented on issue 91 naming the run
      And gh opened no new issue

    Scenario: a skipped scheduled run changes nothing
      Given notice issue 91 is open
      When the scheduled "CI" run ends with "skipped"
      Then gh was not asked to open, comment on or close an issue

  Rule: The Flaky-test report job ends inside its 45 min limit (PRC-1.3)

    Scenario: a hanging pass of the suites is stopped and the job moves on
      Given each pass of the flaky-report suites hangs
      When the flaky-report suite step runs with a pass limit of 2 seconds
      Then the step ends within 20 seconds
      And all 3 passes were started, each with its output in its own log file

    Scenario: the suite step's limits add up to less than the job's
      Then the flaky-report suite step has its own timeout below the job's 45 minutes
      And three passes at the pass limit fit inside the step's timeout
      And the passes' log files are uploaded with the flaky report
