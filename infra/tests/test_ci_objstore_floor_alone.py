"""CI-OBJSTORE-SLOW follow-up (PR #56, run 38020043986 job 114118873082): the store's write
floor is checked alone, as its two dedicated steps do, and never beside the parallel suites.

In that run the floor passed alone before the suites (``2 passed``) and the store's 15 s
samples stayed at 52-118 MB/s, yet the same test, collected again into the ``-n auto`` suite
step, measured one write at 0.571 MB/s while three other xdist workers were loading the same
store. A throughput floor measured under the suites' own load does not measure the store."""

from __future__ import annotations

import re
import shlex
from fnmatch import fnmatch
from typing import Any

import pytest
import yaml
from conftest import REPO_ROOT

pytestmark = pytest.mark.unit

CI = REPO_ROOT / ".github" / "workflows" / "ci.yml"
FLOOR_TEST = "tests/integration/harness/test_ci_objstore_throughput.py"


def _integration_steps() -> list[dict[str, Any]]:
    return yaml.safe_load(CI.read_text())["jobs"]["integration"]["steps"]


def _parallel_suite_steps() -> list[dict[str, Any]]:
    return [s for s in _integration_steps() if "-n auto" in s.get("run", "")]


def _ignored(run: str) -> list[str]:
    """The paths and globs a pytest command line leaves out (``--ignore``/``--ignore-glob``)."""
    words = shlex.split(re.sub(r"\\\n", " ", run))
    return [w.split("=", 1)[1] for w in words if re.match(r"--ignore(-glob)?=", w)]


def _left_out(run: str, path: str) -> bool:
    return any(fnmatch(path, pattern) for pattern in _ignored(run))


def test_the_parallel_backend_suites_do_not_collect_the_floor_test() -> None:
    steps = _parallel_suite_steps()
    assert steps, "the integration job runs the backend suites with pytest-xdist"
    for step in steps:
        assert _left_out(step["run"], FLOOR_TEST), step.get("name")


def test_the_parallel_backend_suites_still_collect_the_other_harness_tests() -> None:
    harness = REPO_ROOT / "backend" / "tests" / "integration" / "harness"
    others = [
        f"tests/integration/harness/{p.name}"
        for p in sorted(harness.glob("test_*.py"))
        if f"tests/integration/harness/{p.name}" != FLOOR_TEST
    ]
    assert others
    for step in _parallel_suite_steps():
        assert not [p for p in others if _left_out(step["run"], p)], step.get("name")


def test_the_floor_still_runs_alone_before_and_after_the_suites() -> None:
    alone = [s for s in _integration_steps() if FLOOR_TEST in s.get("run", "")]
    assert len(alone) == 2, [s.get("name") for s in alone]
    for step in alone:
        assert "-n " not in step["run"], step.get("name")
        assert not _left_out(step["run"], FLOOR_TEST), step.get("name")
