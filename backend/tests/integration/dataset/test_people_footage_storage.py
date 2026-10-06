"""Footage that shows people never lives where git can commit it (SEC-S2-TM-06, QA-RV2-12).

Consent form item 4 (docs/data/gold-capture-protocol.md §3) promises private storage that
only the team can read; the repository is public. ``racket-manifest-check`` therefore
refuses a clip with ``shows_people: true`` whose file is tracked by git or not git-ignored
(``people_in_git``). Integration: real ``git`` and files in a temporary repository.
Negative cases first.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest

from racket.dataset.cli import main
from racket.dataset.filesystem import git_exposed
from tests.unit.dataset.test_gold_set import a_clip, a_raw

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(shutil.which("git") is None, reason="needs the git binary"),
]

CLIP = b"people-clip"


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@example.invalid", *args],
        check=True,
        capture_output=True,
    )


def _repo(tmp_path: Path, gitignore: str = "") -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    if gitignore:
        (repo / ".gitignore").write_text(gitignore)
    return repo


def _people_set(root: Path, *, shows_people: bool = True, gold: bool = False) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / "clips").mkdir(exist_ok=True)
    (root / "clips" / "c1.mp4").write_bytes(CLIP)
    manifest: dict[str, Any] = {
        "id": "people-set",
        "version": 1,
        "licence": "team-private",
        "consent_status": "consented",
        "files": [{"path": "clips/c1.mp4", "sha256": hashlib.sha256(CLIP).hexdigest()}],
        "clips": [
            {
                "path": "clips/c1.mp4",
                "shows_people": shows_people,
                "consent_record": "CF-2026-001" if shows_people else None,
            }
        ],
    }
    (root / "manifest.json").write_text(json.dumps(manifest))
    return root


# --- negative cases first --------------------------------------------------------------


def test_a_people_clip_tracked_by_git_is_refused(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repo = _repo(tmp_path)
    root = _people_set(repo / "fixtures" / "s")
    _git(repo, "add", "fixtures/s/clips/c1.mp4")

    code = main([str(root)])

    assert code == 1
    out = capsys.readouterr().out
    assert "clips/c1.mp4" in out
    assert "[people_in_git]" in out


def test_a_people_clip_git_could_commit_is_refused(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Untracked but not ignored: one ``git add`` away from the public repository."""
    repo = _repo(tmp_path)
    root = _people_set(repo / "fixtures" / "s")

    assert main([str(root)]) == 1
    assert "[people_in_git]" in capsys.readouterr().out


def test_a_tracked_people_clip_is_refused_even_when_a_gitignore_matches_it(
    tmp_path: Path,
) -> None:
    repo = _repo(tmp_path)
    root = _people_set(repo / "private" / "s")
    _git(repo, "add", "private/s/clips/c1.mp4")
    (repo / ".gitignore").write_text("/private/\n")

    assert main([str(root)]) == 1


def test_a_people_clip_in_a_gold_set_under_git_is_refused(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A gold-set manifest v1 clip with shows_people is held to the same rule."""
    repo = _repo(tmp_path)
    root = repo / "fixtures" / "gold" / "g"
    raw = a_raw(consent_status="consented")
    raw["clips"][0] = a_clip(
        1, "V1", shows_people=True, consent_record="CF-2026-001", consent_jurisdiction="US"
    )
    (root / "clips").mkdir(parents=True)
    (root / "clips" / "c1.mp4").write_bytes(CLIP)
    (root / "manifest.json").write_text(json.dumps(raw))

    code = main([str(root)])

    assert code == 1
    lines = capsys.readouterr().out.splitlines()
    assert any("clips/c1.mp4: " in line and "[people_in_git]" in line for line in lines)


# --- positive cases ----------------------------------------------------------------------


def test_a_people_clip_in_a_git_ignored_directory_passes(tmp_path: Path) -> None:
    repo = _repo(tmp_path, gitignore="/.local/\n")
    root = _people_set(repo / ".local" / "gold" / "s")

    assert main([str(root)]) == 0


def test_a_people_clip_outside_any_git_repository_passes(tmp_path: Path) -> None:
    root = _people_set(tmp_path / "private-store" / "s")

    assert main([str(root)]) == 0


def test_a_clip_without_people_may_be_committed(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    root = _people_set(repo / "fixtures" / "s", shows_people=False)
    _git(repo, "add", "fixtures/s")

    assert main([str(root)]) == 0


def test_without_a_git_binary_every_people_clip_counts_as_exposed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Fail closed: the check never passes people footage because it could not ask git."""
    monkeypatch.setattr("racket.dataset.filesystem.shutil.which", lambda _name: None)

    assert git_exposed(tmp_path, ["clips/c1.mp4"]) == frozenset({"clips/c1.mp4"})
