"""QA-VERIFY04R5-01 unit tests (DEMO-1.1): the pure age-gate step behind `make demo`.

No I/O. With ``FEATURE_AGE_GATE`` on, a dev user that never answered the age question gets
403 ``age_confirmation_required`` on ``GET /me`` (FR-003, api-sprint-04 §4). The demo then
answers through ``POST /me/age-confirmation`` with the closed body ``{"is_adult": true}``, as the
player does in the web app; it never writes ``age_confirmed_at`` itself. Negative cases first.
"""

from __future__ import annotations

import importlib.util
import sys
from typing import Any

import pytest
from conftest import SCRIPTS_DIR

pytestmark = pytest.mark.unit


def _plan() -> Any:
    spec = importlib.util.spec_from_file_location("demoplan", SCRIPTS_DIR / "demo" / "demoplan.py")
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["demoplan"] = module
    spec.loader.exec_module(module)
    return module


plan = _plan()


def _error(code: str) -> dict[str, Any]:
    return {"error": {"code": code, "message": code}}


# ---------------------------------------------------------------- not an answer to act on
@pytest.mark.parametrize(
    ("status", "body"),
    [
        (401, _error("unauthenticated")),  # the dev sign-in did not hold
        (403, _error("under_age")),  # a refused answer: never answer for the user again
        (403, None),
        (403, {"error": "age_confirmation_required"}),  # not the error envelope
        (404, _error("not_found")),
        (500, _error("internal")),
    ],
)
def test_any_other_answer_to_get_me_is_a_value_error(status: int, body: Any) -> None:
    with pytest.raises(ValueError, match=f"GET /me: HTTP {status}"):
        plan.needs_age_confirmation(status, body)


def test_a_200_without_an_account_id_is_a_value_error() -> None:
    with pytest.raises(ValueError, match="no account id"):
        plan.needs_age_confirmation(200, {"display_name": "Ivy"})


# ---------------------------------------------------------------- the two expected answers
def test_an_age_gated_session_needs_the_confirmation() -> None:
    assert plan.needs_age_confirmation(403, _error("age_confirmation_required")) is True


def test_an_admitted_session_needs_nothing_flags_off_or_already_confirmed() -> None:
    assert plan.needs_age_confirmation(200, {"id": "u-1", "display_name": "Ivy"}) is False


def test_the_age_answer_is_the_closed_adult_body_and_a_fresh_dict_per_call() -> None:
    first = plan.age_answer()
    assert first == {"is_adult": True}
    first["confirm"] = "delete"
    assert plan.age_answer() == {"is_adult": True}
