# Sprint 3 CI-IT0213-HANG. Owner: senior-backend-engineer. Written before the fix.
# Steps: backend/tests/features/test_ci_it0213_rate_on_a_slow_store.py (real API, Postgres and
# object store; the store is reached through a proxy that takes writes at 64 KiB/s, the rate
# measured in scheduled run 37764445816). Regression for the IT-02-13 timeout in that run.
@story-ST-027 @nfr-023
Feature: The per-account command rate is checked without waiting on the object store

  Scenario: Parallel game starts are limited while the object store is slow
    Given the object store takes writes at only 64 KiB per second
    And Ivy may send 5 scorebook commands per minute
    And Ivy has 12 matches whose video has been received
    When Ivy starts a game on all 12 matches at the same moment
    Then exactly 5 games are started and 7 are refused as rate limited
    And getting the 12 matches ready took less than 20 seconds
