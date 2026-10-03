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

FROM base AS worker
# FFmpeg/ffprobe for the probe stage (ST-009). NOTE: Debian's ffmpeg is built with GPL
# components; ADR 0008 requires an LGPL build. Tracked in docs/sprints/00/blockers.md for
# the ST-009 owner (senior-ml-cv-engineer) and security-privacy-engineer.
RUN apt-get update \
 && apt-get install -y --no-install-recommends ffmpeg \
 && rm -rf /var/lib/apt/lists/*
ENV WORKER_MODULE=racket.worker
USER app
CMD ["sh", "-c", "exec python -m \"$WORKER_MODULE\""]
