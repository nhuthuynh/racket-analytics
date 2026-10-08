"""G02-12 method guard (senior-qa-engineer, goal round 1).

NFR-073 "rules + domain unit suite < 10 s" is a CI-timing gate. CI defines the domain suite as
``DOMAIN_TEST_PATHS`` (W-01, decision-log 2026-10-06). The Sprint 2 goal-scorecard measured the
whole ``tests/unit`` (1,415 tests, the backend unit suite with its own 60 s budget) against the
10 s domain budget, so the scorecard and the merge gate measured different suites (G02-12
rc=124). These tests keep the scorecard's domain run on the same paths and budget as CI.

SRE-S3-02 (TCR 2026-10-07, accepted): the Sprint 2 record is closed, so its domain run is checked
against the list CI had when G02-12 was measured (``SPRINT_2_DOMAIN_TEST_PATHS``); the live check
against CI's ``DOMAIN_TEST_PATHS`` moves to the Sprint 3 scorecard (G03-11 d), which must read the
paths from ``ci.yml`` and requires ``tests/unit/analytics`` (ST-054).
"""

from __future__ import annotations

import re

import pytest
import yaml
from conftest import REPO_ROOT

pytestmark = pytest.mark.unit

CI = REPO_ROOT / ".github" / "workflows" / "ci.yml"
SCORECARD = REPO_ROOT / "docs" / "sprints" / "02" / "goal-scorecard.md"
SCORECARD_03 = REPO_ROOT / "docs" / "sprints" / "03" / "goal-scorecard.md"
# CI's DOMAIN_TEST_PATHS when G02-12 was measured (ci.yml before c7a6443, ST-054).
SPRINT_2_DOMAIN_TEST_PATHS = (
    "tests/unit/sports tests/unit/matches tests/unit/players tests/unit/video_ingest"
)


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
    """Sprint 2 record: the paths CI had then (frozen; the live check is the G03-11 one)."""
    paths = SPRINT_2_DOMAIN_TEST_PATHS
    assert f"-m unit {paths};" in domain_command() or domain_command().endswith(f"-m unit {paths}")


def test_the_whole_unit_suite_keeps_its_own_budget() -> None:
    budget = ci_env()["BACKEND_UNIT_BUDGET_S"]
    assert any(
        f"run_with_budget.py {budget} " in c and re.search(r"pytest -q -m unit;", c)
        for c in g02_12_commands()
    )


# ---------------------------------------------------------------- Sprint 3 (G03-11 d)
def g03_11_block(text: str) -> str:
    section = text.split("### G03-11:", 1)[1]
    return section.split("```bash", 1)[1].split("```", 1)[0]


def g03_11_domain_problems(block: str, ci_paths: str) -> list[str]:
    """Why G03-11 (d) would not measure CI's domain suite; empty when it does."""
    problems = []
    if "['env']['DOMAIN_TEST_PATHS']" not in block or "ci.yml" not in block:
        problems.append("DOMAIN is not read from ci.yml env.DOMAIN_TEST_PATHS")
    if "tests/unit/analytics" not in ci_paths.split():
        problems.append("CI's DOMAIN_TEST_PATHS lacks tests/unit/analytics")
    budget = ci_env()["DOMAIN_UNIT_BUDGET_S"]
    runs = [ln for ln in block.splitlines() if re.search(rf"run_with_budget\.py {budget} ", ln)]
    if len(runs) != 1 or not re.search(r"-m unit \$DOMAIN(;|\s|$)", runs[0]):
        problems.append(f"the {budget} s run does not measure $DOMAIN: {runs}")
    return problems


def test_g03_11_a_hardcoded_domain_list_without_analytics_is_caught() -> None:
    sprint2_style = (
        "python3 ../scripts/ci/run_with_budget.py 10 -- env -u APP_ENV uv run pytest -q -m unit "
        f"{SPRINT_2_DOMAIN_TEST_PATHS}; echo rc=$?\n"
    )
    problems = g03_11_domain_problems(sprint2_style, SPRINT_2_DOMAIN_TEST_PATHS)
    assert len(problems) == 3, problems


def test_g03_11_the_domain_run_uses_ci_domain_paths_with_analytics() -> None:
    block = g03_11_block(SCORECARD_03.read_text())
    assert g03_11_domain_problems(block, ci_env()["DOMAIN_TEST_PATHS"]) == []
