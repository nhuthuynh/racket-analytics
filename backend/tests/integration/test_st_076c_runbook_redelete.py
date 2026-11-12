"""ST-076c review round 2 (F1): restore runbook step 9 works on real log lines and a real database.

Step 9.1's shell block is read from ``docs/ops/restore-runbook.md`` and run with ``jq`` on the
lines the app itself wrote for ``DELETE /matches/{id}`` and ``DELETE /me``: every deleted match
and account must come out, and a deletion line without an id must stop the restore (fail
closed). Step 9.2's Python block is run against the test database: it deletes again a match
and an account that a restore brought back, and a second run changes nothing.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from tests.support import scorebook as sb
from tests.support import stats as st
from tests.support.api import ApiDriver
from tests.support.paths import REPO

RUNBOOK = REPO / "docs/ops/restore-runbook.md"
TAKEN_AT = "2000-01-01T00:00:00Z"

pytestmark = pytest.mark.skipif(shutil.which("jq") is None, reason="jq is not installed")


def _block(after: str, fence: str) -> str:
    """The first fenced block after the line holding ``after``, dedented."""
    text = RUNBOOK.read_text(encoding="utf-8")
    start = text.index(after)
    match = re.search(rf"^( *){fence}\n(.*?)^\1```", text[start:], re.S | re.M)
    assert match, f"no {fence} block after {after!r} in {RUNBOOK}"
    indent = len(match.group(1))
    return "\n".join(line[indent:] for line in match.group(2).splitlines()) + "\n"


def _list_step(tmp_path: Path, lines: list[str]) -> tuple[list[str], list[str], str]:
    (tmp_path / ".local").mkdir(exist_ok=True)
    (tmp_path / ".local/restore-logs.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
    script = re.sub(r"^T=.*$", f"T='{TAKEN_AT}'", _block("List the deletions", "```"), flags=re.M)
    done = subprocess.run(
        ["bash", "-c", script], cwd=tmp_path, capture_output=True, text=True, timeout=60
    )
    assert done.returncode == 0, done.stderr

    def ids(name: str) -> list[str]:
        return (tmp_path / ".local" / name).read_text(encoding="utf-8").split()

    return ids("redelete-accounts.txt"), ids("redelete-matches.txt"), done.stdout + done.stderr


def _deletion_lines(capfd: pytest.CaptureFixture[str]) -> list[str]:
    out, err = capfd.readouterr()
    lines = [line for line in (out + err).splitlines() if line.startswith("{")]
    return [line for line in lines if json.loads(line).get("event", "").endswith(".deleted")]


def _heredoc(shell: str) -> str:
    """The Python the block feeds to ``python -`` (between ``<<'EOF'`` and ``EOF``)."""
    match = re.search(r"<<'EOF'\n(.*?)^EOF$", shell, re.S | re.M)
    assert match, f"no <<'EOF' heredoc in step 9.2 of {RUNBOOK}"
    return match.group(1)


def _redelete(accounts: list[str], matches: list[str]) -> str:
    env = {
        **os.environ,
        "REDELETE_ACCOUNTS": "\n".join(accounts),
        "REDELETE_MATCHES": "\n".join(matches),
    }
    done = subprocess.run(
        [sys.executable, "-"],
        input=_heredoc(_block("Delete those ids again", "```")),
        env=env, capture_output=True, text=True, timeout=120,
    )  # fmt: skip
    assert done.returncode == 0, done.stderr
    return done.stdout


def test_step_9_1_lists_every_id_from_the_apps_own_deletion_lines(
    api: ApiDriver, capfd: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    match_id = api.run(sb.create_doubles(api.as_user("ivy"), "ST-076c redelete"))
    dana = st.me_id(api, "dana")
    capfd.readouterr()
    assert st.delete_match(api, "ivy", match_id).status_code in st.statscontract.DELETE_OK
    assert st.delete_account(api, "dana").status_code in st.statscontract.DELETE_OK
    lines = _deletion_lines(capfd)
    assert {json.loads(line)["event"] for line in lines} == {"match.deleted", "account.deleted"}

    accounts, matches, said = _list_step(tmp_path, [*lines, "not json", "[1]"])

    assert accounts == [dana], said
    assert matches == [match_id], said
    assert "STOP" not in said, said


@pytest.mark.parametrize(
    "bad",
    [
        {"event": "account.deleted", "user_id": None},
        {"event": "match.deleted", "match_id": None, "user_id": None},
        {"event": "account.deleted"},
    ],
)
def test_step_9_1_stops_on_a_deletion_line_without_an_id(
    tmp_path: Path, bad: dict[str, Any]
) -> None:
    line = json.dumps({"ts": "2000-01-01T00:00:01.000Z", "level": "INFO", **bad})
    _, _, said = _list_step(tmp_path, [line])
    assert "STOP" in said, said


def test_step_9_1_stops_when_no_line_is_newer_than_the_backup(tmp_path: Path) -> None:
    old = json.dumps({"ts": "1999-12-31T23:59:59.000Z", "event": "request"})
    _, _, said = _list_step(tmp_path, [old])
    assert "STOP" in said, said


def test_step_9_2_deletes_restored_ids_again_and_is_idempotent(api: ApiDriver) -> None:
    match_id = api.run(sb.create_doubles(api.as_user("ivy"), "ST-076c restored"))
    carlos = st.me_id(api, "carlos")

    first = _redelete([carlos], [match_id])
    again = _redelete([carlos], [match_id])

    assert f"match deleted again {match_id}" in first, first
    assert f"account deleted again {carlos}" in first, first
    assert f"match already deleted or absent {match_id}" in again, again
    assert f"account already deleted or absent {carlos}" in again, again
    assert api.request("ivy", "GET", f"/matches/{match_id}").status_code == 404
