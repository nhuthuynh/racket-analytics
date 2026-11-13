"""OPS-DISK-06 (PRC-13.1): `scripts/ops/worktree_report.py` names each worktree's branch and
its PR state; merged or closed branches are "remove". Unit level: a stubbed REST fetch and
plain dicts, no git and no network."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest
from conftest import SCRIPTS_DIR

sys.path.insert(0, str(SCRIPTS_DIR / "ops"))
import worktree_report as wr

pytestmark = pytest.mark.unit


def pulls(*items: dict[str, Any]) -> Any:
    calls: list[str] = []

    def fetch(url: str) -> list[dict[str, Any]]:
        calls.append(url)
        return list(items)

    fetch.calls = calls  # type: ignore[attr-defined]
    return fetch


def pr(state: str, merged: bool = False, number: int = 5) -> dict[str, Any]:
    return {
        "number": number,
        "state": state,
        "merged_at": "2026-11-12T00:00:00Z" if merged else None,
    }


def test_a_merged_pr_is_remove() -> None:
    assert wr.pr_state("s06/a", pulls(pr("closed", merged=True)), "o/r", "https://api") == (
        "merged",
        5,
    )
    assert wr.action("merged") == "remove"


def test_a_closed_unmerged_pr_is_remove() -> None:
    assert wr.pr_state("s06/a", pulls(pr("closed")), "o/r", "https://api")[0] == "closed"
    assert wr.action("closed") == "remove"


def test_an_open_pr_is_keep() -> None:
    assert wr.pr_state("s06/a", pulls(pr("open")), "o/r", "https://api")[0] == "open"
    assert wr.action("open") == "keep"


def test_no_pr_is_keep_so_unpushed_work_is_never_removed() -> None:
    assert wr.pr_state("s06/a", pulls(), "o/r", "https://api") == ("no PR", None)
    assert wr.action("no PR") == "keep"


def test_a_detached_head_is_checked_by_hand() -> None:
    assert wr.action("detached") == "check"


def test_an_open_pr_wins_over_an_older_closed_one() -> None:
    fetch = pulls(pr("closed", number=3), pr("open", number=9))
    assert wr.pr_state("s06/a", fetch, "o/r", "https://api") == ("open", 9)


def test_the_query_names_owner_and_branch() -> None:
    fetch = pulls()
    wr.pr_state("s06/a b", fetch, "nhuthuynh/racket-analytics", "https://api")
    assert fetch.calls == [
        "https://api/repos/nhuthuynh/racket-analytics/pulls?head=nhuthuynh%3As06%2Fa%20b&state=all"
    ]


def test_a_directory_that_is_not_a_worktree_is_checked_by_hand(tmp_path: Path) -> None:
    (tmp_path / "plain").mkdir()
    rows = wr.report(tmp_path, pulls(), "o/r", "https://api")
    assert [(r["state"], r["action"]) for r in rows] == [("not a worktree", "check")]
