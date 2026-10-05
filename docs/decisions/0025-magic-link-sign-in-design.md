# 0025. Magic-link sign-in: token in the URL fragment, exchanged by POST; sessions of 30 days absolute, 7 days idle

- **Status:** Accepted for Sprint 1 (principal-engineer with security-privacy-engineer). Residual risk on ASVS 6.3.3 (single factor) needs the human product owner's acceptance before any real-user beta (see Consequences).
- **Date:** 2026-10-05
- **Deciders:** principal-engineer, security-privacy-engineer
- **Consulted:** senior-backend-engineer, senior-frontend-engineer, principal-designer (flows A-01..A-05, D-4)
- **Related:** ST-013, ST-014; FR-001, FR-011; NFR-023, NFR-032, NFR-055, NFR-057, NFR-067, NFR-069; api-sprint-01 §2; threat model `docs/security/threat-model-sprint-01.md` §2; ADR 0008 (Mailpit in dev); ADR 0017 (job queue)

## Context and problem statement

FR-001 replaces the dev identity provider with an emailed, single-use link that expires after 15 minutes. Three design questions decide most of the security: where the one-time token sits in the link, how the browser turns it into a session, and how long the session lives. Email links are opened by mail-scanner bots, previewed on other devices and copied into chats, and URLs leak through history, `Referer` and logs [AQS/SEC-05 14.2.1].

## Decision drivers

- No token left in the URL after the exchange (NFR-055) [AQS/SEC-05 14.2.1]; no token in server or proxy logs [AQS/SEC-04 16.2.5].
- Single use and 15-minute lifetime (FR-001; ASVS 6.5.1, 6.5.5); CSPRNG tokens (6.5.3, 6.4.1); rate limits (6.3.1, 6.6.3; NFR-023).
- No account-existence oracle (flows D-4).
- Works when the link is opened on another device or browser than the one that asked (phones open mail links in the system browser, not the installed PWA) (judgment).
- Session lifetimes documented (ASVS 7.1.1, 7.1.2, 7.3.1, 7.3.2).

## Considered options

1. **Token in the URL fragment (`/auth/callback#token=…`); the page POSTs it to `/auth/exchange`; no device binding** (chosen).
2. **Token in the query string; `GET /auth/callback?token=…` on the API sets the cookie and redirects.**
3. **Option 1 plus device binding:** the link only works in the browser that requested it (a `__Host-` nonce cookie set at request time).
4. **A 6-digit code typed by the user instead of a link.**

## Decision outcome

Chosen option: **1**.

- **Link:** `{PUBLIC_WEB_ORIGIN}/auth/callback#token=<43 chars base64url>`. The origin comes from configuration, **never** from the `Host` header (host-header poisoning of the link). The fragment is not sent to any server, so it never reaches access logs, the ingress, or a `Referer`.
- **Token:** 32 bytes from a CSPRNG (256 bits; ASVS 6.5.3, 6.5.4). Stored only as SHA-256 in `sign_in_links(token_sha256 PK, email_key, created_at, expires_at, used_at)`. Lifetime 15 minutes (`MAGIC_LINK_TTL_SECONDS=900`). Requesting a new link does not revoke older unused links (judgment: avoids a race when two emails arrive out of order; each still expires in 15 minutes).
- **Exchange:** A-03 reads the fragment, immediately calls `history.replaceState` to remove it, then `POST /auth/exchange {"token": …}`. The server marks the link used in the same transaction that creates the session (`UPDATE … SET used_at = now() WHERE token_sha256 = :h AND used_at IS NULL AND expires_at > now()`; one row or refuse). Unknown, used and expired tokens get the **same** 401 `link_expired` (D-4: A-04 does not say which). A mail scanner that fetches the link with GET loads a static page and spends nothing.
- **Accounts** are created at the first successful exchange, not at the request, so typos and abuse do not create accounts. `POST /auth/links` answers 202 for every well-formed address (no existence oracle) and the email is sent by a queued job (ADR 0017), so the response time does not depend on whether an account exists.
- **No device binding** (option 3 rejected, below). The binding is to the email address: the link signs in the account for the address it was sent to (ASVS 6.6.2 is met by binding the token to its one request record and address).
- **Session:** the Sprint 0 cookie and token scheme unchanged (api-sprint-00 §2): `__Host-racket_session`, `HttpOnly; Secure; SameSite=Lax`, 256-bit reference token stored hashed, rotated on every sign-in. **Absolute lifetime 30 days; inactivity timeout 7 days**, with `last_seen_at` updated at most once per hour per session (ASVS 7.1.1, 7.3.1, 7.3.2; values are judgment). **At most 10 concurrent sessions** per account; the 11th sign-in deletes the oldest (ASVS 7.1.2). Sign-out deletes the server session and returns `Clear-Site-Data: "cache"`; the client clears its own storage (FR-011).
- **Rate limits** (NFR-023 partial; ASVS 6.3.1, 6.6.3): per email key 5 link requests per rolling 10 minutes (the sprint-01 §7.1 Gherkin); per client IP 20 per 10 minutes; exchange attempts 30 per 10 minutes per IP. Over the limit: 429 `rate_limited` with `Retry-After` and `retry_at`. The per-email limit applies to unknown addresses too, so it reveals nothing.
- **Logging** (NFR-057, NFR-069): `auth.link_requested`, `auth.link_exchanged` (`outcome`), `auth.signed_out`, `auth.rate_limited` to `racket.security`, with UTC time, `request_id`, `account_id` when known, and `email_key` = the first 16 hex characters of HMAC-SHA256(`AUTH_EMAIL_KEY`, normalised email). Never the address, the token or its hash.
- **Dev:** the dev identity provider stays dev/test only (api-sprint-00 §2). Mail goes to Mailpit (ADR 0008).

## Pros and cons of the options

### Option 1
- Good: the token never reaches a server log or `Referer`; GET-prefetching mail scanners cannot burn the link; the exchange is a POST covered by the existing CSRF rules (`Origin` allowlist, JSON body); works across devices.
- Bad: needs JavaScript on A-03 (the PWA already requires it); a token visible in the address bar until `replaceState` runs (milliseconds; no external assets on A-03).

### Option 2
- Good: no JavaScript; simplest server flow.
- Bad: the token is in the query string, so it lands in ingress and app access logs and in browser history before the redirect (fails the spirit of 14.2.1); mail scanners that GET links consume single-use tokens and users see "expired" on first click.

### Option 3
- Good: a forwarded or intercepted link is useless in another browser.
- Bad: breaks the common phone flow (request in the installed PWA, open from the mail app in the system browser) and the "request on laptop, open on phone" flow; FR-001 copy promises neither. The threat it covers needs mailbox access, which already defeats any email-based recovery (judgment).

### Option 4
- Good: no URL at all; works across devices.
- Bad: a code is a typed secret with low entropy, so it needs stricter attempt limits; more typing courtside; closer to a "cognitive function test" concern for some users (NFR-032 judgment).

## Consequences

- Good: NFR-055 holds by construction; IT-01-01..03 test the flow, the rate limit and the logs.
- Trade-offs accepted: a link forwarded by the user to someone else signs that person in as the user, within 15 minutes, once (judgment: same exposure as any email recovery).
- **Residual risk, ASVS 6.3.3 (L2 asks for MFA or a combination of factors):** an email link is a single factor. Passkeys are backlog. This is acceptable for dev and internal testing; **before any real-user beta the human product owner must accept or reject this residual risk in an ADR** (role rule: risk acceptance needs a human decider). Tracked in `docs/sprints/01/blockers.md`.
- Follow-up: production email provider and sender-domain records (Sprint 4 ADR, sprint-01 §10); account deletion purges sessions and links (ASVS 7.4.2, Sprint 3).

## Evidence

| Claim | Evidence | Type |
|---|---|---|
| Sensitive data must not be in URLs | [AQS/SEC-05 14.2.1] | verified source |
| No credentials in logs | [AQS/SEC-04 16.2.5] | verified source |
| Single use, defined lifetime, CSPRNG, entropy, rate limit, binding | ASVS 6.5.1, 6.5.3, 6.5.4, 6.5.5, 6.6.2, 6.6.3, 6.3.1 (`docs/security/asvs-l2-checklist.md`, fetched 2026-10-03) | standard |
| Session lifetime and concurrency must be documented | ASVS 7.1.1, 7.1.2, 7.3.1, 7.3.2 (same checklist) | standard |
| 5 requests in 10 minutes is the rate-limit threshold | sprint-01 §7.1 "Too many link requests" | requirement |
| Same response for unknown and known addresses; no expired-vs-used distinction | flows D-4; sprint-01 §14.3.1 | design |
| Mail scanners prefetch links; phones open mail links outside the PWA; 30/7-day lifetimes | (judgment) | judgment |

## Confirmation

- IT-01-01 (request → Mailpit → exchange → session; reuse fails), IT-01-02 (429 with retry time), IT-01-03 (log lines without email), E2E-01-01 (address bar has no token).
- A unit test that the link base comes from `PUBLIC_WEB_ORIGIN` even when the request carries a different `Host`.
