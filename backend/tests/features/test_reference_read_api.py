"""API binding of tests/features/reference_read_api.feature (ST-170b; FR-170.R4, NFR-050.10).

Each scenario writes a reference tree in a temporary folder (the ST-170a builders, so the lock
digest is the test's own), points the app at it and calls the real routes as a signed-in or
anonymous user on the committed database. Written red first: before ST-170b no route serves a
reference set, so the happy path answers 404.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx
import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from tests.support.api import ApiDriver
from tests.support.no_store import cache_control
from tests.support.reference_api import (
    CURRENT,
    LABELS,
    WRITE_METHODS,
    entry_url,
    point_at,
    without_support_ref,
)
from tests.support.references import SET, entry, reference_doc, write_version

scenarios("reference_read_api.feature")

DRAFT = "REF-AN09-D-BEG"
REVIEWED = "REF-AN09-D-INT"


@pytest.fixture
def ctx() -> dict[str, Any]:
    return {}


@given(parsers.parse('reference set "{name}" v1 with 3 coach-reviewed entries and 1 draft entry'))
def three_reviewed_one_draft(name: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    assert name == SET
    root = tmp_path / "references"
    entries = [
        entry(),
        entry(id="REF-AN09-D-ADV", level_band="advanced", band=[0.5, 0.75]),
        entry(id="REF-AN13-D-INT", pattern_id="AN-13", better_direction="higher",
              source={"citation_id": "SRC-0001"}, band=[4, 8]),
        entry(id=DRAFT, level_band="beginner", status="draft"),
    ]  # fmt: skip
    write_version(root, reference_doc(entries))
    point_at(monkeypatch, root)


@when(parsers.parse('"{user}" reads the current reference set'))
def read_current(api: ApiDriver, ctx: dict[str, Any], user: str) -> None:
    ctx["response"] = api.request(user, "GET", CURRENT)


@when(parsers.parse('"{user}" reads the draft entry by id'))
def read_draft(api: ApiDriver, ctx: dict[str, Any], user: str) -> None:
    ctx["response"] = api.request(user, "GET", entry_url(DRAFT))
    ctx["unknown"] = api.request(user, "GET", entry_url("REF-AN99-D-INT"))
    ctx["control"] = api.request(user, "GET", entry_url(REVIEWED))


@when(parsers.parse('"{user}" sends POST, PUT, PATCH and DELETE to a reviewed entry'))
def write_attempts(api: ApiDriver, ctx: dict[str, Any], user: str) -> None:
    ctx["answers"] = [
        api.request(user, method, entry_url(REVIEWED), json={"status": "verified"})
        for method in WRITE_METHODS
    ]


@then(parsers.parse("the answer is {status:d} with {count:d} entries"))
def answer_with_entries(ctx: dict[str, Any], status: int, count: int) -> None:
    response: httpx.Response = ctx["response"]
    assert response.status_code == status, response.text
    assert len(response.json()["entries"]) == count


@then("every entry has its source_type, citation, version and provenance label")
def entries_say_where_from(ctx: dict[str, Any]) -> None:
    for item in ctx["response"].json()["entries"]:
        assert item["source_type"] == "judgment"
        assert item["citation_id"] in ("SRC-0001", "SRC-0002")
        assert item["version"] == 1
        assert item["provenance_label"] == LABELS["judgment"]


@then("no entry is a draft")
def no_draft(ctx: dict[str, Any]) -> None:
    assert {e["status"] for e in ctx["response"].json()["entries"]} == {"coach-reviewed"}
    assert DRAFT not in ctx["response"].text


@then("the answer is 404 with the same body as an unknown entry id")
def draft_is_unknown(ctx: dict[str, Any]) -> None:
    assert ctx["control"].status_code == 200, ctx["control"].text  # positive control
    assert ctx["response"].status_code == ctx["unknown"].status_code == 404
    assert without_support_ref(ctx["response"].json()) == without_support_ref(ctx["unknown"].json())


@then(parsers.parse("the answer is {status:d}"))
def answer_is(ctx: dict[str, Any], status: int) -> None:
    assert ctx["response"].status_code == status, ctx["response"].text


@then('the answer says "Cache-Control: no-store"')
def no_store(ctx: dict[str, Any]) -> None:
    assert cache_control(ctx["response"].headers) == ["no-store"]


@then(parsers.parse("every answer is {status:d}"))
def every_answer(ctx: dict[str, Any], status: int) -> None:
    assert [r.status_code for r in ctx["answers"]] == [status] * len(WRITE_METHODS)
