"""ST-171a (sprint-06 §3.4: the module joins the nightly mutation list): the player pattern
measures package ``racket.analytics.patterns`` is mutated nightly at >= 0.80 against its own unit
tests, and its unit tests sit under CI's ``DOMAIN_TEST_PATHS`` (NFR-073 budget).
"""

from __future__ import annotations

import shlex

import pytest
import yaml
from conftest import REPO_ROOT

pytestmark = pytest.mark.unit

NIGHTLY = REPO_ROOT / ".github" / "workflows" / "nightly-quality.yml"
CI = REPO_ROOT / ".github" / "workflows" / "ci.yml"
TARGET = "src/racket/analytics/patterns"
TESTS = "tests/unit/analytics/patterns"


def test_the_nightly_mutation_job_scores_the_pattern_measures_at_080() -> None:
    steps = yaml.safe_load(NIGHTLY.read_text())["jobs"]["mutation"]["steps"]
    runs = [s for s in steps if f"--target {TARGET} " in " ".join(s.get("run", "").split()) + " "]
    assert len(runs) == 1, f"expected one mutation step for {TARGET}, got {len(runs)}"
    step = runs[0]
    line = next(ln for ln in step["run"].replace("\\\n", " ").splitlines() if "mutation_score" in ln)
    argv = shlex.split(line)
    start = next(i for i, a in enumerate(argv) if a.endswith("mutation_score.py"))
    args = argv[start + 1 :]
    assert args[args.index("--tests") + 1] == TESTS
    assert float(args[args.index("--min-score") + 1]) == 0.80
    assert args[args.index("--out") + 1].startswith("../reports/mutation-")
    assert step.get("if") == "success() || failure()"  # a red step above must not skip it


def test_the_pattern_unit_tests_are_in_the_domain_suite() -> None:
    paths = yaml.safe_load(CI.read_text())["env"]["DOMAIN_TEST_PATHS"].split()
    assert any(TESTS == p or TESTS.startswith(p.rstrip("/") + "/") for p in paths), paths
