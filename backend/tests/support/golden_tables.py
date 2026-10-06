"""Reads the golden rows straight from the .feature files (one source of truth, ST-023).

Used by the oracle self-test so the oracle is checked against exactly the rows the coach
reviews, never a copy that could drift.
"""

from __future__ import annotations

from pathlib import Path

from tests.support.paths import REPO

FEATURES = REPO / "tests" / "features"


def example_rows(feature: str) -> list[dict[str, str]]:
    """Every Examples row (as a dict) of every table whose first column is ``id``."""
    rows: list[dict[str, str]] = []
    header: list[str] | None = None
    for line in (FEATURES / feature).read_text(encoding="utf-8").splitlines():
        text = line.strip()
        if not text.startswith("|"):
            header = None
            continue
        cells = [c.strip() for c in text.strip("|").split("|")]
        if header is None:
            header = cells if cells and cells[0] == "id" else []
            continue
        if header:
            rows.append(dict(zip(header, cells, strict=True)))
    return rows


def feature_path(feature: str) -> Path:
    return FEATURES / feature
