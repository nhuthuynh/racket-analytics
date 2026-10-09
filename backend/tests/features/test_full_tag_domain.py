"""Binds tests/features/full_tag_domain.feature (ST-052a; FR-150, FR-151).

Pure domain: ``racket.dataset.full_tag`` and the ``full-tag-labels/v1`` validator of
``racket.dataset.labels``; no API and no database. The route-level view of the same rules is
``full_tag.feature`` (QA-ACC-3, red until ST-052c).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from racket.dataset.full_tag import (
    Access,
    ConsentRecord,
    FullTagSession,
    InvalidConsent,
    LabelRefused,
    decide_access,
)
from racket.dataset.labels import LABEL_SCHEMA, validate_labels

scenarios("full_tag_domain.feature")

AT = datetime(2026, 10, 9, 9, 0, tzinfo=UTC)
PLAYERS = ("A1", "A2", "B1", "B2")
ANSWERS = {"not available": Access.NOT_AVAILABLE, "no consent": Access.NO_CONSENT,
           "allowed": Access.ALLOWED}  # fmt: skip


def _frame(text: str) -> int:
    return int(text.replace(",", ""))


@pytest.fixture
def ctx() -> dict[str, Any]:
    return {}


@given(parsers.parse('match "{match_id}" has a team-held consent record'))
def consented(ctx: dict[str, Any], match_id: str) -> None:
    ctx["consent"] = ConsentRecord.create(match_id, "CONSENT-TEAM-SYNTHETIC-001", "acct-9f2", AT)


@when(parsers.parse('a player who is not a labeller asks for Full Tag on match "{match_id}"'))
def player_asks(ctx: dict[str, Any], match_id: str) -> None:
    ctx["access"] = decide_access(is_labeller=False, match_id=match_id, consent=ctx["consent"])


@when(parsers.parse('a labeller asks for Full Tag on match "{match_id}"'))
def labeller_asks(ctx: dict[str, Any], match_id: str) -> None:
    ctx["access"] = decide_access(is_labeller=True, match_id=match_id, consent=ctx["consent"])


@then(parsers.parse('the answer is "{answer}"'))
def answer_is(ctx: dict[str, Any], answer: str) -> None:
    assert ctx["access"] is ANSWERS[answer]


@when(
    parsers.parse(
        'a consent record for match "{match_id}" is made with the reference "{reference}"'
    )
)
def make_consent(ctx: dict[str, Any], match_id: str, reference: str) -> None:
    with pytest.raises(InvalidConsent) as refused:
        ConsentRecord.create(match_id, reference, "acct-9f2", AT)
    ctx["refusal"] = str(refused.value)


@then("the consent record is refused because it must be a code")
def consent_refused(ctx: dict[str, Any]) -> None:
    assert "a code, never a name or an address" in ctx["refusal"]


@given(
    parsers.parse(
        "a labeller has marked a rally from frame {start} to {end} on a {count}-frame clip"
    )
)
def marked_rally(ctx: dict[str, Any], start: str, end: str, count: str) -> None:
    session = FullTagSession("match:7b1f", 60, _frame(count), PLAYERS)
    ctx["session"] = session.add({
        "type": "rally", "start_frame": _frame(start), "end_frame": _frame(end),
        "outcome": {"ending": "winner", "winning_side": "B", "responsible_player": "B1",
                    "fault_kind": None},
    })  # fmt: skip


@when(parsers.parse('they tag a hit by player "{player}" at frame {frame}'))
def tag_hit(ctx: dict[str, Any], player: str, frame: str) -> None:
    try:
        ctx["session"] = ctx["session"].add(
            {"type": "hit", "frame": _frame(frame), "hitter": player}
        )
    except LabelRefused as refused:
        ctx["refusal"] = str(refused)


@then(parsers.parse('the label is refused naming "{text}"'))
def label_refused(ctx: dict[str, Any], text: str) -> None:
    assert text in ctx.get("refusal", "")


def _hits(doc: dict[str, Any]) -> list[dict[str, Any]]:
    return [e for r in doc["rallies"] for e in r["events"] if e["type"] == "hit"]


@then("the export is valid against full-tag-labels/v1 with no hit")
def export_valid_without_hit(ctx: dict[str, Any]) -> None:
    doc = ctx["session"].export()
    assert doc["schema"] == LABEL_SCHEMA
    assert validate_labels(doc) == ()
    assert _hits(doc) == []


@then(
    parsers.parse(
        'the export is valid against full-tag-labels/v1 and holds a hit by "{player}" at '
        "frame {frame:d}"
    )
)
def export_holds_hit(ctx: dict[str, Any], player: str, frame: int) -> None:
    assert "refusal" not in ctx
    doc = ctx["session"].export()
    assert doc["schema"] == LABEL_SCHEMA
    assert validate_labels(doc) == ()
    assert [(h["hitter"], h["frame"]) for h in _hits(doc)] == [(player, frame)]
