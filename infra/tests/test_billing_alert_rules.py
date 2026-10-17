"""IT-04-10 and unit tests for ST-073 (NFR-022; SEC-4 T4-AL-1, T4-AL-2). Negative cases first.

infra/observability/alerts/billing.yml holds six Prometheus alerting rules: the LLM provider and
the object store, each at 50/80/100% of a monthly budget metric. Budgets are env settings,
rendered as that metric by infra/observability/billing_budgets.py; no provider credential and
no receiver address is in git (the receiver URL is a secret file named by an env var).
"""

from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

import pytest
import yaml
from billing_alert_fixtures import (
    ALERTS_DIR,
    BUDGET_METRIC,
    ENV_EXAMPLE,
    OBSERVABILITY,
    OPS_DOC,
    PROMTOOL_IMAGE,
    PROVIDERS,
    RULE_TEST,
    RULES,
    SPEND_METRIC,
    THRESHOLDS,
    alert_name,
    full_env,
    load_rules,
    needs_docker,
    promtool,
    rule_by_alert,
)

SETTINGS = (
    "BILLING_BUDGET_LLM_PROVIDER_USD",
    "BILLING_BUDGET_OBJECT_STORE_USD",
    "BILLING_ALERT_RECEIVER_URL_FILE",
)
SEVERITY = {50: "info", 80: "warning", 100: "critical"}
RECEIVER = "billing-owner"


def _budgets_module():
    spec = importlib.util.spec_from_file_location(
        "billing_budgets", OBSERVABILITY / "billing_budgets.py"
    )
    assert spec is not None, "infra/observability/billing_budgets.py is missing"
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["billing_budgets"] = module
    spec.loader.exec_module(module)
    return module


# ------------------------------------------------- unit: negative cases first (T4-AL-1, -2)

# T4-AL-1: URLs, e-mail addresses and key-shaped strings (>= 20 base64/hex chars) must not be
# in the rule files. Allowlist: the six alert names (CamelCase words, no key material).
SECRET_SHAPES = (
    re.compile(r"https?://", re.IGNORECASE),
    re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+"),
    re.compile(r"(?<![\w/+=-])[A-Za-z0-9+/=]{20,}(?![\w/+=-])"),
)
ALLOWED = frozenset(alert_name(p, t) for p in PROVIDERS for t in THRESHOLDS)


@pytest.mark.unit
@pytest.mark.parametrize(
    "planted",
    [
        "https://hooks.example.invalid/T000/B000/XXXX",
        "owner@example.com",
        "Zm9vYmFyYmF6cXV4cXV1eGNvcmdl",
        "0123456789abcdef0123456789abcdef",
    ],
)
def test_secret_scan_catches_a_planted_secret(planted: str) -> None:
    """The scanner itself is not vacuous: each shape it guards against is caught."""
    assert any(p.search(f"url: {planted}") for p in SECRET_SHAPES)


@pytest.mark.unit
def test_alert_files_hold_no_url_address_or_key() -> None:
    files = sorted(ALERTS_DIR.glob("*.yml"))
    assert RULES in files
    hits = [
        (f.name, p.pattern, m.group(0))
        for f in files
        for p in SECRET_SHAPES
        for m in p.finditer(f.read_text(encoding="utf-8"))
        if m.group(0) not in ALLOWED
    ]
    assert hits == []


@pytest.mark.unit
@pytest.mark.parametrize("missing", SETTINGS)
def test_a_missing_setting_fails_closed_naming_only_the_variable(
    missing: str, tmp_path: Path
) -> None:
    budgets = _budgets_module()
    env = full_env(tmp_path)
    del env[missing]
    with pytest.raises(budgets.BillingConfigError) as err:
        budgets.load_settings(env)
    assert missing in str(err.value)
    for value in env.values():
        assert value not in str(err.value)


@pytest.mark.unit
@pytest.mark.parametrize("bad", ["", "0", "-5", "ten", "nan", "inf"])
def test_a_budget_that_is_not_a_positive_amount_is_refused_without_echoing_it(
    bad: str, tmp_path: Path
) -> None:
    budgets = _budgets_module()
    env = {**full_env(tmp_path), "BILLING_BUDGET_OBJECT_STORE_USD": bad}
    with pytest.raises(budgets.BillingConfigError) as err:
        budgets.load_settings(env)
    assert "BILLING_BUDGET_OBJECT_STORE_USD" in str(err.value)
    if bad:
        assert f"'{bad}'" not in str(err.value)
        assert f" {bad}" not in str(err.value)


@pytest.mark.unit
def test_a_receiver_file_that_does_not_exist_is_refused(tmp_path: Path) -> None:
    budgets = _budgets_module()
    env = {**full_env(tmp_path), "BILLING_ALERT_RECEIVER_URL_FILE": str(tmp_path / "absent")}
    with pytest.raises(budgets.BillingConfigError, match="BILLING_ALERT_RECEIVER_URL_FILE"):
        budgets.load_settings(env)


@pytest.mark.unit
def test_rules_file_has_exactly_six_alerts_and_nothing_else() -> None:
    rules = load_rules()
    assert sorted(r.get("alert", "<record>") for r in rules) == sorted(
        alert_name(p, t) for p in PROVIDERS for t in THRESHOLDS
    )


@pytest.mark.unit
@pytest.mark.parametrize("provider", PROVIDERS)
@pytest.mark.parametrize("threshold", THRESHOLDS)
def test_each_rule_compares_spend_with_its_share_of_the_budget(
    provider: str, threshold: int
) -> None:
    rule = rule_by_alert(alert_name(provider, threshold))
    expr = " ".join(rule["expr"].split())
    assert f'{SPEND_METRIC}{{provider="{provider}"}}' in expr
    assert f'{BUDGET_METRIC}{{provider="{provider}"}}' in expr
    assert expr.endswith(f">= {threshold / 100:g}"), expr
    assert rule.get("for", "0s") in ("0s", "0m")
    assert rule["labels"] == {
        "threshold_percent": str(threshold),
        "severity": SEVERITY[threshold],
        "receiver": RECEIVER,
    }
    assert set(rule["annotations"]) == {"summary", "runbook"}
    assert rule["annotations"]["runbook"] == "docs/ops/billing-alerts.md"


@pytest.mark.unit
def test_committed_rule_test_covers_each_alert_at_and_1pct_below_its_threshold() -> None:
    doc = yaml.safe_load(RULE_TEST.read_text(encoding="utf-8"))
    assert doc["rule_files"] == ["billing.yml"]
    seen: set[tuple[str, int, bool]] = set()
    for case in doc["tests"]:
        series = {s["series"]: s["values"] for s in case["input_series"]}
        for check in case["alert_rule_test"]:
            name = check["alertname"]
            provider = next(p for p in PROVIDERS if alert_name(p, 50)[:-2] in name)
            spend = float(series[f'{SPEND_METRIC}{{provider="{provider}"}}'].split("x")[0])
            budget = float(series[f'{BUDGET_METRIC}{{provider="{provider}"}}'].split("x")[0])
            seen.add((name, round(100 * spend / budget), bool(check["exp_alerts"])))
    for p in PROVIDERS:
        for t in THRESHOLDS:
            assert (alert_name(p, t), t, True) in seen
            assert (alert_name(p, t), t - 1, False) in seen


@pytest.mark.unit
def test_budget_metric_exposition_has_one_sample_per_provider(tmp_path: Path) -> None:
    budgets = _budgets_module()
    text = budgets.exposition(budgets.load_settings(full_env(tmp_path)))
    samples = [line for line in text.splitlines() if not line.startswith("#")]
    assert samples == [
        f'{BUDGET_METRIC}{{provider="llm_provider"}} 1000',
        f'{BUDGET_METRIC}{{provider="object_store"}} 250.5',
    ]
    assert f"# TYPE {BUDGET_METRIC} gauge" in text


@pytest.mark.unit
def test_env_example_lists_the_settings_with_empty_values() -> None:
    lines = ENV_EXAMPLE.read_text(encoding="utf-8").splitlines()
    for name in SETTINGS:
        assert f"{name}=" in lines, name


@pytest.mark.unit
def test_promtool_image_is_pinned_by_digest_through_the_mirror() -> None:
    assert re.fullmatch(
        r"mirror\.gcr\.io/prom/prometheus:v[\d.]+@sha256:[0-9a-f]{64}", PROMTOOL_IMAGE
    )


@pytest.mark.unit
def test_ops_doc_names_every_alert_setting_and_the_rule_test_command() -> None:
    text = OPS_DOC.read_text(encoding="utf-8")
    for name in (*SETTINGS, *(alert_name(p, t) for p in PROVIDERS for t in THRESHOLDS)):
        assert name in text, name
    assert "promtool test rules" in text
    assert PROMTOOL_IMAGE.split("@")[1] in text


# ------------------------------------------------- IT-04-10: the committed rule test, for real


@pytest.mark.integration
@needs_docker
def test_it_04_10_promtool_checks_and_tests_the_billing_rules() -> None:
    check = promtool(ALERTS_DIR, "check", "rules", "billing.yml")
    assert check.returncode == 0, check.stdout + check.stderr
    assert "SUCCESS: 6 rules found" in check.stdout + check.stderr
    result = promtool(ALERTS_DIR, "test", "rules", "billing.test.yml")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "SUCCESS" in result.stdout + result.stderr
