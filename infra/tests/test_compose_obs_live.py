"""IT-05-02 (ST-075b, NFR-042.5): both SLI series reach Prometheus after a demo upload.

Binds the two live scenarios of tests/features/compose_obs_profile.feature. Needs a running
stack started with the obs overlay (``cat infra/observability/obs.env >> infra/.env; make up``):
``RA_OBS_PROMETHEUS_URL`` (e.g. http://127.0.0.1:9090) names its Prometheus, ``RA_DEMO_BASE_URL``
and ``RA_DEMO_CACERT`` its web (demo_live), and ``RA_DEMO_COMPOSE`` the Compose command when the
stack is not the default `make up` project. Skips without ``RA_OBS_PROMETHEUS_URL``; fails when
it is set but unreachable. The API exports every 60 s, so each series is polled for up to 180 s.
"""

from __future__ import annotations

import json
import os
import shlex
import subprocess
import time
import urllib.parse
import urllib.request
import uuid

import pytest
from conftest import REPO_ROOT
from demo_live import live_stack
from pytest_bdd import given, parsers, scenario, then, when

FEATURE = "compose_obs_profile.feature"
pytestmark = [pytest.mark.scenario, pytest.mark.integration]
POLL_S = 180.0


@scenario(FEATURE, "Both SLI series are in Prometheus after a demo upload (IT-05-02)")
def test_it_05_02_sli_series_present_after_demo_upload() -> None:
    pass


@scenario(FEATURE, "The collector drops a metric attribute that is not on the allowlist (T5-OB-1)")
def test_collector_drops_unlisted_attribute() -> None:
    pass


def compose_cmd() -> list[str]:
    return shlex.split(os.environ.get("RA_DEMO_COMPOSE", "docker compose -f infra/compose.yaml"))


def query(prom: str, promql: str) -> list[dict]:
    url = f"{prom}/api/v1/query?" + urllib.parse.urlencode({"query": promql})
    with urllib.request.urlopen(url, timeout=10) as r:  # noqa: S310 - loopback test URL
        return json.load(r)["data"]["result"]


def poll(prom: str, promql: str) -> list[dict]:
    deadline, result = time.monotonic() + POLL_S, []
    while time.monotonic() < deadline:
        result = query(prom, promql)
        if result:
            return result
        time.sleep(5)
    raise AssertionError(f"no series for {promql} after {POLL_S:.0f} s")


@given("a running stack with the obs profile", target_fixture="ctx")
def running_stack() -> dict:
    prom = os.environ.get("RA_OBS_PROMETHEUS_URL")
    if not prom:
        pytest.skip("RA_OBS_PROMETHEUS_URL not set (no stack with the obs profile)")
    with urllib.request.urlopen(f"{prom}/-/ready", timeout=10) as r:  # noqa: S310
        assert r.status == 200
    return {"prom": prom.rstrip("/")}


@when('"make demo" uploads the demo video')
def make_demo(ctx: dict) -> None:
    stack = live_stack()
    overrides = [f"DEMO_URL={stack.base_url}"]
    if os.environ.get("RA_DEMO_COMPOSE"):
        overrides.append(f"COMPOSE={os.environ['RA_DEMO_COMPOSE']}")
    res = subprocess.run(
        ["make", "--no-print-directory", "-C", str(REPO_ROOT), "demo", *overrides],
        capture_output=True, text=True, timeout=600, check=False,
    )  # fmt: skip
    assert res.returncode == 0, (res.stdout[-3000:], res.stderr[-3000:])


@then(parsers.parse('Prometheus has the series "{metric}" with event "{event}"'))
def has_series_with_event(ctx: dict, metric: str, event: str) -> None:
    result = poll(ctx["prom"], f'{metric}{{event="{event}"}}')
    assert all(float(s["value"][1]) >= 1 for s in result), result


@then(parsers.re(r'Prometheus has the series "(?P<metric>[a-z0-9_]+)"$'))
def has_series(ctx: dict, metric: str) -> None:
    result = poll(ctx["prom"], metric)
    assert any("http_response_status_code" in s["metric"] for s in result), result


@then("the collector scrape target is up")
def target_up(ctx: dict) -> None:
    result = query(ctx["prom"], 'up{job="otel-collector"}')
    assert [s["value"][1] for s in result] == ["1"], result


@then(parsers.parse('Prometheus has loaded the rule group "{group}"'))
def rule_group(ctx: dict, group: str) -> None:
    with urllib.request.urlopen(f"{ctx['prom']}/api/v1/rules", timeout=10) as r:  # noqa: S310
        groups = {g["name"] for g in json.load(r)["data"]["groups"]}
    assert group in groups, groups


@when(parsers.parse('a metric point with the attribute "{attribute}" is sent to the collector'))
def send_planted(ctx: dict, attribute: str) -> None:
    """OTLP/HTTP JSON from inside the Compose network: the collector publishes no port."""
    name = f"racket.it0502.planted{uuid.uuid4().hex[:8]}"
    now = str(time.time_ns())
    point = {
        "asInt": "1", "timeUnixNano": now, "startTimeUnixNano": now,
        "attributes": [
            {"key": "event", "value": {"stringValue": "created"}},
            {"key": attribute, "value": {"stringValue": "planted@example.invalid"}},
        ],
    }  # fmt: skip
    body = {
        "resourceMetrics": [{
            "resource": {"attributes": [{"key": "service.name", "value": {"stringValue": "it0502"}}]},
            "scopeMetrics": [{"metrics": [{"name": name, "sum": {
                "dataPoints": [point], "aggregationTemporality": 2, "isMonotonic": True,
            }}]}],
        }]
    }  # fmt: skip
    res = subprocess.run(
        [*compose_cmd(), "exec", "-T", "prometheus", "wget", "-q", "-O", "-",
         "--header", "Content-Type: application/json", "--post-data", json.dumps(body),
         "http://otel-collector:4318/v1/metrics"],
        capture_output=True, text=True, cwd=REPO_ROOT, timeout=60, check=False,
    )  # fmt: skip
    assert res.returncode == 0, res.stdout + res.stderr
    ctx["planted"] = name.replace(".", "_") + "_total"
    ctx["attribute"] = attribute


@then(parsers.parse('Prometheus has that series without a "{label}" label'))
def planted_label_dropped(ctx: dict, label: str) -> None:
    result = poll(ctx["prom"], ctx["planted"])
    assert all(label not in s["metric"] for s in result), result
    assert all(s["metric"].get("event") == "created" for s in result), result
