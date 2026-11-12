"""IT-05-05 (ST-077; NFR-063.1-.2; ADR 0058 rule 5.3; SEC-5 T5-BK-1; AQS/SEC-05 14.1.1-14.1.2).

Binds ``tests/features/data_classification.feature``. Walks every store the stack writes and
looks each item up in ``docs/security/data-classification.md``:

* columns: the SQLAlchemy ``MetaData`` (every ``racket`` module imported) and the live, migrated
  schema of the session database (a column a migration adds without a model is stored too);
* bucket prefixes: the first key segment of every object this test's API wrote for a demo
  upload (``WrittenKeys``; never a whole-bucket diff, QA-R3-02);
* API responses: the ``GET /matches/{id}`` body and the tus ``HEAD`` headers of an unfinished
  upload never return a ``upload_sessions`` column the map marks ``A-SERVER`` (SPE-ST077-01);
  ``GET /me/quota`` and a 429 never return a ``media_assets`` column (``used_bytes`` is the sum
  of ``size_bytes``) or the time computed from ``rate_limit_events.at`` (oldest + window) that
  the map marks ``A-SERVER`` (SPE-ST077-R2-01); ``GET /me``, ``GET /matches/{id}`` and the
  presigned ``GET /matches/{id}/video`` link never return the object key or an id copy (owner,
  match, account) of a ``media_assets``, ``upload_sessions``, ``jobs``, ``sessions``,
  ``account_roles`` or ``plan_done_ops`` column the map marks ``A-SERVER`` (SPE-ST077-R3-01);
* backup artefacts: every file of a set taken by the ST-076a service (``scripts/ops/backup.py
  --once``, real ``pg_dump`` through real ``age``) on the session database and, since
  ST-076a-part2, a private bucket holding the demo upload's objects (``objects.tar.age``).

Negative cases first: a planted unclassified column, a planted unclassified backup file and a
walk that finds zero backup artefacts each fail. Missing ``age`` or Postgres tools fail, they
never skip, so the walk cannot pass empty (PE-PLAN05-06).
"""

from __future__ import annotations

import importlib
import os
import pkgutil
import shutil
import subprocess
import sys
import uuid
from collections.abc import Iterator
from datetime import timedelta
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlsplit

import boto3
import pytest
from pytest_bdd import given, scenarios, then, when
from sqlalchemy import text

from racket.matches.domain import OwnerId, account_creation_key
from tests.support import contract, tus, tus_ext
from tests.support.api import ApiDriver
from tests.support.classification import (
    MAP_PATH,
    NO_BACKUP_ARTEFACT,
    Item,
    backup_files,
    backup_problems,
    incomplete,
    live_columns,
    load_map,
    metadata_columns,
    prefixes,
    server_side_returned,
    stale,
    unclassified,
)
from tests.support.db import database_url
from tests.support.flows import create_match, upload_fixture
from tests.support.paths import REPO, SYNTHETIC_CLIP
from tests.support.written_keys import WrittenKeys

scenarios("data_classification.feature")

BACKUP_SCRIPT = REPO / "scripts" / "ops" / "backup.py"
PG_BIN = Path("/usr/lib/postgresql/16/bin")
PLANTED_TABLE = "st077_planted"
PLANTED_COLUMN = ("column", f"{PLANTED_TABLE}.planted_secret")
PLANTED_FILE = ("backup", "plain-copy.sql")
QUOTA = "/me/quota"  # api-sprint-04 §7
CREATIONS_PER_HOUR = 2
CREATION_WINDOW = timedelta(hours=1)  # matches/service.py _spend_creation_slots
VIDEO = "/matches/{match_id}/video"  # matches/scorebook/api.py: {"url": <presigned GET>}
# Tables that copy the account id ``GET /me`` returns; ivy has no row in them here, so the
# trace uses the id as it would be stored (an FK copy of an id the owner reads).
ACCOUNT_ID_COPIES = ("account_roles", "plan_done_ops")


# ---------------------------------------------------------------- helpers
def all_models_metadata() -> Any:
    """``racket.platform.db.metadata`` after importing every ``racket`` module but entry points."""
    import racket

    for mod in pkgutil.walk_packages(racket.__path__, "racket."):
        if not mod.name.endswith("__main__") and ".migrations" not in mod.name:
            importlib.import_module(mod.name)
    return importlib.import_module("racket.platform.db").metadata


def tool_path() -> str:
    bindir = str(PG_BIN) if (PG_BIN / "pg_dump").exists() else ""
    path = os.pathsep.join(p for p in (bindir, os.environ.get("PATH", "")) if p)
    for tool in ("pg_dump", "pg_dumpall", "psql", "age", "age-keygen"):
        if shutil.which(tool, path=path) is None:
            pytest.fail(f"{tool} not on PATH: the backup walk needs it (CI installs age)")
    return path


def pg_env(url: str) -> dict[str, str]:
    u = urlsplit(url)
    return {
        "PGHOST": u.hostname or "127.0.0.1",
        "PGPORT": str(u.port or 5432),
        "PGUSER": unquote(u.username or ""),
        "PGPASSWORD": unquote(u.password or ""),
        "PGDATABASE": u.path.lstrip("/"),
    }


def s3_client() -> Any:
    names = ("S3_ENDPOINT_URL", "S3_ACCESS_KEY_ID", "S3_SECRET_ACCESS_KEY")
    missing = [n for n in names if not os.environ.get(n)]
    if missing:
        pytest.fail(f"{', '.join(missing)} not set: the backup walk needs the object store")
    return boto3.client(
        "s3", endpoint_url=os.environ["S3_ENDPOINT_URL"],
        aws_access_key_id=os.environ["S3_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["S3_SECRET_ACCESS_KEY"],
        region_name=os.environ.get("S3_REGION", "us-east-1"),
    )  # fmt: skip


@pytest.fixture
def backup_bucket() -> Iterator[str]:
    """A bucket of this test's own for the ST-076a-part2 media mirror (``objects.tar.age``).

    The service mirrors a whole bucket; the shared media bucket changes under parallel
    workers (a key listed then deleted gives a 404), so the set mirrors a private copy."""
    client, name = s3_client(), f"st077-{uuid.uuid4().hex[:12]}"
    client.create_bucket(Bucket=name)
    try:
        yield name
    finally:
        for obj in client.list_objects_v2(Bucket=name).get("Contents", []):
            client.delete_object(Bucket=name, Key=obj["Key"])
        client.delete_bucket(Bucket=name)


def copy_objects(keys: list[str], bucket: str) -> int:
    """The demo upload's objects that still exist, copied from the media bucket."""
    client, media, copied = s3_client(), os.environ["S3_BUCKET_MEDIA"], 0
    for key in keys:
        try:
            body = client.get_object(Bucket=media, Key=key)["Body"].read()
        except client.exceptions.ClientError as exc:
            if exc.response["Error"]["Code"] not in ("NoSuchKey", "404"):
                raise
        else:
            client.put_object(Bucket=bucket, Key=key, Body=body)
            copied += 1
    return copied


def take_backup(backups: Path, keydir: Path, bucket: str) -> None:
    """One on-demand set of the session database and media bucket through the ST-076a service."""
    path = tool_path()
    keygen = subprocess.run(
        ["age-keygen", "-o", str(keydir / "identity.txt")],
        env={**os.environ, "PATH": path}, capture_output=True, text=True, check=True,
    )  # fmt: skip
    clean = {k: v for k, v in os.environ.items() if not k.startswith(("BACKUP_", "PG", "S3_"))}
    store = {"S3_ENDPOINT_URL": os.environ["S3_ENDPOINT_URL"], "S3_BUCKET_MEDIA": bucket,
             "S3_REGION": os.environ.get("S3_REGION", "us-east-1"),
             "BACKUP_S3_ACCESS_KEY_ID": os.environ["S3_ACCESS_KEY_ID"],
             "BACKUP_S3_SECRET_ACCESS_KEY": os.environ["S3_SECRET_ACCESS_KEY"]}  # fmt: skip
    env = {**clean, **pg_env(database_url()), **store, "PATH": path, "BACKUP_DIR": str(backups),
           "BACKUP_AGE_RECIPIENT": keygen.stderr.strip().split()[-1]}  # fmt: skip
    proc = subprocess.run([sys.executable, str(BACKUP_SCRIPT), "--once"], env=env,
                          capture_output=True, text=True, timeout=300, check=False)  # fmt: skip
    assert proc.returncode == 0, proc.stdout + proc.stderr


# ---------------------------------------------------------------- steps
@pytest.fixture
def world() -> dict[str, Any]:
    return {}


@given("the data-classification map")
def the_map(world: dict[str, Any]) -> None:
    world["map"] = load_map()


@given("a live table with a column the map does not name")
def planted_table(world: dict[str, Any], db_session: Any) -> None:
    db_session.execute(text(f"CREATE TABLE {PLANTED_TABLE} (planted_secret text)"))
    world["connection"] = db_session.connection()  # rolled back after the test


@given("an on-demand backup set holding a file the map does not name")
def planted_backup_file(
    world: dict[str, Any], db_engine: Any, tmp_path: Path, backup_bucket: str
) -> None:
    take_backup(tmp_path / "backups", tmp_path, backup_bucket)
    [set_dir] = [p for p in (tmp_path / "backups").iterdir() if p.is_dir()]
    (set_dir / PLANTED_FILE[1]).write_text("-- a plaintext copy someone left in the set\n")
    world["backups"] = tmp_path / "backups"


@given("an empty backup directory")
def empty_backups(world: dict[str, Any], tmp_path: Path) -> None:
    (tmp_path / "backups").mkdir()
    world["backups"] = tmp_path / "backups"


@given("a migrated database, a demo upload and an on-demand backup")
def live_stack(
    world: dict[str, Any], api: ApiDriver, committed_db: Any, written_keys: WrittenKeys,
    tmp_path: Path, backup_bucket: str,
) -> None:  # fmt: skip
    ivy = api.as_user("ivy")
    match_id = api.run(create_match(ivy, "IT-05-05 classification walk"))
    api.run(upload_fixture(ivy, match_id))
    contract.WORKER_RUN_UNTIL_IDLE.load()()
    world["keys"] = list(written_keys.written)
    world["engine"] = committed_db
    assert copy_objects(world["keys"], backup_bucket) > 0, "the mirror must hold the demo video"
    take_backup(tmp_path / "backups", tmp_path, backup_bucket)
    world["backups"] = tmp_path / "backups"


@given("an unfinished upload of a demo video")
def unfinished_upload(world: dict[str, Any], api: ApiDriver, committed_db: Any) -> None:
    ivy = api.as_user("ivy")
    data = SYNTHETIC_CLIP.read_bytes()
    match_id = api.run(create_match(ivy, "IT-05-05 server-side columns"))
    upload = api.run(tus_ext.start(ivy, match_id, data))
    first = tus_ext.first_chunk_size(data)
    assert api.run(tus_ext.patch(ivy, upload, 0, data[:first])).status_code == 204
    world.update(match_id=match_id, upload=upload, engine=committed_db)


@when("the owner reads the match and the upload offset")
def owner_reads_upload(world: dict[str, Any], api: ApiDriver) -> None:
    match = api.request("ivy", "GET", contract.MATCH.format(match_id=world["match_id"]))
    assert match.status_code == 200, match.text
    assert match.json()["upload"] is not None, "the upload must still be unfinished"
    head = api.run(tus.head(api.as_user("ivy"), world["upload"]))
    world["response"] = {"match": match.json(), "head": dict(head.headers)}


@then("no column of that upload session the API returned is marked server-side only")
def no_server_side_column_returned(world: dict[str, Any]) -> None:
    with world["engine"].connect() as conn:
        row = conn.execute(
            text("SELECT * FROM upload_sessions WHERE match_id = :m"), {"m": world["match_id"]}
        ).mappings().one()  # fmt: skip
    found = server_side_returned(world["map"], "upload_sessions", dict(row), world["response"])
    assert found == []


@given("a stored demo video and match creations at the hourly limit")
def stored_video_at_the_limit(
    world: dict[str, Any], request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch
) -> None:
    """FEATURE_QUOTAS on and two creations an hour, set before the app is built."""
    monkeypatch.setenv("FEATURE_QUOTAS", "true")
    monkeypatch.setenv("MATCH_CREATIONS_PER_HOUR", str(CREATIONS_PER_HOUR))
    api: ApiDriver = request.getfixturevalue("api")
    ivy = api.as_user("ivy")
    match_id = api.run(create_match(ivy, "IT-05-05 quota walk"))
    api.run(upload_fixture(ivy, match_id))
    for i in range(CREATIONS_PER_HOUR - 1):
        api.run(create_match(ivy, f"IT-05-05 quota walk {i}"))
    world.update(api=api, match_id=match_id, engine=request.getfixturevalue("committed_db"))


@when("the owner reads the quota and is refused one more match")
def owner_reads_quota(world: dict[str, Any]) -> None:
    api: ApiDriver = world["api"]
    quota = api.request("ivy", "GET", QUOTA)
    assert quota.status_code == 200, quota.text
    assert quota.json()["storage"]["used_bytes"] > 0, "the video must be stored"
    assert quota.json()["match_creations"]["next_slot_at"] is not None, "must be at the limit"
    refused = api.request("ivy", "POST", contract.MATCHES, json={"title": "x", "format": "doubles"})
    assert refused.status_code == 429, refused.text
    world["response"] = {"quota": quota.json(), "refused": refused.json(),
                         "retry_after": refused.headers["Retry-After"]}  # fmt: skip


@then("no stored-video or rate-limit column the API returned is marked server-side only")
def no_server_side_quota_column_returned(world: dict[str, Any]) -> None:
    with world["engine"].connect() as conn:
        asset = conn.execute(
            text("SELECT * FROM media_assets WHERE match_id = :m"), {"m": world["match_id"]}
        ).mappings().one()  # fmt: skip
        oldest = conn.execute(
            text("SELECT min(at) FROM rate_limit_events WHERE key = :k"),
            {"k": account_creation_key(OwnerId(asset["owner_id"]))},
        ).scalar_one()
    assert oldest is not None, "no match creation was counted"
    # What the API computes from the column, not the raw value: oldest hit + window.
    derived = {"at": oldest + CREATION_WINDOW}
    response = world["response"]
    found = server_side_returned(world["map"], "media_assets", dict(asset), response)
    found += server_side_returned(world["map"], "rate_limit_events", derived, response)
    assert found == []


@given("a stored and probed demo video")
def stored_probed_video(world: dict[str, Any], api: ApiDriver, committed_db: Any) -> None:
    ivy = api.as_user("ivy")
    match_id = api.run(create_match(ivy, "IT-05-05 media link"))
    api.run(upload_fixture(ivy, match_id))
    contract.WORKER_RUN_UNTIL_IDLE.load()()
    world.update(api=api, match_id=match_id, engine=committed_db)


@when("the owner reads the account, the match and the video link")
def owner_reads_video_link(world: dict[str, Any]) -> None:
    api: ApiDriver = world["api"]
    reads = {
        "me": contract.ME,
        "match": contract.MATCH.format(match_id=world["match_id"]),
        "video": VIDEO.format(match_id=world["match_id"]),
    }
    world["response"] = {}
    for name, url in reads.items():
        got = api.request("ivy", "GET", url)
        assert got.status_code == 200, f"{url}: {got.status_code} {got.text}"
        world["response"][name] = got.json()
    assert world["response"]["video"]["url"], "the video link must be signed"


@then("no media, upload, job or account column the API returned is marked server-side only")
def no_server_side_media_column_returned(world: dict[str, Any]) -> None:
    me_id = world["response"]["me"]["id"]
    by_match = {"m": world["match_id"]}
    queries = {
        "media_assets": ("SELECT * FROM media_assets WHERE match_id = :m", by_match),
        "upload_sessions": ("SELECT * FROM upload_sessions WHERE match_id = :m", by_match),
        # Only the id copy: the probe job is written sub-ms after matches.updated_at (the
        # owner reads it), so a timestamp trace cannot tell them apart (_returned's limit).
        "jobs": ("SELECT match_id FROM jobs WHERE match_id = :m", by_match),
        "sessions": ("SELECT * FROM sessions WHERE account_id = :a", {"a": me_id}),
    }
    rows: list[tuple[str, dict[str, Any]]] = []
    with world["engine"].connect() as conn:
        for table, (sql, params) in queries.items():
            found = [dict(r) for r in conn.execute(text(sql), params).mappings()]
            assert found, f"no {table} row for the demo upload"
            rows += [(table, r) for r in found]
    rows += [(table, {"account_id": me_id}) for table in ACCOUNT_ID_COPIES]
    returned = [
        hit
        for table, row in rows
        for hit in server_side_returned(world["map"], table, row, world["response"])
    ]
    assert sorted(set(returned)) == []


@when("the database schema is walked")
def walk_schema(world: dict[str, Any]) -> None:
    world["columns"] = metadata_columns(all_models_metadata()) | live_columns(world["connection"])


@when("the backup artefacts are walked")
def walk_backups(world: dict[str, Any]) -> None:
    world["backup_items"] = backup_files(world["backups"])


@when("every store is walked")
def walk_everything(world: dict[str, Any]) -> None:
    with world["engine"].connect() as conn:
        columns = metadata_columns(all_models_metadata()) | live_columns(conn)
    world["columns"] = columns
    world["prefixes"] = prefixes(world["keys"])
    world["backup_items"] = backup_files(world["backups"])


@then("the planted column is reported as unclassified")
def planted_column_reported(world: dict[str, Any]) -> None:
    assert PLANTED_COLUMN in unclassified(world["map"], world["columns"])


@then("the planted file is reported as unclassified")
def planted_file_reported(world: dict[str, Any]) -> None:
    problems = backup_problems(world["map"], world["backup_items"])
    assert f"unclassified backup artefact: {PLANTED_FILE[1]}" in problems


@then("the check fails because no backup artefact was found")
def zero_artefacts_fail(world: dict[str, Any]) -> None:
    assert world["backup_items"] == set()
    assert backup_problems(world["map"], world["backup_items"]) == [NO_BACKUP_ARTEFACT]


@then("no table, column, bucket prefix or backup artefact is unclassified")
def nothing_unclassified(world: dict[str, Any]) -> None:
    assert MAP_PATH.is_file(), f"{MAP_PATH.relative_to(REPO)} does not exist"
    cmap = world["map"]
    columns: set[Item] = world["columns"]
    assert len(columns) > 100, "the schema walk found almost nothing"
    assert ("prefix", "originals/") in world["prefixes"], world["keys"]
    assert world["backup_items"], NO_BACKUP_ARTEFACT
    assert unclassified(cmap, columns | world["prefixes"]) == []
    assert backup_problems(cmap, world["backup_items"]) == []
    assert stale(cmap, columns, "column") == []
    assert stale(cmap, world["backup_items"], "backup") == []


@then("every class and every row has an encryption, a retention and an access rule")
def every_rule_present(world: dict[str, Any]) -> None:
    assert world["map"].classes, "the map defines no class"
    assert incomplete(world["map"]) == []
