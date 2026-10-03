# 0019. The Next.js `/api` rewrite is for dev and CI only; uploads use 8 MiB chunks

- **Status:** Proposed (the principal-engineer confirms, per api-sprint-00 §8)
- **Date:** 2026-10-03
- **Deciders:** senior-frontend-engineer
- **Consulted:** principal-engineer (contract owner), sre-devops-engineer (Compose and ingress)
- **Related:** ST-010, ST-008, api-sprint-00 §1 and §8, ADR 0011, ADR 0018

## Context and problem statement
api-sprint-00 §8 asks the FE to confirm that the Next.js `/api` rewrite streams a PATCH body of at least 64 MiB, which is `UPLOAD_MAX_CHUNK_BYTES`. If it cannot, the FE must raise it. We measured the rewrite against a local echo server and against the real API, using Next.js 15.5.27 with `next start`.

Findings:

1. **The rewrite proxy caps request bodies at 10 MB, with or without middleware.** A 64 MiB PATCH got `500` after about 30 s. Next logged "Request body exceeded 10MB for /api/uploads/abc. Only the first 10MB will be available unless configured" and then ECONNRESET to the upstream. The result was the same after removing `src/middleware.ts` and rebuilding.
2. **An 8 MiB PATCH, the contract's client `chunkSize`, passes intact:** `200`, and the upstream received `bytes: 8388608`.
3. **The rewrite destination is fixed at `next build`.** A build made with `API_INTERNAL_URL=http://127.0.0.1:8702` still proxied to `localhost:8000` when started with a different value. The value is stored in `.next/routes-manifest.json`.

## Decision drivers
- Uploads must work in dev and CI (the walking skeleton, E2E-00-01).
- The production ingress already routes `/api` to the API (api-sprint-00 §1), so Next never proxies uploads in production.
- Avoid buffering large bodies in the web process (memory per concurrent upload).

## Considered options
1. **Keep the rewrite for dev and CI. The client sends 8 MiB chunks (the contract value). Production routes `/api` at the ingress.** Default `API_INTERNAL_URL` to the Compose address `http://api:8000`, because it is baked in at build time.
2. **Raise `middlewareClientMaxBodySize` to about 70 MB.** Next would then buffer up to 64 MiB per request in memory.
3. **A custom streaming route handler (`app/api/[...path]/route.ts`).** This proxies with `fetch(..., { duplex: 'half' })` and reads the target at runtime.
4. **The contract's fallback: direct cross-origin calls with a CORS allowlist.** This changes api-sprint-00 §1 and §2.

## Decision outcome
Chosen option: **1**. It meets the contract as written for the client's 8 MiB chunks, needs no new code path, and keeps production unchanged, because the ingress handles `/api` there. Option 3 is the fallback if dev or CI ever need chunks above 10 MB.

## Pros and cons of the options
### Option 1
- Good: no new proxy code. Proven end to end: the walking-skeleton E2E uploads the fixture through the rewrite to the real API.
- Bad: a client chunk size above 10 MB would fail in dev and CI. The 64 MiB server limit cannot be exercised through the web origin in dev. `API_INTERNAL_URL` is read at build time for the rewrite.
### Option 2
- Bad: it buffers whole chunks in memory and is still not streaming.
### Option 3
- Good: true streaming and a runtime target.
- Bad: a hand-written proxy is a security surface (header forwarding, hop-by-hop headers, `Set-Cookie`).
### Option 4
- Bad: CORS, third-party cookie rules, and a contract change.

## Consequences
- `web/src/lib/upload/tus-policy.ts` fixes `CHUNK_SIZE = 8 MiB`, and a unit test pins it.
- `web/src/lib/api/config.ts` defaults to `http://api:8000`. Developers who run `pnpm dev` outside Compose set `API_INTERNAL_URL=http://localhost:8000`. The Docker build needs no build argument for Compose. Optional (SRE): set `ARG API_INTERNAL_URL` explicitly in `infra/docker/web.Dockerfile`.
- Follow-up for the principal-engineer: record in api-sprint-00 §8 that 64 MiB through the web origin is a production-ingress property, not a dev-rewrite property.

## Evidence
| Claim | Evidence | Type |
|---|---|---|
| 64 MiB PATCH fails through the rewrite | `curl -X PATCH --data-binary @64m.bin http://127.0.0.1:3100/api/uploads/abc` → `500`, `time_total=30.04s`; Next log "Request body exceeded 10MB … Failed to proxy … ECONNRESET" | test result |
| The same failure without middleware | `src/middleware.ts` moved away, rebuilt, same command → `500` after 30.06 s, same log line | test result |
| 8 MiB passes | Same command with `8m.bin` → `status=200`; upstream echo `{"bytes":8388608}` | test result |
| The destination is fixed at build | `API_INTERNAL_URL=http://127.0.0.1:8702 next start` on a build made without it → "Failed to proxy http://localhost:8000/hello" | test result |
| The real upload works through the rewrite | `playwright test e2e/walking-skeleton.spec.ts` (Chromium, real API, worker, Postgres 16, SeaweedFS 3.97) → 2 passed | test result |
| Production routes `/api` at the ingress | api-sprint-00 §1 | contract |

## Confirmation
Walking-skeleton E2E in the CI e2e job, and `tests/unit/tus-policy.test.ts` ("is 8 MiB per the contract").

## Notes
