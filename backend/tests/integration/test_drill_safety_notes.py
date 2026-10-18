"""FIX-04-1d (G04-05 (e); QD-DR-04; drill-review-checklist C5): CLI <-> files, safety notes.

Root cause: the lint had no QD-DR-04 rule (C5 was left to the coach's reading), and the ST-058c
mechanical C5 check read only ``summary`` and ``setup``, so ``pb.volley.line-volleys-no-step-in@1``
(skill ``footwork``) was reviewed with empty ``safety_notes``.

* A ``coach-reviewed`` drill whose content mentions a C5 trigger (the G04-05 (e) pattern
  ``lob|div(e|ing)|sprint|footwork``) and has empty ``safety_notes`` fails, rc 1, naming the
  drill and "safety notes missing".
* A ``draft`` drill, and a reviewed drill ``deprecated_by`` a newer version, are not handed to
  players and pass.
* The library ``content/drills``: no current (latest version, ``coach-reviewed``/``verified``,
  not deprecated) drill with a trigger has empty ``safety_notes``; checked by its own scan, so
  it does not depend on the lint rule it guards.
"""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path
from typing import Any

import pytest

from racket.coaching.drills.lock import LOCK_NAME, lock_entries, render_lock
from tests.integration.test_it_03_14_drill_lint import LIBRARY, LINT, _drills
from tests.support.paths import REPO

SAFETY = REPO / "backend" / "tests" / "fixtures" / "drills-safety"
TRIGGER = re.compile(r"lob|div(e|ing)|sprint|footwork", re.IGNORECASE)
REVIEWED = ("coach-reviewed", "verified")
LIFECYCLE = ("review_status", "deprecated_by", "safety_notes")


def _lint(path: Path, capsys: pytest.CaptureFixture[str]) -> tuple[int, str]:
    capsys.readouterr()
    rc = LINT.load()([str(path)])
    out, err = capsys.readouterr()
    return int(rc), out + err


def library_with(files: list[Path], folder: Path) -> Path:
    """A library folder holding ``files`` (one drill dir each) and a matching lock."""
    docs = []
    for f in files:
        doc = json.loads(f.read_text())
        target = folder / doc["id"] / f"v{doc['version']}.json"
        target.parent.mkdir(parents=True)
        shutil.copyfile(f, target)
        docs.append(doc)
    (folder / LOCK_NAME).write_text(render_lock(lock_entries(docs)))
    return folder


def missing_safety_notes(folder: Path) -> list[str]:
    """``id@version`` of every current reviewed drill with a C5 trigger and no safety notes."""
    latest: dict[str, dict[str, Any]] = {}
    for p in _drills(folder):
        doc = json.loads(p.read_text())
        if isinstance(doc, dict) and "id" in doc:
            if doc["id"] not in latest or doc["version"] > latest[doc["id"]]["version"]:
                latest[doc["id"]] = doc
    found = []
    for d in latest.values():
        if d.get("review_status") not in REVIEWED or d.get("deprecated_by"):
            continue
        content = json.dumps({k: v for k, v in d.items() if k not in LIFECYCLE})
        if TRIGGER.search(content) and not str(d.get("safety_notes", "")).strip():
            found.append(f"{d['id']}@{d['version']}")
    return sorted(found)


def test_a_reviewed_footwork_drill_without_safety_notes_fails(
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = SAFETY / "reviewed-footwork-no-notes.json"
    rc, out = _lint(path, capsys)
    assert rc == 1, out
    assert "pb.safety.reviewed-footwork" in out, out
    assert "safety notes missing" in out.lower(), out


def test_draft_and_deprecated_drills_pass(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    folder = library_with(
        [SAFETY / "draft-footwork-no-notes.json", SAFETY / "deprecated-footwork-no-notes.json"],
        tmp_path / "drills",
    )
    rc, out = _lint(folder, capsys)
    assert rc == 0, out


def test_no_current_reviewed_drill_of_the_library_misses_safety_notes() -> None:
    assert missing_safety_notes(LIBRARY) == []


def test_the_library_still_passes_the_lint(capsys: pytest.CaptureFixture[str]) -> None:
    rc, out = _lint(LIBRARY, capsys)
    assert rc == 0, out
