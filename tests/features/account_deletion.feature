# Sprint 3 §7.5 (QA-ACC-3, written for ST-051; FR-007, NFR-066). Owner: senior-qa-engineer.
# API binding: backend/tests/features/test_account_deletion.py. Browser binding:
# web/e2e/sprint-03/delete-account.spec.ts (E2E-03-04). Re-sign-in rule: PM-1 default (a new,
# empty account).
@M0 @story-ST-051 @nfr-066
Feature: Delete my account
  Scenario: Delete account
    Given Ivy has 3 matches and is signed in on her phone and her laptop
    When she deletes her account and confirms
    Then she is signed out on both devices
    And after the clean-up runs none of her matches or her profile remain stored

  Scenario: Signing in again starts empty
    Given Ivy deleted her account
    When she signs in again with the same address
    Then she sees no matches

  # Sprint 4 C4-TAC5 (T-AC-5; SEC-S3-TM-07; ADR 0045). Roles are keyed by account id, never by
  # address: the new account starts without the labeller role. The Full Tag tool answers her as
  # for an unknown match (SEC-S3-TM-08), so the tool is not revealed.
  @t-ac-5 @fr-150
  Scenario: A re-created account has no labeller role
    Given Ivy was a labeller and deleted her account
    When she signs in again with the same address
    Then the Full Tag tool is not there for her, even on her own consented match
