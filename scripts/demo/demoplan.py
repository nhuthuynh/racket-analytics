"""The pure plan behind `make demo` (MVP-03): which match to seed and which rallies to tag.

Standard library only, no I/O (seed_demo.py does the HTTP). Ubiquitous language of the Match
and Scorebook contexts (api-sprint-02 §2): a doubles *match* gets *game* 1, and each *rally* is
a Quick Tag: its time on the video, the *ending*, the *winning side* and, where the player said
so, the *responsible player* and *fault kind*. The demo only says what a player would tap; the
API decides the score and the stats (no product rule is copied here).
Tests: infra/tests/test_demo_plan.py.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

DEMO_USER = "ivy"  # a seeded dev user (players.service.DEV_USERS); signs in with one click
DEMO_USER_LABEL = "Ivy"
DEMO_TITLE = "Demo match"
FIRST_SERVING_SIDE = "A"
DEMO_PARTICIPANTS = [
    {"slot": "A1", "nickname": "Ivy", "is_me": True},
    {"slot": "A2", "nickname": "Dana", "is_me": False},
    {"slot": "B1", "nickname": "Carlos", "is_me": False},
    {"slot": "B2", "nickname": "Sam", "is_me": False},
]
FAULT_KINDS = frozenset({"serve", "foot", "two_bounce", "nvz", "other"})
DEV_PROFILE = "dev"
_FALSE = {"0", "false", "no", "off"}
_TITLE = re.compile(r"^Demo match(?: \((\d+)\))?$")


def _rally(
    winning_side: str | None,
    ending: str,
    responsible_player: str | None = None,
    fault_kind: str | None = None,
) -> dict[str, Any]:
    return {
        "winning_side": winning_side,
        "ending": ending,
        "responsible_player": responsible_player,
        "fault_kind": fault_kind,
    }


# Game 1, side A serving first. Both sides hit winners and make errors and faults, so every
# published metric has a sample on both sides; one replay; a few rallies with no player tagged.
OUTCOMES: tuple[dict[str, Any], ...] = (
    _rally("A", "winner", "A1"),
    _rally("B", "unforced_error", "A2"),
    _rally("B", "winner", "B1"),
    _rally("A", "forced_error", "B2"),
    _rally("A", "fault", "B1", "nvz"),
    _rally("B", "winner", "B2"),
    _rally("A", "winner", "A2"),
    _rally(None, "replay"),
    _rally("B", "fault", "A1", "serve"),
    _rally("A", "unforced_error"),
    _rally("A", "winner", "A1"),
    _rally("B", "forced_error", "A2"),
)
RALLIES = len(OUTCOMES)


def rally_plan(video_ms: int) -> list[dict[str, Any]]:
    """The demo rallies spread over the video: in order, inside it, with a pause between them."""
    slot = video_ms // RALLIES
    if slot < 1_000:
        raise ValueError(f"video too short for {RALLIES} rallies: {video_ms} ms")
    length = slot * 3 // 4  # the last quarter of each slot is the pause before the next serve
    return [
        {"start_ms": i * slot, "end_ms": i * slot + length, **outcome}
        for i, outcome in enumerate(OUTCOMES)
    ]


def parse_env_file(text: str) -> dict[str, str]:
    """``KEY=value`` lines of a Compose env file; comments and other lines are skipped."""
    out: dict[str, str] = {}
    for line in text.splitlines():
        key, sep, value = line.partition("=")
        key = key.strip()
        if not sep or not key.isidentifier() or line.lstrip().startswith("#"):
            continue
        out[key] = value.strip().strip("'\"")
    return out


def refusal(env: Mapping[str, str]) -> str | None:
    """Why the demo must not run against this profile, or None. Unknown keys do not refuse:
    the live GET /dev/users check decides then (the API mounts /dev/* only when enabled)."""
    app_env = env.get("APP_ENV")
    if app_env is not None and app_env != DEV_PROFILE:
        return f"make demo runs only against the dev profile (APP_ENV=dev); found APP_ENV={app_env}"
    if env.get("DEV_IDENTITY_ENABLED", "").strip().lower() in _FALSE:
        return "dev sign-in is disabled (DEV_IDENTITY_ENABLED); make demo needs a dev stack"
    return None


def is_demo_title(title: str) -> bool:
    return _TITLE.fullmatch(title) is not None


@dataclass(frozen=True)
class DemoMatch:
    id: str
    title: str
    status: str
    rallies: int


@dataclass(frozen=True)
class Action:
    kind: str  # "reuse" or "create"
    title: str
    match_id: str | None


def _number(title: str) -> int:
    found = _TITLE.fullmatch(title)
    return int(found.group(1) or 1) if found else 0


def choose(found: Iterable[DemoMatch], *, planned: int, new: bool = False) -> Action:
    """Reuse a complete demo match; otherwise create the next one ("Demo match (n)")."""
    demos = [m for m in found if is_demo_title(m.title)]
    if not new:
        for m in demos:
            if m.status == "video_received" and m.rallies >= planned:
                return Action("reuse", m.title, m.id)
    highest = max((_number(m.title) for m in demos), default=0)
    title = DEMO_TITLE if highest == 0 else f"{DEMO_TITLE} ({highest + 1})"
    return Action("create", title, None)


def stats_url(origin: str, match_id: str) -> str:
    return f"{origin.rstrip('/')}/matches/{match_id}/stats"
