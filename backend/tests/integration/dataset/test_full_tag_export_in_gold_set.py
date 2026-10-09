"""A Full Tag export is a gold-set label file that ``racket-manifest-check`` accepts (ST-052a;
FR-150, FR-151).

Integration: the session's ``full-tag-labels/v1`` document is written to real files of a
gold set (``gold-set-manifest/v1``) with real sha256 digests, then read back by the CLI
(``racket.dataset.cli.main``, the CI gate) through the filesystem adapter. Negative cases
first: a label file edited after export (a hitter not in the match) fails the gate and names
the file, while the session refuses the same edit, so it can never write that file.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

from racket.dataset.cli import main
from racket.dataset.full_tag import FullTagSession, LabelRefused
from tests.unit.dataset.test_gold_set import a_raw

pytestmark = pytest.mark.integration

PLAYERS = ("A1", "A2", "B1", "B2")
RALLY = {
    "type": "rally", "start_frame": 5, "end_frame": 100,
    "outcome": {"ending": "winner", "winning_side": "A", "responsible_player": "A1",
                "fault_kind": None},
}  # fmt: skip


def _export(clip: str) -> dict[str, Any]:
    session = FullTagSession(clip, 60, 120, PLAYERS).add(RALLY)
    session = session.add({"type": "hit", "frame": 10, "hitter": "A1"})
    session = session.add({"type": "bounce", "frame": 20, "visible": True, "court_xy_m": None})
    return session.export()


def _gold_set(root: Path, edit: Any = None) -> Path:
    """A five-clip gold set whose label files are Full Tag exports; ``edit(path, doc)`` may
    change a document before it is written."""
    raw = a_raw()
    files: dict[str, bytes] = {}
    for clip in raw["clips"]:
        files[clip["path"]] = f"synthetic clip {clip['path']}".encode()
        for key in ("label_file", "second_label_file"):
            if clip.get(key):
                doc = _export(clip["path"])
                if edit is not None:
                    edit(clip[key], doc)
                files[clip[key]] = json.dumps(doc).encode()
    for rel, data in files.items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_bytes(data)
    raw["files"] = [
        {"path": p, "sha256": hashlib.sha256(d).hexdigest()} for p, d in sorted(files.items())
    ]
    (root / "manifest.json").write_text(json.dumps(raw))
    return root


# --- negative cases first ----------------------------------------------------------------


def test_a_label_file_edited_to_an_unknown_hitter_fails_the_gate_and_names_the_file(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    def unknown_hitter(path: str, doc: dict[str, Any]) -> None:
        if path == "labels/c3.json":
            doc["rallies"][0]["events"][0]["hitter"] = "Z9"

    code = main([str(_gold_set(tmp_path, unknown_hitter))])

    assert code == 1
    failures = [line for line in capsys.readouterr().out.splitlines() if line.startswith("FAIL")]
    assert failures
    assert all("labels/c3.json" in line for line in failures)


def test_the_session_refuses_the_edit_that_would_fail_the_gate() -> None:
    session = FullTagSession("clips/c3.mp4", 60, 120, PLAYERS).add(RALLY)

    with pytest.raises(LabelRefused, match="Z9"):
        session.add({"type": "hit", "frame": 10, "hitter": "Z9"})
    assert session.export()["rallies"][0]["events"] == []


# --- positive case -----------------------------------------------------------------------


def test_a_gold_set_of_full_tag_exports_passes_the_gate(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code = main([str(_gold_set(tmp_path))])

    out = capsys.readouterr().out
    assert code == 0, out
    assert out.startswith(f"OK   {tmp_path}: gs-test v1, gold set (vision)")
