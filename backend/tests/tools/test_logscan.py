"""The NFR-069 log scanner finds what it must find (and is not trivially green)."""

from __future__ import annotations

from tests.support.logscan import scan


def test_email_is_found() -> None:
    leaks = scan(['{"msg": "magic link sent", "to": "ivy@example.com"}'])

    assert [(leak.kind, leak.excerpt) for leak in leaks] == [("email", "ivy@example.com")]


def test_signed_url_is_found() -> None:
    line = "GET https://s3/bucket/k?X-Amz-Credential=abc&X-Amz-Signature=deadbeef"

    assert {leak.kind for leak in scan([line])} == {"signed_url"}


def test_nickname_is_found_as_a_whole_word_only() -> None:
    lines = ['{"user": "Ivy"}', '{"msg": "activity started"}']

    assert [(leak.line_no, leak.kind) for leak in scan(lines, nicknames=["ivy"])] == [
        (1, "nickname")
    ]


def test_clean_structured_line_passes() -> None:
    line = '{"ts": "2026-10-05T10:00:00Z", "trace_id": "4bf9", "user_id": "u_9f2c", "msg": "ok"}'

    assert scan([line], nicknames=["ivy", "carlos"]) == []
