"""Score sheets for the analytics unit tests, built by the real projection (ST-026).

The analytics context reads only the projected sheet (sprint-03 §3.4 ST-044), so the tests
build stored scorebooks from Quick Tag values and let ``project`` fold them, exactly as the API
does. The worked example is the coach's hand count, metric-dictionary §2 (v0.1).
"""

from __future__ import annotations

import uuid
from collections.abc import Mapping, Sequence
from typing import Any

from racket.matches.scorebook.domain import (
    GameStart,
    OutcomeInput,
    Rally,
    RallyTimes,
    Scorebook,
    project,
)
from racket.sports.pickleball.rules import Side

RULES = "PROVISIONAL-UNVERIFIED"


def tag(
    winner: str | None, ending: str, kind: str | None = None, player: str | None = None
) -> dict[str, Any]:
    return {
        "winning_side": winner,
        "ending": ending,
        "fault_kind": kind,
        "responsible_player": player,
    }


# metric-dictionary §2: game starts 0-0-2, A serving; rally 8 is a replay.
WORKED_EXAMPLE: list[dict[str, Any]] = [
    tag("A", "winner", None, "A1"),
    tag("B", "fault", "serve", "A2"),
    tag("B", "winner"),
    tag("B", "unforced_error", None, "A1"),
    tag("A", "forced_error", None, "B2"),
    tag("A", "fault", "nvz", "B1"),
    tag("A", "winner", None, "A2"),
    tag(None, "replay"),
    tag("A", "unforced_error"),
    tag("B", "unforced_error", None, "A2"),
    tag("A", "fault"),
    tag("B", "fault", "serve", "A1"),
    tag("B", "winner", None, "B1"),
    tag("B", "winner", None, "B2"),
]


def book(games: Sequence[Mapping[str, Any]], *, best_of: int = 3) -> Scorebook:
    """``games``: ``[{"first_serving_side": "A", "tags": [...]}, ...]`` in play order."""
    rallies, starts, t, seq = [], [], 0, 0
    for number, game in enumerate(games, start=1):
        starts.append(
            GameStart(
                number=number,
                first_serving_side=Side(game["first_serving_side"]),
                ends_switched=False,
                created_version=1,
            )
        )
        for raw in game["tags"]:
            seq += 1
            body = {k: v for k, v in raw.items() if v is not None}
            rallies.append(
                Rally(
                    id=uuid.UUID(int=seq),
                    game_number=number,
                    seq=seq,
                    times=RallyTimes.parse(t, t + 3_000),
                    outcome=OutcomeInput.parse(body, format="doubles"),
                    created_version=seq + 1,
                )
            )
            t += 4_000
    return Scorebook(
        rules_version=RULES,
        format="doubles",
        best_of=best_of,
        version=seq + 1,
        games=tuple(starts),
        rallies=tuple(rallies),
    )


def sheet(games: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    return project(book(games))


def one_game(tags: Sequence[Mapping[str, Any]], first: str = "A") -> dict[str, Any]:
    return sheet([{"first_serving_side": first, "tags": list(tags)}])


def side_a_wins_game(first: str = "A") -> list[dict[str, Any]]:
    """11-0 to A when A serves first: A wins every rally (A1 server 2 at 0-0-2 keeps serving)."""
    return [tag("A", "winner") for _ in range(11)]


def a_serves_and_wins_25() -> dict[str, Any]:
    """Side A serves 25 rallies and wins all of them (11-0, 11-0, 3-0; best of 5), so A's
    AN-01 is 25/25 and A's AN-05 is 0/25: both intervals are narrower than 30 points and only
    ``n`` decides the flag."""
    games = [
        {"first_serving_side": "A", "tags": side_a_wins_game()},
        {"first_serving_side": "A", "tags": side_a_wins_game()},
        {"first_serving_side": "A", "tags": [tag("A", "winner") for _ in range(3)]},
    ]
    return project(book(games, best_of=5))
