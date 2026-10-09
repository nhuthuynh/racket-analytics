"""API binding of tests/features/metric_uncertainty.feature (QA-ACC-3 for ST-044/ST-046; FR-101,
ADR 0005). The tag scripts come from ``stats.receive_script`` (side A receives n, wins k, never
scores) and were checked against the reference: 8/4, 20/10, 40/22 give the stated values and
flags; 22/40 has the Wilson interval 0.398-0.693. Written red first: ``red_until`` ST-046.

Marker ``red_until`` ST-046 removed (ST-046b, TCR row 2026-10-09 in
docs/sprints/03/decisions/ST-046b.md): the stats route is built and every row passes, so the
file is in the per-PR gate and the coverage selection.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from tests.support import stats as st
from tests.support.api import ApiDriver

scenarios("metric_uncertainty.feature")


@pytest.fixture
def ctx(api: ApiDriver, monkeypatch: pytest.MonkeyPatch, tmp_path: Any) -> Iterator[dict[str, Any]]:
    st.with_statuses(monkeypatch, tmp_path)
    yield {"api": api}
    st.clear_dictionary_cache()


def _games_reference(games: list[dict[str, Any]]) -> dict[str, Any]:
    stats: dict[str, Any] = st.statslib.starter_stats(games)
    return stats


@given(parsers.parse("Ivy received serve in {n:d} rallies and won {won:d}"))
def received(ctx: dict[str, Any], n: int, won: int) -> None:
    ctx["games"] = st.receive_script(n, won)
    ctx["match"] = st.tag_games(ctx["api"], "ivy", ctx["games"], f"Receive {won}/{n}")


@given("Ivy has tagged one game")
def one_game(ctx: dict[str, Any]) -> None:
    ctx["games"] = [{"first_serving_side": "A", "tags": st.WORKED_EXAMPLE}]
    ctx["match"] = st.tagged_example(ctx["api"], "ivy", "One game")


@when("she opens her stats")
def opens(ctx: dict[str, Any]) -> None:
    ctx["stats"] = st.stats_body(ctx["api"], "ivy", ctx["match"])
    assert st.stats_diffs(_games_reference(ctx["games"]), ctx["stats"]) == []


def _an02(ctx: dict[str, Any]) -> dict[str, Any]:
    got: dict[str, Any] = ctx["stats"][st.statscontract.METRICS_KEY]["AN-02"]["A"]
    return got


@then(
    parsers.parse(
        '"Rallies won when receiving" shows {pct} with "n = {n:d}" and the low-sample flag "{flag}"'
    )
)
def shows_with_flag(ctx: dict[str, Any], pct: str, n: int, flag: str) -> None:
    got = _an02(ctx)
    assert (f"{round(got['value'] * 100)}%", got["n"]) == (pct, n)
    assert got["low_sample"] is (flag == "yes")


@then(parsers.parse("she sees the range {low} to {high} next to {pct}"))
def the_range(ctx: dict[str, Any], low: str, high: str, pct: str) -> None:
    got = _an02(ctx)
    shown = (round(got["ci_low"] * 100), round(got["ci_high"] * 100), round(got["value"] * 100))
    assert shown == (int(low.rstrip("%")), int(high.rstrip("%")), int(pct.rstrip("%")))


@then('"Unforced errors per game" is shown and flagged "low sample"')
def per_game_flagged(ctx: dict[str, Any]) -> None:
    for side in st.SIDES:
        got = ctx["stats"][st.statscontract.METRICS_KEY]["AN-04"][side]
        assert got["value"] is not None, "shown, never hidden (FR-101)"
        assert got["low_sample"] is True
