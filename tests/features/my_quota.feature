# QA-VERIFY04R3-04 (FR-160; Q-01 "how much is used and when the player can continue").
# Contract: api-sprint-04 §1 rule 2, §7. Steps: backend/tests/features/test_my_quota.py.
# Every case of the route (401, other account, deleted match, at the limit): IT-04-09b.
@story-ST-072a @nfr-023
Feature: A player can see how much of her quota she has used when quotas are on

  Scenario: Ivy sees her stored bytes and match creations against her limits
    Given quotas are on with a storage quota of 100000 bytes
    And Ivy has an unfinished upload of 60000 bytes
    When Ivy asks for her quota
    Then she has used 60000 of 100000 bytes
    And she has used 1 of 10 match creations this hour and need not wait

  Scenario: With quotas off there is no quota to read
    Given quotas are off
    When Ivy asks for her quota
    Then the quota is not found
