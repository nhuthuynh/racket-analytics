"""NFR-056: `.gitleaksignore` may only silence exact gitleaks fingerprints of synthetic values
in test files, each with a reason. Nothing broader (no path, no wildcard, no source file), so
the secret scan keeps covering every other commit and file.

CI run 37521787513 (sprint-03 at 78644f3): `generic-api-key` on the SEC-RV3-02 positive
control in `backend/tests/unit/platform/test_settings_sprint03.py:41` (a made-up 32-character
key, commit 9ca52fe). With GITLEAKS_BIN set, the full-history scan runs here too.
"""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

import pytest
from conftest import REPO_ROOT

IGNORE = REPO_ROOT / ".gitleaksignore"
FINGERPRINT = re.compile(
    r"^(?P<commit>[0-9a-f]{40}):(?P<path>[^:]+):(?P<rule>[a-z0-9-]+):(?P<line>\d+)$"
)


def entries() -> list[tuple[str, str]]:
    """(fingerprint, reason) for each entry; the reason is the comment block above it."""
    out, reason = [], ""
    for raw in IGNORE.read_text().splitlines():
        line = raw.strip()
        if not line:
            reason = ""
        elif line.startswith("#"):
            reason += line.lstrip("# ") + " "
        else:
            out.append((line, reason.strip()))
            reason = ""
    return out


# ---------------------------------------------------------------- negative cases first
@pytest.mark.unit
def test_every_entry_is_an_exact_fingerprint_not_a_pattern() -> None:
    for fp, _ in entries():
        assert FINGERPRINT.match(fp), fp
        assert "*" not in fp, fp


@pytest.mark.unit
def test_only_test_files_may_be_ignored() -> None:
    for fp, _ in entries():
        path = FINGERPRINT.match(fp)["path"]  # type: ignore[index]
        assert "/tests/" in f"/{path}", fp
        assert not path.startswith(("backend/src/", "web/src/", "infra/", ".github/")), fp


@pytest.mark.unit
def test_every_entry_says_why() -> None:
    for fp, reason in entries():
        assert len(reason) >= 20, fp


@pytest.mark.unit
def test_every_entry_names_a_commit_in_this_repository() -> None:
    for fp, _ in entries():
        commit = FINGERPRINT.match(fp)["commit"]  # type: ignore[index]
        res = subprocess.run(
            ["git", "-C", str(REPO_ROOT), "cat-file", "-e", f"{commit}^{{commit}}"],
            capture_output=True,
            check=False,
        )
        assert res.returncode == 0, fp


# ---------------------------------------------------------------- positive case
@pytest.mark.unit
def test_the_sec_rv3_02_positive_control_is_the_only_entry() -> None:
    assert [fp for fp, _ in entries()] == [
        "9ca52fecb2b322539facb467855c62c2667594ce:"
        "backend/tests/unit/platform/test_settings_sprint03.py:generic-api-key:41"
    ]


@pytest.mark.integration
@pytest.mark.skipif(not os.environ.get("GITLEAKS_BIN"), reason="set GITLEAKS_BIN to run the scan")
def test_full_history_scan_is_clean() -> None:
    res = subprocess.run(
        [
            str(Path(os.environ["GITLEAKS_BIN"])),
            "git",
            "--config",
            ".gitleaks.toml",
            "--redact",
            "--exit-code",
            "1",
            ".",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
    )
    assert res.returncode == 0, res.stdout + res.stderr
