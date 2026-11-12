"""ST-076c review round 2 (F1): a deletion line names its account even outside a request.

The restore runbook (step 9.1) re-deletes what was deleted after the backup from the
``match.deleted`` and ``account.deleted`` lines, so their ``user_id`` must survive formatting.
``JsonFormatter`` used to drop an explicit ``extra={"user_id": ...}`` in favour of the request
context variable, which is ``None`` outside an authenticated request (CLI, purge, runbook).
"""

from __future__ import annotations

import json
import logging
import uuid

from racket.platform.logs import JsonFormatter, user_id_var


def _line(extra: dict[str, str]) -> dict[str, object]:
    record = logging.makeLogRecord({"name": "racket.test", "msg": "match deleted", **extra})
    line: dict[str, object] = json.loads(JsonFormatter().format(record))
    return line


def test_an_explicit_user_id_is_kept_when_no_request_user_is_set() -> None:
    owner = str(uuid.uuid4())
    token = user_id_var.set(None)
    try:
        line = _line({"event": "match.deleted", "match_id": str(uuid.uuid4()), "user_id": owner})
    finally:
        user_id_var.reset(token)
    assert line["user_id"] == owner


def test_an_explicit_user_id_names_the_subject_over_the_request_user() -> None:
    owner, caller = str(uuid.uuid4()), str(uuid.uuid4())
    token = user_id_var.set(caller)
    try:
        line = _line({"event": "account.deleted", "user_id": owner})
    finally:
        user_id_var.reset(token)
    assert line["user_id"] == owner


def test_the_request_user_fills_lines_without_an_explicit_user_id() -> None:
    caller = str(uuid.uuid4())
    token = user_id_var.set(caller)
    try:
        line = _line({"event": "request"})
    finally:
        user_id_var.reset(token)
    assert line["user_id"] == caller
