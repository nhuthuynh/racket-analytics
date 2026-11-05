# R1 SLOs and burn-rate alerts (NFR-041, NFR-042, ST-075c)

Owner: sre-devops-engineer. Design: ADR 0057 (§1 SLOs, §2 alerts, §3 `obs` profile). SLI
definitions and metric names: [`sli-metrics.md`](sli-metrics.md). Error-budget policy (draft):
[`error-budget-policy.md`](error-budget-policy.md). Decisions: `docs/sprints/05/decisions/ST-075c.md`.
Threat rows: `docs/security/threat-notes-sprint-05.md` T5-OB-5, T5-OB-6.

**Status: Proposed.** The targets below become a commitment only when the human product owner
decides **P17** (due 2026-11-12, sprint-05 §0.4). A new target changes only the alert thresholds.

## SLOs (30-day rolling window)

| SLI | Good / valid | SLO | Error budget |
|---|---|---|---|
| API availability (NFR-041.2) | non-5xx / all responses; 429 excluded from both | **99.5 %** | 0.5 % (about 3.6 h of full outage per 30 days) |
| Upload completion (NFR-042.2) | completed / (created − rejected − cancelled) | **99.0 %** | 1.0 % |

The 30-day report is the `sli-metrics.md` query over `[30d]`, with `otel_scope_name="racket"`
added to each selector. Only the `racket` meter scope is the SLI (ADR 0026): FastAPI's own
instrumentation exports the same metric name with `otel_scope_name="fastapi"` for a different
set of requests (on the drill stack it counted every injected 500 but 1 of 1149 successful
responses), so mixing the scopes skews the error ratio (found on the drill stack,
`decisions/ST-075c.md`).

## Alerts

File: `infra/observability/alerts/slo.yml`, rule group `slo`, evaluated every 30 s; loaded by
name in `infra/observability/prometheus/prometheus.yml`. An alert fires only when the error
ratio is over **burn rate × budget** in both its long and its short window and the long window
holds enough traffic (at least 100 valid API requests or 10 finished uploads).

| Alert | Windows | Burn rate | Error ratio over | `for` | `severity` |
|---|---|---|---|---|---|
| `ApiAvailabilityFastBurn` | 1 h and 5 m | 14.4 | 7.2 % | 2m | `page` |
| `ApiAvailabilitySlowBurn` | 6 h and 30 m | 1.5 | 0.75 % | 15m | `ticket` |
| `UploadCompletionFastBurn` | 1 h and 5 m | 14.4 | 14.4 % | 2m | `page` |
| `UploadCompletionSlowBurn` | 6 h and 30 m | 1.5 | 1.5 % | 15m | `ticket` |

Labels: `severity`, `slo` (`api_availability`, `upload_completion`), `window` (`fast`, `slow`).
Annotations: `summary`, `runbook` (this page). No series label is copied into an alert (NFR-069).
Recording rules: `slo:api_error_ratio:rate{5m,30m,1h,6h}`, `slo:upload_error_ratio:rate{...}`,
`slo:api_valid_requests:increase{1h,6h}`, `slo:upload_terminal:increase{1h,6h}`.

The upload ratio is `expired / (completed + expired)`: uploads still running are not failures.
An upload failure is therefore seen only when the session expires (24 h idle, 72 h cap), so the
upload alerts are late by design; a server fault during an upload shows first in the API alerts.
Until the purge exports its `expired` events (ADR 0057 PE-5a-01/02, escalated in
`decisions/ST-075b.md`), most failed uploads never reach the ratio, so the upload alerts do not
count toward G05-02 live; their promtool cases do.

No Alertmanager or receiver yet (ADR 0057 §3): read alerts at `http://127.0.0.1:9090/alerts` or
`/api/v1/alerts`.

## When an alert fires

1. Open Prometheus (`/alerts`) and check `slo:*_error_ratio:rate5m` against `rate1h`: a short
   window that has dropped back means the burn has stopped.
2. API alerts: `sum by (http_response_status_code) (rate(http_server_request_duration_seconds_count{otel_scope_name="racket",http_response_status_code=~"5.."}[5m]))`,
   then the API logs (`docker compose logs api`, `request_id` and `support_ref` per 500).
3. Upload alerts: `sum by (job) (increase(racket_upload_sessions_total{event="expired"}[1h]))`
   and the worker and purge logs.
4. A `page` alert firing for more than 1 h is a trigger of the error-budget policy.

## Tests

- `promtool test rules slo.test.yml` (in `infra/observability/alerts/`): 8 cases, each alert
  firing on its NFR burn and not firing on its negative burn (NFR-041.3-.4, NFR-042.3-.4), plus
  the recorded ratio equal to the share of failures (NFR-041.1, NFR-042.1). Image: the one pinned
  in `infra/tests/billing_alert_fixtures.py` (`PROMTOOL_IMAGE`, `prom/prometheus:v3.5.0`):
  ```
  docker run --rm --network=none --entrypoint=/bin/promtool -v "$PWD/infra/observability/alerts:/w:ro" \
    -w /w mirror.gcr.io/prom/prometheus:v3.5.0 test rules slo.test.yml
  ```
- `infra/tests/test_slo_rules.py` (rule shape, the committed cases, the backend's pure SLI
  functions on the same series), `infra/tests/test_slo_alerts_scenarios.py`
  (`tests/features/slo_alerts.feature`), `infra/tests/test_inject_5xx.py`,
  `infra/tests/test_compose_fault_drill.py`.

## Drill (NFR-041.5, G05-02)

The drill burns the API budget through the ST-075d fault seam: `scripts/ops/inject_5xx.py` sends
`--rate` % of its requests with `X-Racket-Fault: 5xx`. The API answers those with 500 only when
`APP_ENV=test` and `RACKET_FAULT_INJECTION=api:5xx_on_header`; under any other `APP_ENV` the
seam is dropped (NFR-041.6). `infra/compose.fault-drill.yaml` adds only that seam value to the
`api` service; `APP_ENV=test` comes from the shell for the drill's own project. The shipped
`infra/compose.yaml` and `infra/env.example` (`APP_ENV=dev`) never name the seam variable.

```
cat infra/env.example infra/observability/obs.env > infra/.env
export COMPOSE_PROJECT_NAME=racket-obs05
APP_ENV=test docker compose -f infra/compose.yaml -f infra/compose.fault-drill.yaml --env-file infra/.env \
  -p "$COMPOSE_PROJECT_NAME" --profile obs up -d --build --wait && make demo
python3 scripts/ops/inject_5xx.py --base-url https://localhost:3000 --rate 0 --minutes 10 \
  --expect-no-alert --prom http://localhost:9090 --json reports/slo-clean.json
python3 scripts/ops/inject_5xx.py --base-url https://localhost:3000 --rate 10 --minutes 10 \
  --expect-alert ApiAvailabilityFastBurn --prom http://localhost:9090 --json reports/slo-drill.json
docker compose -f infra/compose.yaml -f infra/compose.fault-drill.yaml -p "$COMPOSE_PROJECT_NAME" \
  --profile obs down -v --rmi local
```

- Clean run first, on a fresh stack. During a 10 % burst `ApiAvailabilitySlowBurn` goes
  pending too (drill dry run), and it can fire until its 30 m window has cleared, so a clean
  run right after the drill is not clean.
- `inject_5xx.py` sends 10 requests/s by default (ADR 0057: at least 5) to `/api/healthz`. The
  stack must have had no load run in the previous hour, or the 1 h ratio needs a longer burst.
- Exit codes: 0 expectations met; 1 an expectation failed (named on stderr); 2 usage error or
  the API or Prometheus unreachable (not evidence).
- `--cacert` defaults to `.local/demo/root.crt`, which `make demo` copies from `web-tls`.
- **Test-mode differences on the drill stack** (sprint-05 §3.7 ST-075c; T5-OB-6): the session
  cookie is not `__Host-`/Secure; `DEV_IDENTITY_ENABLED` is the `.env` value (dev users seeded
  when on); `/docs`, `/redoc`, `/openapi.json` are public; the API does not migrate on startup
  (the `migrate` service does); the seam is honoured. The stack is local only, bound to
  `127.0.0.1`, demo data only, and torn down after the drill.
- Negative (NFR-041.6): against a `make up` stack (`APP_ENV=dev`),
  `inject_5xx.py --rate 100 --minutes 1 --expect-no-5xx` gets 0 responses with status 500.

## Rollback

Remove `/etc/prometheus/rules/slo.yml` from `prometheus.yml` and delete `slo.yml` and
`slo.test.yml` (ADR 0057 "Rollback"). The drill override and script change nothing unless run.
