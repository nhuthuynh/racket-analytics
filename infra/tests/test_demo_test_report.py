"""Demo step 10 report (FIX-03-2d, goal metric DEMO-03; sprint-03 §12 step 10).

Step 10 shows the goal scorecard and the test report: golden matches, conservation property,
mutation, evidence crawl, open defects (0). The verifier's round-2 walk showed it by hand with
"11/12, 2 open defects" while reporting the demo as given up to step 9. The report is now
computed by ``scripts/measure/demo_test_report.py``. Negative cases first: every short or
missing input fails the step (fail closed, ADR 0014).
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest
from conftest import SCRIPTS_DIR
from demo_report_fixtures import ledger, report_dir, scorecard

pytestmark = pytest.mark.unit

SCRIPT = SCRIPTS_DIR / "measure" / "demo_test_report.py"


def _load():
    spec = importlib.util.spec_from_file_location("demo_test_report", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _report(tmp_path: Path, *, open_rows=(), met: int = 12, **kw) -> dict:
    return _load().step10_report(
        report_dir(tmp_path / "r", **kw), ledger(*open_rows), scorecard(met)
    )


def _detail(result: dict, item: str) -> dict:
    return next(i for i in result["items"] if i["item"] == item)


def test_an_open_major_alone_fails_open_defects(tmp_path: Path) -> None:
    result = _report(tmp_path, open_rows=[("PE-PR24-01", "major")])
    assert not result["ok"]
    assert _detail(result, "open defects") == {
        "item": "open defects",
        "ok": False,
        "detail": "open defects: 1 (PE-PR24-01)",
    }


def test_an_open_minor_is_not_a_defect_for_step_10(tmp_path: Path) -> None:
    assert _report(tmp_path, open_rows=[("PE-PR26-01", "minor")])["ok"]


def test_the_latest_totals_line_wins(tmp_path: Path) -> None:
    result = _report(tmp_path, met=11)
    assert _detail(result, "scorecard")["detail"] == "scorecard: 11 of 12 met"
    assert not result["ok"]


def test_a_scorecard_without_a_totals_line_is_refused(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="no Totals line"):
        _load().step10_report(report_dir(tmp_path / "r"), ledger(), "# Scorecard\n")


@pytest.mark.parametrize(
    ("kw", "item"),
    [
        ({"rules": 0.84}, "mutation rules"),
        ({"stats": 0.79}, "mutation starter stats"),
        ({"passing": 999}, "conservation property"),
        ({"failing": 1}, "conservation property"),
        ({"crawl_failed": True}, "evidence crawl"),
    ],
)
def test_each_item_below_its_target_fails(tmp_path: Path, kw: dict, item: str) -> None:
    result = _report(tmp_path, **kw)
    assert not _detail(result, item)["ok"], _detail(result, item)
    assert not result["ok"]


def test_a_failed_golden_rate_fails(tmp_path: Path) -> None:
    reports = report_dir(tmp_path / "r")
    rate = json.loads((reports / "golden-an-rate.json").read_text())
    (reports / "golden-an-rate.json").write_text(json.dumps({**rate, "failed": 1, "ok": False}))
    result = _load().step10_report(reports, ledger(), scorecard(12))
    assert not _detail(result, "golden matches")["ok"]


def test_a_crawl_with_no_e2e_03_02_case_fails(tmp_path: Path) -> None:
    reports = report_dir(tmp_path / "r")
    (reports / "e2e.xml").write_text('<testsuites><testsuite name="x"/></testsuites>')
    result = _load().step10_report(reports, ledger(), scorecard(12))
    assert _detail(result, "evidence crawl")["detail"] == "evidence crawl: E2E-03-02 0/0 passed"
    assert not result["ok"]


def test_every_item_passing_passes(tmp_path: Path) -> None:
    result = _report(tmp_path)
    assert result["ok"], result
    assert [i["item"] for i in result["items"]] == [
        "scorecard",
        "golden matches",
        "conservation property",
        "mutation rules",
        "mutation starter stats",
        "evidence crawl",
        "open defects",
    ]
