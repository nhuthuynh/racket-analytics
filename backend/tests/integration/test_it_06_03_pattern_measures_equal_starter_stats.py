"""IT-06-03 (ST-171a; FR-171.R1; ADR 0061 Rule 1): Quick Tag pattern measures equal the starter
stats on GS-AN-1.

The golden match gm3 (two corrections, four rallies kept as "needs your decision") is tagged and
corrected through the real API into Postgres, as ST-049 does. Its sheet read back is what
``racket.analytics`` reads; the pattern measures of that sheet must equal, field for field, the
starter stats of the same sheet and the frozen GS-AN-1 v2 values. The in-memory projection of
every GS-AN-1 match is checked the same way. Negative first: the equivalence check reports a
measure that differs from its stat, naming the match, the pattern and the side.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace
from typing import Any

import pytest

from racket.analytics.patterns.measure import PatternMeasure
from racket.analytics.patterns.quick_tag import quick_tag_measures
from racket.analytics.snapshot import policy_from_dictionary
from racket.analytics.starter_stats import starter_stats
from racket.sports.pickleball.metrics import load_dictionary
from tests.regression.test_golden_an import (
    MATCHES,
    GoldenFixture,
    expected,
    product_stats,
    script,
)
from tests.support import scorebook as sb
from tests.support.api import ApiDriver

pytestmark = [pytest.mark.golden_an, pytest.mark.analytics]

GM3 = "gm3-corrections-needs-decision"
SIDES = ("A", "B")
_SHARES = {
    "AN-07:winner": "winner",
    "AN-07:unforced-error": "unforced_error",
    "AN-07:forced-error": "forced_error",
    "AN-07:fault": "fault",
}
# measure field -> starter-stat field, for the metrics with no interval (ADR 0061 Rule 3.1)
_COUNTS = {
    "AN-03": {"value": "value", "n": "turns", "low_sample": "low_sample"},
    "AN-04": {"value": "value", "n": "games", "low_sample": "low_sample"},
    "AN-06": {"value": "longest", "n": "n", "low_sample": "low_sample"},
}


def _as_stat(pattern: str, stats: Mapping[str, Any], side: str) -> dict[str, Any]:
    """The starter-stat fields a measure of ``pattern`` must equal. A frozen GS-AN-1 file keeps
    the AN-07 counts but not the shares, so only the fields ``stats`` holds are compared."""
    if pattern in _COUNTS:
        row = stats[pattern][side]
        return {field: row[key] for field, key in _COUNTS[pattern].items()} | {
            "ci_low": None, "ci_high": None,
        }  # fmt: skip
    metric, share = ("AN-07", _SHARES[pattern]) if pattern in _SHARES else (pattern, None)
    row = stats[metric][side]
    got = row.get("shares", {}).get(share, {}) if share else row
    want = {"n": row["n"], "low_sample": row["low_sample"]}
    return want | {key: got[key] for key in ("value", "ci_low", "ci_high") if key in got}


def _as_measure(m: PatternMeasure) -> dict[str, Any]:
    return {
        "value": m.value, "n": m.n, "low_sample": m.low_sample,
        "ci_low": m.interval.low if m.interval else None,
        "ci_high": m.interval.high if m.interval else None,
    }  # fmt: skip


def differences(
    match: str, measures: Mapping[str, Mapping[str, PatternMeasure]], stats: Mapping[str, Any]
) -> list[str]:
    out = []
    for pattern, by_side in measures.items():
        for side in SIDES:
            want, got = _as_stat(pattern, stats, side), _as_measure(by_side[side])
            for key in want:
                if want[key] != got[key]:
                    where = f"GS-AN-1 {match} {pattern} side {side} {key}"
                    out.append(f"{where}: starter stats {want[key]!r}, measure {got[key]!r}")
    return out


def _frozen(match: str) -> dict[str, Any]:
    """The frozen GS-AN-1 v2 values, in the starter-stats shape (fields the set compares)."""
    return dict(expected(match)["metrics"])


def _stored_sheet(api: ApiDriver) -> dict[str, Any]:
    s = script(GM3)
    (game,) = s["games"]
    match_id = sb.ready_tagged_match(api, "ivy", game["tags"], title="IT-06-03 gm3")
    ivy = api.as_user("ivy")
    for c in s["corrections"]:
        rally_id = sb.sheet_body(api, "ivy", match_id)["rows"][c["rally"] - 1]["rally_id"]
        version = api.run(sb.version_of(ivy, match_id))
        response = api.run(
            sb.command(ivy, "correct", version=version,
                       body={"field": c["field"], "value": c["value"]},
                       match_id=match_id, rally_id=rally_id)
        )  # fmt: skip
        assert response.status_code == 200, response.text
    return sb.sheet_body(api, "ivy", match_id)


def _measures_in_memory(match: str, dictionary: Any) -> Any:
    s = script(match)
    fixture = GoldenFixture()
    for game in s["games"]:
        fixture.start(game["first_serving_side"]).tag(game["tags"])
    for c in s["corrections"]:
        fixture.correct(c["rally"], c["field"], c["value"])
    return quick_tag_measures(fixture.sheet(), dictionary)


# ---------------------------------------------------------------- negative first: the check bites
def test_it_06_03_a_measure_that_differs_from_its_stat_is_reported() -> None:
    dictionary = load_dictionary()
    stats = product_stats(script(GM3))
    measures = {p: dict(by_side) for p, by_side in _measures_in_memory(GM3, dictionary).items()}
    a = measures["AN-05"]["A"]
    measures["AN-05"]["A"] = replace(a, value=(a.value or 0) + 0.1)
    found = differences(GM3, measures, stats)
    assert found == [
        f"GS-AN-1 {GM3} AN-05 side A value: starter stats {a.value!r}, "
        f"measure {(a.value or 0) + 0.1!r}"
    ]


# ---------------------------------------------------------------- IT-06-03
def test_it_06_03_stored_gm3_measures_equal_its_starter_stats_and_gs_an_1(api: ApiDriver) -> None:
    dictionary = load_dictionary()
    sheet = _stored_sheet(api)
    measures = quick_tag_measures(sheet, dictionary)
    stats = starter_stats(sheet, policy_from_dictionary(dictionary))
    assert not differences(GM3, measures, stats), "\n".join(differences(GM3, measures, stats))
    found = differences(GM3, measures, _frozen(GM3))
    assert not found, "\n".join(found)
    assert all(m.definition_version == "0.1" for by in measures.values() for m in by.values())


@pytest.mark.parametrize("match", MATCHES)
def test_it_06_03_every_gs_an_1_match_measures_equal_the_frozen_stats(match: str) -> None:
    measures = _measures_in_memory(match, load_dictionary())
    found = differences(match, measures, _frozen(match))
    assert not found, "\n".join(found)
