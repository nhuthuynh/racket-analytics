"""The JSON Schema subset checker behind ``schema.json`` (ST-053; decision-log 2026-10-07)."""

from __future__ import annotations

from typing import Any

import pytest

from racket.coaching.drills.schema_check import drill_schema, errors, unsupported_keywords

pytestmark = pytest.mark.unit


def test_a_keyword_the_checker_does_not_enforce_is_refused() -> None:
    schema = {"type": "object", "properties": {"a": {"type": "string", "format": "email"}}}
    assert unsupported_keywords(schema) == ["/properties/a/format"]


def test_the_shipped_schema_uses_only_enforced_keywords() -> None:
    assert unsupported_keywords(drill_schema()) == []


@pytest.mark.parametrize(
    ("value", "schema", "expected"),
    [
        (True, {"type": "integer"}, ["(document): must be integer"]),
        (3, {"type": "integer", "maximum": 2}, ["(document): must be <= 2"]),
        ([1, 1], {"type": "array", "uniqueItems": True}, ["(document): items must be unique"]),
        ("x", {"enum": ["y"]}, ["(document): must be one of y"]),
        ({}, {"type": "object", "required": ["a"]}, ["a: required"]),
        ({"a": {"b": 1}}, {"properties": {"a": {"required": ["c"]}}}, ["a.c: required"]),
        (["ab"], {"items": {"pattern": "^a$"}}, ["[0]: does not match ^a$"]),
    ],
)
def test_errors_name_the_path(value: Any, schema: dict[str, Any], expected: list[str]) -> None:
    assert list(errors(value, schema)) == expected


def test_a_valid_value_has_no_errors() -> None:
    schema = {"type": "array", "minItems": 1, "items": {"type": "string", "minLength": 1}}
    assert list(errors(["a"], schema)) == []
