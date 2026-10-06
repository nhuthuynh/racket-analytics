# Sprint 2 §14.3.4 (ST-013b; ADR 0032). Owner: senior-qa-engineer. API binding:
# backend/tests/features/test_account_identity.py (needs Mailpit); the full red set is IT-02-12.
@M0 @story-ST-013b @nfr-057
Feature: The account follows the address
    Scenario: 14.3.4 The service rotates its key
      Given Ivy has an account with 2 matches
      When the service rotates its sign-in key
      And Ivy signs in with the same address
      Then she sees her 2 matches

    Scenario: Two addresses that share a key
      Given two different addresses produce the same key
      When both sign in
      Then each gets an account of its own
