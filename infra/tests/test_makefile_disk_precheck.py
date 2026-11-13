"""OPS-DISK-06 (PRC-13.1): every Makefile target that builds images runs
`bash scripts/disk-precheck.sh` first, so a disk under the build floor stops the build before
Docker writes a layer (docs/ops/disk-and-prune.md). Read from `make -n`, as make runs it."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest
from conftest import REPO_ROOT

pytestmark = pytest.mark.unit

PRECHECK = "bash scripts/disk-precheck.sh"
# A line that builds images: `compose ... --build`, `compose ... build`, or `docker build`.
BUILDS = re.compile(r"(compose\b.*(\s--build\b|\sbuild\b))|(docker\s+(buildx\s+)?build\b)")


def dry_run(target: str, tmp_path: Path) -> list[str]:
    # ENV_FILE in a temp dir: the listing must not depend on a developer's infra/.env.
    res = subprocess.run(
        ["make", "-n", "-C", str(REPO_ROOT), target, f"ENV_FILE={tmp_path / '.env'}"],
        capture_output=True,
        text=True,
        timeout=30,
        check=True,
    )
    return res.stdout.splitlines()


def targets() -> list[str]:
    text = (REPO_ROOT / "Makefile").read_text(encoding="utf-8")
    return sorted(set(re.findall(r"^([a-zA-Z0-9_-]+):", text, flags=re.MULTILINE)))


def build_targets(tmp_path: Path) -> list[str]:
    return [t for t in targets() if any(BUILDS.search(line) for line in dry_run(t, tmp_path))]


def test_make_up_is_a_build_target(tmp_path: Path) -> None:
    assert "up" in build_targets(tmp_path)


@pytest.mark.parametrize("line", ["docker build -t x .", "docker compose -f c.yaml build api"])
def test_the_build_pattern_matches_other_build_commands(line: str) -> None:
    assert BUILDS.search(line)


def test_the_build_pattern_ignores_compose_without_build() -> None:
    assert not BUILDS.search("docker compose -f infra/compose.yaml up -d --wait postgres")


def test_every_build_target_runs_the_precheck_before_its_first_build(tmp_path: Path) -> None:
    missing = []
    for target in build_targets(tmp_path):
        lines = dry_run(target, tmp_path)
        first_build = next(i for i, line in enumerate(lines) if BUILDS.search(line))
        if not any(PRECHECK in line for line in lines[:first_build]):
            missing.append(target)
    assert missing == [], f"build targets without '{PRECHECK}' before the build: {missing}"


def test_the_build_floor_defaults_to_16_gb(tmp_path: Path) -> None:
    lines = dry_run("up", tmp_path)
    assert any("RA_MIN_FREE_GB=16" in line and PRECHECK in line for line in lines), lines
