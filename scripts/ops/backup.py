"""Nightly encrypted backup of Postgres (ST-076a; NFR-045.1; ADR 0058).

Usage (run by the Compose ``backup`` service, profile ``ops``, which ST-076a-part2 adds):
    backup.py            run at start, then on fixed-rate slots every BACKUP_INTERVAL_S
    backup.py --once     one on-demand set (exit 0 complete, 1 failed, 2 refused)
    backup.py --status   newest complete set and its age as JSON (exit 0 fresh, 1 stale/missing)

One set is ``<BACKUP_DIR>/<taken_at UTC>/`` with ``globals.sql.age`` and ``db.dump.age``
(streamed through ``age``: no plaintext touches disk) and ``backup.json``, written last. The
media-bucket mirror ``objects.tar.age`` comes with ST-076a-part2. Every run prunes first, then
checks the recipient (none: exit 2, nothing written), then takes the set, then prunes again
(rule 2). Logs one JSON line per event; never a key or a password. Standard library only.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import shutil
import signal
import subprocess
import sys
import time
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

DAY = 86_400
STALE_AFTER_S = DAY  # NFR-045.1: RPO <= 24 h
STALLED_GRACE_S = 3_600
PURGE_LAG_ALERT_S = 2 * DAY  # ADR 0058 rule 5.1
MAX_KEEP_DAYS = 5
SET_FORMAT = "%Y%m%dT%H%M%SZ"
ARTEFACTS = ("globals.sql.age", "db.dump.age")  # objects.tar.age: ST-076a-part2
AGE_HEADER = b"age-encryption.org/v1\n"
RECIPIENT_RE = re.compile(r"^age1[02-9ac-hj-np-z]{58}$")
LOGGER = "racket.ops.backup"
PURGE_LAG_SQL = (
    "SELECT EXTRACT(EPOCH FROM now() - LEAST((SELECT min(deleted_at) FROM matches),"
    " (SELECT min(deleted_at) FROM accounts)))"
)


class Refused(Exception):
    """A setting the service will not run with (exit 2)."""


class NotEncrypted(Exception):
    pass


def log(level: str, event: str, msg: str, **fields: Any) -> None:
    now = datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")
    rec = {"ts": now, "level": level, "logger": LOGGER, "msg": msg, "event": event, **fields}
    print(json.dumps(rec), flush=True)


def utc_text(t: datetime) -> str:
    return t.astimezone(UTC).isoformat().replace("+00:00", "Z")


# ---------------------------------------------------------------- configuration
@dataclass(frozen=True)
class Config:
    backup_dir: Path
    interval_s: int
    keep_days: int
    recipient: str | None
    env: Mapping[str, str] = field(repr=False)


def _whole(env: Mapping[str, str], name: str, default: int, maximum: int) -> int:
    raw = env.get(name, str(default))
    if not raw.isdigit() or not 1 <= int(raw) <= maximum:
        raise Refused(f"{name} must be a whole number from 1 to {maximum}, got {raw!r}")
    return int(raw)


def load_config(env: Mapping[str, str]) -> Config:
    interval = _whole(env, "BACKUP_INTERVAL_S", DAY, DAY)
    keep = _whole(env, "BACKUP_KEEP_DAYS", MAX_KEEP_DAYS, MAX_KEEP_DAYS)
    # A set must outlive the next run and the stalled grace, or the prune deletes the only one.
    if prune_age_s(keep, interval) <= interval + STALLED_GRACE_S:
        raise Refused(f"BACKUP_KEEP_DAYS={keep} prunes the only complete set at this interval")
    return Config(
        backup_dir=Path(env.get("BACKUP_DIR", "/backups")),
        interval_s=interval,
        keep_days=keep,
        recipient=env.get("BACKUP_AGE_RECIPIENT") or None,
        env=env,
    )


def check_recipient(recipient: str | None) -> str:
    if recipient and recipient.upper().startswith("AGE-SECRET-KEY-"):
        raise Refused("BACKUP_AGE_RECIPIENT holds a private identity; give the public recipient")
    if not recipient or not RECIPIENT_RE.match(recipient):
        raise Refused("BACKUP_AGE_RECIPIENT must be an age X25519 recipient (age1...)")
    return recipient


# ---------------------------------------------------------------- sets, age and prune
@dataclass(frozen=True)
class BackupSet:
    path: Path
    taken_at: datetime
    complete: bool


@dataclass
class PruneResult:
    deleted: list[BackupSet]
    overdue: list[BackupSet]
    oldest_set_age_s: float | None


def set_name(t: datetime) -> str:
    return t.astimezone(UTC).strftime(SET_FORMAT)


def parse_set_name(name: str) -> datetime | None:
    try:
        return datetime.strptime(name, SET_FORMAT).replace(tzinfo=UTC)
    except ValueError:
        return None


def age_s(taken_at: datetime, now: datetime) -> float:
    return (now - taken_at).total_seconds()


def freshness(age: float) -> str:
    return "stale" if age > STALE_AFTER_S else "fresh"


def _is_complete(d: Path) -> bool:
    try:
        return bool(json.loads((d / "backup.json").read_text()).get("status") == "complete")
    except (OSError, ValueError, AttributeError):
        return False


def list_sets(root: Path) -> list[BackupSet]:
    out = []
    for d in sorted(root.iterdir()) if root.is_dir() else []:
        t = parse_set_name(d.name)
        if d.is_dir() and t is not None:
            out.append(BackupSet(d, t, _is_complete(d)))
    return out


def last_complete_at(sets: list[BackupSet]) -> datetime | None:
    return max((s.taken_at for s in sets if s.complete), default=None)


def prune_age_s(keep_days: int, interval_s: int) -> int:
    return keep_days * DAY - interval_s


def due_for_prune(s: BackupSet, now: datetime, keep_days: int, interval_s: int) -> bool:
    age = age_s(s.taken_at, now)
    return age >= prune_age_s(keep_days, interval_s) or (not s.complete and age > interval_s)


def remove_set(path: Path) -> None:
    shutil.rmtree(path)


def prune(root: Path, now: datetime, keep_days: int, interval_s: int) -> PruneResult:
    deleted, overdue = [], []
    for s in list_sets(root):
        if due_for_prune(s, now, keep_days, interval_s):
            try:
                remove_set(s.path)
                deleted.append(s)
            except OSError:
                overdue.append(s)
    left = list_sets(root)
    oldest = max((age_s(s.taken_at, now) for s in left), default=None)
    return PruneResult(deleted, overdue, oldest)


def status_report(root: Path, now: datetime) -> dict[str, Any]:
    newest = last_complete_at(list_sets(root))
    if newest is None:
        return {"newest_complete": None, "taken_at": None, "age_s": None, "state": "missing"}
    age = age_s(newest, now)
    return {
        "newest_complete": set_name(newest),
        "taken_at": utc_text(newest),
        "age_s": age,
        "state": freshness(age),
    }


def next_slot(first_start: float, interval_s: int, now: float) -> float:
    return first_start + (math.floor((now - first_start) / interval_s) + 1) * interval_s


def stalled(last_complete: datetime, now: datetime, interval_s: int) -> bool:
    return age_s(last_complete, now) >= interval_s + STALLED_GRACE_S


def purge_lag_exceeded(oldest_tombstone_age_s: float | None) -> bool:
    return oldest_tombstone_age_s is not None and oldest_tombstone_age_s > PURGE_LAG_ALERT_S


# ---------------------------------------------------------------- integrity
def file_digest(path: Path) -> dict[str, Any]:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return {"size": path.stat().st_size, "sha256": h.hexdigest()}


def verify_encrypted(set_dir: Path) -> None:
    for name in ARTEFACTS:
        with (set_dir / name).open("rb") as f:
            head = f.read(len(AGE_HEADER))
        if head != AGE_HEADER:
            raise NotEncrypted(f"{name} is not an age file")


# ---------------------------------------------------------------- one run
def _encrypt_from(cmd: list[str] | None, recipient: str, dest: Path,
                  writer: Any = None) -> Any:  # fmt: skip
    """``cmd | age -r <recipient> -o dest``, or ``writer(age.stdin)``; raises on any failure."""
    age = subprocess.Popen(["age", "-r", recipient, "-o", str(dest)], stdin=subprocess.PIPE)
    if age.stdin is None:  # pragma: no cover - stdin=PIPE always gives one
        raise RuntimeError("age has no stdin")
    result = None
    try:
        if cmd:
            src = subprocess.run(cmd, stdout=age.stdin, check=False)
            if src.returncode:
                raise RuntimeError(f"{cmd[0]} exited {src.returncode}")
        else:
            result = writer(age.stdin)
    except BaseException:
        age.stdin.close()
        age.wait()
        raise
    age.stdin.close()
    if age.wait():
        raise RuntimeError(f"age exited {age.returncode}")
    return result


def _psql(sql: str) -> str | None:
    p = subprocess.run(["psql", "-XAtqc", sql], capture_output=True, text=True, check=False)
    return p.stdout.strip() if p.returncode == 0 else None


def take_set(cfg: Config, recipient: str, now: datetime) -> Path:
    d = cfg.backup_dir / set_name(now)
    d.mkdir(mode=0o700)
    _encrypt_from(
        ["pg_dumpall", "--globals-only", "--no-role-passwords"], recipient, d / ARTEFACTS[0]
    )
    _encrypt_from(["pg_dump", "-Fc"], recipient, d / ARTEFACTS[1])
    verify_encrypted(d)
    for name in ARTEFACTS:
        with (d / name).open("rb") as f:
            os.fsync(f.fileno())
    meta = {
        "schema_version": 1,
        "taken_at": utc_text(now),
        "status": "complete",
        "alembic_revision": _psql("SELECT version_num FROM alembic_version"),
        "image_tag": cfg.env.get("IMAGE_TAG", "dev"),
        "postgres_server_version": _psql("SHOW server_version"),
        "artefacts": {name: file_digest(d / name) for name in ARTEFACTS},
        "corrections": None,  # the ST-076b fingerprint, once racket-integrity ships
        "recipient": recipient,
    }
    tmp = d / "backup.json.tmp"
    with tmp.open("w") as out:
        json.dump(meta, out, indent=2)
        out.flush()
        os.fsync(out.fileno())
    tmp.rename(d / "backup.json")
    return d


def _prune_and_log(cfg: Config, now: datetime) -> None:
    r = prune(cfg.backup_dir, now, cfg.keep_days, cfg.interval_s)
    log("INFO", "backup.retention", "backup retention", deleted=len(r.deleted),
        oldest_set_age_s=r.oldest_set_age_s)  # fmt: skip
    for s in r.overdue:
        log("ERROR", "backup.retention_overdue", "backup set past its prune age is still present",
            set=s.path.name, age_s=age_s(s.taken_at, now))  # fmt: skip


def run_once(cfg: Config, first_start: datetime | None = None) -> int:
    started, clock = datetime.now(UTC).replace(microsecond=0), time.monotonic()
    cfg.backup_dir.mkdir(parents=True, exist_ok=True)
    _prune_and_log(cfg, started)
    status, rc, extra = "complete", 0, {}
    try:
        d = take_set(cfg, check_recipient(cfg.recipient), started)
        extra = {"bytes": sum(file_digest(d / n)["size"] for n in ARTEFACTS)}
    except Refused as e:
        status, rc, extra = "failed", 2, {"error": str(e)}
    except Exception as e:  # noqa: BLE001 - one failed run is logged; the schedule goes on
        status, rc = "failed", 1
        extra = {"error": type(e).__name__, "code": getattr(e, "code", None)}
    _prune_and_log(cfg, datetime.now(UTC))
    last = last_complete_at(list_sets(cfg.backup_dir))
    last_text = utc_text(last) if last else None
    log("INFO" if rc == 0 else "ERROR", "backup.run", f"backup run {status}", status=status,
        duration_ms=int((time.monotonic() - clock) * 1000), last_complete_at=last_text,
        **extra)  # fmt: skip
    # With no complete set yet, the age counts from the service's first start (ADR 0058 rule 2).
    if stalled(last or first_start or started, datetime.now(UTC), cfg.interval_s):
        log("ERROR", "backup.stalled", "no complete backup within one interval and an hour",
            last_complete_at=last_text)  # fmt: skip
    lag = _psql(PURGE_LAG_SQL)
    if lag and purge_lag_exceeded(float(lag)):
        log("ERROR", "backup.purge_lag", "oldest tombstone is older than 2 days", age_s=float(lag))
    return rc


def main(argv: list[str]) -> int:
    try:
        cfg = load_config(os.environ)
    except Refused as e:
        log("ERROR", "backup.refused", str(e))
        return 2
    if argv[1:] == ["--status"]:
        report = status_report(cfg.backup_dir, datetime.now(UTC))
        print(json.dumps(report))
        return 0 if report["state"] == "fresh" else 1
    if argv[1:] == ["--once"]:
        return run_once(cfg)
    if argv[1:]:
        print("usage: backup.py [--once | --status]", file=sys.stderr)
        return 2
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
    first, first_dt = time.time(), datetime.now(UTC)
    while True:
        run_once(cfg, first_dt)
        time.sleep(max(0.0, next_slot(first, cfg.interval_s, time.time()) - time.time()))


if __name__ == "__main__":
    sys.exit(main(sys.argv))
