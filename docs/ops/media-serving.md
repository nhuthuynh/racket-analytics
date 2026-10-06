# Media serving on the web origin (SRE-MEDIA)

Owner: sre-devops-engineer. Story: SRE-MEDIA (sprint-02 §3; FR-027, NFR-055, NFR-069). Inputs: decision-log "ST-037 media links are presigned for the public origin" (senior-backend-engineer); ADR 0034 E6.

## How a rally video reaches the browser

1. The page asks `GET /api/matches/{id}/rallies/{rally_id}/media` (or `/matches/{id}/video`). The API answers `{url, expires_in_s, start_ms}` with `Cache-Control: no-store`.
2. `url` is an S3 v4 presigned GET, signed for `S3_PUBLIC_ENDPOINT_URL`, which env.example sets to `${PUBLIC_WEB_ORIGIN}`. Example shape: `https://localhost:3000/racket-media/originals/…?X-Amz-Algorithm=…&X-Amz-Signature=…`.
3. `web-tls` (`infra/tls/Caddyfile`) sends `/{$S3_BUCKET_MEDIA}/*` to `objectstore:8333` with path and Host unchanged, because the signature covers both. Everything else goes to the web.
4. The page CSP `media-src 'self' blob:` allows it, because it is the same origin. No CORS rule exists or is needed.

## Edge rules (tested in `infra/tests/test_compose_sprint02.py` and `infra/tests/test_media_edge_headers.py`)

| Rule | Why |
|---|---|
| Only `GET`/`HEAD` with an `X-Amz-Signature` query reach the store; anything else on the bucket path gets 403 from the edge | No listing, no writes, no unsigned reads through the public origin |
| `Cookie` and `Authorization` are removed before the store | The session never leaves the edge (NFR-055: no session token with media) |
| `Access-Control-*` and `Server` are removed from the store's answers | Same origin only; SeaweedFS adds CORS grants and its version banner to every GET (measured) |
| `X-Content-Type-Options: nosniff`, `Content-Security-Policy: default-src 'none'; sandbox` and `Cache-Control: private, no-store` are set on the store's answers; `Seaweed-*` and `X-Seaweedfs-*` are removed (SEC-S2-TM-03) | SeaweedFS ignores the signed `response-content-type` (threat model E3), so the stored type is the only type control: the browser must not sniff, a URL opened as a page runs nothing, a signed private object is not cached, and store internals (owner, upload id) stay at the edge. The integration test runs the pinned Caddy image in front of a stub store that answers `text/html` with SeaweedFS headers |
| Path and Host are not rewritten | Any rewrite breaks every signature |
| TTL `MEDIA_URL_TTL_SECONDS` (default 300) | The API refuses to start above 900 s (NFR-055) |
| No access log on `web-tls` | A signed URL never lands in a log (NFR-069) |

A presigned `HEAD` gets 403: S3 signatures bind the method, and the API signs GET only. Browsers fetch video with GET and `Range`.

## Live check (2026-10-06, stack `racket-sre02`, https://localhost:53000)

| Check | Result |
|---|---|
| `live_tagging.py --runs 1` step `media_link` | ok: 200, `range_status` 206, `tampered_status` 403, `ttl_s` 300 |
| presigned GET `Range: bytes=0-1023` | 206, 1,024 bytes |
| same object without the signature; bucket listing; listing with a fake `X-Amz-Signature`; `PUT` and `DELETE` with the presigned query | 403 each |
| cross-origin request (`Origin: https://evil.example`) | 206 with no `Access-Control-*` and no `Server` header (after the strip; before it, SeaweedFS sent `access-control-allow-methods: PUT, POST, GET, DELETE, OPTIONS` and `server: SeaweedFS 30GB 3.97`) |
| `/racket-media-x` (look-alike path) | 404 from the web, not the store |

## Changing the origin

`S3_PUBLIC_ENDPOINT_URL`, `ALLOWED_ORIGINS` and the sign-in link all follow `PUBLIC_WEB_ORIGIN`, so the goal scorecard's single `sed` remap (§4.0) moves all three. A deployment sets the public https origin (ADR 0034 E6).
