"""API-level binding of tests/features/match_setup.feature (ST-016; sprint-01 §7.3, §14.3.4).

Binds "Wrong participants for the format" and "Rally scoring is not yet available" through
POST /matches; the browser spec web/e2e/sprint-01/match-setup.spec.ts binds every scenario with
the on-screen copy. Field codes map to the copy in tests/support/copy.py (api-sprint-01 §5.3).
Written before ST-016: RED until it lands.
"""

from __future__ import annotations

from typing import Any

import pytest
from pytest_bdd import given, parsers, scenario, then, when

from tests.support import contract
from tests.support.api import ApiDriver
from tests.support.copy import FIELD_COPY, field_messages

pytestmark = pytest.mark.red_until(story="ST-016")

FEATURE = "match_setup.feature"
NAMES = {"A1": "Ivy", "A2": "Dana", "B1": "Carlos", "B2": "Sam"}


@scenario(FEATURE, "Wrong participants for the format")
def test_wrong_participants_for_the_format() -> None:
    """[API]"""


@scenario(FEATURE, "Rally scoring is not yet available")
def test_rally_scoring_is_not_yet_available() -> None:
    """[API]"""


@pytest.fixture
def ctx() -> dict[str, Any]:
    return {}


@given(parsers.parse("Ivy is setting up a {fmt} match"))
def setting_up(ctx: dict[str, Any], fmt: str) -> None:
    ctx["format"] = fmt


def _entered(fmt: str, entered: str) -> list[dict[str, Any]]:
    slots = {"doubles": ["A1", "A2", "B1", "B2"], "singles": ["A1", "B1", "A2"]}[fmt]
    if entered == "three nicknames":
        chosen, me = slots[:3], {"A1"}
    elif entered == 'four nicknames with two marked "me"':
        chosen, me = slots[:4], {"A1", "B1"}
    else:
        raise AssertionError(f"unknown entry {entered!r}")
    return [{"slot": s, "nickname": NAMES[s], "is_me": s in me} for s in chosen]


@when(parsers.parse("she enters {entered}"))
def she_enters(api: ApiDriver, ctx: dict[str, Any], entered: str) -> None:
    body = {"format": ctx["format"], "participants": _entered(ctx["format"], entered)}
    ctx["response"] = api.request("ivy", "POST", contract.MATCHES, json=body)


@then(parsers.parse('she sees an error summary saying "{message}"'))
def error_summary(ctx: dict[str, Any], message: str) -> None:
    assert ctx["response"].status_code == 422, ctx["response"].text
    assert message in field_messages(ctx["response"])


@given('Ivy is on the "scoring system" question')
def on_scoring_question(ctx: dict[str, Any]) -> None:
    ctx["format"] = "doubles"


@then("she can choose side-out scoring")
def can_choose_side_out(api: ApiDriver, ctx: dict[str, Any]) -> None:
    body = {"format": ctx["format"], "scoring_system": "side_out"}
    assert api.request("ivy", "POST", contract.MATCHES, json=body).status_code == 201


@then("rally scoring is shown as provisional and cannot be chosen")
def rally_refused(api: ApiDriver, ctx: dict[str, Any]) -> None:
    body = {"format": ctx["format"], "scoring_system": "rally"}
    ctx["response"] = api.request("ivy", "POST", contract.MATCHES, json=body)
    assert ctx["response"].status_code == 422


@then("she is told it becomes available once the rules are verified")
def told_why(ctx: dict[str, Any]) -> None:
    assert FIELD_COPY["scoring_system_unavailable"] in field_messages(ctx["response"])
