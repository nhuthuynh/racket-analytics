"""The G02-01 harness reads refusal codes from the api-sprint-00 §3 envelope (BE-D1-01,
QA-RV1-02; api-sprint-02 §1.1): ``{"error": {"code", "message", "support_ref"}}``."""

from __future__ import annotations

import importlib.util
import sys
from types import ModuleType

import pytest

from tests.support.paths import REPO


def _harness() -> ModuleType:
    path = REPO / "scripts" / "measure" / "live_tagging.py"
    spec = importlib.util.spec_from_file_location("live_tagging_under_test", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class _Reply:
    def __init__(self, body: bytes) -> None:
        self.body = body

    def json(self) -> object:
        import json

        return json.loads(self.body or b"null")


@pytest.mark.parametrize(
    "body",
    [
        b'{"code": "stale_match"}',  # not the contract's shape: must not count as a pass
        b"not json",
        b"",
        b'{"error": null}',
        b'{"error": "stale_match"}',
        b'["stale_match"]',
    ],
)
def test_a_body_outside_the_envelope_has_no_code(body: bytes) -> None:
    assert _harness()._code(_Reply(body)) is None


@pytest.mark.parametrize("code", ["stale_match", "match_not_ready", "invalid_outcome"])
def test_the_code_is_read_from_the_error_envelope(code: str) -> None:
    body = (
        '{"error": {"code": "%s", "message": "x", "support_ref": "ref_0123456789abcdef"}}' % code
    ).encode()
    assert _harness()._code(_Reply(body)) == code
