"""Sprint 2 goal-scorecard harness (docs/sprints/02/goal-scorecard.md, PO standing rule).

`scripts/measure/taglib.py` turns live Quick Tag / score-sheet observations into the numbers
the scorecard compares with its targets, and `scripts/measure/pw_timings.py` turns Playwright
timing attachments into percentiles. Negative cases first: an empty, unmatched or malformed
input must never read as a pass (fail closed, ADR 0014).

The reference stepper in taglib is a third, independent side-out implementation used only to
derive the expected score calls of the live journey. It is checked here against the QD §2.2
rows already in sprint-01 §7.8 (SOD-01..SOD-16, PROVISIONAL-UNVERIFIED, ADR 0009); it is not
the product engine and not the QA oracle.
"""

from __future__ import annotations

import base64
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest
from conftest import SCRIPTS_DIR

pytestmark = pytest.mark.unit

MEASURE = SCRIPTS_DIR / "measure"


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, MEASURE / f"{name}.py")
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


t = _load("taglib")


def _state(call: str, serving: str = "A") -> object:
    s, r, n = (int(x) for x in call.split("-"))
    other = "B" if serving == "A" else "A"
    return t.DoublesState(score={serving: s, other: r}, serving_side=serving, server_number=n)


# ================================================================ reference stepper: refusals first
def test_unknown_winner_is_refused() -> None:
    with pytest.raises(ValueError, match="winner"):
        t.step_doubles(t.new_doubles_game("A"), "C")


def test_unknown_first_server_side_is_refused() -> None:
    with pytest.raises(ValueError, match="side"):
        t.new_doubles_game("X")


def test_rally_after_game_over_is_refused_sod_12() -> None:
    over = t.step_doubles(_state("10-8-1"), "A")
    assert over.winner == "A"
    with pytest.raises(t.GameOver):
        t.step_doubles(over, "B")


# ================================================================ reference stepper: QD §2.2 rows
@pytest.mark.parametrize(
    ("row", "before", "winner_role", "after", "next_side"),
    [
        ("SOD-01", "0-0-2", "serving", "1-0-2", "A"),
        ("SOD-02", "0-0-2", "receiving", "0-0-1", "B"),
        ("SOD-03", "3-5-1", "receiving", "3-5-2", "A"),
        ("SOD-04", "3-5-2", "receiving", "5-3-1", "B"),
        ("SOD-05", "7-4-1", "serving", "8-4-1", "A"),
        ("SOD-08", "10-10-1", "serving", "11-10-1", "A"),
        ("SOD-10", "10-9-2", "receiving", "9-10-1", "B"),
        ("SOD-16", "5-5-1", "replay", "5-5-1", "A"),
    ],
)
def test_stepper_matches_the_provisional_doubles_rows(
    row: str, before: str, winner_role: str, after: str, next_side: str
) -> None:
    winner = {"serving": "A", "receiving": "B", "replay": "replay"}[winner_role]
    out = t.step_doubles(_state(before), winner)
    assert t.call_doubles(out) == after, row
    assert out.serving_side == next_side, row


@pytest.mark.parametrize(
    ("row", "before", "final"),
    [("SOD-07", "10-8-1", "11-8"), ("SOD-09", "11-10-2", "12-10"), ("SOD-11", "21-20-1", "22-20")],
)
def test_game_ends_at_target_by_margin(row: str, before: str, final: str) -> None:
    target = 21 if row == "SOD-11" else 11
    out = t.step_doubles(_state(before), "A", target=target)
    assert out.winner == "A", row
    assert f"{out.score['A']}-{out.score['B']}" == final


def test_no_game_end_without_the_margin() -> None:
    out = t.step_doubles(_state("10-10-1"), "A")
    assert out.winner is None


# ================================================================ expected score-sheet rows
def test_expected_rows_of_no_tags_is_an_empty_sheet() -> None:
    assert t.expected_rows([], first_serving_side="A") == []


def test_expected_rows_of_the_journey_script() -> None:
    rows = t.expected_rows(t.JOURNEY_TAGS, first_serving_side="A")
    assert [r["number"] for r in rows] == [1, 2, 3, 4, 5, 6]
    assert [r["score_before"] for r in rows] == [
        "0-0-2",
        "1-0-2",
        "0-1-1",
        "0-1-2",
        "1-0-1",
        "1-0-1",
    ]
    assert [r["score_after"] for r in rows] == [
        "1-0-2",
        "0-1-1",
        "0-1-2",
        "1-0-1",
        "1-0-1",
        "2-0-1",
    ]
    assert [r["serving_side"] for r in rows] == ["A", "A", "B", "B", "A", "A"]
    assert all(r["marker"] is None for r in rows)


def test_correcting_rally_2_rescores_every_later_rally_c01() -> None:
    corrected = t.with_winner(t.JOURNEY_TAGS, rally=2, side="A")
    rows = t.expected_rows(corrected, first_serving_side="A")
    assert [r["score_after"] for r in rows] == [
        "1-0-2",
        "2-0-2",
        "3-0-2",
        "4-0-2",
        "4-0-2",
        "5-0-2",
    ]
    # the original script is unchanged (no aliasing)
    assert t.JOURNEY_TAGS[1]["winning_side"] == "B"


def test_with_winner_refuses_a_rally_that_does_not_exist() -> None:
    with pytest.raises(ValueError, match="rally"):
        t.with_winner(t.JOURNEY_TAGS, rally=7, side="A")


def test_rallies_after_game_end_are_kept_and_marked_c02() -> None:
    base = t.expected_rows(t.CONFLICT_TAGS, first_serving_side="A")
    assert len(base) == 14
    assert base[-1]["score_after"] == "11-0-1"
    assert all(r["marker"] is None for r in base)
    flipped = t.with_winner(t.CONFLICT_TAGS, rally=t.CONFLICT_FLIP, side="A")
    rows = t.expected_rows(flipped, first_serving_side="A")
    assert len(rows) == 14  # never deleted
    assert rows[t.CONFLICT_FLIP - 1]["score_after"] == "11-0-2"
    assert [r["number"] for r in rows if r["marker"] == "needs_decision"] == [12, 13, 14]


def test_journey_tags_respect_the_responsible_player_side_rule() -> None:
    assert t.outcome_problems(t.JOURNEY_TAGS) == []


def test_error_attributed_to_the_winning_side_is_a_problem() -> None:
    bad = [dict(t.JOURNEY_TAGS[0], ending="unforced_error", responsible_player="A1")]
    assert t.outcome_problems(bad) == ["rally 1: responsible player A1 is not on the losing side"]


# ================================================================ three-game script
def test_three_game_script_is_deterministic_and_decides_the_match() -> None:
    a = t.three_game_script(seed=20261005)
    b = t.three_game_script(seed=20261005)
    assert a == b
    assert len(a) in (2, 3)
    winners = []
    for game in a:
        rows = t.expected_rows(game["tags"], first_serving_side=game["first_serving_side"])
        assert rows
        assert all(r["marker"] is None for r in rows)
        winners.append(t.game_winner(game["tags"], game["first_serving_side"]))
    assert max(winners.count("A"), winners.count("B")) == 2
    assert t.outcome_problems([tag for g in a for tag in g["tags"]]) == []


# ================================================================ sheet comparison
def test_comparing_two_empty_sheets_fails_closed() -> None:
    assert t.compare_rows([], []) == ["no rows to compare"]


def test_row_count_difference_is_reported() -> None:
    rows = t.expected_rows(t.JOURNEY_TAGS, first_serving_side="A")
    assert "row count: expected 6, got 5" in t.compare_rows(rows, rows[:5])


def test_field_differences_are_reported_per_rally() -> None:
    rows = t.expected_rows(t.JOURNEY_TAGS, first_serving_side="A")
    other = [dict(r) for r in rows]
    other[2]["score_after"] = "9-9-9"
    assert t.compare_rows(rows, other) == ["rally 3 score_after: expected '0-1-2', got '9-9-9'"]


def test_identical_rows_compare_clean() -> None:
    rows = t.expected_rows(t.JOURNEY_TAGS, first_serving_side="A")
    assert t.compare_rows(rows, [dict(r) for r in rows]) == []


def test_normalise_sheet_refuses_a_body_without_rows() -> None:
    with pytest.raises(ValueError, match="rows"):
        t.normalise_sheet({"unofficial": True})


def test_normalise_sheet_reads_the_contract_fields_in_rally_order() -> None:
    body = {
        "rows": [
            {
                "number": 2,
                "serving_side": "A",
                "score_before": "1-0-2",
                "score_after": "0-1-1",
                "winning_side": "B",
                "ending": "unforced_error",
                "marker": None,
                "extra": 1,
            },
            {
                "number": 1,
                "serving_side": "A",
                "score_before": "0-0-2",
                "score_after": "1-0-2",
                "winning_side": "A",
                "ending": "winner",
                "marker": None,
            },
        ]
    }
    rows = t.normalise_sheet(body)
    assert [r["number"] for r in rows] == [1, 2]
    assert "extra" not in rows[1]


# ================================================================ canonical bytes
def test_canonical_bytes_refuses_floats() -> None:
    with pytest.raises(ValueError, match="float"):
        t.canonical_bytes({"a": 1.5})


def test_canonical_bytes_ignores_key_order() -> None:
    assert t.canonical_bytes({"b": 1, "a": [1, {"d": 2, "c": 3}]}) == t.canonical_bytes(
        {"a": [1, {"c": 3, "d": 2}], "b": 1}
    )


# ================================================================ media URL policy (NFR-055)
def test_media_url_with_ttl_over_15_minutes_is_a_problem() -> None:
    assert "ttl 901 s > 900 s" in t.media_url_problems("https://s/x?sig=1", 901, "abc")


def test_media_url_with_no_or_negative_ttl_is_a_problem() -> None:
    assert "ttl missing or not positive" in t.media_url_problems("https://s/x?sig=1", None, "abc")
    assert "ttl missing or not positive" in t.media_url_problems("https://s/x?sig=1", 0, "abc")


def test_media_url_carrying_the_session_is_a_problem() -> None:
    probs = t.media_url_problems("https://s/x?token=SECRETCOOKIE", 300, "SECRETCOOKIE")
    assert "session token in URL" in probs


def test_media_url_with_an_empty_session_value_fails_closed() -> None:
    assert "no session value to check against" in t.media_url_problems("https://s/x", 300, "")


def test_good_media_url_has_no_problem() -> None:
    assert (
        t.media_url_problems("https://s/media/x.mp4?X-Amz-Signature=ab", 900, "SECRETCOOKIE") == []
    )


# ================================================================ timing summary
def test_timing_summary_with_too_few_samples_fails_closed() -> None:
    s = t.timing_summary([10.0] * 4, max_p95_ms=200, min_n=5)
    assert s["ok"] is False
    assert s["n"] == 4


def test_timing_summary_passes_at_target_and_fails_above() -> None:
    assert t.timing_summary([100.0] * 19 + [200.0], max_p95_ms=200, min_n=20)["ok"] is True
    assert t.timing_summary([100.0] * 18 + [250.0] * 2, max_p95_ms=200, min_n=20)["ok"] is False


# ================================================================ pw_timings
pw = _load("pw_timings")


def _attachment(name: str, ms: float) -> dict[str, str]:
    body = base64.b64encode(json.dumps({"ms": ms}).encode()).decode()
    return {"name": name, "contentType": "application/json", "body": body}


def _report(*attachments: dict[str, str]) -> dict:
    return {"suites": [{"specs": [{"tests": [{"results": [{"attachments": list(attachments)}]}]}]}]}


def test_pw_timings_of_a_report_without_timings_is_empty() -> None:
    assert pw.collect(_report()) == {}


def test_pw_timings_collects_samples_by_metric() -> None:
    rep = _report(
        _attachment("timing-tag-optimistic", 120),
        _attachment("axe-T-01", 0),
        _attachment("timing-tag-optimistic", 80),
        _attachment("timing-seek-first-frame", 900),
    )
    assert pw.collect(rep) == {"tag-optimistic": [120.0, 80.0], "seek-first-frame": [900.0]}


def test_pw_timings_refuses_a_malformed_timing_body() -> None:
    bad = {
        "name": "timing-x",
        "contentType": "application/json",
        "body": base64.b64encode(b"not json").decode(),
    }
    with pytest.raises(ValueError, match="timing-x"):
        pw.collect(_report(bad))


def test_pw_timings_cli_fails_when_a_required_metric_is_missing(tmp_path: Path) -> None:
    rep = tmp_path / "e2e.json"
    rep.write_text(json.dumps(_report(*[_attachment("timing-tag-optimistic", 50)] * 20)))
    res = subprocess.run(
        [
            sys.executable,
            str(MEASURE / "pw_timings.py"),
            str(rep),
            "--target",
            "tag-optimistic=200",
            "--target",
            "seek-first-frame=1500",
            "--min-n",
            "20",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert res.returncode == 1
    out = json.loads(res.stdout)
    assert out["metrics"]["tag-optimistic"]["ok"] is True
    assert out["metrics"]["seek-first-frame"]["ok"] is False


def test_pw_timings_cli_passes_when_every_target_is_met(tmp_path: Path) -> None:
    rep = tmp_path / "e2e.json"
    rep.write_text(json.dumps(_report(*[_attachment("timing-tag-optimistic", 50)] * 20)))
    res = subprocess.run(
        [
            sys.executable,
            str(MEASURE / "pw_timings.py"),
            str(rep),
            "--target",
            "tag-optimistic=200",
            "--min-n",
            "20",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert res.returncode == 0, res.stdout + res.stderr


# ======================================================== live scripts refuse below the disk floor
@pytest.mark.parametrize("script", ["live_tagging.py", "tag_latency.py"])
def test_live_scripts_refuse_below_the_disk_floor(script: str) -> None:
    res = subprocess.run(
        [sys.executable, str(MEASURE / script), "--min-free-gb", "100000"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert res.returncode == 2
    assert "prune first" in res.stderr


# ================================ tag_latency seeds through the https origin (SRE-S2-02, QA-RV1-03)
def test_tag_latency_refuses_a_seed_api_that_is_not_an_http_url() -> None:
    res = subprocess.run(
        [sys.executable, str(MEASURE / "tag_latency.py"), "--seed-api", "localhost:34300/api"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert res.returncode == 2
    assert "--seed-api" in res.stderr
    assert "http(s) URL" in res.stderr


def test_tag_latency_seeds_on_the_api_unless_a_seed_api_is_given() -> None:
    tl = _load("tag_latency")
    plain = tl.build_parser().parse_args(["--api", "http://127.0.0.1:34800"])
    assert tl.bases(plain) == ("http://127.0.0.1:34800", "http://127.0.0.1:34800")
    split = tl.build_parser().parse_args(
        ["--api", "http://127.0.0.1:34800", "--seed-api", "https://localhost:34300/api"]
    )
    # Seeding (sign-in, match, tus upload, tags) goes through the origin, where the tus
    # Location's /api prefix is served; the measured load stays on the API port.
    assert tl.bases(split) == ("https://localhost:34300/api", "http://127.0.0.1:34800")
