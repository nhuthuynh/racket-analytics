"""API binding of tests/features/starter_stats.feature (QA-ACC-3 for ST-044/ST-046; FR-100,
NFR-004). Numbers are the coach's hand count of the worked example (metric-dictionary §2) and
are also compared with the independent reference ``statslib``. Every dictionary entry is
published for these scenarios; which entries are shown is metric_dictionary.feature's concern.
Written red first: ``red_until`` ST-046 (the stats route).

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

scenarios("starter_stats.feature")

NAMES = {"Rallies won on serve": "AN-01", "Rallies won when receiving": "AN-02"}


@pytest.fixture
def ctx(api: ApiDriver, monkeypatch: pytest.MonkeyPatch, tmp_path: Any) -> Iterator[dict[str, Any]]:
    st.with_statuses(monkeypatch, tmp_path)
    yield {"api": api}
    st.clear_dictionary_cache()


def _metrics(ctx: dict[str, Any]) -> dict[str, Any]:
    metrics: dict[str, Any] = ctx["stats"][st.statscontract.METRICS_KEY]
    return metrics


def _pct(value: float | None) -> str:
    assert value is not None
    return f"{round(value * 100)}%"


@given("Ivy has tagged the worked-example game of the metric dictionary")
def worked_example(ctx: dict[str, Any]) -> None:
    ctx["match"] = st.tagged_example(ctx["api"], "ivy", "Saturday doubles")
    ctx["tags"] = st.WORKED_EXAMPLE


@when("she opens her stats")
def opens_stats(ctx: dict[str, Any]) -> None:
    ctx["stats"] = st.stats_body(ctx["api"], "ivy", ctx["match"])
    assert st.stats_diffs(st.reference(ctx["tags"]), ctx["stats"]) == []


@then(parsers.parse('"{name}" shows {pct} for her side with "n = {n:d}"'))
def shows_for_her_side(ctx: dict[str, Any], name: str, pct: str, n: int) -> None:
    got = _metrics(ctx)[NAMES[name]]["A"]
    assert (_pct(got["value"]), got["n"]) == (pct, n)


@then("no stat counts rally 8, which was a replay")
def replay_not_counted(ctx: dict[str, Any]) -> None:
    an07 = _metrics(ctx)["AN-07"]
    # 14 rallies, rally 8 a replay: 13 rallies ended by one side or the other
    assert an07["A"]["n"] + an07["B"]["n"] == len(ctx["tags"]) - 1
    an01, an02 = _metrics(ctx)["AN-01"], _metrics(ctx)["AN-02"]
    assert an01["A"]["n"] + an01["B"]["n"] == len(ctx["tags"]) - 1
    assert an02["A"]["n"] + an02["B"]["n"] == len(ctx["tags"]) - 1


@then("her side shows 2 unforced errors in the game")
def two_unforced_errors(ctx: dict[str, Any]) -> None:
    assert _metrics(ctx)["AN-04"]["A"]["count"] == 2


@then('the other side shows 1 with "player not tagged in 1 rally"')
def other_side_one_untagged(ctx: dict[str, Any]) -> None:
    got = _metrics(ctx)["AN-04"]["B"]
    assert (got["count"], got["player_not_tagged"]) == (1, 1)


@given(parsers.parse('her stats show "{name}" as {pct} with "n = {n:d}"'))
def stats_before(ctx: dict[str, Any], name: str, pct: str, n: int) -> None:
    opens_stats(ctx)
    got = _metrics(ctx)[NAMES[name]]["A"]
    assert (_pct(got["value"]), got["n"]) == (pct, n)


@when("she changes rally 3 to won by her side")
def change_rally_3(ctx: dict[str, Any]) -> None:
    response = st.correct_rally_3(ctx["api"], "ivy", ctx["match"])
    assert response.status_code == 200, response.text
    ctx["tags"] = st.corrected_example()
    opens_stats(ctx)


# Anchored on a bare percentage so it never also matches the "for her side" step above (two
# patterns matched it and pytest-bdd took this one, reading pct as "57% for her side"; TCR row
# 2026-10-09 in docs/sprints/03/decisions/ST-046b.md, ported from origin/sprint-03 1345187).
@then(
    parsers.re(r'"(?P<name>[^"]+)" shows (?P<pct>\d+%) with "n = (?P<n>\d+)"'),
    converters={"n": int},
)
def shows(ctx: dict[str, Any], name: str, pct: str, n: int) -> None:
    shows_for_her_side(ctx, name, pct, n)
