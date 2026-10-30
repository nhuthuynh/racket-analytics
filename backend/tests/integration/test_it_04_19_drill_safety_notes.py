"""IT-04-19 (QA-VERIFY04R3-09; FR-140, FR-141; QD-DR-04; checklist C5; G04-05 e): every reviewed,
current drill tagged with a movement skill carries a safety note, over the real ``content/drills``.

Boundaries: CLI <-> files (``racket-drill-lint`` fails naming the drill and "no safety note")
and files -> plan domain (``Drill.from_document``: the deprecated version is never offered).

Negative first: a copy of the library as VERIFY-04-r3 measured it (no
``pb.volley.line-volleys-no-step-in@2``, and v1 not deprecated) fails naming that drill and only
that drill. Then the library passes, its latest version has a coach-reviewed safety note, and the
G04-05 (e) safety method, scoped to the reviewed library of G04-05 (a), finds nothing missing;
every line of the unscoped grep is a draft or a deprecated, locked version. Written red first.
"""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path
from typing import Any

import pytest

from racket.coaching.drills.lock import parse_lock, render_lock
from racket.coaching.plan.domain import Drill, Preferences
from tests.integration.test_it_03_14_drill_lint import LIBRARY, LINT

pytestmark = pytest.mark.integration

DRILL = "pb.volley.line-volleys-no-step-in"
REVIEWED = ("coach-reviewed", "verified")
# The G04-05 (e) method's grep (goal-scorecard §4): grep -liE 'lob|div(e|ing)|sprint|footwork'
SAFETY_TERMS = re.compile(r"lob|div(e|ing)|sprint|footwork", re.IGNORECASE)
PAIRS_HALF_COURT = Preferences(
    minutes_per_session=30,
    sessions_per_week=3,
    players_available=2,
    equipment=frozenset({"half_court"}),
    level="beginner",
)


def _lint(capsys: pytest.CaptureFixture[str], path: Path) -> tuple[int, str]:
    capsys.readouterr()
    rc = LINT.load()([str(path)])
    out, err = capsys.readouterr()
    return int(rc), out + err


def _fails(out: str) -> list[str]:
    return [line for line in out.splitlines() if line.startswith("FAIL ")]


def _files(root: Path) -> list[Path]:
    return sorted(p for p in root.rglob("v*.json"))


def _latest(root: Path) -> list[Path]:
    """The method's file set of G04-05 (a): the highest ``v<n>.json`` of each drill folder."""
    found = []
    for folder in sorted(d for d in root.iterdir() if d.is_dir()):
        versions = sorted(folder.glob("v*.json"), key=lambda p: int(p.stem[1:]))
        if versions:
            found.append(versions[-1])
    return found


def _doc(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------- negative case first
def test_it_04_19_the_verify_04_r3_library_fails_naming_the_volley_drill(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    copy = tmp_path / "drills"
    shutil.copytree(LIBRARY, copy)
    for later in (copy / DRILL).glob("v*.json"):
        if later.name != "v1.json":
            later.unlink()
    v1 = copy / DRILL / "v1.json"
    doc = _doc(v1)
    doc.pop("deprecated_by", None)
    v1.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    lock_path = copy / "library.lock"
    lock = parse_lock(lock_path.read_text(encoding="utf-8"), str(lock_path))
    kept = {k: v for k, v in lock.items() if not (k.startswith(f"{DRILL}@") and k != f"{DRILL}@1")}
    lock_path.write_text(render_lock(kept), encoding="utf-8")

    rc, out = _lint(capsys, copy)
    assert rc == 1, out
    found = _fails(out)
    assert len(found) == 1, out
    assert f"drill {DRILL}: no safety note" in found[0], out


# ---------------------------------------------------------------- the library passes
def test_it_04_19_the_library_passes_the_lint(capsys: pytest.CaptureFixture[str]) -> None:
    rc, out = _lint(capsys, LIBRARY)
    assert rc == 0, out


def test_it_04_19_the_volley_drill_has_a_reviewed_version_with_a_safety_note() -> None:
    versions = {_doc(p)["version"]: _doc(p) for p in (LIBRARY / DRILL).glob("v*.json")}
    latest = versions[max(versions)]
    assert max(versions) >= 2, sorted(versions)
    assert latest["review_status"] in REVIEWED
    assert "deprecated_by" not in latest
    assert latest["safety_notes"].strip()
    assert versions[1]["deprecated_by"] == f"{DRILL}@{max(versions)}"


def test_it_04_19_the_scoped_safety_method_finds_nothing_missing() -> None:
    """G04-05 (e) over G04-05 (a)'s population: latest version, reviewed, not deprecated."""
    missing = [
        doc["id"]
        for path in _latest(LIBRARY)
        if SAFETY_TERMS.search(path.read_text(encoding="utf-8"))
        and (doc := _doc(path))["review_status"] in REVIEWED
        and "deprecated_by" not in doc
        and doc["safety_notes"] == ""
    ]
    assert missing == []


def test_it_04_19_every_unscoped_grep_line_is_a_draft_or_a_deprecated_version() -> None:
    """The VERIFY-04-r3 grep over every ``v*.json``: each remaining line is outside G04-05 (a)."""
    lines = [
        (path, doc)
        for path in _files(LIBRARY)
        if SAFETY_TERMS.search(path.read_text(encoding="utf-8"))
        and (doc := _doc(path))["safety_notes"] == ""
    ]
    assert lines, "the classification needs the grep's lines"
    current = [
        f"{doc['id']}@{doc['version']}"
        for _, doc in lines
        if doc["review_status"] in REVIEWED and "deprecated_by" not in doc
    ]
    assert current == []


# ---------------------------------------------------------------- files -> plan domain
def test_it_04_19_the_plan_offers_only_the_version_with_the_safety_note() -> None:
    fitting = [
        drill.ref
        for path in (LIBRARY / DRILL).glob("v*.json")
        if (drill := Drill.from_document(_doc(path))).fits(PAIRS_HALF_COURT)
    ]
    newest = max(_doc(p)["version"] for p in (LIBRARY / DRILL).glob("v*.json"))
    assert fitting == [f"{DRILL}@{newest}"]
    assert newest >= 2
