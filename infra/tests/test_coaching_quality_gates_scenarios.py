"""Binds tests/features/coaching_quality_gates.feature (SRE-VERIFY04R3-03; retro C5).

Reads the real nightly-quality.yml and ci.yml, runs the real scoring and publishing scripts with
the workflow's own arguments, and the real backend unit tests with the CI steps' selection.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
from coaching_gates import (
    COACHING_TARGETS,
    COACHING_TESTS,
    score_argv,
    scoring_options,
)
from coaching_gates import (
    publish_scopes as workflow_scopes,
)
from conftest import SCRIPTS_DIR
from domain_budget import ci_env, command, run_in_backend
from pytest_bdd import given, parsers, scenarios, then, when

pytestmark = pytest.mark.integration
scenarios("coaching_quality_gates.feature")

CI_SCRIPTS = SCRIPTS_DIR / "ci"
PROPERTY_TESTS = (
    "tests/unit/coaching/test_training_plan.py::test_property_assembled_plans_keep_every_rule",
    "tests/unit/coaching/test_weakness.py::test_every_lost_rally_is_attributed_once_per_game_and_phase",
)


@pytest.fixture
def world() -> dict[str, Any]:
    return {}


def _stats(score: float) -> dict[str, int]:
    killed = round(score * 100)
    return {"killed": killed, "survived": 100 - killed, "total": 100, "no_tests": 0,
            "skipped": 0, "timeout": 0}  # fmt: skip


# ---------------------------------------------------------------- nightly mutation
RESULTS = "mutation results of {plan:f} for coaching/plan and {weak:f} for coaching/weakness"


@given(parsers.parse(RESULTS))
def mutation_results(world: dict[str, Any], tmp_path: Path, plan: float, weak: float) -> None:
    world["stats"] = {}
    for scope, score in (("coaching/plan", plan), ("coaching/weakness", weak)):
        path = tmp_path / f"stats-{scope.replace('/', '-')}.json"
        path.write_text(json.dumps(_stats(score)))
        world["stats"][scope] = path


@when("each coaching mutation command from nightly-quality.yml scores its result")
def score_each(world: dict[str, Any], tmp_path: Path) -> None:
    reports = tmp_path / "reports"
    reports.mkdir()
    world["reports"], world["rc"] = reports, {}
    scopes = workflow_scopes()
    for scope, target in COACHING_TARGETS.items():
        out = reports.parent / scopes[scope]  # the path the publish step reads
        argv = [*scoring_options(score_argv(target)), "--from-stats",
                str(world["stats"][scope]), "--out", str(out)]  # fmt: skip
        res = subprocess.run([sys.executable, str(CI_SCRIPTS / "mutation_score.py"), *argv],
                             capture_output=True, text=True, timeout=60, check=False)  # fmt: skip
        world["rc"][scope] = res.returncode


@when("the publish step's command writes the results into a sprint status file")
def publish(world: dict[str, Any], tmp_path: Path) -> None:
    status = tmp_path / "status.json"
    status.write_text(json.dumps({"sprint": "04"}))
    args = [a for scope, path in workflow_scopes().items()
            for a in ("--mutation-scope", f"{scope}={tmp_path / path}")]  # fmt: skip
    res = subprocess.run([sys.executable, str(CI_SCRIPTS / "nightly_status.py"), "--status",
                          str(status), "--run-url", "u", "--sha", "abc", "--mutation-job",
                          "failure", *args], capture_output=True, text=True, timeout=60,
                         check=False)  # fmt: skip
    assert res.returncode == 0, res.stderr
    world["nightly"] = json.loads(status.read_text())["nightly"]


@then("the coaching/plan command failed and the coaching/weakness command passed")
def plan_failed_weakness_passed(world: dict[str, Any]) -> None:
    assert world["rc"] == {"coaching/plan": 1, "coaching/weakness": 0}


@then("the status file shows coaching/plan failed and coaching/weakness passed against 0.80")
def status_shows_both(world: dict[str, Any]) -> None:
    scopes = world["nightly"]["mutation_scopes"]
    plan, weak = scopes["coaching/plan"], scopes["coaching/weakness"]
    assert (plan["scope"], plan["score"], plan["min_score"], plan["gate"]) == (
        "coaching/plan", 0.79, 0.8, "failed")  # fmt: skip
    assert (weak["scope"], weak["score"], weak["min_score"], weak["gate"]) == (
        "coaching/weakness", 0.81, 0.8, "passed")  # fmt: skip
    assert plan["job"] == weak["job"] == "failure"


# ---------------------------------------------------------------- domain step
@given("CI's DOMAIN_TEST_PATHS")
def domain_paths(world: dict[str, Any]) -> None:
    world["paths"] = ci_env()["DOMAIN_TEST_PATHS"].split()


@when("the budgeted domain step's command from ci.yml collects its tests")
def collect(world: dict[str, Any]) -> None:
    res = run_in_backend([*command(), "--collect-only", "-n", "0", "-p", "no:cacheprovider"])
    assert res.returncode == 0, res.stdout[-3000:] + res.stderr[-2000:]
    world["collected"] = [ln for ln in res.stdout.splitlines() if "::" in ln]


@then("the coaching unit tests are among them")
def coaching_collected(world: dict[str, Any]) -> None:
    coaching = [t for t in world["collected"] if t.startswith(f"{COACHING_TESTS}/")]
    assert len(coaching) > 400, (len(coaching), world["paths"])
    assert any(t.startswith(PROPERTY_TESTS[0]) for t in coaching)


# ---------------------------------------------------------------- property step
@given("the property step from ci.yml on the Hypothesis ci profile")
def property_step(world: dict[str, Any]) -> None:
    assert COACHING_TESTS in ci_env()["DOMAIN_TEST_PATHS"].split()


@when("it runs the coaching property tests")
def run_properties(world: dict[str, Any]) -> None:
    cmd = ["env", "HYPOTHESIS_PROFILE=ci", "uv", "run", "--no-sync", "pytest", "-q", "-m",
           "unit and not red_until", "-p", "no:cacheprovider", "--hypothesis-show-statistics",
           *PROPERTY_TESTS]  # fmt: skip
    world["property"] = run_in_backend(cmd)


@then("each of them passed at least 1,000 examples")
def at_least_1000(world: dict[str, Any]) -> None:
    res = world["property"]
    assert res.returncode == 0, res.stdout[-3000:]
    passing = [int(n) for n in re.findall(r"(\d+) passing\b", res.stdout)]
    # Statistics per test and phase; the generate phase carries the drawn examples.
    per_test = res.stdout.split("Hypothesis Statistics")[-1]
    for name in (t.rsplit("::", 1)[1] for t in PROPERTY_TESTS):
        assert name in per_test, per_test[-2000:]
    assert len([n for n in passing if n >= 1000]) == len(PROPERTY_TESTS), passing
