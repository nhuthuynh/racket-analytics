"""Match HTTP schemas: closed requests and allowlisted responses (NFR-052; api-sprint-00 §5)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class ParticipantOut(BaseModel):
    slot: str
    nickname: str
    is_me: bool


class MediaOut(BaseModel):
    duration_ms: int
    fps: float
    width: int
    height: int
    has_audio: bool
    vfr: bool
    container: str
    video_codec: str


class UploadOut(BaseModel):
    """The owner's unfinished upload (api-sprint-01 §5.2; flows D-3)."""

    state: Literal["receiving", "expired"]
    offset: int
    length: int
    expires_at: str | None
    resume_url: str
    file_name: str | None
    file_last_modified_ms: int | None
    head_sha256: str | None


class RejectionOut(BaseModel):
    code: Literal["not_a_video", "too_large", "too_long", "unsupported_video"]
    at: str


class MatchOut(BaseModel):
    id: str
    title: str
    format: str
    status: Literal["awaiting_upload", "uploading", "video_received", "probe_failed"]
    scoring_system: str
    rules_version: str
    played_on: str | None
    participants: list[ParticipantOut]
    upload: UploadOut | None
    rejection: RejectionOut | None
    media: MediaOut | None
    created_at: str
    updated_at: str


class MatchList(BaseModel):
    items: list[MatchOut]
    next_cursor: None = None
