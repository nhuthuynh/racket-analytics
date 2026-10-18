"""IT-04-16 (ST-060; NFR-005 a; QD-QG-S7; G04-04): ``racket-plan-eval`` over the real drill
library (``content/drills``) and the real eval set (``backend/tests/evals/plan_cases``).

Boundary: the case files and the drill files on disk, read by the CLI; each case is played
through the real scorebook, stats, weakness ranking, citations and rules-only assembly, three
times, and graded by code. Fail closed, negative cases first:

* a case whose expectation the real plan does not meet fails, is named with its grader, rc 1;
* fewer cases than ``--min-cases`` (default 30) is a failure, rc 1; a missing directory, rc 2;
* the eval set: >= 30 cases, every case passes all 3 runs with byte-identical output, rc 0,
  and the ``--json`` report says so per case;
* the console script ``racket-plan-eval`` is declared in ``backend/pyproject.toml``.
"""

from __future__ import annotations

import json
import tomllib
from pathlib import Path
from typing import Any

import pytest

from tests.support.contract import Seam
from tests.support.paths import BACKEND, REPO

pytestmark = [pytest.mark.integration, pytest.mark.coaching]

CLI = Seam("racket.coaching.evals.cli:main", "ST-060", "main(argv: list[str]) -> int")
CASES = BACKEND / "tests" / "evals" / "plan_cases"
LIBRARY = REPO / "content" / "drills"


def run(capsys: pytest.CaptureFixture[str], *argv: object) -> tuple[int, str]:
    capsys.readouterr()
    rc = CLI.load()([str(a) for a in argv])
    out, err = capsys.readouterr()
    return int(rc), out + err


def _copy_case(tmp_path: Path, case_id: str, **changes: Any) -> Path:
    cases = tmp_path / "cases"
    cases.mkdir(exist_ok=True)
    doc = json.loads((CASES / f"{case_id}.json").read_text(encoding="utf-8")) | changes
    (cases / f"{case_id}.json").write_text(json.dumps(doc), encoding="utf-8")
    return cases


def test_it_04_16_a_case_the_real_plan_does_not_meet_fails_and_is_named(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    cases = _copy_case(tmp_path, "pe-13", expect="no_plan_fits")  # pe-13 does get a plan
    rc, out = run(capsys, "--runs", 3, "--cases", cases, "--library", LIBRARY, "--min-cases", 1)
    assert rc == 1, out
    fail = [line for line in out.splitlines() if line.startswith("FAIL pe-13")]
    assert fail, out
    assert "OUTCOME" in fail[0]


def test_it_04_16_fewer_cases_than_the_minimum_fail_closed(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    cases = _copy_case(tmp_path, "pe-01")
    rc, out = run(capsys, "--runs", 3, "--cases", cases, "--library", LIBRARY)
    assert rc == 1, out
    assert "1 case" in out, out
    assert "30" in out, out


def test_it_04_16_a_missing_case_directory_is_rc_2(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    rc, out = run(capsys, "--cases", tmp_path / "nowhere", "--library", LIBRARY)
    assert rc == 2, out


def test_it_04_16_the_eval_set_passes_at_pass3_over_the_real_library(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    report_path = tmp_path / "plan-eval.json"
    rc, out = run(capsys, "--runs", 3, "--json", report_path)
    assert rc == 0, out
    passed = [line for line in out.splitlines() if line.startswith("PASS ")]
    assert len(passed) >= 30, out
    assert not [line for line in out.splitlines() if line.startswith("FAIL ")], out
    assert out.splitlines()[-1].endswith("(100%)"), out
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["runs"] == 3
    assert Path(report["library"]) == LIBRARY
    assert len(report["cases"]) == len(list(CASES.glob("*.json"))) >= 30
    for case in report["cases"]:
        assert case["passed"], case
        assert case["failures"] == [], case
        assert len(case["digests"]) == 3, case
        assert len(set(case["digests"])) == 1, case
    expects = {json.loads(p.read_text())["expect"] for p in CASES.glob("*.json")}
    assert expects == {"plan", "no_plan_fits"}


def test_it_04_16_the_eval_set_spans_the_preference_and_sample_grid() -> None:
    """Read from each case's preferences and tag scripts, not from its description."""
    docs = [json.loads(p.read_text()) for p in sorted(CASES.glob("*.json"))]
    prefs = [d["preferences"] for d in docs]
    assert {p["players_available"] for p in prefs} == {1, 2, 4}
    minutes = {p["minutes_per_session"] for p in prefs}
    assert min(minutes) == 20
    assert max(minutes) == 90
    assert {"ball_machine" in p["equipment"] for p in prefs} == {True, False}
    assert {"wall" in p["equipment"] for p in prefs} == {True, False}
    assert {p["level"] for p in prefs} == {"beginner", "intermediate", "advanced"}
    tags = [sum(len(g["tags"]) for m in d["matches"] for g in m["games"]) for d in docs]
    assert min(tags) < 30  # one short match
    assert max(tags) >= 150  # ... to three long ones


def test_it_04_16_the_console_script_is_declared() -> None:
    project = tomllib.loads((BACKEND / "pyproject.toml").read_text(encoding="utf-8"))
    assert project["project"]["scripts"]["racket-plan-eval"] == "racket.coaching.evals.cli:main"
