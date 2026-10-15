"""Demo step 10 report (FIX-03-2d, goal metric DEMO-03; sprint-03 §12 step 10), computed by
``scripts/measure/demo_test_report.py``. Negative cases first: every short, odd or missing
input fails the step (fail closed, ADR 0014)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from conftest import SCRIPTS_DIR
from demo_report_fixtures import ledger, report_dir, scorecard

pytestmark = pytest.mark.unit

sys.path.insert(0, str(SCRIPTS_DIR / "measure"))
import demo_test_report as dtr  # noqa: E402


def _report(tmp_path: Path, *, open_rows=(), met: int = 12, **kw) -> dict:
    return dtr.step10_report(report_dir(tmp_path / "r", **kw), ledger(*open_rows), scorecard(met))


def _detail(result: dict, item: str) -> dict:
    return next(i for i in result["items"] if i["item"] == item)


def test_an_open_major_alone_fails_open_defects(tmp_path: Path) -> None:
    result = _report(tmp_path, open_rows=[("PE-PR24-01", "major")])
    assert not result["ok"]
    assert _detail(result, "open defects")["detail"] == "open defects: 1 (PE-PR24-01)"


def test_an_open_minor_is_not_a_defect_for_step_10(tmp_path: Path) -> None:
    assert _report(tmp_path, open_rows=[("PE-PR26-01", "minor")])["ok"]


def test_the_latest_totals_line_wins(tmp_path: Path) -> None:
    result = _report(tmp_path, met=11)
    assert _detail(result, "scorecard")["detail"] == "scorecard: 11 of 12 met"
    assert not result["ok"]


def test_a_scorecard_without_a_totals_line_is_refused(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="no Totals line"):
        dtr.step10_report(report_dir(tmp_path / "r"), ledger(), "# Scorecard\n")


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


@pytest.mark.parametrize(
    ("name", "text", "item"),
    [
        (
            "golden-an-rate.json",
            '{"selected": 2, "passed": 1, "failed": 1, "rate": 0.5}',
            "golden matches",
        ),
        ("e2e.xml", '<testsuites><testsuite name="x"/></testsuites>', "evidence crawl"),
        ("conservation-property.txt", "1 passed", "conservation property"),
        ("mutation-rules.json", "[0.9]", "mutation rules"),
    ],
)
def test_a_failed_empty_or_odd_report_fails(
    tmp_path: Path, name: str, text: str, item: str
) -> None:
    reports = report_dir(tmp_path / "r")
    (reports / name).write_text(text)
    result = dtr.step10_report(reports, ledger(), scorecard(12))
    assert not _detail(result, item)["ok"], _detail(result, item)


def test_every_item_passing_passes(tmp_path: Path) -> None:
    result = _report(tmp_path)
    assert result["ok"], result
    items = "scorecard,golden matches,conservation property,mutation rules"
    items += ",mutation starter stats,evidence crawl,open defects"
    assert [i["item"] for i in result["items"]] == items.split(",")
