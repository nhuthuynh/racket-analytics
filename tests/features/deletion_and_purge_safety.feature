# PE-R3S3-03-ITS (review round 3: PE-R3S3-03 / SEC-R3S3-02 / QA-R3S3-05; FR-006, FR-007,
# NFR-066, NFR-047; threat notes T-DL-3, T-DL-4, T-AC-2, T-AC-3; ADR 0045). Owner:
# senior-qa-engineer. API binding: backend/tests/features/test_deletion_and_purge_safety.py.
# The integration tests with the corrupted-row, held-lock and 20-request variants are
# backend/tests/integration/test_pe_r3s3_03_deletion_and_purge_safety.py.
@M0 @story-ST-050 @story-ST-051 @nfr-066
Feature: Deleting one player's data never touches anyone else's and leaves nothing behind
  Rule: The clean-up removes only what belongs to the deleted account, and all of it

    Scenario: Another player's videos survive an account deletion byte for byte
      Given Ivy and Carlos each have a match with its video stored
      When Ivy deletes her account and the clean-up runs
      Then none of Ivy's matches, videos or profile remain stored
      And Carlos's video and match are exactly as they were

    Scenario: A stats update that arrives after a deletion stores nothing
      Given Ivy has a tagged match whose stats update has not arrived yet
      When she deletes the match and the stats update then arrives
      Then no stats are stored for the deleted match, before or after the clean-up

    Scenario: Stats left behind by a match that no longer exists are swept
      Given stats are stored for a match that no longer exists
      When the clean-up runs
      Then those stats are gone and the sweep is logged with the match id

    Scenario: Matches created while the account is being deleted do not survive it
      Given Ivy is creating several matches
      When she deletes her account while those requests are in flight
      Then no match of hers is left live, and after the clean-up nothing of hers remains

    Scenario: A rally video link taken before the deletion stops working
      Given Ivy copied the video link of a rally
      When she deletes her account and the clean-up runs
      Then the copied link answers not found
