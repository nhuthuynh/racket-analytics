# syntax=docker/dockerfile:1.7
# Backend image: one Python project, two entry points (api, worker). ADR 0008.
# Build from the repo root:  docker build -f infra/docker/backend.Dockerfile --target api .
# Entry-point contract with the backend lane (ST-005, ST-007):
#   api    -> ASGI app at racket.platform.app:app  (override: API_APP)
#   worker -> python -m racket.worker              (override: WORKER_MODULE)
# Behind a TLS-intercepting proxy, pass its CA as an optional build secret:
#   docker build --secret id=extra_ca,src=/path/to/ca.crt ...
ARG PYTHON_IMAGE=python:3.11-slim

FROM ${PYTHON_IMAGE} AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PROJECT_ENVIRONMENT=/app/.venv
RUN --mount=type=secret,id=extra_ca,required=false \
    if [ -f /run/secrets/extra_ca ]; then export PIP_CERT=/run/secrets/extra_ca; fi \
 && pip install --no-cache-dir uv==0.8.17 \
 && groupadd --system app && useradd --system --gid app --home /app app
WORKDIR /app
COPY backend/pyproject.toml backend/uv.lock ./
RUN --mount=type=secret,id=extra_ca,required=false \
    if [ -f /run/secrets/extra_ca ]; then export SSL_CERT_FILE=/run/secrets/extra_ca; fi \
 && uv sync --locked --no-dev --no-install-project
COPY backend/src ./src
RUN --mount=type=secret,id=extra_ca,required=false \
    if [ -f /run/secrets/extra_ca ]; then export SSL_CERT_FILE=/run/secrets/extra_ca; fi \
 && uv sync --locked --no-dev
ENV PATH="/app/.venv/bin:$PATH"

FROM base AS api
ENV API_APP=racket.platform.app:app
USER app
EXPOSE 8000
# Graceful SIGTERM (AQS/OPS-02): uvicorn drains in-flight requests.
CMD ["sh", "-c", "exec uvicorn \"$API_APP\" --host 0.0.0.0 --port 8000 --proxy-headers --no-server-header"]

FROM ${PYTHON_IMAGE} AS ffprobe
# LGPL ffprobe for the probe stage (ST-009; ADR 0008 "LGPL build only"; ADR 0020). A static
# BtbN FFmpeg-Builds "lgpl" build, configured without --enable-gpl/--enable-nonfree (LGPL v3
# because of --enable-version3). Pinned to a month-end autobuild tag (month-end tags are kept
# long-term upstream) and sha256-verified. Only bin/ffprobe and the licence text are kept.
ARG FFMPEG_BUILD_TAG=autobuild-2026-09-30-13-08
ARG FFMPEG_BUILD_NAME=ffmpeg-n8.1.3-9-g29e619e767-linux64-lgpl-8.1
ARG FFMPEG_BUILD_SHA256=dfa863a00ca81f1bdf58a372b18cff4820f0017e55de32778de8ecd8ed92a02e
RUN --mount=type=secret,id=extra_ca,required=false python - <<'EOF'
import hashlib, os, ssl, tarfile, urllib.request
tag, name, want = (os.environ[k] for k in ("FFMPEG_BUILD_TAG", "FFMPEG_BUILD_NAME", "FFMPEG_BUILD_SHA256"))
url = f"https://github.com/BtbN/FFmpeg-Builds/releases/download/{tag}/{name}.tar.xz"
ca = "/run/secrets/extra_ca"
ctx = ssl.create_default_context(cafile=ca if os.path.exists(ca) else None)
digest = hashlib.sha256()
with urllib.request.urlopen(url, context=ctx, timeout=300) as r, open("/tmp/ff.tar.xz", "wb") as f:
    while chunk := r.read(1 << 20):
        digest.update(chunk)
        f.write(chunk)
if digest.hexdigest() != want:
    raise SystemExit(f"sha256 mismatch for {name}: {digest.hexdigest()}")
os.makedirs("/out/bin", exist_ok=True)
with tarfile.open("/tmp/ff.tar.xz") as t:
    for member, dest in ((f"{name}/bin/ffprobe", "/out/bin/ffprobe"), (f"{name}/LICENSE.txt", "/out/LICENSE.txt")):
        with t.extractfile(member) as src, open(dest, "wb") as out:
            out.write(src.read())
os.chmod("/out/bin/ffprobe", 0o755)
os.remove("/tmp/ff.tar.xz")
EOF
RUN /out/bin/ffprobe -version | head -n 1 \
 && if /out/bin/ffprobe -version | grep -q -e '--enable-gpl' -e '--enable-nonfree'; then \
      echo "refusing a GPL or nonfree ffprobe build" >&2; exit 1; fi

FROM base AS worker
# No apt ffmpeg: Debian's build is GPL-enabled (ADR 0008 requires LGPL).
COPY --from=ffprobe /out /opt/ffmpeg
ENV WORKER_MODULE=racket.worker FFPROBE_BIN=/opt/ffmpeg/bin/ffprobe
USER app
CMD ["sh", "-c", "exec python -m \"$WORKER_MODULE\""]
