"""Self-cleaning, isolated evidence runs (ADR 0033 rule 3; sprint-02 rows C-05, C-15, C-23).

``scripts/ci/evidence.sh`` is the one door for E2E evidence:

* ``e2e RUN_DIR [playwright args]`` runs Playwright with ``--output RUN_DIR/pw-out`` while
  holding ``flock .local/evidence-e2e.lock`` (C-05, QA-R3-E2E-02: concurrent runs shared
  ``web/test-results`` and produced false reds).

The tests replace Playwright and Docker with a recorder script, so no browser or daemon runs.
"""

from __future__ import annotations

import fcntl
import os
import subprocess
from pathlib import Path

import pytest
from conftest import REPO_ROOT, SCRIPTS_DIR

EVIDENCE = SCRIPTS_DIR / "ci" / "evidence.sh"


def recorder(tmp_path: Path, name: str, rc: int = 0) -> tuple[Path, Path]:
    """A fake command that appends its cwd and argv to a log and exits with ``rc``."""
    log = tmp_path / f"{name}.log"
    script = tmp_path / name
    script.write_text(
        "#!/usr/bin/env bash\n"
        f'printf "%s\\n" "cwd=$PWD" "$@" >> "{log}"\n'
        f'printf "%s\\n" "---" >> "{log}"\n'
        f"exit {rc}\n"
    )
    script.chmod(0o755)
    return script, log


def run(tmp_path: Path, *args: str, **env: str) -> subprocess.CompletedProcess[str]:
    full = {k: v for k, v in os.environ.items() if not k.startswith("RA_")}
    full.setdefault("RA_MIN_FREE_GB", "0")
    full["RA_EVIDENCE_LOCK"] = str(tmp_path / "evidence-e2e.lock")
    full.update(env)
    return subprocess.run(
        ["bash", str(EVIDENCE), *args],
        capture_output=True,
        text=True,
        env=full,
        timeout=60,
        cwd=tmp_path,
    )


# ---------------------------------------------------------------- C-05: negative cases first
@pytest.mark.unit
def test_e2e_refuses_without_a_run_directory(tmp_path: Path) -> None:
    pw, log = recorder(tmp_path, "pw")
    res = run(tmp_path, "e2e", RA_EVIDENCE_PLAYWRIGHT=str(pw))
    assert res.returncode == 2, res
    assert "RUN_DIR" in res.stderr
    assert not log.exists()


@pytest.mark.unit
@pytest.mark.parametrize("flag", [["--output", "elsewhere"], ["--output=elsewhere"]])
def test_e2e_refuses_a_caller_supplied_output_directory(tmp_path: Path, flag: list[str]) -> None:
    # The wrapper owns --output; a second one would silently win and share test-results again.
    pw, log = recorder(tmp_path, "pw")
    res = run(tmp_path, "e2e", str(tmp_path / "run"), *flag, RA_EVIDENCE_PLAYWRIGHT=str(pw))
    assert res.returncode == 2, res
    assert "--output" in res.stderr
    assert not log.exists()


@pytest.mark.unit
def test_e2e_waits_for_the_lock_and_gives_up_after_the_wait_limit(tmp_path: Path) -> None:
    pw, log = recorder(tmp_path, "pw")
    lock = tmp_path / "evidence-e2e.lock"
    with lock.open("w") as held:
        fcntl.flock(held, fcntl.LOCK_EX)
        res = run(
            tmp_path, "e2e", str(tmp_path / "run"),
            RA_EVIDENCE_PLAYWRIGHT=str(pw), RA_EVIDENCE_LOCK_WAIT_S="1",
        )  # fmt: skip
    assert res.returncode == 4, res
    assert "lock" in res.stderr
    assert not log.exists()


@pytest.mark.unit
def test_unknown_subcommand_is_refused(tmp_path: Path) -> None:
    res = run(tmp_path, "deploy")
    assert res.returncode == 2, res
    assert "usage" in res.stderr.lower()


# ---------------------------------------------------------------- C-05: positive
@pytest.mark.unit
def test_e2e_runs_playwright_in_web_with_output_under_the_run_directory(tmp_path: Path) -> None:
    pw, log = recorder(tmp_path, "pw")
    res = run(
        tmp_path, "e2e", "run1", "e2e/sprint-02", "--workers=1", RA_EVIDENCE_PLAYWRIGHT=str(pw)
    )
    assert res.returncode == 0, res
    lines = log.read_text().splitlines()
    assert lines[0] == f"cwd={REPO_ROOT / 'web'}"
    # A relative RUN_DIR is resolved against the caller's directory, not web/.
    out = str(tmp_path / "run1" / "pw-out")
    assert lines[1:5] == ["--output", out, "e2e/sprint-02", "--workers=1"]
    assert (tmp_path / "run1").is_dir()


@pytest.mark.unit
def test_e2e_holds_the_lock_while_playwright_runs(tmp_path: Path) -> None:
    # The fake Playwright tries the lock itself; it must find it taken.
    probe = tmp_path / "probe"
    lock = tmp_path / "evidence-e2e.lock"
    probe.write_text(
        "#!/usr/bin/env bash\n"
        f'if flock -n "{lock}" true; then echo free > "{tmp_path}/state"; '
        f'else echo held > "{tmp_path}/state"; fi\n'
    )
    probe.chmod(0o755)
    res = run(tmp_path, "e2e", str(tmp_path / "run"), RA_EVIDENCE_PLAYWRIGHT=str(probe))
    assert res.returncode == 0, res
    assert (tmp_path / "state").read_text().strip() == "held"


@pytest.mark.unit
def test_e2e_returns_the_playwright_exit_code(tmp_path: Path) -> None:
    pw, _ = recorder(tmp_path, "pw", rc=1)
    res = run(tmp_path, "e2e", str(tmp_path / "run"), RA_EVIDENCE_PLAYWRIGHT=str(pw))
    assert res.returncode == 1, res


@pytest.mark.unit
def test_default_lock_is_the_shared_evidence_lock_under_dot_local() -> None:
    # Every agent and the verifier must contend for the same file (ADR 0033 rule 3).
    text = EVIDENCE.read_text()
    assert "${RA_EVIDENCE_LOCK:-$REPO_ROOT/.local/evidence-e2e.lock}" in text


# ---------------------------------------------------------------- C-23: disk precheck first
@pytest.mark.unit
def test_e2e_refuses_below_the_disk_floor_before_playwright_starts(tmp_path: Path) -> None:
    # PD-R2R-10: live_goal refused below the floor, E2E runs did not.
    pw, log = recorder(tmp_path, "pw")
    res = run(
        tmp_path, "e2e", str(tmp_path / "run"),
        RA_EVIDENCE_PLAYWRIGHT=str(pw), RA_MIN_FREE_GB="1000000",
    )  # fmt: skip
    assert res.returncode == 3, res
    assert "need >= 1000000 GB" in res.stderr
    assert not log.exists()


@pytest.mark.unit
def test_e2e_records_the_df_line_as_evidence(tmp_path: Path) -> None:
    pw, _ = recorder(tmp_path, "pw")
    res = run(tmp_path, "e2e", str(tmp_path / "run"), RA_EVIDENCE_PLAYWRIGHT=str(pw))
    assert res.returncode == 0, res
    assert "Filesystem" in res.stdout
    assert "disk-precheck: ok" in res.stdout


@pytest.mark.unit
def test_e2e_default_floor_is_the_evidence_floor_of_10_gb() -> None:
    text = EVIDENCE.read_text()
    assert 'RA_MIN_FREE_GB="${RA_MIN_FREE_GB:-10}"' in text
