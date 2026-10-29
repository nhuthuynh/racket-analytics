# Sprint 4 ST-068b (FR-003; flows-sprint-04 §5 A-10/A-11 and the footage notice; PM-4 W-A01..W-A09):
# the web half of tests/features/age_confirmation.feature (ST-068a, API). Bound by Vitest + Testing
# Library in web/tests/features/age-question-ui.test.tsx; the wire is web/tests/contract/age.test.ts.
@story-ST-068b @identity @web
Feature: The age question after sign-in
  A new address answers one question before it has an account.

  Scenario: Under-age applicant
    Given the age gate is on
    And a new address has signed in with a link
    When the applicant answers "No, I am under 18"
    Then the page says "You can't have an account yet"
    And it says why: "You need to be 18 or over to use this app. We did not make an account for you."
    And it says what to do instead: "You are welcome to come back when you turn 18."

  Scenario: Adult confirms
    Given the age gate is on
    And a new address has signed in with a link
    When the applicant answers "Yes, I am 18 or over"
    Then they continue to the first-run screen
    And the upload page shows the footage notice

  Scenario: Flag off, no question
    Given the age gate is off
    Then the age question page is not found
    And the upload page shows no footage notice

  Scenario: Existing account still signed in
    Given the age gate is on
    And an existing account that has not answered the question is still signed in
    When it opens the sign-in page, its matches or a new match
    Then each page sends it to the age question
