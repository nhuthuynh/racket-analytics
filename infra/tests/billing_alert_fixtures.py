"""Helpers for the ST-073 billing alert tests (NFR-022; IT-04-10).

``promtool`` runs from the Prometheus image pinned by tag *and* digest, pulled through
mirror.gcr.io (Docker Hub rate-limits CI). Rule files are mounted read-only; nothing else in
the repository is visible to the container.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml
from conftest import REPO_ROOT

OBSERVABILITY = REPO_ROOT / "infra" / "observability"
ALERTS_DIR = OBSERVABILITY / "alerts"
RULES = ALERTS_DIR / "billing.yml"
RULE_TEST = ALERTS_DIR / "billing.test.yml"
ENV_EXAMPLE = REPO_ROOT / "infra" / "env.example"
OPS_DOC = REPO_ROOT / "docs" / "ops" / "billing-alerts.md"

PROMTOOL_IMAGE = (
    "mirror.gcr.io/prom/prometheus:v3.5.0"
    "@sha256:63805ebb8d2b3920190daf1cb14a60871b16fd38bed42b857a3182bc621f4996"
)
PROVIDERS = ("llm_provider", "object_store")
THRESHOLDS = (50, 80, 100)
SPEND_METRIC = "racket_billing_spend_month_to_date_usd"
BUDGET_METRIC = "racket_billing_monthly_budget_usd"

needs_docker = pytest.mark.skipif(shutil.which("docker") is None, reason="docker CLI missing")


def alert_name(provider: str, threshold: int) -> str:
    """Ubiquitous name: ``Billing<Provider>Budget<threshold>``, e.g. BillingLlmProviderBudget80."""
    camel = "".join(part.capitalize() for part in provider.split("_"))
    return f"Billing{camel}Budget{threshold}"


def load_rules() -> list[dict]:
    doc = yaml.safe_load(RULES.read_text(encoding="utf-8"))
    return [rule for group in doc["groups"] for rule in group["rules"]]


def rule_by_alert(name: str) -> dict:
    matches = [r for r in load_rules() if r.get("alert") == name]
    assert len(matches) == 1, f"{name}: {len(matches)} rules"
    return matches[0]


def promtool(workdir: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """Run promtool with ``workdir`` mounted read-only at /w (its cwd)."""
    return subprocess.run(
        [
            "docker",
            "run",
            "--rm",
            "--network=none",
            "--entrypoint=/bin/promtool",
            "-v",
            f"{workdir}:/w:ro",
            "-w",
            "/w",
            PROMTOOL_IMAGE,
            *args,
        ],
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )


def expected_alert(provider: str, threshold: int) -> dict:
    """The alert promtool must see: the spend series' labels plus the rule's labels/annotations."""
    rule = rule_by_alert(alert_name(provider, threshold))
    return {
        "exp_labels": {"provider": provider, **rule["labels"]},
        "exp_annotations": dict(rule["annotations"]),
    }


def rule_test_doc(provider: str, percent: int, budget_usd: int, fires: dict[int, bool]) -> dict:
    """A promtool unit-test document: one budget, one spend sample, expected alerts at t=1m.

    ``fires`` maps a threshold (50/80/100) to whether its alert must fire for ``provider``.
    """
    spend = budget_usd * percent / 100
    return {
        "rule_files": ["billing.yml"],
        "evaluation_interval": "1m",
        "tests": [
            {
                "interval": "1m",
                "input_series": [
                    {
                        "series": f'{BUDGET_METRIC}{{provider="{provider}"}}',
                        "values": f"{budget_usd}x5",
                    },
                    {
                        "series": f'{SPEND_METRIC}{{provider="{provider}"}}',
                        "values": f"{spend:g}x5",
                    },
                ],
                "alert_rule_test": [
                    {
                        "eval_time": "1m",
                        "alertname": alert_name(provider, threshold),
                        "exp_alerts": [expected_alert(provider, threshold)] if fire else [],
                    }
                    for threshold, fire in fires.items()
                ],
            }
        ],
    }


def run_rule_test(tmp_path: Path, doc: dict) -> subprocess.CompletedProcess[str]:
    """Copy billing.yml next to a generated test file and run ``promtool test rules`` on it."""
    work = tmp_path / "promtool"
    work.mkdir(exist_ok=True)
    shutil.copy(RULES, work / "billing.yml")
    (work / "case.test.yml").write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")
    # The image runs promtool as `nobody`; pytest's tmp dirs are 0700 for the test's own user.
    os.chmod(work, 0o755)  # noqa: S103 - throwaway test dir, read-only mount
    for f in work.iterdir():
        os.chmod(f, 0o644)
    return promtool(work, "test", "rules", "case.test.yml")


def render_budgets(env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    """Run the budget renderer as an operator would: env in, exposition text on stdout."""
    return subprocess.run(
        [sys.executable, str(OBSERVABILITY / "billing_budgets.py")],
        capture_output=True,
        text=True,
        env={"PATH": os.environ.get("PATH", ""), **env},
        timeout=30,
        check=False,
    )


def full_env(tmp_path: Path) -> dict[str, str]:
    receiver = tmp_path / "billing_alert_webhook_url"
    receiver.write_text("placeholder-not-a-url\n", encoding="utf-8")
    return {
        "BILLING_BUDGET_LLM_PROVIDER_USD": "1000",
        "BILLING_BUDGET_OBJECT_STORE_USD": "250.5",
        "BILLING_ALERT_RECEIVER_URL_FILE": str(receiver),
    }
