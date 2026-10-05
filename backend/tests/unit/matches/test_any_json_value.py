"""Any JSON value in any field is a field error, never a crash (IT-02-10 finding, 2026-10-05:
an array or object in ``format``, ``ending``, ``fault_kind``, ``field`` or ``decision`` raised
``TypeError: unhashable type`` on a set or dict membership test and gave a 500).
Testing-strategy rule L11. No I/O: the parsers and commands directly."""

from __future__ import annotations

import contextlib
import datetime as dt
from typing import Any

import pytest
from hypothesis import given
from hypothesis import strategies as st

from racket.matches.domain import InvalidSetup, MatchSetup
from racket.matches.scorebook.domain import OutcomeInput
from racket.platform.errors import ValidationFailed
from tests.unit.matches.test_scorebook_corrections import fresh

pytestmark = pytest.mark.unit

JSON = st.recursive(
    st.none() | st.booleans() | st.integers() | st.floats(allow_nan=False) | st.text(max_size=5),
    lambda inner: (
        st.lists(inner, max_size=3) | st.dictionaries(st.text(max_size=3), inner, max_size=3)
    ),
    max_leaves=6,
)
UNHASHABLE = [[], {}, ["winner"], {"a": 1}]


@pytest.mark.parametrize("value", UNHASHABLE, ids=repr)
@pytest.mark.parametrize("key", ["ending", "winning_side", "responsible_player", "fault_kind"])
def test_an_unhashable_outcome_field_is_an_invalid_outcome(key: str, value: Any) -> None:
    body = {"ending": "fault", "winning_side": "A"} | {key: value}
    with pytest.raises(ValidationFailed):
        OutcomeInput.parse(body, format="doubles")


@pytest.mark.parametrize("value", UNHASHABLE, ids=repr)
@pytest.mark.parametrize("key", ["format", "scoring_system", "played_on", "title"])
def test_an_unhashable_setup_field_is_an_invalid_setup(key: str, value: Any) -> None:
    with pytest.raises(InvalidSetup):
        MatchSetup.parse({"format": "doubles"} | {key: value}, today=dt.date(2026, 10, 5))


@pytest.mark.parametrize("value", UNHASHABLE, ids=repr)
def test_an_unhashable_correction_field_or_decision_is_refused(value: Any) -> None:
    b = fresh("A")
    with pytest.raises(ValidationFailed):
        b.b.correct(b.ids[0], value, "B", expected_version=b.v, ctx=b.ctx)
    with pytest.raises(ValidationFailed):
        b.b.correct(b.ids[0], "ending", value, expected_version=b.v, ctx=b.ctx)
    with pytest.raises(ValidationFailed):
        b.b.resolve(b.ids[0], value, expected_version=b.v, ctx=b.ctx)


@given(JSON, st.sampled_from(["ending", "winning_side", "responsible_player", "fault_kind"]))
def test_any_json_value_in_an_outcome_field_is_valid_or_a_field_error(value: Any, key: str) -> None:
    body = {"ending": "fault", "winning_side": "A"} | {key: value}
    with contextlib.suppress(ValidationFailed):
        OutcomeInput.parse(body, format="doubles")
