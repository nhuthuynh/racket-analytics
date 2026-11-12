"""Binds tests/features/ci_domain_budget_gc.feature (CI-DOMAIN-BUDGET, sprint 5; NFR-073).

Runs the budgeted domain step's command from ci.yml with a probe plugin. The probe is loaded
with `-p` into the controller and every worker (xdist passes the option on); at each worker's
first test it records whether the collector is on, how many objects are frozen, and whether
the dict of the test's own module (made during collection) is one of the frozen objects
(gc.get_objects() lists the collector's generations only, never frozen objects).
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pytest
from domain_budget import ci_env, command, run_in_backend
from pytest_bdd import given, scenarios, then, when

pytestmark = pytest.mark.integration
scenarios("ci_domain_budget_gc.feature")

PROBE = """
import gc, json, os
_seen = []
def pytest_runtest_call(item):
    if _seen:
        return
    _seen.append(1)
    module_dict = id(item.module.__dict__)
    tracked = {id(o) for o in gc.get_objects()}
    worker = os.environ.get("PYTEST_XDIST_WORKER", "main")
    record = {"worker": worker, "enabled": gc.isenabled(), "frozen": gc.get_freeze_count(),
              "module_frozen": module_dict not in tracked}
    with open(os.path.join(os.environ["GC_PROBE_DIR"], worker + ".json"), "w") as f:
        json.dump(record, f)
"""


@pytest.fixture
def world() -> dict[str, Any]:
    return {}


@given("the backend unit suite on CI's DOMAIN_TEST_PATHS")
def the_suite() -> None:
    assert "tests/unit/coaching" in ci_env()["DOMAIN_TEST_PATHS"].split()


@when("the budgeted domain step's command from ci.yml runs with a garbage-collector probe")
def run_with_gc_probe(world: dict[str, Any], tmp_path: Path) -> None:
    (tmp_path / "gc_probe.py").write_text(PROBE)
    out = tmp_path / "records"
    out.mkdir()
    # `-v` after the step's `-q` restores the default verbosity, where xdist names its workers.
    extra = ["-v", "-p", "no:cacheprovider", "-p", "gc_probe"]
    env = {"PYTHONPATH": str(tmp_path), "GC_PROBE_DIR": str(out)}
    world["probe"] = (run_in_backend([*command(), *extra], extra_env=env), out)


@then("every worker ran its tests with the collector on and its collected test modules frozen")
def workers_frozen(world: dict[str, Any]) -> None:
    res, out = world["probe"]
    m = re.search(r"\bcreated: (\d+)/\d+ workers", res.stdout)
    assert m, res.stdout[-2000:]
    records = [json.loads(p.read_text()) for p in sorted(out.glob("gw*.json"))]
    assert len(records) == int(m.group(1)) > 1, (m.group(0), records)
    for rec in records:
        assert rec["enabled"], rec  # objects the tests create are still collected
        assert rec["module_frozen"], rec  # frozen after collection, not only at start-up
        assert rec["frozen"] > 50_000, rec  # start-up + collection (~220,000 locally)


@then("no test failed or errored in that run")
def probe_run_green(world: dict[str, Any]) -> None:
    res, _ = world["probe"]
    assert res.returncode == 0, res.stdout[-3000:]
    plain = re.sub(r"\x1b\[[0-9;]*m", "", res.stdout)  # CI sets FORCE_COLOR=1
    assert re.search(r"\b1[0-9]{3} passed\b", plain), plain[-500:]
