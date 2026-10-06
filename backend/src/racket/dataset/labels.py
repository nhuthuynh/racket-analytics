"""Full Tag label schema v1 (ST-040; FR-150, FR-151; docs/data/gold-label-schema.md).

One label document per clip of a gold set. It holds what the Full Tag tool exports: rally
boundaries, hit and bounce events, the hitter, shot facets and the rally outcome.

Pure domain code: the document arrives as parsed JSON data; no I/O, no framework imports
(ddd-guidelines §4.5). ``validate_labels`` never raises on bad data: it lists every problem
with a JSON-path-like location, so the CI gate can name them all at once.

Vocabulary (published language of the Dataset & Labelling context):
* slots ``A1 A2 B1 B2`` and sides ``A B`` as in ``docs/architecture/match-aggregate.md`` §2;
* rally endings and fault kinds as in the Match & Scoring ``Ending`` / sport ``FaultKind``
  (a contract test pins them equal, ``tests/unit/dataset/test_labels.py``);
* shot facets as in QD-TX-01; ``position`` is derived by rule and never labelled.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, TypeGuard

LABEL_SCHEMA = "full-tag-labels/v1"

SINGLES = ("A1", "B1")
DOUBLES = ("A1", "A2", "B1", "B2")
SIDES = ("A", "B")
ENDINGS = ("winner", "unforced_error", "forced_error", "fault", "replay")
FAULT_KINDS = ("serve", "foot", "two_bounce", "nvz", "other")
EVENT_TYPES = ("bounce", "hit")
SHOT_FACETS: Mapping[str, tuple[str, ...]] = {
    "contact": ("groundstroke", "volley"),
    "trajectory": ("drive", "drop", "dink", "lob"),
    "intent": ("neutral", "speed_up", "reset"),
    "technique": ("none", "erne", "atp"),
}
DERIVED_FACETS = ("position",)
# match-aggregate §2.1: the side the responsible player must be on, per ending.
_RESPONSIBLE_SIDE = {
    "winner": "winning",
    "unforced_error": "losing",
    "forced_error": "losing",
    "fault": "losing",
}
_TOP_LEVEL = ("schema", "clip", "fps", "frame_count", "players", "rallies")


@dataclass(frozen=True)
class UnreadableLabels:
    """Stand-in for a label file that could not be parsed (the adapter passes it in)."""

    reason: str


@dataclass(frozen=True)
class LabelProblem:
    where: str
    message: str

    def describe(self) -> str:
        return f"{self.where}: {self.message}"


def _is_int(value: object) -> TypeGuard[int]:
    return isinstance(value, int) and not isinstance(value, bool)


def _is_number(value: object) -> TypeGuard[int | float]:
    return isinstance(value, int | float) and not isinstance(value, bool)


class _Validator:
    def __init__(self) -> None:
        self.problems: list[LabelProblem] = []

    def add(self, where: str, message: str) -> None:
        self.problems.append(LabelProblem(where, message))

    # --- document -------------------------------------------------------------------

    def document(self, doc: object) -> None:
        if isinstance(doc, UnreadableLabels):
            self.add("document", f"label file is not valid JSON: {doc.reason}")
            return
        if not isinstance(doc, Mapping):
            self.add("document", "label document must be a JSON object")
            return
        missing = [k for k in _TOP_LEVEL if k not in doc]
        for key in missing:
            self.add(key, "required")
        if "schema" in doc and doc["schema"] != LABEL_SCHEMA:
            self.add("schema", f"must be {LABEL_SCHEMA!r}, got {doc['schema']!r}")
        if "clip" in doc and not (isinstance(doc["clip"], str) and doc["clip"]):
            self.add("clip", "must be the clip path in the set")
        if "fps" in doc and not (_is_int(doc["fps"]) and doc["fps"] > 0):
            self.add("fps", "must be a positive integer")
        frame_count = doc.get("frame_count")
        if "frame_count" in doc and not (_is_int(frame_count) and frame_count > 0):
            self.add("frame_count", "must be a positive integer")
            frame_count = None
        players = self.players(doc.get("players")) if "players" in doc else ()
        if "rallies" in doc:
            self.rallies(doc["rallies"], frame_count, players)

    def players(self, raw: object) -> tuple[str, ...]:
        if isinstance(raw, list) and tuple(raw) in (SINGLES, DOUBLES):
            return tuple(raw)
        self.add("players", f"must be {list(SINGLES)} (singles) or {list(DOUBLES)} (doubles)")
        return ()

    # --- rallies --------------------------------------------------------------------

    def rallies(self, raw: object, frame_count: Any, players: tuple[str, ...]) -> None:
        if not isinstance(raw, list):
            self.add("rallies", "must be a list")
            return
        previous_end: int | None = None
        for i, rally in enumerate(raw):
            where = f"rallies[{i}]"
            if not isinstance(rally, Mapping):
                self.add(where, "must be an object")
                continue
            bounds = self.rally_bounds(where, rally, frame_count)
            if bounds is not None:
                start, end = bounds
                if previous_end is not None and start <= previous_end:
                    self.add(
                        where, f"starts before rallies[{i - 1}] ends (overlap or out of order)"
                    )
                previous_end = end
            self.outcome(f"{where}.outcome", rally.get("outcome"), players)
            self.events(f"{where}.events", rally.get("events"), bounds, players)

    def rally_bounds(
        self, where: str, rally: Mapping[str, Any], frame_count: Any
    ) -> tuple[int, int] | None:
        start, end = rally.get("start_frame"), rally.get("end_frame")
        ok = True
        for name, value in (("start_frame", start), ("end_frame", end)):
            if not _is_int(value) or value < 0:
                self.add(f"{where}.{name}", "must be a frame number (integer >= 0)")
                ok = False
            elif _is_int(frame_count) and value >= frame_count:
                self.add(f"{where}.{name}", f"must be within 0..{frame_count - 1}")
                ok = False
        if not (ok and _is_int(start) and _is_int(end)):
            return None
        if start >= end:
            self.add(where, "start_frame must be before end_frame")
            return None
        return start, end

    def outcome(self, where: str, raw: object, players: tuple[str, ...]) -> None:
        if not isinstance(raw, Mapping):
            self.add(where, "must be an object")
            return
        ending = raw.get("ending")
        if ending not in ENDINGS:
            self.add(f"{where}.ending", f"must be one of {list(ENDINGS)}")
            return
        side = raw.get("winning_side")
        if ending == "replay":
            if side is not None:
                self.add(f"{where}.winning_side", "must be null for a replay")
        elif side not in SIDES:
            self.add(f"{where}.winning_side", "must be 'A' or 'B'")
            side = None
        responsible = raw.get("responsible_player")
        if responsible is not None:
            if ending == "replay":
                self.add(f"{where}.responsible_player", "must be null for a replay")
            elif players and responsible not in players:
                self.add(
                    f"{where}.responsible_player", f"{responsible!r} is not one of {list(players)}"
                )
            elif side is not None and isinstance(responsible, str):
                expected = _RESPONSIBLE_SIDE[ending]
                on_winning = responsible[:1] == side
                if on_winning != (expected == "winning"):
                    self.add(
                        f"{where}.responsible_player",
                        f"must be on the {expected} side for {ending}",
                    )
        fault_kind = raw.get("fault_kind")
        if fault_kind is not None:
            if ending != "fault":
                self.add(f"{where}.fault_kind", "only for a fault")
            elif fault_kind not in FAULT_KINDS:
                self.add(f"{where}.fault_kind", f"must be one of {list(FAULT_KINDS)} or null")

    # --- events ---------------------------------------------------------------------

    def events(
        self,
        where: str,
        raw: object,
        bounds: tuple[int, int] | None,
        players: tuple[str, ...],
    ) -> None:
        if not isinstance(raw, list):
            self.add(where, "must be a list")
            return
        last_frame: int | None = None
        hit_frames: set[int] = set()
        for j, event in enumerate(raw):
            at = f"{where}[{j}]"
            if not isinstance(event, Mapping):
                self.add(at, "must be an object")
                continue
            kind = event.get("type")
            if kind not in EVENT_TYPES:
                self.add(f"{at}.type", f"must be one of {list(EVENT_TYPES)}")
            frame = event.get("frame")
            if not _is_int(frame) or frame < 0:
                self.add(f"{at}.frame", "must be a frame number (integer >= 0)")
            else:
                if bounds is not None and not bounds[0] <= frame <= bounds[1]:
                    self.add(f"{at}.frame", f"outside the rally ({bounds[0]}..{bounds[1]})")
                if last_frame is not None and frame < last_frame:
                    self.add(f"{at}.frame", "events must be in frame order")
                if kind == "hit" and frame in hit_frames:
                    self.add(f"{at}.frame", "two hits on one frame")
                if kind == "hit":
                    hit_frames.add(frame)
                last_frame = frame
            if kind == "hit":
                self.hit(at, event, players)
            elif kind == "bounce":
                self.bounce(at, event)

    def hit(self, at: str, event: Mapping[str, Any], players: tuple[str, ...]) -> None:
        hitter = event.get("hitter")
        if players and hitter not in players:
            self.add(f"{at}.hitter", f"{hitter!r} is not one of {list(players)}")
        facets = event.get("facets", {})
        if not isinstance(facets, Mapping):
            self.add(f"{at}.facets", "must be an object")
            return
        for name, value in facets.items():
            if name in DERIVED_FACETS:
                self.add(f"{at}.facets.{name}", "derived by rule, never labelled (QD-TX-01)")
            elif name not in SHOT_FACETS:
                self.add(f"{at}.facets.{name}", "unknown facet")
            elif value not in SHOT_FACETS[name]:
                self.add(
                    f"{at}.facets.{name}", f"{value!r} is not one of {list(SHOT_FACETS[name])}"
                )

    def bounce(self, at: str, event: Mapping[str, Any]) -> None:
        if "visible" in event and not isinstance(event["visible"], bool):
            self.add(f"{at}.visible", "must be true or false")
        xy = event.get("court_xy_m")
        if xy is not None and not (
            isinstance(xy, list) and len(xy) == 2 and all(_is_number(v) for v in xy)
        ):
            self.add(f"{at}.court_xy_m", "must be [x, y] in metres or null")


def validate_labels(doc: object) -> tuple[LabelProblem, ...]:
    """Every problem of one Full Tag label document; empty when it is valid."""
    validator = _Validator()
    validator.document(doc)
    return tuple(validator.problems)


def used_facets(doc: object) -> frozenset[str]:
    """The shot facets a (valid or not) label document carries values for."""
    found: set[str] = set()
    if not isinstance(doc, Mapping) or not isinstance(doc.get("rallies"), list):
        return frozenset()
    for rally in doc["rallies"]:
        events = rally.get("events") if isinstance(rally, Mapping) else None
        for event in events if isinstance(events, list) else ():
            facets = event.get("facets") if isinstance(event, Mapping) else None
            if isinstance(facets, Mapping):
                found.update(k for k in facets if k in SHOT_FACETS)
    return frozenset(found)
