# ST-076b (NFR-045.3; ADR 0058 rule 4 step 10; IT-05-04). Owner: senior-backend-engineer,
# QA to accept. Binding: backend/tests/features/test_corrections_fingerprint.py. The full drill
# (destroy volumes, restore, time the RTO) is ST-076c's restore_drill.feature.
@story-ST-076 @nfr-045
Feature: The corrections fingerprint shows that no confirmed correction was lost
  Rule: NFR-045.3 Count and SHA-256 of the confirmed corrections are equal after a restore

    Scenario: A dump restored into an empty database keeps every confirmed correction
      Given Ivy's match has a confirmed correction and its undo
      And the corrections fingerprint is recorded
      When the database is dumped and restored into an empty database
      Then the restored database has the same corrections count and SHA-256

    Scenario: A deleted correction is detected
      Given Ivy's match has a confirmed correction and its undo
      And the corrections fingerprint is recorded
      When one confirmed correction row is deleted behind the append-only guard
      Then the corrections count is one lower and the SHA-256 differs
      And racket-integrity checked against the recorded values exits 1 naming "corrections"

    Scenario: A backup that holds a deleted match stays equal after restore and purge
      Given Ivy's match has a confirmed correction and its undo
      And Ivy's second match with corrections is deleted but not yet purged
      And the corrections fingerprint is recorded
      When the database is dumped and restored into an empty database and the purge runs on it
      Then the deleted match has no correction rows in the restored database
      And the restored database has the same corrections count and SHA-256
