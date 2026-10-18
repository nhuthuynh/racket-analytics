"""The match purge removes the plan rows naming the match before the match row (ST-061b review
PE-ST061b-01/02; T4-PL-9, SEC-S4-TM-03; ADR 0042 order; coaching-plan §8;
deletion-and-purge.md §4.2). Each context's port is faked; the live check is IT-04-02."""

from __future__ import annotations

import uuid
from typing import Any

import pytest

from racket.platform import purge

pytestmark = [pytest.mark.unit]

MATCH = uuid.UUID(int=11)
SESSION = object()
PORTS = (
    "racket.analytics.public.purge_match",
    "racket.dataset.public.purge_match",
    "racket.analysis_jobs.public.purge_match",
    "racket.video_ingest.public.purge_match",
    "racket.coaching.public.purge_match",
    "racket.matches.public.purge_match",
)


def _record(calls: list[str], name: str) -> Any:
    def port(session: Any, match_id: uuid.UUID) -> int:
        assert (session, match_id) == (SESSION, MATCH)
        calls.append(name)
        return 1

    return port


def test_a_failed_plan_purge_leaves_the_match_row(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []
    for port in PORTS:
        monkeypatch.setattr(port, _record(calls, port.split(".")[1]))

    def failing(session: Any, match_id: uuid.UUID) -> int:
        calls.append("coaching")
        raise RuntimeError("plan rows not deleted")

    monkeypatch.setattr("racket.coaching.public.purge_match", failing)
    with pytest.raises(RuntimeError):
        purge.ContextPorts().purge_rows(SESSION, MATCH)
    assert "coaching" in calls
    assert "matches" not in calls


def test_plan_rows_go_before_the_match_row_and_are_counted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []
    for port in PORTS:
        monkeypatch.setattr(port, _record(calls, port.split(".")[1]))
    assert purge.ContextPorts().purge_rows(SESSION, MATCH) == len(PORTS)
    assert calls[-1] == "matches"
    assert "coaching" in calls
