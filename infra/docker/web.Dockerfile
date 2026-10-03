# Web image: Next.js PWA (ST-010). Build from the repo root:
#   docker build -f infra/docker/web.Dockerfile .
# Contract with the frontend lane: web/package.json has `build` and `start` scripts and a
# committed pnpm-lock.yaml; `start` listens on $PORT (3000).
ARG NODE_IMAGE=node:22-slim

FROM ${NODE_IMAGE} AS deps
ENV PNPM_HOME=/pnpm PATH=/pnpm:$PATH
RUN corepack enable
WORKDIR /web
COPY web/package.json web/pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile

FROM deps AS build
COPY web/ ./
ENV NEXT_TELEMETRY_DISABLED=1
RUN pnpm build

FROM ${NODE_IMAGE} AS runtime
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1 PORT=3000 PNPM_HOME=/pnpm PATH=/pnpm:$PATH
RUN corepack enable
WORKDIR /web
COPY --from=build --chown=node:node /web ./
USER node
EXPOSE 3000
CMD ["pnpm", "start"]
