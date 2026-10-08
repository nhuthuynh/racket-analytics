"""C3-04 (QA-RV3-04): scripts/dev-chrome.sh re-provisions the ADR 0036 evidence browser.

Chrome for Testing 141.0.7390.54 at /opt/google/chrome, sha256-checked, idempotent. The tests use
a fake CfT zip served over file:// and a temporary install dir, so they run offline and never
touch the real /opt/google/chrome. Negative cases first.
"""

from __future__ import annotations

import hashlib
import os
import stat
import subprocess
import zipfile
from pathlib import Path

import pytest
from conftest import SCRIPTS_DIR

pytestmark = pytest.mark.unit  # CI selects -m "unit or integration" (PE-R1S3-07)

SCRIPT = SCRIPTS_DIR / "dev-chrome.sh"
VERSION = "141.0.7390.54"
ADR_SHA256 = "5023ec2b8995b74caa5de0e22d5e30f871c3ecce67a6e52d3c9f9dfed423ed01"


def make_zip(tmp: Path, version: str = VERSION) -> Path:
    """A stand-in for chrome-linux64.zip: chrome-linux64/chrome prints the CfT version line."""
    z = tmp / "chrome-linux64.zip"
    with zipfile.ZipFile(z, "w") as zf:
        info = zipfile.ZipInfo("chrome-linux64/chrome")
        info.external_attr = (0o755 | stat.S_IFREG) << 16
        zf.writestr(info, f'#!/bin/sh\necho "Google Chrome for Testing {version} "\n')
        zf.writestr("chrome-linux64/resources.pak", "x")
    return z


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def run(
    install_dir: Path, zip_url: str, sha256: str, *args: str
) -> subprocess.CompletedProcess[str]:
    env = {
        **os.environ,
        "CHROME_DIR": str(install_dir),
        "CHROME_ZIP_URL": zip_url,
        "CHROME_SHA256": sha256,
    }
    return subprocess.run(
        ["bash", str(SCRIPT), *args],
        capture_output=True,
        text=True,
        env=env,
        timeout=120,
        check=False,
    )


def test_checksum_mismatch_refuses_and_installs_nothing(tmp_path: Path) -> None:
    z = make_zip(tmp_path)
    dest = tmp_path / "opt" / "google" / "chrome"
    res = run(dest, z.as_uri(), "0" * 64)
    assert res.returncode != 0
    assert "sha256 mismatch" in res.stderr
    assert not dest.exists()


def test_wrong_version_inside_a_matching_zip_is_refused(tmp_path: Path) -> None:
    z = make_zip(tmp_path, version="140.0.0.0")
    dest = tmp_path / "chrome"
    res = run(dest, z.as_uri(), sha(z))
    assert res.returncode != 0
    assert "version" in res.stderr
    assert not dest.exists()


def test_download_failure_is_a_clear_error(tmp_path: Path) -> None:
    dest = tmp_path / "chrome"
    res = run(dest, (tmp_path / "missing.zip").as_uri(), "0" * 64)
    assert res.returncode != 0
    assert "download failed" in res.stderr
    assert not dest.exists()


def test_installs_the_pinned_build_and_reports_its_version(tmp_path: Path) -> None:
    z = make_zip(tmp_path)
    dest = tmp_path / "opt" / "google" / "chrome"
    res = run(dest, z.as_uri(), sha(z))
    assert res.returncode == 0, res.stderr
    assert os.access(dest / "chrome", os.X_OK)
    assert f"Google Chrome for Testing {VERSION}" in res.stdout
    assert (dest / "resources.pak").exists()


def test_second_run_is_idempotent_and_does_not_download(tmp_path: Path) -> None:
    z = make_zip(tmp_path)
    dest = tmp_path / "chrome"
    assert run(dest, z.as_uri(), sha(z)).returncode == 0
    marker = dest / "resources.pak"
    before = marker.stat().st_mtime_ns
    res = run(dest, (tmp_path / "gone.zip").as_uri(), "0" * 64)
    assert res.returncode == 0, res.stderr
    assert "already installed" in res.stderr
    assert marker.stat().st_mtime_ns == before


def test_an_older_install_is_replaced(tmp_path: Path) -> None:
    dest = tmp_path / "chrome"
    dest.mkdir()
    (dest / "chrome").write_text('#!/bin/sh\necho "Google Chrome for Testing 140.0.0.0 "\n')
    os.chmod(dest / "chrome", 0o700)
    (dest / "stale.pak").write_text("old")
    z = make_zip(tmp_path)
    res = run(dest, z.as_uri(), sha(z))
    assert res.returncode == 0, res.stderr
    out = subprocess.run([str(dest / "chrome"), "--version"], capture_output=True, text=True)
    assert VERSION in out.stdout
    assert not (dest / "stale.pak").exists()


def test_check_mode_fails_closed_when_chrome_is_missing(tmp_path: Path) -> None:
    res = run(tmp_path / "nope", "file:///unused", "0" * 64, "check")
    assert res.returncode != 0
    assert "not installed" in res.stderr


def test_check_mode_refuses_another_installed_version(tmp_path: Path) -> None:
    dest = tmp_path / "chrome"
    dest.mkdir()
    (dest / "chrome").write_text('#!/bin/sh\necho "Google Chrome for Testing 140.0.0.0 "\n')
    os.chmod(dest / "chrome", 0o700)
    res = run(dest, "file:///unused", "0" * 64, "check")
    assert res.returncode != 0
    assert "wrong version" in res.stderr
    assert res.stdout == ""


def test_unknown_mode_is_a_usage_error(tmp_path: Path) -> None:
    res = run(tmp_path / "chrome", "file:///unused", "0" * 64, "upgrade")
    assert res.returncode != 0
    assert "usage" in res.stderr
    assert not (tmp_path / "chrome").exists()


def test_check_mode_reports_the_installed_version(tmp_path: Path) -> None:
    z = make_zip(tmp_path)
    dest = tmp_path / "chrome"
    assert run(dest, z.as_uri(), sha(z)).returncode == 0
    res = run(dest, "file:///unused", "0" * 64, "check")
    assert res.returncode == 0, res.stderr
    assert res.stdout.strip() == f"Google Chrome for Testing {VERSION}"


def test_defaults_are_the_adr_0036_pins() -> None:
    text = SCRIPT.read_text()
    assert ADR_SHA256 in text
    assert f"chrome-for-testing-public/{VERSION}/linux64/chrome-linux64.zip" in text
    assert "/opt/google/chrome" in text


@pytest.mark.skipif(not Path("/opt/google/chrome/chrome").exists(), reason="no local CfT install")
def test_real_install_passes_check_mode() -> None:
    res = subprocess.run(
        ["bash", str(SCRIPT), "check"], capture_output=True, text=True, timeout=60, check=False
    )
    assert res.returncode == 0, res.stderr
    assert VERSION in res.stdout
