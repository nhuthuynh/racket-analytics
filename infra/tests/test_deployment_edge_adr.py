"""C-29 (SEC-R1-S1-05): HSTS is an acceptance criterion of the deployment edge (ADR 0034), and
the dev/E2E proxy never sends it (HSTS on localhost would pin every developer's browser)."""

from __future__ import annotations

import re

import pytest
from conftest import REPO_ROOT

DECISIONS = REPO_ROOT / "docs" / "decisions"
CADDYFILE = REPO_ROOT / "infra" / "tls" / "Caddyfile"


def deployment_adr() -> str:
    found = sorted(DECISIONS.glob("*-deployment-edge-acceptance-criteria.md"))
    assert found, "no deployment edge ADR in docs/decisions"
    return found[-1].read_text()


@pytest.mark.unit
def test_dev_proxy_sends_no_hsts() -> None:
    directives = [ln.split("#", 1)[0] for ln in CADDYFILE.read_text().splitlines()]
    assert not any(re.search("strict-transport", d, re.I) for d in directives)


@pytest.mark.unit
def test_deployment_adr_has_an_hsts_criterion_with_at_least_one_year() -> None:
    rows = [ln for ln in deployment_adr().splitlines() if ln.startswith("| E")]
    hsts = [r for r in rows if "Strict-Transport-Security" in r]
    assert hsts, rows
    max_age = int(re.search(r"max-age=(\d+)", hsts[0]).group(1))
    assert max_age >= 31_536_000
    assert "curl" in hsts[0]  # a runnable check, not prose only


@pytest.mark.unit
@pytest.mark.parametrize("ref", ["C-29", "SEC-R1-S1-05", "X-Forwarded-For", "TRUSTED_PROXY_HOPS"])
def test_deployment_adr_closes_the_deferred_items(ref: str) -> None:
    assert ref in deployment_adr()
