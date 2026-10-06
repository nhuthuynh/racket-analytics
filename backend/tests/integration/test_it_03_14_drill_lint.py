"""IT-03-14 (ST-053; FR-140): CLI <-> files, the drill library lint.

* The valid fixture library (``content/drills``) passes: exit 0.
* Each FR-140 negative fixture fails, exit 1, and the output names the drill id and the
  reason. Fixture files are named by rule (``<rule>.json`` in ``backend/tests/fixtures/
  drills-invalid/``, the scorecard G03-09 folder) so the expected reason is known per file:
  unknown metric, progression cycle, duration over 45, criterion without a number, no source.
* Independently of those fixtures, a copy of a valid drill whose target metric is changed to
  "AN-99", or whose duration is 46 minutes, fails naming the drill (so the lint is not only
  right on the files written with it).
* A deprecated drill keeps its content: the lint fails if a drill version listed as deprecated
  has no file (deprecate, never delete).

The CLI is ``racket-drill-lint`` (``racket.coaching.drills.lint:main``), per ST-053's card.
Written red first (QA-ACC-3): ``red_until`` ST-053.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

import pytest

from tests.support.contract import Seam
from tests.support.paths import REPO

pytestmark = [pytest.mark.red_until(story="ST-053")]

LINT = Seam("racket.coaching.drills.lint:main", "ST-053", "main(argv: list[str]) -> int")
LIBRARY = REPO / "content" / "drills"
INVALID = REPO / "backend" / "tests" / "fixtures" / "drills-invalid"
REASONS = {
    "unknown-metric": "unknown metric",
    "progression-cycle": "progression cycle",
    "duration-over-45": "duration over 45",
    "criterion-no-number": "criterion no number",
    "no-source": "no source",
}


def _lint(path: Path, capsys: pytest.CaptureFixture[str]) -> tuple[int, str]:
    capsys.readouterr()
    rc = LINT.load()([str(path)])
    out, err = capsys.readouterr()
    return int(rc), out + err


def _drills(folder: Path) -> list[Path]:
    if not folder.is_dir():
        return []
    return sorted(p for p in folder.rglob("*.json") if p.name != "schema.json")


def _find_key(doc: Any, test: Any) -> list[str] | None:
    """The path to the first value for which ``test(key, value)`` holds."""
    if isinstance(doc, dict):
        for key, value in doc.items():
            if test(key, value):
                return [key]
            inner = _find_key(value, test)
            if inner is not None:
                return [key, *inner]
    return None


def _set(doc: dict[str, Any], path: list[str], value: Any) -> None:
    for key in path[:-1]:
        doc = doc[key]
    doc[path[-1]] = value


def test_it_03_14_the_valid_library_passes(capsys: pytest.CaptureFixture[str]) -> None:
    assert _drills(LIBRARY), f"no drill files under {LIBRARY}"
    rc, out = _lint(LIBRARY, capsys)
    assert rc == 0, out


@pytest.mark.parametrize("rule", sorted(REASONS))
def test_it_03_14_each_fr_140_rule_fails_naming_the_drill_and_reason(
    rule: str, capsys: pytest.CaptureFixture[str]
) -> None:
    path = INVALID / f"{rule}.json"
    assert path.exists(), f"missing negative fixture {path.relative_to(REPO)}"
    drill_id = json.loads(path.read_text())["id"]
    rc, out = _lint(path, capsys)
    assert rc == 1, out
    assert drill_id in out, f"the failure does not name drill {drill_id!r}: {out}"
    assert REASONS[rule] in out.lower(), f"the failure does not say {REASONS[rule]!r}: {out}"


@pytest.mark.parametrize(
    ("change", "reason"),
    [("metric", "unknown metric"), ("duration", "duration over 45")],
)
def test_it_03_14_a_mutated_valid_drill_fails(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], change: str, reason: str
) -> None:
    drills = _drills(LIBRARY)
    assert drills, f"no drill files under {LIBRARY}"
    source = drills[0]
    doc = json.loads(source.read_text())
    if change == "metric":
        path = _find_key(
            doc,
            lambda k, v: isinstance(v, list) and any(str(x).startswith("AN-") for x in v),
        )
        assert path, "no target-metric list in the drill"
        _set(doc, path, ["AN-99"])
    else:
        path = _find_key(doc, lambda k, v: "duration" in k and isinstance(v, int | float))
        assert path, "no duration field in the drill"
        _set(doc, path, 46)
    copy = tmp_path / "drills"
    shutil.copytree(LIBRARY, copy)
    (copy / source.relative_to(LIBRARY)).write_text(json.dumps(doc))
    rc, out = _lint(copy, capsys)
    assert rc == 1, out
    assert doc["id"] in out
    assert reason in out.lower(), out


def test_it_03_14_a_deprecated_drill_must_keep_its_content(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    copy = tmp_path / "drills"
    shutil.copytree(LIBRARY, copy)
    deprecated = [
        p for p in _drills(copy) if "deprecated" in json.dumps(json.loads(p.read_text())).lower()
    ]
    assert deprecated, "no deprecated drill in the library (FR-140: deprecate, never delete)"
    deprecated[0].unlink()
    rc, out = _lint(copy, capsys)
    assert rc == 1, f"deleting a deprecated drill passed the lint: {out}"
