"""Domain binding of tests/features/attribution_conservation.feature (QA-ACC-3 for ST-045;
FR-109, ADR 0003). The game is driven through the scorebook commands and projected (ST-026);
the product's attribution (``racket.analytics.attribution``) reads the projected sheet. The
script is ``stats.lost_split_script(6, 8)``: side A loses 6 rallies on serve and 8 on receive,
both with A's own errors and B's winners, so both "attributed" and "unattributed" occur.
"""

from __future__ import annotations

from typing import Any

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from tests.regression.test_golden_replay import Fixture
from tests.support import stats as st

scenarios("attribution_conservation.feature")


@pytest.fixture
def state() -> dict[str, Any]:
    return {}


@given(
    parsers.parse(
        "side A lost {lost:d} rallies in game 1, "
        "{on_serve:d} on serve and {on_receive:d} on receive"
    )
)
def lost_split(state: dict[str, Any], lost: int, on_serve: int, on_receive: int) -> None:
    assert lost == on_serve + on_receive
    games = st.timed(st.lost_split_script(on_serve, on_receive))
    fixture = Fixture().start("A").tag(games[0]["tags"])
    from racket.analytics.sheet import counted_rallies

    state["counted"] = counted_rallies(fixture.sheet())
    reference = st.statslib.lost_rallies(games)["A"]
    assert (len(reference["serve"]), len(reference["receive"])) == (on_serve, on_receive)


@when("the lost rallies are attributed")
def attribute(state: dict[str, Any]) -> None:
    from racket.analytics.attribution import attribute_lost_rallies, check_conservation

    state["attributed"] = attribute_lost_rallies(state["counted"])
    check_conservation(state["counted"], state["attributed"])  # raises if broken


def _total(state: dict[str, Any], phase: str) -> tuple[int, set[str]]:
    groups = state["attributed"]["A"][1][phase]
    return sum(len(v) for v in groups.values()), set(groups)


@then(parsers.parse("the attributed and unattributed rallies on serve total {n:d}"))
def on_serve(state: dict[str, Any], n: int) -> None:
    total, categories = _total(state, "serve")
    assert total == n
    assert "unattributed" in categories, "the script has B winners on A's serve"
    assert categories - {"unattributed"}, "the script has A errors on A's serve"


@then(parsers.parse("on receive they total {n:d}"))
def on_receive(state: dict[str, Any], n: int) -> None:
    total, _ = _total(state, "receive")
    assert total == n
