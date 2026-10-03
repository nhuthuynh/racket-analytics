"""SEC-R2-01 / SEC-R2-02: tus integer headers are parsed as strict ASCII decimals.

``str.isdigit`` accepts characters that ``int`` rejects (``'²'``, the latin-1 byte 0xB2) and
``int`` refuses more than 4300 digits, so both used to escape as a 500. Every malformed value
must be a 4xx from the contract (api-sprint-00 §6.2, §6.4), never an unhandled ``ValueError``.
"""

from __future__ import annotations

import contextlib

import pytest
from hypothesis import given
from hypothesis import strategies as st

from racket.platform.errors import BadRequest, LengthRequired, PayloadTooLarge
from racket.video_ingest.service import (
    parse_content_length,
    parse_upload_length,
    parse_upload_offset,
)

pytestmark = pytest.mark.unit

LIMIT = 10_000_000_000
NOT_ASCII_DECIMAL = [
    "²",  # '²' — what the latin-1 byte 0xB2 decodes to
    "1²",
    "١٢",  # Arabic-Indic digits: isdigit() and int() both accept them
    "１",  # fullwidth 1
    "",
    " 1",
    "1 ",
    "+1",
    "-1",
    "1_000",
    "0x10",
    "1e3",
]


# ---------------------------------------------------------------- Upload-Length (POST)
@pytest.mark.parametrize("raw", [None, *NOT_ASCII_DECIMAL])
def test_upload_length_that_is_not_an_ascii_decimal_is_bad_request(raw: str | None) -> None:
    with pytest.raises(BadRequest):
        parse_upload_length(raw, LIMIT)


@pytest.mark.parametrize("raw", ["9" * 21, "9" * 5000, "1" + "0" * 4400])
def test_an_overlong_upload_length_is_too_large_not_a_crash(raw: str) -> None:
    with pytest.raises(PayloadTooLarge):
        parse_upload_length(raw, LIMIT)


def test_upload_length_accepts_a_plain_decimal_and_leading_zeros() -> None:
    assert parse_upload_length("10", LIMIT) == 10
    assert parse_upload_length("0007", LIMIT) == 7
    assert parse_upload_length("0" * 5000 + "7", LIMIT) == 7  # int() alone would raise


def test_upload_length_of_many_zeros_is_bad_request_not_a_crash() -> None:
    with pytest.raises(BadRequest):
        parse_upload_length("0" * 5000, LIMIT)


# ---------------------------------------------------------------- Upload-Offset (PATCH)
@pytest.mark.parametrize("raw", [None, *NOT_ASCII_DECIMAL, "9" * 21, "9" * 5000])
def test_upload_offset_that_is_not_a_bounded_ascii_decimal_is_bad_request(
    raw: str | None,
) -> None:
    with pytest.raises(BadRequest):
        parse_upload_offset(raw)


def test_upload_offset_accepts_zero_and_twenty_digits() -> None:
    assert parse_upload_offset("0") == 0
    assert parse_upload_offset("9" * 20) == int("9" * 20)
    assert parse_upload_offset("0" * 5000) == 0  # int() alone would raise


# ---------------------------------------------------------------- Content-Length (PATCH)
@pytest.mark.parametrize("raw", [None, *NOT_ASCII_DECIMAL])
def test_content_length_that_is_not_an_ascii_decimal_is_length_required(
    raw: str | None,
) -> None:
    with pytest.raises(LengthRequired):
        parse_content_length(raw, 64)


@pytest.mark.parametrize("raw", ["65", "9" * 21, "9" * 5000])
def test_content_length_above_the_chunk_limit_is_too_large(raw: str) -> None:
    with pytest.raises(PayloadTooLarge):
        parse_content_length(raw, 64)


def test_content_length_accepts_zero_and_the_limit() -> None:
    assert parse_content_length("0", 64) == 0
    assert parse_content_length("64", 64) == 64
    assert parse_content_length("0" * 5000 + "1", 64) == 1


# ---------------------------------------------------------------- property: never a ValueError
@given(
    st.text(max_size=64)
    | st.text(alphabet="0123456789\u00b2\u0661", max_size=6000)
    | st.integers(4290, 4400).map(lambda n: "0" * n + "9")
)
def test_any_header_text_gives_a_value_or_a_contract_error(raw: str) -> None:
    for parse in (
        lambda: parse_upload_length(raw, LIMIT),
        lambda: parse_upload_offset(raw),
        lambda: parse_content_length(raw, LIMIT),
    ):
        with contextlib.suppress(BadRequest, LengthRequired, PayloadTooLarge):
            assert parse() >= 0
