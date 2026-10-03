"""Property-based tests for ManifestCheck (ST-011). Profile ``ci`` runs >= 1,000 examples."""

from __future__ import annotations

import pytest
from hypothesis import given
from hypothesis import strategies as st

from racket.dataset.manifest import Manifest, ManifestCheck

pytestmark = pytest.mark.unit

_segment = st.text(alphabet="abcdefghijklmnopqrstuvwxyz0123456789_", min_size=1, max_size=12)
paths = st.builds(
    lambda parts, ext: "/".join(parts) + ext,
    st.lists(_segment, min_size=1, max_size=3),
    st.sampled_from([".mp4", ".json"]),
)
shas = st.binary(min_size=32, max_size=32).map(bytes.hex)
file_sets = st.dictionaries(paths, shas, min_size=1, max_size=8)


def _manifest(files: dict[str, str], version: int = 1) -> Manifest:
    return Manifest.from_dict(
        {
            "id": "p",
            "version": version,
            "licence": "CC0-1.0",
            "consent_status": "synthetic",
            "files": [{"path": p, "sha256": h} for p, h in files.items()],
        }
    )


@given(file_sets)
def test_a_set_always_matches_its_own_manifest(files: dict[str, str]) -> None:
    assert ManifestCheck.check(_manifest(files), files).passed


@given(file_sets, st.data())
def test_any_single_hash_change_is_detected_and_named(
    files: dict[str, str], data: st.DataObject
) -> None:
    victim = data.draw(st.sampled_from(sorted(files)))
    new_sha = data.draw(shas.filter(lambda s: s != files[victim]))

    result = ManifestCheck.check(_manifest(files), {**files, victim: new_sha})

    assert [(p.kind, p.path) for p in result.problems] == [("changed", victim)]


@given(file_sets, paths, shas)
def test_any_added_file_is_detected_and_named(files: dict[str, str], extra: str, sha: str) -> None:
    if extra in files:
        return
    result = ManifestCheck.check(_manifest(files), {**files, extra: sha})

    assert [(p.kind, p.path) for p in result.problems] == [("unlisted", extra)]


@given(file_sets, file_sets)
def test_any_change_to_the_file_set_without_a_bump_fails(
    a: dict[str, str], b: dict[str, str]
) -> None:
    result = ManifestCheck.check_version_bump(base=_manifest(a), head=_manifest(b))

    assert result.passed == (a == b)
