# 0057. SLOs, multiwindow burn-rate alerts, and a self-hosted OTel Collector + Prometheus `obs` profile

- **Status:** Accepted (principal-engineer) for the measurement, alert and backend design. The SLO targets and the error-budget policy stay **Proposed** until the human product owner decides **P17** (due 2026-11-12, sprint-05 §0.4); a change of target there changes only the thresholds in the alert table, not the design.
- **Date:** 2026-11-03
- **Deciders:** principal-engineer (design); human product owner (SLO commitment and error-budget policy, P17)
- **Consulted:** sre-devops-engineer (owner of ST-075b, ST-075c; ADR 0026 author), senior-backend-engineer (ST-075a, ST-075d), security-privacy-engineer (SEC-5 threat notes for the SLO and log pipeline)
- **Related:** ticket PE-5a, story ST-075 (gates ST-075a, ST-075b, ST-075d; feeds ST-075c); NFR-041, NFR-042, NFR-049 and their atomic rows in `docs/sprints/05/requirements-breakdown.md`; goal G05-02 (`docs/sprints/05/goal-scorecard.md`); ADR 0012 (fault seam), ADR 0014 (fail closed), ADR 0026 (SLI metric names and emission), ADR 0056 (tier 0 review)

## Context and problem statement

ADR 0026 made the API emit the two R1 SLIs as OpenTelemetry metrics: `http.server.request.duration` for availability (NFR-041) and `racket.upload.sessions` for upload completion (NFR-042), defined in `docs/ops/sli-metrics.md`. It left three things to Sprint 5: the metrics backend ("collector + Prometheus, or a managed service; a paid service is escalated"), the alerts, and the SLO commitment. Today the metrics go nowhere (`OTEL_EXPORTER_OTLP_METRICS_ENDPOINT` is unset in Compose; Jaeger stores traces only), and `infra/observability/alerts/` holds only the billing rules.

Sprint 5 goal G05-02 needs: promtool rule tests, 4 firing and 4 not firing (NFR-041.3-.4, NFR-042.3-.4); a live fault drill in which the fast-burn API alert fires within 10 minutes and a clean 10-minute run fires nothing (NFR-041.5); both SLI series present in the backend (NFR-042.5). This ADR fixes the windows, thresholds and the backend so that ST-075a, ST-075b, ST-075c and ST-075d build one design.

## Decision drivers

- An explicit numeric SLO per user journey, with an error budget = 100 % − SLO [AQS/REL-01, AQS/REL-02].
- No new paid or external service (sre-devops-engineer role rule; ADR 0026 consequence); licences that allow self-hosting.
- Dev/prod parity: the same backend in Compose as in the R1 deployment [AQS/OPS-05].
- OTel stays the only instrumentation API; no Prometheus client library in the app [AQS/OPS-07].
- Low traffic at R1: an alert must not page on one failed request out of three (judgment).
- No personal data in labels, alert payloads or logs (NFR-069; SEC-5 owns the threat rows).
- Smallest thing that meets G05-02; no Alertmanager, Grafana or long-term storage this sprint [AQS/ENG-04].

## Considered options

### A. Metrics backend

1. **Do nothing.** Pro: no work. Con: no series, no alerts; G05-02 and NFR-042.5 cannot be met.
2. **Managed service** (a hosted Prometheus or OTLP backend). Pro: no ops. Con: an external account and data leaving the host, a possible cost, credentials in env; dev and CI would differ from prod. Rejected under the "no paid service" driver; would need an EM/PO escalation.
3. **Prometheus alone with its native OTLP receiver.** Pro: one container. Con: the receiver is a feature flag of the Prometheus 3 line (unverified); the app would push straight into the TSDB, so later trace forwarding, attribute filtering or a second backend each mean an app config change.
4. **OTel Collector (OTLP receiver → `prometheus` exporter) scraped by Prometheus** (chosen). Pro: the standard OTel pipeline [AQS/OPS-07]; one place to drop or rename attributes before storage (a second PII guard after ST-075a's test); Prometheus evaluates the rules that promtool tests; both Apache-2.0 and self-hosted. Con: two containers.

### B. Alerting method

1. **Static threshold on the SLI** (e.g. availability < 99.5 % over 5 m). Pro: simple. Con: pages on every short blip at low traffic and misses a slow leak; not tied to the budget.
2. **Single-window burn rate.** Pro: tied to the budget. Con: a long window resets slowly after recovery; a short one is noisy.
3. **Multiwindow, multi-burn-rate alerts** (chosen): an alert fires only when the burn rate is over the threshold in both a long and a short window. The method and the 14.4 × over 1 h / 5 m page come from the Google SRE workbook chapter "Alerting on SLOs" (unverified: the SRE workbook is a Blocked source, `docs/research/architecture-quality-security.md` gaps table). Pro: precise and resets fast. Con: more expressions, which recording rules absorb.

## Decision outcome

Chosen: A4 and B3, with the values below.

### 1. SLIs and SLOs (30-day rolling window)

| SLI | Good / valid (unchanged from ADR 0026) | SLO | Error budget |
|---|---|---|---|
| API availability (NFR-041) | non-5xx / all responses, 429 excluded from both | 99.5 % | 0.5 % (≈ 3.6 h of full outage per 30 days) |
| Upload completion (NFR-042) | completed / (created − rejected − cancelled) | 99.0 % | 1.0 % |

The SLO report queries stay the ones in `docs/ops/sli-metrics.md` over `[30d]`. Targets come from `docs/requirements/non-functional-requirements.md` and become a commitment only with P17.

### 2. Burn-rate alerts

Burn rate = error ratio in the window / error budget. Thresholds are error ratios = burn rate × budget.

| Alert | SLI | Long / short window | Burn rate | Error ratio threshold | `for` | `severity` | Budget spent when it fires |
|---|---|---|---|---|---|---|---|
| `ApiAvailabilityFastBurn` | availability | 1 h / 5 m | 14.4 | 7.2 % | 2 m | `page` | 2 % in 1 h |
| `ApiAvailabilitySlowBurn` | availability | 6 h / 30 m | 1.5 | 0.75 % | 15 m | `ticket` | 1.25 % in 6 h |
| `UploadCompletionFastBurn` | upload completion | 1 h / 5 m | 14.4 | 14.4 % | 2 m | `page` | 2 % in 1 h |
| `UploadCompletionSlowBurn` | upload completion | 6 h / 30 m | 1.5 | 1.5 % | 15 m | `ticket` | 1.25 % in 6 h |

Why these values:

- **Fast burn 14.4 over 1 h / 5 m** spends 2 % of a 30-day budget in an hour, the workbook's page level (unverified). The NFR rows hold with margin: 10 % API errors (NFR-041.3) is 20 × and fires, 0.1 % is 0.2 × and does not; 20 % upload failures (NFR-042.3) fires, 0.5 % does not.
- **Slow burn 1.5 over 6 h / 30 m**, not the workbook's 6 ×. The NFR rows need a 1 % API error rate held for 6 h (2 ×) and a 3 % upload failure rate (3 ×) to fire, and 6 × would miss both. 1 × over 6 h would fire on a service that only spends its budget evenly; 1.5 × keeps margin both to the positive cases (2 ×, 3 ×) and to the negatives (0.3 % = 0.6 ×, 0.5 % = 0.5 ×) (judgment). It is a ticket, not a page.
- **Short window = 1/12 of the long one** so an alert stops soon after recovery (workbook, unverified).
- **Minimum volume guard (judgment):** each alert also needs, in its long window, at least 100 valid API requests (availability) or 10 valid uploads (upload completion). Without it one 500 among three requests at night is a 33 % error ratio and pages. promtool cases (NFR-041.3-.4, NFR-042.3-.4) use series above the guard; ST-075c adds no extra case for the guard unless the senior-qa-engineer asks for one.
- **Upload alerts use terminal outcomes.** In a 5 m or 1 h window, uploads that were created but are still running would count as failures under the report formula. The alert ratio is therefore `expired / (completed + expired)` over the window; on a series where every upload has ended this equals the report formula (`upload_completion()` with no open lifecycle), which is what NFR-042.1 checks. Consequence: an upload failure is seen only when the session expires (24 h after the last accepted chunk, capped at 72 h, `ExpiryPolicy` in `backend/src/racket/video_ingest/domain/extensions.py`), so the upload alerts are late by design; a server fault during an upload is caught first by the API availability alerts, because tus PATCH calls are API requests (judgment).
- **One `expired` event per failed upload (required, PE-5a-01).** Today `expired` is emitted only when a client touches an expired session (`backend/src/racket/video_ingest/service.py` line 445). The purge pass deletes abandoned uploads without an event (`_expire_uploads` in `backend/src/racket/platform/purge.py`), so most failed uploads would never reach the alert ratio. The purge pass must emit `UploadEvent.EXPIRED` for each upload it forgets whose status is not already `expired` (so an upload is never counted twice). The 30-day report formula is right without this, because a created upload stays in its base. This is a platform change in ST-075a's directory; the engineering-manager adds it to ST-075a's acceptance (red first: a purged abandoned upload adds one `expired` data point; an upload already marked expired adds none), or opens a separate ticket if ST-075a would pass 400 lines.
- **Recording rules** compute each SLI's error ratio once per window (`slo:api_error_ratio:rate5m`, `...rate30m`, `...rate1h`, `...rate6h`, and the same four for `slo:upload_error_ratio`); the four alerts compare those. Rules and alerts live in `infra/observability/alerts/slo.yml` (group `slo`, `interval: 30s`), tests in `slo.test.yml`, run with the promtool image already pinned in `infra/tests/billing_alert_fixtures.py` (`prom/prometheus:v3.5.0` by tag and digest). Both rule files are new in ST-075c (planned).
- **Labels and annotations:** `severity`, `slo` (`api_availability` or `upload_completion`), `window` (`fast` or `slow`); annotations `summary` and `runbook: docs/ops/slo.md`. Values only from the rule text; no request, user, path or upload attribute is copied into an alert.

Live drill timing (NFR-041.5, G05-02 "firing ≤ 10 min"): metric export every 60 s (the SDK default used by `configure_metrics`), scrape 15 s, rule evaluation 30 s and `for: 2m` add at most about 4 min. The long window also holds traffic from before the burst, so at error rate 10 % the 1 h ratio crosses 7.2 % once the burst has sent about 2.6 × the requests of the preceding hour. `inject_5xx.py` (ST-075c) must therefore send at least 5 requests/s and the drill stack must have had no load run in the previous hour; ST-075c records both in its dry-run row.

### 3. The `obs` Compose profile (ST-075b)

- Services `otel-collector` (`otel/opentelemetry-collector`, the core distribution, if `otelcol components` lists the `otlp` receiver and the `prometheus` exporter; otherwise `otel/opentelemetry-collector-contrib`; ST-075b records the output) and `prometheus` (`prom/prometheus:v3.5.0`, the image the promtool tests already use), both pinned by tag and digest, both in `profiles: [obs]`, so `make up` is unchanged.
- Collector pipeline: `otlp` receiver (HTTP, port 4318, Compose network only) → `batch` → `prometheus` exporter (port 8889, network only). Default name translation gives the series the queries expect: `http_server_request_duration_seconds_count`, `racket_upload_sessions_total`, label `http_response_status_code`.
- Prometheus: scrapes the collector every 15 s, loads `infra/observability/alerts/*.yml`, keeps data in a named volume with `--storage.tsdb.retention.time=31d` (covers the 30-day window) and `--storage.tsdb.retention.size=1GB` (disk floor, `docs/ops/disk-and-prune.md`). Its UI and API are published on `127.0.0.1:9090` only; there is no auth, so it is never bound to a public interface.
- App wiring: `OTEL_EXPORTER_OTLP_METRICS_ENDPOINT` stays empty by default in `infra/env.example` and is passed through to `api` and `purge` (the two emitters of upload events; `api` also emits the HTTP metric). The `obs` stack sets it to `http://otel-collector:4318/v1/metrics`. Without the profile nothing exports, so no export errors in a plain `make up` (the 404 noise in `docs/ops/sli-metrics.md` must not return). `OTEL_METRICS_EXPORTER=none` stays.
- Traces stay on Jaeger (`tracing`); routing traces through the collector is out of scope.
- Not in Sprint 5: Alertmanager and notification receivers (alerts are read from Prometheus `/api/v1/alerts`, which is what G05-02 measures), Grafana (`infra/observability/dashboards/slis.json` can be imported by hand), remote or long-term storage.

### 4. Error-budget policy (NFR-049)

ST-075c drafts `docs/ops/error-budget-policy.md` (planned) with trigger, action and owner. The outline this ADR sets: trigger = a 30-day budget fully spent at sprint planning, or a `page` alert firing for more than 1 h; action = the next sprint starts with reliability work on the cause before new feature tickets [AQS/REL-02 applied; the policy wording is judgment, the SRE workbook policy is unverified]; owner = engineering-manager at planning, sre-devops-engineer for the data. It is a draft until P17.

## Consequences

- **Good:** one design for four tickets; G05-02 is measurable with promtool and a local drill; no paid service, no data leaves the host; the collector is a second place to strip an attribute if one ever leaks.
- **Bad:** PE-5a-01 adds a small backend change to ST-075a; two more containers in the `obs` profile; upload alerts are up to a day late; no notification until an Alertmanager receiver is decided (a later ADR; a paging service with a cost goes to the EM/PO).
- **Follow-up for ST-075c (not edited here, ticket PRs only touch their own files):** the G05-02 method in `docs/sprints/05/goal-scorecard.md` runs promtool from `prom/prometheus:v2.53.2`; this ADR pins v3.5.0, the image of the existing promtool fixture. ST-075c aligns the method line in its own §6 row.
- **Production (R1 host):** the same two containers and rule files run next to the app, so dev and prod use the same backend [AQS/OPS-05]. Retention and size are revisited when traffic is known.
- **Rollback:** remove the `obs` services and the two rule files; unset `OTEL_EXPORTER_OTLP_METRICS_ENDPOINT`. The app is unchanged by this ADR (ADR 0026 emission stays).
- **Licences:** OpenTelemetry Collector and Prometheus are Apache-2.0 (judgment from their repositories; ST-075b records the licence rows with `scripts/ci/check_licences.py` if it covers images, otherwise in its decision file).

## Evidence

| Claim | Evidence |
|---|---|
| Metrics go nowhere today | `docs/ops/sli-metrics.md` §Export ("Compose has no metrics backend yet"); `git grep -n OTEL_EXPORTER_OTLP_METRICS_ENDPOINT origin/main -- infra/compose.yaml infra/env.example` → only the comment on `infra/compose.yaml` line 21 |
| Only billing alerts exist | `git ls-tree --name-only origin/main infra/observability/alerts/` → `billing.test.yml`, `billing.yml` |
| promtool image already pinned | `infra/tests/billing_alert_fixtures.py` line 28: `mirror.gcr.io/prom/prometheus:v3.5.0@sha256:63805ebb…` |
| Upload expiry is 24 h idle, 72 h cap | `backend/src/racket/video_ingest/domain/extensions.py` line 71 (`ExpiryPolicy` docstring); purge threshold `upload_idle = timedelta(hours=24)` (`backend/src/racket/platform/purge.py` line 77) |
| Purge emits no `expired` event | `grep -n -e SLI -e upload_event backend/src/racket/platform/purge.py` → no match; the only `UploadEvent.EXPIRED` call is `backend/src/racket/video_ingest/service.py` line 445 |
| Threshold arithmetic | 0.5 % × 14.4 = 7.2 %; 0.5 % × 1.5 = 0.75 %; 1 % × 14.4 = 14.4 %; 1 % × 1.5 = 1.5 %; 14.4 × 1 h / 720 h = 2 %; 1.5 × 6 h / 720 h = 1.25 % |
| NFR cases fall on the right side | API: 10 % > 7.2 % (fire), 0.1 % < 7.2 % (no); 1 % > 0.75 % (fire), 0.3 % < 0.75 % (no). Upload: 20 % > 14.4 % (fire), 0.5 % < 14.4 % (no); 3 % > 1.5 % (fire), 0.5 % < 1.5 % (no) |
| Executable proof | none in this ADR (docs ticket, TDD does not apply); ST-075c's 8 promtool cases and the G05-02 live drill are the tests of these values |
