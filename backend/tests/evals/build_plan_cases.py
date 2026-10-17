"""Writes the ST-060 eval cases (NFR-005a) to ``plan_cases/``: synthetic Quick Tag scripts plus
plan preferences. Run once by hand; the JSON files are the frozen eval set, reviewed as data.

    cd backend && uv run --no-sync python -m tests.evals.build_plan_cases

Each tag script is played through the real scorebook (``Scorebook.start_game`` / ``tag``), so a
game ends where the rules end it and a new one starts with the other side serving first. Which
side loses a rally, and how, follows the case's weakness ``profile``; a serve fault is only ever
tagged on the serving side. ``random.Random(seed)`` keeps the scripts reproducible; the eval
itself has no randomness.

``expect`` is the case author's oracle, written from the drill library's rules and not from a
run: a session cap under 10 minutes (40% of under 25 minutes) fits no weakness drill (every one
lasts at least 10), a solo player has no reviewed weakness drill above intermediate, and a solo
player without a wall or a full court has no reviewed weakness drill at all, and every reviewed
advanced drill that needs only a half court lasts at least 15 minutes (cap 15 needs a 38-minute
session). The last rule was missed at first and found by the first green run (pe-20; decisions
file ST-060).
"""

from __future__ import annotations

import json
import random
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from racket.matches.scorebook.domain import (
    CommandContext,
    OutcomeInput,
    RallyTimes,
    Scorebook,
)
from racket.matches.scorebook.domain.projection import play
from racket.sports.pickleball.rules import Side

OUT = Path(__file__).resolve().parent / "plan_cases"
RULES = "PROVISIONAL-UNVERIFIED"
LOSS_KINDS = ("unforced_error", "serve_fault", "other_fault", "forced_error", "opponent_winner")
PROFILES: dict[str, tuple[int, int, int, int, int]] = {
    # weights over LOSS_KINDS for the rallies the player's side loses
    "serve-faults": (2, 6, 1, 1, 1),
    "unforced": (7, 1, 1, 1, 1),
    "pressure": (1, 1, 1, 6, 2),
    "winners-against": (1, 1, 1, 2, 6),
    "other-faults": (1, 1, 6, 1, 1),
    "mixed": (3, 2, 2, 2, 2),
}
SLOTS = {"doubles": ("1", "2")}  # the only shipped rules preset is doubles (ADR 0009)


@dataclass
class Spec:
    id: str
    players: int
    minutes: int
    sessions: int
    equipment: tuple[str, ...]
    level: str
    sample: str  # "low" | "high"
    profile: str
    side: str = "A"
    format: str = "doubles"
    weekly: int | None = None
    seed: int = 0
    expect: str = "plan"
    notes: list[str] = field(default_factory=list)


def _tag(
    rng: random.Random, fmt: str, side: str, serving: str, weights: tuple[int, ...]
) -> dict[str, Any]:
    other = "B" if side == "A" else "A"
    if rng.random() < 0.04:
        return {"ending": "replay"}
    me_wins = rng.random() < 0.42
    loser, winner = (other, side) if me_wins else (side, other)
    kind = rng.choices(LOSS_KINDS, weights=weights if not me_wins else (2, 1, 1, 2, 3))[0]
    loser_player = loser + rng.choice(SLOTS[fmt])
    winner_player = winner + rng.choice(SLOTS[fmt])
    named = rng.random() < 0.85  # some tags leave the player out, as players do
    if kind == "serve_fault" and loser == serving:
        tag = {"winning_side": winner, "ending": "fault", "fault_kind": "serve"}
    elif kind in ("serve_fault", "other_fault"):
        tag = {
            "winning_side": winner,
            "ending": "fault",
            "fault_kind": rng.choice(("nvz", "foot", "two_bounce", "other")),
        }
    elif kind == "opponent_winner":
        tag = {"winning_side": winner, "ending": "winner"}
        if named:
            tag["responsible_player"] = winner_player
        return tag
    else:
        tag = {"winning_side": winner, "ending": kind}
    if named:
        tag["responsible_player"] = loser_player
    return tag


def _match(rng: random.Random, spec: Spec, rallies: int, best_of: int) -> dict[str, Any]:
    ctx = CommandContext(
        actor_id=uuid.UUID(int=0), at=datetime(2026, 10, 1, tzinfo=UTC), new_id=lambda: uuid.uuid4()
    )
    book = Scorebook.new(rules_version=RULES, format=spec.format, best_of=best_of)
    games: list[dict[str, Any]] = []
    first = rng.choice(("A", "B"))
    t = 0
    weights = PROFILES[spec.profile]
    while sum(len(g["tags"]) for g in games) < rallies:
        played = play(book)
        if played.winner is not None:
            break
        if not games or played.games[-1].over:
            first = first if not games else ("B" if games[-1]["first_serving_side"] == "A" else "A")
            book = book.start_game(
                first_serving_side=Side(first),
                ends_switched=False,
                ready=True,
                expected_version=book.version,
                ctx=ctx,
            )
            games.append({"first_serving_side": first, "tags": []})
            continue
        state = played.games[-1].state
        assert state is not None
        tag = _tag(rng, spec.format, spec.side, state.serving_side.value, weights)
        book, _ = book.tag(
            RallyTimes.parse(t, t + 3000),
            OutcomeInput.parse(tag, format=spec.format),
            ready=True,
            expected_version=book.version,
            ctx=ctx,
        )
        games[-1]["tags"].append(tag)
        t += 4000
    return {"format": spec.format, "best_of": best_of, "side": spec.side, "games": games}


def build(spec: Spec) -> dict[str, Any]:
    rng = random.Random(f"{spec.id}/{spec.seed}")  # noqa: S311 - reproducible test data
    if spec.sample == "low":
        matches = [_match(rng, spec, rng.randint(12, 20), 1)]
    else:
        matches = [_match(rng, spec, 200, 3) for _ in range(3)]
    prefs: dict[str, Any] = {
        "minutes_per_session": spec.minutes,
        "sessions_per_week": spec.sessions,
        "players_available": spec.players,
        "equipment": sorted(spec.equipment),
        "level": spec.level,
    }
    if spec.weekly is not None:
        prefs["weekly_minutes"] = spec.weekly
    who = {1: "solo", 2: "pairs", 4: "four"}[spec.players]
    kit = ", ".join(spec.equipment) or "no equipment"
    description = (
        f"{who}, {spec.minutes} min x {spec.sessions}/week, {kit}, {spec.level}; "
        f"{spec.sample} sample ({sum(len(g['tags']) for m in matches for g in m['games'])} tags "
        f"in {len(matches)} match(es)), '{spec.profile}' losses, player on side {spec.side} "
        f"({spec.format})"
    )
    return {
        "id": spec.id,
        "description": " ".join([description, *spec.notes]),
        "dimensions": {
            "players": who,
            "minutes_per_session": spec.minutes,
            "ball_machine": "ball_machine" in spec.equipment,
            "wall": "wall" in spec.equipment,
            "level": spec.level,
            "sample": spec.sample,
        },
        "preferences": prefs,
        "matches": matches,
        "expect": spec.expect,
    }


FULL = ("full_court", "half_court")
SPECS = [
    # solo
    Spec("pe-01", 1, 30, 3, ("wall",), "intermediate", "low", "mixed"),
    Spec("pe-02", 1, 30, 3, ("wall", "ball_machine"), "beginner", "high", "unforced"),
    Spec("pe-03", 1, 45, 2, ("wall", *FULL), "beginner", "high", "serve-faults"),
    Spec(
        "pe-04", 1, 60, 4, ("wall", "ball_machine", *FULL), "intermediate", "low", "winners-against"
    ),
    Spec("pe-05", 1, 25, 5, ("wall",), "beginner", "low", "other-faults"),
    Spec("pe-06", 1, 90, 1, FULL, "intermediate", "high", "serve-faults"),
    Spec("pe-07", 1, 40, 3, ("wall",), "intermediate", "high", "pressure", side="B"),
    Spec(
        "pe-08",
        1,
        30,
        3,
        (),
        "beginner",
        "low",
        "mixed",
        expect="no_plan_fits",
        notes=["Refusal: no reviewed solo weakness drill needs no equipment."],
    ),
    Spec(
        "pe-09",
        1,
        45,
        3,
        ("wall", *FULL),
        "advanced",
        "high",
        "unforced",
        expect="no_plan_fits",
        notes=["Refusal: every reviewed solo weakness drill stops at intermediate."],
    ),
    Spec(
        "pe-10",
        1,
        20,
        3,
        ("wall",),
        "beginner",
        "low",
        "unforced",
        expect="no_plan_fits",
        notes=["Refusal: a 20-minute session caps a drill at 8 minutes; none is that short."],
    ),
    Spec("pe-11", 1, 35, 2, ("wall", "ball_machine"), "intermediate", "low", "unforced"),
    # pairs
    Spec("pe-12", 2, 30, 3, ("half_court",), "beginner", "low", "pressure"),
    Spec("pe-13", 2, 30, 3, FULL, "intermediate", "high", "mixed"),
    Spec("pe-14", 2, 45, 3, FULL, "advanced", "high", "winners-against"),
    Spec("pe-15", 2, 60, 2, ("half_court", "wall"), "intermediate", "low", "other-faults"),
    Spec("pe-16", 2, 90, 2, (*FULL, "ball_machine"), "advanced", "low", "serve-faults"),
    Spec("pe-17", 2, 25, 4, ("half_court",), "beginner", "high", "unforced", side="B"),
    Spec("pe-18", 2, 50, 3, (*FULL, "wall", "ball_machine"), "beginner", "high", "winners-against"),
    Spec("pe-19", 2, 75, 2, FULL, "intermediate", "low", "pressure", side="B"),
    Spec(
        "pe-20",
        2,
        30,
        5,
        ("half_court", "ball_machine"),
        "advanced",
        "high",
        "unforced",
        expect="no_plan_fits",
        notes=[
            "Refusal: every reviewed advanced half-court drill lasts at least 15 minutes, "
            "over the 12-minute cap of a 30-minute session."
        ],
    ),
    Spec(
        "pe-21",
        2,
        20,
        2,
        FULL,
        "intermediate",
        "high",
        "mixed",
        expect="no_plan_fits",
        notes=["Refusal: a 20-minute session caps a drill at 8 minutes; none is that short."],
    ),
    Spec(
        "pe-22",
        2,
        60,
        3,
        ("wall",),
        "intermediate",
        "low",
        "unforced",
        notes=["Pairs with only a wall: the solo wall drills fit."],
    ),
    Spec(
        "pe-23",
        2,
        45,
        3,
        FULL,
        "intermediate",
        "high",
        "serve-faults",
        weekly=100,
        notes=["Weekly minutes 100 over 3 sessions: a 33-minute budget."],
    ),
    Spec("pe-24", 2, 40, 4, FULL, "beginner", "low", "other-faults", side="B"),
    # four
    Spec("pe-25", 4, 30, 3, FULL, "intermediate", "high", "mixed"),
    Spec(
        "pe-26",
        4,
        60,
        3,
        (*FULL, "wall", "ball_machine", "partner_feeder"),
        "advanced",
        "high",
        "pressure",
    ),
    Spec("pe-27", 4, 90, 1, FULL, "beginner", "low", "winners-against"),
    Spec("pe-28", 4, 45, 2, ("half_court",), "advanced", "low", "unforced"),
    Spec(
        "pe-29", 4, 25, 5, (*FULL, "ball_machine"), "intermediate", "high", "serve-faults", side="B"
    ),
    Spec("pe-30", 4, 75, 4, (*FULL, "wall"), "beginner", "high", "other-faults"),
    Spec(
        "pe-31",
        4,
        20,
        4,
        (*FULL, "wall"),
        "advanced",
        "low",
        "pressure",
        expect="no_plan_fits",
        notes=["Refusal: a 20-minute session caps a drill at 8 minutes; none is that short."],
    ),
    Spec(
        "pe-32",
        4,
        60,
        7,
        FULL,
        "intermediate",
        "low",
        "mixed",
        weekly=210,
        notes=["Weekly minutes 210 over 7 sessions: a 30-minute budget."],
    ),
]


def dump(case: dict[str, Any]) -> str:
    """One top-level key per line and one match per line: short diffs, still readable."""

    def one(value: Any) -> str:
        return json.dumps(value, sort_keys=True, ensure_ascii=False)

    lines = [f" {one(k)}: {one(v)}," for k, v in sorted(case.items()) if k != "matches"]
    matches = ",\n".join(f"  {one(m)}" for m in case["matches"])
    return "{\n" + "\n".join(lines) + '\n "matches": [\n' + matches + "\n ]\n}\n"


def main() -> None:
    OUT.mkdir(exist_ok=True)
    for spec in SPECS:
        case = build(spec)
        path = OUT / f"{spec.id}.json"
        path.write_text(dump(case), encoding="utf-8")
    print(f"wrote {len(SPECS)} cases to {OUT}")


if __name__ == "__main__":
    main()
