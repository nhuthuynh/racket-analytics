"""IT-01-06..IT-01-08 (ST-017; FR-022; NFR-026; AQS/STACK-06; api-sprint-01 §6) with threat
controls T-UV-5 (checksum), T-UV-6 (same file), T-UV-7 (expiry, quota) and T-UV-8 (BOLA on an
expired upload). API <-> real object store <-> real Postgres. RED until ST-017.
"""

from __future__ import annotations

import email.utils
import hashlib
import time
from typing import Any

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from sqlalchemy import text

from tests.support import contract, tus, tus_ext
from tests.support.api import ApiDriver
from tests.support.flows import create_match
from tests.support.paths import SYNTHETIC_CLIP
from tests.support.written_keys import WrittenKeys

pytestmark = [pytest.mark.slow]

DATA = SYNTHETIC_CLIP.read_bytes()


def _start(api: ApiDriver, user: str = "ivy", data: bytes = DATA, **kw: Any) -> tus.Upload:
    client = api.as_user(user)
    match_id = api.run(create_match(client, f"IT-01-06 {time.monotonic_ns()}"))
    return api.run(tus_ext.start(client, match_id, data, **kw))


def _offset(api: ApiDriver, upload: tus.Upload, user: str = "ivy") -> int:
    return api.run(tus.offset(api.as_user(user), upload))


# ------------------------------------------------------------------ discovery
def test_options_advertises_the_checksum_and_expiration_extensions(api: ApiDriver) -> None:
    response = api.request("anonymous", "OPTIONS", contract.UPLOAD_OPTIONS)
    assert response.status_code == 204
    extensions = {e.strip() for e in response.headers["Tus-Extension"].split(",")}
    assert {"creation", "checksum", "expiration"} <= extensions
    algorithms = {a.strip() for a in response.headers["Tus-Checksum-Algorithm"].split(",")}
    assert "sha256" in algorithms


# ------------------------------------------------------------------ IT-01-06, T-UV-5
def test_it_01_06_corrupted_chunk_is_refused_and_the_offset_is_unchanged(api: ApiDriver) -> None:
    upload = _start(api)
    ivy = api.as_user("ivy")
    first = tus_ext.first_chunk_size(DATA)
    assert api.run(tus_ext.patch(ivy, upload, 0, DATA[:first])).status_code == 204  # control

    chunk = DATA[first:]
    damaged = bytes([chunk[0] ^ 0xFF]) + chunk[1:]
    response = api.run(tus_ext.patch(ivy, upload, first, damaged, tus_ext.checksum(chunk)))

    assert response.status_code == contract.CHECKSUM_MISMATCH
    assert response.json()["error"]["code"] == "checksum_mismatch"
    assert _offset(api, upload) == first
    assert api.run(tus_ext.patch(ivy, upload, first, chunk)).status_code == 204
    assert _offset(api, upload) == len(DATA)


@pytest.mark.parametrize("header", ["md5 AAAA", "sha256", "sha256 !!!notbase64", "sha256  "])
def test_malformed_or_unsupported_checksum_is_a_400(api: ApiDriver, header: str) -> None:
    upload = _start(api)
    response = api.run(tus_ext.patch(api.as_user("ivy"), upload, 0, DATA[:1024], header))
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "checksum_invalid"
    assert _offset(api, upload) == 0


@pytest.fixture
def quota_out_of_the_way(monkeypatch: pytest.MonkeyPatch) -> None:
    """TCR row 14: each example opens a new upload for ivy; the quota (T-UV-7, own tests
    below) must not answer first. Limits stay above the example count incl. shrinking."""
    monkeypatch.setenv("UPLOAD_MAX_OPEN_SESSIONS", "1000")
    monkeypatch.setenv("UPLOAD_CREATE_LIMIT_PER_HOUR", "1000")


@settings(
    max_examples=40, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture]
)
@given(header=st.text(max_size=80))
def test_upload_checksum_parser_never_fails_open_or_crashes(
    quota_out_of_the_way: None, api: ApiDriver, header: str
) -> None:
    """Retro 0 L4 / testing-strategy rule 9: any header text -> 204, 400 or 460, never 5xx."""
    upload = _start(api)
    chunk = DATA[: tus_ext.first_chunk_size(DATA)]
    try:
        response = api.run(tus_ext.patch(api.as_user("ivy"), upload, 0, chunk, header))
    except UnicodeEncodeError:
        return  # httpx refuses non-latin-1 header values before sending
    assert response.status_code in (204, 400, contract.CHECKSUM_MISMATCH), response.text
    if response.status_code != 204:
        assert _offset(api, upload) == 0


# ------------------------------------------------------------------ T-UV-6
def test_a_different_file_cannot_be_resumed_onto_the_upload(api: ApiDriver) -> None:
    upload = _start(api)
    other = bytes(reversed(DATA))
    first = tus_ext.first_chunk_size(other)
    response = api.run(tus_ext.patch(api.as_user("ivy"), upload, 0, other[:first]))
    assert response.status_code == contract.CHECKSUM_MISMATCH
    assert _offset(api, upload) == 0


# ------------------------------------------------------------------ IT-01-07, T-UV-7, T-UV-8
def test_it_01_07_creation_head_and_patch_carry_upload_expires(api: ApiDriver) -> None:
    ivy = api.as_user("ivy")
    match_id = api.run(create_match(ivy, "IT-01-07 headers"))
    created = api.run(tus_ext.create(ivy, match_id, DATA))
    assert created.status_code == 201
    expires = email.utils.parsedate_to_datetime(created.headers["Upload-Expires"])
    assert expires.timestamp() > time.time() + 3600
    upload = tus.Upload(url=created.headers["Location"], length=len(DATA))
    assert "Upload-Expires" in api.run(tus.head(ivy, upload)).headers
    patched = api.run(tus_ext.patch(ivy, upload, 0, DATA[: tus_ext.first_chunk_size(DATA)]))
    assert "Upload-Expires" in patched.headers


@pytest.fixture
def short_expiry(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(contract.UPLOAD_EXPIRY_ENV, "1")


def test_it_01_07_patch_after_expiry_is_refused_and_others_still_get_404(
    short_expiry: None, api: ApiDriver
) -> None:
    upload = _start(api)
    time.sleep(1.5)
    ivy = api.as_user("ivy")

    patched = api.run(tus_ext.patch(ivy, upload, 0, DATA[:1024]))
    head = api.run(tus.head(ivy, upload))
    carlos = api.run(tus_ext.patch(api.as_user("carlos"), upload, 0, DATA[:1024]))

    assert patched.status_code == 410
    assert patched.json()["error"]["code"] == "upload_expired"
    assert head.status_code == 410
    assert head.content == b""
    assert carlos.status_code == 404  # ownership first: never 410 for another user (T-UV-8)


def test_a_fourth_open_upload_is_refused_by_the_quota(api: ApiDriver) -> None:
    for _ in range(3):
        _start(api, "dana")
    dana = api.as_user("dana")
    match_id = api.run(create_match(dana, "IT-01-07 quota"))
    response = api.run(tus_ext.create(dana, match_id, DATA))
    assert response.status_code == 429
    assert response.json()["error"]["code"] == "upload_quota_exceeded"
    assert response.json()["error"]["retry_at"] is None


@pytest.mark.parametrize("last_modified", [str(2**63), "9" * 20])
def test_last_modified_out_of_bigint_range_is_a_400_and_stores_nothing(
    api: ApiDriver, committed_db: Any, last_modified: str
) -> None:
    """SEC-R2-S1-01: client input beyond the BIGINT column was a 500 internal_error."""
    ivy = api.as_user("ivy")
    match_id = api.run(create_match(ivy, f"SEC-R2-S1-01 {time.monotonic_ns()}"))
    response = api.request(
        "ivy",
        "POST",
        contract.UPLOAD_CREATE.format(match_id=match_id),
        headers={
            "Tus-Resumable": contract.TUS_VERSION,
            "Upload-Length": "1000",
            "Upload-Metadata": tus.metadata(filename="a.mp4", last_modified=last_modified),
        },
    )
    assert response.status_code == 400, response.text
    assert response.json()["error"]["code"] == "bad_request"
    with committed_db.connect() as conn:
        rows = conn.execute(
            text("SELECT count(*) FROM upload_sessions WHERE match_id = :m"), {"m": match_id}
        ).scalar_one()
    assert rows == 0


# ------------------------------------------------------------------ IT-01-08 (D-3)
def test_it_01_08_a_restarted_client_resumes_from_the_server_offset(
    api: ApiDriver, written_keys: WrittenKeys
) -> None:
    ivy = api.as_user("ivy")
    store = contract.OBJECT_STORE.load().from_settings()
    match_id = api.run(create_match(ivy, "IT-01-08"))
    upload = api.run(tus_ext.start(ivy, match_id, DATA))
    first = tus_ext.first_chunk_size(DATA)
    assert api.run(tus_ext.patch(ivy, upload, 0, DATA[:first])).status_code == 204

    # "Restart": a new browser session for the same user finds the upload in the read model.
    match = api.request("ivy", "GET", contract.MATCH.format(match_id=match_id)).json()
    pending = match["upload"]
    assert pending["state"] == "receiving"
    assert pending["offset"] == first
    assert pending["length"] == len(DATA)
    assert pending["file_name"] == "Sat doubles.mp4"
    assert pending["head_sha256"] == tus_ext.head_sha256(DATA)
    resumed = tus.Upload(url=pending["resume_url"], length=len(DATA))
    at = api.run(tus.offset(ivy, resumed))
    assert at == first
    assert api.run(tus_ext.patch(ivy, resumed, at, DATA[at:])).status_code == 204

    new_keys = written_keys.stored()
    assert len(new_keys) == 1, new_keys
    assert hashlib.sha256(store.get_bytes(new_keys.pop())).digest() == hashlib.sha256(DATA).digest()
    after = api.request("ivy", "GET", contract.MATCH.format(match_id=match_id)).json()
    assert after["upload"] is None


def test_the_upload_object_is_only_in_the_owners_read_model(api: ApiDriver) -> None:
    ivy = api.as_user("ivy")
    match_id = api.run(create_match(ivy, "IT-01-08 owner only"))
    api.run(tus_ext.start(ivy, match_id, DATA))
    assert api.request("ivy", "GET", contract.MATCH.format(match_id=match_id)).json()["upload"]
    assert api.request("carlos", "GET", contract.MATCH.format(match_id=match_id)).status_code == 404
