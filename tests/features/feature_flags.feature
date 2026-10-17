# Sprint 4, ST-067 (FR-003/008/009/120/160; ADR 0003, ADR 0023, ADR 0051 rule 4).
# Steps: backend/tests/features/test_feature_flags.py. Contract: api-sprint-04 §1 rule 3, §11.
@story-ST-067
Feature: The weakness unit and the R1 feature flags are configuration, and the flags start off

  Scenario: An unknown weakness unit refuses to start
    Given the weakness unit is configured as "points_lost_per_game"
    When the API starts
    Then it refuses to start and names the setting COACHING_WEAKNESS_UNIT

  Scenario: The feature flags are off by default
    Given no feature flag is configured
    When a visitor without a session reads the public configuration
    Then the features on are ""
    And the weakness unit is "rallies_lost_per_game"

  Scenario: A flag switched on is shown to the web
    Given no feature flag is configured
    And FEATURE_QUOTAS is "true"
    When a visitor without a session reads the public configuration
    Then the features on are "quotas"
