# Threat model v0: upload, authentication, media URLs, worker sandbox

- **Status:** v0, for Sprint 0 and as the DoR input for the Sprint 1 security stories. The next revision is due when real sign-in (FR-001) and upload validation (FR-023) are designed (Sprint 1, D2).
- **Date:** 2026-10-03
- **Authors:** security-privacy-engineer (findings and controls), with principal-engineer (architecture, ADR 0011). Written into `docs/` by the principal-engineer's session. The security-privacy-engineer role is read-only (role file), so this document is its returned output.
- **Method:** STRIDE per element over a data-flow diagram, plus abuse cases. The STRIDE categories are Spoofing, Tampering, Repudiation, Information disclosure, Denial of service and Elevation of privilege. Using STRIDE is (judgment); no source for the method is in our verified research.
- **Scope:** the Sprint 0 walking skeleton:
  - the dev identity provider and session cookie;
  - `/matches`;
  - tus upload (ADR 0011);
  - the object store;
  - the Postgres queue;
  - the probe worker with ffprobe;
  - logs and traces.

  Out of scope until their sprint: real sign-in, LLM, GPU provider, sharing (none in the MVP), clips.
- **Target:** OWASP ASVS 5.0 Level 2 [AQS/SEC-01] (NFR-050). The checklist is in [`asvs-l2-checklist.md`](asvs-l2-checklist.md). ASVS item numbers outside the AQS-verified chapters (V2, V5, V8, V13, V14, V16) come from chapter files fetched on 2026-10-03 and listed in that checklist's "Sources" section.
- **Legal:** GDPR, ICO and EDPB obligations are **unverified** [AQS G3.5]. Nothing here asserts law. Questions for the human product owner are marked **PO-LEGAL**.

## 1. Assets and data classes (NFR-063) [AQS/SEC-05 14.1.1]

| Asset | Class | Where | Why it matters |
|---|---|---|---|
| Original match video (identifiable people, possibly minors, possibly third parties) | **High** | object store `originals/…`; staging `staging/…` while uploading | The privacy harm is large, and it is the main cost driver |
| Media facts (duration, fps, resolution, codec) | Low | Postgres | Technical metadata |
| Session token | **High** (credential) | cookie (browser); Postgres stores only its SHA-256 | Account takeover |
| Account (email in S1, display name) | Medium | Postgres | Personal data |
| Match title (free text; may contain names) | Medium | Postgres | Personal data about third parties is possible |
| Upload file name (`Upload-Metadata`) | Medium | **not stored** (API §6.2) | Often contains names or dates |
| Object-store, DB and OTLP credentials | **High** | environment / secret store | Lateral movement |
| Logs and traces | Medium | stdout → collector | Can leak PII and URLs if careless (NFR-069) |
| Job rows (match ID, stage, failure reason) | Low/Medium | Postgres | `failure_reason` may echo tool stderr, which is treated as untrusted |

## 2. Actors and abuse cases

| Actor | Capability | Abuse cases |
|---|---|---|
| **A1** Signed-in curious user (Carlos) | a valid session | AC1 read or upload to Ivy's match by ID (BOLA); AC2 enumerate IDs; AC3 mass-assign `owner_id` |
| **A2** Anonymous internet client | HTTP only | AC4 use the dev sign-in in production; AC5 CSRF via Ivy's browser; AC6 fill storage or CPU (huge or slow uploads, many sessions) |
| **A3** Malicious uploader (own account) | uploads crafted files | AC7 a crafted media file exploits ffprobe or the demuxers (RCE in the worker); AC8 a playlist or reference-style file makes ffprobe fetch internal URLs or local files (SSRF / LFI); AC9 path tricks in the file name (`../../etc/passwd.mp4`); AC10 a file that is not video, a "decompression bomb" or a pixel flood |
| **A4** Network attacker on path | observes and modifies traffic | AC11 steal a session cookie or a presigned URL |
| **A5** Insider or compromised CI or agent | repo or CI access | AC12 secrets in the repo or images; AC13 fault-injection seam enabled in production; AC14 a supply-chain package |
| **A6** Compromised worker (after AC7) | code execution in the worker | AC15 pivot to the internet, the DB or other users' media |

## 3. Data flow and trust boundaries

```
 Browser (PWA, https) ──TB1──▶ Web (Next.js) ──/api rewrite──▶ API (FastAPI)
                                                        │  TB2 (DB creds)    │ TB3 (S3 creds, write)
                                                        ▼                    ▼
                                                    Postgres ◀────────▶ Object store
                                                     (queue)                 ▲
                                                        ▲ TB4                │ presigned GET (≤15 min)
                                                        │                    │
                                         Worker sandbox (internal net only) ─┘
                                         └─ ffprobe (child process, untrusted input)  TB5
 Logs/traces ──▶ OTLP collector (TB6)
```

- **TB1:** internet to the app.
- **TB2/TB3:** app to its backing services.
- **TB4:** worker to the queue.
- **TB5:** parsing untrusted media.
- **TB6:** telemetry.

## 4. STRIDE threats and controls

Status codes:
- **C** = control specified, and a red-first test exists or the story builds it in Sprint 0;
- **P** = partially controlled in Sprint 0;
- **O** = open, with an owner and a sprint.

Findings are graded **Blocking / Should-fix / Nit**, per the role.

### 4.1 Upload (tus core; ADR 0011)

| ID | STRIDE | Threat | Control | ASVS / source | Test | Status |
|---|---|---|---|---|---|---|
| T-UP-1 | E/I | Carlos HEADs or PATCHes Ivy's upload by its URL (AC1) | Ownership in the same query (`id AND owner_id`); 404 identical to a missing upload; anonymous gets 401 | 8.2.2, 8.3.1 [AQS/SEC-03]; [AQS/SEC-09] | `test_bola_matrix.py` (HEAD/PATCH probes, inventory) | C |
| T-UP-2 | T | A PATCH at a wrong offset corrupts the stored bytes | 409 before any write; lock with `FOR UPDATE NOWAIT`; atomic PATCH | [AQS/STACK-06]; 2.3.3 [AQS/SEC-07] | `test_upload_resume.py` (0/30/41/100%), IT-00-07 | C |
| T-UP-3 | T | Two concurrent PATCHes interleave (flaky network) | Row lock; the second gets 409; part numbers come from committed state | 2.3.4 (fetched); ADR 0011 | QA to add a concurrent-PATCH integration test in ST-008 | P |
| T-UP-4 | T/E | The file name is used in a storage path (AC9) | `ObjectKeyPolicy` → `originals/{uuid4hex}`; metadata is not stored or used | 5.3.2 [AQS/SEC-02] | scenario "Stored names never come from the user's file name"; `ObjectKeyPolicy` unit tests | C |
| T-UP-5 | D | Huge declared length or huge chunk fills storage or memory (AC6) | `Upload-Length` ≤ `UPLOAD_MAX_BYTES` (413); `Content-Length` required and ≤ 64 MiB; ingress body and time limits | 5.2.1 [AQS/SEC-02]; [AQS/SEC-10] | 413 cases in `test_upload_resume.py`; caps test to add in ST-008 | P |
| T-UP-6 | D | Many open upload sessions, or slow-loris PATCHes, hold resources and storage (AC6) | **Sprint 0:** one session per match. **Sprint 1:** per-user quota of bytes and open sessions, rate limits, 24 h expiry with an abort-multipart sweeper, ingress request timeouts | 2.4.1 [AQS/SEC-07]; 5.2.4 (L3, adopted) [AQS/SEC-02]; FR-024; NFR-066(d) | — | **O (Should-fix before any public deployment; owner BE + SRE, Sprint 1)** |
| T-UP-7 | D | Tiny chunks amplify object-store I/O | Staging per chunk, read once (≈2x bound, ADR 0011); rate limit in Sprint 1 | [AQS/SEC-10] | — | P |
| T-UP-8 | T | A probe starts on a partial file, or before the upload completes | Enqueue only in the completion transaction | 2.3.1 [AQS/SEC-07] (NFR-060) | IT-00-08 | C |
| T-UP-9 | I | Upload responses cached by an intermediary or the service worker | `Cache-Control: no-store` on tus responses; the SW never caches `/api/*` | 14.3.2 [AQS/SEC-05]; NFR-067 | `test_head_reports_offset_and_length`; `security-headers.spec.ts` | C |
| T-UP-10 | T | Not-video content accepted, or content type trusted from the client (AC10) | **Sprint 1:** magic-byte and container checks via ffprobe on the stored object before `video_received` is final; caps of 10 GB and 150 min | 5.2.2, 5.2.1 [AQS/SEC-02] (NFR-053) | — | **O (Sprint 1, FR-023)** |
| T-UP-11 | R | No record of who uploaded what | Structured log `upload.created` / `upload.completed` with `account_id`, `match_id`, `upload_id`, size; no file name | 16.2.1 [AQS/SEC-04] | IT-00-15 log scan | P |

### 4.2 Authentication and session (dev identity provider; carried into S1)

| ID | STRIDE | Threat | Control | ASVS / source | Test | Status |
|---|---|---|---|---|---|---|
| T-AU-1 | S/E | Dev sign-in reachable in production: anyone becomes Ivy (AC4) | Routes registered only when `DEV_IDENTITY_ENABLED=true`; startup **refuses** `APP_ENV=prod` with it; seeded users only in dev/test; no default accounts in prod | 6.3.2 (fetched); 13.4.2 [AQS/SEC-06] | `test_dev_environment.py` (refuses to start) | C. **Blocking if regressed.** Also add a deploy-time check: prod config must not contain `DEV_IDENTITY_ENABLED` (SRE, ST-002) |
| T-AU-2 | S | Guessable or static session tokens | 256-bit CSPRNG reference tokens; stored as SHA-256; rotated on every sign-in | 7.2.2, 7.2.3, 7.2.4, 11.5.1 (fetched) | unit tests on the token generator (BE, ST-006) | P (test to add) |
| T-AU-3 | I | Token theft via script, network or URL (AC11) | `HttpOnly`; `Secure` + `__Host-` outside `APP_ENV=test`; never in URLs; HSTS at the edge | 3.3.1, 3.3.3, 3.3.4, 3.4.1 (fetched); 14.2.1 [AQS/SEC-05] | cookie-attribute test (BE, ST-006); E2E | P |
| T-AU-4 | S/T | CSRF: a foreign site makes Ivy's browser create matches or PATCH bytes (AC5) | `SameSite=Lax`; only non-simple requests (JSON / `Tus-Resumable`); `Origin` allowlist required in staging/prod | 3.3.2, 3.5.1, 3.5.3 (fetched) | Origin-rejection test (BE, ST-006) | P |
| T-AU-5 | R | Sign-in attempts not attributable | `auth.sign_in` success/failure logged with `account_id`; no username or token | 16.3.1, 16.2.5 [AQS/SEC-04] | IT-00-15; security-log assertion | P |
| T-AU-6 | I | Session survives sign-out | Server-side delete; cookie `Max-Age=0`; client clears stored upload URLs | 7.4.1 (fetched); 14.3.1 [AQS/SEC-05] | sign-out test (BE) and E2E (FE) | P |
| T-AU-7 | E | Mass assignment of `owner_id` or `status` (AC3) | Closed request schemas → 422; owner taken only from the session | 8.2.3 [AQS/SEC-03]; 15.3.3 (fetched); NFR-052 | `test_unknown_request_field_is_rejected` | C |
| T-AU-8 | I | Existence oracle via different status or body for foreign vs missing IDs (AC2) | Identical 404 bodies (except `support_ref`); malformed IDs → 404; 401 before lookup; UUIDv4 IDs | [AQS/SEC-09] | `test_other_user_gets_the_same_404…`, `test_match_ids_are_random_uuid4` | C |
| T-AU-9 | — | Real sign-in (magic link, passkeys): token in URL, link reuse, enumeration, brute force | Designed in Sprint 1: single use, 15 min, token stripped from the URL, rate limits; V6 out-of-band items | 6.5.1, 6.5.5, 6.6.2, 6.6.3, 6.3.1 (fetched); 14.2.1 [AQS/SEC-05]; FR-001 | — | **O (Sprint 1)** |

### 4.3 Media URLs

Sprint 0 gives **no media URL to the browser**. The worker reads originals through a presigned GET.

| ID | STRIDE | Threat | Control | ASVS / source | Test | Status |
|---|---|---|---|---|---|---|
| T-MU-1 | I | A presigned URL leaks through logs, traces, `failure_reason` or error bodies | Never log URLs; redact `X-Amz-*` query parameters in the log formatter; the ffprobe command line is not logged in full | 16.2.5 [AQS/SEC-04]; NFR-069 | IT-00-15 log scan (signed-URL pattern) | P |
| T-MU-2 | I | Long-lived URL usable after sharing or leakage | TTL ≤ 15 min (NFR-055); GET only; one object | 14.2.1 [AQS/SEC-05] | IT-00-16 (expiry → 403) | C (store behaviour verified on SeaweedFS, ADR 0008 note) |
| T-MU-3 | I | Future browser playback: URL for another user's object | Issue URLs only after the ownership check of the match; `Content-Disposition` with a generated name; no public bucket ACL | 5.4.1, 5.4.2 [AQS/SEC-02]; 8.2.2 [AQS/SEC-03] | BOLA matrix entry required when the route is added | O (when playback ships) |
| T-MU-4 | I | Bucket listing or anonymous read misconfigured | Bucket private; no anonymous policy; parity script asserts that anonymous GET → 403 | 13.4.3 [AQS/SEC-06] | add an anonymous-GET assertion to IT-00-16 (SRE) | P |
| T-MU-5 | T | The API's S3 credential can delete or overwrite any object | Separate least-privilege keys: API (put and multipart on `originals/` and `staging/`), worker (get only), retention job (delete) | 13.2.2, 13.3.2 [AQS/SEC-06]; NFR-056 | — | **O. Should-fix: today `api` and `worker` share one S3 key and one DB superuser through `x-app-env` in `infra/compose.yaml` (finding F-1)** |

### 4.4 Worker sandbox (probe stage, ffprobe)

| ID | STRIDE | Threat | Control | ASVS / source | Test | Status |
|---|---|---|---|---|---|---|
| T-WS-1 | E | A crafted file exploits a demuxer bug; code runs in the worker (AC7) | Worker container: internal network only, read-only root, `cap_drop: ALL`, `no-new-privileges`, CPU and memory limits (in `infra/compose.yaml`); ffprobe runs as a child process with a wall-clock timeout; non-root user; pinned FFmpeg version logged at startup | 13.2.4 [AQS/SEC-06]; [AQS/SEC-10]; NFR-054 | IT-00-10 (CI only; blockers.md) | P |
| T-WS-2 | I | ffprobe follows references inside the file (playlists, `file:`, other protocols) to internal hosts or local files (AC8) | Run ffprobe with an explicit protocol allowlist (only what the presigned URL needs) and an input-format allowlist of the MP4/MOV demuxer, so ffprobe does not auto-detect formats. The network sandbox is the second layer. The specific flags are (judgment), from FFmpeg's documented options; the ML engineer confirms them in ST-009 | 1.3.6 SSRF (fetched); 13.2.4 [AQS/SEC-06] | **Add a test:** an HLS playlist renamed `.mp4` that points to `file:///etc/passwd` and an internal URL → `ProbeFailed`, with no fetch (ML + QA, ST-009) | **O. Should-fix in ST-009 (finding F-2)** |
| T-WS-3 | E | User input reaches the command line (AC9) | Argument vector, no shell; only the presigned URL and fixed flags; never the user file name | 1.2.5 (fetched); 5.3.2 [AQS/SEC-02] | unit test that asserts the argv (ML, ST-009) | P |
| T-WS-4 | D | Probe hangs or explodes (AC10) | Wall-clock timeout; CPU and memory limits; a failure → `ProbeFailed`, job `failed`, no partial facts | [AQS/SEC-10]; [AQS/SEC-12]; NFR-047 | `test_fail_closed.py`; `test_job_resilience` | C |
| T-WS-5 | E | A compromised worker pivots to the DB with broad rights (AC15) | Worker DB role limited to the job tables and `media_facts` (no account or session tables). It is in `sandbox` today together with Postgres, which is accepted because the queue lives there (decision-log 2026-10-03, SRE) | 13.2.2 [AQS/SEC-06]; NFR-056 | — | **O. Should-fix before beta (F-1)** |
| T-WS-6 | T | Untrusted ffprobe output (stderr, tags) stored or rendered | Parse JSON into `MediaFacts` with strict types; store only allowlisted fields; `failure_reason` is a fixed code, not stderr | 15.3.1 (fetched); [AQS/SEC-08 API10] | `MediaFacts.from_ffprobe` unit tests (§5) | P |
| T-WS-7 | E | The fault-injection seam (`RACKET_FAULT_INJECTION`) is live outside tests (AC13) | Honoured only when `APP_ENV=test`; regression test `test_fault_injection_is_ignored_outside_test_env` (ADR 0012) | 15.2.3 (fetched); [AQS/SEC-12] | that regression test | C (review the guard in the ST-007 PR) |
| T-WS-8 | — | Licence: the worker image uses Debian's GPL FFmpeg | LGPL build required in the product (ADR 0008) | NFR-062 | blockers.md row (SRE) | O (ML + security, before any release) |

### 4.5 Cross-cutting

| ID | STRIDE | Threat | Control | Source | Status |
|---|---|---|---|---|---|
| T-X-1 | I | Error bodies leak internals | Central handler plus fallback; fixed messages; `support_ref` | 16.5.1 [AQS/SEC-04]; [AQS/SEC-12] | C (`test_error_bodies.py`) |
| T-X-2 | T | Log injection through `X-Request-ID` or titles | JSON logging (encoded); request ID allowlist pattern | 16.4.1 [AQS/SEC-04] | P |
| T-X-3 | D | Malformed `traceparent` breaks requests | Ignore it and start a new trace | [AQS/OPS-06] | C (`test_trace_header.py`) |
| T-X-4 | I | Secrets in the repo, images or logs | gitleaks; env only; settings logged redacted; PreToolUse hook blocks `.env*` | 13.3.1 [AQS/SEC-06]; NFR-056 | C (ST-002/ST-003) |
| T-INF-1 | I | Debug and docs endpoints in prod | `/docs`, `/openapi.json` off in staging/prod; debug off | 13.4.2, 13.4.5 [AQS/SEC-06, fetched] | P |
| T-INF-2 | I | `/readyz` reveals dependency topology publicly | Internal only at the ingress | 13.4.5 (fetched) | O (SRE, at the first deploy) |
| T-X-5 | — | Agents with broad tool access damage the repo or exfiltrate secrets | Hooks; sandboxing at filesystem and network boundaries | [DPA/AI-07], [DPA/AI-10] | C (ST-003) |

## 5. Findings on the current repository (2026-10-03)

| ID | Severity | Finding | Evidence | Fix suggestion | Owner |
|---|---|---|---|---|---|
| F-1 | **Should-fix** (Blocking before any non-dev deployment) | `api` and `worker` share one `DATABASE_URL` (the DB owner `racket`) and one S3 key pair through the `x-app-env` anchor | `infra/compose.yaml` lines 12-15 (`DATABASE_URL: postgresql://${POSTGRES_USER}…`, `S3_ACCESS_KEY_ID`) used by both services | Separate DB roles (`racket_api`, `racket_worker`) and S3 identities (SeaweedFS `s3.json` supports several identities) with the least privileges in T-MU-5 and T-WS-5. Keep parity in dev | sre-devops-engineer (ST-001 follow-up), BE |
| F-2 | **Should-fix** (in ST-009) | ffprobe protocol and format allowlist plus an SSRF/LFI test are not yet in the ST-009 acceptance notes | sprint-00 §3.1 ST-009 lists network isolation and no file names, but not protocol restrictions | Add the T-WS-2 control and test to ST-009 | senior-ml-cv-engineer, QA |
| F-3 | Should-fix (Sprint 1) | No quotas or rate limits on upload creation and PATCH | API §3 reserves 429; no story yet | Sprint 1 story: per-user open-session and byte quota, PATCH rate limit (2.4.1, 5.2.4) | business-analyst to write; BE |
| F-4 | Nit | `infra/env.example` lacks the upload and origin variables this contract adds | api-sprint-00 §9 | Add with comments | SRE |

There are no Blocking findings for Sprint 0 dev use. **Accepting residual risk** for any non-dev deployment needs a human decider in an ADR (role rule).

## 6. Security NFR proposals to the BA (Sprint 1 DoR)

1. Upload quotas and rate limits (F-3): 2.4.1 [AQS/SEC-07]; 5.2.4 [AQS/SEC-02].
2. ffprobe protocol and format allowlist with an SSRF/LFI regression test (F-2): 1.3.6 (fetched); NFR-054 extension.
3. Separate service identities (F-1): NFR-056 already covers it, so this needs a story, not a new NFR.
4. Session lifetime documentation for real sign-in: 7.1.1, 7.3.1, 7.3.2 (fetched).
5. Cookie and Origin tests as part of the BOLA/CSRF regression suite: 3.3.x and 3.5.1 (fetched).

## 7. Questions for the human product owner (PO-LEGAL)

- Lawful basis for storing footage of third parties and minors; age gate wording (NFR-070, OQ-05).
- Consent for training use (Dataset & Labelling, OQ-06).
- Retention windows (ADR 0006, OQ-07).
