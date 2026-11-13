"""Readers and comparison helpers for the QA-REF-GOLD vectors (test support, not frozen).

Paths are repository-relative. The frozen files are listed in ``golden.lock.json``; the
integrity check (``integrity.py``) refuses a changed file whose lock row names no new ADR.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from tests.support.paths import REPO

HERE = Path(__file__).parent
REL = HERE.relative_to(REPO).as_posix()
LOCK = HERE / "golden.lock.json"
MEASURES = HERE / "vectors" / "measures.gs-pat-1-v1.json"
GAPS = HERE / "vectors" / "gaps.gs-pat-1-v1.golden-reference-v1.json"
REFERENCES = HERE / "references"
FIXTURE = REPO / "docs" / "domain" / "hand-counts" / "GS-PAT-1-v1.json"
SIDES = ("A", "B")
# PatternMeasure fields every vector compares (sprint-06 §3.4 ST-171a; FR-171.R1, R5, R6)
FIELDS = (
    "value",
    "n",
    "interval",
    "interval_method",
    "low_sample",
    "rankable",
    "n_excluded",
    "definition_version",
    "unavailable_reason",
)


def load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        pytest.fail(f"frozen file {path.relative_to(REPO)} is missing", pytrace=False)
    data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return data


def labels(match: str) -> dict[str, Any]:
    doc: dict[str, Any] = load(FIXTURE)["matches"][match]["labels"]
    return doc


def measure_cases(pattern: str) -> list[tuple[str, str]]:
    """(match, side) for every frozen measure of ``pattern``; read at collection time."""
    if not MEASURES.is_file():
        return [("missing-vectors", "-")]
    data = json.loads(MEASURES.read_text(encoding="utf-8"))
    return [
        (match, side)
        for match, sides in data["measures"].items()
        for side in SIDES
        if pattern in sides[side]
    ]


def observed(measure: Any, extra: tuple[str, ...] = ()) -> dict[str, Any]:
    """A product ``PatternMeasure`` as the vector's plain fields (rounding only here)."""
    out: dict[str, Any] = {}
    for name in (*FIELDS, *extra):
        if not hasattr(measure, name):
            out[name] = f"<no attribute {name}>"
            continue
        value = getattr(measure, name)
        if name == "interval" and value is not None:
            value = [value.low, value.high]
        out[name] = value
    return out


def expected_fields(vector: dict[str, Any], extra: tuple[str, ...] = ()) -> dict[str, Any]:
    return {name: vector[name] for name in (*FIELDS, *extra)}


def same(got: Any, want: Any, tol: float) -> bool:
    """Exact for strings, ints, booleans and None; ``tol`` (absolute) for floats."""
    if isinstance(want, list):
        return (
            isinstance(got, list | tuple)
            and len(got) == len(want)
            and all(same(g, w, tol) for g, w in zip(got, want, strict=True))
        )
    if isinstance(want, dict):
        return (
            isinstance(got, dict)
            and got.keys() == want.keys()
            and all(same(got[k], want[k], tol) for k in want)
        )
    if isinstance(want, bool) or want is None or isinstance(want, str):
        return got is want or (got == want and type(got) is type(want))
    if isinstance(got, bool) or not isinstance(got, int | float):
        return False
    return abs(float(got) - float(want)) <= tol


def differences(got: dict[str, Any], want: dict[str, Any], tol: float) -> list[str]:
    return [
        f"{name}: product {got.get(name)!r}, frozen {want[name]!r}"
        for name in want
        if not same(got.get(name), want[name], tol)
    ]
