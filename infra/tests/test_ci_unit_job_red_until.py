"""QA-FUZZ-3: the CI unit job selects the same rows as scripts/test-unit.sh (ST-003, ST-012).

`red_until` rows are QA's red-first tests: listed by the red-until report, never gated
(backend/pyproject.toml marker). A unit row marked `red_until` must not fail the unit gate.
"""

from __future__ import annotations

import re

import pytest
import yaml
from conftest import REPO_ROOT

pytestmark = pytest.mark.unit


def _unit_job_pytest_commands() -> list[str]:
    wf = yaml.safe_load((REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text())
    runs = [step.get("run", "") for step in wf["jobs"]["python-unit"]["steps"]]
    return [r for r in runs if "pytest" in r and "--collect-only" not in r]


def test_a_unit_job_pytest_run_never_gates_red_until_rows() -> None:
    commands = _unit_job_pytest_commands()
    assert commands, "python-unit runs no pytest command"
    for cmd in commands:
        m = re.search(r"pytest\b.*?-m\s+\"([^\"]+)\"", cmd, re.S)
        assert m, f"pytest without a quoted -m selection: {cmd.strip()}"
        assert "not red_until" in m.group(1), f"red_until rows gated: {cmd.strip()}"


def test_the_local_unit_entry_point_also_deselects_red_until() -> None:
    script = (REPO_ROOT / "scripts" / "test-unit.sh").read_text()
    assert '-m "unit and not slow and not red_until"' in script
