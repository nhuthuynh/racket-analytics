"""Shared helpers for C4-CA (VR3-S3-01): the optional ``extra_ca`` build secret.

``rendered_secret_ids`` reads the secret ids each built service would hand BuildKit from a
rendered ``docker compose config``. ``probe_build`` builds the small probe image
(``fixtures/extra_ca/probe.Dockerfile``) through the real ``infra/compose.yaml`` secret wiring
and returns what the build saw plus every layer's (decompressed) bytes.
"""

from __future__ import annotations

import gzip
import hashlib
import io
import os
import subprocess
import tarfile
import uuid
from dataclasses import dataclass
from pathlib import Path

import yaml
from conftest import REPO_ROOT

COMPOSE = REPO_ROOT / "infra" / "compose.yaml"
ENV_EXAMPLE = REPO_ROOT / "infra" / "env.example"
PROBE_DIR = Path(__file__).resolve().parent / "fixtures" / "extra_ca"
SECRET_ID = "extra_ca"
PROBE_IMAGE = "${DOCKERHUB_REGISTRY:-docker.io}/library/busybox:1.36"


def docker_env() -> dict[str, str]:
    """The caller's env without upper-case settings (the env file is the only input), as
    ``test_compose.compose_config`` does, keeping what the docker CLI itself needs."""
    keep = {"PATH", "HOME", "DOCKER_HOST", "DOCKER_CONFIG", "XDG_RUNTIME_DIR"}
    return {k: v for k, v in os.environ.items() if not k.isupper() or k in keep}


def env_file(tmp: Path, extra_ca: Path | None) -> Path:
    """infra/env.example, plus EXTRA_CA_FILE when given and the caller's registry mirror."""
    lines = [ENV_EXAMPLE.read_text()]
    if os.environ.get("DOCKERHUB_REGISTRY"):
        lines.append(f"DOCKERHUB_REGISTRY={os.environ['DOCKERHUB_REGISTRY']}")
    if extra_ca is not None:
        lines.append(f"EXTRA_CA_FILE={extra_ca}")
    f = tmp / "stack.env"
    f.write_text("\n".join(lines) + "\n")
    return f


def render(env: Path) -> dict:
    res = subprocess.run(
        ["docker", "compose", "-f", str(COMPOSE), "--env-file", str(env), "config"],
        capture_output=True,
        text=True,
        env=docker_env(),
        timeout=60,
        check=False,
    )
    assert res.returncode == 0, res.stderr
    return yaml.safe_load(res.stdout)


def rendered_secret_ids(config: dict) -> dict[str, set[str]]:
    """Per built service, the ids BuildKit gets: a build secret's target, else its source."""
    ids: dict[str, set[str]] = {}
    for name, svc in config["services"].items():
        if "build" in svc:
            ids[name] = {
                (s.get("target") or s["source"]) if isinstance(s, dict) else s
                for s in svc["build"].get("secrets") or []
            }
    return ids


def make_ca(tmp: Path) -> Path:
    """A throwaway self-signed CA certificate (never committed); its key is deleted."""
    key, crt = tmp / "ca.key", tmp / "ca.crt"
    subprocess.run(
        [
            "openssl",
            "req",
            "-x509",
            "-newkey",
            "rsa:2048",
            "-nodes",
            "-days",
            "1",
            "-subj",
            f"/CN=c4-ca-throwaway-{uuid.uuid4().hex[:12]}",
            "-keyout",
            str(key),
            "-out",
            str(crt),
        ],
        capture_output=True,
        check=True,
        timeout=60,
    )
    key.unlink()
    return crt


def _blob_bytes(data: bytes) -> bytes:
    return gzip.decompress(data) if data[:2] == b"\x1f\x8b" else data


@dataclass
class Probe:
    seen: str  # sha256 of the extra_ca secret the build was given, or "none"
    layers: list[bytes]  # every file of `docker save`, gzip blobs decompressed


def probe_build(tmp: Path, env: Path) -> Probe:
    """Build the probe as the `migrate` service of infra/compose.yaml (its secrets unchanged)."""
    tag = f"racket-extra-ca-probe:{uuid.uuid4().hex[:12]}"
    override = tmp / "probe.override.yaml"
    override.write_text(
        yaml.safe_dump(
            {
                "services": {
                    "migrate": {
                        "image": tag,
                        "build": {
                            "context": str(PROBE_DIR),
                            "dockerfile": "probe.Dockerfile",
                            "target": "probe",
                            "args": {"PROBE_IMAGE": PROBE_IMAGE},
                        },
                    }
                }
            }
        )
    )
    base = [
        "docker",
        "compose",
        "-p",
        f"extra-ca-{uuid.uuid4().hex[:8]}",
        "-f",
        str(COMPOSE),
        "-f",
        str(override),
        "--env-file",
        str(env),
    ]
    try:
        res = subprocess.run(
            [*base, "build", "migrate"],
            capture_output=True,
            text=True,
            env=docker_env(),
            timeout=300,
            check=False,
        )
        assert res.returncode == 0, res.stdout[-3000:] + res.stderr[-3000:]
        seen = subprocess.run(
            ["docker", "run", "--rm", tag, "cat", "/extra-ca-seen"],
            capture_output=True,
            text=True,
            check=True,
            timeout=60,
        ).stdout.strip()
        saved = subprocess.run(
            ["docker", "save", tag], capture_output=True, check=True, timeout=120
        ).stdout
    finally:
        subprocess.run(["docker", "rmi", "-f", tag], capture_output=True, check=False, timeout=60)
    with tarfile.open(fileobj=io.BytesIO(saved)) as t:
        layers = [_blob_bytes(t.extractfile(m).read()) for m in t.getmembers() if m.isfile()]
    return Probe(seen=seen, layers=layers)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pem_body_lines(path: Path) -> list[bytes]:
    """The base64 lines of a PEM certificate: what a copied CA file would contain."""
    return [ln for ln in path.read_bytes().splitlines() if ln and not ln.startswith(b"-----")]


def holds_certificate(probe: Probe, ca: Path) -> bool:
    lines = pem_body_lines(ca)
    return any(ln in layer for layer in probe.layers for ln in lines[1:-1])
