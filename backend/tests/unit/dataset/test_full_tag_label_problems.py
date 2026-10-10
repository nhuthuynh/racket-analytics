"""A refused label names every problem as (label key, closed code) (ST-052c review round 1,
PE-052c-R1-02 / M2; api-sprint-03 §5.4, §6.2). Pure domain.

``LabelRefused.problems`` is what the API turns into ``error.fields``: ``field`` is the label key
(``type``, ``frame``, ``hitter``, ``facets``, ``start_frame``, ``end_frame``, ``outcome``,
``visible``, ``court_xy_m``) or ``None`` for the whole object, and ``code`` is one of ``invalid``,
``unknown_field``, ``outside_clip``, ``no_rally``, ``overlaps_rally``, ``out_of_order``,
``not_a_player``. Label values never appear in them (NFR-057).
"""

from __future__ import annotations

from typing import Any

import pytest

from racket.dataset.full_tag import LABEL_CODES, LABEL_KEYS, FullTagSession, LabelRefused

pytestmark = pytest.mark.unit

CLIP = {"clip": "match:7b1f", "fps": 60, "frame_count": 3600, "players": ("A1", "A2", "B1", "B2")}
OUTCOME = {"ending": "winner", "winning_side": "B", "responsible_player": "B1", "fault_kind": None}
RALLY = {"type": "rally", "start_frame": 1800, "end_frame": 1900, "outcome": OUTCOME}
HIT = {"type": "hit", "frame": 1840, "hitter": "B1"}


def _rally(**changes: Any) -> dict[str, Any]:
    return {**RALLY, **changes}


def _refused(body: object, *before: dict[str, Any]) -> tuple[tuple[str | None, str], ...]:
    session = FullTagSession(**CLIP)
    for earlier in before:
        session = session.add(earlier)
    with pytest.raises(LabelRefused) as refused:
        session.add(body)
    return tuple((p.field, p.code) for p in refused.value.problems)


CASES: list[tuple[str, object, tuple[dict[str, Any], ...], tuple[tuple[str | None, str], ...]]] = [
    ("not-an-object", ["hit"], (), ((None, "invalid"),)),
    ("unknown-type", {"type": "serve", "frame": 1}, (), (("type", "invalid"),)),
    ("type-not-a-string", {"type": ["hit"]}, (), (("type", "invalid"),)),
    ("unknown-key", {**HIT, "note": "x", "extra": 1}, (RALLY,), ((None, "unknown_field"),)),
    ("frame-not-a-number", {**HIT, "frame": "x"}, (RALLY,), (("frame", "invalid"),)),
    ("frame-outside-clip", {**HIT, "frame": 3600}, (RALLY,), (("frame", "outside_clip"),)),
    ("frame-in-no-rally", {**HIT, "frame": 100}, (RALLY,), (("frame", "no_rally"),)),
    ("two-hits-on-one-frame", HIT, (RALLY, HIT), (("frame", "invalid"),)),
    ("hitter-not-a-slot", {**HIT, "hitter": "Z9"}, (RALLY,), (("hitter", "not_a_player"),)),
    ("unknown-facet", {**HIT, "facets": {"spin_x": "top"}}, (RALLY,), (("facets", "invalid"),)),
    (
        "bounce-visible-not-bool",
        {"type": "bounce", "frame": 1850, "visible": "yes", "court_xy_m": None},
        (RALLY,),
        (("visible", "invalid"),),
    ),
    (
        "bounce-position-not-a-pair",
        {"type": "bounce", "frame": 1850, "visible": True, "court_xy_m": [1]},
        (RALLY,),
        (("court_xy_m", "invalid"),),
    ),
    ("rally-end-outside-clip", _rally(end_frame=3600), (), (("end_frame", "outside_clip"),)),
    (
        "rally-ends-before-it-starts",
        _rally(start_frame=1900, end_frame=1800),
        (),
        (("end_frame", "out_of_order"),),
    ),
    (
        "rally-overlaps-a-later-one",
        _rally(start_frame=1850, end_frame=1950),
        (RALLY,),
        (("start_frame", "overlaps_rally"),),
    ),
    (
        "rally-overlaps-an-earlier-one",
        _rally(start_frame=1700, end_frame=1850),
        (RALLY,),
        (("start_frame", "overlaps_rally"),),
    ),
    (
        "responsible-player-not-a-slot",
        _rally(outcome={**OUTCOME, "responsible_player": "Z9"}),
        (),
        (("outcome", "not_a_player"),),
    ),
    ("outcome-not-an-object", _rally(outcome="winner"), (), (("outcome", "invalid"),)),
    (
        "two-problems-in-one-rally",
        _rally(start_frame="a", end_frame=3600),
        (),
        (("start_frame", "invalid"), ("end_frame", "outside_clip")),
    ),
]


@pytest.mark.parametrize(
    ("body", "before", "expected"), [c[1:] for c in CASES], ids=[c[0] for c in CASES]
)
def test_a_refused_label_names_each_problem_by_label_key_and_closed_code(
    body: object,
    before: tuple[dict[str, Any], ...],
    expected: tuple[tuple[str | None, str], ...],
) -> None:
    assert _refused(body, *before) == expected


@pytest.mark.parametrize(("body", "before"), [c[1:3] for c in CASES], ids=[c[0] for c in CASES])
def test_every_problem_uses_a_contract_key_and_code_and_never_a_label_value(
    body: object, before: tuple[dict[str, Any], ...]
) -> None:
    for field, code in _refused(body, *before):
        assert field is None or field in LABEL_KEYS
        assert code in LABEL_CODES
        assert field not in ("note", "extra", "spin_x", "Z9")


def test_the_closed_sets_are_the_contracts() -> None:
    # api-sprint-03 §5.4 / §6.2, verbatim
    keys = {"type", "frame", "hitter", "facets", "start_frame", "end_frame", "outcome", "visible",
            "court_xy_m"}  # fmt: skip
    codes = {"invalid", "unknown_field", "outside_clip", "no_rally", "overlaps_rally",
             "out_of_order", "not_a_player"}  # fmt: skip
    assert frozenset(keys) == LABEL_KEYS
    assert frozenset(codes) == LABEL_CODES


def test_an_accepted_label_after_a_refusal_still_works() -> None:
    session = FullTagSession(**CLIP).add(RALLY)
    with pytest.raises(LabelRefused):
        session.add({**HIT, "hitter": "Z9"})
    assert len(session.add(HIT).events) == 1
