"""Small screen-reader manuals for the S3-DoD-P6 tally tests (FIX-03-1b)."""

from __future__ import annotations

HEAD = "## 3. Script and results\n\n| # | Screen / state | VoiceOver iOS | TalkBack Android |\n|---|---|---|---|\n"
TAIL = "\n## 4. Result\n"


def manual(rows: int, voiceover: int = 0, talkback: int = 0, ids: list[str] | None = None) -> str:
    """A manual of `rows` rows; the first `voiceover` / `talkback` rows have a recorded result."""
    ids = ids or [str(n) for n in range(1, rows + 1)]
    lines = []
    for i, rid in enumerate(ids):
        vo = "pass" if i < voiceover else "not run"
        tb = "fail: label not read (finding QA-X)" if i < talkback else "not run"
        lines.append(f"| {rid} | screen {rid} | {vo} | {tb} |")
    return HEAD + "\n".join(lines) + "\n" + TAIL


def sprint_plan(status: str) -> str:
    return (
        "### 9.1 Sprint-DoD rows\n\n| DoD row | Item | Finding | Waits on | Owner | Status |\n"
        "|---|---|---|---|---|---|\n"
        f"| S3-DoD-P6 | Manual pass | C-06 | P6 | QA | {status} |\n"
    )
