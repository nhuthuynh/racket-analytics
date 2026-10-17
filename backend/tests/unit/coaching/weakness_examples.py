"""The coach's weakness worked examples (COACH-4, weakness-catalogue.md §7) for ST-055 tests.

``catalogue_rows()`` reads the §7 table as the coach wrote it; ``render()`` prints a product
ranking in the same row format, so a test compares the product with the coach's text, not with
numbers copied into the test. ``golden_sheet()`` projects a GS-AN-1 script (corrections applied
to the tags, as the coach's replay does) with the real score sheet projection.
"""

from __future__ import annotations

import json
from typing import Any

from racket.coaching.weakness.domain import WeaknessRanking
from tests.support.paths import BACKEND, REPO
from tests.unit.analytics.sheets import sheet

CATALOGUE = REPO / "docs" / "domain" / "weakness-catalogue.md"
GOLDEN_DIR = BACKEND / "tests" / "regression" / "golden_matches"
GOLDEN = {
    "gm1": "gm1-two-games",
    "gm2": "gm2-three-games",
    "gm3": "gm3-corrections-needs-decision",
}
# Plan target (catalogue §5) -> the label the §7 rows print.
LABEL = {"AN-07:fault": "AN-07 fault", "AN-07:forced-error": "AN-07 FE"}
TAG_KEYS = ("winning_side", "ending", "fault_kind", "responsible_player")


def catalogue_rows() -> dict[tuple[str, str], tuple[int, str, str]]:
    """(example, side) -> (games, ranking cell, rallies-lost cell) from §7."""
    text = CATALOGUE.read_text(encoding="utf-8")
    section = text.split("## 7.", 1)[1]
    rows = {}
    for line in section.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) != 5 or not cells[2].isdigit():
            continue
        rows[(cells[0], cells[1])] = (int(cells[2]), cells[3], cells[4])
    return rows


def render(ranking: WeaknessRanking) -> tuple[str, str]:
    """The ranking in the §7 row format: (ranking cell, rallies-lost cell)."""
    cells = [
        f"{w.rank}. {w.name} {w.lost} = {w.lost_on_serve} + {w.lost_on_receive} "
        f"({float(w.per_game):.1f}/game; {LABEL.get(w.plan_target, w.plan_target)})"
        for w in ranking.weaknesses
    ]
    serve, receive = ranking.lost_on_serve, ranking.lost_on_receive
    totals = f"{serve + receive} = {serve} + {receive}; unattributed {ranking.unattributed}"
    return "<br>".join(cells), totals


def golden_script(name: str) -> dict[str, Any]:
    data: dict[str, Any] = json.loads(
        (GOLDEN_DIR / f"{GOLDEN[name]}.script.json").read_text(encoding="utf-8")
    )
    return data


def corrected_games(name: str) -> list[dict[str, Any]]:
    """The script's games with its corrections applied to the tags (the end state)."""
    script = golden_script(name)
    games = [
        {
            "first_serving_side": g["first_serving_side"],
            "tags": [{k: t.get(k) for k in TAG_KEYS} for t in g["tags"]],
        }
        for g in script["games"]
    ]
    flat = [t for g in games for t in g["tags"]]
    for c in script.get("corrections", []):
        flat[c["rally"] - 1][c["field"]] = c["value"]
    return games


def golden_sheet(name: str) -> dict[str, Any]:
    return sheet(corrected_games(name))
