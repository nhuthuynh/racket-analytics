# Billing alerts (NFR-022, ST-073)

Owner: sre-devops-engineer. Requirement: NFR-022 (R1: LLM provider and object storage; R2 adds
the GPU provider). Threat controls: `docs/security/threat-notes-sprint-04.md` §7 (T4-AL-1,
T4-AL-2). Decisions: `docs/sprints/04/decisions/ST-073.md`.

Scope of this ticket: **config and rules only**. No provider credential, no billing API call, no
receiver address in git. The month-to-date spend exporter and the Alertmanager deployment come
later (no metrics backend in Compose yet, `sli-metrics.md`); the monthly budget amounts wait on
the PO (**P8**, OQ-13).

## Rules

File: `infra/observability/alerts/billing.yml` (Prometheus rule group `billing`, evaluated every
5 min). Each alert fires as soon as month-to-date spend reaches its share of the monthly budget
(no `for:` delay) and stays firing for the rest of the month.

| Alert | Provider (`provider` label) | Fires when spend / budget ≥ | `severity` |
|---|---|---|---|
| `BillingLlmProviderBudget50` | `llm_provider` | 0.5 | `info` |
| `BillingLlmProviderBudget80` | `llm_provider` | 0.8 | `warning` |
| `BillingLlmProviderBudget100` | `llm_provider` | 1 | `critical` |
| `BillingObjectStoreBudget50` | `object_store` | 0.5 | `info` |
| `BillingObjectStoreBudget80` | `object_store` | 0.8 | `warning` |
| `BillingObjectStoreBudget100` | `object_store` | 1 | `critical` |

Every alert also carries `threshold_percent` (`"50"`, `"80"`, `"100"`) and `receiver:
billing-owner` (the Alertmanager receiver name; its URL is not in git), and the annotations
`summary` and `runbook` (this page).

Inputs, both gauges labelled `provider`:

- `racket_billing_monthly_budget_usd`: the monthly budget, from env settings (below).
- `racket_billing_spend_month_to_date_usd`: month-to-date spend in USD from the provider's
  billing export. **Not produced yet**; until an exporter exists the rules evaluate to nothing.

The expression is the ratio with a small tolerance, `spend / on(provider) budget >= t - 1e-9`
(t = 0.5, 0.8, 1). The bare ratio `>= t` is **not** exact for every budget: in IEEE 754 float64
`2.4 / 3` is `0.7999999999999999`, so a 3 USD (or 7, 12, 333 USD ...) budget at exactly 80% would
not fire; 1999 of the whole-dollar budgets 1..5000 miss at 80% that way. The tolerance 1e-9 is
far above that rounding error (< 1e-15) and below one cent for any budget under 10 million USD,
so a cent-exact spend at a threshold fires and a spend one cent below it does not. Pinned by
`billing.test.yml` (budgets 3 and 333) and the unit sweep in
`infra/tests/test_billing_alert_rules.py`.

## Settings (env, `infra/env.example`)

| Variable | Meaning | Default |
|---|---|---|
| `BILLING_BUDGET_LLM_PROVIDER_USD` | Monthly LLM provider budget, USD, > 0 | empty (P8) |
| `BILLING_BUDGET_OBJECT_STORE_USD` | Monthly object store budget, USD, > 0 | empty (P8) |
| `BILLING_ALERT_RECEIVER_URL_FILE` | Path of a mounted secret file holding the receiver's webhook URL (for Alertmanager `webhook_configs[].url_file`) | empty |

Render the budget metric (Prometheus text format, for the node-exporter textfile collector or a
static scrape target):

```bash
BILLING_BUDGET_LLM_PROVIDER_USD=... BILLING_BUDGET_OBJECT_STORE_USD=... \
BILLING_ALERT_RECEIVER_URL_FILE=/run/secrets/billing_alert_receiver_url \
  python3 infra/observability/billing_budgets.py > billing_budgets.prom
```

**Fail closed (T4-AL-2):** a missing, empty, non-numeric, non-finite or ≤ 0 budget, or a receiver
file that does not exist, exits 2 with `billing alerts: refusing to start: <VARIABLE> ...` on
stderr. The message names the variable, never its value; the receiver URL is never read.

## Testing the rules

The rule test `infra/observability/alerts/billing.test.yml` proves each alert fires at its
threshold and not 1% below it (budget 1000 USD; spend 490/500, 790/800, 990/1000). It runs with
`promtool` from the Prometheus image pinned by digest, pulled through mirror.gcr.io:

```bash
IMG=mirror.gcr.io/prom/prometheus:v3.5.0@sha256:63805ebb8d2b3920190daf1cb14a60871b16fd38bed42b857a3182bc621f4996
docker run --rm --network=none --entrypoint=/bin/promtool \
  -v "$PWD/infra/observability/alerts:/w:ro" -w /w "$IMG" check rules billing.yml
docker run --rm --network=none --entrypoint=/bin/promtool \
  -v "$PWD/infra/observability/alerts:/w:ro" -w /w "$IMG" test rules billing.test.yml
```

Expected output: `SUCCESS: 6 rules found` from `promtool check rules`, and `SUCCESS` from
`promtool test rules billing.test.yml`. The same runs in CI (`infra-tests` job):

- IT-04-10 `infra/tests/test_billing_alert_rules.py::test_it_04_10_promtool_checks_and_tests_the_billing_rules`
- scenarios `tests/features/billing_alerts.feature` (bound by
  `infra/tests/test_billing_alerts_scenarios.py`; each case generates its own promtool test)
- unit tests in `test_billing_alert_rules.py`: six rules, thresholds, labels, no URL / e-mail /
  key-shaped string in the rule files (T4-AL-1), fail-closed settings (T4-AL-2).

## When an alert fires

1. `info` (50%): note it in the sprint's blockers file; check the spend trend against the month.
2. `warning` (80%): tell the EM; find the driver (LLM: calls per coaching plan; object store:
   stored bytes per account, ST-072a quotas).
3. `critical` (100%): the EM escalates to the PO the same day (a new spend ceiling is a PO
   decision, P8). The provider-side hard limit, where one exists, is set by a human in the
   provider console; no credential for it is held by the agents.

## Changing a budget or adding a provider

- Budget: change the env value and re-render the metric; the rules do not change.
- New provider (R2: GPU): add its `BILLING_BUDGET_<PROVIDER>_USD` to `billing_budgets.py` and
  `env.example`, three rules to `billing.yml`, and its cases to `billing.test.yml`; the unit
  tests list the providers and fail until all three are in place.
