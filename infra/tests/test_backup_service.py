"""ST-076a unit tests: the backup service's age, prune, schedule and alert rules (NFR-045.1;
ADR 0058 rules 1-3 and 5, Confirmation list; SEC-5 T5-BK-1..3).

``scripts/ops/backup.py`` is standard-library Python that runs in the backup image. These tests
import it and call its pure functions, run its CLI on throwaway backup directories, and read the
``backup`` Compose service. No database or store: IT-05-03 (``test_backup_service_live.py``) does
that. Red first: a 25 h old set is ``stale``. Negative cases first in each group.
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import ModuleType

import pytest
import yaml
from conftest import REPO_ROOT

pytestmark = pytest.mark.unit

SCRIPT = REPO_ROOT / "scripts" / "ops" / "backup.py"
COMPOSE = REPO_ROOT / "infra" / "compose.yaml"
ENV_EXAMPLE = REPO_ROOT / "infra" / "env.example"
DOCKERFILE = REPO_ROOT / "infra" / "docker" / "backup" / "Dockerfile"
DAY = 86_400
HOUR = 3_600
NOW = datetime(2026, 11, 5, 3, 0, 0, tzinfo=UTC)
# A syntactically valid X25519 recipient (age1 + 58 bech32 characters); no identity exists for it.
RECIPIENT = "age1" + "q" * 58
IDENTITY = "AGE-SECRET-KEY-1" + "Q" * 58


def load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("ops_backup", SCRIPT)
    assert spec, f"missing {SCRIPT}"
    assert spec.loader, f"missing {SCRIPT}"
    mod = importlib.util.module_from_spec(spec)
    sys.modules["ops_backup"] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def bk() -> ModuleType:
    return load()


def plant_set(root: Path, taken_at: datetime, *, complete: bool = True) -> Path:
    """A backup set directory as rule 1 lays it out (artefact contents do not matter here)."""
    taken_at = taken_at.replace(microsecond=0)  # set names and `taken_at` are whole seconds
    d = root / taken_at.strftime("%Y%m%dT%H%M%SZ")
    d.mkdir(parents=True)
    for name in ("globals.sql.age", "db.dump.age", "objects.tar.age"):
        (d / name).write_bytes(b"age-encryption.org/v1\n-> X25519 planted\n")
    meta = {
        "schema_version": 1,
        "taken_at": taken_at.isoformat().replace("+00:00", "Z"),
        "status": "complete" if complete else "running",
    }
    (d / "backup.json").write_text(json.dumps(meta))
    return d


def run_cli(
    *args: str, env: dict[str, str], timeout: float = 60
) -> subprocess.CompletedProcess[str]:
    clean = {k: v for k, v in os.environ.items() if not k.startswith(("BACKUP_", "PG", "S3_"))}
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        env={**clean, **env},
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


def events(stdout: str) -> list[dict]:
    return [json.loads(ln) for ln in stdout.splitlines() if ln.startswith("{")]


# ---------------------------------------------------------------- age (NFR-045.1), red first
def test_a_25_hour_old_set_is_stale(bk: ModuleType) -> None:
    assert bk.freshness(bk.age_s(NOW - timedelta(hours=25), NOW)) == "stale"


def test_a_set_just_over_24_hours_old_is_stale_and_one_at_24_hours_is_fresh(bk: ModuleType) -> None:
    assert bk.freshness(DAY + 1) == "stale"
    assert bk.freshness(DAY) == "fresh"
    assert bk.freshness(23 * HOUR) == "fresh"


def test_age_is_measured_in_utc_whatever_the_offset_of_now(bk: ModuleType) -> None:
    local_now = NOW.astimezone(__import__("datetime").timezone(timedelta(hours=7)))
    assert bk.age_s(NOW - timedelta(hours=2), local_now) == 2 * HOUR


def test_status_reports_missing_when_no_complete_set_exists(bk: ModuleType, tmp_path: Path) -> None:
    plant_set(tmp_path, NOW - timedelta(hours=1), complete=False)
    report = bk.status_report(tmp_path, NOW)
    assert report["state"] == "missing"
    assert report["newest_complete"] is None


def test_status_names_the_newest_complete_set_and_its_age(bk: ModuleType, tmp_path: Path) -> None:
    plant_set(tmp_path, NOW - timedelta(hours=49))
    plant_set(tmp_path, NOW - timedelta(hours=25))
    plant_set(tmp_path, NOW - timedelta(hours=2), complete=False)  # newer, but not usable
    report = bk.status_report(tmp_path, NOW)
    assert report["newest_complete"] == (NOW - timedelta(hours=25)).strftime("%Y%m%dT%H%M%SZ")
    assert report["age_s"] == 25 * HOUR
    assert report["state"] == "stale"
    assert report["taken_at"].endswith("Z")


def test_set_names_are_utc_and_round_trip(bk: ModuleType) -> None:
    name = bk.set_name(NOW)
    assert name == "20261105T030000Z"
    assert bk.parse_set_name(name) == NOW
    assert bk.parse_set_name("20261105T030000") is None
    assert bk.parse_set_name("latest") is None


# ---------------------------------------------------------------- configuration (exit 2)
@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("BACKUP_KEEP_DAYS", "6"),
        ("BACKUP_KEEP_DAYS", "0"),
        ("BACKUP_KEEP_DAYS", "five"),
        ("BACKUP_INTERVAL_S", "86401"),
        ("BACKUP_INTERVAL_S", "0"),
        ("BACKUP_INTERVAL_S", "-1"),
    ],
)
def test_out_of_range_settings_are_refused(
    bk: ModuleType, tmp_path: Path, name: str, value: str
) -> None:
    env = {"BACKUP_DIR": str(tmp_path), "BACKUP_AGE_RECIPIENT": RECIPIENT, name: value}
    with pytest.raises(bk.Refused, match=name):
        bk.load_config(env)
    proc = run_cli("--once", env=env)
    assert proc.returncode == 2, proc.stdout + proc.stderr
    assert name in proc.stdout + proc.stderr
    assert list(tmp_path.iterdir()) == []


def test_defaults_are_daily_and_five_days(bk: ModuleType, tmp_path: Path) -> None:
    cfg = bk.load_config({"BACKUP_DIR": str(tmp_path)})
    assert cfg.interval_s == DAY
    assert cfg.keep_days == 5
    assert cfg.recipient is None


def test_a_private_identity_is_never_accepted_as_the_recipient(
    bk: ModuleType, tmp_path: Path
) -> None:
    """T5-BK-2: the backup host holds the public recipient only."""
    with pytest.raises(bk.Refused, match="private identity"):
        bk.check_recipient(IDENTITY)
    with pytest.raises(bk.Refused, match="BACKUP_AGE_RECIPIENT"):
        bk.check_recipient("not-a-key")
    with pytest.raises(bk.Refused, match="BACKUP_AGE_RECIPIENT"):
        bk.check_recipient(None)
    assert bk.check_recipient(RECIPIENT) == RECIPIENT


def test_no_recipient_exits_2_writes_nothing_and_still_prunes(tmp_path: Path) -> None:
    """ADR 0058 rule 3 (fail closed) and rule 2 (prune first)."""
    old = plant_set(tmp_path, datetime.now(UTC) - timedelta(days=4, seconds=1))
    kept = plant_set(tmp_path, datetime.now(UTC) - timedelta(days=1))
    proc = run_cli("--once", env={"BACKUP_DIR": str(tmp_path)})
    assert proc.returncode == 2, proc.stdout + proc.stderr
    assert not old.exists(), "the prune runs before the recipient check"
    assert sorted(p.name for p in tmp_path.iterdir()) == [kept.name], "no new set is written"
    run = [e for e in events(proc.stdout) if e["event"] == "backup.run"]
    assert run
    assert run[-1]["status"] == "failed"
    assert run[-1]["level"] == "ERROR"
    assert run[-1]["last_complete_at"] == json.loads((kept / "backup.json").read_text())["taken_at"]
    assert "BACKUP_AGE_RECIPIENT" in proc.stdout + proc.stderr


# ---------------------------------------------------------------- prune (ADR 0058 rule 2)
def test_prune_age_subtracts_one_interval(bk: ModuleType) -> None:
    assert bk.prune_age_s(5, DAY) == 4 * DAY
    assert bk.prune_age_s(5, HOUR) == 5 * DAY - HOUR


@pytest.mark.parametrize(
    ("interval", "age", "deleted"),
    [
        (DAY, 4 * DAY - 1, False),
        (DAY, 4 * DAY, True),
        (HOUR, 5 * DAY - HOUR - 1, False),
        (HOUR, 5 * DAY - HOUR, True),
    ],
)
def test_prune_boundary(bk: ModuleType, interval: int, age: int, deleted: bool) -> None:
    s = bk.BackupSet(Path("x"), NOW - timedelta(seconds=age), complete=True)
    assert bk.due_for_prune(s, NOW, keep_days=5, interval_s=interval) is deleted


def test_an_incomplete_set_older_than_one_interval_is_pruned(bk: ModuleType) -> None:
    young = bk.BackupSet(Path("a"), NOW - timedelta(seconds=DAY - 1), complete=False)
    old = bk.BackupSet(Path("b"), NOW - timedelta(seconds=DAY + 1), complete=False)
    assert bk.due_for_prune(young, NOW, keep_days=5, interval_s=DAY) is False
    assert bk.due_for_prune(old, NOW, keep_days=5, interval_s=DAY) is True


@pytest.mark.parametrize("interval", [DAY, HOUR])
def test_no_set_is_ever_seen_five_days_old_over_ten_days_of_fixed_rate_runs(
    bk: ModuleType, interval: int
) -> None:
    """Negative case of evidence E9: scheduled sets and on-demand sets at every 600 s offset.

    A set survives a prune until the next run, at most one interval later, so the oldest age
    any set reaches is its age just before the next prune.
    """
    first = NOW
    runs = [first + timedelta(seconds=k * interval) for k in range(10 * DAY // interval + 1)]
    on_demand = [first + timedelta(seconds=o) for o in range(0, 10 * DAY, 600)]
    sets: list = []
    worst = 0.0
    pending = sorted(on_demand)
    for i, run in enumerate(runs):
        while pending and pending[0] <= run:  # an on-demand set prunes too, then is written
            t = pending.pop(0)
            sets = [s for s in sets if not bk.due_for_prune(s, t, keep_days=5, interval_s=interval)]
            sets.append(bk.BackupSet(Path(str(t)), t, complete=True))
        sets = [s for s in sets if not bk.due_for_prune(s, run, keep_days=5, interval_s=interval)]
        sets.append(bk.BackupSet(Path(str(run)), run, complete=True))
        nxt = runs[i + 1] if i + 1 < len(runs) else run + timedelta(seconds=interval)
        worst = max([worst, *(bk.age_s(s.taken_at, nxt - timedelta(seconds=1)) for s in sets)])
    assert worst < 5 * DAY, f"a set lived {worst / DAY:.4f} days"


def test_prune_deletes_due_sets_on_disk_and_reports_the_oldest_age(
    bk: ModuleType, tmp_path: Path
) -> None:
    gone = plant_set(tmp_path, NOW - timedelta(days=4))
    stays = plant_set(tmp_path, NOW - timedelta(days=3))
    stale_partial = plant_set(tmp_path, NOW - timedelta(days=1, seconds=1), complete=False)
    result = bk.prune(tmp_path, NOW, keep_days=5, interval_s=DAY)
    assert not gone.exists()
    assert not stale_partial.exists()
    assert stays.exists()
    assert result.oldest_set_age_s == 3 * DAY
    assert result.overdue == []


def test_a_set_the_prune_could_not_delete_is_retention_overdue(
    bk: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    stuck = plant_set(tmp_path, NOW - timedelta(days=4, hours=1))

    def refuse(path: Path) -> None:
        raise PermissionError(f"planted: cannot delete {path}")

    monkeypatch.setattr(bk, "remove_set", refuse)
    result = bk.prune(tmp_path, NOW, keep_days=5, interval_s=DAY)
    assert stuck.exists()
    assert [s.path for s in result.overdue] == [stuck]
    assert result.oldest_set_age_s == 4 * DAY + HOUR


# ---------------------------------------------------------------- schedule and alerts
def test_fixed_rate_slots_never_drift(bk: ModuleType) -> None:
    first = 1_000_000.0
    assert bk.next_slot(first, DAY, first) == first + DAY
    assert bk.next_slot(first, DAY, first + 10) == first + DAY
    # A run that overran its slot skips to the next slot; it never pushes later runs back.
    assert bk.next_slot(first, DAY, first + DAY + 5) == first + 2 * DAY
    assert bk.next_slot(first, HOUR, first + 3 * HOUR) == first + 4 * HOUR


def test_stalled_fires_one_hour_after_a_missed_interval(bk: ModuleType) -> None:
    last = NOW
    assert bk.stalled(last, last + timedelta(seconds=DAY + HOUR - 1), DAY) is False
    assert bk.stalled(last, last + timedelta(seconds=DAY + HOUR), DAY) is True


def test_failing_nightly_runs_keep_the_last_complete_set_until_stalled_fires(
    bk: ModuleType, tmp_path: Path
) -> None:
    """Review round 2, F5 (evidence E10): complete sets on days 0-2, every run fails after."""
    for d in (0, 1, 2):
        plant_set(tmp_path, NOW + timedelta(days=d))
    day2 = NOW + timedelta(days=2)
    fire = day2 + timedelta(seconds=DAY + HOUR)
    # Each failing scheduled run (days 3, 4, ...) still prunes first, up to the alert time.
    for run in (NOW + timedelta(days=3), fire):
        bk.prune(tmp_path, run, keep_days=5, interval_s=DAY)
    sets = bk.list_sets(tmp_path)
    assert bk.last_complete_at(sets) == day2
    assert bk.stalled(day2, fire - timedelta(seconds=1), DAY) is False
    assert bk.stalled(day2, fire, DAY) is True
    assert any(s.taken_at == day2 and s.path.exists() for s in sets), "day-2 set still present"


def test_purge_lag_alerts_above_two_days(bk: ModuleType) -> None:
    assert bk.purge_lag_exceeded(None) is False
    assert bk.purge_lag_exceeded(2 * DAY) is False
    assert bk.purge_lag_exceeded(2 * DAY + 1) is True


# ---------------------------------------------------------------- encryption (T5-BK-1)
def test_a_planted_plaintext_dump_fails_the_encryption_check(
    bk: ModuleType, tmp_path: Path
) -> None:
    d = plant_set(tmp_path, NOW)
    (d / "db.dump.age").write_bytes(b"PGDMP\x01\x0f\x00plaintext")
    with pytest.raises(bk.NotEncrypted, match=r"db\.dump\.age"):
        bk.verify_encrypted(d)


def test_an_artefact_without_the_age_header_fails_the_encryption_check(
    bk: ModuleType, tmp_path: Path
) -> None:
    d = plant_set(tmp_path, NOW)
    (d / "objects.tar.age").write_bytes(b"objects.manifest.json\x00" * 4)
    with pytest.raises(bk.NotEncrypted, match=r"objects\.tar\.age"):
        bk.verify_encrypted(d)


def test_age_encrypted_artefacts_pass_the_encryption_check(bk: ModuleType, tmp_path: Path) -> None:
    bk.verify_encrypted(plant_set(tmp_path, NOW))


def test_sha256_of_a_file(bk: ModuleType, tmp_path: Path) -> None:
    f = tmp_path / "f"
    f.write_bytes(b"abc")
    assert bk.file_digest(f) == {
        "size": 3,
        "sha256": "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad",
    }


# ---------------------------------------------------------------- object-store request signing
def test_sigv4_matches_the_aws_documented_example(bk: ModuleType) -> None:
    """The GET Object example of the AWS SigV4 documentation (judgment: fixed test vector)."""
    headers = bk.sign_v4(
        "GET",
        "https://examplebucket.s3.amazonaws.com/test.txt",
        access_key="AKIAIOSFODNN7EXAMPLE",
        secret_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
        region="us-east-1",
        now=datetime(2013, 5, 24, tzinfo=UTC),
        extra={"range": "bytes=0-9"},
    )
    assert headers["Authorization"].endswith(
        "Signature=f0e8bdb87c964420e857bd35b5d6ed310bd44f0170aba48dd91039c6036bdb41"
    )
    assert "SignedHeaders=host;range;x-amz-content-sha256;x-amz-date" in headers["Authorization"]


# ---------------------------------------------------------------- Compose service (ops profile)
def services() -> dict:
    return yaml.safe_load(COMPOSE.read_text())["services"]


def backup() -> dict:
    svc = services().get("backup")
    assert svc is not None, "no `backup` service in infra/compose.yaml (ADR 0058 rule 2)"
    return svc


def test_backup_holds_no_app_or_admin_credentials() -> None:
    """ADR 0058 rule 2, T5-BK-3: its own read-only login and store key, never the app's."""
    env = backup()["environment"]
    text = json.dumps(env)
    for forbidden in (
        "POSTGRES_PASSWORD",
        "${S3_SECRET_ACCESS_KEY",
        "WORKER_",
        "${S3_ACCESS_KEY_ID",
    ):
        assert forbidden not in text, forbidden
    assert env["PGUSER"].startswith("${BACKUP_DB_USER:?")
    assert env["PGPASSWORD"].startswith("${BACKUP_DB_PASSWORD:?")
    assert env["BACKUP_S3_ACCESS_KEY_ID"].startswith("${BACKUP_S3_ACCESS_KEY_ID:?")


def test_backup_holds_no_private_identity_and_does_not_require_a_recipient() -> None:
    """T5-BK-2 and ADR 0058 rule 3: no identity in env or mounts; no `:?` on the recipient,
    so `make up` keeps working for everyone without one."""
    svc = backup()
    assert "IDENTITY" not in json.dumps(svc).upper()
    assert svc["environment"]["BACKUP_AGE_RECIPIENT"] == "${BACKUP_AGE_RECIPIENT:-}"
    assert "AGE-SECRET-KEY" not in COMPOSE.read_text() + ENV_EXAMPLE.read_text()
    assert "AGE-SECRET-KEY" not in DOCKERFILE.read_text()


def test_backup_is_in_the_ops_profile_only_and_hardened() -> None:
    svc = backup()
    assert svc["profiles"] == ["ops"]
    assert svc["read_only"] is True
    assert svc["cap_drop"] == ["ALL"]
    assert "no-new-privileges:true" in svc["security_opt"]
    assert svc["networks"] == ["edge"]
    assert not svc.get("ports")
    assert svc["restart"] == "unless-stopped"
    assert svc["stop_signal"] == "SIGTERM"
    for other, s in services().items():
        if other != "backup":
            assert "ops" not in s.get("profiles", []), other


def test_backups_live_outside_the_compose_volumes() -> None:
    """ADR 0058 rule 2: `make down` (down -v) must not delete the sets it is about to restore."""
    svc = backup()
    assert svc["environment"]["BACKUP_DIR"] == "/backups"
    mounts = [v for v in svc["volumes"] if v.endswith(":/backups")]
    assert mounts == ["${BACKUP_HOST_DIR:-../.local/backups}:/backups"]
    assert "backups" not in yaml.safe_load(COMPOSE.read_text()).get("volumes", {})


def test_backup_builds_its_image_and_runs_the_script() -> None:
    svc = backup()
    assert svc["build"]["dockerfile"] == "infra/docker/backup/Dockerfile"
    text = DOCKERFILE.read_text()
    assert "postgres:16-alpine" in text, "pg_dump must match the Postgres 16 server"
    assert "COPY scripts/ops/backup.py /opt/racket/backup.py" in text
    assert 'ENTRYPOINT ["python3", "/opt/racket/backup.py"]' in text
    assert "--checksum=sha256:" in text, "the age release is pinned by checksum"


def test_backup_rules_render_with_the_example_env() -> None:
    env = backup()["environment"]
    assert env["BACKUP_INTERVAL_S"] == "${BACKUP_INTERVAL_S:-86400}"
    assert env["BACKUP_KEEP_DAYS"] == "${BACKUP_KEEP_DAYS:-5}"
    example = dict(
        ln.split("=", 1)
        for ln in ENV_EXAMPLE.read_text().splitlines()
        if ln and not ln.startswith("#")
    )
    for name in (
        "BACKUP_DB_USER",
        "BACKUP_DB_PASSWORD",
        "BACKUP_S3_ACCESS_KEY_ID",
        "BACKUP_S3_SECRET_ACCESS_KEY",
    ):
        assert example.get(name, "").strip(), name
    assert example.get("BACKUP_AGE_RECIPIENT") == "", "env.example ships no recipient"


def test_the_store_gives_the_backup_identity_the_media_bucket_only() -> None:
    """Read and List are what it uses; SeaweedFS 3.97 also needs Write on the bucket to accept
    any SigV4 request (auth_signature_v4.go). No Admin, no unscoped action, no other bucket."""
    cmd = "\n".join(services()["objectstore"]["command"])
    assert '{"name":"racket-backup"' in cmd
    ident = cmd.split('{"name":"racket-backup"', 1)[1].split("]}", 1)[0]
    assert ident.endswith('"actions":["Read:%s","List:%s","Write:%s"')
    assert "Admin" not in ident
    assert "Tagging" not in ident


class FakeStore:
    """Records every request the mirror sends; two listing pages, then the bodies."""

    def __init__(self, objects: dict[str, bytes]) -> None:
        self.objects, self.methods, self.urls = objects, [], []

    def __call__(self, req: object, timeout: float) -> object:
        import io
        from urllib.parse import parse_qs, unquote, urlsplit

        self.methods.append(req.get_method())  # type: ignore[attr-defined]
        self.urls.append(req.full_url)  # type: ignore[attr-defined]
        assert "Authorization" in req.headers  # type: ignore[attr-defined]
        u = urlsplit(req.full_url)  # type: ignore[attr-defined]
        q = parse_qs(u.query)
        keys = sorted(self.objects)
        if q.get("list-type") == ["2"]:
            page = keys[1:] if q.get("continuation-token") else keys[:1]
            more = (
                ""
                if q.get("continuation-token")
                else "<NextContinuationToken>t2</NextContinuationToken>"
            )
            body = (
                '<ListBucketResult xmlns="http://s3.amazonaws.com/doc/2006-03-01/">'
                + "".join(
                    f"<Contents><Key>{k}</Key><Size>{len(self.objects[k])}</Size></Contents>"
                    for k in page
                )
                + f"<IsTruncated>{'false' if q.get('continuation-token') else 'true'}"
                + f"</IsTruncated>{more}"
                + "</ListBucketResult>"
            ).encode()
        else:
            body = self.objects[unquote(u.path.split("/", 2)[2])]
        return io.BytesIO(body)  # a context manager, like the real response


def test_the_mirror_only_reads_and_follows_every_listing_page(
    bk: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    import hashlib
    import io
    import tarfile

    objects = {"matches/a/review.mp4": b"a" * 700, "matches/b/clip one.mp4": b"b" * 3}
    fake = FakeStore(objects)
    monkeypatch.setattr(bk.urllib.request, "urlopen", fake)
    env = {
        "S3_ENDPOINT_URL": "http://objectstore:8333",
        "S3_BUCKET_MEDIA": "racket-media",
        "BACKUP_S3_ACCESS_KEY_ID": "k",
        "BACKUP_S3_SECRET_ACCESS_KEY": "s",
    }
    store = bk.Store(env)
    out = io.BytesIO()
    summary = bk.mirror_objects(store, out)
    assert set(fake.methods) == {"GET"}, "the backup never writes or deletes in the store"
    assert all(u.startswith("http://objectstore:8333/racket-media") for u in fake.urls)
    out.seek(0)
    with tarfile.open(fileobj=out, mode="r:") as tar:
        assert tar.getnames() == [f"objects/{k}" for k in sorted(objects)] + [
            "objects.manifest.json"
        ]
        member = tar.extractfile("objects.manifest.json")
        assert member is not None
        raw = member.read()
    manifest = json.loads(raw)["objects"]
    assert [(m["key"], m["size"], m["sha256"]) for m in manifest] == [
        (k, len(v), hashlib.sha256(v).hexdigest()) for k, v in sorted(objects.items())
    ]
    assert summary == {"count": 2, "sha256": hashlib.sha256(raw).hexdigest()}


def test_db_roles_makes_the_backup_login_a_read_all_data_member_only() -> None:
    svc = services()["db-roles"]
    script = "\n".join(svc["command"])
    assert "GRANT pg_read_all_data TO %I" in script
    assert "BACKUP_DB_USER" in svc["environment"]
    assert "pg_write_all_data" not in script
