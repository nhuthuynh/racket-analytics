# Sprint 4, ST-068a (FR-003; OQ-05 accepted, ADR 0023; api-sprint-04 §4; SEC-4 T4-AG-1, T4-AG-2).
# Steps: backend/tests/features/test_age_confirmation.py. Negative case first.
@story-ST-068a
Feature: An account exists only once its holder confirms being an adult

  Scenario: Under-age applicant
    Given the age gate is on
    And a new address has signed in with a link
    When the applicant answers that they are not an adult
    Then the answer is refused as "under_age"
    And no account exists for the address
    And the sign-in has ended

  Scenario: Adult confirms
    Given the age gate is on
    And a new address has signed in with a link
    And the applicant's account answers "age_confirmation_required"
    When the applicant answers that they are an adult
    Then the address has an account with a confirmation time
    And the applicant can see their account

  Scenario: Flag off, no question
    Given the age gate is off
    And a new address has signed in with a link
    Then the address has an account without a confirmation time
    And the applicant can see their account
    And the age question is not found
