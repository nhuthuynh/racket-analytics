"""Data-classification map checks (ST-077; NFR-063.1-.2; IT-05-05 is the live walk).

Negative cases first (sprint-05 §5): a planted unclassified column, a planted unclassified
backup artefact and zero backup artefacts found are each reported; then the NFR-063.2 rule
that every class and every row has an encryption, a retention and an access rule.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

from tests.support.classification import (
    NO_BACKUP_ARTEFACT,
    backup_problems,
    incomplete,
    parse_map,
    prefixes,
    server_side_returned,
    stale,
    unclassified,
)

pytestmark = pytest.mark.unit

MAP = """
# Data classification

## 1. Classes

| Class | Holds | Encryption | Retention | Access |
|---|---|---|---|---|
| **High** | video | `E-S3` | `R-ORIG` | `A-OWNER` |
| **Low** | metrics | `E-PG` | `R-MATCH` | `A-OWNER` |

## 2. Rules

| Code | Kind | Rule |
|---|---|---|
| `E-PG` | encryption | Postgres volume |
| `E-S3` | encryption | bucket |
| `E-AGE` | encryption | age |
| `R-ORIG` | retention | 30 days after analysis |
| `R-MATCH` | retention | until the match is deleted |
| `R-SET` | retention | under 5 days |
| `A-OWNER` | access | the owner |
| `A-OPS` | access | operator |

## 3. Inventory

| Kind | Name | Class | Encryption | Retention | Access |
|---|---|---|---|---|---|
| column | `matches.id` | Low | `E-PG` | `R-MATCH` | `A-OWNER` |
| column | `matches.title` | High | `E-PG` | `R-MATCH` | `A-OWNER` |
| prefix | `originals/` | High | `E-S3` | `R-ORIG` | `A-OWNER` |
| backup | `db.dump.age` | High | `E-AGE` | `R-SET` | `A-OPS` |
"""


def found_columns(*names: str) -> set[tuple[str, str]]:
    return {("column", n) for n in names}


# ---------------------------------------------------------------- negatives first
def test_a_planted_unclassified_column_is_reported() -> None:
    cmap = parse_map(MAP)

    missing = unclassified(cmap, found_columns("matches.id", "matches.planted_secret"))

    assert missing == [("column", "matches.planted_secret")]


def test_a_planted_unclassified_backup_artefact_is_reported() -> None:
    cmap = parse_map(MAP)

    problems = backup_problems(cmap, {("backup", "db.dump.age"), ("backup", "plain.sql")})

    assert problems == ["unclassified backup artefact: plain.sql"]


def test_zero_backup_artefacts_found_is_a_failure_never_an_empty_pass() -> None:
    assert backup_problems(parse_map(MAP), set()) == [NO_BACKUP_ARTEFACT]


def test_an_empty_map_classifies_nothing() -> None:
    missing = unclassified(parse_map(""), found_columns("matches.id"))

    assert missing == [("column", "matches.id")]


def test_a_map_row_for_a_column_that_no_longer_exists_is_stale() -> None:
    assert stale(parse_map(MAP), found_columns("matches.id"), "column") == [
        ("column", "matches.title")
    ]


def test_a_row_with_an_unknown_class_or_rule_code_is_incomplete() -> None:
    broken = MAP + (
        "| column | `matches.notes` | Medium | `E-PG` | `R-MATCH` | `A-OWNER` |\n"
        "| column | `matches.format` | Low | `E-PG` | `R-NEVER` | `A-OWNER` |\n"
        "| column | `matches.owner_id` | Low | `R-MATCH` | `R-MATCH` | `A-OWNER` |\n"
    )

    assert incomplete(parse_map(broken)) == [
        "matches.notes: class 'Medium' is not defined",
        "matches.format: retention 'R-NEVER' is not a defined retention rule",
        "matches.owner_id: encryption 'R-MATCH' is not a defined encryption rule",
    ]


def test_a_class_without_a_retention_rule_is_incomplete() -> None:
    broken = MAP.replace(
        "| **Low** | metrics | `E-PG` | `R-MATCH` |", "| **Low** | metrics | `E-PG` | |"
    )

    assert incomplete(parse_map(broken)) == [
        "class Low: retention '' is not a defined retention rule"
    ]


def test_an_unknown_kind_in_the_inventory_is_incomplete() -> None:
    broken = MAP + "| table | `matches` | Low | `E-PG` | `R-MATCH` | `A-OWNER` |\n"

    assert incomplete(parse_map(broken)) == [
        "matches: kind 'table' is not one of column, prefix, backup"
    ]


SERVER_MAP = MAP + (
    "| column | `uploads.file_name` | High | `E-PG` | `R-MATCH` | `A-SERVER` |\n"
    "| column | `uploads.offset` | Low | `E-PG` | `R-MATCH` | `A-SERVER` |\n"
    "| column | `uploads.id` | Low | `E-PG` | `R-MATCH` | `A-SERVER` |\n"
    "| column | `uploads.expires_at` | Low | `E-PG` | `R-MATCH` | `A-SERVER` |\n"
    "| column | `uploads.owner_id` | Low | `E-PG` | `R-MATCH` | `A-SERVER` |\n"
    "| column | `uploads.length` | Low | `E-PG` | `R-MATCH` | `A-OWNER` |\n"
)
UPLOAD_ID = uuid.UUID("0b6f4c3e-8c1d-4a52-9d0e-6b1f2a3c4d5e")
UPLOAD_ROW = {
    "id": UPLOAD_ID,
    "owner_id": uuid.UUID("9a8b7c6d-5e4f-4a3b-8c2d-1e0f9a8b7c6d"),
    "file_name": "Sat doubles.mp4",
    "offset": 1048576,
    "length": 2097152,
    "expires_at": datetime(2026, 11, 6, 9, 30, 15, 123456, tzinfo=UTC),
    "parts": [{"n": 1}],
    "staged": True,
}


def test_a_server_side_column_the_api_returns_is_reported() -> None:
    """SPE-ST077-01: ``upload_sessions.*`` was A-SERVER, yet ``UploadOut`` returns its fields."""
    response = {
        "upload": {
            "offset": 1048576,
            "length": 2097152,
            "expires_at": "2026-11-06T09:30:15.123Z",
            "resume_url": f"/api/v1/uploads/{UPLOAD_ID}",
            "file_name": "Sat doubles.mp4",
        },
        "head": {"Upload-Offset": "1048576"},
    }

    assert server_side_returned(parse_map(SERVER_MAP), "uploads", UPLOAD_ROW, response) == [
        "uploads.expires_at is A-SERVER but the API returned it",
        "uploads.file_name is A-SERVER but the API returned it",
        "uploads.id is A-SERVER but the API returned it",
        "uploads.offset is A-SERVER but the API returned it",
    ]


def test_an_http_date_header_counts_as_returning_a_timestamp() -> None:
    response = {"head": {"Upload-Expires": "Fri, 06 Nov 2026 09:30:15 GMT"}}

    assert server_side_returned(parse_map(SERVER_MAP), "uploads", UPLOAD_ROW, response) == [
        "uploads.expires_at is A-SERVER but the API returned it"
    ]


def test_server_side_columns_the_api_does_not_return_pass() -> None:
    response = {"upload": {"length": 2097152, "state": "receiving", "is_me": True}, "n": 1}

    assert server_side_returned(parse_map(SERVER_MAP), "uploads", UPLOAD_ROW, response) == []


# ---------------------------------------------------------------- positives
def test_the_sample_map_parses_classes_rules_and_rows() -> None:
    cmap = parse_map(MAP)

    assert sorted(cmap.classes) == ["High", "Low"]
    assert cmap.classes["High"] == {
        "encryption": "E-S3",
        "retention": "R-ORIG",
        "access": "A-OWNER",
    }
    assert cmap.rules["R-SET"] == "retention"
    row = cmap.rows[("prefix", "originals/")]
    assert (row.cls, row.encryption, row.retention, row.access) == (
        "High",
        "E-S3",
        "R-ORIG",
        "A-OWNER",
    )


def test_the_sample_map_is_complete_and_classifies_its_items() -> None:
    cmap = parse_map(MAP)
    found = found_columns("matches.id", "matches.title") | {("prefix", "originals/")}

    assert incomplete(cmap) == []
    assert unclassified(cmap, found) == []
    assert backup_problems(cmap, {("backup", "db.dump.age")}) == []


def test_object_keys_reduce_to_their_first_segment() -> None:
    keys = ["originals/" + "a" * 32, "staging/" + "b" * 32 + "/" + "0" * 20, "loose"]

    assert prefixes(keys) == {("prefix", "originals/"), ("prefix", "staging/"), ("prefix", "loose")}
