"""Fixture text for the S3-DoD-P10 visibility measurement tests (FIX-03-1c)."""

from __future__ import annotations

import json

PUBLIC = json.dumps({"full_name": "o/r", "private": False, "visibility": "public"})
PRIVATE = json.dumps({"full_name": "o/r", "private": True, "visibility": "private"})


def answer(status: int, body: str) -> str:
    """A recorded GitHub answer: the shape `--from-answer` reads instead of calling GitHub."""
    return json.dumps({"status": status, "body": body})


def po_record(p10: str | None = None) -> str:
    """A PO decision record; with `p10`, a decision-table row answering P10."""
    rows = "| P6-P9 | Relayed to the PO on 2026-10-06; still open. |\n"
    if p10 is not None:
        rows += f"| P10 repository visibility | {p10} |\n"
    return "# PO input\n\n| Item | PO decision |\n|---|---|\n" + rows


def sprint_plan(status: str) -> str:
    """A sprint plan with a section 9.1 table whose S3-DoD-P10 row ends in `status`."""
    return (
        "### 9.1 Sprint-DoD rows\n\n"
        "| DoD row | Item | Finding | Waits on | Owner | Status |\n"
        "|---|---|---|---|---|---|\n"
        "| S3-DoD-P6 | Manual pass | C-06 | P6 | qa | **not met: waiting on P6** |\n"
        f"| S3-DoD-P10 | Repository visibility | SEC-RV3-01 | P10 (PO) | em | {status} |\n"
    )
