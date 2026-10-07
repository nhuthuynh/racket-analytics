"""IT-03-10b (ST-042; SEC-R1S3-01; NFR-051, NFR-054; ASVS 8.2.x, 8.3.1): the media sandbox
worker may UPDATE only the columns the probe stage writes.

A compromised worker that can rewrite ``owner_id`` or ``object_key`` gets past the
``WHERE id = :id AND owner_id = :me`` control on every ID route. Negative cases first; each has
a positive control on a column the probe stage really writes (testing-strategy rule 8).
Real Postgres. QA folds these into IT-03-10 (test-change-requests.md, SEC-R1S3-01).
"""

from __future__ import annotations

from typing import Any

import pytest
import sqlalchemy as sa

from tests.integration.test_it_03_10_worker_grants import _denied, as_worker


@pytest.mark.parametrize(
    "statement",
    [
        "UPDATE matches SET owner_id = owner_id WHERE false",
        "UPDATE matches SET title = title WHERE false",
        "UPDATE matches SET rules_version = rules_version WHERE false",
        "UPDATE matches SET version = version WHERE false",
        "UPDATE media_assets SET owner_id = owner_id WHERE false",
        "UPDATE media_assets SET object_key = object_key WHERE false",
        "UPDATE media_assets SET match_id = match_id WHERE false",
    ],
    ids=["matches-owner", "matches-title", "matches-rules-version", "matches-version",
         "media-owner", "media-object-key", "media-match"],
)  # fmt: skip
def test_it_03_10b_the_worker_role_cannot_update_ownership_or_key_columns(
    db_engine: Any, statement: str
) -> None:
    _denied(db_engine, statement)


@pytest.mark.parametrize(
    "statement",
    [
        "UPDATE matches SET status = status, media_asset_id = media_asset_id,"
        " rejection_code = rejection_code, rejected_at = rejected_at,"
        " updated_at = updated_at WHERE false",
        "UPDATE media_assets SET probe_status = probe_status, updated_at = updated_at WHERE false",
        "SELECT 1 FROM matches WHERE false FOR UPDATE",
    ],
    ids=["matches-refusal-columns", "media-probe-columns", "matches-row-lock"],
)
def test_it_03_10b_the_worker_role_updates_the_columns_the_probe_writes(
    db_engine: Any, statement: str
) -> None:
    with as_worker(db_engine) as conn:
        conn.execute(sa.text(statement))
