"""ST-076a unit tests (review round 1, F1): ``backup.py --once`` takes a set through the real
``age`` with stub ``pg_dumpall``, ``pg_dump`` and ``psql`` first on PATH (NFR-045.1; ADR 0058
rules 1 and 3; SEC-5 T5-BK-1).

Pins what ``take_set``, ``_encrypt_from`` and both branches of ``run_once`` do: the dump reaches
disk only as age ciphertext for the configured recipient, ``backup.json`` is written last with
``status: complete`` and digests equal to ``file_digest`` of each file, and a failing dump or
``age`` gives exit 1, an ERROR ``backup.run`` line, no ``backup.json``, and an unchanged
``--status``. No database: the live dump and restore is ``test_backup_service_dump_live.py``.

ST-076a-part2 adds the third artefact, ``objects.tar.age`` (ADR 0058 rule 1): every run here
mirrors a local fake media bucket (``fake_s3.py``), and a run with no store configured fails
closed (exit 1, no ``backup.json``) instead of writing a set without the objects.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tarfile
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from fake_s3 import FakeS3
from fake_s3 import serve as serve_s3
from test_backup_service import SCRIPT, events, load, plant_set

pytestmark = pytest.mark.unit

AGE_HEADER = b"age-encryption.org/v1\n"
MARKER = b"PLAINTEXT-MARKER-076a"
SECRET = "pw-never-logged-076a"
OBJ_MARKER = b"OBJECT-PLAINTEXT-076a"
OBJECTS = {
    "matches/a/review.mp4": OBJ_MARKER + b" a" * 300,
    "matches/b/clip one.mp4": OBJ_MARKER + b" b",
}
STORE_ENV: dict[str, str] = {}
STUB_PG = f"""#!/bin/sh
echo "$0 $*" >> "$STUB_LOG"
name=$(basename "$0")
if [ "$name" = "$STUB_FAIL" ]; then echo "$name: planted failure" >&2; exit 3; fi
case "$name" in
  psql) case "$*" in
          *alembic_version*) echo 0042_planted ;;
          *server_version*) echo 16.4 ;;
        esac ;;
  *) printf '%s %s\\n' "{MARKER.decode()}" "$name" ;;
esac
"""
# Writes a valid header, then fails: only age's exit code tells the run it went wrong.
FAILING_AGE = """#!/bin/sh
while [ $# -gt 0 ]; do [ "$1" = -o ] && printf 'age-encryption.org/v1\\n' > "$2"; shift; done
cat > /dev/null
echo "age: planted failure" >&2
exit 1
"""


def _exe(path: Path, body: str) -> None:
    path.write_text(body)
    path.chmod(0o755)


@pytest.fixture
def keypair(tmp_path: Path) -> tuple[Path, str]:
    if shutil.which("age-keygen") is None:
        pytest.fail("age and age-keygen must be on PATH (CI installs them)")
    ident = tmp_path / "identity.txt"
    out = subprocess.run(
        ["age-keygen", "-o", str(ident)], capture_output=True, text=True, check=True
    )
    recipient = out.stderr.strip().split()[-1]
    assert recipient.startswith("age1"), out.stderr
    return ident, recipient


@pytest.fixture(autouse=True)
def media_store(monkeypatch: pytest.MonkeyPatch) -> Iterator[FakeS3]:
    with serve_s3(dict(OBJECTS)) as store:
        monkeypatch.setattr(sys.modules[__name__], "STORE_ENV", store.env())
        yield store


@pytest.fixture
def stubs(tmp_path: Path) -> Path:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for name in ("pg_dumpall", "pg_dump", "psql"):
        _exe(bin_dir / name, STUB_PG)
    return bin_dir


def run(
    backups: Path, stubs: Path, recipient: str | None, *args: str, store: bool = True, **extra: str
) -> subprocess.CompletedProcess[str]:
    clean = {k: v for k, v in os.environ.items() if not k.startswith(("BACKUP_", "PG", "S3_"))}
    env = {
        **clean,
        "PATH": f"{stubs}{os.pathsep}{clean.get('PATH', '')}",
        "BACKUP_DIR": str(backups),
        "PGPASSWORD": SECRET,
        "STUB_LOG": str(stubs.parent / "calls.log"),
        "STUB_FAIL": "",
        **({"BACKUP_AGE_RECIPIENT": recipient} if recipient else {}),
        **(STORE_ENV if store else {}),
        **extra,
    }
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )


def run_line(proc: subprocess.CompletedProcess[str]) -> dict:
    lines = [e for e in events(proc.stdout) if e["event"] == "backup.run"]
    assert len(lines) == 1, proc.stdout + proc.stderr
    return lines[0]


def all_bytes(root: Path) -> list[tuple[Path, bytes]]:
    return [(p, p.read_bytes()) for p in sorted(root.rglob("*")) if p.is_file()]


def assert_no_secret(proc: subprocess.CompletedProcess[str], ident: Path) -> None:
    text = proc.stdout + proc.stderr
    assert SECRET not in text
    assert "AGE-SECRET-KEY-" not in text
    assert ident.read_text().split("AGE-SECRET-KEY-")[1].strip() not in text


# ---------------------------------------------------------------- failure first
@pytest.mark.parametrize("failing", ["pg_dump", "pg_dumpall"])
def test_a_failing_dump_exits_1_writes_no_backup_json_and_keeps_the_earlier_set(
    tmp_path: Path, stubs: Path, keypair: tuple[Path, str], failing: str
) -> None:
    ident, recipient = keypair
    backups = tmp_path / "backups"
    earlier = plant_set(backups, datetime.now(UTC) - timedelta(hours=2))
    proc = run(backups, stubs, recipient, "--once", STUB_FAIL=failing)
    assert proc.returncode == 1, proc.stdout + proc.stderr
    line = run_line(proc)
    assert line["level"] == "ERROR"
    assert line["status"] == "failed"
    assert line["error"] == "RuntimeError"
    assert line["last_complete_at"] == json.loads((earlier / "backup.json").read_text())["taken_at"]
    assert [p for p in backups.rglob("backup.json*") if earlier not in p.parents] == []
    for path, data in all_bytes(backups):
        assert MARKER not in data, f"plaintext reached {path}"
    status = run(backups, stubs, recipient, "--status")
    assert status.returncode == 0, status.stdout + status.stderr
    assert json.loads(status.stdout)["newest_complete"] == earlier.name
    assert_no_secret(proc, ident)


def test_a_failing_age_exits_1_and_writes_no_backup_json(
    tmp_path: Path, stubs: Path, keypair: tuple[Path, str]
) -> None:
    ident, recipient = keypair
    _exe(stubs / "age", FAILING_AGE)
    backups = tmp_path / "backups"
    proc = run(backups, stubs, recipient, "--once")
    assert proc.returncode == 1, proc.stdout + proc.stderr
    line = run_line(proc)
    assert (line["level"], line["status"], line["last_complete_at"]) == ("ERROR", "failed", None)
    assert line["error"] == "RuntimeError"
    assert list(backups.rglob("backup.json*")) == []
    for path, data in all_bytes(backups):
        assert MARKER not in data, f"plaintext reached {path}"
    status = run(backups, stubs, recipient, "--status")
    assert status.returncode == 1
    assert json.loads(status.stdout)["state"] == "missing"
    assert_no_secret(proc, ident)


def test_a_run_without_a_media_store_fails_closed_and_writes_no_backup_json(
    tmp_path: Path, stubs: Path, keypair: tuple[Path, str]
) -> None:
    ident, recipient = keypair
    backups = tmp_path / "backups"
    proc = run(backups, stubs, recipient, "--once", store=False)
    assert proc.returncode == 1, proc.stdout + proc.stderr
    line = run_line(proc)
    assert (line["level"], line["status"], line["last_complete_at"]) == ("ERROR", "failed", None)
    assert list(backups.rglob("backup.json*")) == []
    status = run(backups, stubs, recipient, "--status")
    assert (status.returncode, json.loads(status.stdout)["state"]) == (1, "missing")
    assert_no_secret(proc, ident)


# ---------------------------------------------------------------- the happy path
def test_once_writes_only_age_ciphertext_for_the_recipient_and_backup_json_last(
    tmp_path: Path, stubs: Path, keypair: tuple[Path, str], media_store: FakeS3
) -> None:
    ident, recipient = keypair
    backups = tmp_path / "backups"
    proc = run(backups, stubs, recipient, "--once", IMAGE_TAG="t-076a")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    line = run_line(proc)
    assert (line["level"], line["status"]) == ("INFO", "complete")

    [set_dir] = [d for d in backups.iterdir() if d.is_dir()]
    assert sorted(p.name for p in set_dir.iterdir()) == [
        "backup.json",
        "db.dump.age",
        "globals.sql.age",
        "objects.tar.age",
    ]
    assert set_dir.stat().st_mode & 0o777 == 0o700
    for path, data in all_bytes(backups):
        assert MARKER not in data, f"plaintext reached {path}"
        assert OBJ_MARKER not in data, f"object plaintext reached {path}"

    bk = load()
    meta = json.loads((set_dir / "backup.json").read_text())
    assert meta["status"] == "complete"
    assert meta["taken_at"].endswith("Z")
    assert bk.parse_set_name(set_dir.name) == datetime.fromisoformat(meta["taken_at"])
    assert line["last_complete_at"] == meta["taken_at"]
    assert meta["recipient"] == recipient
    assert meta["alembic_revision"] == "0042_planted"
    assert meta["postgres_server_version"] == "16.4"
    assert meta["image_tag"] == "t-076a"
    assert set(meta["artefacts"]) == {"globals.sql.age", "db.dump.age", "objects.tar.age"}
    for name, digest in meta["artefacts"].items():
        assert digest == bk.file_digest(set_dir / name)
    # Written last: every artefact was closed before backup.json was renamed into place.
    newest_artefact = max((set_dir / n).stat().st_mtime_ns for n in meta["artefacts"])
    assert (set_dir / "backup.json").stat().st_mtime_ns >= newest_artefact
    assert line["bytes"] == sum(d["size"] for d in meta["artefacts"].values())

    for name, tool in (("globals.sql.age", "pg_dumpall"), ("db.dump.age", "pg_dump")):
        data = (set_dir / name).read_bytes()
        assert data.startswith(AGE_HEADER)
        assert b"-> X25519 " in data.split(b"\n---", 1)[0]
        plain = subprocess.run(
            ["age", "-d", "-i", str(ident), str(set_dir / name)], capture_output=True, check=True
        ).stdout
        assert plain == MARKER + b" " + tool.encode() + b"\n"

    tar_path = tmp_path / "objects.tar"
    subprocess.run(
        ["age", "-d", "-i", str(ident), "-o", str(tar_path), str(set_dir / "objects.tar.age")],
        check=True,
    )
    with tarfile.open(tar_path) as tar:
        assert tar.getnames() == [f"objects/{k}" for k in sorted(OBJECTS)] + [
            "objects.manifest.json"
        ]
        for key, body in OBJECTS.items():
            member = tar.extractfile(f"objects/{key}")
            assert member is not None
            assert member.read() == body
        manifest = tar.extractfile("objects.manifest.json")
        assert manifest is not None
        raw = manifest.read()
    assert meta["objects"] == {"count": len(OBJECTS), "sha256": hashlib.sha256(raw).hexdigest()}
    assert {method for method, _ in media_store.requests} == {"GET"}
    assert "fake-backup-secret" not in proc.stdout + proc.stderr

    calls = (tmp_path / "calls.log").read_text()
    assert "pg_dumpall --globals-only --no-role-passwords" in calls
    assert "pg_dump -Fc" in calls

    status = run(backups, stubs, recipient, "--status")
    assert status.returncode == 0
    assert json.loads(status.stdout) | {"age_s": 0} == {
        "newest_complete": set_dir.name,
        "taken_at": meta["taken_at"],
        "age_s": 0,
        "state": "fresh",
    }
    assert_no_secret(proc, ident)


def test_the_set_cannot_be_read_without_the_identity(
    tmp_path: Path, stubs: Path, keypair: tuple[Path, str]
) -> None:
    _, recipient = keypair
    other = tmp_path / "other.txt"
    subprocess.run(["age-keygen", "-o", str(other)], capture_output=True, check=True)
    backups = tmp_path / "backups"
    assert run(backups, stubs, recipient, "--once").returncode == 0
    [dump] = backups.rglob("db.dump.age")
    wrong = subprocess.run(["age", "-d", "-i", str(other), str(dump)], capture_output=True)
    assert wrong.returncode != 0
    assert wrong.stdout == b""
