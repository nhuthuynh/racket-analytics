"""In-process domain-event dispatch, after commit (shared kernel; analytics-snapshots.md §4.2;
ADR 0040).

A publisher calls ``publish(event, bind)`` only after its own transaction committed; each
handler gets the event and the database bind and opens its own session (one aggregate per
transaction, ddd-guidelines §4.1). A handler failure is logged and counted, never raised: the
publisher's answer is already decided (IT-03-02 "a failing recompute keeps the tag"). The
retry is the consumer's read repair. Subscriptions are made at the composition root and are
idempotent, so building the app twice (tests) never runs a handler twice.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

log = logging.getLogger(__name__)
Handler = Callable[[Any, Any], None]
_handlers: dict[type, list[Handler]] = {}


def subscribe(event_type: type, handler: Handler) -> None:
    handlers = _handlers.setdefault(event_type, [])
    if handler not in handlers:
        handlers.append(handler)


def publish(event: Any, bind: Any) -> None:
    for handler in list(_handlers.get(type(event), ())):
        try:
            handler(event, bind)
        except Exception as exc:  # noqa: BLE001 - a consumer never fails its publisher
            log.error(
                "event handler failed",
                extra={
                    "event": "platform.event_handler_failed",
                    "event_type": type(event).__name__,
                    "error": type(exc).__name__,
                },
            )
