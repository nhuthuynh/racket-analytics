"""Steps for tests/features/upload_resume_core.feature (ST-008; NFR-026, NFR-053;
AQS/STACK-06 tus 1.0.0; AQS/SEC-02 generated object keys)."""

from __future__ import annotations

from typing import Any

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from tests.support import contract, tus
from tests.support.api import ApiDriver
from tests.support.flows import create_match, percent
from tests.support.paths import SYNTHETIC_CLIP

pytestmark = pytest.mark.red_until(story="ST-008")

scenarios("upload_resume_core.feature")

DATA = SYNTHETIC_CLIP.read_bytes()[: 256 * 1024]  # protocol behaviour does not need the full clip


@pytest.fixture
def ctx() -> dict[str, Any]:
    return {}


def _start(
    api: ApiDriver, ctx: dict[str, Any], filename: str = "clip.mp4", data: bytes = DATA
) -> None:
    ivy = api.as_user("ivy")
    match_id = api.run(create_match(ivy, "Resume test"))
    ctx["data"] = data
    ctx["upload"] = api.run(tus.start(ivy, match_id, len(data), filename=filename))


def _patch(api: ApiDriver, ctx: dict[str, Any], at: int, end: int) -> Any:
    return api.run(tus.patch(api.as_user("ivy"), ctx["upload"], at, ctx["data"][at:end]))


@given("Ivy has started an upload and the server has stored 40% of it")
@given("the server has stored 40% of Ivy's upload")
def stored_40(api: ApiDriver, ctx: dict[str, Any]) -> None:
    _start(api, ctx)
    response = _patch(api, ctx, 0, percent(40, len(ctx["data"])))
    assert response.status_code == 204, response.text


@when("her client asks the server for the current offset", target_fixture="reported")
def ask_offset(api: ApiDriver, ctx: dict[str, Any]) -> int:
    return api.run(tus.offset(api.as_user("ivy"), ctx["upload"]))


@then("the server reports the offset at 40%")
def offset_40(ctx: dict[str, Any], reported: int) -> None:
    assert reported == percent(40, len(ctx["data"]))


@then("sending the rest from that offset completes the upload")
def send_rest(api: ApiDriver, ctx: dict[str, Any], reported: int) -> None:
    response = _patch(api, ctx, reported, len(ctx["data"]))
    assert response.status_code == 204, response.text
    assert int(response.headers["Upload-Offset"]) == len(ctx["data"])
    assert api.run(tus.offset(api.as_user("ivy"), ctx["upload"])) == len(ctx["data"])


@when("her client sends a chunk that starts at 30%", target_fixture="conflict")
def wrong_offset(api: ApiDriver, ctx: dict[str, Any]) -> Any:
    at = percent(30, len(ctx["data"]))
    return _patch(api, ctx, at, percent(60, len(ctx["data"])))


@then("the chunk is refused as a conflict")
def refused_409(conflict: Any) -> None:
    assert conflict.status_code == 409


@then("the stored upload is still at 40%")
def still_40(api: ApiDriver, ctx: dict[str, Any]) -> None:
    assert api.run(tus.offset(api.as_user("ivy"), ctx["upload"])) == percent(40, len(ctx["data"]))


@given(parsers.parse('Ivy uploads a file named "{filename}"'))
def upload_named(api: ApiDriver, ctx: dict[str, Any], filename: str) -> None:
    store = contract.OBJECT_STORE.load().from_settings()
    ctx["keys_before"] = set(store.list_keys())
    ctx["filename"] = filename
    _start(api, ctx, filename=filename)


@when("the upload completes")
def completes(api: ApiDriver, ctx: dict[str, Any]) -> None:
    api.run(tus.send_all(api.as_user("ivy"), ctx["upload"], ctx["data"], chunks=2))


@then("the stored object name contains none of the original file name")
def key_is_generated(ctx: dict[str, Any]) -> None:
    store = contract.OBJECT_STORE.load().from_settings()
    new_keys = set(store.list_keys()) - ctx["keys_before"]
    assert new_keys, "no object was stored"
    fragments = {"..", "etc", "passwd", "passwd.mp4", ctx["filename"]}
    for key in new_keys:
        assert not any(f in key for f in fragments), key
