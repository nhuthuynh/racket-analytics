# API contract: Sprint 0 (walking skeleton)

- **Status:** Accepted for Sprint 0 (principal-engineer, 2026-10-03). Changes go through a PR on this file, reviewed by BE, FE and QA. The test seams in `backend/tests/support/contract.py` (ADR 0012) must change in the same PR.
- **Owner:** principal-engineer. **Security review:** security-privacy-engineer (`docs/security/threat-model-v0.md`).
- **Stories:** ST-005, ST-006, ST-007 (no HTTP), ST-008, ST-009 (facts), ST-010 (client).
- **Decisions this rests on:** ADR 0008 (stack), ADR 0011 (tus core in FastAPI), ADR 0012 (test seams).

This contract matches the QA red-first tests as they stand on 2026-10-03. Where the tests leave a choice open (for example `200` or `204`), this file fixes one answer, and the tests accept it.

## 1. Conventions

| Topic | Rule |
|---|---|
| Base path | The API serves at the **root** (`/matches`, `/uploads/...`). Browsers reach it through the web origin under **`/api`**: Next.js rewrites `/api/:path*` → `http://api:8000/:path*` in dev, and the ingress does the same in production. The API never assumes the prefix, except in the tus `Location` header, which uses `API_PUBLIC_PATH_PREFIX` (§6.2). Same-origin routing removes CORS and keeps the session cookie first-party (judgment). |
| Media type | JSON requests and responses use `application/json; charset=utf-8`. tus PATCH bodies use `application/offset+octet-stream`. Every response with a body has a matching `Content-Type` (ASVS 4.1.1). |
| IDs | Public IDs are UUIDv4 in canonical lowercase form [AQS/SEC-09]. A path ID that is not a UUID returns **404 `not_found`**, never 422, so a malformed ID and a foreign ID look alike (judgment). |
| Timestamps | RFC 3339, UTC, with `Z`, e.g. `2026-10-05T09:12:44.123Z`. |
| Unknown fields | Request bodies are closed schemas (`extra="forbid"`). An unknown field gives **422** (NFR-052) [AQS/SEC-03 8.2.3]. |
| Response fields | Responses are built from explicit allowlist schemas. Nothing else is serialised (NFR-052). |
| Methods | Only the methods listed here. Anything else gives **405** with the generic error body. `TRACE` is not supported. |
| Lists | `{"items": [...], "next_cursor": null}`. Sprint 0 has no paging beyond `limit`. `limit` is an integer from 1 to 100 (default 50), and out of range gives 422 [AQS/SEC-10]. Lists are ordered newest first. |
| Tracing | Accepts W3C `traceparent`/`tracestate`. A malformed header is ignored and a new trace starts. The request still succeeds [AQS/OPS-06] (IT-00-12). |
| Request ID | Every response carries `X-Request-ID`. An incoming value is reused only if it matches `^[A-Za-z0-9._-]{1,64}$`; otherwise a new one is generated. This prevents log injection (ASVS 16.4.1). |

### 1.1 Headers on every API response (ST-005; NFR-061, NFR-067)

| Header | Value | When |
|---|---|---|
| `X-Content-Type-Options` | `nosniff` | always |
| `X-Frame-Options` | `DENY` | always |
| `Referrer-Policy` | `no-referrer` | always (ASVS 3.4.5) |
| `Cache-Control` | `no-store` | every response to an authenticated request, every error response, and every tus response [AQS/SEC-05 14.3.2] |
| `Server` | absent, or without a version number | always (IT-00-14) |
| `Strict-Transport-Security` | set at the TLS terminator in staging and production, not by the app | prod (ASVS 3.4.1) |

## 2. Authentication: the dev identity provider (ST-006)

**There is no `Authorization` header.** Authentication is an **opaque session cookie** set by the API. The real sign-in (FR-001, Sprint 1) will issue the same cookie, so clients do not change.

| Item | Rule |
|---|---|
| Availability | The `/dev/*` routes are **registered only** when `DEV_IDENTITY_ENABLED=true`. Otherwise they do not exist (404). The API **refuses to start** when `APP_ENV=prod` and `DEV_IDENTITY_ENABLED=true` (sprint-00 §5 `Settings` test 2). |
| Seeded users | `ivy` ("Ivy") and `carlos` ("Carlos"), seeded at startup **only** when the dev provider is enabled and `APP_ENV` is `dev` or `test`. No default accounts exist in production (ASVS 6.3.2). |
| Token | 32 bytes from a CSPRNG, base64url-encoded (256 bits; ASVS 7.2.3, 11.5.1). Postgres stores **only its SHA-256** in `sessions(token_sha256, account_id, created_at, expires_at)`. The token is never logged [AQS/SEC-04 16.2.5]. |
| Cookie name and attributes | `APP_ENV` = `dev`, `staging` or `prod`: `__Host-racket_session=<token>; Path=/; Secure; HttpOnly; SameSite=Lax`. `APP_ENV=test`: `racket_session=<token>; Path=/; HttpOnly; SameSite=Lax`. httpx over `http://testserver` will not return a `Secure` cookie, so the test environment is the only one without `Secure`/`__Host-` (ASVS 3.3.1, 3.3.3, 3.3.4, 3.3.2; judgment for the test exception). Dev runs the web app over HTTPS (ST-010), so `Secure` works through the `/api` rewrite. |
| Lifetime | Dev provider: absolute lifetime 12 h, no idle timeout (dev only). Real sign-in lifetimes are decided in Sprint 1 and documented per ASVS 7.1.1. |
| Rotation | Every sign-in issues a new token and deletes the session named by any cookie already presented (ASVS 7.2.4). |
| Unauthenticated | A request without a valid session gets **401 `unauthenticated`**. On routes that take an ID, authentication is checked **before** the resource is looked up, so 401 reveals nothing about existence. |
| CSRF | `SameSite=Lax`, plus every state-changing request is non-simple: JSON bodies need `Content-Type: application/json`, and tus needs `Tus-Resumable`. When `ALLOWED_ORIGINS` is set, a state-changing request whose `Origin` header is present and not in the list gets **403 `forbidden_origin`**. `ALLOWED_ORIGINS` is required when `APP_ENV` is `staging` or `prod`, and the API refuses to start without it (ASVS 3.5.1; judgment). |

### 2.1 `GET /dev/users`

Lists the dev users for the sign-in picker. No authentication is needed.

```
200 {"items": [{"username": "ivy", "display_name": "Ivy"}, {"username": "carlos", "display_name": "Carlos"}]}
```

### 2.2 `POST /dev/sign-in`

```
Request:  {"username": "ivy"}            // closed schema; username in {"ivy","carlos"}
204 No Content
Set-Cookie: __Host-racket_session=…; Path=/; Secure; HttpOnly; SameSite=Lax
```

| Status | When |
|---|---|
| 204 | signed in |
| 401 `unauthenticated` | unknown username. The message does not say whether the user exists |
| 422 `validation_failed` | body not matching the schema |

Each attempt, successful or not, is logged to the `racket.security` logger with `event="auth.sign_in"`, `outcome`, `account_id` (on success), and no username or token [AQS/SEC-04 16.3.1].

### 2.3 `POST /auth/sign-out`

Deletes the server-side session and expires the cookie (`Max-Age=0`). Returns **204** even without a session, so sign-out is idempotent. Clients must also clear any cached authenticated data (ASVS 14.3.1; NFR-067).

### 2.4 `GET /me`

```
200 {"id": "6f0c…-uuid", "display_name": "Ivy"}
401 unauthenticated
```

## 3. Error body (ST-005; NFR-058)

Every non-2xx response that has a body uses exactly this shape. `HEAD` responses have no body.

```json
{"error": {"code": "not_found", "message": "We could not find that.", "support_ref": "ref_5c1e0f3a9b7d4e21"}}
```

- `code` is a machine-readable value from the table below. `message` is a fixed human sentence for that code. It **never echoes request input** and never contains exception types, SQL, module paths, stack traces or secrets [AQS/SEC-04 16.5.1].
- `support_ref` is `ref_` plus 16 random hex characters, unique per error. The same value is logged at ERROR (5xx) or INFO (4xx), with `trace_id` and `request_id`, so support can find the log line.
- One central exception handler and one global fallback produce this body [AQS/SEC-12].
- **There are no per-field details in Sprint 0.** The front end validates forms itself, and the server message is generic. Adding an allowlisted `fields` array later is a contract change that QA must approve, because the error-body regression suite pins the key set.

| HTTP | `code` | `message` (fixed text) |
|---|---|---|
| 400 | `bad_request` | "The request could not be understood." |
| 401 | `unauthenticated` | "Please sign in." |
| 403 | `forbidden_origin` | "This request is not allowed." |
| 404 | `not_found` | "We could not find that." |
| 405 | `method_not_allowed` | "This action is not allowed here." |
| 409 | `conflict` (match state) or `upload_offset_mismatch` (tus) | "This changed in the meantime. Please reload." / "Upload offset does not match. Ask the server for the current offset." |
| 411 | `length_required` | "The request needs a Content-Length." |
| 412 | `tus_version_unsupported` | "Unsupported upload protocol version." (and the response also sends `Tus-Version: 1.0.0`) |
| 413 | `payload_too_large` | "This is larger than allowed." |
| 415 | `unsupported_media_type` | "This content type is not accepted here." |
| 422 | `validation_failed` | "Some of the information is not valid." |
| 429 | `rate_limited` | "Too many requests. Please wait and try again." (reserved; rate limits arrive in Sprint 1) |
| 500 | `internal_error` | "Something went wrong on our side." |
| 503 | `unavailable` | "The service is temporarily unavailable." |

## 4. Health (ST-005)

| Route | Auth | Response |
|---|---|---|
| `GET /healthz` | none | `200 {"status": "ok"}`. Liveness; touches no dependencies. |
| `GET /readyz` | none | `200 {"status": "ready", "checks": {"database": "ok", "object_store": "ok", "queue": "ok"}}`, or `503` with the same shape, `"status": "not_ready"` and the failing check set to `"fail"`. It names the dependency and nothing more. In production it is reachable only from inside the cluster, not through the public ingress (ASVS 13.4.5; threat model T-INF-2). |

`/docs`, `/redoc` and `/openapi.json` are disabled when `APP_ENV` is `staging` or `prod` (ASVS 13.4.5).

## 5. Matches (ST-006, ST-009)

### 5.1 Representation

```json
{
  "id": "0b8f6c1e-3f3a-4c55-9a51-8d1f0e7d2a10",
  "title": "Skeleton test",
  "format": "doubles",
  "status": "video_received",
  "media": {
    "duration_ms": 60000,
    "fps": 60,
    "width": 1920,
    "height": 1080,
    "has_audio": true,
    "vfr": false,
    "container": "mov,mp4,m4a,3gp,3g2,mj2",
    "video_codec": "h264"
  },
  "created_at": "2026-10-05T09:12:44.123Z",
  "updated_at": "2026-10-05T09:14:02.511Z"
}
```

| Field | Type | Notes |
|---|---|---|
| `id` | UUIDv4 string | |
| `title` | string, 1-120 characters after trimming | Free text; the client renders it as text only |
| `format` | `"singles"` \| `"doubles"` | |
| `status` | `"awaiting_upload"` \| `"uploading"` \| `"video_received"` \| `"probe_failed"` | A **read model** composed from `Match` and `video_ingest` state (context map R2). UI labels: "Awaiting upload", "Uploading", "Video received", "We could not read this video" (the QA contract's `STATUS_LABELS`) |
| `media` | object \| `null` | `null` until the probe stage commits facts. A failed probe also leaves it `null`, with status `probe_failed` |
| `media.duration_ms` | integer ≥ 0 | The UI shows `m:ss` (or `h:mm:ss`) |
| `media.fps` | number > 0 | `avg_frame_rate` rounded to 3 decimals; `60`, `59.94`. The UI shows `{fps:g} fps` |
| `media.width`, `media.height` | integer > 0 | The UI shows `1920×1080` |
| `media.has_audio`, `media.vfr` | boolean | `vfr` is true when `r_frame_rate` ≠ `avg_frame_rate` (sprint-00 §5) |
| `media.container`, `media.video_codec` | string | ffprobe `format_name` / `codec_name`, as reported |
| `created_at`, `updated_at` | RFC 3339 UTC | |

**Never returned:** `owner_id`, object keys, upload IDs, storage URLs, `support_ref` values, or user file names (NFR-052; [AQS/SEC-03 8.2.3]).

### 5.2 Routes

| Method and path | Request | Success | Errors |
|---|---|---|---|
| `POST /matches` | `{"title": str, "format": "singles"\|"doubles"}` (closed) | **201**, the match (`status: "awaiting_upload"`, `media: null`), and `Location: /matches/{id}` (without the `/api` prefix; clients use the body) | 401, 403 `forbidden_origin`, 422 |
| `GET /matches?limit=50` | | **200** `{"items": [match, …], "next_cursor": null}`, **only the caller's matches** | 401, 422 (bad `limit`) |
| `GET /matches/{match_id}` | | **200**, the match | 401, **404** (missing *or not yours*: identical body except `support_ref`) |
| `GET /matches/{match_id}/media` | | **200**, the `media` object | 401, **404** (missing, not yours, *or not probed yet*) |

Every route with `{match_id}` loads the match through one ownership dependency (`WHERE id = :id AND owner_id = :me`). A miss logs `event="authz.denied"` to `racket.security`, with `account_id`, route template, method and `request_id`, and **no** target owner or title. The log does not say whether the resource exists [AQS/SEC-04 16.3.2] (NFR-057). The route is in the BOLA matrix (`backend/tests/regression/bola.py`).

## 6. Uploads: tus 1.0.0 core (ST-008; ADR 0011)

The client is tus-js-client. Endpoint: `/api/matches/{match_id}/uploads`, `chunkSize: 8 * 1024 * 1024`, and `retryDelays` as the FE chooses. Every tus request except `OPTIONS` must carry `Tus-Resumable: 1.0.0`. Every tus response carries `Tus-Resumable: 1.0.0` and `Cache-Control: no-store`.

### 6.1 `OPTIONS /uploads`

```
204  Tus-Resumable: 1.0.0
     Tus-Version: 1.0.0
     Tus-Extension: creation
     Tus-Max-Size: <UPLOAD_MAX_BYTES>
```

No authentication; it reveals only configuration. `checksum` and `expiration` join `Tus-Extension` in Sprint 1.

### 6.2 `POST /matches/{match_id}/uploads`: creation

| Request header | Rule |
|---|---|
| `Tus-Resumable` | `1.0.0`, otherwise 412 |
| `Upload-Length` | Required. A decimal integer from 1 to `UPLOAD_MAX_BYTES` (default 10,000,000,000 = 10 GB, provisional, NFR-053/K12). Missing or not an integer gives 400; 0 gives 400; too large gives 413. `Upload-Defer-Length` is not supported (400) |
| `Upload-Metadata` | Optional. Parsed as tus `key base64value` pairs, at most 1 KiB in total, and malformed gives 400. **No metadata value is stored or used in Sprint 0**, including `filename` (data minimisation; it never reaches object keys or tool arguments [AQS/SEC-02 5.3.2]) |

```
201 Created
Location: {API_PUBLIC_PATH_PREFIX}/uploads/{upload_id}     e.g. /api/uploads/5d0c…  (tests: /uploads/5d0c…)
Tus-Resumable: 1.0.0
```

| Status | When |
|---|---|
| 201 | Upload session created. The match status becomes `uploading` |
| 401 | no session |
| 404 | match missing or not yours (BOLA) |
| 409 `conflict` | the match already has an upload session (Sprint 0 allows one upload per match). A client that lost its upload URL cannot start again until expiry or delete arrives in Sprint 1 (FR-024) |
| 400 / 412 / 413 | as in the header table above |

The object key is generated by `ObjectKeyPolicy` as `originals/{uuid4 hex}`. It is random, unrelated to user input or IDs, and never returned [AQS/SEC-02 5.3.2].

### 6.3 `HEAD /uploads/{upload_id}`

```
200 OK            (empty body)
Upload-Offset: 40960
Upload-Length: 102400
Tus-Resumable: 1.0.0
Cache-Control: no-store
```

Errors: 401, 404 (missing or not yours; no body because the method is HEAD), 412.

### 6.4 `PATCH /uploads/{upload_id}`

Request headers: `Tus-Resumable: 1.0.0`, `Upload-Offset: <int>`, `Content-Type: application/offset+octet-stream`, `Content-Length: <int>`. The body is the bytes.

Checks run in this order, and the first failure wins (ADR 0011):

| # | Check | Status |
|---|---|---|
| 1 | session | 401 `unauthenticated` |
| 2 | `Tus-Resumable` = 1.0.0 | 412 `tus_version_unsupported` (+ `Tus-Version`) |
| 3 | upload exists and is yours | 404 `not_found` |
| 4 | `Content-Type` | 415 `unsupported_media_type` |
| 5 | `Upload-Offset` is a non-negative integer | 400 `bad_request` |
| 6 | `Content-Length` present; ≤ `UPLOAD_MAX_CHUNK_BYTES` (default 64 MiB) | 411 `length_required`; 413 `payload_too_large` |
| 7 | `Upload-Offset` = stored offset, and no other PATCH holds the lock | 409 `upload_offset_mismatch` |
| 8 | `Upload-Offset + Content-Length` ≤ `Upload-Length` | 413 `payload_too_large` |

On success:

```
204 No Content
Upload-Offset: <new offset>
Tus-Resumable: 1.0.0
Cache-Control: no-store
```

- A PATCH is **atomic**. If the body arrives short (a dropped connection), nothing from that request is stored, and HEAD returns the previous offset (ADR 0011).
- Every failed PATCH leaves the stored offset unchanged (regression suite).
- When the new offset equals `Upload-Length`, the upload is complete. In the **same transaction**, the match becomes `video_received` and one `probe` job is queued (NFR-060; IT-00-08). Media facts appear on `GET /matches/{id}` after the worker's probe stage commits (ST-009). If the probe fails, the status becomes `probe_failed`.

### 6.5 Upload object lifecycle (internal, for reviewers)

- Staging objects `staging/{upload_id}/{offset}` exist only while an upload is receiving. They are deleted at completion; Sprint 1 adds the sweeper.
- After completion the bucket holds exactly one new object, `originals/{random}` (IT-00-06).
- No media URL goes to the browser in Sprint 0. The worker reads the original through a presigned GET with a TTL of 15 min or less (NFR-055), issued for the object store's internal endpoint.

## 7. Status codes per route (summary for the BOLA matrix)

| Route | Owner | Other user | Missing | Anonymous |
|---|---|---|---|---|
| `GET /matches/{id}` | 200 | 404 | 404 | 401 |
| `GET /matches/{id}/media` | 200 / 404 (not probed) | 404 | 404 | 401 |
| `POST /matches/{id}/uploads` | 201 / 409 | 404 | 404 | 401 |
| `HEAD /uploads/{id}` | 200 | 404 | 404 | 401 |
| `PATCH /uploads/{id}` | 204 / 409 / … | 404 | 404 | 401 |

Routes without a path ID: `GET /healthz`, `GET /readyz`, `GET /dev/users`, `POST /dev/sign-in`, `POST /auth/sign-out`, `GET /me`, `POST /matches`, `GET /matches`, `OPTIONS /uploads`.

## 8. Client notes (ST-010)

- Use `fetch` with `credentials: "same-origin"` against `/api/...`. Never store the session token; it is `HttpOnly`.
- The service worker must not cache `/api/*` responses or media (NFR-067; `web/e2e/security-headers.spec.ts`).
- tus-js-client may store the upload URL in `localStorage` to resume after a reload. That URL holds no credential: access still needs the cookie, and it contains no personal data (ASVS 14.3.3 allows it; judgment). Clear the stored URLs on sign-out (ASVS 14.3.1).
- Render `title` as text only (ASVS 3.2.2).
- The FE must confirm in ST-010 that the Next.js `/api` rewrite streams a PATCH body of at least 64 MiB without buffering problems. If it cannot, raise it with the principal-engineer. The fallback is direct cross-origin calls with a CORS allowlist, which would amend §1 and §2.

## 9. Configuration this contract adds (SRE to add to `infra/env.example`)

| Variable | Default | Notes |
|---|---|---|
| `UPLOAD_MAX_BYTES` | `10000000000` | NFR-053 provisional cap |
| `UPLOAD_MAX_CHUNK_BYTES` | `67108864` | Upper bound for one PATCH body |
| `UPLOAD_PART_MIN_BYTES` | `5242880` | S3 multipart minimum for every part but the last |
| `API_PUBLIC_PATH_PREFIX` | `""` | `/api` behind the web rewrite or ingress; empty in tests |
| `ALLOWED_ORIGINS` | unset | Comma-separated; required in `staging`/`prod` |

Existing: `APP_ENV`, `DEV_IDENTITY_ENABLED`, `DATABASE_URL`, `S3_*`, `OTEL_*`. `PUBLIC_API_BASE_URL` stays for server-side web code only.
