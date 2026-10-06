"""IT-00-15 (logs, ST-005; NFR-069, NFR-076b; AQS/OPS-03): structured JSON logs carry the
correlation fields, and a scanner over the run finds no email, nickname or signed URL."""

from __future__ import annotations

import json
import logging
from typing import Any

import pytest

from tests.support import contract
from tests.support.api import ApiDriver
from tests.support.flows import create_match, upload_fixture
from tests.support.logscan import scan

pytestmark = pytest.mark.slow

NICKNAMES = ["ivy", "carlos"]


def _flow(api: ApiDriver) -> None:
    ivy = api.as_user("ivy")
    match_id = api.run(create_match(ivy, "Log scan with Carlos"))
    api.run(upload_fixture(ivy, match_id))
    contract.WORKER_RUN_UNTIL_IDLE.load()()
    api.request("carlos", "GET", contract.MATCH.format(match_id=match_id))  # a security event


def test_no_personal_data_or_signed_urls_in_logs(
    api: ApiDriver, caplog: pytest.LogCaptureFixture, capfd: pytest.CaptureFixture[str]
) -> None:
    with caplog.at_level(logging.DEBUG):
        _flow(api)
    out, err = capfd.readouterr()
    lines = out.splitlines() + err.splitlines() + [caplog.handler.format(r) for r in caplog.records]
    lines += [json.dumps(r.__dict__, default=str) for r in caplog.records]

    assert lines, "nothing was logged; the scan would be vacuous"
    assert scan(lines, nicknames=NICKNAMES) == []


def test_request_log_lines_are_json_with_correlation_fields(
    api: ApiDriver, capfd: pytest.CaptureFixture[str]
) -> None:
    api.request("anonymous", "GET", "/healthz")
    out, _ = capfd.readouterr()
    records: list[dict[str, Any]] = [
        json.loads(line) for line in out.splitlines() if line.startswith("{")
    ]

    assert records, "no JSON log line on stdout"
    for record in records:
        assert record["ts"].endswith("Z") or record["ts"].endswith("+00:00")
        assert {"level", "msg", "trace_id", "request_id"} <= set(record)
