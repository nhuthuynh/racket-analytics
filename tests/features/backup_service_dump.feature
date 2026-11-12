# ST-076a review round 1 (QA-076a-R1-01; NFR-045.1; ADR 0058 rules 1 and 3; SEC-5 T5-BK-1).
# Owner: sre-devops-engineer. Written before the binding ran. Binding:
# infra/tests/test_backup_service_dump_live.py runs scripts/ops/backup.py --once against a real
# Postgres 16 from scripts/dev-postgres.sh with the host pg_dump and age.
@ticket-ST-076a @nfr-045
Feature: An on-demand backup of a live database can be restored
  Rule: A complete set is age ciphertext with matching digests, and it restores the data

    Scenario: An on-demand backup restores the planted row into a scratch database
      Given a live database holding a planted row
      When an on-demand backup runs against it
      Then the backup command exits with code 0
      And every artefact of the new set starts with the age header
      And backup.json is complete and its digests match the files
      And decrypting the dump and restoring it into a scratch database returns the planted row

    Scenario: A wrong database password leaves no complete set
      Given a live database holding a planted row
      And the backup uses a wrong database password
      When an on-demand backup runs against it
      Then the backup command exits with code 1
      And no backup.json exists
      And the backup status is reported as "missing"
