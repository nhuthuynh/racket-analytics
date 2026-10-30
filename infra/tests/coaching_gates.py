"""Helpers for the SRE-VERIFY04R3-03 tests (coaching gates of sprint-04 §8; retro C5).

Reads the coaching mutation commands of ``nightly-quality.yml`` and the publish step's
``--mutation-scope`` arguments exactly as the workflow declares them.
"""

from __future__ import annotations

import re
import shlex
from typing import Any

import yaml
from conftest import REPO_ROOT

NIGHTLY = REPO_ROOT / ".github" / "workflows" / "nightly-quality.yml"
COACHING_TARGETS = {
    "coaching/plan": "src/racket/coaching/plan",
    "coaching/weakness": "src/racket/coaching/weakness",
}
COACHING_TESTS = "tests/unit/coaching"
MIN_SCORE = "0.80"


def nightly() -> dict[str, Any]:
    return yaml.safe_load(NIGHTLY.read_text())


def mutation_job() -> dict[str, Any]:
    return nightly()["jobs"]["mutation"]


def coaching_step(target: str) -> dict[str, Any]:
    """The one mutation step that scores ``target`` (``src/racket/coaching/...``)."""
    steps = [s for s in mutation_job()["steps"] if f"--target {target} " in s.get("run", "") + " "]
    assert len(steps) == 1, f"expected one mutation step for {target}, got {len(steps)}"
    return steps[0]


def score_argv(target: str) -> list[str]:
    """``mutation_score.py`` arguments of the step for ``target`` (after the script name)."""
    run = coaching_step(target)["run"].replace("\\\n", " ")
    lines = [ln for ln in run.splitlines() if "mutation_score.py" in ln]
    assert len(lines) == 1, lines
    argv = shlex.split(lines[0])
    start = next(i for i, a in enumerate(argv) if a.endswith("mutation_score.py"))
    return argv[start + 1 :]


def option(argv: list[str], name: str) -> str | None:
    for i, a in enumerate(argv):
        if a == name and i + 1 < len(argv):
            return argv[i + 1]
    return None


def publish_run() -> str:
    return "\n".join(s.get("run", "") for s in nightly()["jobs"]["publish"]["steps"])


def publish_scopes() -> dict[str, str]:
    """``--mutation-scope SCOPE=PATH`` arguments of the publish step: scope -> report path."""
    pairs = re.findall(r"--mutation-scope\s+(\S+)=(\S+)", publish_run())
    return dict(pairs)


def scoring_options(argv: list[str]) -> list[str]:
    """``score_argv`` without the options that only a mutmut run uses (and without ``--out``),
    so the same target and minimum can score a given stats file (``--from-stats``)."""
    out: list[str] = []
    skip = False
    for a in argv:
        if skip:
            skip = False
            continue
        if a in {"--project", "--tests", "--ignore", "--out"}:
            skip = True
            continue
        out.append(a)
    return out
