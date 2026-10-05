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


class MatchOut(BaseModel):
    id: str
    title: str
    format: str
    status: Literal["awaiting_upload", "uploading", "video_received", "probe_failed"]
    scoring_system: str
    rules_version: str
    played_on: str | None
    participants: list[ParticipantOut]
    media: MediaOut | None
    created_at: str
    updated_at: str


class MatchList(BaseModel):
    items: list[MatchOut]
    next_cursor: None = None
