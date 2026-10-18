"""Plan API request and response schemas (ST-061b; api-sprint-04 §2.1, §2.3).

* ``parse_preferences`` checks a ``POST /me/plan`` body field by field and returns the domain's
  ``Preferences``, or raises ``ValidationFailed`` with one closed code per field (``required``,
  ``invalid``, ``out_of_range``, ``unknown_value``, ``duplicate``; an unknown key is
  ``{"field": null, "code": "unknown_field"}``). Input is never echoed (NFR-058).
* ``PreferencesIn`` documents the same closed body in OpenAPI; the route does not use it to parse,
  because Pydantic's errors cannot carry the contract's field codes.
* ``plan_body`` renders a saved, cited plan (``PlanView``) as the §2.3 representation: rallies
  lost per game rounded to 2 places, proportions to 4 (coaching-plan §6 step 4).
* ``parse_op_id`` checks the ``Idempotency-Key`` of ``POST .../done`` (ST-062; api-sprint-04 §3.1).
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from fractions import Fraction
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from racket.coaching.plan.domain import CitedPlan, Preferences
from racket.coaching.plan.domain.model import LEVELS, MIN_SESSION, NEEDS
from racket.coaching.plan.repository import StoredPlan
from racket.coaching.weakness.domain import WeaknessRanking
from racket.platform.errors import FieldError, ValidationFailed

UNOFFICIAL_LABEL = "unofficial scoring (rules not yet verified)"  # FR-055, as GET stats
MAX_MINUTES = 180
MAX_SESSIONS = 7
MAX_WEEKLY = MAX_SESSIONS * MAX_MINUTES  # judgment: no budget can use more (decisions ST-061b)
_INTEGERS = {
    "minutes_per_session": (MIN_SESSION, MAX_MINUTES),
    "sessions_per_week": (1, MAX_SESSIONS),
    "players_available": (1, 4),
}
# api-sprint-04 §2.1 table order; every field but weekly_minutes is required
FIELDS = (
    "minutes_per_session",
    "sessions_per_week",
    "weekly_minutes",
    "players_available",
    "equipment",
    "level",
)
OPTIONAL = frozenset({"weekly_minutes"})
OP_ID_HEADER = "Idempotency-Key"
_OP_ID = re.compile(r"[A-Za-z0-9_-]{1,64}")


def parse_op_id(header: str | None) -> str:
    """The client's op id: 1-64 characters ``A-Z a-z 0-9 - _`` (api-sprint-04 §3.1)."""
    if not header:
        raise ValidationFailed("done op id", [FieldError(OP_ID_HEADER, "required")])
    if _OP_ID.fullmatch(header) is None:
        raise ValidationFailed("done op id", [FieldError(OP_ID_HEADER, "invalid")])
    return header


class PreferencesIn(BaseModel):
    """OpenAPI only: the closed ``POST /me/plan`` body (api-sprint-04 §2.1)."""

    model_config = ConfigDict(extra="forbid")

    minutes_per_session: int = Field(ge=MIN_SESSION, le=MAX_MINUTES)
    sessions_per_week: int = Field(ge=1, le=MAX_SESSIONS)
    weekly_minutes: int | None = Field(
        default=None,
        le=MAX_WEEKLY,
        description="Default minutes_per_session x sessions_per_week; at least 15 per session",
    )
    players_available: int = Field(ge=1, le=4)
    equipment: list[Literal["wall", "half_court", "full_court", "ball_machine", "partner_feeder"]]
    level: Literal["beginner", "intermediate", "advanced"]


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _code(name: str, value: Any, body: Mapping[str, Any]) -> str | None:
    """The field code of one present field, None when it is valid."""
    if name in _INTEGERS:
        low, high = _INTEGERS[name]
        if not _is_int(value):
            return "invalid"
        return None if low <= value <= high else "out_of_range"
    if name == "weekly_minutes":
        if value is None:
            return None
        if not _is_int(value):
            return "invalid"
        # The floor counts sessions_per_week only when it is valid; else one session, so an
        # invalid sessions_per_week gets its own code and none here (QA-ST061b-R2-01).
        sessions: Any = body.get("sessions_per_week")
        valid = _is_int(sessions) and _code("sessions_per_week", sessions, body) is None
        floor = MIN_SESSION * (int(sessions) if valid else 1)
        return None if floor <= value <= MAX_WEEKLY else "out_of_range"
    if name == "equipment":
        if not isinstance(value, list) or not all(isinstance(x, str) for x in value):
            return "invalid"
        if not set(value) <= NEEDS:
            return "unknown_value"
        return "duplicate" if len(set(value)) != len(value) else None
    if not isinstance(value, str):
        return "invalid"
    return None if value in LEVELS else "unknown_value"


def parse_preferences(body: Any) -> Preferences:
    if not isinstance(body, dict):
        raise ValidationFailed("plan preferences", [FieldError(None, "invalid")])
    found = [FieldError(None, "unknown_field")] if set(body) - set(FIELDS) else []
    for name in FIELDS:
        if name not in body:
            code = None if name in OPTIONAL else "required"
        else:
            code = _code(name, body[name], body)
        if code is not None:
            found.append(FieldError(name, code))
    if found:
        raise ValidationFailed("plan preferences", found)
    return Preferences(
        minutes_per_session=body["minutes_per_session"],
        sessions_per_week=body["sessions_per_week"],
        players_available=body["players_available"],
        equipment=frozenset(body["equipment"]),
        level=body["level"],
        weekly_minutes=body.get("weekly_minutes"),
    )


@dataclass(frozen=True, slots=True)
class PlanView:
    """What ``GET``/``POST /me/plan`` answers: the saved plan with its ids, the ranking it was
    built from, its citations and the library's drill names."""

    stored: StoredPlan
    ranking: WeaknessRanking
    cited: CitedPlan
    drill_names: Mapping[str, str]
    regenerated: str | None = None


def _per_game(x: Fraction) -> float:
    return float(round(x, 2))


def _time(at: datetime | None) -> str | None:
    if at is None:
        return None
    return at.astimezone(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def _ranking(r: WeaknessRanking) -> dict[str, Any]:
    return {
        "unit": r.unit,
        "side_out_verified": r.side_out_verified,
        "games": r.games,
        "rallies": r.rallies,
        "skipped_matches": r.skipped_matches,
        "weaknesses": [
            {
                "id": w.id,
                "name": w.name,
                "metric_id": w.metric_id,
                "rank": w.rank,
                "per_game": _per_game(w.per_game),
                "on_serve_per_game": _per_game(w.on_serve_per_game),
                "on_receive_per_game": _per_game(w.on_receive_per_game),
                "conceded_per_game": _per_game(w.conceded_per_game),
            }
            for w in r.weaknesses
        ],
    }


def _citation(c: Any) -> dict[str, Any]:
    value = round(c.value, 2) if c.metric_id == "AN-04" else round(c.value, 4)
    return {
        "metric_id": c.metric_id,
        "metric_version": c.metric_version,
        "side": c.evidence[0].side if c.evidence else None,
        "value": float(value),
        "n": c.n,
        "k": c.k,
        "low_sample": c.low_sample,
        "rally_ids": [r.rally_id for r in c.rally_ids],
        "evidence": [{"match_id": e.match_id, "side": e.side, "n": e.n} for e in c.evidence],
    }


def plan_body(view: PlanView) -> dict[str, Any]:
    stored, plan = view.stored, view.stored.plan
    shape = [len(s.assignments) for s in plan.sessions]
    if [len(s.assignment_ids) for s in stored.sessions] != shape:
        raise ValueError(f"plan {stored.id}: stored ids do not match its sessions")
    sessions = []
    for ids, s, cited in zip(stored.sessions, plan.sessions, view.cited.sessions, strict=True):
        assignments = []
        for assignment_id, x in zip(ids.assignment_ids, cited, strict=True):
            d = x.assignment.drill
            assignments.append(
                {
                    "id": str(assignment_id),
                    "position": x.assignment.position,
                    "drill": {
                        "id": d.id,
                        "version": d.version,
                        "name": view.drill_names.get(d.ref, d.id),
                        "players": d.players,
                        "needs": sorted(d.needs),
                        "skills": sorted(d.skills),
                    },
                    "minutes": x.assignment.minutes,
                    "weakness_id": x.assignment.weakness_id,
                    "warm_up": x.assignment.weakness_id is None,
                    "citation": _citation(x.citation),
                    "why": x.why,
                }
            )
        sessions.append(
            {
                "id": str(ids.id),
                "week": s.week,
                "index": s.index,
                "minutes_budget": s.minutes_budget,
                "done": ids.done_at is not None,
                "done_at": _time(ids.done_at),
                "assignments": assignments,
            }
        )
    p = plan.preferences
    drills = [x.drill for s in plan.sessions for x in s.assignments]
    limited = view.cited.limited_data
    return {
        "id": str(stored.id),
        "version": plan.version,
        "created_at": _time(stored.created_at),
        "content_digest": view.cited.content_digest(),
        "library_version": plan.library_version,
        "regenerated": view.regenerated,
        "unofficial": not view.ranking.side_out_verified,  # as GET stats until P7
        "label": UNOFFICIAL_LABEL,
        "drills_verified": all(d.review_status == "verified" for d in drills),
        "preferences": {
            "minutes_per_session": p.minutes_per_session,
            "sessions_per_week": p.sessions_per_week,
            "weekly_minutes": p.weekly_total,
            "players_available": p.players_available,
            "equipment": sorted(p.equipment),
            "level": p.level,
        },
        "ranking": _ranking(view.ranking),
        "limited_data": None if limited is None else {"rallies": limited.rallies},
        "unfitted": [{"weakness_id": u.weakness_id, "reason": u.reason} for u in plan.unfitted],
        "sessions": sessions,
    }
