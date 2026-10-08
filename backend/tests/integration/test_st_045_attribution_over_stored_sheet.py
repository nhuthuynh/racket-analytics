"""ST-045 integration (FR-109, ADR 0003): attribution conservation over a sheet stored and
projected by the real stack. Matches are tagged through the API into Postgres; the sheet read
back (GET .../sheet) is what ``racket.analytics`` reads. Every lost rally is attributed once per
game, side and phase, and the stats computation runs the check (a broken attribution refuses).
"""

from __future__ import annotations

from typing import Any

import pytest

import racket.analytics.starter_stats as stats_module
from racket.analytics.attribution import (
    PHASES,
    UNATTRIBUTED,
    AttributionBroken,
    attribute_lost_rallies,
    check_conservation,
    lost_rallies,
)
from racket.analytics.sheet import SIDES, counted_rallies
from racket.analytics.starter_stats import starter_stats
from tests.support import scorebook as sb
from tests.support.api import ApiDriver
from tests.unit.analytics.sheets import WORKED_EXAMPLE, one_game


def _stored_sheet(api: ApiDriver, tags: list[dict[str, Any]], title: str) -> Any:
    match_id = sb.ready_tagged_match(api, "ivy", sb.taglib.with_times(tags), title=title)
    return sb.sheet_body(api, "ivy", match_id)


def test_st_045_a_broken_attribution_of_a_stored_match_refuses_the_stats(
    api: ApiDriver, monkeypatch: pytest.MonkeyPatch
) -> None:
    stored = _stored_sheet(api, WORKED_EXAMPLE, "ST-045 broken")

    def broken(counted: Any) -> Any:
        attributed = attribute_lost_rallies(counted)
        attributed["B"][1]["receive"] = {}
        return attributed

    monkeypatch.setattr(stats_module, "attribute_lost_rallies", broken)
    with pytest.raises(AttributionBroken, match="B game 1 receive"):
        starter_stats(stored)


def test_st_045_the_stored_worked_example_conserves_every_lost_rally(api: ApiDriver) -> None:
    stored = _stored_sheet(api, WORKED_EXAMPLE, "ST-045 worked example")
    counted = counted_rallies(stored)
    attributed = attribute_lost_rallies(counted)
    check_conservation(counted, attributed)
    lost = lost_rallies(counted)
    assert lost["A"][1] == {"serve": [2, 10, 12], "receive": [3, 4, 13, 14]}
    assert lost["B"][1] == {"serve": [5, 6], "receive": [1, 7, 9, 11]}
    for side in SIDES:
        for game, phases in lost[side].items():
            for phase in PHASES:
                got = sorted(n for v in attributed[side][game][phase].values() for n in v)
                assert got == phases[phase], (side, game, phase)
    assert attributed["A"][1]["receive"][UNATTRIBUTED] == [3, 13, 14]
    assert attributed == attribute_lost_rallies(counted_rallies(one_game(WORKED_EXAMPLE)))
    starter_stats(stored)  # the check passes inside every computation
