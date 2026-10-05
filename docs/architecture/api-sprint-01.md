# API contract: Sprint 1 (sign-in, match setup, resumable and validated upload)

- **Status:** Accepted for Sprint 1 (principal-engineer, 2026-10-05). Changes go through a PR on this file reviewed by BE, FE and QA; test seams in `backend/tests/support/contract.py` change in the same PR (ADR 0012).
- **Owner:** principal-engineer. **Security:** `docs/security/threat-model-sprint-01.md` (controls there are acceptance criteria of the named stories, ADR 0022 rule 4).
- **Stories:** ST-013, ST-014, ST-016, ST-017, ST-018 (and ST-024 metric names, §10).
- **Builds on:** `api-sprint-00.md` (amended 2026-10-05). Everything there still holds unless a section here says "replaces". Decisions: ADR 0011 (tus), ADR 0019 (chunks), ADR 0024 (participants), ADR 0025 (magic link).
- **Purpose:** BE and FE build in parallel against this file. Every request, response, status and code below is final for Sprint 1; anything marked "(judgment)" may be tuned by config, not by shape.

## 1. Convention changes

### 1.1 Error body: `fields` on 422, `retry_at` on 429 (replaces api-sprint-00 §3 "no per-field details")

```json
{"error": {"code": "validation_failed", "message": "Some of the information is not valid.",
           "support_ref": "ref_5c1e0f3a9b7d4e21",
           "fields": [{"field": "participants.side_b", "code": "side_needs_two_players"},
                      {"field": "participants.me", "code": "choose_one_me"}]}}
```

- `fields` appears **only** on 422 and is always an array (possibly empty). `field` is a path from the route's closed list (§5.3, §2.1) or `null`; `code` is from the closed table in §4.2. **No input value is ever echoed**, including unknown field names: an unknown body key gives `{"field": null, "code": "unknown_field"}`. Order follows the form order in §5.3.
- `retry_at` appears **only** on 429: RFC 3339 UTC, or `null` when waiting does not help (quota). A 429 with a non-null `retry_at` also sends `Retry-After: <seconds>`.
- The FE maps `code` (and field `code`) to the copy in `docs/design/flows-sprint-01.md`; server `message` stays generic.
- This changes the key set pinned by the error-body regression suite: QA adds a row to `docs/sprints/01/test-change-requests.md` and owns the test change.

### 1.2 Unchanged

Root base path behind `/api` (dev rewrite, prod ingress), `application/json` without `charset`, UUIDv4 IDs with 404 for malformed IDs, closed request schemas, security headers, `Cache-Control: no-store` (api-sprint-00 §1, amended 2026-10-05).

## 2. Authentication: magic link (ST-013, ST-014; ADR 0025)

### 2.1 `POST /auth/links`: request a sign-in link

No session needed. Rate-limited (§2.4).

```
Request:  {"email": "ivy@example.com"}                       // closed schema
202 Accepted   (no body)
```

| Status | When |
|---|---|
| 202 | Any well-formed address, **whether or not an account exists** (no oracle, D-4). A `send_sign_in_link` job is queued; the response does not wait for SMTP |
| 422 `validation_failed` | `fields: [{"field": "email", "code": "email_invalid"}]`. Well-formed = after trim, 3-254 characters, exactly one `@`, no whitespace, a dot in the domain part. Normalised to lowercase for lookup (judgment) |
| 429 `rate_limited` | §2.4; `retry_at` set |
| 403 `forbidden_origin` | `Origin` not allowed (api-sprint-00 §2) |

Email (plain text and HTML, no remote images or tracking): subject "Your sign-in link", body with the link `{PUBLIC_WEB_ORIGIN}/auth/callback#token=<token>` and "It works once and expires in 15 minutes. If you did not ask for it, ignore this email." Dev: Mailpit.

### 2.2 `POST /auth/exchange`: turn a link into a session

The web page `/auth/callback` (A-03) reads `location.hash`, calls `history.replaceState(null, "", "/auth/callback")` **before** the request, then posts the token. The token is never stored on the device.

```
Request:  {"token": "<43 chars base64url>"}                  // closed schema
200 OK
Set-Cookie: __Host-racket_session=…; Path=/; Secure; HttpOnly; SameSite=Lax   (test env: racket_session, no Secure)
{"account": {"id": "6f0c…", "display_name": null}, "new_account": true}
```

| Status | When |
|---|---|
| 200 | Valid, unused, unexpired link. Marks it used and creates the session in one transaction. Creates the account on first use (`new_account: true` → F-01; `false` → M-01). Rotates any session cookie already presented (ASVS 7.2.4) |
| 401 `link_expired` | Unknown, already used, or older than 15 minutes: **one** code and body for all three (D-4). The FE shows A-04 with an **empty** email field (never pre-filled from the token or URL) |
| 422 `validation_failed` | Body not matching the schema; `token` not 43 base64url characters |
| 429 `rate_limited` | §2.4 |

### 2.3 Session, sign-out, `/me`

- Cookie and token scheme: api-sprint-00 §2, unchanged. **Lifetimes:** absolute 30 days, inactivity 7 days, at most 10 concurrent sessions per account (the oldest is deleted). An expired session behaves as no session (401).
- `POST /auth/sign-out`: unchanged (204, idempotent), plus the response header `Clear-Site-Data: "cache"`. The client also clears `localStorage`, `sessionStorage`, IndexedDB and every Cache Storage entry holding authenticated data, and unregisters nothing else (the app shell stays for the offline A-01 banner) (FR-011, NFR-067).
- `GET /me`: `{"id": "…", "display_name": "Ivy" | null}`. `display_name` is `null` for magic-link accounts until a later story lets the user set it; the FE shows "Your account". (Shape change: `display_name` becomes nullable.)
- `POST /dev/sign-in`, `GET /dev/users`: unchanged, dev/test only.

### 2.4 Rate limits (NFR-023 partial; ASVS 6.3.1, 6.6.3)

Fixed-window counters in Postgres (`rate_limits(key, window_start, count)`); no new infrastructure.

| Key | Limit (config) | Applies to |
|---|---|---|
| `link:email:<email_key>` | 5 per 600 s | `POST /auth/links`, for every address (known or not) |
| `link:ip:<client ip>` | 20 per 600 s | `POST /auth/links` |
| `exchange:ip:<client ip>` | 30 per 600 s | `POST /auth/exchange` |
| `upload:create:<account_id>` | 10 per 3600 s | `POST /matches/{id}/uploads` (§6.3) |

Client IP = the address `TRUSTED_PROXY_HOPS` hops from the right of `X-Forwarded-For`, or the socket peer when it is 0. Never the left-most value.

## 3. (reserved)

## 4. Codes added in Sprint 1

### 4.1 Error codes (same body as api-sprint-00 §3; fixed messages)

| HTTP | `code` | `message` | Routes |
|---|---|---|---|
| 400 | `checksum_invalid` | "The upload checksum is not valid." | PATCH: malformed `Upload-Checksum` or unsupported algorithm |
| 401 | `link_expired` | "This sign-in link can no longer be used." | `/auth/exchange` |
| 410 | `upload_expired` | "This upload has expired. Please start again." | HEAD (no body), PATCH |
| 413 | `video_too_large` | "This video is larger than allowed." | upload creation (`Upload-Length` above the cap) |
| 415 | `not_a_video` | "This file is not a video we can read." | PATCH at offset 0 |
| 429 | `upload_quota_exceeded` | "You have too many unfinished uploads." | upload creation; `retry_at: null` |
| 460 | `checksum_mismatch` | "Part of the upload was damaged. Please send it again." | PATCH (tus checksum extension status) |

`payload_too_large` (413) stays for a PATCH body above `UPLOAD_MAX_CHUNK_BYTES` or past `Upload-Length`. `rate_limited` (429) is now live.

### 4.2 Field codes (`fields[].code`, closed)

`email_invalid`, `format_required`, `format_invalid`, `scoring_system_invalid`, `scoring_system_unavailable`, `played_on_invalid`, `played_on_in_future`, `title_invalid`, `side_needs_two_players`, `side_needs_one_player`, `invalid_slot`, `choose_one_me`, `nickname_required`, `nickname_too_long`, `nickname_invalid`, `participants_without_format`, `unknown_field`, `invalid` (any other schema error on a known field).

## 5. Matches (ST-016; ADR 0024)

### 5.1 `POST /matches` (extends api-sprint-00 §5.2)

```json
{
  "format": "doubles",
  "scoring_system": "side_out",
  "played_on": "2026-10-03",
  "participants": [
    {"slot": "A1", "nickname": "Ivy", "is_me": true},
    {"slot": "A2", "nickname": "Dana", "is_me": false},
    {"slot": "B1", "nickname": "Carlos", "is_me": false},
    {"slot": "B2", "nickname": "Sam", "is_me": false}
  ]
}
```

| Field | Required | Rule |
|---|---|---|
| `format` | yes | `"doubles"` \| `"singles"` |
| `scoring_system` | no (default `"side_out"`) | `"side_out"`. `"rally"` → 422 `scoring_system_unavailable` (FR-043). Anything else → `scoring_system_invalid` |
| `played_on` | no (default: today in UTC) | `YYYY-MM-DD`, from 2000-01-01 to **UTC today + 1 day** (a user east of UTC can be a day ahead; the FE enforces "today or earlier" in local time, so the Gherkin "tomorrow" case is an FE/E2E check, and the server IT uses today + 2) |
| `participants` | no (the Sprint 0 client and tests omit it) | When present: the full set for the format, validated as one unit (ADR 0024). The Sprint 1 web client always sends it |
| `title` | no | 1-120 characters after trim. Default: `"{Doubles\|Singles} · {d Mon yyyy}"` from `played_on`, e.g. `"Doubles · 3 Oct 2026"` (flows D-2) |

`rules_version` is set by the server to `"PROVISIONAL-UNVERIFIED"` (the only preset, ADR 0009) and is not accepted from the client. Success: **201**, the match (§5.2), `Location: /matches/{id}`.

### 5.2 Match representation (adds to api-sprint-00 §5.1)

```json
{
  "id": "0b8f…", "title": "Doubles · 3 Oct 2026", "format": "doubles", "status": "uploading",
  "scoring_system": "side_out", "rules_version": "PROVISIONAL-UNVERIFIED", "played_on": "2026-10-03",
  "participants": [{"slot": "A1", "nickname": "Ivy", "is_me": true}, …],
  "upload": {
    "state": "receiving", "offset": 2040109465, "length": 3187671040,
    "expires_at": "2026-10-06T09:12:44Z", "resume_url": "/api/uploads/5d0c…",
    "file_name": "Sat doubles.mp4", "file_last_modified_ms": 1759480000000,
    "head_sha256": "9f86d081…"
  },
  "rejection": null,
  "media": null, "created_at": "…", "updated_at": "…"
}
```

| Field | Rule |
|---|---|
| `participants` | slot order `A1, A2, B1, B2`; `[]` when none were given. Nicknames rendered as text only |
| `upload` | **The resume source of truth (flows D-3, U-04).** Present while an upload session exists and is not complete: `state` `"receiving"` or `"expired"` (expired sessions show until the Sprint 2 sweeper removes them). `null` otherwise. `resume_url` uses `API_PUBLIC_PATH_PREFIX` like the tus `Location` (this replaces the Sprint 0 "upload IDs are never returned" rule, for the upload's owner only). `file_name`, `file_last_modified_ms` and `head_sha256` echo the creation metadata (§6.3) or are `null` |
| `rejection` | The last refusal of a file for this match: `{"code": "not_a_video" \| "too_large" \| "too_long" \| "unsupported_video", "at": "<RFC 3339>"}`, else `null`. Cleared when a new upload is created. With a rejection the match is back to `status: "awaiting_upload"` ("No video yet", §14.3.6) |
| `status` | Unchanged values. `uploading` only while `upload.state == "receiving"` |

### 5.3 Validation paths and order (`fields[].field`)

`format`, `scoring_system`, `played_on`, `title`, `participants` (`invalid_slot`, `participants_without_format`), `participants.side_a`, `participants.side_b` (`side_needs_two_players` / `side_needs_one_player`), `participants.<slot>.nickname` (`nickname_required`, `nickname_too_long` above 30 characters, `nickname_invalid` for control characters), `participants.me` (`choose_one_me` when zero or more than one `is_me`). All failures are reported together, in this order.

Gherkin mapping (§7.3): "Each side needs two players" = `side_needs_two_players`; "Each side needs one player" = `side_needs_one_player`; "Choose one player as \"me\"" = `choose_one_me`.

### 5.4 Contact-detail warning (client and domain share one rule)

A nickname **looks like contact details** when, after trim, it matches `^[^@\s]+@[^@\s]+\.[^@\s]+$` (email) or contains 7 or more digits once spaces, `-`, `.`, `(`, `)` and a leading `+` are removed (phone) (judgment). The FE shows the warning and lets the user continue (§14.3.4). The server **accepts** such nicknames; `Participants.looks_like_contact_details` implements the same rule for tests and later analytics redaction.

## 6. Uploads: checksum, expiration, validation (ST-017, ST-018)

### 6.1 `GET /upload-policy` (new; authenticated)

```json
{"max_bytes": 10000000000, "max_duration_ms": 9000000,
 "containers": ["mp4", "mov"], "video_codecs": ["h264", "hevc"],
 "chunk_min_bytes": 5242880, "chunk_max_bytes": 8388608,
 "checksum_algorithms": ["sha256", "sha1"], "expires_after_s": 86400}
```

All values come from configuration (§8); the caps are provisional until ST-025 (R-05, D-5). The FE builds its copy from them ("10 GB", "2 hours 30 minutes") and adapts chunk size between `chunk_min_bytes` and `chunk_max_bytes` (NFR-016; ADR 0019 amendment). Status: 200, 401.

### 6.2 `OPTIONS /uploads`

```
204  Tus-Resumable: 1.0.0   Tus-Version: 1.0.0
     Tus-Extension: creation,checksum,expiration
     Tus-Checksum-Algorithm: sha256,sha1
     Tus-Max-Size: <UPLOAD_MAX_BYTES>
```

### 6.3 `POST /matches/{match_id}/uploads`: creation (delta to api-sprint-00 §6.2)

Checks, in order, after the Sprint 0 header checks (`Tus-Resumable`, `Upload-Length` syntax). The order matches `UploadService.create` (`racket.video_ingest.service`); amended 2026-10-05 for PE-R1-01 / PE-R2-01:

| # | Check | Result |
|---|---|---|
| 1 | session; match exists and is yours | 401; 404 |
| 2 | an **unexpired** session already exists for the match | 409 `conflict`. An expired one is marked expired and replaced (no 409). Runs before the size cap so a 413 never records a refusal on a match with a live upload or its video (PE-R1-01) |
| 3 | `Upload-Length` > `UPLOAD_MAX_BYTES` | **413 `video_too_large`**, before any byte is stored; `rejection` set to `too_large` (NFR-053) |
| 4 | `Upload-Metadata` | Sprint 1 reads only `filename` (decoded UTF-8, control characters removed, cut to 255 bytes), `last_modified` (decimal ms) and `head_sha256` (64 lowercase hex: SHA-256 of the first min(1 MiB, length) bytes). Malformed `head_sha256` or `last_modified` → 400. Other keys are ignored and not stored. Checked before quota and rate, so a malformed request does not spend a creation-rate slot |
| 5 | the account has ≥ `UPLOAD_MAX_OPEN_SESSIONS` (3) receiving sessions, or their declared bytes plus this one exceed `UPLOAD_MAX_OPEN_BYTES` (30 GB) | 429 `upload_quota_exceeded`, `retry_at: null` (T-UP-6; ASVS 5.2.4) |
| 6 | creation rate (§2.4) | 429 `rate_limited`. Counted only for requests that passed checks 1-5 |

Success: **201**, `Location`, `Tus-Resumable`, and **`Upload-Expires: <HTTP-date>`** (e.g. `Tue, 06 Oct 2026 09:12:44 GMT`). The stored file name never reaches object keys, logs, metrics or tool arguments [AQS/SEC-02 5.3.2]; it is deleted when the session completes or expires.

### 6.4 Expiration

`expires_at` = 24 h after the last accepted chunk (or creation), capped at 72 h after creation (ADR 0006 "abandoned uploads freed after 24 h"; cap is judgment). HEAD, PATCH (2xx) and creation responses carry `Upload-Expires`. After expiry the owner gets **410 `upload_expired`** on HEAD (no body) and PATCH; another user still gets 404 (ownership is checked first). Sprint 1 enforces expiry lazily; the sweeper that deletes staged bytes is ST-038 (Sprint 2).

### 6.5 `PATCH /uploads/{upload_id}` (delta to api-sprint-00 §6.4)

Optional request header `Upload-Checksum: <algorithm> <base64 digest of this request's body>` (tus checksum extension). The FE sends `sha256` on every chunk.

| # (Sprint 0 order) | New check | Status |
|---|---|---|
| after 3 (exists, yours) | session expired | 410 `upload_expired` |
| after 6 (`Content-Length`) | `Upload-Checksum` malformed, or algorithm not in `sha256, sha1` | 400 `checksum_invalid` |
| after the body is fully read, before anything is committed | digest differs | **460 `checksum_mismatch`**; nothing stored, offset unchanged (IT-01-06) |
| same point, only when `Upload-Offset` is 0 and `Content-Length` > 0 | the body must hold ≥ min(12, `Upload-Length`) bytes; bytes 4-7 are `ftyp`, or a QuickTime top-level atom (`moov`, `mdat`, `wide`, `free`, `skip`) | otherwise **415 `not_a_video`**: the session is deleted, nothing is kept, `rejection` = `not_a_video`, the match returns to `awaiting_upload`, no job (NFR-053, NFR-060) |
| same point, offset 0 with `head_sha256` stored | SHA-256 of the first min(1 MiB, length) bytes equals `head_sha256` (the 5 MiB minimum chunk always covers it) | otherwise 460 `checksum_mismatch` |

Success: 204 with `Upload-Offset`, `Upload-Expires`, `Tus-Resumable`. All other Sprint 0 rules (atomic PATCH, 409 cases, completion transaction) are unchanged.

### 6.6 After completion: content validation by probe (ST-018)

The existing probe job (ST-009) is the content check; no other job runs in Sprint 1. After ffprobe returns facts, `UploadPolicy.check(facts)` (pure, `racket.video_ingest.domain`) decides:

| Condition | Outcome |
|---|---|
| ffprobe cannot read the file (parse failure, timeout, sandbox kill) | `status: "probe_failed"` as in Sprint 0; the FE shows "This file is not a video we can read" |
| container not MP4/MOV, or video codec not H.264/HEVC, or width × height > `UPLOAD_MAX_FRAME_PIXELS` (ASVS 5.2.6) | `rejection` = `unsupported_video` |
| duration > `UPLOAD_MAX_DURATION_MS` | `rejection` = `too_long` |
| otherwise | facts committed; `status: "video_received"` |

On a rejection: in one transaction the facts are not stored, the match returns to `awaiting_upload` with `rejection` set (`Match.reject_video`, via `racket.matches.public`); then the original object is deleted (idempotent, retried by the job runtime). IT-01-09's "no job created" means no job beyond this probe.

The client also pre-checks size (`File.size`) and, when the browser can read it, duration (`<video>` metadata) before creating the upload; the server stays authoritative.

## 7. Status per route (BOLA matrix additions)

| Route | Owner | Other user | Missing | Anonymous |
|---|---|---|---|---|
| `HEAD /uploads/{id}` | 200 / 410 | 404 | 404 | 401 |
| `PATCH /uploads/{id}` | 204 / 409 / 410 / 415 / 460 / … | 404 | 404 | 401 |

No new route takes a path ID in Sprint 1. New routes without an ID: `POST /auth/links`, `POST /auth/exchange`, `GET /upload-policy`. `DELETE /uploads/{id}` (tus termination, "Cancel upload") is **Sprint 2 (ST-038)**; in Sprint 1 the FE hides "Cancel upload".

## 8. Configuration added (SRE adds to `infra/env.example`)

| Variable | Default | Notes |
|---|---|---|
| `PUBLIC_WEB_ORIGIN` | none; required unless `APP_ENV=test` | Base of sign-in links; never taken from `Host` |
| `MAIL_SMTP_URL` / `MAIL_FROM` | `smtp://mailpit:1025` in dev / `no-reply@localhost` | Prod provider: Sprint 4 ADR |
| `AUTH_EMAIL_KEY` | none; required in `staging`/`prod` (secret) | HMAC key for `email_key` (rate limits, logs) |
| `MAGIC_LINK_TTL_SECONDS` | `900` | FR-001 |
| `SESSION_ABSOLUTE_SECONDS` / `SESSION_IDLE_SECONDS` / `SESSION_MAX_PER_ACCOUNT` | `2592000` / `604800` / `10` | ADR 0025 |
| `AUTH_LINK_LIMIT_PER_EMAIL` / `AUTH_LINK_LIMIT_PER_IP` / `AUTH_EXCHANGE_LIMIT_PER_IP` / `AUTH_WINDOW_SECONDS` | `5` / `20` / `30` / `600` | §2.4 |
| `TRUSTED_PROXY_HOPS` | `0` (`1` behind the dev rewrite or the ingress) | §2.4 |
| `UPLOAD_MAX_DURATION_MS` | `9000000` | 150 min, provisional (K12, R-05) |
| `UPLOAD_MAX_FRAME_PIXELS` | `8294400` | 3840 × 2160 (judgment) |
| `UPLOAD_CLIENT_CHUNK_MIN_BYTES` / `UPLOAD_CLIENT_CHUNK_MAX_BYTES` | `5242880` / `8388608` (staging/prod: `52428800`) | ADR 0019 amendment |
| `UPLOAD_EXPIRY_SECONDS` / `UPLOAD_EXPIRY_MAX_SECONDS` | `86400` / `259200` | §6.4 |
| `UPLOAD_MAX_OPEN_SESSIONS` / `UPLOAD_MAX_OPEN_BYTES` / `UPLOAD_CREATE_LIMIT_PER_HOUR` | `3` / `30000000000` / `10` | §6.3 |

## 9. Routed work outside this contract (ADR 0022)

| Item | Owner | Test owner |
|---|---|---|
| R3-04 / QA-R3-10: add `Tus-Resumable: 1.0.0` to 405 and global-fallback 500 responses on tus paths (edge middleware by path prefix) | senior-backend-engineer | senior-qa-engineer (pin `DELETE /uploads/{uuid}` → 405 with the header) |
| Error-body key set gains `fields` (422) and `retry_at` (429) | senior-backend-engineer | senior-qa-engineer (test-change row) |
| `GET /me` `display_name` becomes nullable | senior-backend-engineer | senior-qa-engineer |
| `CHUNK_SIZE` constant becomes the fallback; chunk bounds from `/upload-policy` | senior-frontend-engineer | senior-qa-engineer (test-change row for `tus-policy.test.ts`) |
| Ingress body limit ≥ `UPLOAD_MAX_CHUNK_BYTES`; Mailpit service; new env vars | sre-devops-engineer | — |

## 10. Metric names for the SLIs (ST-024; proposal, SRE confirms)

OpenTelemetry instruments [AQS/OPS-07], no personal data in attributes:

- `racket.upload.sessions` (counter), attribute `event` ∈ `created`, `completed`, `expired`, `rejected`; `rejected` also has `reason` ∈ the `rejection` codes. **Upload-completion SLI (NFR-042)** = `completed / (created − rejected)` over the window; user cancellations are subtracted once `DELETE` ships (Sprint 2).
- `racket.upload.chunk.bytes` (histogram) and `racket.upload.chunk.duration` (histogram, s) for NFR-016.
- **Availability SLI (NFR-041)** from the standard `http.server.request.duration` with `http.response.status_code`: non-5xx / all, excluding 429.
- `racket.auth.links` (counter), attribute `outcome` ∈ `requested`, `rate_limited`, `exchanged`, `refused`.
