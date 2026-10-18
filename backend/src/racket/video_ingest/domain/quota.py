"""``StorageQuota``: how many bytes of video one account may keep (ST-072a; FR-160; NFR-023;
api-sprint-04 §7 check 4a). Pure Python.

Used bytes are the account's stored videos plus the declared ``Upload-Length`` of its open
uploads, so an upload is counted once, from creation, and resuming it never counts again.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class QuotaUsage:
    """What a refusal reports: the caller's own numbers only (SEC-4 T4-QT-6)."""

    used_bytes: int
    limit_bytes: int
    requested_bytes: int


@dataclass(frozen=True)
class StorageQuota:
    limit_bytes: int

    def __post_init__(self) -> None:
        if self.limit_bytes < 0:
            raise ValueError("a storage quota is never negative")

    def refusal(
        self, *, stored_bytes: int, reserved_bytes: int, requested_bytes: int
    ) -> QuotaUsage | None:
        """``None`` when the new upload fits, else the usage to report (fail closed on nonsense)."""
        if stored_bytes < 0 or reserved_bytes < 0 or requested_bytes < 1:
            raise ValueError("impossible byte counts")
        used = stored_bytes + reserved_bytes
        if used + requested_bytes <= self.limit_bytes:
            return None
        return QuotaUsage(used, self.limit_bytes, requested_bytes)
