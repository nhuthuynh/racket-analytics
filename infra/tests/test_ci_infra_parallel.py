"""CI-INFRA-BUDGET (push CI on main 5bba847, run 40908731812): the infra-tests job ran its whole
suite on one core, crept up to its 10-minute timeout and was cancelled. Its pytest invocation
must use pytest-xdist, keep each test file on one worker (module-scoped service fixtures such as
the SeaweedFS stack in test_object_store_parity.py then start once per file, as before), and
keep the timeout as headroom (at most 15 minutes), never as the fix."""

from __future__ import annotations

import shlex

import pytest
import yaml
from conftest import REPO_ROOT, SCRIPTS_DIR

pytestmark = pytest.mark.unit

CI = REPO_ROOT / ".github" / "workflows" / "ci.yml"


def infra_job() -> dict:
    return yaml.safe_load(CI.read_text())["jobs"]["infra-tests"]


def pytest_argv() -> list[str]:
    runs = [s["run"] for s in infra_job()["steps"] if "pytest" in s.get("run", "")]
    assert len(runs) == 1, runs
    return shlex.split(runs[0])


def option(argv: list[str], flag: str) -> str | None:
    for i, arg in enumerate(argv):
        if arg == flag and i + 1 < len(argv):
            return argv[i + 1]
        if arg.startswith(flag + "="):
            return arg.split("=", 1)[1]
    return None


# ---------------------------------------------------------------- negative cases first
def test_infra_pytest_does_not_run_serially() -> None:
    assert option(pytest_argv(), "-n") == "auto", pytest_argv()


def test_infra_pytest_keeps_each_test_file_on_one_worker() -> None:
    assert option(pytest_argv(), "--dist") == "loadfile", pytest_argv()


def test_timeout_is_headroom_not_the_fix() -> None:
    assert 10 <= infra_job()["timeout-minutes"] <= 15


def test_weed_download_is_taken_under_a_lock() -> None:
    # Parallel workers share <repo>/.local/bin; the download must be serialised (the behaviour
    # is proven in test_ci_infra_budget_scenarios.py).
    text = (SCRIPTS_DIR / "dev-objectstore.sh").read_text()
    assert "flock" in text


# ---------------------------------------------------------------- positive case
def test_parallel_run_keeps_the_marker_expression() -> None:
    assert option(pytest_argv(), "-m") == "unit or integration"
    assert pytest_argv()[:3] == ["uv", "run", "pytest"]
