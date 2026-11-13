#!/usr/bin/env python3
"""Timed restore drill (ST-076c; NFR-045.1-.4; ADR 0058 rules 4 and 6; goal G05-03).

On a Compose project of its own: seed, fingerprint (ST-076b `racket-integrity`) and inventory
the bucket, back up (ST-076a `backup --once`), destroy the volumes, restore by
`docs/ops/restore-runbook.md` (rule 4 steps 1-10, timed), compare, write JSON. Exit 0 every
target met, 1 a target missed or a step failed (`error`), 2 usage. `--check REPORT` re-reads a
verdict. `objects ...` runs inside the API image (boto3), never on the host.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
import uuid
from collections.abc import Callable, Iterable, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[2]
RPO_MAX_HOURS = 24.0  # NFR-045.1
RTO_MAX_MINUTES = 240.0  # NFR-045.2
ARTEFACTS = ("globals.sql.age", "db.dump.age", "objects.tar.age")
PROJECT_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,62}$")
EQUALS = {"alembic_revision": ("equal",), "corrections": ("equal",),
          "objects": ("equal", "manifest_equal")}  # fmt: skip
RUN = ["run", "--rm", "--no-deps", "-T"]
API_PY = ["--entrypoint", "python", "api"]
USER = f"{os.getuid()}:{os.getgid()}" if hasattr(os, "getuid") else "0:0"


class SetRefused(Exception):
    """The backup set must not be restored (rule 3: verify before decrypting)."""


class DrillError(Exception):
    pass


def words(text: str) -> list[str]:
    return text.split()


# ---------------------------------------------------------------- verdict (pure)
def _within(v: Any, low: float, high: float) -> bool:
    return isinstance(v, int | float) and not isinstance(v, bool) and low <= v <= high


def failures(r: dict[str, Any]) -> list[str]:
    """Names of the missed targets; a missing measurement is a miss (fail closed)."""
    out = ["error"] if r.get("error") else []
    if not _within(r.get("rpo_hours"), 0, RPO_MAX_HOURS):
        out.append("rpo")
    if not _within(r.get("rto_minutes"), 1e-9, RTO_MAX_MINUTES):
        out.append("rto")
    if r.get("healthz") != 200:
        out.append("healthz")
    for name, keys in EQUALS.items():
        part = r.get(name)
        if not isinstance(part, dict) or any(part.get(k) is not True for k in keys):
            out.append(name)
    if r.get("dangling_object_refs") != []:
        out.append("dangling_object_refs")
    return out


def rpo_hours(taken_at: str, drill_start: datetime) -> float:
    taken = datetime.fromisoformat(taken_at.replace("Z", "+00:00"))
    return round((drill_start - taken).total_seconds() / 3600, 4)


def object_digest(inventory: Iterable[dict[str, Any]]) -> dict[str, Any]:
    lines = sorted(json.dumps(o, sort_keys=True) for o in inventory)
    h = hashlib.sha256("".join(ln + "\n" for ln in lines).encode())
    return {"count": len(lines), "sha256": h.hexdigest()}


def dangling(refs: Iterable[str], inventory: Iterable[dict[str, Any]]) -> list[str]:
    keys = {o["key"] for o in inventory}
    return sorted(k for k in refs if k not in keys)


def strip_owner_role(sql: str, owner: str) -> str:
    """Rule 4 step 4: the image already made the owner role; its ALTER ROLE line stays."""
    return "\n".join(ln for ln in sql.splitlines() if ln.strip() != f"CREATE ROLE {owner};")


# ---------------------------------------------------------------- the set (rule 3)
def _sha256(path: Path) -> str:
    with path.open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def verify_set(d: Path) -> dict[str, Any]:
    meta: dict[str, Any] = json.loads((d / "backup.json").read_text())
    if meta.get("status") != "complete":
        raise SetRefused(f"{d.name}: status is not complete")
    for name in ARTEFACTS:
        want = (meta.get("artefacts") or {}).get(name, {}).get("sha256")
        if not (d / name).is_file() or _sha256(d / name) != want:
            raise SetRefused(f"{d.name}: {name} is missing or does not match backup.json")
    return meta


def newest_complete(root: Path) -> Path:
    for d in sorted((p for p in root.iterdir() if p.is_dir()), reverse=True):
        try:
            if json.loads((d / "backup.json").read_text()).get("status") == "complete":
                return d
        except (OSError, ValueError):
            continue
    raise SetRefused(f"no complete backup set in {root}")


# ---------------------------------------------------------------- settings
def parse_env(text: str) -> dict[str, str]:
    pairs = (ln.split("=", 1) for ln in text.splitlines() if ln and not ln.startswith("#"))
    return {p[0]: p[1] for p in pairs if len(p) == 2}


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def drill_env(
    example: str, *, flags: str, backups: Path, port: Callable[[], int] = free_port
) -> dict[str, str]:
    env = parse_env(example)
    for k in env:
        if k.endswith("_HOST_PORT"):
            env[k] = str(port())
        elif k.startswith("FEATURE_"):
            env[k] = "true" if flags == "on" else "false"
    env["BACKUP_HOST_DIR"] = str(backups)
    env["DOCKERHUB_REGISTRY"] = os.environ.get("DOCKERHUB_REGISTRY", env["DOCKERHUB_REGISTRY"])
    return env


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="restore_drill.py")
    p.add_argument("--project", help="a Compose project of the drill's own (deleted after)")
    p.add_argument("--flags", choices=("on", "off"), default="on")
    services_help = "all: the default stack (make up); api: the API and what it needs"
    p.add_argument("--services", choices=("all", "api"), default="all", help=services_help)
    plant_help = "delete one correction after the before-state, before the backup"
    p.add_argument("--plant-delete-correction", action="store_true", help=plant_help)
    p.add_argument("--json", type=Path, default=REPO / "reports" / "restore-drill.json")
    p.add_argument("--keep", action="store_true", help="leave the project's stack running")
    p.add_argument("--check", type=Path, help="print the verdict of a recorded report")
    args = p.parse_args(argv)
    if args.check is None and not PROJECT_RE.match(args.project or ""):
        p.error("--project must be a lower-case Compose project name")
    return args


# ---------------------------------------------------------------- the live drill
class Stack:
    def __init__(self, project: str, env: dict[str, str], work: Path) -> None:
        self.project, self.env, self.work = project, env, work
        self.env_file = work / "drill.env"
        self.env_file.write_text("".join(f"{k}={v}\n" for k, v in env.items()))
        self.host_env = {
            k: v
            for k, v in os.environ.items()
            if not k.isupper() or k in {"PATH", "HOME", "DOCKER_HOST", "EXTRA_CA_FILE"}
        }
        self.opts: dict[str, Any] = {"timeout": 3600, "env": self.host_env, "check": False}

    def cmd(self, *args: str) -> list[str]:
        """Profile `ops` only for the backup's own calls and `down`: `up --wait` with it would
        wait on the backup service's 1 h start period."""
        ops = ["--profile", "ops"] if args[0] == "down" or "backup" in args else []
        compose = ["docker", "compose", "-p", self.project, "-f", str(REPO / "infra/compose.yaml")]
        return [*compose, "--env-file", str(self.env_file), *ops, *args]

    def __call__(self, *args: str, stdin: bytes | None = None, ok: Sequence[int] = (0,)) -> str:
        p = subprocess.run(self.cmd(*args), input=stdin, capture_output=True, **self.opts)  # noqa: S603
        if p.returncode not in ok:
            err = p.stderr.decode(errors="replace")[-2000:]
            raise DrillError(f"{' '.join(args[:3])}: exit {p.returncode}: {err}")
        return str(p.stdout.decode())

    def pipe(self, src: Sequence[str], dst: Sequence[str]) -> str:
        with tempfile.TemporaryFile() as src_err:
            a = subprocess.Popen(  # noqa: S603 - docker compose with our own arguments
                self.cmd(*src), stdout=subprocess.PIPE, stderr=src_err, env=self.host_env
            )
            b = subprocess.run(self.cmd(*dst), stdin=a.stdout, capture_output=True, **self.opts)  # noqa: S603
            if a.stdout:
                a.stdout.close()
            a.wait()
            src_err.seek(0)
            err = (src_err.read() + b.stderr).decode(errors="replace")[-2000:]
        if a.returncode or b.returncode:
            raise DrillError(f"{dst[-1]}: exit {a.returncode}/{b.returncode}: {err}")
        return str(b.stdout.decode())

    def sql(self, sql: str, **params: str) -> str:
        psql = words("exec -T postgres psql -XAtq -v ON_ERROR_STOP=1")
        user_db = ["-U", self.env["POSTGRES_USER"], "-d", self.env["POSTGRES_DB"]]
        return self(*psql, *user_db, *(f"-v{k}={v}" for k, v in params.items()), stdin=sql.encode())

    def decrypt(self, artefact: Path) -> list[str]:
        mounts = ["-v", f"{self.work / 'age-identity.txt'}:/run/id.txt:ro"]
        mounts += ["-v", f"{artefact.parent}:/in:ro"]
        run = [*RUN, "-u", USER, *mounts]
        return [*run, *words("--entrypoint age backup -d -i /run/id.txt"), f"/in/{artefact.name}"]

    def in_api(self, *args: str) -> list[str]:
        mount = ["-v", f"{REPO / 'scripts/ops'}:/opt/drill:ro"]
        return [*RUN, *mount, *API_PY, "/opt/drill/restore_drill.py", *args]

    def up(self, services: str) -> None:
        self("up", "-d", "--build", "--wait", *(["api"] if services == "api" else []))

    def db_roles(self) -> None:  # `up api` alone does not run the db-roles one-shot
        self("run", "--rm", "--no-deps", "db-roles")

    def integrity(self, expect: dict[str, Any] | None = None) -> dict[str, Any]:
        more = []
        if expect:
            more = ["--expect-count", str(expect["count"]), "--expect-sha256", expect["sha256"]]
        out = self("exec", "-T", "api", "racket-integrity", *more, ok=(0, 1) if more else (0,))
        return dict(json.loads(out)["corrections"])

    def inventory(self) -> list[dict[str, Any]]:
        return list(json.loads(self(*self.in_api("objects", "inventory"))))


SEED_SQL = """BEGIN;
INSERT INTO accounts (id, created_at) VALUES (:'acc', now());
INSERT INTO matches (id, owner_id, title, format, status, created_at, updated_at)
  VALUES (:'m0', :'acc', 'drill 0', 'doubles', 'scoring', now(), now()),
         (:'m1', :'acc', 'drill 1', 'doubles', 'scoring', now(), now());
INSERT INTO media_assets (id, owner_id, match_id, object_key, size_bytes, probe_status,
  created_at, updated_at) VALUES (gen_random_uuid(), :'acc', :'m0', :'k0', :n0, 'probed', now(),
  now()), (gen_random_uuid(), :'acc', :'m1', :'k1', :n1, 'probed', now(), now());
INSERT INTO match_corrections (id, match_id, version, kind, actor_id, at, field, old_value,
  new_value) SELECT gen_random_uuid(), m, v, 'correction', :'acc', now(), 'winning_side',
  '"A"', '"B"' FROM (VALUES (:'m0'::uuid, 1), (:'m0'::uuid, 2), (:'m1'::uuid, 1)) AS c (m, v);
COMMIT;"""


def seed(st: Stack) -> None:
    """One account, two live matches with a media object each, three confirmed corrections."""
    ids = {k: str(uuid.uuid4()) for k in ("acc", "m0", "m1")}
    for n in (0, 1):
        ids[f"k{n}"], body = f"originals/{uuid.uuid4().hex}", os.urandom(65_536 + n)
        ids[f"n{n}"] = str(len(body))
        st(*st.in_api("objects", "put", ids[f"k{n}"]), stdin=body)
    st.sql(SEED_SQL, **ids)


PLANT_SQL = (  # superuser only: the append-only triggers (migrations 0010, 0011) refuse DELETE
    "SET session_replication_role = replica;"
    " DELETE FROM match_corrections WHERE id = (SELECT min(id::text)::uuid FROM match_corrections);"
)
LIVE_REFS_SQL = (
    "SELECT a.object_key FROM media_assets a JOIN matches m ON m.id = a.match_id"
    " WHERE m.deleted_at IS NULL ORDER BY 1"
)


def healthz(port: str, deadline_s: float = 300) -> int:
    end, status = time.monotonic() + deadline_s, 0
    while time.monotonic() < end:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/healthz", timeout=5) as r:
                status = r.status
        except OSError:
            status = 0
        if status == 200:
            return status
        time.sleep(2)
    return status


def restore(st: Stack, d: Path, args: argparse.Namespace, r: dict[str, Any]) -> None:
    """ADR 0058 rule 4, steps 1-10; RTO runs from step 1 to the end of step 10."""
    r["drill_started_at"] = datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
    t0 = time.monotonic()
    st("down", "-v", "--remove-orphans")  # 1
    st("up", "-d", "--wait", "postgres", "objectstore")  # 2
    st("run", "--rm", "objectstore-init")
    meta = verify_set(d)  # 3
    r["rpo_hours"] = rpo_hours(meta["taken_at"], datetime.fromisoformat(r["drill_started_at"]))
    owner, db = st.env["POSTGRES_USER"], st.env["POSTGRES_DB"]
    globals_sql = st(*st.decrypt(d / ARTEFACTS[0]))  # 4
    st.sql(strip_owner_role(globals_sql, owner))
    pg_restore = words("exec -T postgres pg_restore --exit-on-error --single-transaction")
    st.pipe(st.decrypt(d / ARTEFACTS[1]), [*pg_restore, "-U", owner, "-d", db])  # 5
    got, want = st.sql("SELECT version_num FROM alembic_version").strip(), meta["alembic_revision"]
    r["alembic_revision"] = {"backup": want, "restored": got, "equal": got == want}  # 6
    if not r["alembic_revision"]["equal"]:
        raise DrillError("alembic revision differs from backup.json: follow ADR 0058 rule 7")
    put = json.loads(st.pipe(st.decrypt(d / ARTEFACTS[2]), st.in_api("objects", "restore")))  # 7
    r["objects"]["manifest_equal"] = put["uploaded"] == put["manifest"]
    st.db_roles()  # 8
    st(*RUN, *API_PY, *words("-m racket.platform.purge --once"))  # 9
    st.up(args.services)  # 10
    r["healthz"] = healthz(st.env["API_HOST_PORT"])
    r["corrections"]["after"] = st.integrity(r["corrections"]["before"])
    r["rto_minutes"] = round((time.monotonic() - t0) / 60, 3)


def run_drill(args: argparse.Namespace) -> dict[str, Any]:
    work = REPO / ".local" / "drill" / args.project
    shutil.rmtree(work, ignore_errors=True)
    (work / "backups").mkdir(parents=True)
    env = drill_env(
        (REPO / "infra/env.example").read_text(), flags=args.flags, backups=work / "backups"
    )
    st = Stack(args.project, env, work)
    plant = "delete-correction" if args.plant_delete_correction else None
    r: dict[str, Any] = {"schema_version": 1, "project": args.project, "flags": args.flags}
    r.update(services=args.services, planted=plant)
    try:
        st("down", "-v", "--remove-orphans")
        st("build", "backup")
        keys = st(*RUN, "--entrypoint", "age-keygen", "backup")
        (work / "age-identity.txt").write_text(keys)
        (work / "age-identity.txt").chmod(0o600)
        recipient = re.search(r"^# public key: (age1\w+)$", keys, re.M)
        st.up(args.services)
        st.db_roles()
        seed(st)
        r["corrections"] = {"before": st.integrity()}
        before = st.inventory()
        r["objects"] = {"before": object_digest(before)}
        if plant:
            st.sql(PLANT_SQL)
        recipient_env = f"BACKUP_AGE_RECIPIENT={recipient.group(1) if recipient else ''}"
        st(*RUN, "-u", USER, "-e", recipient_env, "backup", "--once")
        d = newest_complete(work / "backups")
        r["backup_set"], r["taken_at"] = d.name, verify_set(d)["taken_at"]
        restore(st, d, args, r)
        after = st.inventory()
        r["objects"]["after"] = object_digest(after)
        r["objects"]["equal"] = r["objects"]["after"] == r["objects"]["before"]
        r["dangling_object_refs"] = dangling(st.sql(LIVE_REFS_SQL).split(), after)
        r["corrections"]["equal"] = r["corrections"]["after"].pop("equal", False)
    except (DrillError, SetRefused, OSError, ValueError, KeyError, subprocess.SubprocessError) as e:
        r["error"] = f"{type(e).__name__}: {e}"
    finally:
        if not args.keep:
            st("down", "-v", "--remove-orphans", "--rmi", "local", ok=range(256))
            shutil.rmtree(work, ignore_errors=True)
    return r


# ---------------------------------------------------------------- inside the API image
def _hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def objects_main(argv: Sequence[str]) -> int:
    """`objects put KEY` (stdin), `objects inventory`, `objects restore` (an objects.tar on
    stdin, ADR 0058 rule 1). Uses the app's own media-store settings and boto3."""
    import tarfile

    import boto3  # the API image's dependency; never imported on the host

    e = os.environ
    keys = {
        "aws_access_key_id": e["S3_ACCESS_KEY_ID"],
        "aws_secret_access_key": e["S3_SECRET_ACCESS_KEY"],
    }
    s3 = boto3.client("s3", endpoint_url=e["S3_ENDPOINT_URL"], region_name=e["S3_REGION"], **keys)
    bucket = e["S3_BUCKET_MEDIA"]
    if argv[0] == "put":  # the first write can race the store growing its first volume
        body = sys.stdin.buffer.read()
        for attempt in range(30):
            try:
                s3.put_object(Bucket=bucket, Key=argv[1], Body=body)
                return 0
            except Exception:  # retried, then raised (as in IT-05-03)
                if attempt == 29:
                    raise
                time.sleep(1)
    if argv[0] == "inventory":
        out = []
        for page in s3.get_paginator("list_objects_v2").paginate(Bucket=bucket):
            for o in page.get("Contents", []):
                body = s3.get_object(Bucket=bucket, Key=o["Key"])["Body"].read()
                out.append({"key": o["Key"], "size": len(body), "sha256": _hex(body)})
        print(json.dumps(out))
        return 0
    uploaded, manifest = [], []
    with tarfile.open(fileobj=sys.stdin.buffer, mode="r|") as tar:
        for m in tar:
            f = tar.extractfile(m)
            data = f.read() if f else b""
            if m.name == "objects.manifest.json":
                manifest = json.loads(data)["objects"]
            elif m.name.startswith("objects/"):
                s3.put_object(Bucket=bucket, Key=m.name[8:], Body=data)
                uploaded.append({"key": m.name[8:], "size": len(data), "sha256": _hex(data)})
    print(json.dumps({"uploaded": uploaded, "manifest": manifest}))
    return 0


def main(argv: Sequence[str]) -> int:
    if argv[:1] == ["objects"]:
        return objects_main(argv[1:])
    args = parse_args(argv)
    if args.check:
        try:
            r = json.loads(args.check.read_text())
        except (OSError, ValueError) as e:
            print(f"restore_drill: cannot read {args.check}: {e}", file=sys.stderr)
            return 2
    else:
        r = run_drill(args)
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(r, indent=2, sort_keys=True) + "\n")
    missed = failures(r)
    print(json.dumps({"failures": missed, "ok": not missed}, sort_keys=True))
    if missed:
        print(f"restore drill failed: {', '.join(missed)} {r.get('error', '')}", file=sys.stderr)
    return 1 if missed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
