"""Unit tests of the scorecard G04-03 (a)/(c) checks, read from the scorecard (FIX-04-1c)."""

from __future__ import annotations

import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
from goal_g04_03 import (
    EXTRA_GOLDEN,
    MARKERS,
    PROPERTY_TEST,
    SCORECARD_COMPARISONS,
    check_argv,
    check_line,
    matches,
    method_text,
    pytest_line,
    required_patterns,
    requires_of,
)

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "measure"))
from measurelib import junit_rate

pytestmark = pytest.mark.unit

GOLDEN_IDS = (*SCORECARD_COMPARISONS, *EXTRA_GOLDEN)


def _junit(path: Path, ids: tuple[str, ...]) -> Path:
    suite = ET.Element("testsuite")
    for tid in ids:
        classname, name = tid.split("::")
        ET.SubElement(suite, "testcase", classname=classname, name=name)
    ET.ElementTree(suite).write(path)
    return path


# ---------------------------------------------------------------- negative cases first
def test_a_marker_name_never_matches_a_junit_test_id(tmp_path: Path) -> None:
    """Root cause of QA-V04R1-01: the id is file|classname::name, without markers."""
    result = junit_rate([_junit(tmp_path / "g.xml", GOLDEN_IDS)], ".", ["weakness_golden"])
    assert (result["passed"], result["missing"], result["ok"]) == (9, ["weakness_golden"], False)


def test_no_g04_03_check_requires_a_bare_marker_name() -> None:
    bare = [p for p in required_patterns(method_text()) if p in MARKERS]
    assert bare == [], f"a marker is not part of a JUnit id, so these never match: {bare}"


def test_a_check_missing_one_comparison_is_caught(tmp_path: Path) -> None:
    line = check_line(method_text(), "weakness_golden")
    ids = tuple(i for i in GOLDEN_IDS if not i.endswith("[gm2-B]"))
    result = junit_rate(
        [_junit(tmp_path / "g.xml", ids)], ".", requires_of(check_argv(line, tmp_path))
    )
    assert result["ok"] is False
    assert len(result["missing"]) == 1


# ---------------------------------------------------------------- the golden check (a)
def test_the_golden_check_requires_each_scorecard_comparison_by_its_own_pattern(
    tmp_path: Path,
) -> None:
    line = check_line(method_text(), "weakness_golden")
    hits = matches(requires_of(check_argv(line, tmp_path)), GOLDEN_IDS)
    assert all(len(ids) == 1 for ids in hits.values()), hits
    assert sorted(i for ids in hits.values() for i in ids) == sorted(SCORECARD_COMPARISONS)


def test_the_golden_check_reads_the_golden_run_report_and_fails_closed(tmp_path: Path) -> None:
    text = method_text()
    assert '--junitxml "$GOAL/weakness-golden.xml"' in pytest_line(text, "weakness_golden")
    argv = check_argv(check_line(text, "weakness_golden"), tmp_path)
    assert argv[-1] == str(tmp_path / "weakness-golden.xml")
    assert "--allow-skips" not in argv
    assert argv[argv.index("--include") + 1] == "."


# ---------------------------------------------------------------- the property check (c)
def test_the_property_check_requires_the_property_test_by_name(tmp_path: Path) -> None:
    text = method_text()
    assert '--junitxml "$GOAL/plan-property.xml"' in pytest_line(text, "plan_property")
    argv = check_argv(check_line(text, "plan_property"), tmp_path)
    hits = matches(requires_of(argv), (PROPERTY_TEST, *GOLDEN_IDS))
    assert hits, "no --require in the property check"
    assert all(ids == [PROPERTY_TEST] for ids in hits.values()), hits
    assert "--allow-skips" not in argv
    assert argv[-1] == str(tmp_path / "plan-property.xml")
