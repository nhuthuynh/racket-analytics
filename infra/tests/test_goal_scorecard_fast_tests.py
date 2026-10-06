"""G02-12 method guard (senior-qa-engineer, goal round 1).

NFR-073 "rules + domain unit suite < 10 s" is a CI-timing gate. CI defines the domain suite as
``DOMAIN_TEST_PATHS`` (W-01, decision-log 2026-10-06). The Sprint 2 goal-scorecard measured the
whole ``tests/unit`` (1,415 tests, the backend unit suite with its own 60 s budget) against the
10 s domain budget, so the scorecard and the merge gate measured different suites (G02-12
rc=124). These tests keep the scorecard's domain run on the same paths and budget as CI.
"""

from __future__ import annotations

import re

import pytest
import yaml
from conftest import REPO_ROOT

pytestmark = pytest.mark.unit

CI = REPO_ROOT / ".github" / "workflows" / "ci.yml"
SCORECARD = REPO_ROOT / "docs" / "sprints" / "02" / "goal-scorecard.md"


def ci_env() -> dict:
    return yaml.safe_load(CI.read_text())["env"]


def g02_12_commands() -> list[str]:
    text = SCORECARD.read_text()
    section = text.split("### G02-12: fast tests", 1)[1]
    block = section.split("```bash", 1)[1].split("```", 1)[0]
    return [ln.strip() for ln in block.splitlines() if "run_with_budget.py" in ln]


def domain_command() -> str:
    budget = ci_env()["DOMAIN_UNIT_BUDGET_S"]
    hits = [c for c in g02_12_commands() if re.search(rf"run_with_budget\.py {budget} ", c)]
    assert len(hits) == 1, hits
    return hits[0]


# ---------------------------------------------------------------- negative cases first
def test_the_domain_budget_never_measures_the_whole_unit_suite() -> None:
    cmd = domain_command()
    assert not re.search(r"-m unit tests/unit(\s|;|$)", cmd), cmd


def test_the_domain_run_uses_the_ci_domain_paths_in_order() -> None:
    paths = ci_env()["DOMAIN_TEST_PATHS"]
    assert f"-m unit {paths};" in domain_command() or domain_command().endswith(
        f"-m unit {paths}"
    )


def test_the_whole_unit_suite_keeps_its_own_budget() -> None:
    budget = ci_env()["BACKEND_UNIT_BUDGET_S"]
    assert any(
        f"run_with_budget.py {budget} " in c and re.search(r"pytest -q -m unit;", c)
        for c in g02_12_commands()
    )
