# QA-VERIFY04R3-03 (G04-09 b, G04-10 a-c; FR-003, FR-160, NFR-023). Owner: senior-qa-engineer.
# Binding: infra/tests/test_live_privacy_harness_scenarios.py (the QA-HARNESS-4b stub, whose
# refusals now use the API's error body {"error": {"code", "message", "support_ref", ...}}
# of api-sprint-01 §1.1, as backend/src/racket/platform/errors.py sends it).
# Found live by SMOKE-04-03 and VERIFY-04-r3: the harness read `code`, `retry_at` and `quota`
# at the top level of the body and so failed a product that behaved as the rows ask.
@ticket-QA-VERIFY04R3-03
Feature: The privacy and quota harness reads refusals from the API's error envelope

  Rule: A refusal is judged only on the fields inside "error" (fail closed, ADR 0014)

    Scenario: A rate-limit refusal whose code sits outside the error envelope is found
      Given a stack that puts refusal codes at the top level of the body
      When the burst step runs
      Then the step fails, naming "status 429 None"

    Scenario: An under-18 refusal whose code sits outside the error envelope is found
      Given a stack that refuses under-18 answers without writing a row
      And a stack that puts refusal codes at the top level of the body
      When the age step runs
      Then the step fails, naming "under-18 answer status 403 None"

    Scenario: A storage refusal whose quota sits outside the error envelope is found
      Given a stack that puts refusal codes at the top level of the body
      When the quota step runs
      Then the step fails, naming "body lacks quota usage and limit"

    Scenario: A rate-limit refusal in the envelope without retry_at is found
      Given a stack whose rate-limit refusal carries no retry_at
      When the burst step runs
      Then the step fails, naming "429 without retry_at"

    Scenario: Refusals in the error envelope pass the age, burst and quota steps
      Given a stack that refuses under-18 answers without writing a row
      And a stack that accepts 10 matches an hour and refuses uploads past the quota
      When the steps "age burst quota" run
      Then every step passes
