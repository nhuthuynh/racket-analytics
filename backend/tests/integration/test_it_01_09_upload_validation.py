"""IT-01-09 and IT-01-10 (ST-018; FR-023; NFR-053, NFR-054, NFR-060; AQS/SEC-02;
api-sprint-01 §6.3, §6.5, §6.6) with threat controls T-UV-1..T-UV-4.

Every refusal has a positive control in this file: the valid phone-like clip goes through the
same path and is accepted (testing-strategy rule 8). Real Postgres, object store and the
in-process worker. RED until ST-018.
"""

from __future__ import annotations

import time
from typing import Any

import pytest

from tests.support import contract, media, tus, tus_ext
from tests.support.api import ApiDriver
from tests.support.flows import create_match
from tests.support.worker import jobs_for_match, media_facts_count
from tests.support.written_keys import WrittenKeys

pytestmark = [pytest.mark.slow]

TWELVE_GB = 12 * 1000**3


def _match(api: ApiDriver, match_id: str) -> dict[str, Any]:
    response = api.request("ivy", "GET", contract.MATCH.format(match_id=match_id))
    assert response.status_code == 200
    body: dict[str, Any] = response.json()
    return body


def _send_whole_file(api: ApiDriver, data: bytes, filename: str) -> tuple[str, Any, Any]:
    ivy = api.as_user("ivy")
    match_id = api.run(create_match(ivy, f"IT-01-09 {filename}"))
    upload = api.run(tus_ext.start(ivy, match_id, data, filename=filename))
    response = api.run(tus_ext.patch(ivy, upload, 0, data))
    return match_id, upload, response


def _assert_refused_and_nothing_kept(
    api: ApiDriver, committed_db: Any, match_id: str, code: str, written_keys: WrittenKeys
) -> None:
    match = _match(api, match_id)
    assert match["rejection"]["code"] == code
    assert match["status"] == "awaiting_upload"
    assert match["upload"] is None
    assert match["media"] is None
    assert written_keys.stored() == set(), "an object from a refused file was kept"
    assert media_facts_count(committed_db, match_id) == 0


# ------------------------------------------------------------------ T-UV-1: content, not name
@pytest.mark.parametrize(
    ("data", "filename"),
    [(media.pdf_bytes(), "match.mp4"), (media.executable_bytes(), "match.mov")],
    ids=["pdf-renamed-mp4", "program-renamed-mov"],
)
def test_it_01_09_non_video_content_is_refused_on_the_first_chunk(
    api: ApiDriver, committed_db: Any, data: bytes, filename: str, written_keys: WrittenKeys
) -> None:
    match_id, upload, response = _send_whole_file(api, data, filename)

    assert response.status_code == 415
    assert response.json()["error"]["code"] == "not_a_video"
    assert api.run(tus.head(api.as_user("ivy"), upload)).status_code == 404  # session deleted
    _assert_refused_and_nothing_kept(api, committed_db, match_id, "not_a_video", written_keys)
    assert jobs_for_match(committed_db, match_id) == []  # NFR-060


def test_positive_control_a_real_mp4_passes_the_same_first_chunk_check(
    api: ApiDriver, committed_db: Any
) -> None:
    data = media.valid_clip_bytes()
    match_id, _, response = _send_whole_file(api, data, "match.mp4")
    assert response.status_code == 204
    contract.WORKER_RUN_UNTIL_IDLE.load()()
    match = _match(api, match_id)
    assert match["status"] == "video_received"
    assert match["rejection"] is None
    assert media_facts_count(committed_db, match_id) == 1


# ------------------------------------------------------------------ T-UV-2: declared size
def test_it_01_09_declared_12_gb_is_refused_before_any_byte_is_stored(
    api: ApiDriver, committed_db: Any, written_keys: WrittenKeys
) -> None:
    ivy = api.as_user("ivy")
    match_id = api.run(create_match(ivy, "IT-01-09 12 GB"))

    response = api.run(tus_ext.create(ivy, match_id, b"\x00" * 16, length=TWELVE_GB))

    assert response.status_code == 413
    assert response.json()["error"]["code"] == "video_too_large"
    assert "Location" not in response.headers
    _assert_refused_and_nothing_kept(api, committed_db, match_id, "too_large", written_keys)
    assert jobs_for_match(committed_db, match_id) == []


@pytest.fixture
def cap_at_clip_size(monkeypatch: pytest.MonkeyPatch) -> int:
    size = len(media.valid_clip_bytes())
    monkeypatch.setenv(contract.UPLOAD_MAX_BYTES_ENV, str(size))
    return size


def test_size_cap_boundary_cap_is_accepted_and_cap_plus_one_is_not(
    cap_at_clip_size: int, api: ApiDriver
) -> None:
    """T-UV-3 boundaries (cap, cap + 1), with the cap from configuration (FR-023 K12)."""
    ivy = api.as_user("ivy")
    at_cap = api.run(create_match(ivy, "cap"))
    over = api.run(create_match(ivy, "cap+1"))
    data = media.valid_clip_bytes()
    assert api.run(tus_ext.create(ivy, at_cap, data)).status_code == 201
    assert api.run(tus_ext.create(ivy, over, data, length=cap_at_clip_size + 1)).status_code == 413


# ------------------------------------------------------------------ T-UV-3: duration from probe
def test_it_01_09_a_4_hour_video_is_refused_after_the_probe_and_deleted(
    api: ApiDriver, committed_db: Any, written_keys: WrittenKeys
) -> None:
    match_id, _, response = _send_whole_file(api, media.long_clip_bytes(), "match.mp4")
    assert response.status_code == 204  # real MP4: the magic bytes pass
    assert written_keys.stored(), "the received video was never stored; 'deleted' is vacuous"

    contract.WORKER_RUN_UNTIL_IDLE.load()()

    _assert_refused_and_nothing_kept(api, committed_db, match_id, "too_long", written_keys)
    stages = [job.key.stage for job in jobs_for_match(committed_db, match_id)]
    assert stages == [contract.PROBE_STAGE_NAME], "no job beyond the probe (NFR-060)"


# ------------------------------------------------------------------ IT-01-10 (T-UV-4)
def _malformed_mp4() -> bytes:
    """A valid ``ftyp`` box (passes the magic-byte check) followed by garbage."""
    head = media.valid_clip_bytes()[:32]
    return head + bytes((i * 131 + 7) % 256 for i in range(256 * 1024))


def test_it_01_10_a_crafted_malformed_container_ends_failed_within_its_time_limit(
    api: ApiDriver, committed_db: Any
) -> None:
    match_id, _, response = _send_whole_file(api, _malformed_mp4(), "match.mp4")
    assert response.status_code == 204

    started = time.monotonic()
    contract.WORKER_RUN_UNTIL_IDLE.load()()
    elapsed = time.monotonic() - started

    assert _match(api, match_id)["status"] == "probe_failed"
    assert elapsed < 60, f"probe of a malformed file took {elapsed:.1f}s"
    assert media_facts_count(committed_db, match_id) == 0
