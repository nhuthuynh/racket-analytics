"""CI-PERF-GATES (Sprint 3; NFR-073 integration suite < 10 min): the 600 s budget times the
suite, not the runner's setup, and the suite fits it again by running in parallel.

Root cause (profile, ``--durations=0`` on ``origin/sprint-03`` ``efd5316``, coverage on, one
process): 728 s of test time, of which the two JSON fuzz files (IT-02-10: 169 tests, 274 s;
IT-03-12, new in Sprint 3: 51 tests, 106 s) are 52%; every test pays real HTTP + per-example
row counts. The suite grew; nothing regressed. ``pytest-xdist`` runs it on every runner core,
and every worker already gets its own database (C-32, ``tests/support/db.py``). The budget
(600 s) and the suite selection are unchanged. A collect-only warm-up (unbudgeted, as in
``python-unit``, CI run 37298471332) keeps cold bytecode compilation out of the budget.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest
import yaml
from conftest import REPO_ROOT, SCRIPTS_DIR

pytestmark = pytest.mark.unit

BUDGET = SCRIPTS_DIR / "ci" / "run_with_budget.py"
CI = REPO_ROOT / ".github" / "workflows" / "ci.yml"
BACKEND = REPO_ROOT / "backend"


def budget(*args: str, timeout: float = 30) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(BUDGET), *args],
        capture_output=True, text=True, timeout=timeout, check=False, env=dict(os.environ),
    )  # fmt: skip


def integration_steps() -> list[dict]:
    return yaml.safe_load(CI.read_text())["jobs"]["integration"]["steps"]


def _index(steps: list[dict], needle: str) -> int:
    return next((i for i, s in enumerate(steps) if needle in s.get("run", "")), -1)


# ---------------------------------------------------------------- the budget record
@pytest.mark.parametrize("args", [["1", "--json"], ["1", "--json", "x.json"]])
def test_a_json_option_without_a_command_is_a_usage_error(args: list[str]) -> None:
    assert budget(*args).returncode == 2


def test_an_over_budget_suite_is_stopped_and_recorded_as_over(tmp_path: Path) -> None:
    rec = tmp_path / "budget.json"
    res = budget("1", "--json", str(rec), "--", "sleep", "5")
    assert res.returncode == 124, res.stdout
    body = json.loads(rec.read_text())
    assert body["within_budget"] is False
    assert body["rc"] == 124
    assert body["budget_s"] == 1
    assert 1 <= body["elapsed_s"] < 5


def test_a_failing_suite_is_recorded_with_its_own_exit_code(tmp_path: Path) -> None:
    rec = tmp_path / "budget.json"
    res = budget("10", "--json", str(rec), "--", "sh", "-c", "exit 3")
    assert res.returncode == 3
    body = json.loads(rec.read_text())
    assert body["rc"] == 3
    assert body["within_budget"] is True  # in time, but the suite itself failed


def test_a_suite_within_budget_is_recorded_with_its_wall_time(tmp_path: Path) -> None:
    rec = tmp_path / "sub" / "budget.json"
    res = budget("10", "--json", str(rec), "--", "sleep", "0.2")
    assert res.returncode == 0
    body = json.loads(rec.read_text())
    assert body == {**body, "rc": 0, "within_budget": True, "budget_s": 10}
    assert 0.2 <= body["elapsed_s"] < 10
    assert body["command"] == ["sleep", "0.2"]


# ---------------------------------------------------------------- CI wiring
def test_the_integration_budget_is_still_600_s() -> None:
    assert yaml.safe_load(CI.read_text())["env"]["INTEGRATION_BUDGET_S"] == "600"


def test_the_budgeted_suite_runs_in_parallel_workers() -> None:
    run = integration_steps()[_index(integration_steps(), "$INTEGRATION_BUDGET_S")]["run"]
    assert " -n auto" in run  # pytest-xdist, one worker per runner core
    # selection unchanged: same markers, same two sandbox files left to their own jobs
    assert '-m "(unit or integration or scenario or regression) and not nightly' in run
    assert run.count("--ignore=tests/integration/test_it_00_10_worker_sandbox") == 2
    assert "--cov-report=xml:../reports/coverage-backend.xml" in run  # diff-cover input kept


def test_the_budget_wraps_only_pytest_and_records_its_time() -> None:
    steps = integration_steps()
    run = steps[_index(steps, "$INTEGRATION_BUDGET_S")]["run"]
    budgeted = run.split("run_with_budget.py", 1)[1]
    assert "uv sync" not in budgeted and "compose" not in budgeted.lower()
    assert '"$INTEGRATION_BUDGET_S" --json ../reports/integration-budget.json --' in run
    assert "--durations=25" in budgeted  # the slowest tests are listed on every run


def test_a_collect_only_warm_up_runs_before_the_budget_and_is_not_budgeted() -> None:
    steps = integration_steps()
    budgeted = _index(steps, "$INTEGRATION_BUDGET_S")
    warm = _index(steps, "--collect-only")
    assert 0 <= warm < budgeted, "integration needs an unbudgeted collect-only warm-up"
    assert "run_with_budget.py" not in steps[warm]["run"]


def test_pytest_xdist_is_a_locked_backend_dev_dependency() -> None:
    dev = tomllib.loads((BACKEND / "pyproject.toml").read_text())["dependency-groups"]["dev"]
    assert any(d.startswith("pytest-xdist") for d in dev)
    assert 'name = "pytest-xdist"' in (BACKEND / "uv.lock").read_text()
