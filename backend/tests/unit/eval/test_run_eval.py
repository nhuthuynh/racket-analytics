"""Unit tests for ``scripts/eval/run_eval.py`` (ST-176a; NFR-006.7; ADR 0060 Rules 1-3).

Pure functions only: the row table, the per-row verdict, the run verdict and rc, the
CPU-seconds ratio and the report rendering. No FFmpeg, no files. Written red first.
"""

from __future__ import annotations

import importlib.util
import sys
from types import ModuleType
from typing import Any

import pytest

from tests.support.paths import REPO


def _load() -> ModuleType:
    path = REPO / "scripts" / "eval" / "run_eval.py"
    spec = importlib.util.spec_from_file_location("run_eval", path)
    assert spec is not None, path
    assert spec.loader is not None, path
    module = importlib.util.module_from_spec(spec)
    sys.modules["run_eval"] = module
    spec.loader.exec_module(module)
    return module


ev = _load()


def row(metric: str) -> Any:
    return next(r for r in ev.ROWS if r.id == metric)


# ------------------------------------------------------------------ the ADR 0060 Rule 3 table


def test_the_table_has_the_eleven_adr_0060_rows_in_order() -> None:
    assert [r.id for r in ev.ROWS] == [f"M{i}" for i in range(1, 12)]


@pytest.mark.parametrize(
    ("metric", "higher", "target", "tolerance", "min_units", "label"),
    [
        ("M1", True, 80.0, 1.0, 2000, "capability"),
        ("M3", True, 70.0, 5.0, 20, "capability"),
        ("M4", False, 15.0, 1.0, 20, "capability"),
        ("M7", False, 33.0, 3.0, 500, "capability"),
        ("M8", False, 100.0, 10.0, 500, "capability"),
        ("M9", True, 70.0, 2.0, 300, "capability"),
        ("M10", False, 60.0, 3.0, 300, "capability"),
        ("M11", True, 90.0, 1.0, 100, "regression"),
    ],
)
def test_rows_carry_the_adr_values(
    metric: str, higher: bool, target: float, tolerance: float, min_units: int, label: str
) -> None:
    r = row(metric)
    assert (r.higher_is_better, r.target, r.tolerance, r.min_units, r.label) == (
        higher, target, tolerance, min_units, label,
    )  # fmt: skip


def test_only_rally_f1_is_regression_labelled() -> None:
    assert [r.id for r in ev.ROWS if r.label == "regression"] == ["M11"]


# ------------------------------------------------------------------ Rule 1 per row


def test_a_drop_beyond_tolerance_fails_a_higher_is_better_row() -> None:
    result = ev.judge(row("M1"), ev.Measure(78.9, 2000), baseline=80.0)
    assert (result.verdict, result.delta) == ("fail", pytest.approx(-1.1))


def test_a_drop_of_exactly_the_tolerance_passes() -> None:
    assert ev.judge(row("M1"), ev.Measure(79.0, 2000), baseline=80.0).verdict == "pass"
    assert ev.judge(row("M7"), ev.Measure(33.0, 500), baseline=30.0).verdict == "pass"
    assert ev.judge(row("M5"), ev.Measure(84.9, 500), baseline=85.9).verdict == "pass"


def test_a_rise_beyond_tolerance_fails_a_lower_is_better_row() -> None:
    result = ev.judge(row("M7"), ev.Measure(33.5, 500), baseline=30.0)
    assert (result.verdict, result.delta) == ("fail", pytest.approx(3.5))


def test_an_improvement_passes_in_both_directions() -> None:
    assert ev.judge(row("M2"), ev.Measure(70.0, 3), baseline=60.0).verdict == "pass"
    assert ev.judge(row("M10"), ev.Measure(40.0, 300), baseline=58.0).verdict == "pass"


def test_no_baseline_is_not_applicable() -> None:
    result = ev.judge(row("M1"), ev.Measure(50.0, 2000), baseline=None)
    assert (result.verdict, result.delta) == ("n/a: no baseline", None)


def test_fewer_units_than_the_minimum_is_low_sample_not_pass_or_fail() -> None:
    assert ev.judge(row("M1"), ev.Measure(10.0, 1999), baseline=80.0).verdict == "low sample"


def test_a_metric_the_candidate_did_not_measure_is_reported_as_such() -> None:
    assert ev.judge(row("M4"), None, baseline=14.0).verdict == "not measured"


def test_target_met_is_reported_in_the_metric_direction() -> None:
    assert ev.judge(row("M4"), ev.Measure(15.0, 20), baseline=None).target_met is True
    assert ev.judge(row("M4"), ev.Measure(15.1, 20), baseline=None).target_met is False
    assert ev.judge(row("M1"), ev.Measure(80.0, 2000), baseline=None).target_met is True


# ------------------------------------------------------------------ Rule 2 (M11 target gate)


def test_m11_below_target_fails_once_a_baseline_has_met_the_target() -> None:
    result = ev.judge(row("M11"), ev.Measure(89.8, 100), baseline=90.5)
    assert result.verdict == "fail"


def test_m11_below_target_passes_while_no_baseline_has_met_it() -> None:
    assert ev.judge(row("M11"), ev.Measure(75.0, 100), baseline=74.0).verdict == "pass"


def test_a_capability_row_below_target_is_never_gated_by_the_target() -> None:
    assert ev.judge(row("M1"), ev.Measure(79.5, 2000), baseline=82.0).verdict == "fail"
    assert ev.judge(row("M1"), ev.Measure(79.5, 2000), baseline=80.0).verdict == "pass"


# ------------------------------------------------------------------ run verdict and inputs

GOLD = {"id": "g", "version": 1}
CONFIG = {"seed": 0, "ball_px_threshold": 10}


def metrics(**values: float) -> dict[str, Any]:
    return {k: {"value": v, "units": 10_000} for k, v in values.items()}


def test_any_one_failing_row_fails_the_run_with_rc_1() -> None:
    results = ev.evaluate(
        {"gold_set": GOLD, "config": CONFIG, "metrics": metrics(M1=70.0, M2=70.0)},
        {
            "gold_set": GOLD,
            "config": CONFIG,
            "metrics": {"M1": {"value": 80.0}, "M2": {"value": 60.0}},
        },
    )
    assert ev.exit_code(results) == 1


def test_all_rows_passing_or_not_applicable_is_rc_0() -> None:
    results = ev.evaluate({"gold_set": GOLD, "metrics": metrics(M1=80.0)}, None)
    assert [r.verdict for r in results][:2] == ["n/a: no baseline", "not measured"]
    assert ev.exit_code(results) == 0


def test_a_baseline_on_another_gold_set_version_is_an_input_error() -> None:
    with pytest.raises(ev.InputError, match="gold-set version"):
        ev.evaluate(
            {"gold_set": GOLD, "metrics": metrics(M1=80.0)},
            {"gold_set": {"id": "g", "version": 2}, "metrics": {}},
        )


def test_an_unknown_metric_id_is_an_input_error() -> None:
    with pytest.raises(ev.InputError, match="M12"):
        ev.evaluate({"gold_set": GOLD, "metrics": metrics(M12=1.0)}, None)


# ------------------------------------------------------------------ cost and report


def test_cpu_seconds_per_match_minute() -> None:
    assert ev.per_match_minute(cpu_seconds=3.0, durations_s=[60.0, 30.0]) == pytest.approx(2.0)


def test_cpu_seconds_per_match_minute_needs_some_footage() -> None:
    with pytest.raises(ev.InputError, match="no footage"):
        ev.per_match_minute(cpu_seconds=1.0, durations_s=[])


def test_the_report_fills_every_template_field() -> None:
    template = "# {{title}}\n{{provenance}}\n{{rows}}\n{{verdict}}\n"
    candidate = {"gold_set": GOLD, "pipeline_version": "p1", "dry_run": True,
                 "weights": {"licence": "MIT"}, "config": CONFIG,
                 "metrics": metrics(M1=79.5)}  # fmt: skip
    baseline = {"gold_set": GOLD, "config": CONFIG, "metrics": {"M1": {"value": 80.0}}}
    results = ev.evaluate(candidate, baseline)
    cost = ev.Cost(cpu_seconds=1.0, durations_s=[60.0], stage="decode")

    report = ev.render(template, candidate, results, cost, weights_sha256=None, date="2026-11-13")

    assert "{{" not in report
    assert "| M1 | Ball F1" in report
    assert "| 79.50 | 10000 | 80.00 | -0.50 | pass |" in report
    assert "| Gold set | g v1 |" in report
    assert "DRY RUN" in report
    assert "rc 0" in report


# ------------------------------------------------------------------ review round 1 (PR #261)
# F1 (principal-engineer): Rule 1 baseline = same gold-set version AND same config.


def _pair(cand_config: Any, base_config: Any) -> tuple[dict[str, Any], dict[str, Any]]:
    candidate: dict[str, Any] = {"gold_set": GOLD, "metrics": metrics(M1=80.0)}
    baseline: dict[str, Any] = {"gold_set": GOLD, "metrics": {"M1": {"value": 80.0}}}
    if cand_config is not None:
        candidate["config"] = cand_config
    if base_config is not None:
        baseline["config"] = base_config
    return candidate, baseline


def test_a_baseline_run_with_another_config_is_an_input_error() -> None:
    candidate, baseline = _pair(
        {"seed": 0, "ball_px_threshold": 20, "rally_match_window_s": 5.0},
        {"seed": 0, "ball_px_threshold": 10, "rally_match_window_s": 1.0},
    )
    with pytest.raises(ev.InputError, match="config differs"):
        ev.evaluate(candidate, baseline)


@pytest.mark.parametrize(
    ("cand_config", "base_config"),
    [(CONFIG, None), (None, CONFIG), (None, None), (CONFIG, "seed=0"), ([1], [1])],
)
def test_a_missing_or_malformed_config_with_a_baseline_is_an_input_error(
    cand_config: Any, base_config: Any
) -> None:
    candidate, baseline = _pair(cand_config, base_config)
    with pytest.raises(ev.InputError, match="config"):
        ev.evaluate(candidate, baseline)


def test_the_same_config_on_both_sides_is_judged() -> None:
    candidate, baseline = _pair(dict(CONFIG), dict(reversed(list(CONFIG.items()))))
    assert ev.evaluate(candidate, baseline)[0].verdict == "pass"


def test_the_report_prints_the_baseline_config() -> None:
    template = "{{provenance}}"
    candidate, baseline = _pair(CONFIG, CONFIG)
    results = ev.evaluate(candidate, baseline)
    cost = ev.Cost(cpu_seconds=1.0, durations_s=[60.0], stage="decode")

    report = ev.render(template, candidate, results, cost, None, "2026-11-13", baseline=baseline)

    assert '| Baseline config | `{"ball_px_threshold": 10, "seed": 0}` |' in report


def test_the_report_says_when_there_is_no_baseline_config() -> None:
    candidate, _ = _pair(CONFIG, None)
    results = ev.evaluate(candidate, None)
    cost = ev.Cost(cpu_seconds=1.0, durations_s=[60.0], stage="decode")

    report = ev.render("{{provenance}}", candidate, results, cost, None, "2026-11-13")

    assert "| Baseline config | — (no baseline) |" in report


# F2 (principal-engineer): a missing or malformed gold_set fails closed on either input.


@pytest.mark.parametrize(
    ("cand_gold", "base_gold"),
    [
        (None, None),
        (None, GOLD),
        (GOLD, None),
        ({"id": "g"}, {"id": "g"}),
        ({"version": 1}, {"version": 1}),
        ("g v1", "g v1"),
        ({"id": "", "version": 1}, {"id": "", "version": 1}),
    ],
)
def test_a_missing_or_malformed_gold_set_is_an_input_error(cand_gold: Any, base_gold: Any) -> None:
    candidate, baseline = _pair(CONFIG, CONFIG)
    candidate.pop("gold_set")
    baseline.pop("gold_set")
    if cand_gold is not None:
        candidate["gold_set"] = cand_gold
    if base_gold is not None:
        baseline["gold_set"] = base_gold
    with pytest.raises(ev.InputError, match="gold_set"):
        ev.evaluate(candidate, baseline)


def test_a_candidate_without_a_gold_set_is_an_input_error_even_with_no_baseline() -> None:
    with pytest.raises(ev.InputError, match="gold_set"):
        ev.evaluate({"metrics": metrics(M1=80.0)}, None)


# F1 (senior-qa-engineer): NFR-006.7 weights hash; a declared sha256 without a path is kept.


def test_a_declared_sha256_without_a_path_is_recorded() -> None:
    declared = "ab" * 32
    assert ev.weights_hash({"sha256": declared, "licence": "Apache-2.0"}) == declared


def test_a_malformed_declared_sha256_is_an_input_error() -> None:
    with pytest.raises(ev.InputError, match="sha256"):
        ev.weights_hash({"sha256": "not-a-hash", "licence": "Apache-2.0"})


def test_the_report_marks_a_declared_hash_as_not_verified() -> None:
    declared = "ab" * 32
    candidate, _ = _pair(CONFIG, None)
    candidate["weights"] = {"sha256": declared, "licence": "Apache-2.0"}
    results = ev.evaluate(candidate, None)
    cost = ev.Cost(cpu_seconds=1.0, durations_s=[60.0], stage="decode")

    report = ev.render("{{provenance}}", candidate, results, cost, declared, "2026-11-13")

    assert f"| Weights sha256 | `{declared}` (declared; no file to verify) |" in report
