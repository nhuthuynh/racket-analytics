"""API-level binding of tests/features/upload_validation.feature (ST-018; sprint-01 §7.5,
§14.3.6). Every scenario is decided by the server; "she sees <copy>" asserts the rejection or
error code that the FE maps to that copy (tests/support/copy.py). The browser spec
web/e2e/sprint-01/upload-validation.spec.ts checks the copy on U-03. RED until ST-018.
"""

from __future__ import annotations

from typing import Any

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from tests.support import contract, media, tus_ext
from tests.support.api import ApiDriver
from tests.support.copy import ERROR_COPY
from tests.support.flows import create_match
from tests.support.worker import jobs_for_match, media_facts_count
from tests.support.written_keys import WrittenKeys

pytestmark = [pytest.mark.red_until(story="ST-018"), pytest.mark.slow]

TWELVE_GB = 12 * 1000**3
FILES = {
    "a PDF renamed to match.mp4": (media.pdf_bytes, "match.mp4", None),
    "a program renamed to match.mov": (media.executable_bytes, "match.mov", None),
    "a 12 GB video": (media.valid_clip_bytes, "match.mp4", TWELVE_GB),
    "a 4-hour video": (media.long_clip_bytes, "match.mp4", None),
    "a 1080p 60 fps MP4 recorded on a phone": (media.valid_clip_bytes, "IMG_0042.MP4", None),
}

scenarios("upload_validation.feature")


@pytest.fixture
def ctx() -> dict[str, Any]:
    return {}


def _start_upload(
    api: ApiDriver, ctx: dict[str, Any], file: str, written_keys: WrittenKeys
) -> None:
    # Recording starts before the first write; the Then steps read it from ctx, so a step
    # order that skipped this could never pass vacuously (QA-R3-02).
    ctx["written_keys"] = written_keys
    make, filename, declared = FILES[file]
    data = make()
    ivy = api.as_user("ivy")
    ctx["match_id"] = api.run(create_match(ivy, "Sat doubles"))
    created = api.run(
        tus_ext.create(ivy, ctx["match_id"], data, filename=filename, length=declared)
    )
    ctx["response"] = created
    if created.status_code == 201:
        upload = tus_ext.tus.Upload(url=created.headers["Location"], length=len(data))
        ctx["response"] = api.run(tus_ext.patch(ivy, upload, 0, data))
        contract.WORKER_RUN_UNTIL_IDLE.load()()


def _match(api: ApiDriver, ctx: dict[str, Any]) -> dict[str, Any]:
    body: dict[str, Any] = api.request(
        "ivy", "GET", contract.MATCH.format(match_id=ctx["match_id"])
    ).json()
    return body


@given(parsers.parse("Ivy selects {file}"))
def selects(ctx: dict[str, Any], file: str) -> None:
    ctx["file"] = file


@when("she starts the upload")
@when("the upload completes")
def starts_upload(api: ApiDriver, ctx: dict[str, Any], written_keys: WrittenKeys) -> None:
    _start_upload(api, ctx, ctx["file"], written_keys)


@then(parsers.parse('she sees "There is a problem" with "{message}"'))
def sees_problem(api: ApiDriver, ctx: dict[str, Any], message: str) -> None:
    rejection = _match(api, ctx)["rejection"]
    assert rejection is not None, "the match shows no rejection"
    assert ERROR_COPY[rejection["code"]] == message


@then("no match video is stored from that file")
def nothing_stored(api: ApiDriver, committed_db: Any, ctx: dict[str, Any]) -> None:
    match = _match(api, ctx)
    assert match["media"] is None
    assert ctx["written_keys"].stored() == set()
    assert media_facts_count(committed_db, ctx["match_id"]) == 0


@then(parsers.parse('the match shows the status "{label}"'))
def shows_status(api: ApiDriver, ctx: dict[str, Any], label: str) -> None:
    assert contract.STATUS_LABELS[_match(api, ctx)["status"]] == label


@given(parsers.parse("Ivy starts an upload that declares {size:d} GB"))
def declares(ctx: dict[str, Any], size: int) -> None:
    assert size * 1000**3 == TWELVE_GB
    ctx["file"] = "a 12 GB video"


@when("the server receives the upload request")
def server_receives(api: ApiDriver, ctx: dict[str, Any], written_keys: WrittenKeys) -> None:
    _start_upload(api, ctx, ctx["file"], written_keys)


@then(parsers.parse('the upload is refused with "{message}"'))
def refused_with(ctx: dict[str, Any], message: str) -> None:
    response = ctx["response"]
    assert response.status_code == 413
    assert ERROR_COPY[response.json()["error"]["code"]] == message


@then("no bytes of that file are stored")
def no_bytes(ctx: dict[str, Any]) -> None:
    assert ctx["written_keys"].stored() == set()


@given(parsers.parse('Ivy\'s file was refused as "{message}"'))
def file_refused(
    api: ApiDriver, ctx: dict[str, Any], message: str, written_keys: WrittenKeys
) -> None:
    _start_upload(api, ctx, "a PDF renamed to match.mp4", written_keys)
    assert ctx["response"].status_code == 415
    assert ERROR_COPY[ctx["response"].json()["error"]["code"]] == message


@when("she opens the match")
def opens_match(api: ApiDriver, ctx: dict[str, Any]) -> None:
    ctx["match"] = _match(api, ctx)


@then('the match shows "No video yet"')
def no_video_yet(ctx: dict[str, Any]) -> None:
    assert ctx["match"]["status"] == "awaiting_upload"
    assert ctx["match"]["media"] is None
    assert ctx["match"]["upload"] is None


@then("no video check was started for that file")
def no_check(committed_db: Any, ctx: dict[str, Any]) -> None:
    assert jobs_for_match(committed_db, ctx["match_id"]) == []
