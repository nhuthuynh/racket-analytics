"""The `obs` Compose profile check (ST-075b; ADR 0057 §3; SEC-5 T5-OB-1, T5-OB-4, T5-OB-7).

``check`` is a pure function of the Compose file, the Prometheus config, the collector config
and the alert rules directory, so a test can plant a broken copy of any of them and see it fail.
It returns one line per problem, naming the service or key; [] when there is none.
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml
from conftest import REPO_ROOT

OBSERVABILITY = REPO_ROOT / "infra" / "observability"
PROMETHEUS_YML = OBSERVABILITY / "prometheus" / "prometheus.yml"
COLLECTOR_YML = OBSERVABILITY / "collector" / "config.yaml"
ALERTS_DIR = OBSERVABILITY / "alerts"
OBS_OVERLAY = OBSERVABILITY / "obs.env"

OBS_SERVICES = ("otel-collector", "prometheus")
# The two emitters of the SLI metrics (ADR 0057 §3 "App wiring").
EXPORTERS = ("api", "purge")
METRICS_ENDPOINT = "http://otel-collector:4318/v1/metrics"
ENDPOINT_PASSTHROUGH = "${OTEL_EXPORTER_OTLP_METRICS_ENDPOINT:-}"
# Pinned by tag and digest, pulled through the registry variable (test_compose_registry).
PINNED = re.compile(
    r"^\$\{DOCKERHUB_REGISTRY:-docker\.io\}/[a-z0-9./_-]+:[\w.-]+@sha256:[0-9a-f]{64}$"
)
# T5-OB-4: no write or admin path into Prometheus.
FORBIDDEN_FLAGS = (
    "--web.enable-admin-api",
    "--web.enable-remote-write-receiver",
    "--web.enable-otlp-receiver",
)
# T5-OB-7 and the 30-day SLO window (ADR 0057 §3).
RETENTION_FLAGS = ("--storage.tsdb.retention.time=31d", "--storage.tsdb.retention.size=1GB")
# docs/ops/sli-metrics.md attribute table (NFR-069; T5-OB-1 second guard).
ALLOWED_ATTRIBUTES = ("http.request.method", "http.response.status_code", "event", "reason")
STALENESS = "25h"  # longer than any PURGE_INTERVAL_S the scheduler accepts (86400 s)
RULES_MOUNT = "/etc/prometheus/rules/"


def _load(path: Path) -> dict:
    return yaml.safe_load(path.read_text()) or {}


def _env(svc: dict) -> dict[str, str]:
    env = svc.get("environment") or {}
    if isinstance(env, list):
        env = dict(e.split("=", 1) for e in env)
    return {k: str(v) for k, v in env.items()}


def _compose_problems(compose: dict) -> list[str]:
    services = compose.get("services") or {}
    problems: list[str] = []
    for name in OBS_SERVICES:
        svc = services.get(name)
        if svc is None:
            problems.append(f"{name}: missing from compose.yaml")
            continue
        if svc.get("profiles") != ["obs"]:
            problems.append(f"{name}: must be in profiles [obs] only, so `make up` is unchanged")
        if not PINNED.match(str(svc.get("image", ""))):
            problems.append(f"{name}: image {svc.get('image')!r} is not pinned by tag and digest")
        for port in svc.get("ports") or []:
            if not str(port).startswith("127.0.0.1:"):
                problems.append(f"{name}: port {port} is not bound to 127.0.0.1")
        command = [str(c) for c in svc.get("command") or []]
        for flag in FORBIDDEN_FLAGS:
            if any(c.startswith(flag) for c in command):
                problems.append(f"{name}: {flag} opens a write or admin path")
        if "healthcheck" not in svc:
            problems.append(f"{name}: no healthcheck")
    if services.get("otel-collector", {}).get("ports"):
        problems.append("otel-collector: publishes a port; OTLP and the exporter stay on the network")
    command = [str(c) for c in services.get("prometheus", {}).get("command") or []]
    problems += [f"prometheus: {f} missing" for f in RETENTION_FLAGS if f not in command]
    for name, svc in services.items():
        if name in OBS_SERVICES:
            continue
        deps = svc.get("depends_on") or {}
        for dep in deps if isinstance(deps, (list, dict)) else []:
            if dep in OBS_SERVICES and not svc.get("profiles"):
                problems.append(f"{name}: depends on {dep}, which only runs with the obs profile")
        env = _env(svc)
        endpoint = env.get("OTEL_EXPORTER_OTLP_METRICS_ENDPOINT")
        if name in EXPORTERS and endpoint != ENDPOINT_PASSTHROUGH:
            problems.append(f"{name}: OTEL_EXPORTER_OTLP_METRICS_ENDPOINT must be {ENDPOINT_PASSTHROUGH}")
        if name not in EXPORTERS and endpoint is not None:
            problems.append(f"{name}: exports metrics but is not an SLI emitter")
        if env.get("OTEL_METRICS_EXPORTER", "none") != "none":
            problems.append(f"{name}: OTEL_METRICS_EXPORTER must stay none (C-13)")
        temporality = env.get("OTEL_EXPORTER_OTLP_METRICS_TEMPORALITY_PREFERENCE")
        if name == "purge" and temporality != "delta":
            problems.append("purge: OTEL_EXPORTER_OTLP_METRICS_TEMPORALITY_PREFERENCE must be delta")
        if name != "purge" and temporality is not None:
            problems.append(f"{name}: only purge exports delta (ADR 0057 C4)")
    return problems


def _prometheus_problems(prom: dict, alerts_dir: Path) -> list[str]:
    problems: list[str] = []
    for rule_file in prom.get("rule_files") or []:
        name = str(rule_file)
        if any(ch in name for ch in "*?["):
            problems.append(f"rule_files: {name} is a glob; it would load the promtool test files")
        elif not name.startswith(RULES_MOUNT) or name.endswith(".test.yml"):
            problems.append(f"rule_files: {name} is not a rule file under {RULES_MOUNT}")
        elif not (alerts_dir / name.removeprefix(RULES_MOUNT)).is_file():
            problems.append(f"rule_files: {name} has no file in {alerts_dir.name}/")
    targets = [
        t
        for job in prom.get("scrape_configs") or []
        for sc in job.get("static_configs") or []
        for t in sc.get("targets") or []
    ]
    if "otel-collector:8889" not in targets:
        problems.append("scrape_configs: the collector exporter otel-collector:8889 is not scraped")
    return problems


def _collector_problems(col: dict) -> list[str]:
    problems: list[str] = []
    protocols = ((col.get("receivers") or {}).get("otlp") or {}).get("protocols") or {}
    if set(protocols) != {"http"}:
        problems.append(f"receivers.otlp: protocols {sorted(protocols)} must be [http] only")
    processors = col.get("processors") or {}
    if (processors.get("deltatocumulative") or {}).get("max_stale") != STALENESS:
        problems.append(f"processors.deltatocumulative: max_stale must be {STALENESS}")
    statements = [
        s
        for st in (processors.get("transform/allowlist") or {}).get("metric_statements") or []
        for s in st.get("statements") or []
    ]
    want = "keep_keys(attributes, [" + ", ".join(f'"{a}"' for a in ALLOWED_ATTRIBUTES) + "])"
    if statements != [want]:
        problems.append(f"processors.transform/allowlist: statements must be [{want}]")
    exporter = (col.get("exporters") or {}).get("prometheus") or {}
    if exporter.get("metric_expiration") != STALENESS:
        problems.append(f"exporters.prometheus: metric_expiration must be {STALENESS}")
    pipeline = (((col.get("service") or {}).get("pipelines") or {}).get("metrics")) or {}
    want_pipeline = {
        "receivers": ["otlp"],
        "processors": ["transform/allowlist", "deltatocumulative", "batch"],
        "exporters": ["prometheus"],
    }
    if pipeline != want_pipeline:
        problems.append(f"service.pipelines.metrics: must be {want_pipeline}")
    return problems


def check(
    compose_path: Path,
    prometheus_path: Path = PROMETHEUS_YML,
    collector_path: Path = COLLECTOR_YML,
    alerts_dir: Path = ALERTS_DIR,
) -> list[str]:
    """Every obs-profile problem, one line each; [] when none."""
    return (
        _compose_problems(_load(compose_path))
        + _prometheus_problems(_load(prometheus_path), alerts_dir)
        + _collector_problems(_load(collector_path))
    )
