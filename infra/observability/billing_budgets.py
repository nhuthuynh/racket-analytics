"""Render the monthly billing budgets (env settings) as the Prometheus metric the billing alert
rules compare spend against (ST-073, NFR-022; SEC-4 T4-AL-1, T4-AL-2).

    BILLING_BUDGET_LLM_PROVIDER_USD=... BILLING_BUDGET_OBJECT_STORE_USD=... \\
    BILLING_ALERT_RECEIVER_URL_FILE=/run/secrets/billing_alert_receiver_url \\
    python infra/observability/billing_budgets.py > budgets.prom

Fail closed: a missing or invalid setting, or a receiver URL file that does not exist, stops the
render with exit code 2 and a message naming the variable only (never its value), so the alerts
cannot go silently off. The receiver URL is never read here; only its file's existence is checked.
Standard library only: it runs wherever the textfile collector or a sidecar runs.
"""

from __future__ import annotations

import math
import os
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

BUDGET_METRIC = "racket_billing_monthly_budget_usd"
BUDGET_SETTINGS = {
    "llm_provider": "BILLING_BUDGET_LLM_PROVIDER_USD",
    "object_store": "BILLING_BUDGET_OBJECT_STORE_USD",
}
RECEIVER_SETTING = "BILLING_ALERT_RECEIVER_URL_FILE"


class BillingConfigError(ValueError):
    """A billing alert setting is missing or invalid. The message names the variable only."""


@dataclass(frozen=True)
class MonthlyBudget:
    """A paid provider's monthly budget in USD; always a finite amount above zero."""

    provider: str
    usd: float

    def __post_init__(self) -> None:
        if not (math.isfinite(self.usd) and self.usd > 0):
            raise BillingConfigError(f"monthly budget for {self.provider} must be positive")


@dataclass(frozen=True)
class BillingAlertSettings:
    budgets: tuple[MonthlyBudget, ...]
    receiver_url_file: Path


def _required(env: Mapping[str, str], name: str) -> str:
    value = env.get(name, "").strip()
    if not value:
        raise BillingConfigError(f"{name} is not set")
    return value


def _budget(env: Mapping[str, str], provider: str, name: str) -> MonthlyBudget:
    raw = _required(env, name)
    try:
        return MonthlyBudget(provider, float(raw))
    except (ValueError, BillingConfigError):
        raise BillingConfigError(f"{name} must be a positive amount in USD") from None


def load_settings(env: Mapping[str, str]) -> BillingAlertSettings:
    budgets = tuple(_budget(env, p, name) for p, name in BUDGET_SETTINGS.items())
    receiver = Path(_required(env, RECEIVER_SETTING))
    if not receiver.is_file():
        raise BillingConfigError(f"{RECEIVER_SETTING} does not name an existing file")
    return BillingAlertSettings(budgets, receiver)


def _amount(usd: float) -> str:
    """Full precision, no exponent for whole amounts: 1000 -> '1000', 250.5 -> '250.5'."""
    return str(int(usd)) if usd.is_integer() else repr(usd)


def exposition(settings: BillingAlertSettings) -> str:
    """Prometheus text format (textfile collector or a static scrape target)."""
    lines = [
        f"# HELP {BUDGET_METRIC} Monthly budget per paid provider, from env settings (NFR-022).",
        f"# TYPE {BUDGET_METRIC} gauge",
        *(f'{BUDGET_METRIC}{{provider="{b.provider}"}} {_amount(b.usd)}' for b in settings.budgets),
    ]
    return "\n".join(lines) + "\n"


def main(env: Mapping[str, str]) -> int:
    try:
        text = exposition(load_settings(env))
    except BillingConfigError as err:
        print(f"billing alerts: refusing to start: {err}", file=sys.stderr)
        return 2
    sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main(os.environ))
