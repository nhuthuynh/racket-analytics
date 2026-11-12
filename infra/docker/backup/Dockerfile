# syntax=docker/dockerfile:1.7
# Backup image (ST-076a, ADR 0058 rules 1-3): pg_dump/pg_dumpall of the Postgres 16 server, the
# `age` release (BSD-3-Clause) pinned by checksum, and the standard-library Python of
# scripts/ops/backup.py. Built from the repo root by the compose `backup` service (profile ops).
# No key is ever in this image: the service gets the public recipient from the environment.
ARG PG_IMAGE=postgres:16-alpine
ARG PYTHON_IMAGE=python:3.11-alpine
ARG AGE_VERSION=v1.2.1
ARG TARGETARCH

FROM ${PYTHON_IMAGE} AS python

# The age release from GitHub, verified by checksum (no package index needed at build time).
FROM ${PYTHON_IMAGE} AS age-amd64
ARG AGE_VERSION
ADD --checksum=sha256:7df45a6cc87d4da11cc03a539a7470c15b1041ab2b396af088fe9990f7c79d50 \
    https://github.com/FiloSottile/age/releases/download/${AGE_VERSION}/age-${AGE_VERSION}-linux-amd64.tar.gz /age.tgz
FROM ${PYTHON_IMAGE} AS age-arm64
ARG AGE_VERSION
ADD --checksum=sha256:57fd79a7ece5fe501f351b9dd51a82fbee1ea8db65a8839db17f5c080245e99f \
    https://github.com/FiloSottile/age/releases/download/${AGE_VERSION}/age-${AGE_VERSION}-linux-arm64.tar.gz /age.tgz
FROM age-${TARGETARCH:-amd64} AS age
RUN mkdir /out && tar -xzf /age.tgz -C /out --strip-components=1 age/age age/age-keygen

FROM ${PG_IMAGE}
# Python from the official Alpine image (same musl libc); only the interpreter and stdlib.
COPY --from=python /usr/local/bin/python3.11 /usr/local/bin/python3
COPY --from=python /usr/local/lib/libpython3.11.so.1.0 /usr/local/lib/
COPY --from=python /usr/local/lib/python3.11 /usr/local/lib/python3.11
COPY --from=age /out/age /out/age-keygen /usr/local/bin/
COPY scripts/ops/backup.py /opt/racket/backup.py
RUN age --version && python3 -c "import ssl, tarfile, urllib.request, xml.etree.ElementTree"
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
STOPSIGNAL SIGTERM
ENTRYPOINT ["python3", "/opt/racket/backup.py"]
