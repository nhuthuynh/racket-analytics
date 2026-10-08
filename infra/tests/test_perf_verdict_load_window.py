"""Achieved rate over the loaded window, not the seeding (ST-039 gate; CI run 37739461709).

The locustfile seeds the account and match in ``test_start``, inside Locust's ``-t 60s`` limit
and before any user spawns. Locust's ``Aggregated`` ``Requests/s`` divides by the whole run,
seeding included: run 37739461709 seeded for 13.6 s, then 50 readers delivered ~52 RPS for
45 s, yet Locust reported 39.8 RPS and the gate failed. The verdict therefore reads
``<prefix>_stats_history.csv`` (written next to ``<prefix>_stats.csv`` by ``--csv``) and
measures the rate from the first second with users spawned to the last sample.
"""

from __future__ import annotations

import csv
from pathlib import Path

import pytest
from test_perf_verdict import verdict, write_run

HISTORY_HEADER = [
    "Timestamp", "User Count", "Type", "Name", "Requests/s", "Failures/s", "50%", "66%",
    "75%", "80%", "90%", "95%", "98%", "99%", "99.9%", "99.99%", "100%",
    "Total Request Count", "Total Failure Count", "Total Median Response Time",
    "Total Average Response Time", "Total Min Response Time", "Total Max Response Time",
    "Total Average Content Size",
]  # fmt: skip


def write_history(stats: Path, *, seed_s: int, load_s: int, rate: float, users: int = 51) -> Path:
    """One Aggregated row per second, as Locust writes it: no users while seeding, then load."""
    path = stats.with_name(stats.stem + "_history.csv")
    t0 = 1_791_000_000
    rows = [[t0 + s, 0, "", "Aggregated", 0, 0, *["N/A"] * 11, 0, 0, 0, 0, 0, 0, 0]
            for s in range(seed_s)]  # fmt: skip
    for s in range(load_s + 1):
        total = round(rate * s)
        rows.append([t0 + seed_s + s, users, "", "Aggregated", rate, 0, *[40] * 11,
                     total, 0, 40, 40.0, 5, 600, 100])  # fmt: skip
    with path.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(HISTORY_HEADER)
        w.writerows(rows)
    return path


# ---------------------------------------------------------------- negative cases first
@pytest.mark.unit
def test_a_slow_loaded_window_fails_even_when_seeding_was_short(tmp_path: Path) -> None:
    stats, state = write_run(tmp_path, rps=50.0)  # whole-run figure would pass
    write_history(stats, seed_s=1, load_s=58, rate=40.0)
    rc, body, _ = verdict(stats, state)
    assert rc == 1
    assert body["checks"]["achieved_rps"] is False
    assert body["achieved_rps"] == pytest.approx(40.0, abs=0.5)


@pytest.mark.unit
def test_a_history_where_no_user_ever_spawned_fails_closed(tmp_path: Path) -> None:
    stats, state = write_run(tmp_path, rps=50.0)
    write_history(stats, seed_s=60, load_s=0, rate=50.0, users=0)
    rc, body, _ = verdict(stats, state)
    assert rc == 1
    assert body["checks"]["achieved_rps"] is False


# ---------------------------------------------------------------- positive
@pytest.mark.unit
def test_seeding_time_is_not_counted_against_the_rate(tmp_path: Path) -> None:
    # Run 37739461709: Locust's whole-run figure 39.8, the load itself ~52 RPS for 45 s.
    stats, state = write_run(tmp_path, rps=39.8)
    write_history(stats, seed_s=14, load_s=45, rate=52.0)
    rc, body, out = verdict(stats, state)
    assert rc == 0, out
    assert body["checks"]["achieved_rps"] is True
    assert body["achieved_rps"] == pytest.approx(52.0, abs=0.5)
    assert body["load_window_s"] == 45
