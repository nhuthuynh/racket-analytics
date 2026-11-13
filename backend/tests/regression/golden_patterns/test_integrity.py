"""QA-REF-GOLD integrity on the repository (integration: filesystem; NFR-078; ADR 0061 Rule 6).

* Every file in ``golden.lock.json`` has the hash of its last change row, each row names an ADR
  that exists and names QA-REF-GOLD, and every file under ``vectors/`` and ``references/`` is
  locked (``integrity.check``).
* The golden reference set lints with ``racket-reference-lint`` (rc 0) with the repository's
  catalogue and sources register, and the gaps vector's reference rows are its entries.
* Two independent counts agree: the QA measure vectors equal the coach's hand count in
  GS-PAT-1 v1 (``counts``) bucket by bucket (ADR 0044 writer/reviewer split), and the gaps
  vector's measure inputs are the measure vectors.

Green from QA-REF-GOLD on; the product goldens (``test_golden_*.py``) stay ``red_until`` their
stories. Written red first: before QA-REF-GOLD no frozen file exists.
"""

from __future__ import annotations

import importlib
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

from tests.regression.golden_patterns import support
from tests.support.references import CATALOGUE, LINT, SOURCES

pytestmark = [pytest.mark.golden_patterns]


def _integrity() -> ModuleType:
    try:
        return importlib.import_module("tests.regression.golden_patterns.integrity")
    except ImportError as exc:
        pytest.fail(f"RED until QA-REF-GOLD: no integrity check ({exc})", pytrace=False)


def test_frozen_files_match_their_lock_and_adr() -> None:
    integrity = _integrity()
    assert integrity.check_repository() == []


def test_golden_reference_set_lints() -> None:
    lint = LINT.load()
    args = [str(support.REFERENCES), "--catalogue", str(CATALOGUE), "--sources", str(SOURCES)]
    assert lint(args) == 0


def _reference_entries() -> dict[str, dict[str, Any]]:
    docs = sorted(Path(support.REFERENCES).glob("*/v*.json"))
    assert [d.relative_to(support.REFERENCES).as_posix() for d in docs] == [
        "golden-reference/v1.json"
    ]
    return {e["id"]: e for e in support.load(docs[0])["entries"]}


def test_gap_reference_rows_are_the_golden_reference_entries() -> None:
    entries = _reference_entries()
    for case in support.load(support.GAPS)["cases"]:
        for row in case["rows"]:
            ref = row["reference"]
            if ref is None:
                continue
            entry = entries[ref["id"]]
            assert (entry["pattern_id"], entry["level_band"], entry["format"]) == (
                row["pattern_id"],
                case["level_band"],
                case["format"],
            ), ref["id"]
            assert ref["band"] == entry["band"], ref["id"]
            assert ref["version"] == entry["version"], ref["id"]
            assert row["better_direction"] == entry["better_direction"], ref["id"]


def test_no_reference_rows_have_no_entry() -> None:
    entries = _reference_entries()
    keys = {(e["pattern_id"], e["level_band"], e["format"]) for e in entries.values()}
    for case in support.load(support.GAPS)["cases"]:
        for row in case["rows"]:
            if row["reference"] is None:
                key = (row["pattern_id"], case["level_band"], case["format"])
                assert key not in keys, (case["id"], key)


def _counted(pattern: str, bucket: dict[str, Any]) -> dict[str, Any]:
    """The hand count bucket of one side as the vector's count fields."""
    excluded = {reason: len(ids) for reason, ids in bucket["excluded"].items()}
    if pattern == "AN-09":
        mix = {t: len(ids) for t, ids in bucket["mix"].items()}
        return {"k": mix.get("drop", 0), "n": sum(mix.values()), "mix": mix, "excluded": excluded}
    if pattern == "AN-13":
        samples = sorted(bucket["samples"].values())
        return {
            "samples": samples,
            "n": len(samples),
            "n_censored": len(bucket["censored"]),
            "excluded": excluded,
        }
    k = len(bucket["deep"])
    return {"k": k, "n": k + len(bucket["not_deep"]), "excluded": excluded}


def test_measure_vectors_equal_the_coach_hand_count() -> None:
    vectors = support.load(support.MEASURES)
    fixture = support.load(support.FIXTURE)
    assert vectors["gold_set"] == fixture["gold_set"] == "GS-PAT-1"
    assert vectors["gold_set_version"] == fixture["gold_set_version"] == 1
    assert vectors["catalogue_version"] == fixture["catalogue_version"]
    assert sorted(vectors["measures"]) == sorted(fixture["matches"])
    diffs = []
    for match, sides in vectors["measures"].items():
        counts = fixture["matches"][match]["counts"]
        assert sides["format"] == fixture["matches"][match]["format"]
        assert sides["unassigned"] == {r: len(ids) for r, ids in counts["unassigned"].items()}
        for side in support.SIDES:
            for pattern, vector in sides[side].items():
                hand = _counted(pattern, counts[pattern][side])
                mine = {key: vector[key] for key in hand}
                if mine != hand:
                    diffs.append(f"{match} {side} {pattern}: QA {mine}, coach {hand}")
                assert vector["n_excluded"] == sum(hand["excluded"].values())
    assert diffs == []


def test_gap_measure_inputs_are_the_measure_vectors() -> None:
    measures = support.load(support.MEASURES)["measures"]
    for case in support.load(support.GAPS)["cases"]:
        frozen = measures[case["match"]][case["side"]]
        assert measures[case["match"]]["format"] == case["format"], case["id"]
        assert sorted(r["pattern_id"] for r in case["rows"]) == sorted(frozen), case["id"]
        for row in case["rows"]:
            vector = frozen[row["pattern_id"]]
            assert row["measure"] == support.expected_fields(vector), (case["id"], row)
