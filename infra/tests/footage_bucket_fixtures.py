"""Fixture text for the S3-DoD-P11 footage bucket measurement tests (FIX-03-1d)."""

from __future__ import annotations

import json


def probe(exists: bool, anonymous_status: int, anonymous_object_status: int | None = None) -> str:
    """A recorded bucket probe: the shape `--from-probe` reads instead of calling a store.

    `anonymous_status` answers an anonymous listing of the bucket root; `anonymous_object_status`
    answers an anonymous GET of a canary object put with credentials (omitted when None)."""
    answer: dict = {"exists": exists, "anonymous_status": anonymous_status}
    if anonymous_object_status is not None:
        answer["anonymous_object_status"] = anonymous_object_status
    return json.dumps(answer)


def po_record(p11: str | None = None) -> str:
    """A PO decision record; with `p11`, a decision-table row answering P11."""
    rows = "| P12 human-gated goal items (BLK-GOLD-01 footage bucket / P11) | Option (b) |\n"
    if p11 is not None:
        rows += f"| P11 footage bucket provider | {p11} |\n"
    return "# PO input\n\n| Item | PO decision |\n|---|---|\n" + rows


def sprint_plan(status: str) -> str:
    """A sprint plan with a section 9.1 table whose S3-DoD-P11 row ends in `status`."""
    return (
        "| DoD row | Item | Finding | Waits on | Owner | Status |\n"
        "|---|---|---|---|---|---|\n"
        "| S3-DoD-P10 | Visibility | SEC-RV3-01 | P10 | em | **not met: waiting on P10** |\n"
        f"| S3-DoD-P11 | Private footage bucket | BLK-GOLD-01 | P11 (provider) | sre | {status} |\n"
    )
