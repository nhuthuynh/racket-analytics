"""Error vocabulary and the generic error body (ST-005; NFR-058; AQS/SEC-04, AQS/SEC-12).

A shared kernel with no framework imports: contexts raise these exceptions, and one central
handler turns any exception into ``{"error": {"code", "message", "support_ref"}}`` with a fixed
message per code (docs/architecture/api-sprint-00.md §3). Exception text is never sent.
"""

from __future__ import annotations

import secrets
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any, ClassVar

# status -> (code, fixed message); api-sprint-00 §3
STATUS_TABLE: dict[int, tuple[str, str]] = {
    400: ("bad_request", "The request could not be understood."),
    401: ("unauthenticated", "Please sign in."),
    403: ("forbidden_origin", "This request is not allowed."),
    404: ("not_found", "We could not find that."),
    405: ("method_not_allowed", "This action is not allowed here."),
    409: ("conflict", "This changed in the meantime. Please reload."),
    411: ("length_required", "The request needs a Content-Length."),
    412: ("tus_version_unsupported", "Unsupported upload protocol version."),
    413: ("payload_too_large", "This is larger than allowed."),
    415: ("unsupported_media_type", "This content type is not accepted here."),
    422: ("validation_failed", "Some of the information is not valid."),
    429: ("rate_limited", "Too many requests. Please wait and try again."),
    500: ("internal_error", "Something went wrong on our side."),
    503: ("unavailable", "The service is temporarily unavailable."),
}
CODE_MESSAGES: dict[str, str] = dict(STATUS_TABLE.values())
CODE_MESSAGES["upload_offset_mismatch"] = (
    "Upload offset does not match. Ask the server for the current offset."
)
# api-sprint-01 §4.1: codes added in Sprint 1, with fixed messages.
CODE_MESSAGES.update(
    {
        "checksum_invalid": "The upload checksum is not valid.",
        "link_expired": "This sign-in link can no longer be used.",
        "upload_expired": "This upload has expired. Please start again.",
        "video_too_large": "This video is larger than allowed.",
        "not_a_video": "This file is not a video we can read.",
        "upload_quota_exceeded": "You have too many unfinished uploads.",
        "checksum_mismatch": "Part of the upload was damaged. Please send it again.",
    }
)
# Sprint 3 (api-sprint-03 §6.1), fixed messages.
CODE_MESSAGES.update(
    {
        "no_consent": "This match has no consent record for labelling.",
        "invalid_label": "This label is not valid.",
    }
)
# Sprint 2 (ST-026..ST-032; match-aggregate §3 refusals), fixed messages.
CODE_MESSAGES.update(
    {
        "invalid_rally": "These rally times are not possible.",
        "invalid_outcome": "This rally outcome is not possible.",
        "match_not_ready": "Tagging starts once the video is received.",
        "stale_match": "This match changed on another device. Showing the latest score.",
        "game_not_started": "Start a game before tagging rallies.",
        "game_not_over": "The current game is not over yet.",
        "game_over": "This game is over. Start the next game.",
        "match_over": "This match is over.",
        "decision_needed": "Some rallies need your decision first.",
        "nothing_to_undo": "There is nothing to undo.",
        "rules_unavailable": "Scoring for this match format is not available yet.",
        "scorebook_full": "This match cannot hold more rallies or changes.",
        "client_closed_request": "The connection closed before the request was complete.",
    }
)


class AppError(Exception):
    """An expected failure with a known status. ``str(exc)`` is for logs only, never sent."""

    status: int = 500
    code: str = "internal_error"
    headers: ClassVar[Mapping[str, str]] = {}


class BadRequest(AppError):
    status, code = 400, "bad_request"


class Unauthenticated(AppError):
    status, code = 401, "unauthenticated"


class ForbiddenOrigin(AppError):
    status, code = 403, "forbidden_origin"


class NotFound(AppError):
    status, code = 404, "not_found"


class Conflict(AppError):
    status, code = 409, "conflict"


class UploadOffsetMismatch(AppError):
    status, code = 409, "upload_offset_mismatch"


class LengthRequired(AppError):
    status, code = 411, "length_required"


class TusVersionUnsupported(AppError):
    status, code = 412, "tus_version_unsupported"
    headers: ClassVar[Mapping[str, str]] = {"Tus-Version": "1.0.0"}


class PayloadTooLarge(AppError):
    status, code = 413, "payload_too_large"


class UnsupportedMediaType(AppError):
    status, code = 415, "unsupported_media_type"


@dataclass(frozen=True)
class FieldError:
    """One entry of ``fields`` on a 422 (api-sprint-01 §1.1): a path from the route's closed
    list (or ``None``) and a code from the closed table §4.2. Never an input value."""

    field: str | None
    code: str


class ValidationFailed(AppError):
    status, code = 422, "validation_failed"

    def __init__(self, message: str = "validation failed", fields: Iterable[FieldError] = ()):
        super().__init__(message)
        self.fields: tuple[FieldError, ...] = tuple(fields)


class ClientClosedRequest(AppError):
    """The client went away mid-request (C-14, SRE-G2-02): a 400 nobody reads, logged at
    INFO, so an abandoned tab never counts against the availability SLI (NFR-041)."""

    status, code = 400, "client_closed_request"


class Unavailable(AppError):
    status, code = 503, "unavailable"


def new_support_ref() -> str:
    return "ref_" + secrets.token_hex(8)


@dataclass(frozen=True)
class ErrorResponse:
    status: int
    code: str
    message: str
    support_ref: str
    headers: Mapping[str, str] = field(default_factory=dict)
    fields: tuple[FieldError, ...] = ()
    retry_at: str | None = None

    def body(self) -> dict[str, dict[str, Any]]:
        """api-sprint-01 §1.1: ``fields`` only on 422 (always a list), ``retry_at`` only on 429."""
        error: dict[str, Any] = {
            "code": self.code,
            "message": self.message,
            "support_ref": self.support_ref,
        }
        if self.status == 422:
            error["fields"] = [{"field": f.field, "code": f.code} for f in self.fields]
        if self.status == 429:
            error["retry_at"] = self.retry_at
        return {"error": error}


class ErrorMapper:
    """Turns any exception (or bare status) into the generic error response."""

    def __init__(self, new_support_ref: Callable[[], str] = new_support_ref) -> None:
        self._new_ref = new_support_ref

    def map(self, exc: BaseException) -> ErrorResponse:
        if isinstance(exc, AppError):
            return ErrorResponse(
                status=exc.status,
                code=exc.code,
                message=CODE_MESSAGES[exc.code],
                support_ref=self._new_ref(),
                headers={**exc.headers, **getattr(exc, "response_headers", {})},
                fields=getattr(exc, "fields", ()),
                retry_at=getattr(exc, "retry_at", None),
            )
        return self.for_status(500)

    def for_status(self, status: int) -> ErrorResponse:
        if status not in STATUS_TABLE:
            status = 500
        code, message = STATUS_TABLE[status]
        return ErrorResponse(status, code, message, self._new_ref())
