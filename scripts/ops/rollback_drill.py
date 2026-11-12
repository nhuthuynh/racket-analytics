#!/usr/bin/env python3
"""Rollback drill: roll a Compose project back to the previous release (ST-082; REL-1.2; ADR 0058
rule 7).

    rollback_drill.py --project P --to-previous-tag --backup-cmd "<on-demand backup>"
                      [--restore-cmd "<restore>"] [--to TAG --revision REV] [--report out.json]

``--to-previous-tag`` reads ``previous_release`` and ``previous_alembic_revision`` from the
release notes (``--notes``, default ``docs/releases/r1-rc.md``). Order, as rule 7:
0. refuse (exit 2) before any change when an image ``racket-<service>:<tag>`` of the previous or
   the current release is missing, or no backup can be taken;
1. ``backup``: the on-demand backup (``--backup-cmd``, else the project's ``backup`` service in
   the current release image);
2. ``downgrade``: ``alembic downgrade <revision>`` with the current release's ``migrate`` image
   (``racket-migrate:<current>`` through compose.release.yaml, never a per-project build), then
   the revision is read back from ``alembic_version``;
3. ``redeploy``: the previous tag set with ``--no-build --wait`` (compose.release.yaml);
4. ``health``: ``GET /healthz`` inside the ``api`` container is 200;
5. when step 2, 3 or 4 fails: ``restore`` (``--restore-cmd``), then ``redeploy`` and ``health``
   of the **current** release (front matter ``release``, or ``--current``), whose schema the
   restored backup has: an older image never runs on a newer schema. Without ``--restore-cmd``
   the drill stops and names the restore runbook.
Exit 0 rolled back and healthy; 1 a step failed or the fallback ran; 2 refused. The report is
JSON: target, steps (name, rc, seconds) and rc.
"""

from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
import time
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
COMPOSE = ROOT / "infra" / "compose.yaml"
RELEASE = ROOT / "infra" / "compose.release.yaml"
RUNBOOK = "docs/ops/restore-runbook.md (ADR 0058 rule 4)"
DOWNGRADE = (
    "import os, sys\n"
    "from alembic import command\n"
    "from alembic.config import Config\n"
    "from sqlalchemy import create_engine\n"
    "from racket.platform.db import MIGRATIONS_DIR, sqlalchemy_url\n"
    "with create_engine(sqlalchemy_url(os.environ['DATABASE_URL'])).begin() as conn:\n"
    "    config = Config()\n"
    "    config.set_main_option('script_location', str(MIGRATIONS_DIR))\n"
    "    config.attributes['connection'] = conn\n"
    "    command.downgrade(config, sys.argv[1])\n"
)
REVISION = (
    'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "SELECT version_num FROM alembic_version"'
)
HEALTH = (
    "import sys, urllib.request; sys.exit(0 if urllib.request.urlopen("
    "'http://127.0.0.1:8000/healthz', timeout=5).status == 200 else 1)"
)


class Refused(Exception):
    pass


def front_matter(path: Path) -> dict:
    parts = path.read_text().split("---\n", 2)
    data = yaml.safe_load(parts[1]) if len(parts) == 3 else None
    return data if isinstance(data, dict) else {}


def built_services() -> list[str]:
    services = yaml.safe_load(COMPOSE.read_text())["services"]
    return [name for name, svc in services.items() if "build" in svc]


class Drill:
    def __init__(self, project: str, tag: str, revision: str, current: str) -> None:
        self.base = ["docker", "compose", "-p", project, "-f", str(COMPOSE)]
        self.tag, self.revision, self.current = tag, revision, current
        self.steps: list[dict] = []

    def run(
        self, name: str, argv: list[str], env: dict | None = None
    ) -> subprocess.CompletedProcess:
        start = time.monotonic()
        proc = subprocess.run(argv, capture_output=True, text=True, env=env)
        self.steps.append(
            {"name": name, "rc": proc.returncode, "seconds": round(time.monotonic() - start, 3)}
        )
        print(f"{name}: rc {proc.returncode}", flush=True)
        if proc.returncode:
            print((proc.stderr or proc.stdout).strip()[-2000:], file=sys.stderr)
        return proc

    def released(self, tag: str) -> tuple[list[str], dict[str, str]]:
        """The compose argv prefix and environment that run the images of release ``tag``."""
        return [*self.base, "-f", str(RELEASE)], {**os.environ, "IMAGE_TAG": tag}

    def downgrade(self) -> bool:
        base, env = self.released(self.current)
        argv = [
            *base,
            "run",
            "--rm",
            "--no-deps",
            "-T",
            "migrate",
            "python",
            "-c",
            DOWNGRADE,
            self.revision,
        ]
        if self.run("downgrade", argv, env=env).returncode:
            return False
        read = subprocess.run(
            [*self.base, "exec", "-T", "postgres", "sh", "-c", REVISION],
            capture_output=True,
            text=True,
        )
        at = read.stdout.strip()
        if read.returncode or at != self.revision:
            print(
                f"downgrade: database is at {at or '?'}, expected {self.revision}", file=sys.stderr
            )
            self.steps[-1]["rc"] = self.steps[-1]["rc"] or 1
            return False
        return True

    def redeploy(self, tag: str) -> bool:
        base, env = self.released(tag)
        up = [*base, "up", "-d", "--no-build", "--wait"]
        if self.run("redeploy", up, env=env).returncode:
            return False
        probe = [*self.base, "exec", "-T", "api", "python", "-c", HEALTH, "healthz"]
        return self.run("health", probe).returncode == 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--project", required=True)
    target = ap.add_mutually_exclusive_group(required=True)
    target.add_argument("--to-previous-tag", action="store_true")
    target.add_argument("--to", metavar="TAG")
    ap.add_argument("--revision", help="with --to: the previous release's Alembic revision")
    ap.add_argument("--current", metavar="TAG", help="the release to restore to (default: notes)")
    ap.add_argument("--notes", type=Path, default=ROOT / "docs" / "releases" / "r1-rc.md")
    ap.add_argument("--backup-cmd")
    ap.add_argument("--restore-cmd")
    ap.add_argument("--report", type=Path)
    args = ap.parse_args(argv)
    try:
        notes = front_matter(args.notes) if args.notes.is_file() else {}
        if args.to:
            if not args.revision:
                raise Refused("--to needs --revision")
            tag, revision = args.to, args.revision
        else:
            tag, revision = notes.get("previous_release"), notes.get("previous_alembic_revision")
            if not tag or not revision:
                raise Refused(
                    f"{args.notes}: front matter needs previous_release and "
                    "previous_alembic_revision"
                )
        current = args.current or notes.get("release")
        if not current:
            raise Refused(
                "no current release to restore to: pass --current or set release in the notes"
            )
        drill = Drill(args.project, str(tag), str(revision), str(current))
        missing = [
            f"racket-{svc}:{t}"
            for t in (drill.tag, drill.current)
            for svc in built_services()
            if subprocess.run(
                ["docker", "image", "inspect", f"racket-{svc}:{t}"], capture_output=True
            ).returncode
        ]
        if missing:
            raise Refused(
                f"missing images {', '.join(missing)}; build them (docs/releases/r1-rc.md)"
            )
        backup_env = None
        if args.backup_cmd:
            backup = shlex.split(args.backup_cmd)
        elif "backup" in yaml.safe_load(COMPOSE.read_text())["services"]:
            base, backup_env = drill.released(drill.current)
            backup = [*base, "--profile", "ops", "run", "--rm", "backup", "--once"]
        else:
            raise Refused(
                "no backup service in compose.yaml; pass --backup-cmd (ADR 0058 rule 7 step 1)"
            )
    except Refused as exc:
        print(f"rollback_drill: refused: {exc}", file=sys.stderr)
        return 2

    rc = 0
    if drill.run("backup", backup, env=backup_env).returncode:
        rc = 1  # nothing changed yet: no fallback needed, and none to fall back to
    elif not (drill.downgrade() and drill.redeploy(drill.tag)):
        rc = 1
        if not args.restore_cmd:
            print(
                f"rollback_drill: rollback failed; restore the step-1 backup by {RUNBOOK}",
                file=sys.stderr,
            )
        elif drill.run("restore", shlex.split(args.restore_cmd)).returncode == 0:
            drill.redeploy(drill.current)
    report = {
        "project": args.project,
        "to": {"tag": drill.tag, "revision": drill.revision},
        "fallback_tag": drill.current,
        "steps": drill.steps,
        "rc": rc,
    }
    if args.report:
        args.report.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report))
    return rc


if __name__ == "__main__":
    sys.exit(main())
