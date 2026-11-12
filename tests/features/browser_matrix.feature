# Sprint 5, ST-079 (senior-frontend-engineer; NFR-024.1-.3; goal G05-04). Acceptance criteria
# drafted by BA-5 (docs/sprints/05/requirements-breakdown.md, NFR-024), written before the method.
# Binding: infra/tests/test_browser_matrix_scenarios.py: web/'s real Playwright runs a stand-in
# suite of the critical journeys and the real scripts/measure/browser_matrix.py reads its reports,
# as goal-scorecard §4 G05-04 does. NFR-024.4-.5 (real phones) are human: P20, device checklist.
@nfr-024 @ticket-ST-079
Feature: R1 critical journeys pass on the emulated phones players use

  Rule: A project passes only when every critical journey passes in every repeat

    Scenario Outline: The critical journeys pass in one Playwright project (NFR-024.1-.3)
      Given the specs tagged "@critical" (E2E-04-01..05, sign-in, upload resume)
      When they run in the "<project>" project 3 times with retries off
      Then the browser-matrix method passes for "<project>"

      Examples:
        | project        |
        | chromium       |
        | webkit         |
        | android-chrome |

    Scenario: A journey that fails in one repeat is flaky and fails the project
      Given the specs tagged "@critical" with "E2E-04-03" failing in its second repeat
      When they run in the "android-chrome" project 3 times with retries off
      Then the browser-matrix method fails naming "E2E-04-03" as flaky in "android-chrome"

    Scenario: A critical journey that did not run fails the project
      Given the specs tagged "@critical" without the upload resume journey
      When they run in the "android-chrome" project 3 times with retries off
      Then the browser-matrix method fails naming "upload-resume" as missing in "android-chrome"

    Scenario: A required project with no report fails closed (planted failure)
      Given the specs tagged "@critical" (E2E-04-01..05, sign-in, upload resume)
      When they run in the "chromium" project 3 times with retries off
      Then the browser-matrix method fails when it also requires "firefox"
