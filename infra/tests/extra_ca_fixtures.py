"""C4-CA (VR3-S3-01) helpers: ``rendered_secret_ids`` (per built service, from ``docker compose
config``) and ``probe_build`` (``fixtures/extra_ca/probe.Dockerfile`` through the real compose
secret wiring: what the build saw plus every layer's decompressed bytes)."""

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
from typing import Any

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
    cmd = ["docker", "compose", "-f", str(COMPOSE), "--env-file", str(env), "config"]
    res = _run(cmd, text=True, env=docker_env(), check=False)
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


def _run(cmd: list[str], **kw: Any) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, timeout=300, **kw)


def make_ca(tmp: Path) -> Path:
    """A throwaway self-signed CA certificate (never committed); its key is deleted."""
    key, crt = tmp / "ca.key", tmp / "ca.crt"
    subj = f"/CN=c4-ca-throwaway-{uuid.uuid4().hex[:12]}"
    cmd = ["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-days", "1", "-subj"]
    _run([*cmd, subj, "-keyout", str(key), "-out", str(crt)], check=True)
    key.unlink()
    return crt


@dataclass
class Probe:
    seen: str  # sha256 of the extra_ca secret the build was given, or "none"
    layers: list[bytes]  # every file of `docker save`, gzip blobs decompressed


def probe_build(tmp: Path, env: Path) -> Probe:
    """Build the probe as the `migrate` service of infra/compose.yaml (its secrets unchanged).

    ``--no-cache``: BuildKit does not key its cache on secret contents, so a cached step from
    an earlier probe build would report that build's secret.
    """
    tag = f"racket-extra-ca-probe:{uuid.uuid4().hex[:12]}"
    build = {"context": str(PROBE_DIR), "dockerfile": "probe.Dockerfile", "target": "probe"}
    build["args"] = {"PROBE_IMAGE": PROBE_IMAGE}
    override = tmp / "probe.override.yaml"
    override.write_text(yaml.safe_dump({"services": {"migrate": {"image": tag, "build": build}}}))
    project = f"extra-ca-{uuid.uuid4().hex[:8]}"
    compose = ["docker", "compose", "-p", project, "-f", str(COMPOSE), "-f", str(override)]
    try:
        res = _run(
            [*compose, "--env-file", str(env), "build", "--no-cache", "migrate"],
            text=True,
            env=docker_env(),
            check=False,
        )
        assert res.returncode == 0, res.stdout[-3000:] + res.stderr[-3000:]
        seen = _run(["docker", "run", "--rm", tag, "cat", "/extra-ca-seen"], text=True, check=True)
        saved = _run(["docker", "save", tag], check=True).stdout
    finally:
        _run(["docker", "rmi", "-f", tag], check=False)
    with tarfile.open(fileobj=io.BytesIO(saved)) as t:
        blobs = [t.extractfile(m).read() for m in t.getmembers() if m.isfile()]
    layers = [gzip.decompress(b) if b[:2] == b"\x1f\x8b" else b for b in blobs]
    return Probe(seen=seen.stdout.strip(), layers=layers)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def holds_certificate(probe: Probe, ca: Path) -> bool:
    """Any inner base64 line of the PEM in any layer: what a copied CA file would contain."""
    lines = [ln for ln in ca.read_bytes().splitlines() if ln and not ln.startswith(b"-----")]
    return any(ln in layer for layer in probe.layers for ln in lines[1:-1])
