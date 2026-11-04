"""Locust 2.46.7 ``--csv`` files of an R1 read run (ST-074; NFR-010.1-.9), written per test.

The R1 run (``backend/tests/perf/locustfile_r1.py``) names its reads ``match``,
``score-sheet``, ``dashboard:stats``, ``dashboard:evidence`` and ``plan``. The locustfile
resets Locust's statistics once the warm-up is over, so the stats file holds only the
measured window, and the history file shows the reset as a drop of the Aggregated total.
"""

from __future__ import annotations

import csv
from pathlib import Path

STATS_HEADER = [
    "Type", "Name", "Request Count", "Failure Count", "Median Response Time",
    "Average Response Time", "Min Response Time", "Max Response Time", "Average Content Size",
    "Requests/s", "Failures/s", "50%", "66%", "75%", "80%", "90%", "95%", "98%", "99%",
    "99.9%", "99.99%", "100%",
]  # fmt: skip
HISTORY_HEADER = [
    "Timestamp", "User Count", "Type", "Name", "Requests/s", "Failures/s", "50%", "66%", "75%",
    "80%", "90%", "95%", "98%", "99%", "99.9%", "99.99%", "100%", "Total Request Count",
    "Total Failure Count", "Total Median Response Time", "Total Average Response Time",
    "Total Min Response Time", "Total Max Response Time", "Total Average Content Size",
]  # fmt: skip
NAMES = ("match", "score-sheet", "dashboard:stats", "dashboard:evidence", "plan")
GROUPS = "match,score-sheet,dashboard,plan"
WINDOW_S = 300
T0 = 1_793_000_000


def stats_rows(
    *, requests: int = 3000, p95: dict[str, object] | None = None,
    p99: dict[str, object] | None = None, failures: dict[str, int] | None = None,
    omit: tuple[str, ...] = (),
) -> list[list[object]]:
    """One row per R1 name (``requests`` each, p95 120 ms, p99 400 ms, no failures unless
    overridden) and the Aggregated row, whose Requests/s is the window rate."""
    p95, p99, failures = p95 or {}, p99 or {}, failures or {}
    rows: list[list[object]] = []
    for name in NAMES:
        if name in omit:
            continue
        a, b = p95.get(name, 120), p99.get(name, 400)
        rows.append(["GET", name, requests, failures.get(name, 0), 20, 30, 2, 900, 800,
                     round(requests / WINDOW_S, 2), 0, 20, 30, 40, 50, 90, a, 200, b, 700,
                     800, 900])  # fmt: skip
    total = sum(int(r[2]) for r in rows)
    failed = sum(int(r[3]) for r in rows)
    rows.append(["", "Aggregated", total, failed, 20, 30, 2, 900, 800,
                 round(total / WINDOW_S, 2), 0, 20, 30, 40, 50, 90, 120, 200, 400, 700, 800,
                 900])  # fmt: skip
    return rows


def history_rows(*, seed_s: int = 20, warmup_s: int = 60, window_s: int = WINDOW_S,
                 rps: float = 50.0, reset: bool = True) -> list[list[object]]:
    """One Aggregated sample per second: seeding (no reads), the warm-up at ``rps``, then the
    reset (the total drops to 0) and ``window_s`` measured seconds at ``rps``."""
    rows: list[list[object]] = []
    total = 0.0
    for i in range(seed_s + warmup_s + window_s + 1):
        if i == seed_s + warmup_s and reset:
            total = 0.0
        elif i > seed_s:
            total += rps
        rows.append([T0 + i, 50, "", "Aggregated", rps, 0, *[20] * 11, int(total), 0, 20, 30,
                     2, 900, 800])  # fmt: skip
    return rows


def write_run(tmp: Path, prefix: str = "r1-1", *, history: list | None = None,
              **stats: object) -> Path:
    """Write ``<prefix>_stats.csv`` (and ``<prefix>_stats_history.csv`` unless ``history``
    is ``[]``); return the stats path."""
    path = tmp / f"{prefix}_stats.csv"
    _write(path, STATS_HEADER, stats_rows(**stats))  # type: ignore[arg-type]
    hist = history_rows() if history is None else history
    if hist:
        _write(tmp / f"{prefix}_stats_history.csv", HISTORY_HEADER, hist)
    return path


def _write(path: Path, header: list[str], rows: list[list[object]]) -> None:
    with path.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(header)
        w.writerows(rows)
