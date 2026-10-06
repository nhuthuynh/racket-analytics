"""Sprint 3 goal-scorecard harness (docs/sprints/03/goal-scorecard.md, PO standing rule).

`scripts/measure/statslib.py` is an **independent reference** for the starter stats AN-01..AN-07
(docs/domain/metric-dictionary.md, all PROVISIONAL-UNVERIFIED rules, ADR 0009) plus the
Wilson interval and low-sample rule (FR-101, ADR 0005), the evidence check (FR-103) and the
purge inventory (FR-006, FR-007, NFR-066). The live scripts compare the product with it.

Negative cases first: an empty, unmatched or malformed input never reads as a pass (fail
closed, ADR 0014). The worked example of metric-dictionary §2 (hand count by the coach) is the
oracle for the stats; the Wilson values are checked against the closed form at k = 0.
"""

from __future__ import annotations

import importlib.util
import sys

import pytest
from conftest import SCRIPTS_DIR

pytestmark = pytest.mark.unit

MEASURE = SCRIPTS_DIR / "measure"
if str(MEASURE) not in sys.path:
    sys.path.insert(0, str(MEASURE))


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, MEASURE / f"{name}.py")
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


s = _load("statslib")


def _t(winner, ending, subtype=None, player=None):
    return {
        "winning_side": winner,
        "ending": ending,
        "fault_kind": subtype,
        "responsible_player": player,
    }


# metric-dictionary §2 worked example (the replay has no winning side, taglib convention).
WORKED = [
    _t("A", "winner", None, "A1"),
    _t("B", "fault", "serve", "A2"),
    _t("B", "winner"),
    _t("B", "unforced_error", None, "A1"),
    _t("A", "forced_error", None, "B2"),
    _t("A", "fault", "nvz", "B1"),
    _t("A", "winner", None, "A2"),
    _t(None, "replay"),
    _t("A", "unforced_error"),
    _t("B", "unforced_error", None, "A2"),
    _t("A", "fault"),
    _t("B", "fault", "serve", "A1"),
    _t("B", "winner", None, "B1"),
    _t("B", "winner", None, "B2"),
]


# ======================================== Wilson and low sample: refusals first
def test_wilson_with_no_sample_is_none() -> None:
    assert s.wilson(0, 0) is None


@pytest.mark.parametrize(("k", "n"), [(-1, 5), (6, 5), (1, -1)])
def test_wilson_refuses_impossible_counts(k: int, n: int) -> None:
    with pytest.raises(ValueError, match="impossible"):
        s.wilson(k, n)


def test_wilson_zero_successes_matches_closed_form() -> None:
    lo, hi = s.wilson(0, 6)
    z2 = s.Z95**2
    assert lo == 0.0
    assert hi == pytest.approx(z2 / (6 + z2), abs=1e-9)


@pytest.mark.parametrize(
    ("k", "n", "lo", "hi"),
    [(22, 40, 0.3983, 0.6929), (4, 8, 0.2152, 0.7848), (4, 7, 0.2505, 0.8418)],
)
def test_wilson_known_values(k: int, n: int, lo: float, hi: float) -> None:
    got = s.wilson(k, n)
    assert got[0] == pytest.approx(lo, abs=1e-4)
    assert got[1] == pytest.approx(hi, abs=1e-4)


@pytest.mark.parametrize(
    ("n", "won", "flag"),
    [(0, 0, True), (8, 4, True), (19, 19, True), (40, 22, False)],
)
def test_low_sample_examples_of_fr_101(n: int, won: int, flag: bool) -> None:
    assert s.proportion_flag(won, n) is flag


def test_low_sample_flags_a_wide_interval_even_at_n_20() -> None:
    # 10/20: width 0.4 > 0.30 -> flagged though n >= 20 (FR-101 second clause)
    assert s.proportion_flag(10, 20) is True


def test_count_metric_flag_needs_two_games() -> None:
    assert s.count_flag(games=1) is True
    assert s.count_flag(games=2) is False


# ======================================== annotate: refusals first
def test_annotate_refuses_unknown_ending() -> None:
    with pytest.raises(ValueError, match="ending"):
        s.annotate([_t("A", "smash")], first_serving_side="A")


def test_annotate_refuses_an_empty_game() -> None:
    with pytest.raises(ValueError, match="no rallies"):
        s.annotate([], first_serving_side="A")


def test_annotate_marks_the_replay_excluded() -> None:
    recs = s.annotate(WORKED, first_serving_side="A")
    assert [r["excluded"] for r in recs].count(True) == 1
    assert recs[7]["excluded"] is True


def test_annotate_reads_points_from_the_score_sequence() -> None:
    recs = s.annotate(WORKED, first_serving_side="A")
    assert recs[0]["serving_side"] == "A"
    assert recs[0]["point_to"] == "A"
    assert recs[1]["point_to"] is None  # side-out, no point (provisional rule)
    assert recs[-1]["score_after"] == {"A": 4, "B": 4}


# ======================================== the coach's hand count (metric-dictionary §2)
@pytest.fixture(scope="module")
def worked() -> dict:
    return s.starter_stats([{"first_serving_side": "A", "tags": WORKED}])


def test_an01_rallies_won_on_serve(worked: dict) -> None:
    assert (worked["AN-01"]["A"]["k"], worked["AN-01"]["A"]["n"]) == (4, 7)
    assert (worked["AN-01"]["B"]["k"], worked["AN-01"]["B"]["n"]) == (4, 6)
    assert worked["AN-01"]["A"]["low_sample"] is True


def test_an02_rallies_won_when_receiving(worked: dict) -> None:
    assert (worked["AN-02"]["A"]["k"], worked["AN-02"]["A"]["n"]) == (2, 6)
    assert (worked["AN-02"]["B"]["k"], worked["AN-02"]["B"]["n"]) == (3, 7)


def test_an03_points_per_service_turn(worked: dict) -> None:
    assert (worked["AN-03"]["A"]["points"], worked["AN-03"]["A"]["turns"]) == (4, 2)
    assert (worked["AN-03"]["B"]["points"], worked["AN-03"]["B"]["turns"]) == (4, 2)
    assert worked["AN-03"]["A"]["value"] == 2.0
    assert worked["AN-03"]["A"]["low_sample"] is True  # < 10 turns


def test_an04_unforced_errors_per_game(worked: dict) -> None:
    assert worked["AN-04"]["A"]["count"] == 2
    assert worked["AN-04"]["A"]["by_player"] == {"A1": 1, "A2": 1}
    assert worked["AN-04"]["B"]["count"] == 1
    assert worked["AN-04"]["B"]["player_not_tagged"] == 1
    assert worked["AN-04"]["A"]["games"] == 1
    assert worked["AN-04"]["A"]["low_sample"] is True


def test_an05_serve_faults(worked: dict) -> None:
    assert (worked["AN-05"]["A"]["k"], worked["AN-05"]["A"]["n"]) == (2, 7)
    assert (worked["AN-05"]["B"]["k"], worked["AN-05"]["B"]["n"]) == (0, 6)
    assert worked["AN-05"]["A"]["fault_type_not_tagged"] == 0


def test_an06_longest_run(worked: dict) -> None:
    assert worked["AN-06"]["A"]["longest"] == 3
    assert worked["AN-06"]["B"]["longest"] == 2
    assert worked["AN-06"]["A"]["low_sample"] is False  # descriptive, never flagged
    assert worked["AN-06"]["B"]["histogram"] == {"1": 0, "2": 2, "3": 0, "4": 0, "5+": 0}


def test_an07_rally_ending_mix(worked: dict) -> None:
    a, b = worked["AN-07"]["A"], worked["AN-07"]["B"]
    assert a["n"] == 6
    assert a["counts"] == {"winner": 2, "unforced_error": 2, "forced_error": 0, "fault": 2}
    assert b["n"] == 7
    assert b["counts"] == {"winner": 3, "unforced_error": 1, "forced_error": 1, "fault": 2}


def test_every_metric_carries_its_rally_numbers(worked: dict) -> None:
    # FR-103: the evidence of AN-01 for A is the 7 rallies A served (replay excluded)
    assert worked["AN-01"]["A"]["rallies"] == [1, 2, 7, 9, 10, 11, 12]


# ======================================== FR-109 attribution conservation
def test_conservation_holds_on_the_worked_example() -> None:
    assert s.conservation_problems([{"first_serving_side": "A", "tags": WORKED}]) == []


def test_conservation_detects_a_rally_counted_twice() -> None:
    lost = {"A": {"serve": [2, 10], "receive": [3, 4, 13, 14]}}
    attributed = {"A": {"serve": [2, 10, 10], "receive": [3, 4, 13, 14]}}
    assert s.attribution_problems(lost, attributed)


# ======================================== compare with the API: fail closed
def test_compare_nothing_is_not_a_pass(worked: dict) -> None:
    assert s.compare_stats(worked, {}) == ["no metrics in the response"]


def test_compare_reports_a_missing_metric(worked: dict) -> None:
    actual = s.as_api_shape(worked)
    del actual["metrics"]["AN-03"]
    assert any("AN-03" in d for d in s.compare_stats(worked, actual))


def test_compare_reports_a_wrong_n(worked: dict) -> None:
    actual = s.as_api_shape(worked)
    actual["metrics"]["AN-01"]["A"]["n"] = 8
    assert any("AN-01 A n" in d for d in s.compare_stats(worked, actual))


def test_compare_reports_a_missing_low_sample_flag(worked: dict) -> None:
    actual = s.as_api_shape(worked)
    actual["metrics"]["AN-02"]["B"]["low_sample"] = False
    assert any("AN-02 B low_sample" in d for d in s.compare_stats(worked, actual))


def test_compare_accepts_its_own_shape(worked: dict) -> None:
    assert s.compare_stats(worked, s.as_api_shape(worked)) == []


# ======================================== evidence (FR-103, NFR-038)
def test_evidence_with_more_than_ten_items_is_refused() -> None:
    body = {"total": 12, "items": [{"number": i} for i in range(1, 12)]}
    assert any("more than 10" in p for p in s.evidence_problems(body, list(range(1, 13))))


def test_evidence_total_must_equal_n() -> None:
    body = {"total": 6, "items": [{"number": 1}]}
    assert any("total" in p for p in s.evidence_problems(body, [1, 2, 7, 9, 10, 11, 12]))


def test_evidence_item_outside_the_metric_is_refused() -> None:
    body = {"total": 2, "items": [{"number": 1}, {"number": 3}]}
    assert any("rally 3" in p for p in s.evidence_problems(body, [1, 2]))


def test_empty_evidence_for_a_non_empty_metric_is_refused() -> None:
    assert s.evidence_problems({"total": 0, "items": []}, [1]) != []


def test_good_evidence_passes() -> None:
    body = {"total": 2, "items": [{"number": 1}, {"number": 2}]}
    assert s.evidence_problems(body, [1, 2]) == []


# ======================================== purge inventory (FR-006, FR-007, NFR-066)
def test_inventory_refuses_an_id_that_is_not_a_uuid() -> None:
    with pytest.raises(ValueError, match="uuid"):
        s.count_sql([("matches", "id")], ["1; drop table matches"])


def test_inventory_with_no_tables_is_refused() -> None:
    with pytest.raises(ValueError, match="no tables"):
        s.count_sql([], ["0b6f5c3e-1c2d-4e5f-8a9b-0c1d2e3f4a5b"])


def test_inventory_refuses_an_unsafe_identifier() -> None:
    with pytest.raises(ValueError, match="identifier"):
        s.count_sql([('matches"; --', "id")], ["0b6f5c3e-1c2d-4e5f-8a9b-0c1d2e3f4a5b"])


def test_inventory_counts_every_pair() -> None:
    sql = s.count_sql(
        [("matches", "id"), ("match_rallies", "match_id")],
        ["0b6f5c3e-1c2d-4e5f-8a9b-0c1d2e3f4a5b"],
    )
    assert '"matches"' in sql
    assert '"match_rallies"' in sql
    assert sql.count("UNION ALL") == 1


def test_purge_problems_fail_closed() -> None:
    assert s.purge_problems({}) == ["no tables inventoried"]
    assert s.purge_problems({"matches.id": 0, "match_rallies.match_id": 2}) == [
        "match_rallies.match_id: 2 rows left"
    ]
    assert s.purge_problems({"matches.id": 0}) == []


def test_parse_counts_reads_psql_unaligned_output() -> None:
    out = "matches.id|0\nmatch_rallies.match_id|3\n"
    assert s.parse_counts(out) == {"matches.id": 0, "match_rallies.match_id": 3}
    with pytest.raises(ValueError, match=r"key\|count"):
        s.parse_counts("garbage\n")


# ======================================== the live journey's stats game
def test_live_stats_game_is_the_worked_example() -> None:
    strip = [{k: r[k] for k in WORKED[0]} for r in s.STATS_TAGS]
    assert strip == WORKED


def test_live_stats_game_is_valid_under_i6() -> None:
    t = sys.modules["taglib"]
    assert t.outcome_problems(s.STATS_TAGS) == []
    corrected = t.with_winner(s.STATS_TAGS, rally=s.CORRECTED_RALLY, side="A")
    assert t.outcome_problems(corrected) == []


def test_correction_changes_the_reference() -> None:
    t = sys.modules["taglib"]
    before = s.starter_stats([{"first_serving_side": "A", "tags": s.STATS_TAGS}])
    corrected = t.with_winner(s.STATS_TAGS, rally=s.CORRECTED_RALLY, side="A")
    after = s.starter_stats([{"first_serving_side": "A", "tags": corrected}])
    assert s.compare_stats(after, s.as_api_shape(before)) != []


# ======================================== live scripts refuse to start rather than pass
def test_live_stats_refuses_below_the_disk_floor() -> None:
    live = _load("live_stats")
    assert live.main(["--min-free-gb", "100000"]) == 2


def test_live_stats_refuses_a_purge_check_without_psql() -> None:
    live = _load("live_stats")
    assert live.main(["--min-free-gb", "0", "--purge-cmd", "true"]) == 2


def test_stats_latency_refuses_below_the_disk_floor() -> None:
    lat = _load("stats_latency")
    assert lat.main(["--min-free-gb", "100000"]) == 2


def test_stats_contract_paths_fill_every_placeholder() -> None:
    sk = _load("statscontract")
    for name in sk.ROUTES:
        _, p = sk.path(name, match_id="m", metric_id="AN-01", side="A")
        assert "{" not in p
