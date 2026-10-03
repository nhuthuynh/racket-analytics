# Sprint 0 §7. Owner: senior-qa-engineer. Written before implementation (ST-012).
# Steps: backend/tests/features/test_dev_environment.py
@M0 @story-ST-001 @nfr-080 @nfr-081
Feature: Development environment matches production's backing services

  Rule: Configuration comes only from the environment

    Scenario: A required setting is missing
      Given the database address is not set
      When the API starts
      Then it refuses to start and names the missing setting

    Scenario: Development identities cannot run in production
      Given the environment is production and the development sign-in is enabled
      When the API starts
      Then it refuses to start and says development sign-in is not allowed
