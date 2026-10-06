# syntax=docker/dockerfile:1.7
# Web image: Next.js PWA (ST-010). Build from the repo root:
#   docker build -f infra/docker/web.Dockerfile .
# Behind a TLS-intercepting proxy, pass its CA as an optional build secret (QA-R2-03; same as
# backend.Dockerfile):  docker build --secret id=extra_ca,src=/path/to/ca.crt ...
# Contract with the frontend lane: web/package.json has `build` and `start` scripts and a
# committed pnpm-lock.yaml; `start` listens on $PORT (3000).
ARG NODE_IMAGE=node:22-slim

FROM ${NODE_IMAGE} AS deps
ENV PNPM_HOME=/pnpm PATH=/pnpm:$PATH
RUN corepack enable
WORKDIR /web
COPY web/package.json web/pnpm-lock.yaml ./
RUN --mount=type=secret,id=extra_ca,required=false \
    if [ -f /run/secrets/extra_ca ]; then export NODE_EXTRA_CA_CERTS=/run/secrets/extra_ca; fi \
 && pnpm install --frozen-lockfile

FROM deps AS build
COPY web/ ./
ENV NEXT_TELEMETRY_DISABLED=1
# The runtime copies this stage, so the Next build cache goes (C-15, disk per evidence round).
# Dev dependencies stay: `next start` transpiles next.config.ts and needs TypeScript (measured
# 2026-10-06: after `pnpm prune --prod` the container exits trying `pnpm add typescript`).
RUN --mount=type=secret,id=extra_ca,required=false \
    if [ -f /run/secrets/extra_ca ]; then export NODE_EXTRA_CA_CERTS=/run/secrets/extra_ca; fi \
 && pnpm build \
 && rm -rf .next/cache

FROM ${NODE_IMAGE} AS runtime
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1 PORT=3000
WORKDIR /web
COPY --from=build --chown=node:node /web ./
USER node
EXPOSE 3000
# No pnpm at runtime: corepack would download it at container start (QA-R2-03 finding).
# `next start` reads $PORT itself.
CMD ["node", "node_modules/next/dist/bin/next", "start"]
