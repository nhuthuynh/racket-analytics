"""IT-02-08 (ST-032; NFR-013): a server-confirmed correction on a decided 3-game match within
1.5 s p95 over 50 runs, and the sheet restored byte for byte after the matching undos.

API <-> DB, real Postgres; the client is in-process (no network), so this is the server's
share of NFR-013. The live, over-https number is G02-02 (a) (``live_tagging.py``).
Fixture: ``taglib.three_game_script(seed=2)`` (every rally "winner", so any winner change is
a valid command, I6). Each run changes the winner of a rally in game 1 (the worst case: every
later rally of the match is re-scored), then undoes it.
"""

from __future__ import annotations

import time

import pytest

from tests.support import scorebook as sb
from tests.support.api import ApiDriver

pytestmark = pytest.mark.slow

RUNS = 50
P95_MS = 1_500


def _p95(samples: list[float]) -> float:
    ordered = sorted(samples)
    return ordered[max(0, round(0.95 * len(ordered) + 0.5) - 1)]


def test_it_02_08_correction_is_confirmed_within_1_5_s_p95(api: ApiDriver) -> None:
    ivy = api.as_user("ivy")
    match_id = api.run(sb.create_doubles(ivy, "IT-02-08"))
    api.run(sb.receive_video(ivy, match_id))
    clock = 0
    for game in sb.taglib.three_game_script(seed=2):
        api.run(sb.start_game(ivy, match_id, game["first_serving_side"]))
        tags = sb.taglib.with_times(game["tags"], duration_ms=len(game["tags"]) * 2_000)
        tags = [
            {**t, "start_ms": t["start_ms"] + clock, "end_ms": t["end_ms"] + clock} for t in tags
        ]
        clock = tags[-1]["end_ms"] + 1_000
        api.run(sb.tag_all(ivy, match_id, tags))
    baseline = api.run(sb.sheet(ivy, match_id)).json()
    assert baseline["match_winner"] in ("A", "B"), "the fixture match must be decided"
    rows = baseline["rows"]
    assert len(rows) >= 60
    assert {r["game"] for r in rows} >= {1, 2}

    samples: list[float] = []
    version = api.run(sb.version_of(ivy, match_id))
    for run in range(RUNS):
        row = rows[run % 10]  # game 1: every later rally is re-scored
        other = "A" if row["winning_side"] == "B" else "B"
        started = time.perf_counter()
        change = {"field": "winning_side", "value": other}
        response = api.run(
            sb.command(ivy, "correct", version=version, body=change,
                       match_id=match_id, rally_id=row["rally_id"])
        )  # fmt: skip
        samples.append((time.perf_counter() - started) * 1000)
        assert response.status_code == 200, response.text
        undo = api.run(
            sb.command(ivy, "undo", version=response.json()["version"], match_id=match_id)
        )
        assert undo.status_code == 200, undo.text
        version = undo.json()["version"]

    assert len(samples) == RUNS
    assert _p95(samples) <= P95_MS, f"p95 {_p95(samples):.0f} ms over {RUNS} corrections"
    restored = api.run(sb.sheet(ivy, match_id)).json()
    assert sb.canonical(restored) == sb.canonical(baseline)
    print(
        f"IT-02-08 p95_ms={_p95(samples):.1f} max_ms={max(samples):.1f} n={RUNS} rows={len(rows)}"
    )
