"""The coach's status rows in ``docs/domain/metric-dictionary.md`` (GS-AN-1-V2; ADR 0044).

Test support shared by the unit, scenario and integration checks that the shipped
``metrics.json`` mirrors the coach's record (PD-R2S3-01, PE-R2S3-05). The document has one
``| status / source |`` row per ``### AN-0x`` section; only the pickleball-domain-coach moves it.
"""

from __future__ import annotations

import re

from tests.support.paths import REPO

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


def recorded_statuses() -> dict[str, str]:
    """The coach's record as committed."""
    return doc_statuses(DICTIONARY_DOC.read_text(encoding="utf-8"))


def mismatches(shipped: dict[str, str], recorded: dict[str, str]) -> list[str]:
    """Every entry whose shipped status differs from the record, either way round."""
    return sorted(
        f"{key}: shipped {shipped.get(key)!r}, recorded {recorded.get(key)!r}"
        for key in set(shipped) | set(recorded)
        if shipped.get(key) != recorded.get(key)
    )
