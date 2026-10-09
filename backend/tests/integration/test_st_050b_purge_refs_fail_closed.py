"""ST-050b integration (SEC-S3-TM-01 / T-DL-3, NFR-066 b; deletion-and-purge.md §4.6 and §6;
ADR 0042, ADR 0045): the purge's typed object refs over the real app, Postgres and object store.

Two owners, one match each. Negative cases first (PE-050b-01, QA-50b-R1-01): a row of Ivy's
deleted match is rewritten so that it names an object of Carlos's match, either

1. a media row naming Carlos's original key, or
2. a staged chunk naming a key in Carlos's upload's staging folder.

One pass refuses Ivy's match (exit 1, ``purge.failed`` with ``stage=objects``) before any store
call: no delete, no folder delete, no multipart abort; Ivy's rows are kept (the match stays due)
and Carlos's rows and objects are untouched.

Then the positive case (PE-050b-02): each owner has an open upload holding one multipart part
and one staged chunk. After Ivy deletes her match, one pass aborts her multipart upload and
empties her staging folder (no orphan, ADR 0042) and leaves no row of her match, while Carlos's
open upload, part and staged chunk are untouched.
"""

from __future__ import annotations

import json
from typing import Any

import pytest
import sqlalchemy as sa

from tests.support import scorebook as sb
from tests.support import stats as st
from tests.support import tus
from tests.support.api import ApiDriver

MIB = 1024 * 1024
PART = 5 * MIB  # the part minimum: this PATCH is sent to the store as multipart part 1
CHUNK = 1 * MIB  # below the part minimum: this PATCH is staged as an object
LENGTH = 7 * MIB  # the upload stays open after both PATCHes
STORE_CALLS = ("delete", "delete_prefix", "abort_multipart")


def _store() -> Any:
    return st.OBJECT_STORE.load().from_settings()


def _upload_row(engine: Any, match_id: str) -> dict[str, Any]:
    with engine.connect() as conn:
        row = (
            conn.execute(
                sa.text(
                    "SELECT id, object_key, s3_upload_id, status FROM upload_sessions "
                    "WHERE match_id::text = :m"
                ),
                {"m": match_id},
            )
            .mappings()
            .one()
        )
    return dict(row)


def _staged(engine: Any, match_id: str) -> list[str]:
    upload_id = _upload_row(engine, match_id)["id"]
    return sorted(_store().list_keys(prefix=f"staging/{upload_id.hex}/"))


def _parts(key: str, upload_id: str) -> list[int] | None:
    """Part numbers of an open multipart upload; None once it is aborted or completed. Open is
    read from the store's listing of multipart uploads (SeaweedFS still answers ``ListParts``
    for an aborted upload, with no parts)."""
    store = _store()
    listed = store._client.list_multipart_uploads(Bucket=store.bucket, Prefix=key)
    if upload_id not in [u["UploadId"] for u in listed.get("Uploads", [])]:
        return None
    response = store._client.list_parts(Bucket=store.bucket, Key=key, UploadId=upload_id)
    return [int(p["PartNumber"]) for p in response.get("Parts", [])]


def _open_upload(api: ApiDriver, user: str, title: str, *, with_part: bool) -> str:
    """A match whose upload is still receiving: optionally one part, then one staged chunk."""
    client = api.as_user(user)
    match_id = api.run(sb.create_doubles(client, title))
    data = tus.video_bytes(LENGTH)
    upload = api.run(tus.start(client, match_id, len(data)))
    at = 0
    for size in (PART, CHUNK) if with_part else (CHUNK,):
        response = api.run(tus.patch(client, upload, at, data[at : at + size]))
        assert response.status_code == 204, response.text
        at += size
    return match_id


def _received(api: ApiDriver, user: str, title: str) -> str:
    client = api.as_user(user)
    match_id = api.run(sb.create_doubles(client, title))
    api.run(sb.receive_video(client, match_id))
    return match_id


def _spy_store(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, tuple[Any, ...]]]:
    """Record every deleting store call the purge makes (and still make it)."""
    store_cls = st.OBJECT_STORE.load()
    calls: list[tuple[str, tuple[Any, ...]]] = []
    for name in STORE_CALLS:
        real = getattr(store_cls, name)

        def spy(self: Any, *args: Any, _name: str = name, _real: Any = real) -> Any:
            calls.append((_name, args))
            return _real(self, *args)

        monkeypatch.setattr(store_cls, name, spy)
    return calls


def _purge(capfd: pytest.CaptureFixture[str]) -> tuple[int, list[dict[str, Any]]]:
    capfd.readouterr()
    rc = st.PURGE_MAIN.load()(["--once"])
    out, err = capfd.readouterr()
    lines = [json.loads(line) for line in (out + err).splitlines() if line.startswith("{")]
    return rc, lines


def _assert_refused(rc: int, lines: list[dict[str, Any]], calls: list[Any], match_id: str) -> None:
    assert calls == [], f"the purge called the store for a refused match: {calls}"
    assert rc == 1, f"purge --once exit {rc}, a refused match must fail the pass"
    failed = [r for r in lines if r.get("event") == "purge.failed"]
    assert [(r.get("kind"), r.get("match_id"), r.get("stage"), r.get("error")) for r in failed] == [
        ("match", match_id, "objects", "UnsafeObjectRef")
    ], failed
    assert not [r for r in lines if r.get("event") == "match.purged"], lines


def test_st_050b_a_row_naming_another_matchs_original_is_refused_before_any_store_call(
    api: ApiDriver,
    committed_db: Any,
    monkeypatch: pytest.MonkeyPatch,
    capfd: pytest.CaptureFixture[str],
) -> None:
    ivy = _received(api, "ivy", "ST-050b shared key ivy")
    carlos = _received(api, "carlos", "ST-050b shared key carlos")
    ivy_keys = st.object_keys_of(committed_db, ivy)
    (carlos_key,) = st.object_keys_of(committed_db, carlos)
    assert st.keys_still_stored([*ivy_keys, carlos_key]) == [*ivy_keys, carlos_key]
    assert st.delete_match(api, "ivy", ivy).status_code in st.statscontract.DELETE_OK
    with committed_db.begin() as conn:  # a corrupted row: Ivy's media names Carlos's video
        conn.execute(
            sa.text("UPDATE media_assets SET object_key = :k WHERE match_id::text = :m"),
            {"k": carlos_key, "m": ivy},
        )
    ivy_rows = st.rows_holding(committed_db, [ivy])
    carlos_rows = st.rows_holding(committed_db, [carlos])
    calls = _spy_store(monkeypatch)

    rc, lines = _purge(capfd)

    _assert_refused(rc, lines, calls, ivy)
    assert st.keys_still_stored([carlos_key]) == [carlos_key], "Carlos's video was deleted"
    assert st.keys_still_stored(ivy_keys) == ivy_keys
    assert st.rows_holding(committed_db, [ivy]) == ivy_rows, "a refused match keeps its rows"
    assert st.rows_holding(committed_db, [carlos]) == carlos_rows
    assert sb.sheet_body(api, "carlos", carlos) is not None


def test_st_050b_a_staged_chunk_outside_its_uploads_folder_is_refused_before_any_store_call(
    api: ApiDriver,
    committed_db: Any,
    monkeypatch: pytest.MonkeyPatch,
    capfd: pytest.CaptureFixture[str],
) -> None:
    ivy = _open_upload(api, "ivy", "ST-050b staged ivy", with_part=False)
    carlos = _open_upload(api, "carlos", "ST-050b staged carlos", with_part=False)
    (ivy_chunk,) = _staged(committed_db, ivy)
    (carlos_chunk,) = _staged(committed_db, carlos)
    assert st.delete_match(api, "ivy", ivy).status_code in st.statscontract.DELETE_OK
    with committed_db.begin() as conn:  # a corrupted row: Ivy's chunk names Carlos's folder
        conn.execute(
            sa.text(
                "UPDATE upload_sessions "
                "SET staged = jsonb_set(staged, '{0,key}', to_jsonb(CAST(:k AS text))) "
                "WHERE match_id::text = :m"
            ),
            {"k": carlos_chunk, "m": ivy},
        )
    ivy_rows = st.rows_holding(committed_db, [ivy])
    carlos_rows = st.rows_holding(committed_db, [carlos])
    calls = _spy_store(monkeypatch)

    rc, lines = _purge(capfd)

    _assert_refused(rc, lines, calls, ivy)
    assert _staged(committed_db, carlos) == [carlos_chunk], "Carlos's staged chunk was deleted"
    assert _staged(committed_db, ivy) == [ivy_chunk]
    assert st.rows_holding(committed_db, [ivy]) == ivy_rows, "a refused match keeps its rows"
    assert st.rows_holding(committed_db, [carlos]) == carlos_rows


def test_st_050b_the_purge_frees_an_open_uploads_part_and_staged_chunk_and_only_those(
    api: ApiDriver, committed_db: Any
) -> None:
    ivy = _open_upload(api, "ivy", "ST-050b open ivy", with_part=True)
    carlos = _open_upload(api, "carlos", "ST-050b open carlos", with_part=True)
    ivy_up, carlos_up = _upload_row(committed_db, ivy), _upload_row(committed_db, carlos)
    ivy_staged, carlos_staged = _staged(committed_db, ivy), _staged(committed_db, carlos)
    # positive controls: each open upload holds one part and one staged chunk
    assert _parts(ivy_up["object_key"], ivy_up["s3_upload_id"]) == [1]
    assert _parts(carlos_up["object_key"], carlos_up["s3_upload_id"]) == [1]
    assert len(ivy_staged) == 1
    assert len(carlos_staged) == 1
    carlos_rows = st.rows_holding(committed_db, [carlos])

    assert st.delete_match(api, "ivy", ivy).status_code in st.statscontract.DELETE_OK
    st.run_purge_once()

    assert _staged(committed_db, carlos) == carlos_staged
    assert _parts(carlos_up["object_key"], carlos_up["s3_upload_id"]) == [1]
    assert st.rows_holding(committed_db, [carlos]) == carlos_rows
    left = {k: n for k, n in st.rows_holding(committed_db, [ivy]).items() if n}
    assert left == {}, f"rows still hold the match after the purge: {left}"
    assert sorted(_store().list_keys(prefix=f"staging/{ivy_up['id'].hex}/")) == [], (
        "the purge left the deleted match's staged chunk"
    )
    assert _parts(ivy_up["object_key"], ivy_up["s3_upload_id"]) is None, (
        "the purge left the deleted match's multipart upload open"
    )
