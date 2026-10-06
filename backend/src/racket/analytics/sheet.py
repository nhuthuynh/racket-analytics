"""Reading the projected score sheet for analytics (ST-044, ST-045; metric-dictionary rules
0.1 and 0.2).

The sheet is Match & Scoring's projection (ST-026) read as plain JSON: this context imports
nothing of that one. Rows that are replays or that the sheet could not score
(``needs_decision``) never count. Who scored is read from the score total, never from a rule.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

SIDES = ("A", "B")
_OTHER = {"A": "B", "B": "A"}


@dataclass(frozen=True, slots=True)
class CountedRally:
    """One sheet row that counts towards the stats (rules 0.1 and 0.2 applied)."""

    number: int
    rally_id: str
    game: int
    winning_side: str
    ending: str
    fault_kind: str | None
    responsible_player: str | None
    serving_side: str
    actor: str  # the side that made the ending (rule 0.2)
    point_to: str | None  # the side that scored, or None when only the serve moved


def _total(call: object) -> int | None:
    """Sum of the two scores of a call ("4-2-1" or "4-2"); None if it is not a call."""
    if not isinstance(call, str):
        return None
    parts = call.split("-")
    if len(parts) < 2 or not all(p.isdigit() for p in parts[:2]):
        return None
    return int(parts[0]) + int(parts[1])


def counted_rallies(sheet: Mapping[str, Any]) -> list[CountedRally]:
    out = []
    for row in sheet.get("rows", ()):
        side, serving = row.get("winning_side"), row.get("serving_side")
        if row.get("marker") is not None or row.get("ending") == "replay":
            continue
        if side not in _OTHER or serving not in _OTHER:
            continue  # defensive: the sheet never scores such a row
        before, after = _total(row.get("score_before")), _total(row.get("score_after"))
        scored = before is not None and after is not None and after == before + 1
        ending = row["ending"]
        out.append(
            CountedRally(
                number=row["number"],
                rally_id=row["rally_id"],
                game=row["game"],
                winning_side=side,
                ending=ending,
                fault_kind=row.get("fault_kind"),
                responsible_player=row.get("responsible_player"),
                serving_side=serving,
                actor=side if ending == "winner" else _OTHER[side],
                point_to=side if scored else None,
            )
        )
    return out


def games_in_scope(sheet: Mapping[str, Any]) -> int:
    """Completed games plus the current one (dictionary AN-04); a game the sheet cannot score
    because an earlier game is unfinished is not in scope (C-03)."""
    return sum(1 for g in sheet.get("games", ()) if g.get("score_a") is not None)
