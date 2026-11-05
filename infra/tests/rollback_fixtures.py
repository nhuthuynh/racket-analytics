"""A recording stand-in for `docker` and a runner for scripts/ops/rollback_drill.py (ST-082;
REL-1.2). The stand-in appends one JSON line per call (argv and IMAGE_TAG) to $FAKE_DOCKER_LOG,
fails a call whose argv contains $FAKE_DOCKER_FAIL, reports `image inspect` of a reference that
contains $FAKE_DOCKER_MISSING as missing, and prints $FAKE_DOCKER_REVISION for the revision
query. Nothing reaches a Docker daemon."""

from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
from pathlib import Path

from conftest import REPO_ROOT

SCRIPT = REPO_ROOT / "scripts" / "ops" / "rollback_drill.py"

FAKE_DOCKER = """#!{python}
import json, os, sys
argv = sys.argv[1:]
with open(os.environ["FAKE_DOCKER_LOG"], "a") as log:
    log.write(json.dumps({{"argv": argv, "image_tag": os.environ.get("IMAGE_TAG")}}) + "\\n")
joined = " ".join(argv)
fail = os.environ.get("FAKE_DOCKER_FAIL")
if fail and fail in joined:
    sys.exit(1)
missing = os.environ.get("FAKE_DOCKER_MISSING")
if argv[:2] == ["image", "inspect"] and missing and missing in joined:
    sys.exit(1)
if "alembic_version" in joined:
    print(os.environ.get("FAKE_DOCKER_REVISION", ""))
sys.exit(0)
"""

NOTES = """---
release: r1-rc1
alembic_revision: "0021"
previous_release: {tag}
previous_ref: 09d279ddb42563bfd014a26d74e84db30c90e237
previous_alembic_revision: "{revision}"
---
# notes
"""


def make_env(tmp_path: Path, tag: str, revision: str) -> dict[str, str]:
    """A bin dir with the stand-in first on PATH, a call log and release notes naming `tag`."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    docker = bin_dir / "docker"
    docker.write_text(FAKE_DOCKER.format(python=sys.executable))
    docker.chmod(docker.stat().st_mode | stat.S_IEXEC)
    (tmp_path / "notes.md").write_text(NOTES.format(tag=tag, revision=revision))
    env = {k: v for k, v in os.environ.items() if k not in {"IMAGE_TAG", "FAKE_DOCKER_FAIL"}}
    env.update(
        PATH=f"{bin_dir}{os.pathsep}{env.get('PATH', '')}",
        FAKE_DOCKER_LOG=str(tmp_path / "docker.log"),
        FAKE_DOCKER_REVISION=revision,
    )
    return env


def marker_cmd(tmp_path: Path, name: str) -> str:
    """A shell command that appends `name` to the call log, standing in for backup or restore."""
    marker = tmp_path / "marker.py"
    marker.write_text(
        "import json, os, sys\n"
        "with open(os.environ['FAKE_DOCKER_LOG'], 'a') as log:\n"
        "    log.write(json.dumps({'step': sys.argv[1]}) + '\\n')\n"
    )
    return f"{sys.executable} {marker} {name}"


def run_drill(
    tmp_path: Path, env: dict[str, str], *args: str
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--notes",
            str(tmp_path / "notes.md"),
            "--report",
            str(tmp_path / "report.json"),
            *args,
        ],
        capture_output=True,
        text=True,
        timeout=60,
        cwd=REPO_ROOT,
        env=env,
    )


def calls(tmp_path: Path) -> list[dict]:
    log = tmp_path / "docker.log"
    if not log.exists():
        return []
    return [json.loads(ln) for ln in log.read_text().splitlines() if ln.strip()]


def report(tmp_path: Path) -> dict:
    return json.loads((tmp_path / "report.json").read_text())
