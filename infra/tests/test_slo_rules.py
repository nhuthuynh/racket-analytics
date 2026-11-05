"""Unit tests and the promtool IT for the SLO burn-rate rules (ST-075c; ADR 0057 §2).

infra/observability/alerts/slo.yml holds the recording rules (one error ratio per SLI and
window, one volume per SLI) and the four multiwindow burn-rate alerts; slo.test.yml holds the
eight promtool cases, one firing and one not firing per alert (NFR-041.3-.4, NFR-042.3-.4).
Negative cases first. The scenarios of tests/features/slo_alerts.feature are bound in
test_slo_alerts_scenarios.py.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess

import pytest
import yaml
from billing_alert_fixtures import ALERTS_DIR, needs_docker, promtool
from compose_obs import PROMETHEUS_YML
from conftest import REPO_ROOT
from slo_rule_fixtures import (
    ALERTS,
    RUNBOOK,
    SLO_RULE_TEST,
    SLO_RULES,
    burn_case,
    load_rules,
    rule_by_alert,
)

# (alert, percent, duration, fires): the NFR rows of docs/sprints/05/requirements-breakdown.md.
NFR_CASES = (
    ("ApiAvailabilityFastBurn", 0.1, "10m", False),  # NFR-041.3 negative: the first red
    ("ApiAvailabilityFastBurn", 10, "10m", True),  # NFR-041.3
    ("ApiAvailabilitySlowBurn", 0.3, "6h", False),  # NFR-041.4 negative
    ("ApiAvailabilitySlowBurn", 1, "6h", True),  # NFR-041.4
    ("UploadCompletionFastBurn", 0.5, "10m", False),  # NFR-042.3 negative
    ("UploadCompletionFastBurn", 20, "10m", True),  # NFR-042.3
    ("UploadCompletionSlowBurn", 0.5, "6h", False),  # NFR-042.4 negative
    ("UploadCompletionSlowBurn", 3, "6h", True),  # NFR-042.4
)
WINDOWS = {"fast": ("1h", "5m"), "slow": ("6h", "30m")}
RATIO = {"api_availability": "slo:api_error_ratio", "upload_completion": "slo:upload_error_ratio"}
VOLUME = {
    "api_availability": ("slo:api_valid_requests", 100),
    "upload_completion": ("slo:upload_terminal", 10),
}


def _records() -> dict[str, str]:
    return {r["record"]: " ".join(r["expr"].split()) for r in load_rules() if "record" in r}


def _alert_expr(name: str) -> str:
    return " ".join(rule_by_alert(name)["expr"].split())


# ------------------------------------------------- unit: negative cases first


@pytest.mark.unit
@pytest.mark.parametrize(("alert", "percent", "duration", "fires"), NFR_CASES)
def test_each_nfr_case_is_on_the_right_side_of_the_adr_threshold(
    alert: str, percent: float, duration: str, fires: bool
) -> None:
    """ADR 0057 §2 arithmetic: a steady error ratio fires iff it is over the threshold."""
    assert (percent / 100 > ALERTS[alert].error_ratio) is fires


@pytest.mark.unit
def test_rules_file_has_exactly_the_four_burn_rate_alerts() -> None:
    alerts = [r["alert"] for r in load_rules() if "alert" in r]
    assert sorted(alerts) == sorted(ALERTS)


@pytest.mark.unit
def test_rules_are_one_group_slo_evaluated_every_30s() -> None:
    doc = yaml.safe_load(SLO_RULES.read_text(encoding="utf-8"))
    assert [(g["name"], g.get("interval")) for g in doc["groups"]] == [("slo", "30s")]


@pytest.mark.unit
@pytest.mark.parametrize("name", sorted(ALERTS))
def test_each_alert_needs_both_windows_over_the_threshold_and_the_volume_guard(name: str) -> None:
    a = ALERTS[name]
    long_w, short_w = WINDOWS[a.window]
    ratio = RATIO[a.slo]
    volume, floor = VOLUME[a.slo]
    assert _alert_expr(name) == (
        f"{ratio}:rate{long_w} > {a.error_ratio:g} and {ratio}:rate{short_w} > {a.error_ratio:g}"
        f" and {volume}:increase{long_w} >= {floor}"
    )


@pytest.mark.unit
@pytest.mark.parametrize("name", sorted(ALERTS))
def test_each_alert_has_the_adr_labels_annotations_and_for(name: str) -> None:
    a = ALERTS[name]
    rule = rule_by_alert(name)
    assert rule["for"] == a.for_
    assert rule["labels"] == {"severity": a.severity, "slo": a.slo, "window": a.window}
    assert set(rule["annotations"]) == {"summary", "runbook"}
    assert rule["annotations"]["runbook"] == RUNBOOK


@pytest.mark.unit
def test_no_alert_copies_a_series_label_into_its_payload() -> None:
    """ADR 0057 §2: values only from the rule text (NFR-069): no template, no `$labels`."""
    for rule in load_rules():
        text = yaml.safe_dump({k: rule.get(k) for k in ("labels", "annotations")})
        name = rule.get("alert") or rule["record"]
        assert "{{" not in text, name
        assert "$labels" not in text, name


@pytest.mark.unit
def test_every_recorded_series_an_alert_reads_is_defined_once() -> None:
    names = [r["record"] for r in load_rules() if "record" in r]
    assert len(names) == len(set(names))
    used = {m for name in ALERTS for m in re.findall(r"slo:[a-z_]+:[a-z0-9]+", _alert_expr(name))}
    assert used <= set(names), used - set(names)


@pytest.mark.unit
@pytest.mark.parametrize("window", ["5m", "30m", "1h", "6h"])
def test_api_error_ratio_is_5xx_over_all_with_429_out_of_both(window: str) -> None:
    """NFR-041.1, the docs/ops/sli-metrics.md query as an error ratio, summed over emitters."""
    count = "http_server_request_duration_seconds_count"
    assert _records()[f"slo:api_error_ratio:rate{window}"] == (
        f'sum(rate({count}{{http_response_status_code=~"5.."}}[{window}]))'
        f' / sum(rate({count}{{http_response_status_code!="429"}}[{window}]))'
    )


@pytest.mark.unit
@pytest.mark.parametrize("window", ["5m", "30m", "1h", "6h"])
def test_upload_error_ratio_is_expired_over_terminal_outcomes(window: str) -> None:
    """NFR-042.1 with terminal outcomes only (ADR 0057 §2), summed over api and purge."""
    uploads = "racket_upload_sessions_total"
    assert _records()[f"slo:upload_error_ratio:rate{window}"] == (
        f'sum(increase({uploads}{{event="expired"}}[{window}]))'
        f' / sum(increase({uploads}{{event=~"completed|expired"}}[{window}]))'
    )


@pytest.mark.unit
def test_prometheus_loads_slo_yml_by_name() -> None:
    prom = yaml.safe_load(PROMETHEUS_YML.read_text(encoding="utf-8"))
    assert "/etc/prometheus/rules/slo.yml" in prom["rule_files"]


@pytest.mark.unit
def test_committed_rule_test_has_the_eight_nfr_cases_and_nothing_else() -> None:
    """Each committed case is the NFR burn (series and expected alert) of NFR_CASES."""
    doc = yaml.safe_load(SLO_RULE_TEST.read_text(encoding="utf-8"))
    assert doc["rule_files"] == ["slo.yml"]
    got = [(case["input_series"], case["alert_rule_test"]) for case in doc["tests"]]
    want = [
        (c["input_series"], c["alert_rule_test"])
        for c in (burn_case(a, p, d, f) for a, p, d, f in NFR_CASES)
    ]
    assert got == want


# ------------------------------------------------- IT: the committed rules and test, for real


@pytest.mark.integration
@needs_docker
def test_promtool_checks_the_slo_rules_and_passes_the_eight_cases() -> None:
    check = promtool(ALERTS_DIR, "check", "rules", "slo.yml")
    assert check.returncode == 0, check.stdout + check.stderr
    assert "SUCCESS:" in check.stdout + check.stderr
    result = promtool(ALERTS_DIR, "test", "rules", "slo.test.yml")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "SUCCESS" in result.stdout + result.stderr


# The backend's pure SLI functions (racket.platform.slis, ST-024) on one minute of each case.
PURE = """
import json, sys
from racket.platform.slis import availability, upload_completion
out = []
for c in json.load(sys.stdin):
    if c["sli"] == "api":
        codes = [int(code) for code, n in c["per_min"].items() for _ in range(n)]
        out.append(1 - availability(codes))
    else:
        n = c["per_min"]
        life = [("created", "completed")] * n["completed"] + [("created", "expired")] * n["expired"]
        life += [("created", "rejected")] * n["rejected"]
        good, base = upload_completion(life)
        out.append(1 - good / base)
print(json.dumps(out))
"""


def _per_minute(case: dict) -> dict:
    """Per-minute increments of a committed case, by status code (API) or by event (uploads)."""
    api: dict[str, int] = {}
    uploads: dict[str, int] = {"completed": 0, "expired": 0, "rejected": 0, "created": 0}
    for s in case["input_series"]:
        step = int(s["values"].split("+")[1].split("x")[0])
        if code := re.search(r'http_response_status_code="(\d+)"', s["series"]):
            api[code.group(1)] = api.get(code.group(1), 0) + step
        else:
            event = re.search(r'event="(\w+)"', s["series"]).group(1)  # type: ignore[union-attr]
            uploads[event] += step
    return {"sli": "api", "per_min": api} if api else {"sli": "uploads", "per_min": uploads}


@pytest.mark.integration
@pytest.mark.skipif(shutil.which("uv") is None, reason="uv missing")
def test_the_recorded_ratio_pinned_in_each_case_equals_the_backend_pure_function() -> None:
    """NFR-041.1, NFR-042.1: promtool pins the query value; this pins it to slis.py."""
    doc = yaml.safe_load(SLO_RULE_TEST.read_text(encoding="utf-8"))
    exprs = [c["promql_expr_test"][0]["expr"] for c in doc["tests"]]
    pinned = [float(re.search(r" - ([\d.e-]+)\) < bool", e).group(1)) for e in exprs]  # type: ignore[union-attr]
    res = subprocess.run(
        ["uv", "run", "--locked", "python", "-c", PURE],
        input=json.dumps([_per_minute(c) for c in doc["tests"]]),
        cwd=REPO_ROOT / "backend", capture_output=True, text=True, timeout=600, check=False,
    )  # fmt: skip
    assert res.returncode == 0, res.stderr
    assert json.loads(res.stdout) == pytest.approx(pinned, abs=1e-12)
