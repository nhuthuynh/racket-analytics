"""FIX-04-2c (goal scorecard G04-03 a and c): ``junit_rate --require-marker`` requires a pytest
marker by exact name, read from the JUnit testcase property ``markers`` (comma-separated).

``--require`` stays a regex over ``file|classname::name``: a marker name is not in a test id, so
``--require weakness_golden`` failed closed on a passing golden run. Negative cases first: a report
with no marker property, a near-miss name, or a marker only on an unselected case never passes.
Written red first.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest
from conftest import SCRIPTS_DIR

pytestmark = pytest.mark.unit

MEASURE = SCRIPTS_DIR / "measure"


def _load():
    spec = importlib.util.spec_from_file_location("measurelib", MEASURE / "measurelib.py")
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["measurelib"] = module
    spec.loader.exec_module(module)
    return module


m = _load()

NO_MARKERS = """<?xml version="1.0"?>
<testsuites><testsuite name="pytest">
 <testcase classname="tests.unit.coaching.test_weakness" name="test_the_fr_120_example"/>
</testsuite></testsuites>
"""
WITH_MARKERS = """<?xml version="1.0"?>
<testsuites><testsuite name="pytest">
 <testcase classname="tests.unit.coaching.test_weakness" name="test_the_fr_120_example">
  <properties><property name="markers" value="unit,weakness_golden"/></properties>
 </testcase>
 <testcase classname="tests.unit.coaching.test_training_plan" name="test_property">
  <properties><property name="markers" value="plan_property,unit"/></properties>
 </testcase>
</testsuite></testsuites>
"""


def _xml(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "junit.xml"
    path.write_text(text, encoding="utf-8")
    return path


def test_a_report_without_marker_properties_fails_closed(tmp_path: Path) -> None:
    result = m.junit_rate([_xml(tmp_path, NO_MARKERS)], ".", require_markers=["weakness_golden"])
    assert result["missing"] == ["marker:weakness_golden"]
    assert result["ok"] is False


def test_a_near_miss_marker_name_does_not_count(tmp_path: Path) -> None:
    report = _xml(tmp_path, WITH_MARKERS)
    for near in ("golden", "weakness_golden_x", "weakness_.*", "WEAKNESS_GOLDEN"):
        result = m.junit_rate([report], ".", require_markers=[near])
        assert result["missing"] == [f"marker:{near}"], near
        assert result["ok"] is False


def test_a_marker_only_on_an_unselected_case_does_not_count(tmp_path: Path) -> None:
    result = m.junit_rate(
        [_xml(tmp_path, WITH_MARKERS)], "test_weakness", require_markers=["plan_property"]
    )
    assert result["selected"] == 1
    assert result["missing"] == ["marker:plan_property"]
    assert result["ok"] is False


def test_the_regex_require_still_matches_ids_not_markers(tmp_path: Path) -> None:
    result = m.junit_rate([_xml(tmp_path, WITH_MARKERS)], ".", require=["weakness_golden"])
    assert result["missing"] == ["weakness_golden"]


def test_a_marker_on_a_selected_passing_case_is_ok(tmp_path: Path) -> None:
    result = m.junit_rate(
        [_xml(tmp_path, WITH_MARKERS)], ".", require_markers=["weakness_golden", "plan_property"]
    )
    assert result["missing"] == []
    assert result["ok"] is True


def test_the_cli_takes_require_marker_once_per_name(tmp_path: Path) -> None:
    report = _xml(tmp_path, WITH_MARKERS)

    def cli(*argv: str) -> tuple[int, dict[str, object]]:
        res = subprocess.run(
            [sys.executable, str(MEASURE / "junit_rate.py"), "--include", ".", *argv, str(report)],
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
        return res.returncode, json.loads(res.stdout or "null")

    rc, result = cli("--require-marker", "weakness_golden", "--require-marker", "nope")
    assert (rc, result["missing"]) == (1, ["marker:nope"])
    rc, result = cli("--require-marker", "weakness_golden", "--require-marker", "plan_property")
    assert (rc, result["ok"]) == (0, True)
