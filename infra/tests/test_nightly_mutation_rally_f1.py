"""ST-084b (sprint-05 §8: every new domain module joins the nightly mutation list in its own PR):
the rally-segmentation F1 matcher is mutated nightly at >= 0.80 by its own unit tests, and a red
step above it does not skip it.
"""

from __future__ import annotations

import shlex

import pytest
import yaml
from conftest import REPO_ROOT

pytestmark = pytest.mark.unit

WORKFLOW = REPO_ROOT / ".github" / "workflows" / "nightly-quality.yml"
TARGET = "src/racket/dataset/rally_f1.py"
TESTS = "tests/unit/dataset/test_rally_f1.py"


def _step() -> dict[str, str]:
    steps = yaml.safe_load(WORKFLOW.read_text())["jobs"]["mutation"]["steps"]
    runs = [s for s in steps if f"--target {TARGET} " in " ".join(s.get("run", "").split()) + " "]
    assert len(runs) == 1, f"expected one mutation step for {TARGET}, got {len(runs)}"
    return runs[0]


def test_the_nightly_mutation_job_scores_the_rally_f1_matcher_at_080() -> None:
    step = _step()
    line = next(
        ln for ln in step["run"].replace("\\\n", " ").splitlines() if "mutation_score" in ln
    )
    argv = shlex.split(line)
    start = next(i for i, a in enumerate(argv) if a.endswith("mutation_score.py"))
    args = argv[start + 1 :]
    assert args[args.index("--tests") + 1] == TESTS
    assert float(args[args.index("--min-score") + 1]) == 0.80
    assert args[args.index("--out") + 1] == "../reports/mutation-dataset-rally-f1.json"
    assert step.get("if") == "success() || failure()"


def test_the_rally_f1_step_starts_from_an_empty_mutants_dir() -> None:
    assert "rm -rf mutants" in _step()["run"]
