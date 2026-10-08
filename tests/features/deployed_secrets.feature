# Sprint 3, SEC-RV3-02 (T-ML-7; ADR 0025; NFR-056 "default credentials: 0").
# Owner: senior-backend-engineer. Steps: backend/tests/features/test_deployed_secrets.py
# Process-level twin: backend/tests/integration/platform/test_sec_rv3_02_dev_email_key.py
@M0 @story-SEC-RV3-02 @nfr-056
Feature: A deployed API never runs on the development email key

  Rule: Staging and production refuse a dev-only AUTH_EMAIL_KEY, however long it is

    Scenario Outline: The development email key is refused when deployed
      Given the environment is <environment> and the email key is the development placeholder from env.example
      When the API starts
      Then it refuses to start and says the email key is a development placeholder
      And the message does not show the key

      Examples:
        | environment |
        | staging     |
        | prod        |

    Scenario: A real email key is accepted in production
      Given the environment is prod and the email key is a real secret
      When the API starts
      Then it starts
