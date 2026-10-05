"""tus 1.0.0 core routes (ST-008; ADR 0011; api-sprint-00 §6).

Checks run in the contract's order and the first failure wins: 401 (dependency), 412, 404,
415, 400, 411/413, 409 (upload complete), 409, 413. A PATCH body is read only after every
header check passed, and only up to ``Content-Length`` bytes; a short body stores nothing
(atomic PATCH).
"""

from __future__ import annotations

import email.utils
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from racket.platform.db import get_session
from racket.platform.errors import (
    BadRequest,
    PayloadTooLarge,
    TusVersionUnsupported,
    UnsupportedMediaType,
)
from racket.platform.http import ERROR_HEADERS_STATE
from racket.platform.settings import Settings
from racket.players.api import CurrentAccount
from racket.video_ingest.domain import (
    ChunkBeyondLength,
    OffsetMismatch,
    UploadAlreadyComplete,
    UploadChecksum,
)
from racket.video_ingest.service import (
    UploadService,
    parse_content_length,
    parse_upload_offset,
)

TUS_VERSION = "1.0.0"
OCTET = "application/offset+octet-stream"
TUS_HEADERS = {"Tus-Resumable": TUS_VERSION}


def _tus_headers_on_errors(request: Request) -> None:
    """Every tus response carries ``Tus-Resumable``, errors included (api-sprint-00 §6)."""
    setattr(request.state, ERROR_HEADERS_STATE, TUS_HEADERS)


# A router dependency runs before the route's own (session, ownership), so even 401 has it.
router = APIRouter(dependencies=[Depends(_tus_headers_on_errors)])


def get_upload_service(
    request: Request, session: Annotated[Session, Depends(get_session)]
) -> UploadService:
    return UploadService(session, request.app.state.object_store(), request.app.state.settings)


Service = Annotated[UploadService, Depends(get_upload_service)]


def _require_tus(request: Request) -> None:
    if request.headers.get("tus-resumable") != TUS_VERSION:
        raise TusVersionUnsupported("missing or unsupported Tus-Resumable")


def _route(request: Request) -> str:
    return getattr(request.scope.get("route"), "path", "")


def http_date(value: datetime | None) -> dict[str, str]:
    """``Upload-Expires`` as an HTTP-date (tus expiration extension, api-sprint-01 §6.4)."""
    if value is None:
        return {}
    return {"Upload-Expires": email.utils.format_datetime(value.astimezone(UTC), usegmt=True)}


policy_router = APIRouter()


@policy_router.get("/upload-policy")
def upload_policy(request: Request, account: CurrentAccount) -> dict[str, Any]:
    """Caps and chunk bounds from configuration (api-sprint-01 §6.1; provisional until R-05)."""
    s: Settings = request.app.state.settings
    return {
        "max_bytes": s.upload_max_bytes,
        "max_duration_ms": s.upload_max_duration_ms,
        "containers": ["mp4", "mov"],
        "video_codecs": ["h264", "hevc"],
        "chunk_min_bytes": s.upload_client_chunk_min_bytes,
        "chunk_max_bytes": min(s.upload_client_chunk_max_bytes, s.upload_max_chunk_bytes),
        "checksum_algorithms": ["sha256", "sha1"],
        "expires_after_s": s.upload_expiry_seconds,
    }


@router.options("/uploads", status_code=204)
def discover(request: Request) -> Response:
    settings: Settings = request.app.state.settings
    return Response(
        status_code=204,
        headers={
            **TUS_HEADERS,
            "Tus-Version": TUS_VERSION,
            "Tus-Extension": "creation,checksum,expiration",
            "Tus-Checksum-Algorithm": "sha256,sha1",
            "Tus-Max-Size": str(settings.upload_max_bytes),
        },
    )


@router.post("/matches/{match_id}/uploads", status_code=201)
def create_upload(
    match_id: str, request: Request, account: CurrentAccount, service: Service
) -> Response:
    _require_tus(request)
    upload = service.create(
        owner_id=account.id,
        raw_match_id=match_id,
        upload_length=request.headers.get("upload-length"),
        upload_metadata=request.headers.get("upload-metadata"),
        route=_route(request),
        method=request.method,
    )
    prefix = service.settings.api_public_path_prefix
    return Response(
        status_code=201,
        headers={
            **TUS_HEADERS,
            "Location": f"{prefix}/uploads/{upload.id}",
            **http_date(upload.expires_at),
        },
    )


@router.head("/uploads/{upload_id}")
def head_upload(
    upload_id: str, request: Request, account: CurrentAccount, service: Service
) -> Response:
    _require_tus(request)
    upload = service.load_owned(
        owner_id=account.id, raw_upload_id=upload_id, route=_route(request), method="HEAD"
    )
    return Response(
        status_code=200,
        headers={
            **TUS_HEADERS,
            "Upload-Offset": str(upload.offset),
            "Upload-Length": str(upload.length),
            **http_date(upload.expires_at),
        },
    )


async def _read_exactly(request: Request, length: int) -> bytes:
    chunks: list[bytes] = []
    received = 0
    async for chunk in request.stream():
        received += len(chunk)
        if received > length:
            raise PayloadTooLarge("body longer than Content-Length")
        chunks.append(chunk)
    if received != length:
        raise BadRequest("body shorter than Content-Length")  # dropped connection: store nothing
    return b"".join(chunks)


@router.patch("/uploads/{upload_id}", status_code=204)
async def patch_upload(
    upload_id: str, request: Request, account: CurrentAccount, service: Service
) -> Response:
    _require_tus(request)
    # A snapshot; the read transaction ends here, before the body streams (R1-05).
    upload = await run_in_threadpool(
        lambda: service.patch_target(
            owner_id=account.id, raw_upload_id=upload_id, route=_route(request), method="PATCH"
        )
    )
    if request.headers.get("content-type", "").split(";")[0].strip().lower() != OCTET:
        raise UnsupportedMediaType("PATCH needs application/offset+octet-stream")
    offset = parse_upload_offset(request.headers.get("upload-offset"))
    length = parse_content_length(
        request.headers.get("content-length"), service.settings.upload_max_chunk_bytes
    )
    raw_checksum = request.headers.get("upload-checksum")
    checksum = None if raw_checksum is None else UploadChecksum.parse(raw_checksum)  # 400
    if upload.complete:  # a finished upload takes no more bytes (SEC-R1-02; §6.4 check 7a)
        raise UploadAlreadyComplete("upload is complete")
    if offset != upload.offset:
        raise OffsetMismatch("chunk does not start at the stored offset")
    if offset + length > upload.length:
        raise ChunkBeyondLength("chunk goes past the declared length")

    data = await _read_exactly(request, length)
    written = await run_in_threadpool(service.write_chunk, upload.id, offset, data, checksum)
    return Response(
        status_code=204,
        headers={
            **TUS_HEADERS,
            "Upload-Offset": str(written.offset),
            **http_date(written.expires_at),
        },
    )
