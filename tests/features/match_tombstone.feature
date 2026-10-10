# ST-050a (FR-006, NFR-066 a; api-sprint-03 §4.1; ADR 0042). Owner: senior-backend-engineer,
# QA to accept. API binding: backend/tests/features/test_match_tombstone.py. The purge half of
# match_deletion.feature ("after the clean-up runs ...") is ST-050b.
@M0 @story-ST-050 @nfr-066
Feature: A deleted match is hidden at once
  Rule: Once Ivy confirms the deletion, nothing in her account shows the match

    Scenario: Deleting without the typed confirmation deletes nothing
      Given Ivy has a tagged match with stats
      When she deletes the match without typing the confirmation
      Then she is asked to confirm
      And her match is still in her list with its score sheet

    Scenario: A deleted match is gone from her account at once
      Given Ivy has a tagged match with stats
      When she deletes the match and confirms the stated consequences
      Then she is told when it will be purged, within 7 days
      And the match, its stats, its evidence, its score sheet and its video are not found
      And her list no longer shows the match
      And tagging a rally of it is refused as not found
