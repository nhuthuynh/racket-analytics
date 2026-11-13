"""Integrity of the QA-REF-GOLD frozen files: no edit without an ADR (ADR 0061 Rule 6; NFR-078).

``golden.lock.json`` is a list of change rows. Each row names the ADR that authorises it and the
sha256 of every file it freezes (repository-relative paths). A file's current hash must equal
the one in the last row that names it. A row is valid only when its ADR is a
``docs/decisions/NNNN-*.md`` file that exists, names QA-REF-GOLD and authorised no earlier row,
and the rows are in date order. So an edited vector, reference or input fixture fails until a
new ADR is written and a new row locks the new hash; the lock itself sits under
``backend/tests/`` and so needs ``qa-approved-test-change`` too (``check_test_immutability.py``).
Standard library only.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Callable, Iterable, Mapping
from typing import Any

from tests.support.paths import REPO

SCHEMA = "golden-patterns-lock/v1"
TICKET = "QA-REF-GOLD"
FIELDS = ("date", "ticket", "by", "adr", "reason", "files")
_ADR = re.compile(r"^docs/decisions/\d{4}-[a-z0-9-]+\.md$")
GOLDEN = "backend/tests/regression/golden_patterns"
LOCK = f"{GOLDEN}/golden.lock.json"
FROZEN_DIRS = (f"{GOLDEN}/vectors", f"{GOLDEN}/references")

Reader = Callable[[str], bytes | None]
AdrText = Callable[[str], str | None]


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _row_problems(
    i: int, row: Mapping[str, Any], seen: dict[str, int], adr_text: AdrText
) -> list[str]:
    problems = [f"change {i}: missing {f}" for f in FIELDS if f not in row]
    adr = row.get("adr")
    if "adr" in row:
        if not isinstance(adr, str) or not _ADR.match(adr):
            problems.append(f"change {i}: ADR {adr!r} is not a docs/decisions/NNNN-*.md path")
        elif adr in seen:
            problems.append(f"change {i}: ADR {adr} already authorised change {seen[adr]}")
        else:
            text = adr_text(adr)
            if text is None:
                problems.append(f"change {i}: ADR {adr} does not exist")
            elif TICKET not in text:
                problems.append(f"change {i}: ADR {adr} does not name {TICKET}")
            seen[adr] = i
    files = row.get("files")
    if "files" in row and (not isinstance(files, dict) or not files):
        problems.append(f"change {i}: files must name at least one file")
    return problems


def check(
    lock: Mapping[str, Any], read: Reader, adr_text: AdrText, present: Iterable[str] = ()
) -> list[str]:
    """Problems with ``lock`` against the files ``read`` returns; [] when intact."""
    if lock.get("schema") != SCHEMA:
        return [f"lock: schema must be {SCHEMA}, got {lock.get('schema')!r}"]
    rows = lock.get("changes")
    if not isinstance(rows, list) or not rows:
        return ["lock: no change row"]
    problems: list[str] = []
    seen: dict[str, int] = {}
    hashes: dict[str, str] = {}
    last_date = ""
    for i, row in enumerate(rows, start=1):
        problems += _row_problems(i, row, seen, adr_text)
        date = str(row.get("date", ""))
        if date < last_date:
            problems.append(f"change {i}: date before change {i - 1}")
        last_date = max(last_date, date)
        if isinstance(row.get("files"), dict):
            hashes.update(row["files"])
    for path, want in sorted(hashes.items()):
        data = read(path)
        if data is None:
            problems.append(f"{path}: missing")
        elif sha256(data) != want:
            problems.append(f"{path}: edited without an ADR (sha256 {sha256(data)}, lock {want})")
    problems += [f"{path}: not in the lock" for path in sorted(set(present) - set(hashes))]
    return problems


def read_repo(path: str) -> bytes | None:
    target = REPO / path
    return target.read_bytes() if target.is_file() else None


def adr_text(path: str) -> str | None:
    data = read_repo(path)
    return None if data is None else data.decode("utf-8")


def present_files() -> list[str]:
    """Every file under the frozen directories (each must be locked)."""
    return sorted(
        p.relative_to(REPO).as_posix()
        for d in FROZEN_DIRS
        for p in (REPO / d).rglob("*")
        if p.is_file()
    )


def check_repository() -> list[str]:
    data = read_repo(LOCK)
    if data is None:
        return [f"{LOCK}: missing"]
    return check(json.loads(data), read_repo, adr_text, present_files())
