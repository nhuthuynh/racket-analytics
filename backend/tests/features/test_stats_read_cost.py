"""Binds tests/features/stats_read_cost.feature (CI-NIGHTLY-PERF; NFR-010 dashboard, NFR-013;
analytics-snapshots.md §4.2).

Through the API on the committed test database (``api`` fixture); the statements a read sends
are recorded on every engine (``tests.support.statements``)."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from tests.support import stats as st
from tests.support.api import ApiDriver
from tests.support.statements import SCOREBOOK_TABLES, reads_of, statements, writes

scenarios("stats_read_cost.feature")

pytestmark = [pytest.mark.needs_verification]

READ_BUDGET = 4  # statements of one dashboard read of an unchanged match (was 9)


@pytest.fixture
def ctx(monkeypatch: pytest.MonkeyPatch, tmp_path: Any) -> Iterator[dict[str, Any]]:
    st.with_statuses(monkeypatch, tmp_path)
    yield {}
    st.clear_dictionary_cache()


@given(parsers.parse('"{user}" has tagged the worked example'))
def tagged(api: ApiDriver, ctx: dict[str, Any], committed_db: Any, user: str) -> None:
    ctx["match"] = st.tagged_example(api, user, "CI-NIGHTLY-PERF scenario")


@given(parsers.parse('"{user}" has read the stats of the match'))
def has_read(api: ApiDriver, ctx: dict[str, Any], user: str) -> None:
    ctx["before"] = st.stats_body(api, user, ctx["match"])


@when(parsers.parse('"{user}" corrects rally 3 of the match'))
def corrects(api: ApiDriver, ctx: dict[str, Any], user: str) -> None:
    assert st.correct_rally_3(api, user, ctx["match"]).status_code == 200


@when(parsers.parse('"{user}" reads the stats of the match'))
def reads_stats(api: ApiDriver, ctx: dict[str, Any], user: str) -> None:
    ctx["after"] = st.stats_body(api, user, ctx["match"])


@when(parsers.parse('"{user}" reads the stats and the evidence of the match'))
def reads_both(api: ApiDriver, ctx: dict[str, Any], user: str) -> None:
    sent_per_read = []
    for read in (
        lambda: st.stats(api, user, ctx["match"]),
        lambda: st.evidence(api, user, ctx["match"], "AN-01", "A"),
    ):
        with statements() as sent:
            assert read().status_code == 200
        sent_per_read.append(sent)
    ctx["sent"] = sent_per_read


@then("the stats read are the corrected worked example")
def corrected(ctx: dict[str, Any]) -> None:
    assert st.stats_diffs(st.reference(st.corrected_example()), ctx["after"]) == []
    assert ctx["after"]["sheet_version"] > ctx["before"]["sheet_version"]


@then("the reads replayed no scorebook and wrote nothing")
def nothing_replayed(ctx: dict[str, Any]) -> None:
    for sent in ctx["sent"]:
        assert reads_of(sent, *SCOREBOOK_TABLES) == []
        assert writes(sent) == []
        assert len(sent) <= READ_BUDGET, sent
