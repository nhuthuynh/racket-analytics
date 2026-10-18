"""ST-060 graders (NFR-005a; QD-QG-S7): code graders over one eval run's output.

Every test breaks exactly one thing in a valid hand-built output (``eval_helpers``) and expects
the finding to name its grader: ``DRILL`` (id@version exists and is reviewed), ``CITE`` (the
metric, value and n the stats show), ``QD-PL-01..03``, ``WEAKNESS`` (the plan trains the ranked
top 3), ``OUTCOME`` (plan or the expected refusal). Negative cases first; the valid output last.
"""

from __future__ import annotations

from typing import Any

import pytest

from tests.unit.coaching.eval_helpers import (
    DOCS,
    SERVE,
    WARM,
    first_drill,
    grade,
    valid_output,
)

pytestmark = pytest.mark.unit


def _only(findings: list[str], grader: str) -> None:
    assert findings, f"no finding, expected {grader}"
    assert all(f.startswith(f"{grader}:") for f in findings), findings


# ------------------------------------------------------------------ DRILL
def test_a_drill_missing_from_the_library_is_named() -> None:
    out = valid_output()
    first_drill(out)["drill"] = "t.serve@9"
    findings = grade(out)
    assert any(f.startswith("DRILL:") and "t.serve@9" in f for f in findings), findings


@pytest.mark.parametrize("status", ["draft", "in-review"])
def test_a_drill_that_is_not_reviewed_is_named(status: str, monkeypatch: Any) -> None:
    monkeypatch.setitem(DOCS, SERVE, DOCS[SERVE] | {"review_status": status})
    findings = grade(valid_output())
    assert any(f.startswith("DRILL:") and status in f for f in findings), findings


def test_a_deprecated_drill_is_named(monkeypatch: Any) -> None:
    monkeypatch.setitem(DOCS, SERVE, DOCS[SERVE] | {"deprecated_by": "t.serve@2"})
    findings = grade(valid_output())
    assert any(f.startswith("DRILL:") and "deprecated" in f for f in findings), findings


# ------------------------------------------------------------------ CITE
def test_an_assignment_without_a_citation_is_named() -> None:
    out = valid_output()
    del first_drill(out)["citation"]
    _only(grade(out), "CITE")


@pytest.mark.parametrize(
    ("field", "value"),
    [("n", 9), ("k", 3), ("value", 0.3), ("metric_version", "0.2")],
)
def test_a_citation_the_stats_do_not_show_is_named(field: str, value: Any) -> None:
    out = valid_output()
    first_drill(out)["citation"][field] = value
    findings = grade(out)
    _only(findings, "CITE")
    assert any(field in f for f in findings), findings


def test_a_cited_rally_outside_the_metric_evidence_is_named() -> None:
    out = valid_output()
    first_drill(out)["citation"]["rally_ids"].append(["m1", "r9"])
    findings = grade(out)
    _only(findings, "CITE")
    assert any("r9" in f for f in findings), findings


def test_a_metric_the_stats_do_not_show_is_named() -> None:
    out = valid_output()
    del out["stats"][0]["metrics"]["AN-05"]
    _only(grade(out), "CITE")


def test_a_why_without_the_value_and_n_is_named() -> None:
    out = valid_output()
    first_drill(out)["why"] = "Serve faults"
    _only(grade(out), "CITE")


def test_a_weakness_drill_citing_another_target_is_named() -> None:
    out = valid_output()
    first_drill(out)["citation"] = first_drill(out, position=1)["citation"]
    findings = grade(out)
    assert any(f.startswith("CITE:") and "AN-05" in f for f in findings), findings


def test_an_ending_share_cites_the_count_of_its_ending() -> None:
    """AN-07:fault: k is the fault count of the ending counts, n all ended rallies."""
    out = valid_output()
    share = {"metric_id": "AN-07", "target": "AN-07:fault", "metric_version": "0.1",
             "value": 0.4444, "n": 9, "k": 4, "low_sample": True,
             "rally_ids": [["m1", "r1"]], "evidence": [["m1", "A", 3]]}  # fmt: skip
    out["plan"]["weaknesses"][0]["target"] = "AN-07:fault"
    out["ranking"]["weaknesses"][0]["target"] = "AN-07:fault"
    DOCS_FAULT = {**DOCS, SERVE: DOCS[SERVE] | {"target_metrics": ["AN-07"],
                                                  "skills": ["AN-07", "share:fault"]}}  # fmt: skip
    for s in out["plan"]["sessions"]:
        s["assignments"][1]["citation"] = dict(share)
        s["assignments"][1]["why"] = "Rally endings (faults): 44% of 9 rallies"
    from tests.unit.coaching.eval_helpers import GRADE, case

    assert GRADE.load()(out, case(), DOCS_FAULT) == []
    first_drill(out)["citation"]["k"] = 1  # the forced-error count, not the fault count
    _only(GRADE.load()(out, case(), DOCS_FAULT), "CITE")


# ------------------------------------------------------------------ QD-PL-01..03
def test_a_session_over_its_budget_breaks_qd_pl_01() -> None:
    out = valid_output()
    findings = grade(out, minutes_per_session=20)  # budget 20: 10 + 12 = 22
    assert any(f.startswith("QD-PL-01:") for f in findings), findings


def test_a_week_over_the_weekly_minutes_breaks_qd_pl_01() -> None:
    findings = grade(valid_output(), weekly_minutes=21)
    assert any(f.startswith("QD-PL-01:") for f in findings), findings


def test_minutes_outside_the_drill_duration_break_qd_pl_01() -> None:
    out = valid_output()
    first_drill(out)["minutes"] = 9  # t.serve lasts 10-15
    findings = grade(out)
    assert any(f.startswith("QD-PL-01:") and SERVE in f for f in findings), findings


def test_a_missing_session_breaks_qd_pl_01() -> None:
    out = valid_output()
    out["plan"]["sessions"].pop()
    findings = grade(out)
    assert any(f.startswith("QD-PL-01:") for f in findings), findings


@pytest.mark.parametrize(
    ("change", "prefs"),
    [
        ({"needs": ["wall", "ball_machine"]}, {}),
        ({"players": 2}, {}),
        ({"level_min": "advanced"}, {}),
    ],
)
def test_a_drill_that_does_not_fit_the_setup_breaks_qd_pl_02(
    change: dict[str, Any], prefs: dict[str, Any], monkeypatch: Any
) -> None:
    monkeypatch.setitem(DOCS, SERVE, DOCS[SERVE] | change)
    findings = grade(valid_output(), **prefs)
    _only(findings, "QD-PL-02")


def test_a_session_not_starting_with_a_warm_up_breaks_qd_pl_03() -> None:
    out = valid_output()
    for s in out["plan"]["sessions"]:
        s["assignments"] = s["assignments"][1:]
        s["assignments"][0]["position"] = 1
    findings = grade(out)
    assert any(f.startswith("QD-PL-03:") and "warm-up" in f for f in findings), findings


def test_a_warm_up_of_more_than_10_minutes_breaks_qd_pl_03(monkeypatch: Any) -> None:
    monkeypatch.setitem(DOCS, WARM, DOCS[WARM] | {"duration_max": 12})
    out = valid_output()
    first_drill(out, position=1)["minutes"] = 11
    findings = grade(out)
    _only(findings, "QD-PL-03")


def test_a_drill_over_40_percent_of_the_session_breaks_qd_pl_03() -> None:
    out = valid_output()
    first_drill(out)["minutes"] = 13  # cap: 40% of 30 = 12
    _only(grade(out), "QD-PL-03")


def test_a_second_warm_up_breaks_qd_pl_03() -> None:
    out = valid_output()
    first_drill(out)["drill"] = WARM
    first_drill(out)["minutes"] = 8
    findings = grade(out)
    assert any(f.startswith("QD-PL-03:") and "second warm-up" in f for f in findings), findings


# ------------------------------------------------------------------ WEAKNESS, OUTCOME
def test_a_plan_not_training_the_ranked_weaknesses_is_named() -> None:
    out = valid_output()
    out["ranking"]["weaknesses"].reverse()
    assert any(f.startswith("WEAKNESS:") for f in grade(out))


def test_a_refusal_where_a_plan_was_expected_is_named() -> None:
    out = valid_output() | {"plan": None, "refusal": "no_plan_fits"}
    assert grade(out) == ["OUTCOME: expected a plan, got the refusal no_plan_fits"]


def test_a_plan_where_a_refusal_was_expected_is_named() -> None:
    findings = grade(valid_output(), expect="no_plan_fits")
    assert findings == ["OUTCOME: expected the refusal no_plan_fits, got a plan"]


def test_the_expected_refusal_passes() -> None:
    out = valid_output() | {"plan": None, "refusal": "no_plan_fits"}
    assert grade(out, expect="no_plan_fits") == []


def test_a_valid_plan_passes_every_grader() -> None:
    assert grade(valid_output()) == []
