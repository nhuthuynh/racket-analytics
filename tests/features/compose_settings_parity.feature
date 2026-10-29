# Sprint 4 fix wave, ticket SRE-VERIFY04R3-02 (sre-devops-engineer; retro C2/C3, VERIFY-04-r3).
# Written before compose.yaml forwarded the settings. Binding:
# infra/tests/test_compose_settings_parity_scenarios.py (parity check on real or planted copies of
# infra/env.example + infra/compose.yaml; the stack's real `docker compose config`).
@ticket-SRE-VERIFY04R3-02
Feature: Every app setting in infra/env.example reaches the Compose services that read it
  Rule: a setting the backend reads is forwarded to every service that builds its Settings,
        with the env.example value as the fallback, so infra/.env alone switches it

    Scenario: A planted setting that Compose does not forward is reported
      Given env.example declares "FEATURE_PLANTED" which the backend Settings reads
      And compose.yaml does not forward it
      When the env-to-Compose parity check runs
      Then it fails naming "FEATURE_PLANTED" for the services "api, worker, mailer, purge"

    Scenario: The shipped env.example and compose.yaml are in parity
      Given the shipped env.example and compose.yaml
      When the env-to-Compose parity check runs
      Then it reports no problem

    Scenario: With the env.example values the Sprint 4 flags are off in every backend service
      Given an env file copied from env.example
      When Compose renders the stack configuration
      Then "FEATURE_AGE_GATE, FEATURE_RETENTION_SETTING, FEATURE_TRAINING_CONSENT, FEATURE_QUOTAS" are "false" in "api, worker, mailer, purge"
      And "COACHING_WEAKNESS_UNIT" is "rallies_lost_per_game" in "api, worker, mailer, purge"

    Scenario: Switching the flags on in the env file switches them on in every backend service
      Given an env file copied from env.example
      And the env file sets "FEATURE_AGE_GATE, FEATURE_RETENTION_SETTING, FEATURE_TRAINING_CONSENT, FEATURE_QUOTAS" to "1"
      And the env file sets "STORAGE_QUOTA_BYTES" to "1048576"
      When Compose renders the stack configuration
      Then "FEATURE_AGE_GATE, FEATURE_RETENTION_SETTING, FEATURE_TRAINING_CONSENT, FEATURE_QUOTAS" are "1" in "api, worker, mailer, purge"
      And "STORAGE_QUOTA_BYTES" is "1048576" in "api, worker, mailer, purge"
