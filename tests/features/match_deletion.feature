# Sprint 3 §7.5 (QA-ACC-3, written for ST-050; FR-006, NFR-066, ADR 0006). Owner: senior-qa-engineer.
# API binding: backend/tests/features/test_match_deletion.py ("Delete a tagged match",
# "Someone else's match"). "The confirmation says what will go" is screen text: browser binding
# web/e2e/sprint-03/journey-v2.spec.ts (E2E-03-01, dialog X-01).
@M0 @story-ST-050 @nfr-066
Feature: Delete a match
  Rule: A deleted match is gone from the account at once and from storage soon after

    Scenario: Delete a tagged match
      Given Ivy has a tagged match with stats
      When she deletes the match and confirms the stated consequences
      Then within 1 minute the match no longer appears anywhere in her account
      And after the clean-up runs no stored file or record of the match remains

    Scenario: The confirmation says what will go
      When Ivy starts deleting a match
      Then she is told the video, tags, score sheet and stats will be deleted and cannot be restored

    Scenario: Someone else's match
      Given Carlos knows the address of Ivy's match
      When he tries to delete it
      Then he is told it does not exist
      And Ivy's match is unchanged
