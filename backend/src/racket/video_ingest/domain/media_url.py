"""``MediaUrlPolicy``: short-lived links to a match's video (ST-037; FR-027; NFR-055).

A media URL is a bearer secret: it is presigned by the object store, lives at most 15 minutes,
never carries the session token or the session cookie's name, and is never logged
(NFR-069) [AQS/SEC-05 14.2.1]. Pure (ddd-guidelines §4.5).
"""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlsplit

MAX_TTL_SECONDS = 15 * 60
SESSION_COOKIE_NAMES = ("racket_session",)  # also matches "__Host-racket_session"


class UnsafeMediaUrl(Exception):
    """A URL the policy will not hand out (fail closed: the route answers 500, logs no URL)."""


@dataclass(frozen=True, slots=True)
class MediaUrlPolicy:
    ttl_seconds: int

    def __post_init__(self) -> None:
        ttl = self.ttl_seconds
        if isinstance(ttl, bool) or not isinstance(ttl, int) or not 1 <= ttl <= MAX_TTL_SECONDS:
            raise ValueError(f"media URL TTL must be 1..{MAX_TTL_SECONDS} seconds")

    def check(self, url: str, *, session_token: str | None) -> str:
        parts = urlsplit(url)
        if parts.scheme not in ("http", "https") or not parts.netloc:
            raise UnsafeMediaUrl("not an absolute http(s) URL")
        if session_token and session_token in url:
            raise UnsafeMediaUrl("session token in URL")
        if any(name in url for name in SESSION_COOKIE_NAMES):
            raise UnsafeMediaUrl("session cookie name in URL")
        return url
