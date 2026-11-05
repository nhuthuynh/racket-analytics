"""ST-076a-part2 unit tests (NFR-045.1; ADR 0058 rules 1-3; T5-BK-1..3): the media-bucket
mirror artefact, SigV4 request signing, the mirror's read-only requests, and the Compose
``backup`` service (profile ops), its ``db-roles`` login and its object-store identity.
Split from ``test_backup_service.py`` (PR-policy step, docs/sprints/05/decisions/ST-076a.md).
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from types import ModuleType

import pytest
import yaml
from conftest import REPO_ROOT
from test_backup_service import NOW, load, plant_set

pytestmark = pytest.mark.unit

COMPOSE = REPO_ROOT / "infra" / "compose.yaml"
ENV_EXAMPLE = REPO_ROOT / "infra" / "env.example"
DOCKERFILE = REPO_ROOT / "infra" / "docker" / "backup" / "Dockerfile"


@pytest.fixture(scope="module")
def bk() -> ModuleType:
    return load()


# ---------------------------------------------------------------- encryption (T5-BK-1)
def test_an_artefact_without_the_age_header_fails_the_encryption_check(
    bk: ModuleType, tmp_path: Path
) -> None:
    d = plant_set(tmp_path, NOW)
    (d / "objects.tar.age").write_bytes(b"objects.manifest.json\x00" * 4)
    with pytest.raises(bk.NotEncrypted, match=r"objects\.tar\.age"):
        bk.verify_encrypted(d)


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
