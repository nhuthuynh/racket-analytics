"""SEC-S3-TM-01 / T-DL-3 (deletion-and-purge.md §4.6 (1)): the purge deletes only typed refs
whose shape is the server's generated name. Negative cases first."""

from __future__ import annotations

import uuid

import pytest

from racket.video_ingest.domain.object_refs import (
    MultipartRef,
    OriginalKey,
    StagingPrefix,
    UnsafeObjectRef,
)

pytestmark = [pytest.mark.unit]

HEX = "0123456789abcdef0123456789abcdef"


@pytest.mark.parametrize(
    "key",
    ["", "originals/", f"originals/{HEX[:31]}", f"originals/{HEX}0", f"originals/{HEX.upper()}",
     f"staging/{HEX}/", f"originals/{HEX}/", f"originals/../{HEX}", f" originals/{HEX}", None, 7],
)  # fmt: skip
def test_an_original_key_of_another_shape_is_refused(key: object) -> None:
    with pytest.raises(UnsafeObjectRef):
        OriginalKey(key)  # type: ignore[arg-type]


def test_an_original_key_of_the_generated_shape_is_accepted() -> None:
    assert OriginalKey(f"originals/{HEX}").key == f"originals/{HEX}"


def test_a_staging_prefix_is_built_from_the_upload_id_only() -> None:
    upload = uuid.UUID(HEX)
    assert StagingPrefix.of(upload).prefix == f"staging/{HEX}/"
    with pytest.raises(UnsafeObjectRef):
        StagingPrefix("staging/../")
    with pytest.raises(UnsafeObjectRef):
        StagingPrefix.of("not-a-uuid")  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("key", "upload_id"),
    [(f"originals/{HEX}", ""), (f"originals/{HEX}", None), ("originals/x", "u1"),
     (f"staging/{HEX}/12", "u1"), (f"staging/{HEX}/{0:021d}", "u1")],
)  # fmt: skip
def test_a_multipart_ref_needs_a_safe_key_and_an_upload_id(key: str, upload_id: object) -> None:
    with pytest.raises(UnsafeObjectRef):
        MultipartRef(key, upload_id)  # type: ignore[arg-type]


def test_a_multipart_ref_on_an_original_or_a_chunk_is_accepted() -> None:
    assert MultipartRef(f"originals/{HEX}", "u1").upload_id == "u1"
    assert MultipartRef(f"staging/{HEX}/{0:020d}", "u1").key.endswith("0" * 20)
