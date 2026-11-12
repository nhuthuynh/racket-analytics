# Sprint 5, ST-079 (senior-frontend-engineer; NFR-024.1-.3; G05-04; BA-5 draft, negative case).
# Binding: web/tests/features/playwright-projects.test.ts runs the real `playwright test --list`
# on web/playwright.config.ts (no browser is launched by a listing).
@nfr-024 @ticket-ST-079
Feature: The browser matrix projects list the critical journeys

  Scenario Outline: The critical journeys are listed in the "<project>" project
    Given PW_PROJECTS names "<project>"
    When the specs tagged "@critical" are listed
    Then E2E-04-01..05, sign-in and upload resume are listed in "<project>" only

    Examples:
      | project        |
      | chromium       |
      | webkit         |
      | android-chrome |

  Scenario: An unknown project name is refused (negative)
    Given PW_PROJECTS names "android-firefox"
    When the specs tagged "@critical" are listed
    Then it fails naming "android-firefox"
