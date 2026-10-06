"""Capture & Media domain (pure; ddd-guidelines §4.5). One module per aggregate or policy."""

from racket.video_ingest.domain.extensions import (
    ChecksumInvalid,
    ChecksumMismatch,
    ExpiryPolicy,
    UploadChecksum,
    UploadExpired,
    UploadFile,
)
from racket.video_ingest.domain.media_facts import InvalidProbeOutput, MediaFacts, NotAVideo
from racket.video_ingest.domain.media_url import MediaUrlPolicy, UnsafeMediaUrl
from racket.video_ingest.domain.policy import Rejection, UploadPolicy
from racket.video_ingest.domain.uploads import (
    ChunkBeyondLength,
    ChunkPlan,
    InvalidUploadLength,
    ObjectKeyPolicy,
    OffsetMismatch,
    Part,
    StagedChunk,
    UploadAlreadyComplete,
    UploadIncomplete,
    UploadSession,
    UploadStatus,
)

__all__ = [
    "ChecksumInvalid",
    "ChecksumMismatch",
    "ChunkBeyondLength",
    "ChunkPlan",
    "ExpiryPolicy",
    "InvalidProbeOutput",
    "InvalidUploadLength",
    "MediaFacts",
    "MediaUrlPolicy",
    "NotAVideo",
    "ObjectKeyPolicy",
    "OffsetMismatch",
    "Part",
    "Rejection",
    "StagedChunk",
    "UnsafeMediaUrl",
    "UploadAlreadyComplete",
    "UploadChecksum",
    "UploadExpired",
    "UploadFile",
    "UploadIncomplete",
    "UploadPolicy",
    "UploadSession",
    "UploadStatus",
]
