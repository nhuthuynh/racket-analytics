"""tus 1.0.0 core routes (ST-008; ADR 0011; api-sprint-00 §6).

Checks run in the contract's order and the first failure wins: 401 (dependency), 412, 404,
415, 400, 411/413, 409, 413. A PATCH body is read only after every header check passed, and
only up to ``Content-Length`` bytes; a short body stores nothing (atomic PATCH).
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from racket.platform.db import get_session
from racket.platform.errors import (
    BadRequest,
    LengthRequired,
    PayloadTooLarge,
    TusVersionUnsupported,
    UnsupportedMediaType,
)
from racket.platform.settings import Settings
from racket.players.api import CurrentAccount
from racket.video_ingest.domain import ChunkBeyondLength, OffsetMismatch
from racket.video_ingest.service import UploadService

TUS_VERSION = "1.0.0"
OCTET = "application/offset+octet-stream"
TUS_HEADERS = {"Tus-Resumable": TUS_VERSION}

router = APIRouter()


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


@router.options("/uploads", status_code=204)
def discover(request: Request) -> Response:
    settings: Settings = request.app.state.settings
    return Response(
        status_code=204,
        headers={
            **TUS_HEADERS,
            "Tus-Version": TUS_VERSION,
            "Tus-Extension": "creation",
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
        status_code=201, headers={**TUS_HEADERS, "Location": f"{prefix}/uploads/{upload.id}"}
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
    upload = await run_in_threadpool(
        lambda: service.load_owned(
            owner_id=account.id, raw_upload_id=upload_id, route=_route(request), method="PATCH"
        )
    )
    if request.headers.get("content-type", "").split(";")[0].strip().lower() != OCTET:
        raise UnsupportedMediaType("PATCH needs application/offset+octet-stream")
    raw_offset = request.headers.get("upload-offset", "")
    if not raw_offset.isdigit():
        raise BadRequest("Upload-Offset must be a non-negative integer")
    offset = int(raw_offset)
    raw_length = request.headers.get("content-length")
    if raw_length is None or not raw_length.isdigit():
        raise LengthRequired("Content-Length required")
    length = int(raw_length)
    if length > service.settings.upload_max_chunk_bytes:
        raise PayloadTooLarge("chunk above the limit")
    if offset != upload.offset:
        raise OffsetMismatch("chunk does not start at the stored offset")
    if offset + length > upload.length:
        raise ChunkBeyondLength("chunk goes past the declared length")

    data = await _read_exactly(request, length)
    new_offset = await run_in_threadpool(service.write_chunk, upload.id, offset, data)
    return Response(status_code=204, headers={**TUS_HEADERS, "Upload-Offset": str(new_offset)})
