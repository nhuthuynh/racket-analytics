# Sprint 2 §7.6, used unchanged for ST-038 (sprint-03 §7: "The Sprint 2
# abandoned_upload_expiry.feature is used unchanged"; FR-024, NFR-066 d, ADR 0006).
# API binding: backend/tests/features/test_abandoned_upload_expiry.py (both scenarios; the
# purge pass runs once in the time that passed). Integration level: IT-03-09.
@M0 @story-ST-038 @nfr-066
Feature: Abandoned upload expiry
  Scenario: Upload never finished
    Given Ivy started an upload 25 hours ago and never finished it
    When she opens her matches list
    Then the partial upload is not listed
    And it cannot be resumed

  Scenario: Upload finished in time
    Given Ivy started an upload 23 hours ago and finished it 1 hour later
    When she opens her matches list
    Then the match is listed with its video
