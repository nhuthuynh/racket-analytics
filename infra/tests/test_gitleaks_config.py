"""NFR-056: the `.gitleaks.toml` allowlist covers named synthetic test values only.

CI run 41970230703 (PR #210, ST-076a, job 127056500694): `generic-api-key` on
`SECRET = "pw-never-logged-076a"` in `infra/tests/test_backup_service_take.py:29` (commit
d9bbf053), the made-up password whose absence from every log line the backup tests assert. The
scan reads the full history of HEAD and pushed history is never rewritten, so the value is
allowlisted by its exact literal, which also holds when the PR's commits reach `main` with new
hashes. Anything else of the same shape is still a finding. With GITLEAKS_BIN set, the scan runs.
"""

from __future__ import annotations

import hashlib
import os
import re
import subprocess
import tomllib
from pathlib import Path

import pytest
from conftest import REPO_ROOT

CONFIG = REPO_ROOT / ".gitleaks.toml"
ST_076A_PASSWORD = "pw-never-logged-076a"
# Not allowlisted; both built at runtime so no scannable value is committed here.
NEAR_MISS = "pw-never-logged-" + "076b"
OTHER_KEY = hashlib.sha256(b"st-076a other key").hexdigest()[:32]


def allowlist_regexes() -> list[str]:
    return list(tomllib.loads(CONFIG.read_text())["allowlist"]["regexes"])


def allowed(value: str) -> bool:
    return any(re.search(rx, value) for rx in allowlist_regexes())


# ---------------------------------------------------------------- negative cases first
@pytest.mark.unit
@pytest.mark.parametrize("value", [NEAR_MISS, OTHER_KEY, f"x{ST_076A_PASSWORD}"])
def test_a_value_that_is_not_the_named_synthetic_one_is_not_allowlisted(value: str) -> None:
    assert not allowed(value), value


@pytest.mark.unit
def test_the_allowlist_keeps_the_default_rules() -> None:
    assert tomllib.loads(CONFIG.read_text())["extend"]["useDefault"] is True


# ---------------------------------------------------------------- positive case
@pytest.mark.unit
def test_the_st_076a_synthetic_password_is_allowlisted() -> None:
    assert allowed(ST_076A_PASSWORD)


def _scan(tmp_path: Path, text: str) -> subprocess.CompletedProcess[str]:
    (tmp_path / ".gitleaks.toml").write_text(CONFIG.read_text())
    (tmp_path / "test_x.py").write_text(text)
    return subprocess.run(
        [os.environ["GITLEAKS_BIN"], "dir", "--config", ".gitleaks.toml", "--redact",
         "--exit-code", "1", "test_x.py"],
        cwd=tmp_path, capture_output=True, text=True, timeout=120, check=False,
    )  # fmt: skip


needs_gitleaks = pytest.mark.skipif(not os.environ.get("GITLEAKS_BIN"), reason="GITLEAKS_BIN")


@pytest.mark.integration
@needs_gitleaks
def test_the_scan_still_flags_a_near_miss_of_the_st_076a_line(tmp_path: Path) -> None:
    res = _scan(tmp_path, f'SECRET = "{NEAR_MISS}"\n')
    assert res.returncode == 1, res.stdout + res.stderr


@pytest.mark.integration
@needs_gitleaks
def test_the_scan_passes_the_st_076a_line(tmp_path: Path) -> None:
    res = _scan(tmp_path, f'SECRET = "{ST_076A_PASSWORD}"\n')
    assert res.returncode == 0, res.stdout + res.stderr
