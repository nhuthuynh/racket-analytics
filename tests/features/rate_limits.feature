# Sprint 4, ST-072a (FR-160; NFR-023; SEC-4 T4-QT-1, T4-QT-4). Contract: api-sprint-04 §7.
# Steps: backend/tests/features/test_rate_limits.py. The bursts of 50 are IT-04-09.
@story-ST-072a @nfr-023
Feature: Match creations and stored video are limited per account when quotas are on

  Scenario: Too many matches: the 11th match in an hour is refused with a time
    Given quotas are on
    And Ivy has created 10 matches in the last hour
    When Ivy creates another match
    Then it is refused as rate limited with a time within the hour
    And Ivy still has 10 matches

  Scenario: Storage quota: an upload that would pass the quota is refused before any byte
    Given quotas are on with a storage quota of 100000 bytes
    And Ivy has an unfinished upload of 60000 bytes
    When Ivy starts an upload of 50000 bytes on another match
    Then it is refused as over the storage quota with 60000 used of 100000
    And nothing is stored for that match

  Scenario: With quotas off only today's limits apply
    Given quotas are off with a storage quota of 100000 bytes
    And Ivy has created 10 matches in the last hour
    When Ivy creates another match
    Then the match is created
    And an upload of 150000 bytes on it is accepted
