"""ErrorMapper (ST-005; sprint-00 §5 TDD plan, in order; NFR-058; AQS/SEC-04, AQS/SEC-12)."""

from __future__ import annotations

import itertools
import re

from racket.platform.errors import (
    ErrorMapper,
    NotFound,
    TusVersionUnsupported,
    UploadOffsetMismatch,
    ValidationFailed,
)

SECRETISH = "password=hunter2 SELECT * FROM matches at racket.matches.repository line 87"


def mapper() -> ErrorMapper:
    counter = itertools.count()
    return ErrorMapper(new_support_ref=lambda: f"ref_{next(counter):016x}")


# 1. unknown exception -> generic 500 body with support_ref and no stack trace
def test_unknown_exception_becomes_a_generic_500() -> None:
    error = mapper().map(RuntimeError(SECRETISH))

    assert error.status == 500
    assert error.body() == {
        "error": {
            "code": "internal_error",
            "message": "Something went wrong on our side.",
            "support_ref": "ref_0000000000000000",
        }
    }
    assert "hunter2" not in repr(error.body())


def test_support_refs_differ_per_error() -> None:
    m = mapper()

    assert m.map(RuntimeError()).support_ref != m.map(RuntimeError()).support_ref


def test_default_support_ref_has_the_contract_shape() -> None:
    ref = ErrorMapper().map(RuntimeError()).support_ref

    assert re.fullmatch(r"ref_[0-9a-f]{16}", ref)


# 2. domain NotFound -> 404 generic body
def test_not_found_is_a_generic_404() -> None:
    error = mapper().map(NotFound("match 42 of owner 7 is not there"))

    assert error.status == 404
    assert error.body()["error"]["code"] == "not_found"
    assert error.body()["error"]["message"] == "We could not find that."


# 3. validation error -> 422 without echoing input or secrets
def test_validation_failure_is_422_without_echoing_input() -> None:
    error = mapper().map(ValidationFailed(f"title={SECRETISH!r} is invalid"))

    assert error.status == 422
    assert error.body()["error"]["code"] == "validation_failed"
    assert "hunter2" not in repr(error.body())


def test_status_only_errors_use_the_contract_table() -> None:
    m = mapper()

    assert m.for_status(405).body()["error"]["code"] == "method_not_allowed"
    assert m.for_status(404).body()["error"]["code"] == "not_found"
    assert m.for_status(418).status == 500  # anything off the table is a generic 500


def test_tus_errors_carry_their_code_and_headers() -> None:
    m = mapper()

    conflict = m.map(UploadOffsetMismatch())
    version = m.map(TusVersionUnsupported())

    assert (conflict.status, conflict.code) == (409, "upload_offset_mismatch")
    assert (version.status, version.code) == (412, "tus_version_unsupported")
    assert version.headers == {"Tus-Version": "1.0.0"}
