# Sprint 3, ST-042 (NFR-054; SEC-R1S3-01; threat model S1-F3, v0 F-1).
# Owner: senior-backend-engineer. Steps: backend/tests/features/test_media_worker_identity.py
# Integration twins: backend/tests/integration/test_it_03_10_worker_grants.py (IT-03-10),
# backend/tests/integration/test_it_03_10b_worker_column_grants.py (IT-03-10b).
# Compose half (own login, own S3 key): infra/tests/test_compose_worker_identity(_live).py.
@M0 @story-ST-042 @nfr-054
Feature: The media sandbox worker runs with least privilege
  The worker that opens untrusted video files connects as its own Postgres role.
  That role can do the probe stage's work and nothing more.

  Rule: The media worker role cannot read identity data

    Scenario Outline: The media worker role is refused identity tables
      Given the database is migrated
      When the media worker role reads the <table> table
      Then the database answers "permission denied"

      Examples:
        | table            |
        | sessions         |
        | accounts         |
        | sign_in_links    |
        | sign_in_requests |

    Scenario: The media worker role reads the job table
      Given the database is migrated
      When the media worker role reads the jobs table
      Then the read succeeds

  Rule: The media worker role updates only the columns the probe stage writes

    Scenario Outline: The media worker role cannot change ownership or storage keys
      Given the database is migrated
      When the media worker role updates <column> of <table>
      Then the database answers "permission denied"

      Examples:
        | table        | column     |
        | matches      | owner_id   |
        | media_assets | owner_id   |
        | media_assets | object_key |

    Scenario: The media worker role records a probe result
      Given the database is migrated
      When the media worker role updates probe_status of media_assets
      Then the update succeeds
