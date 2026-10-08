"""Rule L11 on the delete confirmation, at the domain (QA-FUZZ-3; NFR-023; api-sprint-03 §4.1).

The same input domain as IT-03-12 (IT-02-10's generators): ``"delete"`` with a control,
surrogate or line/paragraph separator inside it, and any JSON value, is refused with exactly
``confirm`` / ``confirmation_required`` and never with any other exception. Pure: no network,
no disk. The rule is reached through a seam (tests/support/contract.py), so a missing module
is a red row naming the story. Written red first: ``red_until`` ST-050.
"""

from __future__ import annotations

from typing import Any

import pytest
from hypothesis import given

from tests.integration.test_it_02_10_json_string_fuzz import ANY_JSON, SETTINGS, bad_text
from tests.support.contract import Seam

pytestmark = [pytest.mark.unit, pytest.mark.red_until(story="ST-050")]

CONFIRM_DELETION = Seam(
    "racket.matches.deletion:confirm_deletion",
    "ST-050",
    "confirm_deletion(body) -> None; anything but {'confirm': 'delete'} raises ValidationFailed",
)
VALIDATION_FAILED = Seam("racket.platform.errors:ValidationFailed", "ST-005")
REFUSED = [("confirm", "confirmation_required")]


def _refusal(body: Any) -> list[tuple[Any, str]]:
    confirm, failed = CONFIRM_DELETION.load(), VALIDATION_FAILED.load()
    with pytest.raises(failed) as exc:
        confirm(body)
    return [(f.field, f.code) for f in exc.value.fields]


@pytest.mark.parametrize(
    "value",
    ["del\x00ete", "del\ud800ete", "del\udfffete", "del ete", "del ete", "del\x7fete"],
    ids=["nul", "high-surrogate", "low-surrogate", "line-separator", "para-separator", "del"],
)
def test_a_named_hidden_character_inside_the_confirmation_is_refused(value: str) -> None:
    assert _refusal({"confirm": value}) == REFUSED


@SETTINGS
@given(value=bad_text("delete"))
def test_any_hidden_character_inside_the_confirmation_is_refused(value: str) -> None:
    assert _refusal({"confirm": value}) == REFUSED


@SETTINGS
@given(value=ANY_JSON)
def test_any_json_value_is_refused_as_not_confirmed(value: Any) -> None:
    if value == "delete":
        return  # the valid value; the positive control below covers it
    assert _refusal({"confirm": value}) == REFUSED


def test_positive_control_the_typed_confirmation_is_accepted() -> None:
    CONFIRM_DELETION.load()({"confirm": "delete"})
