# Sprint 1 §7.1 + §14.3.1 (ST-013). Owner: senior-qa-engineer. Written before implementation.
# Bindings: API level backend/tests/features/test_sign_in.py (scenarios marked [API]);
# browser level web/e2e/sprint-01/sign-in.spec.ts (all scenarios, E2E-01-01). Copy: flows A-01..A-04.
@M0 @story-ST-013 @nfr-032
Feature: Sign in without a memorised password
  Rule: Authentication never requires a cognitive function test

    Scenario: Sign up with an email sign-in link
      Given Ivy has no account
      When she requests a sign-in link and opens it within 15 minutes
      Then she is signed in and sees "Record your first match"
      And the address bar no longer contains the sign-in code

    Scenario Outline: A link that can no longer be used
      Given Ivy's sign-in link <condition>
      When she opens it
      Then she sees "This link has expired"
      And she is offered a new link
      Examples:
        | condition               |
        | is 16 minutes old       |
        | was already used        |

    Scenario: Too many link requests
      Given Ivy has requested 5 sign-in links in the last 10 minutes
      When she requests another one
      Then she is told when she can request a new link

  Rule: Requesting a link never reveals whether an account exists

    Scenario: Link requested for an unknown address
      Given no account exists for "new@example.com"
      When a sign-in link is requested for "new@example.com"
      Then the page says "Check your email"
      And the response is the same as for an address that has an account

  Rule: Sign-in never asks for a password or a puzzle

    Scenario: The sign-in page asks only for an email address
      Given Ivy opens the sign-in page
      Then the only field is "Email address"
      And pasting into it is allowed
