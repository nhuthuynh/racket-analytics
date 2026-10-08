"""ST-049 unit (FR-151, QD-GD-03, NFR-004): the shape of the frozen set GS-AN-1 v1.

The files under ``tests/regression/golden_matches/`` are data; these checks keep them usable
as a gold set: the manifest lists exactly the set's files, every expected file covers every
metric and side with the fields the reference compares, the scripts carry no video and no
people, and every game but the last of a script is finished before the next starts.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from tests.support.scorebook import _load

statslib = _load("statslib")

SET_DIR = Path(__file__).resolve().parents[2] / "regression" / "golden_matches"
MATCHES = ("gm1-two-games", "gm2-three-games", "gm3-corrections-needs-decision")


def _json(path: Path) -> Any:
    return json.loads(path.read_text())


def _set_files() -> set[str]:
    return {
        p.relative_to(SET_DIR).as_posix()
        for p in SET_DIR.rglob("*")
        if p.is_file() and p.name != "manifest.json"
    }


def test_the_manifest_lists_exactly_the_files_of_the_set() -> None:
    manifest = _json(SET_DIR / "manifest.json")
    listed = {f["path"] for f in manifest["files"]}
    assert listed == _set_files()
    assert all(len(f["sha256"]) == 64 and f["bytes"] > 0 for f in manifest["files"])


def test_the_manifest_records_rules_dictionary_and_labellers() -> None:
    manifest = _json(SET_DIR / "manifest.json")
    assert (manifest["id"], manifest["version"]) == ("GS-AN-1", 1)
    assert manifest["rules_version"] == "PROVISIONAL-UNVERIFIED"
    assert manifest["metric_dict_version"] == "0.1"
    assert manifest["consent_status"] == "synthetic"
    roles = {labeller["role"] for labeller in manifest["labellers"]}
    assert {"senior-qa-engineer", "pickleball-domain-coach"} <= roles


def test_every_expected_file_covers_every_metric_side_and_compared_field() -> None:
    for match in MATCHES:
        metrics = _json(SET_DIR / "expected" / f"{match}.json")["metrics"]
        assert sorted(metrics) == sorted(statslib.METRICS), match
        for metric in statslib.METRICS:
            for side in ("A", "B"):
                fields = metrics[metric][side]
                missing = [k for k in statslib.COMPARED[metric] if k not in fields]
                assert not missing, f"{match} {metric} {side}: missing {missing}"
                assert "rallies" in fields, f"{match} {metric} {side}: no evidence rallies"


def test_the_scripts_carry_no_video_and_no_people() -> None:
    for match in MATCHES:
        s = _json(SET_DIR / f"{match}.script.json")
        assert s["match"] == match
        assert s["gold_set"] == "GS-AN-1"
        assert s["rules_version"] == "PROVISIONAL-UNVERIFIED"
        assert not {"video", "clip", "people", "shows_people"} & set(s), match


def test_every_game_but_the_last_is_finished_before_the_next_starts() -> None:
    counts = {}
    for match in MATCHES:
        s = _json(SET_DIR / f"{match}.script.json")
        counts[match] = [len(g["tags"]) for g in s["games"]]
        for number, game in enumerate(s["games"][:-1], start=1):
            recs = statslib.annotate(game["tags"], first_serving_side=game["first_serving_side"])
            assert all(r["serving_side"] is not None for r in recs), f"{match} game {number}"
            last = recs[-1]["score_after"]
            assert max(last.values()) >= 11, f"{match} game {number} unfinished: {last}"
            assert abs(last["A"] - last["B"]) >= 2, f"{match} game {number} unfinished: {last}"
    assert sum(counts["gm1-two-games"]) == 59
    assert sum(counts["gm2-three-games"]) == 59
    assert counts["gm3-corrections-needs-decision"] == [23]
