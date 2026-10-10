# SRE-PURGE-b (NFR-066 c, NFR-054; ADR 0038 Accepted; goal G03-03 c). Owner: sre-devops-engineer.
# Written before the binding ran green. Binding: infra/tests/test_purge_compose_service_scenarios.py
# renders infra/compose.yaml with the real `docker compose config` and an env file built from
# infra/env.example (what an operator does), then reads the rendered `purge` service.
# The live run of the service on a full stack is recorded in docs/ops/purge-schedule.md.
@ticket-SRE-PURGE-b @nfr-066 @nfr-054
Feature: The Compose stack runs the purge job at least once a day with the app identity
  Rule: The purge service holds the app's database login and object-store key, never the
        media sandbox worker's, and its schedule renders at most one day

    Scenario: The purge service never holds the media sandbox worker's login or key
      Given the stack environment from infra/env.example
      When the Compose configuration is rendered
      Then the purge service connects to the database as "POSTGRES_USER", not as "WORKER_DB_USER"
      And the purge service uses the object-store key "S3_ACCESS_KEY_ID", not "WORKER_S3_ACCESS_KEY_ID"
      And the purge service is on the "edge" network only

    Scenario: With no interval set, the purge job is scheduled once a day
      Given the stack environment from infra/env.example
      And PURGE_INTERVAL_S is not set
      When the Compose configuration is rendered
      Then the purge service's PURGE_INTERVAL_S is "86400"
      And the purge service runs "python -m racket.platform.purge --once" under the purge scheduler

    Scenario: An operator interval is passed to the purge scheduler as given
      Given the stack environment from infra/env.example
      And PURGE_INTERVAL_S is set to "3600"
      When the Compose configuration is rendered
      Then the purge service's PURGE_INTERVAL_S is "3600"
