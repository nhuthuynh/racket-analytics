# SLI metrics (ST-024)

Owner: sre-devops-engineer. Decision: ADR 0026. Contract: `docs/architecture/api-sprint-01.md` §10
(names confirmed by SRE on 2026-10-05). Code: `backend/src/racket/platform/slis.py`.
Alerts and burn-rate paging are Sprint 5.

## Instruments

| Instrument | Type | Attributes | Emitted by |
|---|---|---|---|
| `http.server.request.duration` | histogram, s | `http.request.method` (unknown methods → `_OTHER`), `http.response.status_code` | `HttpMetricsMiddleware`, the outermost API middleware. A crash before any response counts as 500 |
| `racket.upload.sessions` | counter | `event` ∈ `created`, `completed`, `expired`, `rejected`, `cancelled`; `reason` (rejection code) on `rejected` only | the upload context via `SLIRecorder().upload_event(UploadEvent.X, reason=...)` (ST-017, ST-018; `cancelled` with DELETE in Sprint 2) |

No user ID, email, path, match or file data in attributes (NFR-069). Meter name: `racket`.

## SLIs

| SLI | Definition | Pure function (unit-tested) | Prometheus query (OTel → Prometheus naming) |
|---|---|---|---|
| Availability (NFR-041) | non-5xx / all responses, 429 excluded from both | `availability(status_codes)` | `sum(rate(http_server_request_duration_seconds_count{http_response_status_code!~"5..\|429"}[w])) / sum(rate(http_server_request_duration_seconds_count{http_response_status_code!="429"}[w]))` |
| Upload completion (NFR-042) | completed / (created − rejected − cancelled); expired or still-open uploads stay in the base | `upload_completion(lifecycles)` → `(good, base)` | `sum(increase(racket_upload_sessions_total{event="completed"}[w])) / (sum(increase(racket_upload_sessions_total{event="created"}[w])) - sum(increase(racket_upload_sessions_total{event=~"rejected\|cancelled"}[w])))` |

Dashboard: `infra/observability/dashboards/slis.json` (Grafana; import it and choose the Prometheus data source).

## Export

- Set `OTEL_EXPORTER_OTLP_METRICS_ENDPOINT` (full URL, e.g. `http://collector:4318/v1/metrics`) to export over OTLP/HTTP every 60 s. Unset means the global no-op provider: nothing is exported.
- Compose has no metrics backend yet; Jaeger (`tracing`) stores traces only, so do not point the metrics endpoint at it.
- **FastAPI's automatic telemetry** (`fastapi/telemetry/_runtime.py`, in the locked FastAPI) exports traces, metrics and logs to `{OTEL_EXPORTER_OTLP_ENDPOINT}/v1/<signal>` on its own. Compose therefore sets `OTEL_METRICS_EXPORTER=none` and `OTEL_LOGS_EXPORTER=none` for api, worker and mailer (C-13, SRE-G2-01). Before that, Jaeger answered every minute's metrics batch with 404 (`Failed to export metrics batch code: 404`, CI run 37429011095 and live). These two variables do not affect `OTEL_EXPORTER_OTLP_METRICS_ENDPOINT`, which our own `configure_metrics` reads. Live check (racket-sre02, 2026-10-06): 0 export errors in api, worker and mailer over more than one 60 s interval after the change; traces still arrive in Jaeger. Choosing the backend (collector + Prometheus, or a managed service) is a Sprint 5 decision with the alerts; a paid service is escalated to the EM/PO.

## Nightly quality results

`.github/workflows/nightly-quality.yml` writes the `nightly` key of the current sprint's `status.json`
(see ADR 0026 and `scripts/ci/nightly_status.py`): `run_date`, `run_url`, `commit`,
`oracle` (`status`, `sequences`, `disagreements`, `passed`, `seed`, `shortest`, `job`) and
`mutation` (`status`, `score` 0..1, `scope`, counts, `job`). Run by hand: Actions → Nightly quality → Run workflow.
