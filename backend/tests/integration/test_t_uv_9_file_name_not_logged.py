"""T-UV-9 (ST-017; threat-model-sprint-01 §3; ASVS 5.3.2, 16.2.5): the stored file name is
display-only. It never appears in a log line or an object key across the whole flow: creation,
every PATCH, completion and the probe in the worker. SEC-R4-S1-03: the threat model named this
log scan but no test ran it.

Positive controls (testing-strategy rule 8): the name does reach the server (the owner's read
model shows it mid-upload), and the scan does see a known value from the same run (the match
id), so an empty capture cannot pass.
"""

from __future__ import annotations

import json
import logging

import pytest

from tests.support import contract, tus_ext
from tests.support.api import ApiDriver
from tests.support.flows import create_match
from tests.support.paths import SYNTHETIC_CLIP
from tests.support.written_keys import WrittenKeys

pytestmark = [pytest.mark.slow]

FILE_NAME = "Zq7 secret-court-tuesday.mp4"
MARKERS = ("Zq7", "secret-court-tuesday")


def test_t_uv_9_the_file_name_is_in_no_log_line_and_no_object_key(
    api: ApiDriver,
    written_keys: WrittenKeys,
    caplog: pytest.LogCaptureFixture,
    capfd: pytest.CaptureFixture[str],
) -> None:
    data = SYNTHETIC_CLIP.read_bytes()
    ivy = api.as_user("ivy")
    with caplog.at_level(logging.DEBUG):
        match_id = api.run(create_match(ivy, "T-UV-9"))
        upload = api.run(tus_ext.start(ivy, match_id, data, filename=FILE_NAME))
        first = tus_ext.first_chunk_size(data)
        assert api.run(tus_ext.patch(ivy, upload, 0, data[:first])).status_code == 204
        mid = api.request("ivy", "GET", contract.MATCH.format(match_id=match_id)).json()
        assert mid["upload"]["file_name"] == FILE_NAME  # positive control: the name was sent
        assert api.run(tus_ext.patch(ivy, upload, first, data[first:])).status_code == 204
        contract.WORKER_RUN_UNTIL_IDLE.load()()

    out, err = capfd.readouterr()
    lines = out.splitlines() + err.splitlines()
    lines += [caplog.handler.format(r) for r in caplog.records]
    lines += [json.dumps(r.__dict__, default=str) for r in caplog.records]

    assert any(match_id in line for line in lines), "the scan saw nothing from this run"
    leaks = [line for line in lines if any(m in line for m in MARKERS)]
    assert leaks == []
    assert written_keys.written, "nothing was stored; the key check would be vacuous"
    assert [k for k in written_keys.written if any(m in k for m in MARKERS)] == []
