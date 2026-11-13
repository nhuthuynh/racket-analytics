"""Full Tag label documents (full-tag-labels/v1) for the pattern tests (ST-171b).

Team-made, no real people: slots ``A1 A2 B1 B2``. ``rally("r1", "A1", "B1", ("A2", "drop"))``
is a rally whose hits are, in frame order, A1 (serve), B1 (return) and A2 with the facet
``trajectory: drop``; a bare slot is a hit with no facet.
"""

from __future__ import annotations

from typing import Any

Hit = str | tuple[str, str]


def rally(rid: str, *hits: Hit, ending: str = "winner", winner: str | None = "A") -> dict[str, Any]:
    events: list[dict[str, Any]] = []
    for i, hit in enumerate(hits):
        hitter, trajectory = (hit, None) if isinstance(hit, str) else hit
        event: dict[str, Any] = {"type": "hit", "frame": 10 * (i + 1), "hitter": hitter}
        if trajectory is not None:
            event["facets"] = {"trajectory": trajectory}
        events.append(event)
    outcome = {"ending": ending, "winning_side": None if ending == "replay" else winner}
    return {"id": rid, "start_frame": 0, "end_frame": 10 * (len(hits) + 1),
            "outcome": outcome, "events": events}  # fmt: skip


def doc(*rallies: dict[str, Any]) -> dict[str, Any]:
    return {"schema": "full-tag-labels/v1", "clip": "clips/test.mp4", "fps": 60,
            "frame_count": 100_000, "players": ["A1", "A2", "B1", "B2"],
            "rallies": list(rallies)}  # fmt: skip


def third_shots(server: str, trajectories: list[str | None], start: int = 1) -> list[Any]:
    """One rally per entry, served by ``server``'s side, whose third shot has that trajectory
    (``None``: no facet)."""
    returner, third = ("B1", "A2") if server == "A" else ("A1", "B2")
    out = []
    for i, trajectory in enumerate(trajectories, start=start):
        last: Hit = third if trajectory is None else (third, trajectory)
        out.append(rally(f"r{i}", f"{server}1", returner, last))
    return out
