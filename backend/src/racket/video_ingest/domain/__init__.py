"""Capture & Media domain (pure; ddd-guidelines §4.5). One module per aggregate or policy."""

from racket.video_ingest.domain.media_facts import InvalidProbeOutput, MediaFacts, NotAVideo
from racket.video_ingest.domain.uploads import (
    ChunkBeyondLength,
    ChunkPlan,
    InvalidUploadLength,
    ObjectKeyPolicy,
    OffsetMismatch,
    Part,
    StagedChunk,
    UploadIncomplete,
    UploadSession,
    UploadStatus,
)

__all__ = [
    "ChunkBeyondLength",
    "ChunkPlan",
    "InvalidProbeOutput",
    "InvalidUploadLength",
    "MediaFacts",
    "NotAVideo",
    "ObjectKeyPolicy",
    "OffsetMismatch",
    "Part",
    "StagedChunk",
    "UploadIncomplete",
    "UploadSession",
    "UploadStatus",
]
