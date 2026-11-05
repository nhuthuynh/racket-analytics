"""Helpers for the ST-075c SLO burn-rate tests (NFR-041.3-.4, NFR-042.3-.4; ADR 0057 §2).

A "burn" is a synthetic series, one sample a minute: ``BASE`` valid events a minute, of which
``percent`` % fail, held for ``duration``. The API series also carries 500 responses a minute
with status 429, which must be in neither part of the ratio (NFR-041.1); the upload series also
carries ``created`` and ``rejected`` events, which the alert ratio ignores (ADR 0057 §2, terminal
outcomes only). ``promtool`` runs from the image pinned in ``billing_alert_fixtures``.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

import yaml
from billing_alert_fixtures import ALERTS_DIR, promtool

SLO_RULES = ALERTS_DIR / "slo.yml"
SLO_RULE_TEST = ALERTS_DIR / "slo.test.yml"
RUNBOOK = "docs/ops/slo.md"
BASE = 1000  # valid events a minute
RATE_LIMITED_PER_MIN = 500
HTTP_COUNT = "http_server_request_duration_seconds_count"
UPLOADS = "racket_upload_sessions_total"


@dataclass(frozen=True)
class Alert:
    """One row of the ADR 0057 §2 alert table."""

    name: str
    sli: str  # "API responses" or "uploads" (the feature's words)
    slo: str
    window: str
    severity: str
    error_ratio: float  # burn rate x error budget
    for_: str


ALERTS = {
    a.name: a
    for a in (
        Alert("ApiAvailabilityFastBurn", "API responses", "api_availability", "fast", "page",
              0.072, "2m"),
        Alert("ApiAvailabilitySlowBurn", "API responses", "api_availability", "slow", "ticket",
              0.0075, "15m"),
        Alert("UploadCompletionFastBurn", "uploads", "upload_completion", "fast", "page",
              0.144, "2m"),
        Alert("UploadCompletionSlowBurn", "uploads", "upload_completion", "slow", "ticket",
              0.015, "15m"),
    )
}  # fmt: skip


def minutes(duration: str) -> int:
    """'10m' -> 10, '6h' -> 360."""
    unit = {"m": 1, "h": 60}[duration[-1]]
    return int(duration[:-1]) * unit


def burn_series(sli: str, percent: float, duration: str) -> list[dict[str, str]]:
    """promtool input series for ``percent`` % failures among ``BASE`` valid events a minute."""
    bad = round(BASE * percent / 100)
    assert abs(bad - BASE * percent / 100) < 1e-9, "percent must be a whole share of BASE"
    n = minutes(duration) + 5
    if sli == "API responses":
        labels = 'job="racket-api",http_request_method="GET",http_response_status_code'
        rows = {
            f'{HTTP_COUNT}{{{labels}="{code}"}}': per_min
            for code, per_min in ((200, BASE - bad), (500, bad), (429, RATE_LIMITED_PER_MIN))
        }
    elif sli == "uploads":
        rows = {
            f'{UPLOADS}{{job="racket-api",event="created"}}': BASE + 100,
            f'{UPLOADS}{{job="racket-api",event="rejected",reason="too_large"}}': 100,
            f'{UPLOADS}{{job="racket-api",event="completed"}}': BASE - bad,
            # Expirations come from both emitters (ADR 0057 §2): the API and the purge.
            f'{UPLOADS}{{job="racket-api",event="expired"}}': bad - bad // 2,
            f'{UPLOADS}{{job="racket-purge",event="expired"}}': bad // 2,
        }
    else:
        raise ValueError(f"unknown SLI {sli!r}")
    return [{"series": s, "values": f"0+{per_min}x{n}"} for s, per_min in rows.items()]


def load_rules(path: Path = SLO_RULES) -> list[dict]:
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    return [rule for group in doc["groups"] for rule in group["rules"]]


def rule_by_alert(name: str, path: Path = SLO_RULES) -> dict:
    matches = [r for r in load_rules(path) if r.get("alert") == name]
    assert len(matches) == 1, f"{name}: {len(matches)} rules"
    return matches[0]


def expected_alert(name: str) -> dict:
    """What promtool must see: the rule's labels and annotations (the SLIs are summed away)."""
    rule = rule_by_alert(name)
    return {"exp_labels": dict(rule["labels"]), "exp_annotations": dict(rule["annotations"])}


def burn_case(alert: str, percent: float, duration: str, firing: bool) -> dict:
    """One promtool test case: the burn, then the alert state at the end of ``duration``."""
    a = ALERTS[alert]
    verdict = "fires" if firing else "does not fire"
    return {
        "name": f"{alert}: {percent:g} % of {a.sli} fail for {duration} -> {verdict}",
        "interval": "1m",
        "input_series": burn_series(a.sli, percent, duration),
        "alert_rule_test": [
            {
                "eval_time": duration,
                "alertname": alert,
                "exp_alerts": [expected_alert(alert)] if firing else [],
            }
        ],
    }


def rule_test_doc(*cases: dict) -> dict:
    return {"rule_files": ["slo.yml"], "evaluation_interval": "30s", "tests": list(cases)}


def run_rule_test(
    tmp_path: Path, doc: dict | None = None, rules_text: str | None = None
) -> subprocess.CompletedProcess[str]:
    """``promtool test rules`` on a copy: ``doc`` (default the committed test) and the rules
    (default the committed slo.yml, or ``rules_text`` for a planted change)."""
    work = tmp_path / "promtool"
    work.mkdir(exist_ok=True)
    if rules_text is None:
        shutil.copy(SLO_RULES, work / "slo.yml")
    else:
        (work / "slo.yml").write_text(rules_text, encoding="utf-8")
    if doc is None:
        shutil.copy(SLO_RULE_TEST, work / "case.test.yml")
    else:
        (work / "case.test.yml").write_text(yaml.safe_dump(doc, sort_keys=False), "utf-8")
    # The image runs promtool as `nobody`; pytest's tmp dirs are 0700 for the test's own user.
    os.chmod(work, 0o755)  # noqa: S103 - throwaway test dir, read-only mount
    for f in work.iterdir():
        os.chmod(f, 0o644)
    return promtool(work, "test", "rules", "case.test.yml")
