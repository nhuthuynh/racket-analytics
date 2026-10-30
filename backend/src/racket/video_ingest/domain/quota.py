"""``StorageQuota``: bytes of video one account may keep (ST-072a; FR-160; api-sprint-04 §7
check 4a). Pure. Used = stored videos + declared ``Upload-Length`` of open uploads, so an upload
counts once, from creation; resuming it never counts again."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class QuotaUsage:
    """What a refusal reports: the caller's own numbers only (SEC-4 T4-QT-6)."""

    used_bytes: int
    limit_bytes: int
    requested_bytes: int


@dataclass(frozen=True)
class StorageUsage:
    """What ``GET /me/quota`` shows (QA-VERIFY04R3-04; api-sprint-04 §7): the caller's own."""

    used_bytes: int
    limit_bytes: int


@dataclass(frozen=True)
class StorageQuota:
    limit_bytes: int

    def __post_init__(self) -> None:
        if self.limit_bytes < 0:
            raise ValueError("a storage quota is never negative")

    def usage(self, *, stored_bytes: int, reserved_bytes: int) -> StorageUsage:
        """Used as check 4a counts it, so the page and a refusal agree (fail closed on nonsense)."""
        if stored_bytes < 0 or reserved_bytes < 0:
            raise ValueError("impossible byte counts")
        return StorageUsage(stored_bytes + reserved_bytes, self.limit_bytes)

    def refusal(
        self, *, stored_bytes: int, reserved_bytes: int, requested_bytes: int
    ) -> QuotaUsage | None:
        """``None`` when the new upload fits, else the usage to report (fail closed on nonsense)."""
        if requested_bytes < 1:
            raise ValueError("impossible byte counts")
        used = self.usage(stored_bytes=stored_bytes, reserved_bytes=reserved_bytes).used_bytes
        if used + requested_bytes <= self.limit_bytes:
            return None
        return QuotaUsage(used, self.limit_bytes, requested_bytes)
