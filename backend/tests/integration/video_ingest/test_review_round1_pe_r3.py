"""Sprint 1 review round 1, carried PE findings (api-sprint-01 §6.3, §6.6).

* PE-R3-01: a malformed ``last_modified`` / ``head_sha256`` is a 400 before quota and rate
  (§6.3 check 4), also for an owner already at the open-upload quota.
* PE-R3-02 (was PE-R1-08): a probe refusal deletes the original object only after the
  transaction that removes the asset and session rows has committed (§6.6). If the runner rolls
  back (lost lease), the rows and the bytes both survive, and a re-run refuses the file again.

Real Postgres, object store and the in-process worker.
"""

from __future__ import annotations

from typing import Any

import pytest
import sqlalchemy as sa

from tests.support import contract, media, tus, tus_ext
from tests.support.api import ApiDriver
from tests.support.flows import create_match
from tests.support.worker import jobs_for_match, probe_job
from tests.support.written_keys import WrittenKeys

pytestmark = [pytest.mark.slow]

DATA = tus.video_bytes(64 * 1024)


def _fill_quota(api: ApiDriver, user: str) -> None:
    client = api.as_user(user)
    for n in range(3):
        match_id = api.run(create_match(client, f"PE-R3-01 quota {n}"))
        api.run(tus_ext.start(client, match_id, DATA))


@pytest.mark.parametrize(
    "meta",
    [
        {"filename": "a.mp4", "last_modified": str(2**63)},
        {"filename": "a.mp4", "last_modified": "12x"},
        {"filename": "a.mp4", "head_sha256": "A" * 64},
    ],
    ids=["last_modified-out-of-range", "last_modified-not-decimal", "head_sha256-upper-hex"],
)
def test_pe_r3_01_malformed_metadata_at_quota_is_400_not_429(
    api: ApiDriver, meta: dict[str, str]
) -> None:
    _fill_quota(api, "dana")
    dana = api.as_user("dana")
    match_id = api.run(create_match(dana, "PE-R3-01 malformed"))

    response = api.run(
        dana.post(
            contract.UPLOAD_CREATE.format(match_id=match_id),
            headers={
                "Tus-Resumable": contract.TUS_VERSION,
                "Upload-Length": str(len(DATA)),
                "Upload-Metadata": tus.metadata(**meta),
            },
        )
    )

    assert response.status_code == 400, response.text[:200]


def test_pe_r3_01_positive_control_well_formed_metadata_at_quota_is_429(api: ApiDriver) -> None:
    _fill_quota(api, "dana")
    dana = api.as_user("dana")
    match_id = api.run(create_match(dana, "PE-R3-01 control"))
    response = api.run(tus_ext.create(dana, match_id, DATA))
    assert response.status_code == 429
    assert response.json()["error"]["code"] == "upload_quota_exceeded"


# ------------------------------------------------------------------ PE-R3-02
def _match(api: ApiDriver, match_id: str) -> dict[str, Any]:
    response = api.request("ivy", "GET", contract.MATCH.format(match_id=match_id))
    assert response.status_code == 200
    body: dict[str, Any] = response.json()
    return body


def _asset_rows(engine: Any, match_id: str) -> int:
    with engine.connect() as conn:
        return int(
            conn.execute(
                sa.text("SELECT count(*) FROM media_assets WHERE match_id = :m"), {"m": match_id}
            ).scalar_one()
        )


def test_pe_r3_02_a_rolled_back_refusal_keeps_the_bytes_and_a_rerun_refuses_again(
    api: ApiDriver,
    committed_db: Any,
    written_keys: WrittenKeys,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ivy = api.as_user("ivy")
    data = media.long_clip_bytes()
    match_id = api.run(create_match(ivy, "PE-R3-02 lost lease"))
    upload = api.run(tus_ext.start(ivy, match_id, data, filename="match.mp4"))
    assert api.run(tus_ext.patch(ivy, upload, 0, data)).status_code == 204
    assert written_keys.stored(), "the received video was never stored"

    # The stage returns, then the runner finds it lost the lease and rolls back.
    queue_class = contract.JOB_QUEUE.load()
    real_lock_running = queue_class.lock_running
    monkeypatch.setattr(queue_class, "lock_running", lambda *_a, **_k: None)
    contract.WORKER_RUN_UNTIL_IDLE.load()()

    rolled_back = _match(api, match_id)
    assert rolled_back["rejection"] is None, "the refusal was rolled back"
    assert _asset_rows(committed_db, match_id) == 1, "the asset row survives the rollback"
    assert written_keys.stored(), "the bytes were deleted although the refusal rolled back"

    # Another worker reclaims the job once the lease expires; the re-run refuses the file again.
    monkeypatch.setattr(queue_class, "lock_running", real_lock_running)
    job = probe_job(committed_db, match_id)
    with committed_db.begin() as conn:
        conn.execute(
            sa.text(
                "UPDATE jobs SET lease_expires_at = now() - interval '1 second' WHERE id = :id"
            ),
            {"id": job.id},
        )
    contract.WORKER_RUN_UNTIL_IDLE.load()()

    final = _match(api, match_id)
    assert final["rejection"]["code"] == "too_long"
    assert final["media"] is None
    assert _asset_rows(committed_db, match_id) == 0
    assert written_keys.stored() == set(), "the refused file's bytes were kept after commit"
    stages = [j.key.stage for j in jobs_for_match(committed_db, match_id)]
    assert stages == [contract.PROBE_STAGE_NAME]
