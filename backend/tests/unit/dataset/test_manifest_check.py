"""ManifestCheck unit tests (ST-011, FR-151, NFR-078; sprint-00 §5 TDD order).

Pure domain: no disk, no network. Hashes are given as data.
"""

from __future__ import annotations

import pytest

from racket.dataset.manifest import Manifest, ManifestCheck, ManifestFormatError

pytestmark = pytest.mark.unit

SHA_A = "a" * 64
SHA_B = "b" * 64
SHA_C = "c" * 64


def a_manifest(files: dict[str, str], version: int = 1) -> Manifest:
    return Manifest.from_dict(
        {
            "id": "synthetic-60s",
            "version": version,
            "licence": "CC0-1.0",
            "consent_status": "synthetic",
            "files": [{"path": p, "sha256": h} for p, h in files.items()],
        }
    )


def test_changed_file_fails_and_names_the_file() -> None:
    manifest = a_manifest({"clip.mp4": SHA_A, "notes.txt": SHA_B})

    result = ManifestCheck.check(manifest, actual={"clip.mp4": SHA_C, "notes.txt": SHA_B})

    assert not result.passed
    assert [(p.kind, p.path) for p in result.problems] == [("changed", "clip.mp4")]


def test_unlisted_file_fails_and_names_the_file() -> None:
    manifest = a_manifest({"clip.mp4": SHA_A})

    result = ManifestCheck.check(manifest, actual={"clip.mp4": SHA_A, "extra.mp4": SHA_B})

    assert not result.passed
    assert [(p.kind, p.path) for p in result.problems] == [("unlisted", "extra.mp4")]


def test_file_listed_but_absent_fails_and_names_the_file() -> None:
    manifest = a_manifest({"clip.mp4": SHA_A, "labels.json": SHA_B})

    result = ManifestCheck.check(manifest, actual={"clip.mp4": SHA_A})

    assert not result.passed
    assert [(p.kind, p.path) for p in result.problems] == [("missing", "labels.json")]


def test_matching_set_passes() -> None:
    manifest = a_manifest({"clip.mp4": SHA_A, "notes.txt": SHA_B})

    result = ManifestCheck.check(manifest, actual={"clip.mp4": SHA_A, "notes.txt": SHA_B})

    assert result.passed
    assert result.problems == ()


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("sha256", "not-a-hash"),
        ("sha256", "A" * 64),  # upper case is rejected so equal hashes compare equal
        ("path", "../escape.mp4"),
        ("path", "/abs/clip.mp4"),
        ("path", ""),
    ],
)
def test_malformed_file_entry_is_rejected(field: str, value: str) -> None:
    entry = {"path": "clip.mp4", "sha256": SHA_A, field: value}

    with pytest.raises(ManifestFormatError):
        Manifest.from_dict(
            {
                "id": "x",
                "version": 1,
                "licence": "CC0-1.0",
                "consent_status": "synthetic",
                "files": [entry],
            }
        )


@pytest.mark.parametrize("missing", ["id", "version", "licence", "consent_status", "files"])
def test_manifest_without_required_field_is_rejected(missing: str) -> None:
    data = {
        "id": "x",
        "version": 1,
        "licence": "CC0-1.0",
        "consent_status": "synthetic",
        "files": [{"path": "clip.mp4", "sha256": SHA_A}],
    }
    del data[missing]

    with pytest.raises(ManifestFormatError, match=missing):
        Manifest.from_dict(data)


@pytest.mark.parametrize("version", [0, -1, "1", 1.5, True])
def test_version_must_be_a_positive_integer(version: object) -> None:
    with pytest.raises(ManifestFormatError, match="version"):
        Manifest.from_dict(
            {
                "id": "x",
                "version": version,
                "licence": "CC0-1.0",
                "consent_status": "synthetic",
                "files": [],
            }
        )


def test_duplicate_path_is_rejected() -> None:
    with pytest.raises(ManifestFormatError, match=r"clip\.mp4"):
        Manifest.from_dict(
            {
                "id": "x",
                "version": 1,
                "licence": "CC0-1.0",
                "consent_status": "synthetic",
                "files": [
                    {"path": "clip.mp4", "sha256": SHA_A},
                    {"path": "clip.mp4", "sha256": SHA_B},
                ],
            }
        )


# --- version bump rule: a hash may change only together with a higher version (FR-151) ---


def test_hash_changed_in_manifest_without_version_bump_fails_naming_file() -> None:
    base = a_manifest({"clip.mp4": SHA_A, "notes.txt": SHA_B}, version=1)
    head = a_manifest({"clip.mp4": SHA_C, "notes.txt": SHA_B}, version=1)

    result = ManifestCheck.check_version_bump(base=base, head=head)

    assert not result.passed
    assert [(p.kind, p.path) for p in result.problems] == [("version_not_bumped", "clip.mp4")]


def test_file_added_or_removed_without_version_bump_fails() -> None:
    base = a_manifest({"clip.mp4": SHA_A, "old.txt": SHA_B}, version=2)
    head = a_manifest({"clip.mp4": SHA_A, "new.txt": SHA_C}, version=2)

    result = ManifestCheck.check_version_bump(base=base, head=head)

    assert [(p.kind, p.path) for p in result.problems] == [
        ("version_not_bumped", "new.txt"),
        ("version_not_bumped", "old.txt"),
    ]


def test_version_going_backwards_fails() -> None:
    base = a_manifest({"clip.mp4": SHA_A}, version=3)
    head = a_manifest({"clip.mp4": SHA_A}, version=2)

    result = ManifestCheck.check_version_bump(base=base, head=head)

    assert [(p.kind, p.path) for p in result.problems] == [("version_decreased", "")]


def test_hash_change_with_version_bump_passes() -> None:
    base = a_manifest({"clip.mp4": SHA_A}, version=1)
    head = a_manifest({"clip.mp4": SHA_C}, version=2)

    assert ManifestCheck.check_version_bump(base=base, head=head).passed


def test_unchanged_manifest_passes_version_rule() -> None:
    base = a_manifest({"clip.mp4": SHA_A}, version=1)

    assert ManifestCheck.check_version_bump(base=base, head=base).passed


def test_problem_describes_itself_for_ci_output() -> None:
    manifest = a_manifest({"clip.mp4": SHA_A})

    result = ManifestCheck.check(manifest, actual={"clip.mp4": SHA_B})

    assert "clip.mp4" in result.problems[0].describe()
    assert "changed" in result.problems[0].describe()
