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

  # ST-075c (sre-devops-engineer; ADR 0057 §2). Written before infra/observability/alerts/slo.yml.
  # Binding: infra/tests/test_slo_alerts_scenarios.py, one @scenario per name. "is firing" and
  # "is not firing" are the real `promtool test rules` (pinned image) on a synthetic series.
  Rule: A burn-rate alert fires on a real error-budget burn and not on noise (NFR-041.3-.4, NFR-042.3-.4)

    Scenario Outline: A burn under the threshold does not fire its alert
      Given the SLO rules
      When <percent> % of <sli> fail for <duration>
      Then "<alert>" is not firing

      Examples:
        | alert                    | sli           | percent | duration |
        | ApiAvailabilityFastBurn  | API responses | 0.1     | 10m      |
        | ApiAvailabilitySlowBurn  | API responses | 0.3     | 6h       |
        | UploadCompletionFastBurn | uploads       | 0.5     | 10m      |
        | UploadCompletionSlowBurn | uploads       | 0.5     | 6h       |

    Scenario Outline: A burn over the threshold fires its alert
      Given the SLO rules
      When <percent> % of <sli> fail for <duration>
      Then "<alert>" is firing

      Examples:
        | alert                    | sli           | percent | duration |
        | ApiAvailabilityFastBurn  | API responses | 10      | 10m      |
        | ApiAvailabilitySlowBurn  | API responses | 1       | 6h       |
        | UploadCompletionFastBurn | uploads       | 20      | 10m      |
        | UploadCompletionSlowBurn | uploads       | 3       | 6h       |

    Scenario: A fast-burn threshold planted at 100 % fails the committed rule test
      Given the SLO rules with the "ApiAvailabilityFastBurn" threshold planted at 100 %
      When the committed rule test runs
      Then it fails naming "ApiAvailabilityFastBurn"

  Rule: The drill burns the budget only through the test-only fault seam (NFR-041.5; ADR 0012)

    Scenario: The drill sends the fault header on the requested share of requests
      Given an API stub that answers 500 to "X-Racket-Fault: 5xx"
      When inject_5xx.py sends 200 requests at rate 10
      Then 20 requests carried the fault header
      And the report counts 20 responses with status 500

    Scenario: The drill fails when the expected alert never fires
      Given an API stub that answers 500 to "X-Racket-Fault: 5xx"
      And a Prometheus stub with no firing alert
      When inject_5xx.py runs expecting the alert "ApiAvailabilityFastBurn"
      Then it exits 1 naming "ApiAvailabilityFastBurn"

    Scenario: A 500 fails a run that expects none
      Given an API stub that answers 500 to "X-Racket-Fault: 5xx"
      When inject_5xx.py runs at rate 100 expecting no 5xx
      Then it exits 1 naming "500"
