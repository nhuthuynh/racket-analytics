"""MVP-01 integration: the README quick start against the real make and Docker Compose.

Every `make <target>` the "Run it locally" section names is resolved by GNU make itself
(`make -n`, nothing executed), and the Docker Hub mirror tip really changes the images that
`docker compose config` resolves.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys

import pytest
from conftest import REPO_ROOT, SCRIPTS_DIR

sys.path.insert(0, str(SCRIPTS_DIR / "ci"))
import check_readme_quickstart as c

pytestmark = pytest.mark.integration


def _section_targets() -> list[str]:
    return c.make_targets_named(c.quick_start_section((REPO_ROOT / "README.md").read_text()))


def test_the_section_names_the_full_local_journey() -> None:
    assert {"up", "demo", "ps", "logs", "down"} <= set(_section_targets())


def test_every_named_target_is_resolved_by_make() -> None:
    targets = sorted(set(_section_targets()))
    assert targets, "the README names no make target"
    for target in targets:
        res = subprocess.run(
            ["make", "-n", "-C", str(REPO_ROOT), target],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        assert res.returncode == 0, f"make -n {target}: {res.stderr}"


@pytest.mark.skipif(shutil.which("docker") is None, reason="docker CLI not installed")
def test_the_mirror_tip_changes_every_docker_hub_image() -> None:
    env = {**os.environ, "DOCKERHUB_REGISTRY": "mirror.gcr.io"}
    res = subprocess.run(
        [
            "docker",
            "compose",
            "-f",
            "infra/compose.yaml",
            "--env-file",
            "infra/env.example",
            "config",
            "--images",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
        env=env,
    )
    assert res.returncode == 0, res.stderr
    pulled = [i for i in res.stdout.split() if "/" in i and not i.startswith("infra-")]
    assert pulled, res.stdout
    assert [i for i in pulled if not i.startswith("mirror.gcr.io/")] == []
