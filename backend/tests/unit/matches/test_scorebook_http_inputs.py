"""The scorebook routes' input parsing (ST-027; BE-D1-02): ``If-Match`` and the closed body.

No I/O. The routes themselves (201 with the new sheet, 409 ``stale_match`` / ``match_not_ready``,
422 ``invalid_outcome``, 404 for another owner) are IT-02-04 / IT-02-05 (QA lane).
"""

from __future__ import annotations

from typing import Any

import pytest

from racket.matches.scorebook.domain import InvalidRally, StaleMatch
from racket.matches.scorebook.service import TAG_KEYS, _object, parse_version

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("raw", [None, "", " ", "abc", "-1", "1.0", "１", "1" * 10, '"', "W/"])
def test_a_missing_or_malformed_if_match_is_a_stale_version(raw: str | None) -> None:
    with pytest.raises(StaleMatch) as exc:
        parse_version(raw)
    assert (exc.value.status, exc.value.code) == (409, "stale_match")


@pytest.mark.parametrize(("raw", "expected"), [("0", 0), ("3", 3), ('"3"', 3), ('W/"12"', 12),
                                               (" 7 ", 7)])  # fmt: skip
def test_if_match_takes_a_bare_or_quoted_version(raw: str, expected: int) -> None:
    assert parse_version(raw) == expected


@pytest.mark.parametrize("body", [None, [], "x", 3])
def test_a_body_that_is_not_an_object_is_refused(body: Any) -> None:
    with pytest.raises(InvalidRally) as exc:
        _object(body, TAG_KEYS, InvalidRally)
    assert [(f.field, f.code) for f in exc.value.fields] == [(None, "invalid")]


def test_an_unknown_key_is_refused_without_naming_it() -> None:
    with pytest.raises(InvalidRally) as exc:
        _object({"start_ms": 0, "score_after": "11-0-2"}, TAG_KEYS, InvalidRally)
    assert [(f.field, f.code) for f in exc.value.fields] == [(None, "unknown_field")]
