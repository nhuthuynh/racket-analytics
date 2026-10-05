"""API-level binding of tests/features/resumable_upload.feature (ST-017; sprint-01 §7.4, §14.3.5).

Binds the scenarios the server decides: damaged chunk, return after closing the tab (the read
model offers the resume, flows D-3), expired upload, and Carlos. The browser spec
web/e2e/sprint-01/resumable-upload.spec.ts binds every scenario, including the client-side
"different file" check and the progress wording. The "3 GB" video is the 1.7 MB fixture: the
percentages are what the scenarios assert. RED until ST-017.
"""

from __future__ import annotations

import time
from typing import Any

import pytest
from pytest_bdd import given, parsers, scenario, then, when

from tests.support import contract, tus, tus_ext
from tests.support.api import ApiDriver
from tests.support.copy import ERROR_COPY, error_code
from tests.support.flows import create_match, percent_of, percent_up
from tests.support.paths import SYNTHETIC_CLIP

pytestmark = [pytest.mark.red_until(story="ST-017"), pytest.mark.slow]

FEATURE = "resumable_upload.feature"
DATA = SYNTHETIC_CLIP.read_bytes()


@scenario(FEATURE, "A damaged chunk is not kept")
def test_a_damaged_chunk_is_not_kept() -> None:
    """[API]"""


@scenario(FEATURE, "Return after closing the tab")
def test_return_after_closing_the_tab() -> None:
    """[API] the offer comes from the server read model (D-3)."""


@scenario(FEATURE, "The unfinished upload has expired")
def test_the_unfinished_upload_has_expired() -> None:
    """[API]"""


@scenario(FEATURE, "Carlos tries to send data to Ivy's upload")
def test_carlos_tries_to_send_data_to_ivys_upload() -> None:
    """[API] also the BOLA matrix row for PATCH /uploads/{id} (IT-01-11)."""


@pytest.fixture
def ctx() -> dict[str, Any]:
    return {}


@pytest.fixture
def expiry_env(monkeypatch: pytest.MonkeyPatch, request: pytest.FixtureRequest) -> None:
    if "expired" in request.node.name:
        monkeypatch.setenv(contract.UPLOAD_EXPIRY_ENV, "1")


def _upload_to(api: ApiDriver, ctx: dict[str, Any], pct: int) -> None:
    ivy = api.as_user("ivy")
    ctx["match_id"] = api.run(create_match(ivy, "Sat doubles"))
    ctx["upload"] = api.run(tus_ext.start(ivy, ctx["match_id"], DATA, with_head=False))
    sent = percent_up(pct, len(DATA))  # lands on pct%, not 0.0001% below it (TCR row 32)
    assert api.run(tus_ext.patch(ivy, ctx["upload"], 0, DATA[:sent])).status_code == 204
    ctx["sent"] = sent


def _offset(api: ApiDriver, ctx: dict[str, Any]) -> int:
    return api.run(tus.offset(api.as_user("ivy"), ctx["upload"]))


@given(parsers.parse("Ivy's upload is at {pct:d}%"))
def upload_at(api: ApiDriver, ctx: dict[str, Any], pct: int) -> None:
    _upload_to(api, ctx, pct)


@when("a chunk arrives that does not match its checksum")
def damaged_chunk(api: ApiDriver, ctx: dict[str, Any]) -> None:
    chunk = DATA[ctx["sent"] : ctx["sent"] + 65536]
    damaged = bytes(b ^ 0x01 for b in chunk)
    ctx["response"] = api.run(
        tus_ext.patch(
            api.as_user("ivy"), ctx["upload"], ctx["sent"], damaged, tus_ext.checksum(chunk)
        )
    )


@then("the chunk is refused")
def chunk_refused(ctx: dict[str, Any]) -> None:
    assert ctx["response"].status_code == contract.CHECKSUM_MISMATCH


@then(parsers.parse("the upload is still at {pct:d}%"))
def still_at(api: ApiDriver, ctx: dict[str, Any], pct: int) -> None:
    assert percent_of(_offset(api, ctx), len(DATA)) == pct


@given(parsers.parse("Ivy closed the tab when her upload was {pct:d}% done"))
def closed_tab(api: ApiDriver, ctx: dict[str, Any], pct: int) -> None:
    _upload_to(api, ctx, pct)


@when("she opens the app again within 24 hours")
def opens_again(api: ApiDriver, ctx: dict[str, Any]) -> None:
    ctx["match"] = api.request("ivy", "GET", contract.MATCH.format(match_id=ctx["match_id"])).json()


@then(parsers.parse("she is offered to resume from {pct:d}%"))
def offered_resume(ctx: dict[str, Any], pct: int) -> None:
    upload = ctx["match"]["upload"]
    assert upload["state"] == "receiving"
    assert percent_of(upload["offset"], upload["length"]) == pct
    assert upload["resume_url"]
    assert upload["expires_at"]


@given("Ivy's unfinished upload has passed its expiry time")
def expired_upload(expiry_env: None, api: ApiDriver, ctx: dict[str, Any]) -> None:
    _upload_to(api, ctx, 40)
    time.sleep(1.5)


@when("she tries to resume it")
def tries_to_resume(api: ApiDriver, ctx: dict[str, Any]) -> None:
    ctx["response"] = api.run(
        tus_ext.patch(api.as_user("ivy"), ctx["upload"], ctx["sent"], DATA[ctx["sent"] :])
    )


@then("she is told the upload expired and must be started again")
def told_expired(api: ApiDriver, ctx: dict[str, Any]) -> None:
    assert ctx["response"].status_code == 410
    assert ERROR_COPY[error_code(ctx["response"])].startswith("This upload expired")
    match = api.request("ivy", "GET", contract.MATCH.format(match_id=ctx["match_id"])).json()
    assert match["upload"]["state"] == "expired"


@given("Ivy has an unfinished upload")
def unfinished(api: ApiDriver, ctx: dict[str, Any]) -> None:
    _upload_to(api, ctx, 40)


@when("Carlos sends a chunk to it")
def carlos_sends(api: ApiDriver, ctx: dict[str, Any]) -> None:
    carlos = api.as_user("carlos")
    chunk = DATA[ctx["sent"] : ctx["sent"] + 1024]
    ctx["response"] = api.run(tus_ext.patch(carlos, ctx["upload"], ctx["sent"], chunk))
    missing = tus.Upload(
        url=contract.UPLOAD_RESOURCE.format(upload_id="00000000-0000-4000-8000-000000000000"),
        length=1,
    )
    ctx["missing"] = api.run(tus_ext.patch(carlos, missing, 0, chunk))


@then('Carlos gets the same "not found" result as for an upload that does not exist')
def same_not_found(ctx: dict[str, Any]) -> None:
    got, missing = ctx["response"], ctx["missing"]
    assert got.status_code == missing.status_code == 404
    assert got.json()["error"]["code"] == missing.json()["error"]["code"]


@then("Ivy's upload is unchanged")
def unchanged(api: ApiDriver, ctx: dict[str, Any]) -> None:
    assert _offset(api, ctx) == ctx["sent"]
