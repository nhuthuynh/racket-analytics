"""Binds tests/features/dev_chrome.feature (C3-04; QA-RV3-04; ADR 0036).

The real scripts/dev-chrome.sh, run as a developer runs it, against a stand-in CfT zip served
over file:// and a temporary install dir (never the real /opt/google/chrome).
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from pathlib import Path

import pytest
from pytest_bdd import given, parsers, scenarios, then, when
from test_dev_chrome import make_zip, run, sha

pytestmark = pytest.mark.integration
scenarios("dev_chrome.feature")


@dataclass
class Machine:
    dest: Path
    zip_url: str = ""
    sha256: str = ""
    runs: list[subprocess.CompletedProcess[str]] = field(default_factory=list)


@given("the evidence browser is not installed", target_fixture="machine")
def not_installed(tmp_path: Path) -> Machine:
    dest = tmp_path / "opt" / "google" / "chrome"
    assert not dest.exists()
    return Machine(dest=dest)


@given("the download does not match the pinned sha256")
def wrong_sha(machine: Machine, tmp_path: Path) -> None:
    machine.zip_url = make_zip(tmp_path).as_uri()
    machine.sha256 = "0" * 64


@given("the download matches the pinned sha256")
def right_sha(machine: Machine, tmp_path: Path) -> None:
    z = make_zip(tmp_path)
    machine.zip_url, machine.sha256 = z.as_uri(), sha(z)


@when("the developer installs the evidence browser")
def install(machine: Machine) -> None:
    machine.runs.append(run(machine.dest, machine.zip_url, machine.sha256))


@when("the developer installs the evidence browser again with the download gone")
def install_again(machine: Machine, tmp_path: Path) -> None:
    machine.runs.append(run(machine.dest, (tmp_path / "gone.zip").as_uri(), "0" * 64))


@then(parsers.parse('the install is refused with "{message}"'))
def refused(machine: Machine, message: str) -> None:
    res = machine.runs[-1]
    assert res.returncode != 0
    assert message in res.stderr


@then("no evidence browser is installed")
def nothing_installed(machine: Machine) -> None:
    assert not machine.dest.exists()


@then(parsers.parse('the second install reports "{message}"'))
def second_install(machine: Machine, message: str) -> None:
    first, second = machine.runs
    assert first.returncode == 0, first.stderr
    assert second.returncode == 0, second.stderr
    assert message in second.stderr


@then(parsers.parse('check mode reports "{version}"'))
def check_mode(machine: Machine, version: str) -> None:
    res = run(machine.dest, "file:///unused", "0" * 64, "check")
    assert res.returncode == 0, res.stderr
    assert res.stdout.strip() == version
