"""ST-039 slice 3 (SRE): put the sheet back after the Locust run when the run stopped a
correction mid-flight (CI run 37505286086, PR #2: `restored_byte_identical: false`).

Locust's -t limit kills the correction user while its PATCH is in flight; the server applies it
(version 122 committed 186 ms after "--run-time limit reached"), the client never sees the
answer, so no undo follows and the C-04 check compares a corrected sheet with the baseline.
Every command bumps the version by one and the user only sends correct/undo pairs, so an odd
distance from the seeded version means exactly one unanswered correction to undo.
"""

from __future__ import annotations

import importlib.util

import pytest
from conftest import REPO_ROOT

PERF = REPO_ROOT / "backend" / "tests" / "perf"
SPEC = importlib.util.spec_from_file_location("perf_restore", PERF / "perf_restore.py")
assert SPEC
assert SPEC.loader
restore = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(restore)

pytestmark = pytest.mark.unit


class Server:
    """Versions the server reports, one per read; undo answers the next version."""

    def __init__(self, reads: list[int]) -> None:
        self.reads, self.undone_at = list(reads), []

    def version(self) -> int:
        return self.reads.pop(0) if len(self.reads) > 1 else self.reads[0]

    def undo(self, version: int) -> None:
        self.undone_at.append(version)


def run(server: Server, seed: int) -> int:
    return restore.restore_orphan_correction(
        server.version, server.undo, seed, sleep=lambda _s: None
    )


def test_an_unanswered_correction_is_undone_at_the_server_version() -> None:
    # Seeded at 7; 57 pairs (+114) and one correction the client never saw (+1).
    server = Server([122])
    assert run(server, 7) == 1
    assert server.undone_at == [122]


def test_complete_pairs_are_left_alone() -> None:
    server = Server([121])
    assert run(server, 7) == 0
    assert server.undone_at == []


def test_waits_for_an_in_flight_command_to_commit_before_deciding() -> None:
    # First read is before the PATCH commits (even, looks clean); it then lands at 122.
    server = Server([121, 122, 122])
    assert run(server, 7) == 1
    assert server.undone_at == [122]


def test_a_version_below_the_seed_fails_closed() -> None:
    with pytest.raises(ValueError, match="below the seeded version"):
        run(Server([6]), 7)


def test_the_locustfile_restores_before_the_byte_check() -> None:
    text = (PERF / "locustfile_sprint02.py").read_text(encoding="utf-8")
    assert "restore_orphan_correction(" in text
    assert text.index("restore_orphan_correction(") < text.index('STATE["restored_byte_identical"]')
