"""Log scanner for NFR-069 / IT-00-15: no email, nickname or signed URL in logs."""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass

EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
SIGNED_URL = re.compile(
    r"(X-Amz-Signature|X-Amz-Credential|X-Goog-Signature|Signature=|sig=)[^\s\"'&]*", re.IGNORECASE
)


@dataclass(frozen=True)
class Leak:
    line_no: int
    kind: str
    excerpt: str


def scan(lines: Iterable[str], nicknames: Iterable[str] = ()) -> list[Leak]:
    nick_patterns = [
        (n, re.compile(rf"(?<![A-Za-z0-9]){re.escape(n)}(?![A-Za-z0-9])", re.IGNORECASE))
        for n in nicknames
        if n
    ]
    leaks: list[Leak] = []
    for i, line in enumerate(lines, start=1):
        if m := EMAIL.search(line):
            leaks.append(Leak(i, "email", m.group(0)))
        if m := SIGNED_URL.search(line):
            leaks.append(Leak(i, "signed_url", m.group(0)[:40]))
        for nick, pattern in nick_patterns:
            if pattern.search(line):
                leaks.append(Leak(i, "nickname", nick))
    return leaks
