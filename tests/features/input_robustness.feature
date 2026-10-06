# Sprint 2 §14.3.1 (C-01). Owner: senior-qa-engineer. API binding:
# backend/tests/features/test_input_robustness.py; the generated cases are IT-02-10.
@M0 @story-C-01 @nfr-058
Feature: Input that is not text is refused cleanly
  Rule: Control characters never break the service

    Scenario Outline: 14.3.1 Control character in a field
      Given Ivy is on the "<form>" form
      When she submits a <field> containing a "<character>" character
      Then she is told the <field> is not valid
      And nothing is saved
      Examples:
        | form      | field         | character      |
        | sign-in   | email address | NUL            |
        | sign-in   | email address | line separator |
        | new match | title         | NUL            |
        | new match | title         | lone surrogate |
