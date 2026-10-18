"""Reads and runs the G04-03 (a)-(c) checks of the Sprint 4 goal scorecard (FIX-04-1c).

QA-V04R1-01: the method checked the golden and property runs with ``--require weakness_golden``
and ``--require plan_property``. ``junit_rate.py`` matches each pattern against the JUnit test
id ``file|classname::name``, and a pytest marker is not part of that id, so both checks exited 1
although every selected test passed. These helpers take the commands from the scorecard as
written, so the tests guard the method itself, not a copy of it.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

from conftest import REPO_ROOT

SCORECARD = REPO_ROOT / "docs" / "sprints" / "04" / "goal-scorecard.md"
BACKEND = REPO_ROOT / "backend"
JUNIT_RATE = REPO_ROOT / "scripts" / "measure" / "junit_rate.py"
MARKERS = frozenset({"weakness_golden", "plan_property", "coaching", "scenario"})
_ID = "tests.unit.coaching.test_weakness::"
# The 7 comparisons of scorecard G04-03 (a): the FR-120 example and GS-AN-1 gm1..gm3 x 2 sides.
SCORECARD_COMPARISONS = (
    f"{_ID}test_the_fr_120_example_equals_the_catalogue",
    *(
        f"{_ID}test_the_golden_matches_equal_the_catalogue_per_side[{g}-{s}]"
        for g in ("gm1", "gm2", "gm3")
        for s in "AB"
    ),
)
# Also in the weakness_golden run (catalogue §7), not one of the 7 comparisons.
EXTRA_GOLDEN = tuple(
    f"{_ID}test_the_metric_dictionary_example_equals_the_catalogue[{s}]" for s in "AB"
)
PROPERTY_TEST = (
    "tests.unit.coaching.test_training_plan::test_property_assembled_plans_keep_every_rule"
)
# The JUnit report each marker's run writes, and the check that reads it.
REPORTS = {"weakness_golden": "weakness-golden.xml", "plan_property": "plan-property.xml"}


def method_text(text: str | None = None) -> str:
    """The scorecard §4 bullet for G04-03 (a)-(c), up to the next method bullet."""
    text = SCORECARD.read_text(encoding="utf-8") if text is None else text
    start = text.index("- **G04-03 (a)-(c):**")
    end = text.index("\n- **", start + 1)
    return text[start:end]


def required_patterns(text: str) -> list[str]:
    """Every ``--require`` value written literally in the method text."""
    out = []
    for m in re.finditer(r"--require\s+('[^']*'|\"[^\"]*\"|[^\s`]+)", text):
        out.append(m.group(1).strip("'\""))
    return out


def command_lines(text: str) -> list[str]:
    """The lines of the method's fenced bash block (comments and blank lines dropped)."""
    blocks = re.findall(r"```bash\n(.*?)```", text, flags=re.S)
    lines = [ln.strip() for b in blocks for ln in b.splitlines()]
    return [ln for ln in lines if ln and not ln.startswith("#")]


def _strip_rc(line: str) -> str:
    return re.sub(r";\s*echo rc=\$\?\s*$", "", line)


def pytest_line(text: str, marker: str) -> str:
    hits = [ln for ln in command_lines(text) if "pytest" in ln and f"-m {marker} " in ln + " "]
    assert len(hits) == 1, f"no single pytest run selecting -m {marker} in the method: {hits}"
    return _strip_rc(hits[0])


def check_line(text: str, marker: str) -> str:
    report = REPORTS[marker]
    hits = [ln for ln in command_lines(text) if "junit_rate.py" in ln and report in ln]
    assert len(hits) == 1, f"no single junit_rate.py check over {report} in the method: {hits}"
    return _strip_rc(hits[0])


def check_argv(line: str, goal: Path) -> list[str]:
    """The argv the shell gives junit_rate.py for ``line`` (loops and quotes expanded)."""
    head = "python3 scripts/measure/junit_rate.py"
    assert line.startswith(head), line
    script = 'set -f; argv() { printf "%s\\0" "$@"; }; argv' + line[len(head) :]
    res = subprocess.run(
        ["bash", "-c", script],
        cwd=REPO_ROOT,
        env={"PATH": "/usr/bin:/bin", "GOAL": str(goal)},
        capture_output=True,
        text=True,
        check=True,
    )
    return res.stdout.split("\0")[:-1]


def requires_of(argv: list[str]) -> list[str]:
    return [argv[i + 1] for i, a in enumerate(argv) if a == "--require"]


def matches(patterns: list[str], ids: tuple[str, ...]) -> dict[str, list[str]]:
    """pattern -> the ids it matches, as junit_rate.py searches ``file|classname::name``."""
    return {p: [i for i in ids if re.search(p, f"|{i}")] for p in patterns}


def run_marker(marker: str, report: Path) -> None:
    """``pytest -m <marker> --junitxml <report>`` in backend/, as the method runs it."""
    from domain_budget import run_in_backend

    cmd = ["uv", "run", "pytest", "-q", "-m", marker, "-p", "no:cacheprovider"]
    res = run_in_backend([*cmd, "--junitxml", str(report)])
    assert res.returncode == 0, res.stdout[-2000:] + res.stderr[-2000:]


def run_check(line: str, goal: Path) -> tuple[subprocess.CompletedProcess[str], dict[str, Any]]:
    argv = check_argv(line, goal)
    res = subprocess.run(
        [sys.executable, str(JUNIT_RATE), *argv],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=60,
    )
    return res, json.loads(res.stdout) if res.stdout.strip().startswith("{") else {}
