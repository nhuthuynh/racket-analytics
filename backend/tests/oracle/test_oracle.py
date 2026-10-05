"""Self-tests of the differential oracle P9 (ST-022, NFR-002b; sprint-01 §14.3.7).

The oracle is only useful if (1) it agrees with the golden rows the coach reviews, and (2) the
comparison can tell a wrong engine from a right one (positive control, retro 0 lesson L4).
Only the last test touches the production engine, through the seams (RED until ST-020).
"""

from __future__ import annotations

import os
from dataclasses import replace

import pytest

from tests.oracle import differential, mutants
from tests.oracle import engine as oracle
from tests.support.golden_tables import example_rows
from tests.support.scoring import random_sequences

PROVISIONAL = oracle.Rules(points_to_win=11, win_by=2, first_service_single_server=True)
FAULTS = {"serve", "foot fault on serve", "two-bounce", "nvz", "other"}


def _declared(call: str, serving: str) -> oracle.OracleState:
    s, r, n = (int(x) for x in call.split("-"))
    a, b = (s, r) if serving == "A" else (r, s)
    base = oracle.start(PROVISIONAL, serving)
    server = base.server if n == 1 else oracle.PARTNER[base.server]
    return replace(base, a=a, b=b, server_number=n, server=server)


def _call(st: oracle.OracleState) -> str:
    s, r = (st.a, st.b) if st.serving == "A" else (st.b, st.a)
    return f"{s}-{r}-{st.server_number}"


def _raw(word: str, st: oracle.OracleState, fault: str | None = None) -> tuple[str, ...]:
    if word == "replay":
        return ("replay",)
    who = st.serving if word == "serving" else oracle.OTHER[st.serving]
    return ("fault", who, fault.upper()) if fault else ("won", who)


SOD = [r for r in example_rows("side_out_doubles_provisional.feature") if "after" in r]
SOD_END = [r for r in example_rows("side_out_doubles_provisional.feature") if "state" in r]
FAULT_ROWS = [r for r in example_rows("faults_provisional.feature") if "after" in r]


def test_golden_tables_are_found() -> None:
    assert {r["id"] for r in SOD} == {f"SOD-{n:02d}" for n in (1, 2, 3, 4, 5, 8, 10, 16)}
    assert {r["id"] for r in SOD_END} == {"SOD-07", "SOD-09", "SOD-11"}
    assert {r["id"] for r in FAULT_ROWS} == {f"F-0{n}" for n in range(1, 6)}


@pytest.mark.parametrize("row", SOD, ids=lambda r: r["id"])
def test_oracle_matches_side_out_rows(row: dict[str, str]) -> None:
    before = _declared(row["before"], row["srv"])
    after = oracle.step(before, _raw(row["winner"], before), PROVISIONAL)
    assert (_call(after), after.serving) == (row["after"], row["next"])


@pytest.mark.parametrize("row", SOD_END, ids=lambda r: r["id"])
def test_oracle_matches_game_end_rows(row: dict[str, str]) -> None:
    before = _declared(row["before"], "A")
    after = oracle.step(before, _raw(row["winner"], before), PROVISIONAL)
    _, letter, score = row["state"].rsplit(" ", 2)
    a, b = (int(x) for x in score.split("-"))
    assert (after.winner, after.a, after.b) == (letter, a, b)


@pytest.mark.parametrize("row", FAULT_ROWS, ids=lambda r: r["id"])
def test_oracle_matches_fault_rows(row: dict[str, str]) -> None:
    before = _declared(row["before"], "A")
    kind = {"foot fault on serve": "foot", "two-bounce": "two_bounce"}.get(
        row["fault"], row["fault"]
    )
    after = oracle.step(before, _raw(row["side"], before, kind), PROVISIONAL)
    assert (_call(after), after.serving) == (row["after"], row["next"])


def test_oracle_starts_on_server_2_with_the_first_service_exception() -> None:
    assert _call(oracle.start(PROVISIONAL, "A")) == "0-0-2"
    assert (
        _call(oracle.start(replace(PROVISIONAL, first_service_single_server=False), "B")) == "0-0-1"
    )


def test_oracle_refuses_a_rally_after_game_over() -> None:
    over = oracle.step(_declared("10-8-1", "A"), ("won", "A"), PROVISIONAL)
    assert over.winner == "A"
    with pytest.raises(oracle.GameAlreadyOver):
        oracle.step(over, ("replay",), PROVISIONAL)


def test_oracle_agrees_with_itself() -> None:
    report = differential.compare(differential.oracle_run, random_sequences(7, 300))
    assert report.passed
    assert report.sequences == 300


def test_positive_control_a_wrong_engine_is_caught_with_the_shortest_sequence() -> None:
    report = differential.compare(mutants.receiver_scores, random_sequences(11, 300))
    assert not report.passed
    assert report.disagreements > 0
    shortest = report.shortest
    assert shortest is not None
    # minimal: the sequence without its last rally still agrees, the full one does not
    seq = [tuple(r) for r in shortest.sequence]
    rules = oracle.Rules(**shortest.rules)
    first = shortest.first_server
    assert mutants.receiver_scores(seq[:-1], rules, first) == differential.oracle_run(
        seq[:-1], rules, first
    )
    assert mutants.receiver_scores(seq, rules, first) != differential.oracle_run(seq, rules, first)
    assert seq[-1][0] == "won"  # the bug fires on a receiving-side win
    assert shortest.expected != shortest.actual


@pytest.mark.red_until(story="ST-020")
def test_differential_production_engine_agrees_with_the_oracle() -> None:
    """NFR-002a/b: 1,000 sequences per CI run; the nightly job sets ORACLE_SEQUENCES=100000."""
    count = int(os.environ.get("ORACLE_SEQUENCES", "1000"))
    report = differential.compare(differential.production_run, random_sequences(20261019, count))
    assert report.passed, f"{report.disagreements} disagreements; shortest: {report.shortest}"
