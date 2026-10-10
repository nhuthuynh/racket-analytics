"""Full Tag: who may label, the team-held consent record, and the label session (ST-052;
FR-150, FR-151; docs/data/gold-label-schema.md §4).

Pure domain code (ddd-guidelines §4.5): no I/O, no framework. The API adapter maps
``Access.NOT_AVAILABLE`` to 404 (a player is never told the tool exists, FR-150), and
``Access.NO_CONSENT`` and ``LabelRefused`` to 4xx with the reason.

The session holds what the labeller has marked: rallies (boundaries and outcome) and hit and
bounce events. Every command is checked against ``full-tag-labels/v1`` by building the document
it would export and running ``validate_labels`` on it, so the export can never be invalid
because of a command that was accepted. An event must fall inside a marked rally.

A refusal names each problem as a ``LabelIssue`` (label key or ``None``, closed code; api-sprint-03
§5.4, §6.2), which the API returns as ``error.fields``; label values are never in it (NFR-057).

The session owns its state: ``add`` deep-copies the body it accepts and ``export`` returns a
deep copy, so neither the caller's input nor a returned document is shared with the session.
"""

from __future__ import annotations

import copy
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, TypeGuard

from racket.dataset.labels import LABEL_SCHEMA, LabelProblem, validate_labels

_REFERENCE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,63}$")
# api-sprint-03 §5.4 / §6.2: the keys a refusal may name and its closed codes.
LABEL_KEYS = frozenset({"type", "frame", "hitter", "facets", "start_frame", "end_frame", "outcome",
                        "visible", "court_xy_m"})  # fmt: skip
LABEL_CODES = frozenset({"invalid", "unknown_field", "outside_clip", "no_rally", "overlaps_rally",
                         "out_of_order", "not_a_player"})  # fmt: skip
# the key of a rally-level problem of the validator, by its code
_RALLY_KEY = {"overlaps_rally": "start_frame", "out_of_order": "end_frame"}
_WHERE = re.compile(r"^rallies\[\d+\](?:\.events\[\d+\])?(?:\.(?P<key>[a-z_]+))?")
_FIELDS = {
    "rally": frozenset({"type", "start_frame", "end_frame", "outcome"}),
    "hit": frozenset({"type", "frame", "hitter", "facets"}),
    "bounce": frozenset({"type", "frame", "visible", "court_xy_m"}),
}


class Access(Enum):
    NOT_AVAILABLE = "not_available"  # not a labeller: the tool does not exist for them
    NO_CONSENT = "no_consent"  # a labeller, but the match has no team-held consent record
    ALLOWED = "allowed"


class InvalidConsent(ValueError):
    """A consent record that would be unsafe or incomplete to store."""


@dataclass(frozen=True, slots=True)
class LabelIssue:
    """One problem of a refused label: the label key it is about (``None``: the whole object)
    and a code from ``LABEL_CODES``. Never a label value."""

    field: str | None
    code: str


class LabelRefused(ValueError):
    """A label command the session does not accept; ``problems`` lists every problem (the
    message describes them for people and may carry values, so it is never returned)."""

    def __init__(self, message: str, *problems: LabelIssue) -> None:
        super().__init__(message)
        self.problems: tuple[LabelIssue, ...] = problems or (LabelIssue(None, "invalid"),)


def _issue(problem: LabelProblem) -> LabelIssue:
    found = _WHERE.match(problem.where)
    key = found.group("key") if found else None
    if key is None:
        key = _RALLY_KEY.get(problem.code)
    code = problem.code if problem.code in LABEL_CODES else "invalid"
    return LabelIssue(key if key in LABEL_KEYS else None, code)


class ExportInvalid(ValueError):
    """The session cannot produce a valid ``full-tag-labels/v1`` document."""


@dataclass(frozen=True, slots=True)
class ConsentRecord:
    """The team-held record that a match may be labelled (Sprint 3; training consent by the
    player, FR-009, is Sprint 4). ``reference`` points at the signed paper or file the team
    keeps outside git; it is a short code, never a name or an address."""

    match_id: str
    reference: str
    recorded_by: str  # pseudonymous account id of the labeller-admin
    recorded_at: datetime

    @classmethod
    def create(
        cls, match_id: str, reference: str, recorded_by: str, recorded_at: datetime
    ) -> ConsentRecord:
        if not match_id:
            raise InvalidConsent("match id required")
        if not _REFERENCE.match(reference):
            raise InvalidConsent(
                "consent reference must be 1-64 of A-Z a-z 0-9 . _ : - (a code, never a name "
                "or an address)"
            )
        if not recorded_by:
            raise InvalidConsent("recorded_by (pseudonymous account id) required")
        if recorded_at.tzinfo is None:
            raise InvalidConsent("recorded_at must carry a time zone")
        return cls(match_id, reference, recorded_by, recorded_at)


def decide_access(*, is_labeller: bool, match_id: str, consent: ConsentRecord | None) -> Access:
    if not is_labeller:
        return Access.NOT_AVAILABLE
    if consent is None or consent.match_id != match_id:
        return Access.NO_CONSENT
    return Access.ALLOWED


@dataclass(frozen=True, slots=True)
class FullTagSession:
    clip: str
    fps: int
    frame_count: int
    players: tuple[str, ...]
    rallies: tuple[Mapping[str, Any], ...] = field(default=())
    events: tuple[Mapping[str, Any], ...] = field(default=())

    def add(self, body: object) -> FullTagSession:
        """A new session with ``body`` (a rally, hit or bounce) added, or ``LabelRefused``."""
        if not isinstance(body, Mapping):
            raise LabelRefused("a label must be a JSON object", LabelIssue(None, "invalid"))
        kind = body.get("type")
        if not isinstance(kind, str) or kind not in _FIELDS:
            raise LabelRefused(
                f"type: must be one of {sorted(_FIELDS)}", LabelIssue("type", "invalid")
            )
        if extra := sorted(set(body) - _FIELDS[kind]):
            raise LabelRefused(
                f"unknown field(s): {', '.join(map(str, extra))}",
                LabelIssue(None, "unknown_field"),
            )
        owned = copy.deepcopy(dict(body))  # never share the caller's nested objects
        if kind == "rally":
            candidate = FullTagSession(self.clip, self.fps, self.frame_count, self.players,
                                       (*self.rallies, owned), self.events)  # fmt: skip
        else:
            event = owned
            if kind == "hit":
                event.setdefault("facets", {})
            frame = event.get("frame")
            if not _is_frame(frame):
                raise LabelRefused(
                    "frame: must be a frame number (integer >= 0)", LabelIssue("frame", "invalid")
                )
            if frame >= self.frame_count:
                raise LabelRefused(
                    f"frame: {frame} is outside the clip (0..{self.frame_count - 1})",
                    LabelIssue("frame", "outside_clip"),
                )
            if not any(_contains(r, frame) for r in self.rallies):
                raise LabelRefused(
                    f"no rally contains frame {frame}; mark the rally first",
                    LabelIssue("frame", "no_rally"),
                )
            candidate = FullTagSession(self.clip, self.fps, self.frame_count, self.players,
                                       self.rallies, (*self.events, event))  # fmt: skip
        if problems := validate_labels(candidate._document()):
            issues = tuple(dict.fromkeys(_issue(p) for p in problems))  # one per problem, in order
            raise LabelRefused("; ".join(p.describe() for p in problems), *issues)
        return candidate

    def _document(self) -> dict[str, Any]:
        rallies = sorted(self.rallies, key=_start)
        out = []
        for number, rally in enumerate(rallies, start=1):
            inside = [e for e in self.events if _contains(rally, e.get("frame"))]
            out.append({
                "id": f"r{number}",
                "start_frame": rally.get("start_frame"),
                "end_frame": rally.get("end_frame"),
                "outcome": rally.get("outcome"),
                "events": sorted(inside, key=lambda e: e["frame"]),
            })  # fmt: skip
        return {"schema": LABEL_SCHEMA, "clip": self.clip, "fps": self.fps,
                "frame_count": self.frame_count, "players": list(self.players),
                "rallies": out}  # fmt: skip

    def export(self) -> dict[str, Any]:
        """A fresh ``full-tag-labels/v1`` document; ``ExportInvalid`` if it would not validate."""
        doc = self._document()
        if problems := validate_labels(doc):
            raise ExportInvalid("; ".join(p.describe() for p in problems))
        return copy.deepcopy(doc)


def _start(rally: Mapping[str, Any]) -> int:
    start = rally.get("start_frame")
    return start if _is_frame(start) else -1


def _is_frame(value: object) -> TypeGuard[int]:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _contains(rally: Mapping[str, Any], frame: object) -> bool:
    start, end = rally.get("start_frame"), rally.get("end_frame")
    return _is_frame(frame) and _is_frame(start) and _is_frame(end) and start <= frame <= end
