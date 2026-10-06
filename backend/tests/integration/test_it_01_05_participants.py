"""IT-01-05 (ST-016; FR-005, FR-021, FR-043; ADR 0024; api-sprint-01 §5) with threat controls
T-MS-1 (no mass assignment) and T-MS-3 (validation never echoes input).

Negative cases first; the valid doubles and singles matches are the positive controls.
"""

from __future__ import annotations

import datetime as dt
from typing import Any

import pytest

from tests.support import contract
from tests.support.api import ApiDriver


def people(*slots: str, me: tuple[str, ...] = ("A1",)) -> list[dict[str, Any]]:
    names = {"A1": "Ivy", "A2": "Dana", "B1": "Carlos", "B2": "Sam"}
    return [{"slot": s, "nickname": names[s], "is_me": s in me} for s in slots]


def post(api: ApiDriver, body: dict[str, Any]) -> Any:
    return api.request("ivy", "POST", contract.MATCHES, json=body)


def fields(response: Any) -> list[tuple[Any, str]]:
    assert response.status_code == 422, response.text
    error = response.json()["error"]
    assert error["code"] == "validation_failed"
    return [(f["field"], f["code"]) for f in error["fields"]]


@pytest.mark.parametrize(
    ("body", "expected"),
    [
        (
            {"format": "doubles", "participants": people("A1", "A2", "B1")},
            ("participants.side_b", "side_needs_two_players"),
        ),
        (
            {"format": "singles", "participants": people("A1", "B1", "A2")},
            ("participants.side_a", "side_needs_one_player"),
        ),
        (
            {"format": "doubles", "participants": people("A1", "A2", "B1", "B2", me=("A1", "B1"))},
            ("participants.me", "choose_one_me"),
        ),
        (
            {"format": "doubles", "participants": people("A1", "A2", "B1", "B2", me=())},
            ("participants.me", "choose_one_me"),
        ),
        (
            {"format": "doubles", "scoring_system": "rally"},
            ("scoring_system", "scoring_system_unavailable"),
        ),
        (
            {"format": "doubles", "scoring_system": "bogus"},
            ("scoring_system", "scoring_system_invalid"),
        ),
        ({"participants": people("A1", "B1")}, ("format", "format_required")),
    ],
    ids=["doubles-3", "singles-3", "two-me", "no-me", "rally", "unknown-system", "no-format"],
)
def test_it_01_05_invalid_participants_and_systems_are_refused_with_field_errors(
    api: ApiDriver, body: dict[str, Any], expected: tuple[str, str]
) -> None:
    assert expected in fields(post(api, body))


def test_future_date_is_refused(api: ApiDriver) -> None:
    later = (dt.datetime.now(dt.UTC).date() + dt.timedelta(days=2)).isoformat()
    assert ("played_on", "played_on_in_future") in fields(
        post(api, {"format": "singles", "played_on": later})
    )


def test_all_failures_are_reported_together_in_form_order(api: ApiDriver) -> None:
    body = {
        "format": "doubles",
        "scoring_system": "rally",
        "participants": people("A1", "A2", "B1", me=("A1", "A2")),
    }
    assert [f for f, _ in fields(post(api, body))] == [
        "scoring_system",
        "participants.side_b",
        "participants.me",
    ]


@pytest.mark.parametrize(
    "key", ["rules_version", "owner_id", "status", "<script>alert(1)</script>"]
)
def test_unknown_or_server_owned_fields_are_refused_without_echo(api: ApiDriver, key: str) -> None:
    """T-MS-1 and T-MS-3."""
    response = post(api, {"format": "singles", key: "PROVISIONAL-UNVERIFIED"})
    assert (None, "unknown_field") in fields(response)
    assert key not in response.text
    assert "PROVISIONAL-UNVERIFIED" not in response.text


def test_valid_doubles_match_is_stored_with_participants_in_slot_order(api: ApiDriver) -> None:
    response = post(
        api,
        {
            "format": "doubles",
            "scoring_system": "side_out",
            "played_on": "2026-10-03",
            "participants": list(reversed(people("A1", "A2", "B1", "B2"))),
        },
    )
    assert response.status_code == 201, response.text
    match = api.request("ivy", "GET", response.headers["Location"]).json()
    assert [p["slot"] for p in match["participants"]] == ["A1", "A2", "B1", "B2"]
    assert [p["is_me"] for p in match["participants"]] == [True, False, False, False]
    assert match["rules_version"] == contract.PROVISIONAL_PRESET
    assert match["scoring_system"] == "side_out"
    assert match["title"] == "Doubles · 3 Oct 2026"


def test_valid_singles_match_is_stored(api: ApiDriver) -> None:
    response = post(api, {"format": "singles", "participants": people("A1", "B1", me=("B1",))})
    assert response.status_code == 201, response.text
    assert [p["slot"] for p in response.json()["participants"]] == ["A1", "B1"]
    assert response.json()["rules_version"] == contract.PROVISIONAL_PRESET


def test_a_nickname_that_looks_like_an_email_is_accepted(api: ApiDriver) -> None:
    """§14.3.4 / ADR 0024: a warning in the client, never a server refusal."""
    body = {"format": "singles", "participants": people("A1", "B1")}
    body["participants"][1]["nickname"] = "carlos@example.com"
    assert post(api, body).status_code == 201
    predicate = contract.PARTICIPANTS.load().looks_like_contact_details
    assert predicate("carlos@example.com") is True
    assert predicate("+61 (2) 9876-5432") is True
    assert predicate("Carlos") is False
