"""ST-060 eval pipeline seams (NFR-005a): a tag script becomes a score sheet through Match &
Scoring's published port (the real scorebook commands), and the sheet's published metrics come
through Analytics' published port, exactly as ``GET …/stats`` and ``…/evidence`` compute them.
Negative case first."""

from __future__ import annotations

from typing import Any

import pytest

from racket.analytics.starter_stats import starter_stats
from tests.support.contract import Seam
from tests.unit.analytics.sheets import WORKED_EXAMPLE, one_game

pytestmark = pytest.mark.unit

SHEET_OF_TAGS = Seam(
    "racket.matches.public:sheet_of_tags",
    "ST-060",
    "sheet_of_tags(games, *, format, best_of) -> the projected score sheet; refuses what the "
    "scorebook refuses",
)
METRIC_FACTS_OF_SHEET = Seam(
    "racket.analytics.public:metric_facts_of_sheet",
    "ST-060",
    "metric_facts_of_sheet(sheet, side) -> MatchMetrics, as metric_facts reads a live sheet",
)
GAMES = [{"first_serving_side": "A", "tags": WORKED_EXAMPLE}]


def _without_ids(sheet: dict[str, Any]) -> dict[str, Any]:
    return sheet | {"rows": [{**r, "rally_id": None} for r in sheet["rows"]]}


def test_a_rally_after_the_game_is_over_is_refused() -> None:
    won = [{"winning_side": "A", "ending": "winner"} for _ in range(12)]  # 11-0 ends the game
    with pytest.raises(Exception, match="over"):
        SHEET_OF_TAGS.load()([{"first_serving_side": "A", "tags": won}])


def test_the_sheet_of_a_tag_script_is_the_scorebook_projection() -> None:
    sheet = SHEET_OF_TAGS.load()(GAMES)
    assert _without_ids(sheet) == _without_ids(one_game(WORKED_EXAMPLE))
    assert sheet == SHEET_OF_TAGS.load()(GAMES)  # deterministic ids: the same bytes every time


def test_metric_facts_of_a_sheet_are_the_published_stats_and_evidence() -> None:
    sheet = SHEET_OF_TAGS.load()(GAMES)
    stats = starter_stats(sheet)
    found = METRIC_FACTS_OF_SHEET.load()(sheet, "A")
    assert found.rallies == 13
    ids = {row["number"]: row["rally_id"] for row in sheet["rows"]}
    for metric in ("AN-01", "AN-02", "AN-05", "AN-07"):
        fact = found.metrics[metric]
        assert (fact.k, fact.n) == (stats[metric]["A"].get("k", 0), stats[metric]["A"]["n"])
        assert list(fact.rally_ids) == [ids[n] for n in stats[metric]["A"]["rallies"]]
    assert (found.metrics["AN-04"].k, found.metrics["AN-04"].n) == (
        stats["AN-04"]["A"]["count"],
        stats["AN-04"]["A"]["games"],
    )
