"""Pure helpers for the goal-scorecard measurement scripts (docs/sprints/01/goal-scorecard.md).

Standard library only, so every script runs with any Python 3.11 on the host. The network
code lives in the scripts; this module only turns observations into numbers, and it fails
closed: no samples or no selected tests never reads as a pass (ADR 0014).
Tests: infra/tests/test_measure_scripts.py.
"""

from __future__ import annotations

import base64
import hashlib
import math
import re
import xml.etree.ElementTree as ET
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any

SIGN_IN_TOKEN = re.compile(r"/auth/callback#token=(?P<token>[A-Za-z0-9_-]{43})")
SESSION_COOKIES = ("__Host-racket_session", "racket_session")


def percentile(samples: Sequence[float], p: float) -> float:
    """Nearest-rank percentile (no interpolation), p in (0, 100]."""
    if not samples:
        raise ValueError("no samples")
    if not 0 < p <= 100:
        raise ValueError("p must be in (0, 100]")
    ordered = sorted(samples)
    rank = max(1, math.ceil(p / 100 * len(ordered)))
    return ordered[rank - 1]


def latency_summary(
    latencies_ms: Sequence[float], statuses: Sequence[int], wall_s: float
) -> dict[str, Any]:
    """Latency percentiles of the successful (< 500, not 429) requests, plus NFR-041
    availability = non-5xx / all responses excluding 429."""
    n_5xx = sum(1 for s in statuses if s >= 500 or s == 0)  # 0 = no response at all
    n_429 = sum(1 for s in statuses if s == 429)
    counted = len(statuses) - n_429
    has = bool(latencies_ms)
    return {
        "requests": len(statuses),
        "status_5xx": n_5xx,
        "status_429": n_429,
        "status_unexpected": sum(1 for s in statuses if 300 <= s < 500 and s != 429),
        "availability": (counted - n_5xx) / counted if counted else 0.0,
        "achieved_rps": len(statuses) / wall_s if wall_s > 0 else 0.0,
        "p50_ms": percentile(latencies_ms, 50) if has else None,
        "p95_ms": percentile(latencies_ms, 95) if has else None,
        "p99_ms": percentile(latencies_ms, 99) if has else None,
        "max_ms": max(latencies_ms) if has else None,
    }


def throughput_mbps(n_bytes: int, seconds: float) -> float:
    if seconds <= 0:
        raise ValueError("elapsed time must be positive")
    return n_bytes * 8 / seconds / 1_000_000


def chunk_plan(length: int, size: int, start: int = 0) -> list[tuple[int, int]]:
    """(offset, n) for every chunk from ``start`` to ``length``."""
    if length < 0 or size <= 0 or not 0 <= start <= max(length, 0):
        raise ValueError("bad length, chunk size or start")
    return [(off, min(size, length - off)) for off in range(start, length, size)]


def effective_chunk(length: int, max_chunk: int, min_chunks: int = 5) -> int:
    """The chunk size, cut down so a small file still has ``min_chunks`` chunks and the
    simulated drop at 40 % happens mid-upload."""
    if length <= 0 or max_chunk <= 0 or min_chunks <= 0:
        raise ValueError("bad length, chunk size or chunk count")
    return max(1, min(max_chunk, math.ceil(length / min_chunks)))


def tus_metadata(**pairs: str) -> str:
    return ",".join(f"{k} {base64.b64encode(v.encode()).decode()}" for k, v in pairs.items())


def checksum_header(data: bytes) -> str:
    return "sha256 " + base64.b64encode(hashlib.sha256(data).digest()).decode()


def token_from(body: str) -> str | None:
    found = SIGN_IN_TOKEN.search(body)
    return found.group("token") if found else None


def session_cookie(set_cookie_headers: Iterable[str]) -> str | None:
    """``name=value`` of the session cookie among Set-Cookie headers, else None."""
    for header in set_cookie_headers:
        pair = header.split(";", 1)[0].strip()
        name, _, value = pair.partition("=")
        if name in SESSION_COOKIES and value:
            return pair
    return None


def _outcome(case: ET.Element) -> str:
    if case.find("failure") is not None or case.find("error") is not None:
        return "failed"
    if case.find("skipped") is not None:
        return "skipped"
    return "passed"


def junit_rate(
    paths: Sequence[Path],
    include: str,
    require: Sequence[str] = (),
    allow_skips: bool = False,
) -> dict[str, Any]:
    """Pass rate of the test cases whose ``classname::name`` (or ``file``) matches ``include``.

    Skips count as not passed unless ``allow_skips``; then they leave the denominator.
    Every pattern in ``require`` must match at least one selected case.
    """
    pattern = re.compile(include)
    selected: list[tuple[str, str]] = []
    for path in paths:
        for case in ET.parse(path).getroot().iter("testcase"):  # noqa: S314 (local reports)
            test_id = f"{case.get('file', '')}|{case.get('classname', '')}::{case.get('name', '')}"
            if pattern.search(test_id):
                selected.append((test_id, _outcome(case)))
    counts = {k: sum(1 for _, o in selected if o == k) for k in ("passed", "failed", "skipped")}
    denominator = len(selected) - (counts["skipped"] if allow_skips else 0)
    rate = counts["passed"] / denominator if denominator > 0 else None
    missing = [r for r in require if not any(re.search(r, t) for t, _ in selected)]
    return {
        "include": include,
        "selected": len(selected),
        **counts,
        "rate": rate,
        "missing": missing,
        "failures": [t for t, o in selected if o == "failed"],
        "ok": rate == 1.0 and not missing and counts["failed"] == 0,
    }


_FINDING_ID = re.compile(r"\b[A-Z]{2,4}-[RV]\d+(?:-S\d+)?-\d+\b")
_OPEN_SEVERITY = re.compile(r"\b(blocker|blocking|major)\b")
_OPEN_DISPOSITION = re.compile(r"^(open|not re-verified|not fixed|partly)")


def _cells(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def _disposition_column(header: list[str]) -> int | None:
    lowered = [h.lower() for h in header]
    for key in ("disposition", "fix", "state", "status"):
        for i, h in enumerate(lowered):
            if key in h:
                return i
    return None


def open_defects(text: str) -> list[dict[str, Any]]:
    """Blocker or major findings whose latest row is still open (goal scorecard G01-11).

    Reads every Markdown table that has a finding-id column, a ``Severity`` column and a
    disposition column (``Disposition`` first, else ``Fix…``, ``State…`` or ``Status``).
    The last row naming a finding id wins. A row is open when its disposition starts with
    "Open", "Not re-verified", "Not fixed" or "Partly" (fail closed, ADR 0014, ADR 0030).
    A text without any such table is refused, so a wrong file never reads as 0.
    """
    rows: list[dict[str, Any]] = []
    latest: dict[str, int] = {}
    header: list[str] | None = None
    tables = 0
    for number, line in enumerate(text.splitlines(), start=1):
        if not line.lstrip().startswith("|"):
            header = None
            continue
        cells = _cells(line)
        if header is None:
            header = cells
            lowered = [h.lower() for h in header]
            sev_col = next((i for i, h in enumerate(lowered) if "severity" in h), None)
            disp_col = _disposition_column(header)
            if sev_col is not None and disp_col is not None and disp_col != sev_col:
                tables += 1
            else:
                sev_col = disp_col = None
            continue
        if sev_col is None or disp_col is None or set("".join(cells)) <= set("-: "):
            continue
        ids = _FINDING_ID.findall(cells[0])
        if not ids or len(cells) <= max(sev_col, disp_col):
            continue
        severity = cells[sev_col].replace("*", "").strip().lower()
        disposition = cells[disp_col].replace("*", "").strip()
        rows.append({"ids": ids, "severity": severity, "disposition": disposition, "line": number})
        for finding in ids:
            latest[finding] = len(rows) - 1
    if tables == 0:
        raise ValueError("no review table with Severity and Disposition columns")
    open_rows = []
    for index in sorted(set(latest.values())):
        row = rows[index]
        if _OPEN_SEVERITY.search(row["severity"]) and _OPEN_DISPOSITION.match(
            row["disposition"].lower()
        ):
            open_rows.append(row)
    return open_rows
