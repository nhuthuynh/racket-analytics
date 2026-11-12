# ST-076a-part2 (NFR-045.1; ADR 0058 rules 1-3; SEC-5 T5-BK-1..3). Owner: sre-devops-engineer.
# Written before the binding ran green. Binding: infra/tests/test_backup_service_live.py runs the
# real `backup` Compose service (profile ops) and is IT-05-03. The process-level scenarios are in
# backup_service.feature (ST-076a part 1).
@ticket-ST-076a @nfr-045
Feature: Backups of the Compose stack restore
  Rule: A complete set restores into an empty database and mirrors every media object

    @integration
    Scenario: A backup of the Compose stack restores into an empty database
      Given the Compose stack with one confirmed correction and one media object
      When an on-demand backup runs in the backup service
      Then the newest set is complete, fresh and holds no plaintext dump
      And the set restores into an empty database with the correction and its append-only triggers
      And the object mirror holds the media object with its SHA-256
