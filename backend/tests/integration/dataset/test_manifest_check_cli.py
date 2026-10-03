"""ManifestCheck against real files on disk and through its CLI (ST-011, FR-151, NFR-078).

Integration (filesystem boundary); no services needed.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from racket.dataset.cli import main
from racket.dataset.filesystem import hash_set

pytestmark = pytest.mark.integration


def _write_set(root: Path, files: dict[str, bytes], version: int = 1) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    for name, data in files.items():
        (root / name).parent.mkdir(parents=True, exist_ok=True)
        (root / name).write_bytes(data)
    manifest = {
        "id": "tmp-set",
        "version": version,
        "licence": "CC0-1.0",
        "consent_status": "synthetic",
        "files": [
            {"path": n, "sha256": hashlib.sha256(d).hexdigest()} for n, d in sorted(files.items())
        ],
    }
    (root / "manifest.json").write_text(json.dumps(manifest))
    return root


def test_hash_set_excludes_the_manifest_and_uses_posix_relative_paths(tmp_path: Path) -> None:
    root = _write_set(tmp_path / "s", {"clip.mp4": b"abc", "sub/labels.json": b"{}"})

    hashes = hash_set(root)

    assert hashes == {
        "clip.mp4": hashlib.sha256(b"abc").hexdigest(),
        "sub/labels.json": hashlib.sha256(b"{}").hexdigest(),
    }


def test_cli_fails_and_names_changed_file(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = _write_set(tmp_path / "s", {"clip.mp4": b"abc"})
    (root / "clip.mp4").write_bytes(b"tampered")

    code = main([str(root)])

    assert code == 1
    assert "clip.mp4" in capsys.readouterr().out


def test_cli_fails_and_names_unlisted_file(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = _write_set(tmp_path / "s", {"clip.mp4": b"abc"})
    (root / "sneaky.mp4").write_bytes(b"x")

    code = main([str(root)])

    assert code == 1
    assert "sneaky.mp4" in capsys.readouterr().out


def test_cli_rejects_malformed_manifest_with_exit_code_2(tmp_path: Path) -> None:
    root = tmp_path / "s"
    root.mkdir()
    (root / "manifest.json").write_text(json.dumps({"id": "x"}))

    assert main([str(root)]) == 2


def test_cli_rejects_symlinks_in_a_set(tmp_path: Path) -> None:
    root = _write_set(tmp_path / "s", {"clip.mp4": b"abc"})
    (root / "link.mp4").symlink_to(root / "clip.mp4")

    assert main([str(root)]) == 1


def test_cli_version_rule_against_base_manifest(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    base = _write_set(tmp_path / "base", {"clip.mp4": b"abc"}, version=1)
    head = _write_set(tmp_path / "head", {"clip.mp4": b"changed"}, version=1)

    code = main([str(head), "--base-manifest", str(base / "manifest.json")])

    assert code == 1
    out = capsys.readouterr().out
    assert "clip.mp4" in out
    assert "version_not_bumped" in out


def test_cli_passes_for_intact_set(tmp_path: Path) -> None:
    base = _write_set(tmp_path / "base", {"clip.mp4": b"abc"}, version=1)
    head = _write_set(tmp_path / "head", {"clip.mp4": b"new"}, version=2)

    assert main([str(head), "--base-manifest", str(base / "manifest.json")]) == 0
