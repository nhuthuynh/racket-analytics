"""Consent rule of the manifest check (ST-025, OQ-06 / ADR 0023; sprint-01 §14.3.9).

A fixture or gold clip that shows people must carry a consent record. Pure domain: no disk.
Per-clip entries follow the QA seam in tests/support/contract.py (phones-v1):
{"path", "device_model", "fps", "vfr", "shows_people", "consent_record"}.
"""

from __future__ import annotations

from typing import Any

import pytest

from racket.dataset.manifest import Manifest, ManifestCheck, ManifestFormatError

pytestmark = pytest.mark.unit

SHA_A = "a" * 64
SHA_B = "b" * 64


def a_clip(path: str = "clip.mp4", **overrides: Any) -> dict[str, Any]:
    clip: dict[str, Any] = {
        "path": path,
        "device_model": "test-phone",
        "fps": 60,
        "vfr": False,
        "shows_people": False,
        "consent_record": None,
    }
    clip.update(overrides)
    return clip


def a_manifest(clips: list[dict[str, Any]], files: dict[str, str] | None = None) -> Manifest:
    files = files if files is not None else {"clip.mp4": SHA_A}
    return Manifest.from_dict(
        {
            "id": "phones-v1",
            "version": 1,
            "licence": "CC0-1.0",
            "consent_status": "synthetic",
            "files": [{"path": p, "sha256": h} for p, h in files.items()],
            "clips": clips,
        }
    )


# --- negative cases first -------------------------------------------------------------


def test_clip_with_people_and_no_consent_record_fails_and_names_the_file() -> None:
    manifest = a_manifest([a_clip(shows_people=True, consent_record=None)])

    result = ManifestCheck.check(manifest, actual={"clip.mp4": SHA_A})

    assert not result.passed
    assert [(p.kind, p.path) for p in result.problems] == [("consent_missing", "clip.mp4")]
    assert "clip.mp4" in result.problems[0].describe()


@pytest.mark.parametrize("blank", ["", "   "])
def test_blank_consent_record_counts_as_missing(blank: str) -> None:
    manifest = a_manifest([a_clip(shows_people=True, consent_record=blank)])

    result = ManifestCheck.check(manifest, actual={"clip.mp4": SHA_A})

    assert [p.kind for p in result.problems] == ["consent_missing"]


def test_clip_entry_for_a_file_not_in_the_manifest_files_fails() -> None:
    manifest = a_manifest([a_clip(path="other.mov")])

    result = ManifestCheck.check(manifest, actual={"clip.mp4": SHA_A})

    assert [(p.kind, p.path) for p in result.problems] == [("clip_not_in_files", "other.mov")]


@pytest.mark.parametrize("field", ["path", "shows_people", "consent_record"])
def test_clip_entry_missing_a_consent_field_is_malformed(field: str) -> None:
    clip = a_clip()
    del clip[field]

    with pytest.raises(ManifestFormatError):
        a_manifest([clip])


@pytest.mark.parametrize("value", ["yes", 1, None])
def test_shows_people_must_be_a_boolean(value: object) -> None:
    with pytest.raises(ManifestFormatError):
        a_manifest([a_clip(shows_people=value)])


def test_consent_record_must_be_a_string_or_null() -> None:
    with pytest.raises(ManifestFormatError):
        a_manifest([a_clip(shows_people=True, consent_record=42)])


def test_duplicate_clip_entries_are_malformed() -> None:
    with pytest.raises(ManifestFormatError):
        a_manifest([a_clip(), a_clip()])


def test_clips_must_be_a_list() -> None:
    with pytest.raises(ManifestFormatError):
        a_manifest({"clip.mp4": a_clip()})  # type: ignore[arg-type]


# --- positive controls (testing-strategy, retro 0 L4) ------------------------------------


def test_clip_with_people_and_a_consent_record_passes() -> None:
    manifest = a_manifest([a_clip(shows_people=True, consent_record="consent/2026-10-05-team.pdf")])

    assert ManifestCheck.check(manifest, actual={"clip.mp4": SHA_A}).passed


def test_clip_without_people_needs_no_consent_record() -> None:
    manifest = a_manifest([a_clip(shows_people=False, consent_record=None)])

    assert ManifestCheck.check(manifest, actual={"clip.mp4": SHA_A}).passed


def test_manifest_without_clips_is_unchanged_by_the_rule() -> None:
    manifest = Manifest.from_dict(
        {
            "id": "synthetic-60s",
            "version": 1,
            "licence": "CC0-1.0",
            "consent_status": "synthetic",
            "files": [{"path": "clip.mp4", "sha256": SHA_A}],
        }
    )

    assert ManifestCheck.check(manifest, actual={"clip.mp4": SHA_A}).passed
    assert manifest.clips == ()


def test_consent_problems_follow_the_hash_problems() -> None:
    manifest = a_manifest(
        [
            a_clip(path="a.mp4", shows_people=True),
            a_clip(path="b.mov", shows_people=False),
        ],
        files={"a.mp4": SHA_A, "b.mov": SHA_B},
    )

    result = ManifestCheck.check(manifest, actual={"a.mp4": SHA_A, "b.mov": SHA_A})

    assert [(p.kind, p.path) for p in result.problems] == [
        ("changed", "b.mov"),
        ("consent_missing", "a.mp4"),
    ]
