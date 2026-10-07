"""In-process after-commit dispatch (ST-046; ADR 0040; analytics-snapshots.md §4.2 step 3)."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

import pytest

from racket.platform import events

pytestmark = [pytest.mark.unit]


@dataclass(frozen=True)
class Happened:
    n: int


@pytest.fixture(autouse=True)
def clean() -> Iterator[None]:
    saved = dict(events._handlers)
    events._handlers.clear()
    yield
    events._handlers.clear()
    events._handlers.update(saved)


def test_a_failing_handler_never_reaches_the_publisher_and_later_handlers_still_run(
    caplog: pytest.LogCaptureFixture,
) -> None:
    seen: list[Any] = []

    def broken(event: Any, bind: Any) -> None:
        raise RuntimeError("secret detail")

    events.subscribe(Happened, broken)
    events.subscribe(Happened, lambda e, b: seen.append((e, b)))
    events.publish(Happened(1), "bind")
    assert seen == [(Happened(1), "bind")]
    failed = [
        r for r in caplog.records if getattr(r, "event", "") == "platform.event_handler_failed"
    ]
    assert len(failed) == 1
    assert failed[0].error == "RuntimeError"  # the class only, never the message
    assert "secret detail" not in caplog.text


def test_subscribing_twice_runs_the_handler_once() -> None:
    seen: list[int] = []

    def handler(event: Happened, bind: Any) -> None:
        seen.append(event.n)

    events.subscribe(Happened, handler)
    events.subscribe(Happened, handler)
    events.publish(Happened(7), None)
    assert seen == [7]


def test_an_event_without_subscribers_does_nothing() -> None:
    events.publish(Happened(1), None)
