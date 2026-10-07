"""The shipped metric statuses follow the coach's record (PD-R2S3-01, PE-R2S3-05; FR-102).

Only the pickleball-domain-coach moves an entry's status, in ``docs/domain/metric-dictionary.md``
(one ``| status / source |`` row per ``### AN-0x`` section; ADR 0044). ``metrics.json`` mirrors
it. These tests read the status rows from the document, so a status the coach moves and the
code does not (or the reverse) fails here instead of on a live stack, where D-01 would show no
metric. Status is outside the definition digest (analytics-snapshots §5.1): no version bump.
Negative cases first.
"""

from __future__ import annotations

import re

import pytest

from racket.sports.pickleball.metrics import load_dictionary
from tests.support.paths import REPO

pytestmark = pytest.mark.unit

DICTIONARY_DOC = REPO / "docs" / "domain" / "metric-dictionary.md"
_SECTION = re.compile(r"^### (AN-\d{2})\b", re.MULTILINE)
_STATUS_ROW = re.compile(r"^\| status / source \| `([a-z-]+)`", re.MULTILINE)


def doc_statuses(text: str) -> dict[str, str]:
    """Status per entry from the document's ``### AN-0x`` sections; every section needs one row."""
    found: dict[str, str] = {}
    heads = list(_SECTION.finditer(text))
    for i, head in enumerate(heads):
        end = heads[i + 1].start() if i + 1 < len(heads) else len(text)
        body = text[head.end() : end]
        body = body.split("\n## ", 1)[0]  # a section ends at the next top-level heading
        rows = _STATUS_ROW.findall(body)
        if len(rows) != 1:
            raise ValueError(f"{head.group(1)}: expected one status row, found {len(rows)}")
        found[head.group(1)] = rows[0]
    return found


def mismatches(shipped: dict[str, str], recorded: dict[str, str]) -> list[str]:
    return sorted(
        f"{key}: shipped {shipped.get(key)!r}, recorded {recorded.get(key)!r}"
        for key in set(shipped) | set(recorded)
        if shipped.get(key) != recorded.get(key)
    )


# ---------------------------------------------------------------- negative cases first
def test_a_section_without_a_status_row_is_refused() -> None:
    with pytest.raises(ValueError, match="AN-09: expected one status row, found 0"):
        doc_statuses("### AN-09 Something\n\n| unit | % |\n")


def test_a_status_the_code_did_not_mirror_is_reported() -> None:
    text = "### AN-01 X\n| status / source | `coach-reviewed` 2026-10-07 / QD |\n"
    assert mismatches({"AN-01": "draft"}, doc_statuses(text)) == [
        "AN-01: shipped 'draft', recorded 'coach-reviewed'"
    ]


def test_an_entry_missing_on_either_side_is_reported() -> None:
    assert mismatches({"AN-01": "draft"}, {}) == ["AN-01: shipped 'draft', recorded None"]


# ---------------------------------------------------------------- the shipped file
def test_the_shipped_statuses_equal_the_coachs_status_rows() -> None:
    recorded = doc_statuses(DICTIONARY_DOC.read_text(encoding="utf-8"))
    shipped = {e.id: e.status for e in load_dictionary().entries}
    assert mismatches(shipped, recorded) == []


def test_the_shipped_published_set_is_an_01_to_an_07() -> None:
    """COACH-1 (2026-10-07, ADR 0044) moved all seven to coach-reviewed: the API shows all seven."""
    load_dictionary.cache_clear()
    assert [e.id for e in load_dictionary().published()] == [f"AN-0{i}" for i in range(1, 8)]
