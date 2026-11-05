# ST-076a (NFR-045.1; ADR 0058 rules 1-3, 5; SEC-5 T5-BK-1..3). Owner: sre-devops-engineer.
# Written before the binding ran green. Binding: infra/tests/test_backup_service_scenarios.py runs
# scripts/ops/backup.py as a process on throwaway backup directories; the restore scenario runs
# the real `backup` Compose service (profile ops) and is IT-05-03.
@ticket-ST-076a @nfr-045
Feature: Nightly encrypted backups whose age is known
  Rule: A backup set older than 24 hours is stale, an unencrypted backup is never written,
        and a complete set restores into an empty database

    Scenario: A backup set taken 25 hours ago is stale
      Given a complete backup set taken 25 hours ago
      When the backup status is read
      Then the newest complete set is reported as "stale"
      And the status command exits with code 1

    Scenario: A backup set taken 23 hours ago is fresh
      Given a complete backup set taken 23 hours ago
      When the backup status is read
      Then the newest complete set is reported as "fresh"
      And the status command exits with code 0

    Scenario: With no encryption recipient nothing is written, but old sets are still pruned
      Given a complete backup set taken 4 days ago
      And no encryption recipient is set
      When an on-demand backup runs
      Then the backup command exits with code 2 naming "BACKUP_AGE_RECIPIENT"
      And the set taken 4 days ago is gone
      And no new backup set exists

    Scenario: A private identity given as the recipient is refused
      Given the encryption recipient is an age private identity
      When an on-demand backup runs
      Then the backup command exits with code 2 naming "private identity"
      And no new backup set exists

    @integration
    Scenario: A backup of the Compose stack restores into an empty database
      Given the Compose stack with one confirmed correction and one media object
      When an on-demand backup runs in the backup service
      Then the newest set is complete, fresh and holds no plaintext dump
      And the set restores into an empty database with the correction and its append-only triggers
      And the object mirror holds the media object with its SHA-256
