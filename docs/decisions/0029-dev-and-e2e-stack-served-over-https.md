# 0029. The dev and E2E stack is served over https (`web-tls`), not given an insecure cookie

- **Status:** Accepted (security-privacy-engineer decision; human product owner directive 2026-10-05 in `docs/requirements/po-input-2026-10-05.md` addendum: "use HTTPS for the dev stack", option (c) not to be used)
- **Date:** 2026-10-05
- **Deciders:** human product owner (directive), security-privacy-engineer (decision and threat reasoning); sre-devops-engineer, senior-backend-engineer, senior-frontend-engineer (implementation)
- **Consulted:** senior-qa-engineer (E2E specs are QA-owned; test-change row in `docs/sprints/01/test-change-requests.md`)
- **Related:** blockers.md 2026-10-05 rows "E2E WebKit cannot sign in over `http://localhost`" and the BE input row; ST-006, ST-010, ST-013, ST-014; ADR 0025 (magic link), ADR 0027 (mailer); api-sprint-00 §2; T-ML-8; NFR-024 (browser matrix)

## Context and problem statement

Outside `APP_ENV=test`, the API sets the session cookie as `__Host-racket_session` with `Secure`, `HttpOnly`, `Path=/` and `SameSite=Lax` (`backend/src/racket/players/api.py`). The Compose stack, which CI's E2E job uses, ran `APP_ENV=dev` over plain `http://localhost:3000`. WebKit drops a `Secure` cookie set over http, so every WebKit journey that signs in failed. On CI run 37277549983 (job E2E), 3 of 14 tests failed, all `[webkit]`, at `signInAs` (`web/e2e/helpers/journey.ts:17`), while Chromium passed. Chromium passes because it treats `http://localhost` as a secure context. ST-013's magic-link exchange uses the same `set_session_cookie` path, so it would hit the same problem. The question: how do dev and E2E sign in on every browser in the matrix without weakening the production cookie?

## Decision drivers

- Dev/prod parity [AQS/OPS-05]. The E2E suite should run the same cookie attributes as production, so it catches regressions in cookie handling.
- `__Host-` requires `Secure`, `Path=/` and no `Domain` (RFC 6265bis §4.1.3.2, judgment: not in our verified sources). Dropping `Secure` also means renaming the cookie.
- An insecure switch must never be able to reach staging or prod: fail closed [AQS/SEC-12].
- No private key in the repository [AQS/SEC-06, NFR-056].
- The per-IP sign-in limits must keep keying on the real client address (T-ML-8).

## Considered options

1. **(a) Serve the dev/E2E stack over https through a TLS-terminating proxy** (chosen). Caddy `tls internal` sits in front of the web as `web-tls` and is the only browser entry point.
2. **(b) Run E2E with `APP_ENV=test`.** The cookie becomes non-`Secure` `racket_session`, and the test-only seams (fault injection, defaults) switch on in the E2E stack.
3. **(c) A dev-only `SESSION_COOKIE_INSECURE` flag**, refused by `Settings` outside `dev`/`test`, which renames the cookie to `racket_session` and drops `Secure`.

### Pros and cons of the options

- **(a)** Good: identical cookie name and attributes in dev, E2E and prod, so every browser exercises the production cookie, and the `https` origin in sign-in links matches prod. No new configuration surface in the API. It also closes a dev-stack gap measured on 2026-10-05: before this change, a client-supplied `X-Forwarded-For` passed straight through the Next rewrite. Caddy now replaces it with the real peer (see Evidence). Bad: one more container. The dev CA is untrusted, so browsers warn on manual use, and Playwright needs certificate handling. Chromium also refuses to register a service worker on an origin with a certificate error, even with `ignoreHTTPSErrors`, so the Chromium project needs `--ignore-certificate-errors` for the loopback origin, and CI installs the public root certificate.
- **(b)** Good: no new service. Bad: E2E then never tests the production cookie. `APP_ENV=test` also turns on test seams (`RACKET_FAULT_INJECTION`, test-only defaults) in a stack that looks like dev. The weakest parity of the three.
- **(c)** Good: small code change (BE estimated it test-first). Bad: a security-relevant switch that exists in production code and must be guarded forever. The cookie name differs between dev and prod, so E2E tests a different cookie than production. One misconfigured deployment env would be guarded only by `Settings`.

## Decision outcome

Chosen option: **(a)**. Implementation:

- `infra/compose.yaml`: new `web-tls` service, `caddy:2.10.2-alpine` from `${DOCKERHUB_REGISTRY}`. It publishes `127.0.0.1:${WEB_HOST_PORT:-3000}:443`, so the default origin is `https://localhost:3000`, and has a read-only root FS, `cap_drop: [ALL]` plus `NET_BIND_SERVICE`, `no-new-privileges`, and a healthcheck on an unpublished `:8080/healthz`. The `web` service is **no longer published** to the host, so there is no plain-http door.
- `infra/tls/Caddyfile`: `tls internal`, `skip_install_trust`, `admin off`, no `trusted_proxies`, no ACME. The CA and leaf key are generated at first start into the `caddy-data` volume. Nothing is committed (guarded by `infra/tests/test_compose_tls.py::test_no_private_key_or_certificate_is_committed`).
- `PUBLIC_WEB_ORIGIN=https://localhost:3000` in `infra/env.example`. `TRUSTED_PROXY_HOPS` stays `1` (measured, see Evidence).
- CI E2E job: `BASE_URL=https://localhost:3000`. A new step copies **only** `root.crt` out of `web-tls`, adds it to the runner's trust store and proves the chain with `curl --fail` (no `-k`).
- Playwright (`web/playwright.config.ts`): `ignoreHTTPSErrors` and Chromium's `--ignore-certificate-errors` apply only when `trustsDevCertificate(baseURL)` holds: an `https:` URL whose hostname is exactly `localhost`, `127.0.0.1` or `[::1]`, with no userinfo (`web/src/lib/security/dev-tls.ts`). The previous check, `startsWith('https://localhost')`, also matched `https://localhost.attacker.example`.
- API `Settings`: `staging`/`prod` now refuse a non-https `PUBLIC_WEB_ORIGIN` (`ConfigurationError`). The sign-in link carries a token, and the cookie is `Secure`-only. There is deliberately **no** setting that drops `Secure` outside `test`. `backend/tests/unit/players/test_session_cookie_policy.py` pins both.
- The no-Docker local recipe (`web/README.md`) stays on http for Chromium only, and the README says so.

### Threat reasoning (security-privacy-engineer)

- **Dev CA key compromise:** the key exists only in a Docker volume on a developer machine or an ephemeral CI runner. It is trusted only by that runner's system store, and only during the E2E job. Browsers on developer machines do not trust it (`skip_install_trust`). Impact is limited to impersonating `localhost` on that machine. Accepted (judgment).
- **Certificate-error bypass leaking to real hosts:** both bypasses are gated on an exact loopback hostname, and unit tests cover look-alike hosts (`localhost.attacker.example`, `localhost@attacker.example`).
- **Rate-limit evasion via forged `X-Forwarded-For` (T-ML-8):** the plain-http stack accepted a forged header (it passed through the Next rewrite). The `web-tls` stack does not (measured). Production topology must give the same guarantee. That is recorded for the deployment ADR, not decided here.
- **Insecure cookie reaching production:** not possible by configuration. No switch exists, and staging/prod also refuse an http sign-in origin.

## Evidence

- CI run 37277549983, job E2E: 3 failed, all `[webkit]`, at `signInAs`. Chromium passed (blockers.md row).
- Local stack (`docker compose -p racket-tls ... up -d --build --wait`, all services healthy):
  - `POST https://localhost:13000/api/dev/sign-in` → `HTTP/2 204`, `set-cookie: __Host-racket_session=…; HttpOnly; Max-Age=43200; Path=/; SameSite=lax; Secure`.
  - `curl --cacert root.crt https://localhost:13000/` → `200 ssl_verify=0`. `http://localhost:13000/` → `400` (no plain-http door).
  - Header echo in place of the API: with and without `X-Forwarded-For: 203.0.113.9`, the API received `x-forwarded-for: 172.21.0.1` (the host gateway), `x-forwarded-proto: https`. With `TRUSTED_PROXY_HOPS=1`, the rate-limit key was `link:ip:172.21.0.1`. A first attempt with `2` keyed on the web container (`link:ip:172.21.0.8`), so `1` is correct.
  - Chromium: `navigator.serviceWorker.register('/sw.js')` with only `ignoreHTTPSErrors` → `SecurityError: An SSL certificate error occurred when fetching the script`. With `--ignore-certificate-errors` → `activated`.
- WebKit is not installed in the sandbox (`/opt/pw-browsers` has no webkit), so the WebKit result comes from GitHub CI (see dated note below or `docs/sprints/01/blockers.md`).

## Consequences

- Positive: production cookie parity on every browser. Sign-in links use an https origin. The dev stack no longer trusts a client's `X-Forwarded-For`.
- Negative: one more service. Manual browsing to `https://localhost:3000` shows a certificate warning unless the developer chooses to trust the dev root. Developers with an old `infra/.env` must update `PUBLIC_WEB_ORIGIN` to https (Compose still starts, but links point at http).
- Follow-ups: the deployment ADR must state how the edge sets `X-Forwarded-For` and how many hops the API trusts (T-ML-8).
