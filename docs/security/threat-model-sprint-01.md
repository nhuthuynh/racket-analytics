# Threat model, Sprint 1 delta: magic-link sign-in and upload validation

- **Status:** v1 delta to [`threat-model-v0.md`](threat-model-v0.md) (which still holds). Closes Sprint 1 DoR item P8 for ST-013, ST-014, ST-017 and ST-018.
- **Date:** 2026-10-05
- **Authors:** security-privacy-engineer (threats, controls, findings) with principal-engineer (architecture). Written into `docs/` by the principal-engineer session; the security role is read-only.
- **Method:** STRIDE per element plus abuse cases, as in v0 (judgment). ASVS item numbers are from `asvs-l2-checklist.md` (fetched 2026-10-03).
- **Contracts reviewed:** `docs/architecture/api-sprint-01.md`, ADR 0025 (magic link), ADR 0024 (participants), ADR 0019 (chunks, amended).
- **Rule (ADR 0022 rule 4):** every control below that names a story is an **acceptance criterion of that story** and needs a red test first. The "Test" column names the test the story must add; QA owns test files.
- **Legal:** obligations remain **unverified** [AQS G3.5]. The PO named the US and Australia as beta jurisdictions (`docs/requirements/po-input-2026-10-05.md`); the legal review before any real-user beta (NFR-070) must cover both. Nothing here asserts law.

## 1. New or changed assets

| Asset | Class | Where | Notes |
|---|---|---|---|
| Account email address | **Medium-High** (contact data, account recovery) | **Today (`17c850d`):** only in `sign_in_requests` until the mail job sends the link; `accounts` holds no address (identity is the 64-bit `email_key`, SEC-R3-S1-01). **Target (ADR 0032, ST-013b):** `accounts.email` (unique identity) and `sign_in_links.email` until use or expiry | Never logged; logs use `email_key` (HMAC, ADR 0025) |
| Sign-in link token | **High** (credential, 15 min) | email body; URL fragment for milliseconds; Postgres stores SHA-256 only | Single use |
| `AUTH_EMAIL_KEY` | **High** (secret) | environment / secret store | **Today:** also the account-identity key, so rotating or losing it orphans every account and a 64-bit collision merges two people (SEC-R3-S1-01). Do not rotate before ST-013b. **After ADR 0032 / ST-013b:** rotating it resets rate-limit windows and log correlation only |
| Participant nicknames (third parties) | Medium | `match_participants` | ADR 0024; deleted with the match |
| Upload file name | Medium | `upload_sessions` while open (**changed**: v0 said "not stored") | Display only for resume (D-3); deleted at completion or expiry |
| `head_sha256` of the first MiB | Low | `upload_sessions` while open | Not reversible to content in practice (judgment) |
| Rate-limit counters | Low | `rate_limits` | Keys hold `email_key` and IP addresses; keep ≤ 24 h (judgment) |

## 2. Magic-link sign-in and sessions (ST-013, ST-014)

New actors and abuse cases: **A7** email-bomber (makes us mail a victim repeatedly); **A8** mailbox-adjacent attacker (sees forwarded or previewed links, a shared device's history); **A9** credential-stuffing/guessing bot against `/auth/exchange`; A2 now probes for account existence (AC16) and poisons links via `Host` (AC17).

| ID | STRIDE | Threat | Control (acceptance criterion) | ASVS / source | Story | Test | Status |
|---|---|---|---|---|---|---|---|
| T-ML-1 | S | Guessing a valid token | 256-bit CSPRNG token; SHA-256 at rest; 30 exchanges / 10 min / IP | 6.5.3, 6.5.4, 6.6.3 | ST-013 | unit: token length and alphabet; IT-01-02 variant for `/auth/exchange` 429 | C (designed) |
| T-ML-2 | S | Replay of a used or old link (history, forwarded mail) | Single use, enforced by a conditional `UPDATE … WHERE used_at IS NULL AND expires_at > now()`; 15 min TTL with an injected clock | 6.5.1, 6.5.5 | ST-013 | IT-01-01 (reuse fails); unit with injected clock (sprint-01 §5 `MagicLinkToken` 1-2) | C |
| T-ML-3 | S/T | Two concurrent exchanges of one token both succeed | Same conditional update; exactly one row updated wins, the other gets 401 | 6.5.1; 2.3.4 (fetched) | ST-013 | integration: two parallel exchanges → one 200, one 401 | C |
| T-ML-4 | I | Token leaks through URL: access logs, `Referer`, proxies, analytics | Token in the **fragment**; `replaceState` before the POST; A-03 loads no external asset; `Referrer-Policy: no-referrer` | [AQS/SEC-05 14.2.1]; NFR-055 | ST-013 | E2E-01-01 (address bar clean); log scan finds no 43-char token | C |
| T-ML-5 | S | Mail scanners prefetch the link and burn it | GET of `/auth/callback` is a static page; only POST spends the token | ADR 0025 (judgment) | ST-013 | E2E: GET the link URL twice, then exchange → 200 | C |
| T-ML-6 | I | Account-existence oracle (AC16) via status, body, timing or the rate limit | 202 for every well-formed address; email sent by a queued job; per-email limit applies to unknown addresses; exchange errors are one code | 6.3.1; flows D-4 | ST-013 | §14.3.1 scenario; integration: known vs unknown address → identical status, headers and body | C |
| T-ML-7 | T | Link poisoning via `Host` / `X-Forwarded-Host` (AC17): the email points to an attacker origin | Link base only from `PUBLIC_WEB_ORIGIN`; the API refuses to start without it outside `test` | 13.4.x config hygiene (judgment) | ST-013 | unit: request with `Host: evil.example` → link uses the configured origin | C |
| T-ML-8 | D | Email bombing a victim; sender reputation and cost (A7) | 5 links / 10 min per address; 20 / 10 min per IP; IP from `TRUSTED_PROXY_HOPS`, never the left-most `X-Forwarded-For` | 2.4.1, 6.3.1 [AQS/SEC-07]; NFR-023 | ST-013 | IT-01-02; unit: spoofed `X-Forwarded-For` does not reset the IP limit | C |
| T-ML-9 | R/I | Auth events not attributable, or logs contain the address or token | `auth.*` events with UTC, `request_id`, `account_id` or `email_key`; never email, token or hash | 16.2.1, 16.3.1, 16.2.5 [AQS/SEC-04]; NFR-057, NFR-069 | ST-013 | IT-01-03 (log scan for `@` and token patterns) | C |
| T-ML-10 | S | Session fixation or a session surviving re-sign-in | New token on every exchange; presented session deleted | 7.2.4 | ST-013 | integration: old cookie invalid after exchange | C |
| T-ML-11 | I/E | Long-lived sessions on shared devices | 30 d absolute, 7 d idle, max 10 per account; sign-out deletes server-side and sends `Clear-Site-Data: "cache"`; client clears storage and caches | 7.1.1, 7.1.2, 7.3.1, 7.3.2, 7.4.1; 14.3.1 [AQS/SEC-05]; NFR-067 | ST-013, ST-014 | unit with injected clock (idle, absolute); IT-01-04; sign-out E2E (§7.1 shared device) | C |
| T-ML-12 | S/E | CSRF on `/auth/exchange` logs the victim into the attacker's account (login CSRF) | POST with JSON body (non-simple), `Origin` allowlist in staging/prod; token must be in the body | 3.5.1, 3.5.3 | ST-013 | integration: foreign `Origin` → 403 `forbidden_origin`, no `Set-Cookie`, on `POST /auth/links` and `POST /auth/exchange` with `ALLOWED_ORIGINS` set (`test_it_01_01_magic_link.py::test_t_ml_12_a_foreign_origin_cannot_request_a_link_or_sign_in`, SEC-R1-S1-01) | C |
| T-ML-13 | S | Single-factor authentication at L2 | Email link is one factor; passkeys are backlog | **6.3.3** | — | — | **O: residual risk. PO must accept or reject before any real-user beta** (blockers.md; options and recommendation in ADR 0031, Proposed, awaiting the PO) |
| T-ML-14 | I | The email address is used as a username in URLs or the UI of others | The address is never in a URL, never returned except to its owner (not even in `/me` in Sprint 1) | 14.2.1 [AQS/SEC-05] | ST-013 | response allowlist test (`/me` keys) | C |

## 3. Upload validation and resumable upload (ST-017, ST-018)

| ID | STRIDE | Threat | Control (acceptance criterion) | ASVS / source | Story | Test | Status |
|---|---|---|---|---|---|---|---|
| T-UV-1 | T | Non-video content stored under a video name (AC10) | Magic bytes on the offset-0 PATCH (`ftyp` / QuickTime atoms) → 415 `not_a_video`, session deleted, nothing kept; never the extension or `Content-Type`; then ffprobe with the MP4/MOV demuxer allowlist (ADR 0021) | 5.2.2 [AQS/SEC-02]; NFR-053 | ST-018 | IT-01-09 (PDF and executable renamed) **with a positive control**: a real MP4 fixture passes the same path (retro L4) | C |
| T-UV-2 | D | Oversized declared length fills storage | 413 `video_too_large` from `Upload-Length` before any byte or object is created | 5.2.1 [AQS/SEC-02]; NFR-053 | ST-018 | IT-01-09 (12 GB declared) + assertion that the bucket gained no object | C |
| T-UV-3 | D | Over-long or huge-frame video (pixel flood) costs worker time later | Probe facts checked by `UploadPolicy`: duration ≤ cap, frame pixels ≤ cap, codec H.264/HEVC; rejection deletes the original; no job beyond the probe | 5.2.1, 5.2.6 (L3 adopted) [AQS/SEC-02]; NFR-060 | ST-018 | IT-01-09 (4-hour fixture header); unit table for `UploadPolicy` incl. boundaries (cap − 1, cap, cap + 1) | C |
| T-UV-4 | E | Crafted container exploits the demuxer | Unchanged from v0 T-WS-1/2 (sandbox, protocol and format allowlists) | 13.2.4 [AQS/SEC-06]; NFR-054 | ST-018 | IT-01-10 with a positive control (a valid file probes in the same sandbox) | P (as v0) |
| T-UV-5 | T | A corrupted chunk is stored | `Upload-Checksum` (sha256/sha1) verified before commit → 460, offset unchanged | [AQS/STACK-06] | ST-017 | IT-01-06; property test for the `Upload-Checksum` parser (retro L4: parsers of untrusted headers) | C |
| T-UV-6 | T | A different file is resumed onto an existing upload | `head_sha256` stored at creation and verified on the offset-0 chunk; the client compares name, size, last-modified and `head_sha256` before resuming | ADR 0011 (judgment) | ST-017 | §14.3.5 "different file" scenario; integration: offset-0 chunk with another head → 460 | C |
| T-UV-7 | D | Abandoned sessions hold storage forever; many open sessions | Expiry 24 h sliding / 72 h cap, enforced on HEAD/PATCH (410); ≤ 3 open sessions and ≤ 30 GB declared per account; 10 creations / hour | 2.4.1 [AQS/SEC-07]; 5.2.4 [AQS/SEC-02]; 14.2.7; ADR 0006 | ST-017 | IT-01-07; integration: 4th open session → 429 `upload_quota_exceeded` | **P**: staged bytes of expired sessions stay until the ST-038 sweeper (Sprint 2). Accepted for dev only (judgment); **Should-fix before any non-dev deployment** |
| T-UV-8 | E/I | Carlos resumes, probes or reads Ivy's upload (AC1) via the now-returned `resume_url` | Ownership check first on HEAD/PATCH; 404 identical to missing; 410 only for the owner; `upload` object only in the owner's match read model | 8.2.2, 8.3.1 [AQS/SEC-03]; [AQS/SEC-09] | ST-017 | BOLA matrix incl. an **expired** upload as Carlos → 404 (not 410); §14.3.5 Carlos scenario | C |
| T-UV-9 | I | The stored file name leaks into object keys, logs, metrics or ffprobe arguments | Display-only field; keys from `ObjectKeyPolicy`; not a metric or log attribute; deleted at completion or expiry | 5.3.2 [AQS/SEC-02]; 16.2.5 [AQS/SEC-04] | ST-017 | unit: `ObjectKeyPolicy` ignores metadata; log scan for the fixture's file name | C |
| T-UV-10 | I | Stored XSS through file name or nickname | Rendered as text only (React escaping; no `dangerouslySetInnerHTML`); CSP with nonces (ADR 0018) | 3.2.2 | ST-016, ST-017 | E2E: nickname and file name `<img src=x onerror=…>` render as text | C |

## 4. Match setup (ST-016)

| ID | STRIDE | Threat | Control | ASVS / source | Test | Status |
|---|---|---|---|---|---|---|
| T-MS-1 | E | Mass assignment of `rules_version`, `owner_id` or `status` on `POST /matches` | Closed schema; `rules_version` set by the server | 8.2.3 [AQS/SEC-03]; NFR-052 | unknown-field test incl. `rules_version` → 422 `unknown_field` | C |
| T-MS-2 | I | Contact details of third parties stored as nicknames | Helper text, client warning, shared predicate (ADR 0024); 30-character cap | NFR-063 (judgment) | §14.3.4 scenario | P (cannot be prevented, only discouraged) |
| T-MS-3 | I | Validation errors echo input (reflected content, log injection) | `fields` carry paths and codes only; unknown keys reported as `field: null` | 16.5.1 [AQS/SEC-04] | error-body suite: an unknown key named `<script>` is not echoed | C |

## 5. Findings on the Sprint 1 design (2026-10-05)

| ID | Severity | Finding | Fix | Owner |
|---|---|---|---|---|
| S1-F1 | **Should-fix before any real-user beta** | ASVS 6.3.3: magic link is single-factor at L2 (T-ML-13) | PO accepts the residual risk in an ADR, or passkeys move into R1. Escalated 2026-10-05 as ADR 0031 (Proposed; decider: human PO) | human product owner (via EM) |
| S1-F2 | Should-fix before non-dev deployment | Expired sessions' staged bytes are not deleted until ST-038 (T-UV-7) | Keep ST-038 in Sprint 2; no non-dev deployment before it | BE (Sprint 2) |
| S1-F3 | Should-fix (Sprint 1) | v0 F-1 (shared DB role and S3 key for api and worker) still open; Sprint 1 adds email addresses to the same database | Separate roles before any non-dev deployment (v0 F-1) | SRE, BE |
| S1-F4 | Nit | Rate-limit rows keep IP addresses; retention unstated | Delete windows older than 24 h in the same job as the counter update | BE |

No Blocking finding for Sprint 1 dev use.

## 6. ASVS checklist rows this delta moves (for the checklist owner)

6.1.1, 6.1.3, 6.3.1, 6.3.4, 6.4.1, 6.5.1, 6.5.3, 6.5.4, 6.5.5, 6.6.2, 6.6.3, 7.1.1, 7.1.2, 7.3.1, 7.3.2, 5.2.2, 5.2.4, 5.2.6, 2.4.1 → "S1 designed" (this file, api-sprint-01, ADR 0025). 6.3.3 → "Open: PO risk decision". Documented authentication pathways (6.1.3, 6.3.4): magic link (all environments); dev identity provider (`dev`/`test` only, refused in `prod`); no others.
