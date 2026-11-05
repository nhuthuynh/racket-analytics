# Sprint 5, story ST-075 "We know when R1 is unhealthy" (NFR-041, NFR-042; ADR 0057).
# ST-075d (senior-backend-engineer) adds the fault seam rule, written before the middleware.
# Binding (seam rule): backend/tests/features/test_slo_alerts.py, one @scenario per name, so
# rules that ST-075c adds here (burn-rate alerts, the drill) bind in their own step modules.
@story-ST-075 @nfr-041
Feature: We know when R1 is unhealthy

  Rule: The API fault seam is honoured only when APP_ENV is test (ADR 0012; NFR-041.6)

    Scenario: The fault seam is inert outside the test environment
      Given the API runs with APP_ENV "dev" and the fault seam "api:5xx_on_header"
      When a request carries the header "X-Racket-Fault: 5xx"
      Then the API answers normally

    Scenario: An injected API fault is a 500 counted against availability
      Given the API runs with APP_ENV "test" and the fault seam "api:5xx_on_header"
      When a request carries the header "X-Racket-Fault: 5xx"
      Then the API answers with a generic 500 error
      And the 500 is recorded in the request duration metric
