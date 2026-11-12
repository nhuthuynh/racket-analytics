"""ST-075b unit tests: the `obs` Compose profile (NFR-042.5; ADR 0057 §3; SEC-5 T5-OB-1/4/7).

Negative cases first: each rule of ``compose_obs.check`` fails on a planted copy before the
shipped files are checked. The Docker cases run the pinned images' own validators
(``promtool check config``, ``otelcol-contrib validate`` and ``components``) on the shipped
config files, mounted read-only.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest
import yaml
from compose_env_parity import env_example
from compose_obs import (
    ALERTS_DIR,
    ALLOWED_ATTRIBUTES,
    COLLECTOR_YML,
    PROMETHEUS_YML,
    check,
)
from test_compose import COMPOSE, ENV_EXAMPLE

ENDPOINT = "OTEL_EXPORTER_OTLP_METRICS_ENDPOINT"
API_NAME = "      OTEL_SERVICE_NAME: racket-api"
needs_docker = pytest.mark.skipif(shutil.which("docker") is None, reason="docker CLI missing")


def services() -> dict:
    return yaml.safe_load(COMPOSE.read_text())["services"]


def image(name: str) -> str:
    return services()[name]["image"].replace("${DOCKERHUB_REGISTRY:-docker.io}", "mirror.gcr.io")


def planted(tmp_path: Path, which: str, old: str, new: str) -> list[str]:
    """Run the check with one of the three files replaced by a copy where old -> new."""
    files = {"compose": COMPOSE, "prometheus": PROMETHEUS_YML, "collector": COLLECTOR_YML}
    text = files[which].read_text()
    assert old in text, f"{old!r} not in {files[which].name}"
    copy = tmp_path / files[which].name
    copy.write_text(text.replace(old, new))
    files[which] = copy
    return check(files["compose"], files["prometheus"], files["collector"], ALERTS_DIR)


# ---------------------------------------------------------------- negative cases first
@pytest.mark.unit
def test_a_prometheus_port_on_every_interface_fails(tmp_path: Path) -> None:
    problems = planted(
        tmp_path, "compose", "127.0.0.1:${PROMETHEUS_HOST_PORT:-9090}:9090", "0.0.0.0:9090:9090"
    )
    assert "prometheus: port 0.0.0.0:9090:9090 is not bound to 127.0.0.1" in problems


@pytest.mark.unit
def test_a_published_collector_port_fails(tmp_path: Path) -> None:
    problems = planted(
        tmp_path,
        "compose",
        "    profiles: [obs]\n",
        '    profiles: [obs]\n    ports: ["127.0.0.1:4318:4318"]\n',
    )
    assert any(p.startswith("otel-collector: publishes a port") for p in problems), problems


@pytest.mark.unit
@pytest.mark.parametrize("flag", ["--web.enable-admin-api", "--web.enable-remote-write-receiver"])
def test_an_admin_or_write_flag_on_prometheus_fails(tmp_path: Path, flag: str) -> None:
    old = "      - --storage.tsdb.retention.size=1GB\n"
    problems = planted(tmp_path, "compose", old, f"{old}      - {flag}\n")
    assert f"prometheus: {flag} opens a write or admin path" in problems


@pytest.mark.unit
def test_an_image_without_a_digest_fails(tmp_path: Path) -> None:
    text = COMPOSE.read_text()
    tagged = services()["prometheus"]["image"]
    problems = planted(tmp_path, "compose", tagged, tagged.split("@")[0])
    assert any(p.startswith("prometheus: image") and "not pinned" in p for p in problems)
    assert tagged in text


@pytest.mark.unit
def test_an_app_service_that_needs_an_obs_service_fails(tmp_path: Path) -> None:
    old = (
        "      mailpit:\n        condition: service_healthy\n"
        '    healthcheck:\n      test: ["CMD", "python"'
    )
    new = old.replace(
        "      mailpit:\n",
        "      prometheus:\n        condition: service_healthy\n      mailpit:\n",
    )
    problems = planted(tmp_path, "compose", old, new)
    assert "api: depends on prometheus, which only runs with the obs profile" in problems


@pytest.mark.unit
def test_a_hard_coded_metrics_endpoint_fails(tmp_path: Path) -> None:
    problems = planted(
        tmp_path,
        "compose",
        f"{ENDPOINT}: ${{{ENDPOINT}:-}}\n{API_NAME}",
        f"{ENDPOINT}: http://otel-collector:4318/v1/metrics\n{API_NAME}",
    )
    assert any(p.startswith("api: OTEL_EXPORTER_OTLP_METRICS_ENDPOINT must be") for p in problems)


@pytest.mark.unit
def test_a_rule_file_glob_fails(tmp_path: Path) -> None:
    problems = planted(
        tmp_path, "prometheus", "/etc/prometheus/rules/billing.yml", "/etc/prometheus/rules/*.yml"
    )
    assert any(p.startswith("rule_files: /etc/prometheus/rules/*.yml is a glob") for p in problems)


@pytest.mark.unit
def test_a_promtool_test_file_in_rule_files_fails(tmp_path: Path) -> None:
    problems = planted(
        tmp_path,
        "prometheus",
        "/etc/prometheus/rules/billing.yml",
        "/etc/prometheus/rules/billing.test.yml",
    )
    assert any("billing.test.yml is not a rule file" in p for p in problems), problems


@pytest.mark.unit
def test_a_rule_file_that_does_not_exist_fails(tmp_path: Path) -> None:
    problems = planted(
        tmp_path,
        "prometheus",
        "/etc/prometheus/rules/billing.yml",
        "/etc/prometheus/rules/nope.yml",
    )
    assert any("nope.yml has no file" in p for p in problems), problems


@pytest.mark.unit
def test_the_default_five_minute_staleness_fails(tmp_path: Path) -> None:
    problems = planted(tmp_path, "collector", "max_stale: 25h", "max_stale: 5m")
    assert "processors.deltatocumulative: max_stale must be 25h" in problems
    problems = planted(tmp_path, "collector", "metric_expiration: 25h", "metric_expiration: 5m")
    assert "exporters.prometheus: metric_expiration must be 25h" in problems


@pytest.mark.unit
def test_an_attribute_added_to_the_collector_allowlist_fails(tmp_path: Path) -> None:
    problems = planted(tmp_path, "collector", '"reason"]', '"reason", "user.email"]')
    assert any(p.startswith("processors.transform/allowlist") for p in problems), problems


@pytest.mark.unit
def test_a_grpc_receiver_fails(tmp_path: Path) -> None:
    problems = planted(tmp_path, "collector", "      http:\n", "      grpc:\n      http:\n")
    assert any(p.startswith("receivers.otlp: protocols") for p in problems), problems


# ---------------------------------------------------------------- the shipped files
@pytest.mark.unit
def test_shipped_obs_profile_passes_the_check() -> None:
    assert check(COMPOSE) == []


@pytest.mark.unit
def test_the_collector_allowlist_is_the_sli_attribute_table() -> None:
    table = (COMPOSE.parents[1] / "docs" / "ops" / "sli-metrics.md").read_text()
    for attribute in ALLOWED_ATTRIBUTES:
        assert f"`{attribute}`" in table, attribute


@pytest.mark.unit
def test_env_example_ships_the_export_off_and_the_prometheus_port() -> None:
    example = env_example(ENV_EXAMPLE)
    assert example["OTEL_EXPORTER_OTLP_METRICS_ENDPOINT"] == ""
    assert example["PROMETHEUS_HOST_PORT"] == "9090"
    # Unset, so Compose's daily default applies (purge_compose_service.feature, ADR 0038);
    # only the obs overlay shortens it.
    assert "PURGE_INTERVAL_S" not in example


@pytest.mark.unit
@needs_docker
def test_promtool_accepts_the_shipped_prometheus_config() -> None:
    res = subprocess.run(
        [
            "docker", "run", "--rm", "--entrypoint", "promtool",
            "-v", f"{PROMETHEUS_YML}:/etc/prometheus/prometheus.yml:ro",
            "-v", f"{ALERTS_DIR}:/etc/prometheus/rules:ro",
            image("prometheus"), "check", "config", "/etc/prometheus/prometheus.yml",
        ],
        capture_output=True, text=True, timeout=180, check=False,
    )  # fmt: skip
    assert res.returncode == 0, res.stdout + res.stderr
    assert "SUCCESS: 2 rule files found" in res.stdout + res.stderr


@pytest.mark.unit
@needs_docker
def test_the_collector_accepts_the_shipped_config_and_has_the_components() -> None:
    mount = f"{COLLECTOR_YML}:/etc/otelcol-contrib/config.yaml:ro"
    run = ["docker", "run", "--rm", "-v", mount, image("otel-collector")]
    valid = subprocess.run(
        [*run, "validate", "--config=/etc/otelcol-contrib/config.yaml"],
        capture_output=True, text=True, timeout=180, check=False,
    )  # fmt: skip
    assert valid.returncode == 0, valid.stdout + valid.stderr
    comps = yaml.safe_load(
        subprocess.run(
            [*run, "components"], capture_output=True, text=True, timeout=180, check=True
        ).stdout
    )
    names = {
        kind: {c["name"] for c in comps[kind]} for kind in ("receivers", "processors", "exporters")
    }
    assert "otlp" in names["receivers"]
    assert {"deltatocumulative", "transform", "batch"} <= names["processors"]
    assert "prometheus" in names["exporters"]
