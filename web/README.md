# web: Racket Analytics PWA (ST-010)

This is a Next.js 15 App Router app written in strict TypeScript. It talks to the API only through the typed client in `src/lib/api/` and the same-origin `/api` rewrite, following the contract in `docs/architecture/api-sprint-00.md`.

| Command | What it does |
|---|---|
| `pnpm install` | Install dependencies (lockfile committed) |
| `pnpm dev` / `pnpm dev:https` | Dev server; `dev:https` uses a local mkcert certificate so the `Secure` session cookie works |
| `pnpm build` / `pnpm start` | Production build; `start` listens on `$PORT` (default 3000) |
| `pnpm lint` · `pnpm typecheck` · `pnpm test:unit` | ESLint (0 warnings), `tsc --noEmit`, Vitest (`tests/unit/`) |
| `pnpm test:coverage` | Vitest with v8 coverage |
| `pnpm check:first-route-js` | NFR-015 budget (≤ 200 KB gzipped) on the last build |
| `pnpm test:e2e` | Playwright journeys in `e2e/` (QA-owned) against `BASE_URL`; `PW_PROJECTS=chromium` limits the browser projects |
| `pnpm tokens` | Regenerate `src/app/tokens.css` from `docs/design/tokens.json` (a unit test fails if they differ) |

## Configuration

- `API_INTERNAL_URL`: where the server reaches the API. The default is `http://api:8000`, the Compose service. The `/api` rewrite **reads it at build time**, and server components read it at runtime (ADR 0019). Outside Compose, set it for both `build` and `start`, or for `dev`.

## Running the walking skeleton without Docker

From the repo root:

```bash
eval "$(scripts/dev-postgres.sh start)"; eval "$(scripts/dev-objectstore.sh start)"
export APP_ENV=dev DEV_IDENTITY_ENABLED=true API_PUBLIC_PATH_PREFIX=/api
(cd backend && uv run python -m racket.platform.migrate \
  && uv run uvicorn racket.platform.app:create_app --factory --port 8811 &)
(cd backend && uv run python -m racket.worker &)
cd web && API_INTERNAL_URL=http://127.0.0.1:8811 pnpm build \
  && API_INTERNAL_URL=http://127.0.0.1:8811 pnpm start &
BASE_URL=http://localhost:3000 PW_PROJECTS=chromium pnpm test:e2e
```

This no-Docker recipe serves plain http, which only Chromium accepts for the `Secure` session cookie (it treats `localhost` as secure). WebKit needs https: run the Compose stack (`infra/compose.yaml`), whose `web-tls` proxy serves `https://localhost:3000` (the Playwright default; ADR 0029).

## Rules this code follows

- Authorisation lives in the API only. Pages map a 401 to sign-in and a 404 to the single not-found page.
- Titles and other user text are rendered as text, never as HTML (ESLint forbids `dangerouslySetInnerHTML` and `innerHTML`).
- Colours come only from the token CSS variables (`--color-*`).
- `public/sw.js` caches only content-hashed `/_next/static/` files and never caches pages, `/api/*` or media.
- CSP uses a per-request nonce (`src/middleware.ts`, ADR 0018). Other security headers are set in `next.config.ts`.
