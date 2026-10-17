# Sprint 4, ticket ST-073 (sre-devops-engineer; NFR-022; SEC-4 T4-AL-1, T4-AL-2). Written before
# the rules existed. Binding: infra/tests/test_billing_alerts_scenarios.py evaluates the committed
# infra/observability/alerts/billing.yml with the real `promtool test rules` (pinned Prometheus
# image via mirror.gcr.io), feeding it a monthly budget metric and a month-to-date spend series.
@ticket-ST-073 @NFR-022 @IT-04-10
Feature: Billing alerts at 50/80/100% of the monthly budget (NFR-022)
  Rule: each paid provider (LLM provider, object store) has one alert per threshold; an alert
        fires when month-to-date spend reaches its share of the monthly budget, and not 1% below

    Scenario: 49% of the budget -> no billing alert
      Given the monthly budget for "llm_provider" is 1000 USD
      When the month-to-date spend for "llm_provider" is 49% of the budget
      Then no billing alert fires for "llm_provider"

    Scenario Outline: 1% below a threshold -> that threshold's alert does not fire
      Given the monthly budget for "<provider>" is 1000 USD
      When the month-to-date spend for "<provider>" is <below>% of the budget
      Then the <threshold>% alert for "<provider>" does not fire

      Examples:
        | provider     | threshold | below |
        | llm_provider | 50        | 49    |
        | llm_provider | 80        | 79    |
        | llm_provider | 100       | 99    |
        | object_store | 50        | 49    |
        | object_store | 80        | 79    |
        | object_store | 100       | 99    |

    Scenario Outline: At a threshold -> its alert fires
      Given the monthly budget for "<provider>" is 1000 USD
      When the month-to-date spend for "<provider>" is <threshold>% of the budget
      Then the <threshold>% alert for "<provider>" fires

      Examples:
        | provider     | threshold |
        | llm_provider | 50        |
        | llm_provider | 80        |
        | llm_provider | 100       |
        | object_store | 50        |
        | object_store | 80        |
        | object_store | 100       |

  Rule: budgets are env settings; a missing or invalid one fails closed and names only the variable

    Scenario: A missing budget setting -> no budget metric, error names the variable
      Given every billing setting is set except "BILLING_BUDGET_OBJECT_STORE_USD"
      When the budget metrics are rendered
      Then rendering fails naming "BILLING_BUDGET_OBJECT_STORE_USD"
      And no budget metric is written

    Scenario: All budget settings present -> one budget metric per provider
      Given every billing setting is set
      When the budget metrics are rendered
      Then a budget metric is written for "llm_provider" and "object_store"
