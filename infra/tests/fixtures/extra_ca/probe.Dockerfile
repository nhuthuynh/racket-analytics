# Probe image for C4-CA (IT-04-14): built through infra/compose.yaml's real build-secret wiring
# (the test swaps only the `migrate` service's context and Dockerfile). It records the sha256 of
# the extra_ca secret it was given, or "none"; the certificate itself stays in the secret mount.
ARG PROBE_IMAGE=busybox:1.36
FROM ${PROBE_IMAGE} AS probe
RUN --mount=type=secret,id=extra_ca,required=false \
    if [ -f /run/secrets/extra_ca ]; then sha256sum /run/secrets/extra_ca | cut -d' ' -f1 > /extra-ca-seen; \
    else echo none > /extra-ca-seen; fi
