# Sprint 4, FIX-04-1f (goal metric G04-07; api-sprint-04 §1 "Flag-on E2E"; PE-4 decisions row 18).
# Owner: senior-qa-engineer. Written before implementation.
# Binding: infra/tests/test_e2e_projects_scenarios.py (the real Playwright of web/ lists stand-in
# specs through web/playwright.config.ts; no browser is launched, no stack is needed).
# Root cause: web/playwright.config.ts had no `flags-on` project, so the G04-07 flag-on command
# (`PW_PROJECTS=flags-on playwright test`) selected no project and Playwright printed only
# "No tests found"; a flag-on spec under web/e2e/sprint-04/flags-on/ would also have run in the
# per-PR chromium and webkit legs against a stack with every FEATURE_* off.
@nfr-024 @fix-04-1f @g04-07
Feature: The flag-on E2E specs run only in the flags-on project
  The verifier measures the flag-on journeys (age, privacy settings, over-limit) on a stack
  started with every feature flag on, and the per-PR journeys on a stack with every flag off.
  Each Playwright project runs only the specs written for its stack.

  Scenario: An unknown project name is refused, naming the known projects
    Given the E2E projects are chosen with "chromuim"
    When the E2E specs are listed
    Then the listing is refused naming "chromium, webkit, flags-on"

  Scenario: The per-PR browsers never run a flag-on spec
    Given a flag-on spec "E2E-04-06 age question" and a spec "E2E-04-05 keyboard only"
    And the E2E projects are chosen with "chromium,webkit"
    When the E2E specs are listed
    Then "E2E-04-05 keyboard only" is listed in "chromium" and "webkit"
    And "E2E-04-06 age question" is not listed

  Scenario: The flags-on project runs only the flag-on specs
    Given a flag-on spec "E2E-04-06 age question" and a spec "E2E-04-05 keyboard only"
    And the E2E projects are chosen with "flags-on"
    When the E2E specs are listed
    Then "E2E-04-06 age question" is listed in "flags-on"
    And "E2E-04-05 keyboard only" is not listed
